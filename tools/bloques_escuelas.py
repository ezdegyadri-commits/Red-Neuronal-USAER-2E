"""Conciliación local de bloques fijos de USAER; nunca inicia el siguiente bloque."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from getpass import getpass
import json
from pathlib import Path
import time
import tracemalloc

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from config.settings import ESCUELAS_USAER
from tools.copia_controlada import (leer_json, permiso_real, preparar_bd, verificar_destino,
                                   verificar_paquete)
from tools.migracion_paralela import PESTANAS
from tools.expedientes_b01 import ICHC, conteo_ichc, evidencia_ichc
from utils.text import normalizar_texto

BLOQUES = {
    "USAER-B01": ("ESC-001", "ESC-002", "ESC-003", "ESC-004"),
    "USAER-B02": ("ESC-005", "ESC-006", "ESC-007", "ESC-008"),
}
NOMBRES = {clave: nombre for nombre, clave in ESCUELAS_USAER.items()}
CCT_PUBLICOS = {
    "ESC-001": ("31DPR0414P",), "ESC-002": ("31DPR0232G",),
    "ESC-003": ("31DPR0466V",), "ESC-004": ("31EPR0232F", "31EPR0771P"),
    "ESC-005": ("31EPR0039A",), "ESC-006": ("31EPR0040Q",),
    "ESC-007": ("31EPR0075F",), "ESC-008": ("31EPR0092W",),
}
COMPATIBLES = {"Escuelas", "Alumnos", "Documentos_Expediente", "Archivos_Expediente", "EPP_Versiones",
               "NEE", "Planeaciones_Versiones", "Informes", "Actas", "Anexo3_Deteccion", "Anexo4_Sugerencias",
               "Anexo5_Eventos", "Anexo7_Derivacion", "Registro_Visitas", "Expedientes",
               "Relaciones_Documentos", "Asignaciones_Apoyo"}
ESPACIO = text("""SELECT coalesce(sum(pg_total_relation_size(c.oid)), 0)
    FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
    WHERE n.nspname='copia_controlada' AND c.relkind='r'""")


def catalogo():
    return {bloque: [{"id": clave, "nombre": NOMBRES[clave], "cct_publicos_por_cotejar": CCT_PUBLICOS[clave]}
                     for clave in claves]
            for bloque, claves in BLOQUES.items()}


def preparar_bloque(engine, bloque, paquetes, *, clase, aplicar=False, referencia=None, padron=None):
    claves = BLOQUES[bloque]
    if not 1 <= len(paquetes) <= len(claves):
        raise ValueError("Indica hasta cuatro paquetes de un mismo bloque.")
    if clase == "real":
        permiso_real(referencia)
    verificar_destino(engine.url, clase)
    informes, alumnos, ccts = {}, set(), set()
    for paquete in paquetes:
        m = verificar_paquete(paquete, clase=clase)
        escuela = m["escuela"]
        if escuela not in claves or escuela in informes:
            raise ValueError("Escuela ajena o repetida en el bloque.")
        hojas = paquete["copia"]["pestanas"]
        catalogo_escuela = next(f for f in hojas["Escuelas"][1:] if any(c.strip() for c in f))
        fila = dict(zip(hojas["Escuelas"][0], catalogo_escuela))
        cct = fila.get("CCT", "").strip().upper()
        turno = normalizar_texto(fila.get("Turno", ""))
        if clase == "real" and (len(cct) != 10 or not cct.isascii() or not cct.isalnum()
                                 or cct in ccts or normalizar_texto(fila.get("Nombre_Escuela", ""))
                                 != normalizar_texto(NOMBRES[escuela])):
            raise ValueError("Coteja CCT y nombre con el padrón institucional autorizado.")
        if clase == "real":
            validado = (padron or {}).get(escuela, {})
            if (cct != validado.get("cct", "").strip().upper() or not turno
                    or turno != normalizar_texto(validado.get("turno", ""))
                    or normalizar_texto(validado.get("nombre", "")) != normalizar_texto(NOMBRES[escuela])):
                raise ValueError("CCT, nombre o turno difieren del padrón autorizado.")
        ccts.add(cct)
        identidades = set(m["identidades"]["Alumnos"])
        if alumnos & identidades:
            raise ValueError("Un alumno aparece en dos escuelas del bloque. Conserva las copias y concilia su traslado.")
        alumnos.update(identidades)
        informes[escuela] = {
            "nombre_catalogo": NOMBRES[escuela], "cct_de_la_copia": cct or None,
            "turno_de_la_copia": turno or None,
            "cct_publicos_por_cotejar": CCT_PUBLICOS[escuela],
            "cct_coincide_con_referencia_publica": cct in CCT_PUBLICOS[escuela] if cct else None,
            "capturada": m["capturada"], "alumnos": m["pestanas"]["Alumnos"]["filas"],
            "expedientes_explicitos": m["pestanas"].get("Expedientes", {}).get("filas", 0),
            "filas_documentales": {n: datos["filas"] for n, datos in m["pestanas"].items()
                                    if n not in {"Escuelas", "Alumnos"}},
            "compatibilidad_por_conciliar": sorted(COMPATIBLES & hojas.keys()),
            "solo_preparacion": sorted(hojas.keys() - COMPATIBLES),
            "pestanas_ausentes": sorted(PESTANAS.keys() - hojas.keys()),
            "errores_conciliacion": {n: {k: v for k, v in datos["errores"].items() if v}
                                    for n, datos in m["pestanas"].items() if any(datos["errores"].values())},
        }
        if escuela == ICHC:
            informes[escuela]["asignaciones"] = conteo_ichc(hojas)
            informes[escuela]["evidencia_en_padron_sin_conceder_acceso"] = evidencia_ichc(hojas)
    tracemalloc.start()
    reloj, cpu = time.monotonic(), time.process_time()
    try:
        if aplicar:
            with engine.begin() as db:
                db.execute(text("SELECT pg_advisory_xact_lock(28150038)"))
                espacio_anterior = db.scalar(ESPACIO)
                for paquete in paquetes:
                    informes[paquete["manifiesto"]["escuela"]]["preparacion"] = preparar_bd(
                        engine, paquete, aplicar=True, referencia=referencia, _conexion=db,
                    )
                almacenamiento = int(db.scalar(ESPACIO) - espacio_anterior)
        else:
            for paquete in paquetes:
                informes[paquete["manifiesto"]["escuela"]]["preparacion"] = preparar_bd(
                    engine, paquete, referencia=referencia,
                )
            almacenamiento = None
        _, pico = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    estados = Counter()
    for informe in informes.values():
        estados.update(informe["preparacion"].get("estados", {}))
    cotejo = [escuela for escuela, informe in informes.items()
              if clase == "real" and not informe["cct_coincide_con_referencia_publica"]]
    if estados["cuarentena"]:
        estado = "bloqueado_por_cuarentena"
    elif cotejo:
        estado = "bloqueado_por_cotejo_cct"
    elif informes.get(ICHC, {}).get("asignaciones", {}).get("pendientes"):
        estado = "bloqueado_por_asignaciones"
    else:
        estado = "pendiente_validacion_operativa"
    return {
        "bloque": bloque, "clase": clase, "aplicado_en_preparacion": aplicar,
        "estado_validacion": estado, "cct_requieren_cotejo": cotejo,
        "ultima_conciliacion": datetime.now(timezone.utc).isoformat(),
        "escuelas": informes, "faltantes": [c for c in claves if c not in informes],
        "alumnos": sum(r["alumnos"] for r in informes.values()),
        "estados": dict(estados),
        "recursos": {"cpu_proceso_segundos": round(time.process_time() - cpu, 4),
                     "duracion_segundos": round(time.monotonic() - reloj, 4),
                     "pico_asignaciones_python_bytes": pico,
                     "crecimiento_tablas_preparacion_bytes": almacenamiento},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    comandos = parser.add_subparsers(dest="comando", required=True)
    comandos.add_parser("catalogo")
    preparar = comandos.add_parser("preparar")
    preparar.add_argument("bloque", choices=BLOQUES)
    preparar.add_argument("paquetes", type=Path, nargs="+")
    preparar.add_argument("--aplicar", action="store_true")
    preparar.add_argument("--real", action="store_true")
    preparar.add_argument("--referencia")
    preparar.add_argument("--padron-autorizado", type=Path)
    args = parser.parse_args()
    if args.comando == "catalogo":
        print(json.dumps(catalogo(), ensure_ascii=False, indent=2))
        return
    try:
        clase = "real" if args.real else "ensayo"
        if args.real:
            permiso_real(args.referencia)
            if not args.padron_autorizado:
                raise ValueError("Se requiere el padrón autorizado de CCT y turno.")
        padron = leer_json(args.padron_autorizado) if args.real else None
        if len(args.paquetes) > len(BLOQUES[args.bloque]):
            raise ValueError("Un bloque admite hasta cuatro paquetes.")
        paquetes = [leer_json(archivo) for archivo in args.paquetes]
        url = make_url(getpass("URL del PostgreSQL privado: "))
        verificar_destino(url, clase)
        engine = create_engine(url, hide_parameters=True, connect_args={"connect_timeout": 5})
        try:
            resultado = preparar_bloque(engine, args.bloque, paquetes, clase=clase,
                                        aplicar=args.aplicar, referencia=args.referencia, padron=padron)
        finally:
            engine.dispose()
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
    except (KeyError, ValueError, OSError):
        raise SystemExit("Bloque cancelado. Revisa manifiestos, destino y conciliación en el entorno privado.") from None
    except Exception:
        raise SystemExit("Falló la preparación; la transacción de escritura se revirtió.") from None


if __name__ == "__main__":
    main()

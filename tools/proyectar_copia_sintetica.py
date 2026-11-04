"""Proyección aditiva del padrón y los anexos tabulares hacia una SPA sintética local."""
from argparse import ArgumentParser
import json
import os
from pathlib import Path
import sys

from sqlalchemy import select, text
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from data.sincronizacion_pg import DESTINOS, preparar as preparar_tablas
from tools.migracion_paralela import MAX_BYTES, preparar, verificar_base_local, verificar_destino_local
from tools.documentos_historicos import TABLAS_DOCUMENTOS, proyectar_documentos
from tools.expedientes_b01 import TABLAS_B01, proyectar_asignaciones, proyectar_expedientes

TABLAS = ("Escuelas", "Alumnos", "Anexo3_Deteccion", "Anexo4_Sugerencias",
          "Anexo5_Eventos", "Anexo7_Derivacion", "Registro_Visitas")
ARCHIVOS = {"Documentos_Expediente", "Archivos_Expediente"}


def proyectar(engine, copia, *, aplicar=False):
    verificar_destino_local(engine.url, "proyeccion")
    _, conciliacion = preparar(copia)
    fuente = copia["pestanas"]
    if any(any(conciliacion[n]["errores"].values()) for n in (*TABLAS, *TABLAS_DOCUMENTOS, *ARCHIVOS) if n in conciliacion):
        raise ValueError("Las pestañas operativas tienen identidades o relaciones sin conciliar.")
    if len(fuente["Escuelas"]) < 2:
        raise ValueError("La proyección requiere un catálogo de escuelas explícito.")
    plan, exclusiones = preparar_tablas({n: fuente[n] for n in TABLAS if n in fuente})
    if exclusiones:
        raise ValueError("La proyección no admite exclusiones automáticas de registros.")
    for tabla, campo in (("Escuelas", "nombre_escuela"), ("Alumnos", "nombre_completo")):
        if any(not fila.get(campo, "").strip() for fila in plan[tabla]):
            raise ValueError(f"{tabla}: falta un nombre obligatorio. Conserva la fila en preparación.")
    alumnos_origen = {r["id"] for r in plan["Alumnos"]}
    curps = [r["curp"].strip().upper() for r in plan["Alumnos"] if r.get("curp", "").strip()]
    if len(curps) != len(set(curps)):
        raise ValueError("Hay CURP repetidas en el origen.")
    for nombre in TABLAS[2:-1]:
        if any(r.get("id_alumno") not in alumnos_origen for r in plan.get(nombre, [])):
            raise ValueError(f"{nombre}: se requiere un alumno de origen conciliado.")
    proyectadas = TABLAS_DOCUMENTOS | TABLAS_B01 | (ARCHIVOS if "Documentos_Expediente" in fuente else set())
    resultado = {"aplicado": aplicar, "solo_archivo": sorted(set(fuente) - set(plan) - proyectadas), "tablas": {}}
    with engine.begin() as db:
        verificar_base_local(db, "proyeccion")
        db.execute(text("SET LOCAL search_path TO public"))
        # Los nombres proceden del catálogo fijo, nunca del archivo.
        if aplicar:
            nombres = {DESTINOS[n][0].__tablename__ for n in TABLAS if n in plan}
            if TABLAS_DOCUMENTOS & fuente.keys():
                nombres.update(("epp_documentos", "informes_educativos_spa", "spa_cambios", "usuarios",
                                "planeaciones", "spa_planeacion_alumnos", "spa_planeacion_grupos", "registro_visitas"))
            if ARCHIVOS & fuente.keys():
                nombres.update(("spa_adjunto_expediente", "spa_cambios"))
            if TABLAS_B01 & fuente.keys():
                nombres.update(("spa_apoyo_alumno", "spa_expedientes_historicos", "spa_relaciones_historicas", "usuarios"))
            nombres = ", ".join(sorted(nombres))
            db.execute(text(f"LOCK TABLE {nombres} IN SHARE ROW EXCLUSIVE MODE"))
        alumnos_en_conflicto = set()
        escuelas_en_conflicto = set()
        for nombre in (n for n in TABLAS if n in plan):
            filas = plan[nombre]
            tabla = DESTINOS[nombre][0].__table__
            existentes = {r["id"]: r for r in db.execute(select(tabla)).mappings()}
            curps_db = {str(r["curp"] or "").strip().upper(): aid for aid, r in existentes.items()
                        if nombre == "Alumnos" and r["curp"]}
            cuenta = {"nuevas": 0, "iguales": 0, "conflictos_preservados": 0}
            for fila in filas:
                actual = existentes.get(fila["id"])
                curp = fila.get("curp", "").strip().upper()
                if (fila.get("id_alumno") in alumnos_en_conflicto
                        or fila.get("id_escuela") in escuelas_en_conflicto
                        or nombre == "Alumnos" and curp and curps_db.get(curp, fila["id"]) != fila["id"]):
                    cuenta["conflictos_preservados"] += 1
                    if nombre == "Alumnos":
                        alumnos_en_conflicto.add(fila["id"])
                elif actual is None:
                    cuenta["nuevas"] += 1
                    if aplicar:
                        db.execute(tabla.insert().values(**fila))
                elif all(str(actual[k] or "") == v for k, v in fila.items()):
                    cuenta["iguales"] += 1
                else:
                    cuenta["conflictos_preservados"] += 1
                    if nombre == "Alumnos":
                        alumnos_en_conflicto.add(fila["id"])
                    if nombre == "Escuelas":
                        escuelas_en_conflicto.add(fila["id"])
            resultado["tablas"][nombre] = cuenta
        alumnos_conciliados = {r["id"]: r for r in plan["Alumnos"] if r["id"] not in alumnos_en_conflicto}
        resultado["tablas"].update(proyectar_documentos(db, fuente, alumnos_conciliados, aplicar=aplicar))
        if "Asignaciones_Apoyo" in fuente:
            resultado["tablas"]["Asignaciones_Apoyo"] = proyectar_asignaciones(db, fuente, alumnos_conciliados, aplicar)
        resultado["tablas"].update(proyectar_expedientes(db, fuente, alumnos_conciliados, aplicar))
    return resultado


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("archivo", type=Path)
    parser.add_argument("--aplicar", action="store_true")
    args = parser.parse_args()
    if args.archivo.stat().st_size > MAX_BYTES:
        parser.error("La copia supera el límite.")
    url = make_url(os.getenv("USAER_PROYECCION_TEST_URL") or "sqlite://")
    try:
        verificar_destino_local(url, "proyeccion")
    except ValueError as exc:
        parser.error(str(exc))
    os.environ.update(DATABASE_URL=url.render_as_string(hide_password=False),
                      USAER_SPA_MODE="postgres-synthetic", USAER_SPA_ROLE="owner")
    from data.database import get_engine
    from piloto_spa.backend.main import verificar_base_piloto

    verificar_base_piloto()
    copia = json.loads(args.archivo.read_text(encoding="utf-8-sig"))
    if "manifiesto" in copia:
        from tools.copia_controlada import verificar_paquete

        verificar_paquete(copia, clase="ensayo")
        copia = copia["copia"]
    print(json.dumps(proyectar(get_engine(initialize_schema=False), copia, aplicar=args.aplicar),
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

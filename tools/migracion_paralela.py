"""Captura incremental y reversible de copias sintéticas de Sheets en PostgreSQL."""

from argparse import ArgumentParser
from collections import Counter
from getpass import getpass
import json
import os
from pathlib import Path
import re
import sys

from sqlalchemy import text
from sqlalchemy.engine import make_url
import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from data.sincronizacion_pg import huella
from utils.text import normalizar_texto

MARCA = "USAER_SPA_COPIA_SINTETICA_V1"
MAX_BYTES = 32 * 1024 * 1024
PESTANAS = {
    "Escuelas": ("ID_Escuela",), "Alumnos": ("ID_Alumno",),
    "Expedientes": ("ID_Expediente",), "EPP_Versiones": ("Alumno", "Ciclo", "Parte", "Revision"),
    "NEE": ("ID_NEE",), "Anexo3_Deteccion": ("ID_Anexo3",),
    "Anexo4_Sugerencias": ("ID_Anexo4",), "Anexo5_Eventos": ("ID_Evento",),
    "EventosVersiones": ("ID_Evento", "Revision"), "Anexo7_Derivacion": ("ID_Anexo7",),
    "Planeaciones_Versiones": ("Documento", "Revision", "Parte"),
    "Informes": ("ID_Informe",), "Registro_Visitas": ("ID_Visita",),
    "Actas": ("ID_Acta",), "Relaciones_Documentos": ("ID_Relacion",),
    "Documentos_Expediente": ("ID_Documento",), "Archivos_Expediente": ("ID_Documento", "Indice"),
    "Tramites_Expedientes": ("ID_Tramite", "Revision"),
    "Juntas_Academicas_Versiones": ("Documento", "Revision"),
    "Movimientos_Alumnos": ("ID_Movimiento", "Estado"),
}
RAIZ_API = "https://sheets.googleapis.com/v4/spreadsheets/"


def leer_sheets(identificador, token, *, cliente=None):
    """GET exclusivamente, sin utilizar cuentas o configuración del repositorio."""
    if not re.fullmatch(r"[A-Za-z0-9_-]{20,160}", identificador) or not token:
        raise ValueError("Se requieren el ID explícito de la copia sintética y un token de solo lectura.")

    def obtener(http, sufijo="", **params):
        with http.stream("GET", RAIZ_API + identificador + sufijo, params=params,
                         headers={"Authorization": f"Bearer {token}"}) as respuesta:
            if respuesta.status_code != 200:
                raise ValueError(f"Sheets rechazó la lectura ({respuesta.status_code}).")
            datos = bytearray()
            for fragmento in respuesta.iter_bytes():
                datos.extend(fragmento)
                if len(datos) > MAX_BYTES:
                    raise ValueError("La copia supera el límite de 32 MiB.")
            return json.loads(datos)

    from contextlib import nullcontext
    with (nullcontext(cliente) if cliente is not None else
          httpx.Client(timeout=30, trust_env=False, follow_redirects=False)) as http:
        info = obtener(http, fields="properties(title),sheets(properties(title)")
        if info.get("properties", {}).get("title") != MARCA:
            raise ValueError("La copia no tiene el título de seguridad requerido.")
        nombres = {hoja["properties"]["title"] for hoja in info["sheets"]}
        elegidas = [nombre for nombre in PESTANAS if nombre in nombres]
        if not {"Escuelas", "Alumnos"} <= set(elegidas):
            raise ValueError("La copia debe contener Escuelas y Alumnos.")
        respuesta = obtener(http, "/values:batchGet", ranges=[f"'{nombre}'" for nombre in elegidas],
                            majorDimension="ROWS", valueRenderOption="FORMATTED_VALUE")
        rangos = respuesta.get("valueRanges", [])
        if respuesta.get("spreadsheetId") != identificador or len(rangos) != len(elegidas):
            raise ValueError("La respuesta no coincide con las pestañas solicitadas.")
        for nombre, rango in zip(elegidas, rangos):
            if rango.get("range", "").split("!", 1)[0].strip("'") != nombre:
                raise ValueError("Sheets devolvió una pestaña distinta de la solicitada.")
        return {"marca": MARCA, "origen": "sheets-" + huella(identificador)[:24],
                "pestanas": {n: [[c if isinstance(c, str) else json.dumps(c) for c in fila]
                                 for fila in r.get("values", [])] for n, r in zip(elegidas, rangos)}}


def preparar(copia):
    if copia.get("marca") != MARCA or not re.fullmatch(r"[a-z0-9_-]{1,80}", copia.get("origen", "")):
        raise ValueError("Se requiere una copia sintética marcada y un origen explícito.")
    hojas = copia.get("pestanas")
    if not isinstance(hojas, dict) or set(hojas) - PESTANAS.keys() or not {"Escuelas", "Alumnos"} <= hojas.keys():
        raise ValueError("Hay pestañas no admitidas o falta el padrón de escuelas y alumnos.")
    filas, reporte, registros = {}, {}, {}
    for nombre, tabla in sorted(hojas.items()):
        if (not isinstance(tabla, list) or not tabla or len(tabla) > 50001
                or any(not isinstance(r, list) or len(r) > 150 or any(not isinstance(c, str) for c in r) for r in tabla)):
            raise ValueError(f"{nombre}: formato o tamaño de tabla inválido.")
        encabezados = tabla[0]
        if any(re.search(r"PASSWORD|CONTRASENA|TOKEN|SECRET|CREDENCIAL|CLAVE PRIVADA", normalizar_texto(c))
               for c in encabezados):
            raise ValueError(f"{nombre}: encabezado de credenciales no admitido.")
        if len(set(encabezados)) != len(encabezados) or not set(PESTANAS[nombre]) <= set(encabezados):
            raise ValueError(f"{nombre}: encabezados duplicados o identidad incompleta.")
        identidades, errores = Counter(), Counter()
        registros[nombre] = []
        for fila in tabla[1:]:
            if not any(c.strip() for c in fila):
                continue
            if len(fila) > len(encabezados):
                raise ValueError(f"{nombre}: celdas fuera de los encabezados.")
            row = dict(zip(encabezados, fila + [""] * (len(encabezados) - len(fila))))
            clave = tuple(row[k] for k in PESTANAS[nombre])
            if not all(c.strip() for c in clave):
                errores["sin_identidad"] += 1
            else:
                identidades[clave] += 1
            registros[nombre].append(row)
        errores["identidad_repetida"] = sum(n - 1 for n in identidades.values())
        filas[nombre] = [(huella([nombre, encabezados, fila]), fila) for fila in tabla]
        reporte[nombre] = {"filas": len(registros[nombre]), "sha256": huella(tabla), "errores": dict(errores)}
    escuelas = {r["ID_Escuela"] for r in registros["Escuelas"] if r["ID_Escuela"]}
    alumnos = {r["ID_Alumno"] for r in registros["Alumnos"] if r["ID_Alumno"]}
    for nombre, rows in registros.items():
        errores = reporte[nombre]["errores"]
        if nombre == "Alumnos":
            errores["escuela_no_encontrada"] = sum(r.get("ID_Escuela") not in escuelas for r in rows)
        elif nombre not in {"Escuelas", "Planeaciones_Versiones", "Documentos_Expediente"}:
            errores["alumno_no_encontrado"] = sum(
                bool(aid := r.get("ID_Alumno") or r.get("Alumno")) and aid not in alumnos for r in rows)
        elif nombre in {"Planeaciones_Versiones", "Documentos_Expediente"}:
            for row in rows:
                try:
                    ids = json.loads(row.get("Alumnos_JSON") or row.get("ID_Alumnos_JSON") or "[]")
                    if not isinstance(ids, list) or any(not isinstance(aid, str) or aid not in alumnos for aid in ids):
                        raise ValueError
                except ValueError:
                    errores["alumnos_documento_no_conciliados"] = errores.get("alumnos_documento_no_conciliados", 0) + 1
    documentos = {r["ID_Documento"] for r in registros.get("Documentos_Expediente", [])}
    if "Archivos_Expediente" in registros:
        reporte["Archivos_Expediente"]["errores"]["documento_no_encontrado"] = sum(
            r["ID_Documento"] not in documentos for r in registros["Archivos_Expediente"])
    if "Relaciones_Documentos" in registros:
        conocidas = {(n, row[claves[0]]) for n, claves in PESTANAS.items()
                     for row in registros.get(n, []) if row[claves[0]]}
        reporte["Relaciones_Documentos"]["errores"]["extremos_no_conciliados"] = sum(
            (row.get("Origen_Tipo"), row.get("Origen_ID")) not in conocidas
            or (row.get("Destino_Tipo"), row.get("Destino_ID")) not in conocidas
            for row in registros["Relaciones_Documentos"])
    return filas, reporte


def verificar_destino_local(url, perfil):
    if (url.get_backend_name() != "postgresql" or url.host not in {"127.0.0.1", "::1"}
            or url.query or not re.fullmatch(rf"usaer_spa_test_{perfil}_[a-z0-9_]+", url.database or "")
            or url.username != url.database.replace("usaer_spa_test_", "spa_fixture_", 1)):
        raise ValueError("Se requiere un PostgreSQL sintético local con base y rol independientes.")


def verificar_base_local(db, perfil):
    base, rol, marca, propietario, version, elevado = db.execute(text("""
        SELECT current_database(), current_user, shobj_description(oid, 'pg_database'),
               pg_get_userbyid(datdba), current_setting('server_version_num')::int,
               (SELECT rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls
                FROM pg_roles WHERE rolname=current_user)
        FROM pg_database WHERE datname=current_database()
    """)).one()
    if (not re.fullmatch(rf"usaer_spa_test_{perfil}_[a-z0-9_]+", base)
            or rol != base.replace("usaer_spa_test_", "spa_fixture_", 1)
            or propietario != rol or marca != "USAER SPA synthetic only"
            or elevado or not 170000 <= version < 180000):
        raise ValueError("La base no pertenece al perfil independiente de migración sintética.")


def _esquema(db):
    verificar_base_local(db, "migracion")
    db.execute(text("SELECT pg_advisory_xact_lock(28150031)"))
    for ddl in (
        "CREATE SCHEMA IF NOT EXISTS copia_usaer",
        """CREATE TABLE IF NOT EXISTS copia_usaer.lote (
           id text PRIMARY KEY, origen text NOT NULL, creado timestamptz DEFAULT now(),
           reporte jsonb NOT NULL, revertido boolean NOT NULL DEFAULT false)""",
        "CREATE TABLE IF NOT EXISTS copia_usaer.fila (huella text PRIMARY KEY, celdas jsonb NOT NULL)",
        """CREATE TABLE IF NOT EXISTS copia_usaer.orden (
           lote text REFERENCES copia_usaer.lote, pestana text, posicion int,
           huella text NOT NULL REFERENCES copia_usaer.fila, PRIMARY KEY(lote, pestana, posicion))""",
    ):
        db.execute(text(ddl))


def guardar(engine, copia, *, aplicar=False):
    hojas, reporte = preparar(copia)
    origen = copia["origen"]
    lote = huella([origen, {n: v["sha256"] for n, v in reporte.items()}])
    resultado = {"lote": lote, "origen": origen, "pestanas": reporte, "aplicado": aplicar,
                 "pestanas_ausentes": sorted(PESTANAS.keys() - hojas.keys())}
    if not aplicar:
        return resultado
    verificar_destino_local(engine.url, "migracion")
    with engine.begin() as db:
        _esquema(db)
        previo = db.execute(text("SELECT revertido FROM copia_usaer.lote WHERE id=:id"), {"id": lote}).scalar()
        filas_antes = db.execute(text("SELECT count(*) FROM copia_usaer.fila")).scalar_one()
        if previo is True:
            raise ValueError("El lote se revirtió. Requiere una revisión antes de reutilizarse.")
        if previo is None:
            db.execute(text("INSERT INTO copia_usaer.lote(id,origen,reporte) VALUES(:id,:origen,CAST(:r AS jsonb))"),
                       {"id": lote, "origen": origen, "r": json.dumps(reporte)})
            for nombre, filas in hojas.items():
                db.execute(text("""INSERT INTO copia_usaer.fila(huella,celdas)
                                VALUES(:h,CAST(:c AS jsonb)) ON CONFLICT DO NOTHING"""),
                           [{"h": h, "c": json.dumps(c)} for h, c in filas])
                db.execute(text("INSERT INTO copia_usaer.orden VALUES(:id,:n,:p,:h)"),
                           [{"id": lote, "n": nombre, "p": i, "h": h} for i, (h, _) in enumerate(filas)])
        _reconstruir(db, lote, reporte)
        nuevas = db.execute(text("SELECT count(*) FROM copia_usaer.fila")).scalar_one() - filas_antes
        return {**resultado, "repetido": previo is False, "huellas_verificadas": len(hojas),
                "filas_nuevas_en_archivo": nuevas}


def _reconstruir(db, lote, reporte):
    hojas = {}
    for nombre, informe in reporte.items():
        hojas[nombre] = list(db.execute(text("""
            SELECT f.celdas FROM copia_usaer.orden o JOIN copia_usaer.fila f USING(huella)
            WHERE o.lote=:id AND o.pestana=:n ORDER BY o.posicion
        """), {"id": lote, "n": nombre}).scalars())
        if huella(hojas[nombre]) != informe["sha256"]:
            raise RuntimeError(f"El contenido reconstruido no coincide para {nombre}.")
    return hojas


def recuperar(engine, lote):
    """Reconstruye una copia exacta sin consultar Sheets ni tablas operativas."""
    if not re.fullmatch(r"[0-9a-f]{64}", lote):
        raise ValueError("Identificador de lote inválido.")
    verificar_destino_local(engine.url, "migracion")
    with engine.connect().execution_options(isolation_level="REPEATABLE READ") as db, db.begin():
        db.execute(text("SET TRANSACTION READ ONLY"))
        verificar_base_local(db, "migracion")
        if not db.scalar(text("SELECT to_regclass('copia_usaer.lote')")):
            raise ValueError("No hay lotes de migración archivados.")
        registro = db.execute(text("""
            SELECT origen, reporte FROM copia_usaer.lote WHERE id=:id AND NOT revertido
        """), {"id": lote}).one_or_none()
        if registro is None:
            raise ValueError("El lote no existe o está revertido.")
        origen, reporte = registro
        if huella([origen, {n: v["sha256"] for n, v in reporte.items()}]) != lote:
            raise RuntimeError("El manifiesto archivado no coincide con la identidad del lote.")
        return {"marca": MARCA, "origen": origen, "pestanas": _reconstruir(db, lote, reporte)}


def revertir(engine, lote):
    if not re.fullmatch(r"[0-9a-f]{64}", lote):
        raise ValueError("Identificador de lote inválido.")
    verificar_destino_local(engine.url, "migracion")
    with engine.begin() as db:
        _esquema(db)
        cambio = db.execute(text("UPDATE copia_usaer.lote SET revertido=true WHERE id=:id"), {"id": lote})
        if cambio.rowcount != 1:
            raise ValueError("Lote desconocido.")
        db.execute(text("DELETE FROM copia_usaer.orden WHERE lote=:id"), {"id": lote})
        db.execute(text("DELETE FROM copia_usaer.fila f WHERE NOT EXISTS (SELECT 1 FROM copia_usaer.orden o WHERE o.huella=f.huella)"))


def destino():
    url = make_url(os.getenv("USAER_MIGRACION_TEST_URL") or "sqlite://")
    verificar_destino_local(url, "migracion")
    os.environ.update(DATABASE_URL=url.render_as_string(hide_password=False),
                      USAER_SPA_MODE="postgres-synthetic", USAER_SPA_ROLE="owner")
    from piloto_spa.backend.main import verificar_base_piloto
    from data.database import get_engine

    verificar_base_piloto()
    return get_engine(initialize_schema=False)


def main():
    parser = ArgumentParser(description=__doc__)
    origen = parser.add_mutually_exclusive_group(required=True)
    origen.add_argument("--json", type=Path)
    origen.add_argument("--id-copia-sintetica")
    origen.add_argument("--revertir")
    origen.add_argument("--recuperar-lote")
    parser.add_argument("--aplicar", action="store_true")
    args = parser.parse_args()
    try:
        if args.recuperar_lote:
            if args.aplicar:
                raise ValueError("La recuperación es exclusivamente de lectura.")
            reporte = recuperar(destino(), args.recuperar_lote)
        elif args.revertir:
            if not args.aplicar:
                raise ValueError("La reversión requiere --aplicar.")
            revertir(destino(), args.revertir)
            reporte = {"revertido": args.revertir}
        else:
            if args.json:
                if args.json.stat().st_size > MAX_BYTES:
                    raise ValueError("La copia supera 32 MiB.")
                copia = json.loads(args.json.read_text(encoding="utf-8-sig"))
            else:
                copia = leer_sheets(args.id_copia_sintetica, getpass("Token OAuth de solo lectura: "))
            reporte = guardar(destino() if args.aplicar else None, copia, aplicar=args.aplicar)
        print(json.dumps(reporte, ensure_ascii=False, indent=2))
    except httpx.HTTPError:
        raise SystemExit("No se pudo completar la lectura HTTPS de la copia sintética.") from None
    except (ValueError, RuntimeError, OSError) as exc:
        raise SystemExit(str(exc)) from None


if __name__ == "__main__":
    main()

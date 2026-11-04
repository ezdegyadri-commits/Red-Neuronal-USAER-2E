"""Captura acotada y preparación incremental en una base privada independiente."""
import argparse
from collections import Counter
from contextlib import nullcontext
import csv
from datetime import datetime, timezone
from getpass import getpass
import json
import os
from pathlib import Path
import re

import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from data.sincronizacion_pg import huella
from tools.migracion_paralela import MARCA, MAX_BYTES, PESTANAS, RAIZ_API, preparar

ALCANCE = "https://www.googleapis.com/auth/spreadsheets.readonly"
MARCA_PRIVADA = "USAER COPIA PRIVADA AISLADA V1"
MARCA_REAL = "USAER_COPIA_REAL_CONTROLADA_V1"
RAIZ = Path(__file__).resolve().parents[1]
ORDEN = ("Escuelas", "Alumnos", "Expedientes", "Documentos_Expediente", "Archivos_Expediente",
         "Relaciones_Documentos", "EPP_Versiones", "NEE", "Anexo3_Deteccion", "Planeaciones_Versiones",
         "Informes", "Anexo4_Sugerencias", "Anexo5_Eventos")


def reloj(valor):
    instante = datetime.fromisoformat(valor)
    if instante.tzinfo is None:
        raise ValueError("Indica la zona horaria del momento de captura.")
    return instante.astimezone(timezone.utc)


def permiso_real(referencia):
    if not re.fullmatch(r"[A-Z0-9][A-Z0-9_-]{5,63}", referencia or ""):
        raise ValueError("Se requiere la referencia del acta de autorización institucional.")
    if os.getenv("USAER_COPIA_PRIVADA_AUTORIZADA") != "1":
        raise ValueError("El perfil privado para datos reales permanece desactivado.")


def alcance_copia(copia, escuela):
    _, reporte = preparar({**copia, "marca": MARCA})
    hojas = copia["pestanas"]
    registros = {n: [dict(zip(tabla[0], fila)) for fila in tabla[1:] if any(c.strip() for c in fila)]
                 for n, tabla in hojas.items()}
    alumnos = registros["Alumnos"]
    if (len(registros["Escuelas"]) != 1 or registros["Escuelas"][0].get("ID_Escuela") != escuela
            or any(r.get("ID_Escuela") != escuela for r in alumnos)):
        raise ValueError("La copia debe corresponder a una sola escuela.")
    ids = {r.get("ID_Alumno") for r in alumnos}
    if None in ids or "" in ids:
        raise ValueError("El padrón del ensayo contiene una identidad sin conciliar.")
    for filas in registros.values():
        for fila in filas:
            if (fila.get("ID_Escuela") or fila.get("Escuela_ID") or escuela) != escuela:
                raise ValueError("La copia contiene documentos de otra escuela.")
            if (aid := fila.get("ID_Alumno") or fila.get("Alumno")) and aid not in ids:
                raise ValueError("La copia contiene un alumno fuera del conjunto autorizado.")
            for campo in ("Alumnos_JSON", "ID_Alumnos_JSON"):
                if fila.get(campo):
                    referencias = json.loads(fila[campo])
                    if not isinstance(referencias, list) or any(not isinstance(a, str) or a not in ids for a in referencias):
                        raise ValueError("La copia contiene destinatarios fuera del conjunto autorizado.")
    return registros, reporte


def empaquetar(copia, escuela, capturada, *, clase):
    if clase not in {"ensayo", "real"}:
        raise ValueError("Clase de copia inválida.")
    if copia.get("marca") != (MARCA_REAL if clase == "real" else MARCA):
        raise ValueError("La marca de la copia no corresponde a su perfil.")
    registros, reporte = alcance_copia(copia, escuela)
    manifiesto = {"clase": clase, "origen": copia["origen"], "escuela": escuela,
                  "capturada": reloj(capturada).isoformat(), "pestanas": reporte,
                  "identidades": {n: [huella([n, [r.get(k, "") for k in PESTANAS[n]]]) for r in filas]
                                  for n, filas in registros.items()}}
    return {"manifiesto": manifiesto, "lote": huella(manifiesto), "copia": copia}


def leer_lote_sheets(cliente, libro, rangos, encabezados):
    """Una llamada GET acotada. La credencial OAuth se configura fuera del cliente."""
    if not re.fullmatch(r"[A-Za-z0-9_-]{20,160}", libro) or not 1 <= len(rangos) <= 25:
        raise ValueError("Identificador o cantidad de rangos fuera del límite.")
    for nombre, tramo in rangos.items():
        m = re.fullmatch(r"A([1-9][0-9]{0,4}):([A-Z]{1,2})([1-9][0-9]{0,4})", tramo)
        if nombre not in PESTANAS or not m or not 0 <= int(m[3]) - int(m[1]) < 2000:
            raise ValueError("Solo se admiten pestañas conocidas y páginas de hasta 2000 filas.")
    with cliente.stream("GET", RAIZ_API + libro + "/values:batchGet",
                        params={"ranges": [f"'{n}'!{r}" for n, r in rangos.items()],
                                "majorDimension": "ROWS", "valueRenderOption": "FORMATTED_VALUE"},
                        headers=encabezados) as respuesta:
        if respuesta.status_code != 200:
            raise ValueError(f"Sheets rechazó la lectura ({respuesta.status_code}).")
        datos = bytearray()
        for fragmento in respuesta.iter_bytes():
            datos.extend(fragmento)
            if len(datos) > MAX_BYTES:
                raise ValueError("La respuesta supera el límite de copia.")
    carga = json.loads(datos)
    devueltos = carga.get("valueRanges", [])
    if carga.get("spreadsheetId") != libro or len(devueltos) != len(rangos):
        raise ValueError("La respuesta no coincide con el libro autorizado.")
    hojas = {}
    for nombre, bloque in zip(rangos, devueltos):
        pestaña, _, tramo = bloque.get("range", "").partition("!")
        if pestaña.strip("'") != nombre or tramo != rangos[nombre]:
            raise ValueError("Sheets devolvió una pestaña o rango distinto del solicitado.")
        hojas[nombre] = bloque.get("values", [])
    return hojas


def leer_captura_paginada(cliente, libro, pestañas, encabezados, *, tamano=250):
    if not 1 <= tamano <= 500 or not {"Escuelas", "Alumnos"} <= pestañas.keys():
        raise ValueError("Indica la extensión autorizada de Escuelas y Alumnos.")
    hojas, bytes_total = {}, 0
    for nombre, alcance in pestañas.items():
        final, columna = alcance["ultima_fila"], alcance["ultima_columna"]
        if (nombre not in PESTANAS or type(final) is not int or not 1 <= final <= 50001
                or not re.fullmatch(r"[A-Z]{1,2}", columna)):
            raise ValueError("La extensión declarada de una pestaña es inválida.")
        filas = []
        for inicio in range(1, final + 1, tamano):
            fin = min(final, inicio + tamano - 1)
            pagina = leer_lote_sheets(cliente, libro, {nombre: f"A{inicio}:{columna}{fin}"}, encabezados)[nombre]
            n = fin - inicio + 1
            if not isinstance(pagina, list) or len(pagina) > n or (inicio == 1 and not pagina):
                raise ValueError("Página truncada o fuera del rango declarado.")
            filas.extend(pagina)
            filas.extend([] for _ in range(n - len(pagina)))
            bytes_total += len(json.dumps(pagina, ensure_ascii=False).encode("utf-8")) + 4 * (n - len(pagina))
            if bytes_total > MAX_BYTES:
                raise ValueError("La captura excede el tamaño seguro. Usa exportaciones manuales separadas y conciliadas.")
        hojas[nombre] = filas
    return hojas


def verificar_destino(url, clase):
    prefijo = "usaer_copia_privada_" if clase == "real" else "usaer_copia_ensayo_"
    if (url.drivername not in {"postgresql+psycopg", "postgresql+psycopg2"}
            or url.host not in {"127.0.0.1", "::1"} or not url.port or url.query
            or not re.fullmatch(prefijo + "[a-z0-9_]+", url.database or "")
            or url.username != url.database.replace("usaer_copia_", "copia_", 1)):
        raise ValueError("El destino debe ser una base dedicada de loopback con su rol exclusivo.")


def verificar_paquete(paquete, *, clase=None):
    m = paquete["manifiesto"]
    comprobado = empaquetar(paquete["copia"], m["escuela"], m["capturada"], clase=m["clase"])
    if paquete != comprobado or (clase and m["clase"] != clase):
        raise ValueError("El manifiesto o los datos no coinciden con el lote.")
    return m


def preparar_bd(engine, paquete, *, aplicar=False, referencia=None, _conexion=None):
    m = verificar_paquete(paquete)
    clase = m["clase"]
    if clase == "real":
        permiso_real(referencia)
    verificar_destino(engine.url, clase)
    registros, reporte = alcance_copia(paquete["copia"], m["escuela"])
    con_datos = []
    for nombre in (*ORDEN, *(n for n in PESTANAS if n not in ORDEN)):
        if nombre not in registros:
            continue
        filas = registros[nombre]
        claves = m["identidades"][nombre]
        repetidas = Counter(claves)
        error_tabla = any(reporte[nombre]["errores"].values())
        for clave, fila in zip(claves, filas):
            campo_nombre = {"Escuelas": "Nombre_Escuela", "Alumnos": "Nombre_Completo"}.get(nombre)
            if repetidas[clave] > 1:
                motivo = "identidad_repetida"
            elif error_tabla:
                motivo = "relacion_o_identidad"
            elif campo_nombre and not fila.get(campo_nombre, "").strip():
                motivo = "nombre_requerido_para_proyeccion"
            else:
                motivo = ""
            con_datos.append((nombre, clave, huella(fila), fila, motivo))
    if _conexion is not None and (not aplicar or _conexion.engine is not engine):
        raise ValueError("La conexión de lote no corresponde al destino de escritura.")
    with (engine.begin() if _conexion is None else nullcontext(_conexion)) as db:
        if not aplicar:
            db.execute(text("SET TRANSACTION READ ONLY"))
        marca, permitido = db.execute(text("""
            SELECT shobj_description(d.oid, 'pg_database'),
                   d.datdba=r.oid AND NOT (r.rolsuper OR r.rolcreatedb OR r.rolcreaterole
                     OR r.rolreplication OR r.rolbypassrls)
                   AND current_setting('server_version_num')::int BETWEEN 170000 AND 179999
            FROM pg_database d CROSS JOIN pg_roles r
            WHERE d.datname=current_database() AND r.rolname=current_user
              AND d.datname=:base AND r.rolname=:rol
        """), {"base": engine.url.database, "rol": engine.url.username}).one_or_none() or (None, False)
        esperada = MARCA_PRIVADA if clase == "real" else "USAER COPIA ENSAYO V1"
        if marca != esperada or not permitido:
            raise ValueError("La base no está marcada o el rol no cumple el perfil aislado.")
        if aplicar:
            db.execute(text("SELECT pg_advisory_xact_lock(28150038)"))
            db.execute(text("CREATE SCHEMA IF NOT EXISTS copia_controlada"))
            db.execute(text("REVOKE ALL ON SCHEMA copia_controlada FROM PUBLIC"))
            db.execute(text("""CREATE TABLE IF NOT EXISTS copia_controlada.lote (
                id text PRIMARY KEY, origen text NOT NULL, escuela text NOT NULL, capturada timestamptz NOT NULL,
                manifiesto jsonb NOT NULL, autorizacion text)"""))
            db.execute(text("""CREATE TABLE IF NOT EXISTS copia_controlada.registro (
                lote text REFERENCES copia_controlada.lote, posicion integer, pestana text NOT NULL,
                clave text NOT NULL, huella text NOT NULL, estado text NOT NULL, motivo text NOT NULL,
                datos jsonb NOT NULL, PRIMARY KEY(lote,posicion))"""))
            db.execute(text("""CREATE INDEX IF NOT EXISTS ix_copia_registro
                ON copia_controlada.registro (pestana, clave, lote)"""))
        existe = db.scalar(text("SELECT to_regclass('copia_controlada.lote')"))
        params = {"id": paquete["lote"], "origen": m["origen"], "escuela": m["escuela"]}
        if existe and db.scalar(text("SELECT 1 FROM copia_controlada.lote WHERE id=:id"), params):
            estados = dict(db.execute(text("""SELECT estado, count(*) FROM copia_controlada.registro
                WHERE lote=:id GROUP BY estado"""), params).all())
            return {"lote": params["id"], "repetido": True, "capturada": m["capturada"], "estados": estados}
        ultima = db.scalar(text("""SELECT max(capturada) FROM copia_controlada.lote
            WHERE origen=:origen AND escuela=:escuela"""), params) if existe else None
        if ultima and reloj(m["capturada"]) <= ultima:
            raise ValueError("La captura debe ser posterior al último lote del mismo origen y escuela.")
        anteriores = {}
        if existe:
            anteriores = {(n, k): h for n, k, h in db.execute(text("""
                SELECT DISTINCT ON (r.pestana, r.clave) r.pestana, r.clave, r.huella
                FROM copia_controlada.registro r JOIN copia_controlada.lote l ON l.id=r.lote
                WHERE l.origen=:origen AND l.escuela=:escuela AND r.estado <> 'cuarentena'
                ORDER BY r.pestana,r.clave,l.capturada DESC
            """), params)}
        totales = Counter()
        pendientes = []
        presentes = {(n, k) for n, k, *_ in con_datos}
        for i, (n, k, h, fila, motivo) in enumerate(con_datos):
            anterior = anteriores.get((n, k))
            estado = "cuarentena" if motivo else "nuevo" if anterior is None else "igual" if anterior == h else "modificado"
            totales[estado] += 1
            pendientes.append(dict(id=params["id"], posicion=i, pestana=n, clave=k, huella=h,
                                   estado=estado, motivo=motivo, datos=json.dumps(fila, ensure_ascii=False)))
        if aplicar:
            db.execute(text("""INSERT INTO copia_controlada.lote VALUES
                (:id,:origen,:escuela,:capturada,CAST(:manifiesto AS jsonb),:autorizacion)"""),
                       {**params, "capturada": reloj(m["capturada"]), "manifiesto": json.dumps(m),
                        "autorizacion": referencia})
            db.execute(text("""INSERT INTO copia_controlada.registro VALUES
                (:id,:posicion,:pestana,:clave,:huella,:estado,:motivo,CAST(:datos AS jsonb))"""), pendientes)
    return {"lote": params["id"], "aplicado": aplicar,
            "ultima_copia_anterior": ultima.astimezone(timezone.utc).isoformat() if ultima else None,
            "capturada": m["capturada"], "estados": dict(totales),
            "pendientes_de_revision_en_lote": sum(totales[e] for e in ("nuevo", "modificado", "cuarentena")),
            "ausentes_en_pestanas_presentes": sum(n in registros for n, k in anteriores.keys() - presentes)}


def archivo_privado(path):
    path = path.expanduser().resolve()
    if path.is_relative_to(RAIZ):
        raise ValueError("Guarda las copias y credenciales fuera del repositorio.")
    return path


def leer_json(path):
    path = archivo_privado(path)
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("El archivo excede 32 MiB.")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def leer_csvs(path, origen, *, real):
    carpeta = archivo_privado(path)
    hojas, peso = {}, 0
    for archivo in sorted(carpeta.iterdir()):
        if archivo.suffix.lower() != ".csv":
            continue
        if archivo.is_symlink() or archivo.stem not in PESTANAS or archivo.stem in hojas:
            raise ValueError("Se encontraron CSV no admitidos o repetidos.")
        peso += archivo.stat().st_size
        if peso > MAX_BYTES:
            raise ValueError("Los CSV exceden 32 MiB.")
        with archivo.open(encoding="utf-8-sig", newline="") as entrada:
            hojas[archivo.stem] = list(csv.reader(entrada, strict=True))
    return {"marca": MARCA_REAL if real else MARCA, "origen": origen, "pestanas": hojas}


def escribir(path, contenido):
    archivo = archivo_privado(path)
    datos = json.dumps(contenido, ensure_ascii=False).encode("utf-8")
    if len(datos) > MAX_BYTES:
        raise ValueError("El paquete excede 32 MiB.")
    with os.fdopen(os.open(archivo, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as salida:
        salida.write(datos)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    comandos = parser.add_subparsers(dest="comando", required=True)
    for nombre in ("empaquetar", "exportar-copia"):
        cmd = comandos.add_parser(nombre)
        cmd.add_argument("entrada", type=Path)
        cmd.add_argument("salida", type=Path)
        cmd.add_argument("--escuela", required=True)
        cmd.add_argument("--capturada", required=True)
        cmd.add_argument("--referencia")
    comandos.choices["empaquetar"].add_argument("--real", action="store_true")
    comandos.choices["empaquetar"].add_argument("--origen", help="Alias estable requerido al usar una carpeta de CSV.")
    comandos.choices["exportar-copia"].add_argument("--credencial", required=True, type=Path)
    cargar = comandos.add_parser("preparar")
    cargar.add_argument("entrada", type=Path)
    cargar.add_argument("--referencia")
    cargar.add_argument("--aplicar", action="store_true")
    cargar.add_argument("--real", action="store_true")
    args = parser.parse_args()
    try:
        real = args.comando == "exportar-copia" or args.real
        if real:
            permiso_real(args.referencia)
        if args.comando == "empaquetar" and args.entrada.is_dir():
            if not args.origen:
                raise ValueError("Indica el alias de origen de los CSV.")
            entrada = leer_csvs(args.entrada, args.origen, real=real)
        else:
            entrada = leer_json(args.entrada)
        if args.comando == "preparar":
            clase = entrada["manifiesto"]["clase"]
            if clase != ("real" if real else "ensayo"):
                raise ValueError("La orden debe indicar explícitamente el perfil del paquete.")
            url = make_url(getpass("URL del PostgreSQL privado: "))
            verificar_destino(url, clase)
            engine = create_engine(url, hide_parameters=True, connect_args={"connect_timeout": 5})
            try:
                print(json.dumps(preparar_bd(engine, entrada, aplicar=args.aplicar, referencia=args.referencia)))
            finally:
                engine.dispose()
            return
        if args.comando == "exportar-copia":
            from google.auth.transport.requests import Request
            from google.oauth2 import service_account
            from requests import Session

            if entrada.get("tipo") != "copia_filtrada_autorizada":
                raise ValueError("El exportador requiere una copia filtrada y autorizada.")
            datos_credencial = leer_json(args.credencial)
            if datos_credencial.get("token_uri") != "https://oauth2.googleapis.com/token":
                raise ValueError("Servidor de emisión OAuth no autorizado.")
            credencial = service_account.Credentials.from_service_account_info(datos_credencial, scopes=[ALCANCE])
            with Session() as sesion:
                sesion.trust_env = False
                credencial.refresh(Request(session=sesion))
            with httpx.Client(timeout=15, trust_env=False, follow_redirects=False) as cliente:
                hojas = leer_captura_paginada(cliente, entrada["libro"], entrada["pestanas"],
                                              {"Authorization": f"Bearer {credencial.token}"},
                                              tamano=entrada.get("filas_por_pagina", 250))
            entrada = {"marca": MARCA_REAL, "origen": entrada["origen"], "pestanas": hojas}
        paquete = empaquetar(entrada, args.escuela, args.capturada, clase="real" if real else "ensayo")
        escribir(args.salida, paquete)
        print(json.dumps({"lote": paquete["lote"], "capturada": paquete["manifiesto"]["capturada"]}))
    except Exception:
        raise SystemExit("Operación cancelada. Revisa el perfil, alcance, integridad y autorización en el entorno privado.") from None


if __name__ == "__main__":
    main()

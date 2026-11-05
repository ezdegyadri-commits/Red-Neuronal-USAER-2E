"""Perfil separado para la base operativa local cifrada de B01."""
from ctypes import create_unicode_buffer
import os
from pathlib import Path
import sys

from sqlalchemy import text

BASE = "usaer_operativa_privada_b01"
MARCA = "USAER B01 OPERATIVA LOCAL CIFRADA V1"
OWNER = "b01_oper_owner"
RUNTIME = "b01_oper_runtime"
MODO = "b01-private-local"
MODO_B02 = "b02-private-local"
MODO_UNIFICADO = "usaer-private-local"
PERFILES = {
    MODO: (BASE, MARCA, OWNER, RUNTIME),
    MODO_UNIFICADO: ("usaer_operativa_privada_unificada", "USAER OPERATIVA UNIFICADA LOCAL CIFRADA V1",
                    "usaer_unificada_owner", "usaer_unificada_runtime"),
    MODO_B02: ("usaer_operativa_privada_b02", "USAER B02 OPERATIVA LOCAL CIFRADA V1",
               "b02_oper_owner", "b02_oper_runtime"),
}


def perfil():
    datos = PERFILES.get(os.getenv("USAER_SPA_MODE"))
    if datos is None:
        raise RuntimeError("Perfil operativo privado no reconocido.")
    return datos


def volumen():
    if sys.platform != "win32":
        raise RuntimeError("B01 requiere su volumen VeraCrypt local.")
    from ctypes import windll

    destino = create_unicode_buffer(2048)
    if not windll.kernel32.QueryDosDeviceW("V:", destino, len(destino)) or destino.value != r"\Device\VeraCryptVolumeV":
        raise RuntimeError("VeraCrypt V: no está verificado.")
    if not Path("V:/B01/postgres/cluster17/PG_VERSION").is_file():
        raise RuntimeError("El clúster local de B01 no está disponible.")


def verificar_url(url, *, propietario=False):
    volumen()
    base, _, owner, runtime = perfil()
    rol = owner if propietario else runtime
    if (url.drivername != "postgresql+psycopg2"
            or (url.host, url.port, url.database, url.username) != ("127.0.0.1", 55481, base, rol)
            or not url.password or url.query):
        raise RuntimeError("Destino fuera del perfil operativo privado B01.")


def verificar_conexion(db, *, propietario=False):
    base, marca, owner, runtime = perfil()
    esperado = owner if propietario else runtime
    datos = db.execute(text("""
        SELECT current_database(), current_user, host(inet_server_addr()), inet_server_port(),
            current_setting('server_version_num')::int, shobj_description(d.oid, 'pg_database'),
            pg_get_userbyid(d.datdba),
            r.rolsuper OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication OR r.rolbypassrls,
            has_schema_privilege(current_user, 'public', 'CREATE')
        FROM pg_database d CROSS JOIN pg_roles r
        WHERE d.datname=current_database() AND r.rolname=current_user
    """)).one()
    if (tuple(datos[:4]) != (base, esperado, "127.0.0.1", 55481) or not 170000 <= datos[4] < 180000
            or tuple(datos[5:8]) != (marca, owner, False) or datos[8] != propietario):
        raise RuntimeError("La base o el rol no cumplen el perfil operativo privado B01.")

"""Arranque y migración explícita del piloto sintético de Uppcoder."""
from ipaddress import ip_network
import json
import os
from pathlib import Path
import re
import sys

from sqlalchemy import inspect, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError

HOST_DB = "zja3x8j3-postgresql-17"
BASE_DB = "usaer_2e_2_0"
USUARIO_DB = "ezdegyadri"
MARCA = "uppcoder-sintetico-v1"
TABLA_MARCA = "usaer_uppcoder_piloto"
CONFIG_SPARK = Path.home() / ".config" / "usaer-spark" / "config.json"


def destino_postgres():
    host = os.getenv("USAER_UPPCODER_DB_HOST", HOST_DB)
    base = os.getenv("USAER_UPPCODER_DB_NAME", BASE_DB)
    usuario = os.getenv("USAER_UPPCODER_DB_USER", USUARIO_DB)
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", host):
        raise RuntimeError("Indica el nombre interno de PostgreSQL, sin esquema ni puerto.")
    if not all(re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]{0,62}", valor) for valor in (base, usuario)):
        raise RuntimeError("La base y el usuario deben ser identificadores PostgreSQL simples.")
    return host, 5432, base, usuario


def password_conexion():
    host, puerto, base, usuario = destino_postgres()
    if clave := os.getenv("USAER_UPPCODER_DB_PASSWORD"):
        return clave
    if (os.getenv("POSTGRES_HOST"), os.getenv("POSTGRES_PORT", "5432"),
            os.getenv("POSTGRES_DB"), os.getenv("POSTGRES_USER")) == (host, str(puerto), base, usuario):
        if clave := os.getenv("POSTGRES_PASSWORD"):
            return clave
    if previa := os.getenv("DATABASE_URL"):
        try:
            url = make_url(previa)
        except (ArgumentError, ValueError):
            return None
        if (url.host, url.port or 5432, url.database, url.username) == (host, puerto, base, usuario):
            return url.password
    return None


def cargar_spark():
    if CONFIG_SPARK.is_symlink():
        raise RuntimeError("La configuración Spark no admite enlaces simbólicos.")
    if not CONFIG_SPARK.is_file() or CONFIG_SPARK.stat().st_mode & 0o077:
        raise RuntimeError("Falta la configuración Spark privada o sus permisos no son 0600.")
    datos = json.loads(CONFIG_SPARK.read_text(encoding="utf-8"))
    if not all(campo in datos for campo in ("db_host", "db_name", "db_user")):
        raise RuntimeError("Ejecuta activar_spark.py para registrar el destino PostgreSQL de esta pila.")
    configurar_spark(datos)


def configurar_spark(datos):
    os.environ.update(
        USAER_UPPCODER_DB_HOST=datos["db_host"],
        USAER_UPPCODER_DB_NAME=datos["db_name"],
        USAER_UPPCODER_DB_USER=datos["db_user"],
    )
    os.environ["USAER_UPPCODER_PUBLIC_HOST"] = datos["host"]
    os.environ["USAER_UPPCODER_SYNTHETIC"] = "1"
    os.environ["USAER_UPPCODER_SPARK"] = "1"
    if not password_conexion() and datos.get("password"):
        os.environ["USAER_UPPCODER_DB_PASSWORD"] = datos["password"]


def host_publico():
    host = os.environ.get("USAER_UPPCODER_PUBLIC_HOST", "")
    if len(host) > 253 or not re.fullmatch(
        r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", host,
    ):
        raise RuntimeError("Configura USAER_UPPCODER_PUBLIC_HOST con el host HTTPS exacto, sin esquema ni puerto.")
    return host


def configurar():
    host_publico()
    if os.getenv("USAER_UPPCODER_SYNTHETIC") != "1":
        raise RuntimeError("Este perfil requiere USAER_UPPCODER_SYNTHETIC=1 y una base exclusiva de pruebas.")
    password = password_conexion()
    if not password:
        raise RuntimeError("Configura el secreto USAER_UPPCODER_DB_PASSWORD.")
    driver = "postgresql+psycopg" if os.getenv("USAER_UPPCODER_SPARK") == "1" else "postgresql+psycopg2"
    host, puerto, base, usuario = destino_postgres()
    url = URL.create(driver, username=usuario, password=password, host=host, port=puerto, database=base)
    os.environ.update(USAER_SPA_MODE="uppcoder", USAER_SPA_ROLE="runtime",
                      DATABASE_URL=url.render_as_string(hide_password=False))


def verificar_url():
    url = make_url(os.environ.get("DATABASE_URL", "sqlite://"))
    if (os.getenv("USAER_UPPCODER_SYNTHETIC") != "1" or os.getenv("USAER_SPA_ROLE") != "runtime"
            or url.drivername not in {"postgresql+psycopg2", "postgresql+psycopg"}
            or (url.host, url.port, url.database, url.username) != destino_postgres()
            or not url.password or url.query):
        raise RuntimeError("Destino PostgreSQL fuera del perfil sintético autorizado de Uppcoder.")


def verificar_conexion(db):
    base, rol, esquema, version, privilegiado = db.execute(text("""
        SELECT current_database(), current_user, current_schema(), current_setting('server_version_num')::int,
               rolsuper OR rolreplication OR rolbypassrls OR rolcreaterole OR rolcreatedb
        FROM pg_roles WHERE rolname = current_user
    """)).one()
    _, _, base_esperada, rol_esperado = destino_postgres()
    if (base, rol, esquema) != (base_esperada, rol_esperado, "public") or not 170000 <= version < 180000 or privilegiado:
        raise RuntimeError("Uppcoder requiere PostgreSQL 17 y el rol configurado sin privilegios elevados.")


def verificar_instalacion(db):
    verificar_conexion(db)
    if not inspect(db).has_table(TABLA_MARCA, schema="public"):
        raise RuntimeError("Ejecuta primero la migración sintética de Uppcoder.")
    if db.execute(text("SELECT perfil FROM public.usaer_uppcoder_piloto WHERE id = 1")).scalar() != MARCA:
        raise RuntimeError("La base de Uppcoder carece de la marca de instalación sintética.")


def migrar():
    from data.database import Alumno, Base, Escuela, Usuario, get_engine
    from piloto_spa.backend.auth_service import hash_password
    from sqlalchemy.orm import Session

    verificar_url()
    with get_engine(initialize_schema=False).begin() as db:
        verificar_conexion(db)
        db.execute(text("SELECT pg_advisory_xact_lock(17002200)"))
        presentes = set(inspect(db).get_table_names(schema="public"))
        if TABLA_MARCA in presentes:
            verificar_instalacion(db)
            Base.metadata.create_all(db)
            return
        if presentes & Base.metadata.tables.keys():
            raise RuntimeError("Ya existen tablas USAER sin marca sintética. Usa una base nueva y dedicada.")
        clave = os.environ.get("USAER_UPPCODER_DIRECTOR_PASSWORD", "")
        if not 16 <= len(clave) <= 255 or clave != clave.strip():
            raise RuntimeError("Configura un secreto inicial aleatorio de 16 a 255 caracteres para Dirección.")
        Base.metadata.create_all(db)
        db.execute(text("CREATE TABLE public.usaer_uppcoder_piloto (id integer PRIMARY KEY, perfil text NOT NULL)"))
        db.execute(text("INSERT INTO public.usaer_uppcoder_piloto VALUES (1, :marca)"), {"marca": MARCA})
        with Session(bind=db) as sesion:
            sesion.add(Usuario(id="direccion-uppcoder", usuario="direccion.piloto", nombre="Dirección ficticia",
                               rol="DIRECTOR", escuelas_permitidas="TODAS", password=hash_password(clave)))
            for letra in ("a", "b"):
                escuela = f"esc-uppcoder-{letra}"
                nombre = f"Escuela ficticia {letra.upper()}"
                sesion.add(Escuela(id=escuela, nombre_escuela=nombre, nivel="Primaria"))
                sesion.add(Alumno(id=f"alu-uppcoder-{letra}", id_escuela=escuela, nombre_escuela=nombre,
                                  nombre_completo=f"Estudiante ficticio {letra.upper()}", nivel_educativo="Primaria",
                                  grado="3°", grupo="A", estatus="Activo", tipo_atencion="Individual"))
            sesion.flush()
            sesion.commit()


def proxies_confiables():
    redes = os.getenv("USAER_UPPCODER_PROXY_IPS", "127.0.0.1,::1").split(",")
    for red in redes:
        if ip_network(red, strict=False).prefixlen == 0:
            raise ValueError("Indica solo las IP o redes concretas del proxy de Uppcoder.")
    return ",".join(redes)


def main():
    if sys.argv[1:] not in (["migrar"], ["servir"]):
        raise SystemExit("Indica migrar o servir.")
    try:
        configurar()
        if sys.argv[1] == "migrar":
            migrar()
            print("Esquema sintético de Uppcoder listo.")
            return
        import uvicorn

        puerto = int(os.getenv("PORT", "8000"))
        if not 1 <= puerto <= 65535:
            raise ValueError("PORT debe ser un puerto TCP válido.")
        uvicorn.run("piloto_spa.backend.main:app", host="0.0.0.0", port=puerto,
                    proxy_headers=True, forwarded_allow_ips=proxies_confiables(), access_log=False)
    except (RuntimeError, ValueError) as exc:
        raise SystemExit(str(exc)) from None
    except Exception:
        raise SystemExit("Falló la operación de PostgreSQL. Revisa la red interna y los permisos de la cuenta.") from None


if __name__ == "__main__":
    main()

"""Arranque y migración explícita del piloto sintético de Uppcoder."""
from ipaddress import ip_network
import os
import re
import sys

from sqlalchemy import inspect, text
from sqlalchemy.engine import URL, make_url

HOST_DB = "gwhdki61-postgresql-17"
BASE_DB = "usaer_2e_2_0"
USUARIO_DB = "usaer_app"
MARCA = "uppcoder-sintetico-v1"
TABLA_MARCA = "usaer_uppcoder_piloto"


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
    password = os.environ.get("USAER_UPPCODER_DB_PASSWORD")
    if not password:
        raise RuntimeError("Configura el secreto USAER_UPPCODER_DB_PASSWORD.")
    url = URL.create("postgresql+psycopg2", username=USUARIO_DB, password=password,
                     host=HOST_DB, port=5432, database=BASE_DB)
    os.environ.update(USAER_SPA_MODE="uppcoder", USAER_SPA_ROLE="runtime",
                      DATABASE_URL=url.render_as_string(hide_password=False))


def verificar_url():
    url = make_url(os.environ.get("DATABASE_URL", "sqlite://"))
    if (os.getenv("USAER_UPPCODER_SYNTHETIC") != "1" or os.getenv("USAER_SPA_ROLE") != "runtime"
            or url.drivername != "postgresql+psycopg2" or url.host != HOST_DB or url.port != 5432
            or url.database != BASE_DB or url.username != USUARIO_DB or not url.password or url.query):
        raise RuntimeError("Destino PostgreSQL fuera del perfil sintético autorizado de Uppcoder.")


def verificar_conexion(db):
    base, rol, esquema, version, privilegiado = db.execute(text("""
        SELECT current_database(), current_user, current_schema(), current_setting('server_version_num')::int,
               rolsuper OR rolreplication OR rolbypassrls OR rolcreaterole OR rolcreatedb
        FROM pg_roles WHERE rolname = current_user
    """)).one()
    if (base, rol, esquema) != (BASE_DB, USUARIO_DB, "public") or not 170000 <= version < 180000 or privilegiado:
        raise RuntimeError("Uppcoder requiere PostgreSQL 17 y el rol usaer_app sin privilegios elevados.")


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

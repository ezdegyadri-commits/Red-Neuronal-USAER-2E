"""Prepara el piloto Spark y entrega main:app al supervisor existente."""
import argparse
import ast
from getpass import getpass
from importlib import metadata
import json
import os
from pathlib import Path
from secrets import token_urlsafe
import shutil
import subprocess
import sys
import tempfile

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
MIB = 1024**2


def atomico(destino, datos):
    with tempfile.NamedTemporaryFile(dir=destino.parent, delete=False) as archivo:
        temporal = Path(archivo.name)
        try:
            archivo.write(datos)
            archivo.close()
            temporal.chmod(0o600)
            os.replace(temporal, destino)
        finally:
            temporal.unlink(missing_ok=True)


def espacio(limite):
    libre = shutil.disk_usage(REPO).free // MIB
    print(f"Espacio disponible en el volumen de la aplicación: {libre} MiB.", flush=True)
    if libre < limite:
        raise RuntimeError(f"Se requieren al menos {limite} MiB libres. Revisa la cuota y los tamaños antes de continuar.")


def limpiar():
    casa = Path.home().resolve()
    for ruta in (casa / ".cache/pip", REPO / "piloto_spa/frontend/node_modules"):
        if not ruta.exists() or ruta.is_symlink() or ruta.resolve() != ruta:
            continue
        print(f"Limpiando archivos regenerables de {ruta}.", flush=True)
        shutil.rmtree(ruta)


def es_ejemplo(contenido):
    arbol = ast.parse(contenido)
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Return) and isinstance(nodo.value, ast.Dict):
            try:
                if ast.literal_eval(nodo.value) == {"Hello": "World"}:
                    return True
            except (TypeError, ValueError):
                pass
    return False


def instalar():
    from pip._vendor.packaging.requirements import Requirement

    faltan = []
    requisitos = REPO / "requirements-spark.txt"
    for linea in requisitos.read_text(encoding="utf-8").splitlines():
        if not linea.strip():
            continue
        requisito = Requirement(linea)
        try:
            version = metadata.version(requisito.name)
        except metadata.PackageNotFoundError:
            version = None
        if version is None or version not in requisito.specifier:
            faltan.append(requisito.name)
    espacio(400 if faltan else 64)
    if faltan:
        print("Dependencias faltantes o incompatibles: " + ", ".join(faltan), flush=True)
        subprocess.run([sys.executable, "-m", "pip", "install", "--no-cache-dir", "--only-binary=:all:",
                        "-r", str(requisitos)], check=True)
    espacio(64)
    controlador = subprocess.run([sys.executable, "-c", "import psycopg"],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if controlador.returncode:
        print("Falta una implementación libpq utilizable. Instalando solo el driver binario.", flush=True)
        subprocess.run([sys.executable, "-m", "pip", "install", "--no-cache-dir", "--only-binary=:all:",
                        "psycopg[binary]>=3.2,<4"], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True, help="Host HTTPS del stack, sin esquema ni puerto.")
    parser.add_argument("--db-host", default=os.getenv("USAER_UPPCODER_DB_HOST"), help="Nombre interno de PostgreSQL.")
    parser.add_argument("--db-name", default=os.getenv("USAER_UPPCODER_DB_NAME"), help="Base sintética dedicada.")
    parser.add_argument("--db-user", default=os.getenv("USAER_UPPCODER_DB_USER"), help="Rol sin privilegios elevados.")
    parser.add_argument("--limpiar-cache", action="store_true", help="Retira solo caché de pip y dependencias Node regenerables.")
    args = parser.parse_args()
    if sys.platform != "linux" or REPO != Path.home().resolve() / "app/usaer2e":
        raise RuntimeError("Ejecuta desde el clon ~/app/usaer2e del entorno Linux web-fastapi.")
    inicio = REPO.parent / "main.py"
    adaptador = (REPO / "deploy/main_spark.py").read_bytes()
    if inicio.is_symlink() or not inicio.is_file():
        raise RuntimeError("Falta el main.py esperado del supervisor o es un enlace.")
    anterior = inicio.read_bytes()
    if anterior != adaptador and not es_ejemplo(anterior):
        raise RuntimeError("main.py ya contiene otro servicio. Se conserva para revisión.")
    for nombre in ("index.html", "app.js", "app.css"):
        if not (REPO / "piloto_spa/frontend/dist" / nombre).is_file():
            raise RuntimeError("Faltan los assets React compilados del repositorio.")
    if args.limpiar_cache:
        limpiar()
    instalar()

    from deploy import uppcoder
    cfg = uppcoder.CONFIG_SPARK
    if cfg.parent.is_symlink() or cfg.parent.parent.is_symlink() or cfg.is_symlink():
        raise RuntimeError("La configuración privada no admite enlaces.")
    cfg.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    cfg.parent.chmod(0o700)
    destino = {
        "db_host": uppcoder.HOST_DB if args.db_host is None else args.db_host,
        "db_name": uppcoder.BASE_DB if args.db_name is None else args.db_name,
        "db_user": uppcoder.USUARIO_DB if args.db_user is None else args.db_user,
    }
    usuario = uppcoder.USUARIO_RUNTIME
    if destino["db_user"] == usuario:
        raise RuntimeError("Usa la cuenta del proveedor para migrar, separada del rol operativo.")
    datos = {"host": args.host, **destino}
    uppcoder.configurar_spark(datos)
    uppcoder.host_publico()
    if not uppcoder.password_conexion():
        guardada = json.loads(cfg.read_text()) if cfg.is_file() and not cfg.stat().st_mode & 0o077 else {}
        clave = guardada.get("password") if all(guardada.get(k) == v for k, v in destino.items()) else None
        clave = clave or getpass("Contraseña PostgreSQL del rol configurado: ")
        if not clave:
            raise RuntimeError("Falta la contraseña PostgreSQL.")
        datos["password"] = clave
    uppcoder.configurar_spark(datos)
    uppcoder.configurar()
    from data.database import get_engine
    from sqlalchemy import create_engine, inspect

    motor_migracion = get_engine(initialize_schema=False)
    with motor_migracion.connect() as db:
        uppcoder.verificar_conexion(db, migracion=True)
        nueva = not inspect(db).has_table(uppcoder.TABLA_MARCA, schema="public")
    if nueva and not os.getenv("USAER_UPPCODER_DIRECTOR_PASSWORD"):
        os.environ["USAER_UPPCODER_DIRECTOR_PASSWORD"] = getpass("Contraseña inicial de direccion.piloto (mínimo 16): ")
    try:
        uppcoder.migrar(cuenta_migracion=True)
    finally:
        os.environ.pop("USAER_UPPCODER_DIRECTOR_PASSWORD", None)
    clave_runtime = token_urlsafe(32)
    with motor_migracion.begin() as db:
        creado = uppcoder.preparar_runtime(db, usuario, clave_runtime)
    motor_migracion.dispose()
    datos = {"host": args.host, **destino, "db_user": usuario, "separado": True}
    if not creado:
        guardada = json.loads(cfg.read_text()) if cfg.is_file() and not cfg.stat().st_mode & 0o077 else {}
        campos = ("db_host", "db_name", "db_user")
        clave_runtime = guardada.get("password") if all(guardada.get(k) == datos[k] for k in campos) else None
        clave_runtime = clave_runtime or getpass(f"Contraseña PostgreSQL del rol operativo {usuario}: ")
    if not clave_runtime:
        raise RuntimeError(f"Falta la contraseña del rol operativo {usuario}.")
    datos["password"] = clave_runtime
    uppcoder.configurar_spark(datos)
    uppcoder.configurar()
    uppcoder.verificar_url()
    motor_runtime = create_engine(os.environ["DATABASE_URL"], hide_parameters=True,
                                 connect_args={"connect_timeout": 5, "options": "-c search_path=public"})
    try:
        with motor_runtime.connect() as db:
            uppcoder.verificar_instalacion(db)
    finally:
        motor_runtime.dispose()
    respaldo = cfg.parent / "main.original.py"
    if anterior != adaptador:
        if respaldo.is_symlink() or (respaldo.exists() and respaldo.read_bytes() != anterior):
            raise RuntimeError("Ya existe un respaldo de main.py. Revísalo antes de sustituir el arranque.")
        if not respaldo.exists():
            atomico(respaldo, anterior)
    atomico(cfg, json.dumps(datos).encode())
    if anterior != adaptador:
        atomico(inicio, adaptador)
    print("SPA entregada a main:app. Comprueba el reinicio en el supervisor de Uppcoder.", flush=True)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError, OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit(str(exc)) from None
    except Exception:
        raise SystemExit("Falló la preparación de Spark. Revisa permisos y conexión PostgreSQL. Se conserva el arranque anterior si no se activó.") from None

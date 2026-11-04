"""Prepara el piloto Spark y entrega main:app al supervisor existente."""
import argparse
import ast
from getpass import getpass
from importlib import metadata
import json
import os
from pathlib import Path
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
    os.environ["USAER_UPPCODER_PUBLIC_HOST"] = args.host
    uppcoder.host_publico()
    cfg = uppcoder.CONFIG_SPARK
    if cfg.parent.is_symlink() or cfg.parent.parent.is_symlink() or cfg.is_symlink():
        raise RuntimeError("La configuración privada no admite enlaces.")
    cfg.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    cfg.parent.chmod(0o700)
    datos = {"host": args.host}
    if not uppcoder.password_conexion():
        guardada = json.loads(cfg.read_text()) if cfg.is_file() and not cfg.stat().st_mode & 0o077 else {}
        clave = guardada.get("password") or getpass("Contraseña PostgreSQL de usaer_app: ")
        if not clave:
            raise RuntimeError("Falta la contraseña PostgreSQL.")
        datos["password"] = clave
    atomico(cfg, json.dumps(datos).encode())
    uppcoder.cargar_spark()
    uppcoder.configurar()
    from data.database import get_engine
    from sqlalchemy import inspect

    with get_engine(initialize_schema=False).connect() as db:
        uppcoder.verificar_conexion(db)
        nueva = not inspect(db).has_table(uppcoder.TABLA_MARCA, schema="public")
    if nueva and not os.getenv("USAER_UPPCODER_DIRECTOR_PASSWORD"):
        os.environ["USAER_UPPCODER_DIRECTOR_PASSWORD"] = getpass("Contraseña inicial de direccion.piloto (mínimo 16): ")
    try:
        uppcoder.migrar()
    finally:
        os.environ.pop("USAER_UPPCODER_DIRECTOR_PASSWORD", None)
    respaldo = cfg.parent / "main.original.py"
    if anterior != adaptador:
        if respaldo.exists() or respaldo.is_symlink():
            raise RuntimeError("Ya existe un respaldo de main.py. Revísalo antes de sustituir el arranque.")
        atomico(respaldo, anterior)
        atomico(inicio, adaptador)
    print("SPA entregada a main:app. Comprueba el reinicio en el supervisor de Uppcoder.", flush=True)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError, OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit(str(exc)) from None
    except Exception:
        raise SystemExit("Falló la preparación de Spark. Revisa permisos y conexión PostgreSQL. Se conserva el arranque anterior si no se activó.") from None

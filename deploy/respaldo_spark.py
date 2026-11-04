"""Respalda únicamente la base sintética de Spark, sin datos de sesión."""
import argparse
import os
from pathlib import Path
import subprocess

from sqlalchemy.engine import make_url

from deploy import uppcoder


def respaldar(url, destino, *, pg_dump="pg_dump"):
    env = {k: v for k, v in os.environ.items() if not k.startswith("PG")}
    env["PGPASSWORD"] = url.password
    comando = [pg_dump, "--host", url.host, "--port", str(url.port),
               "--username", url.username, "--dbname", url.database,
               "--no-password", "--format=custom", "--exclude-table-data=public.spa_sesiones",
               "--exclude-table-data=public.spa_intentos_acceso"]
    descriptor = os.open(destino, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as archivo:
            subprocess.run(comando, env=env, stdout=archivo, check=True)
    except (OSError, subprocess.SubprocessError):
        destino.unlink(missing_ok=True)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destino", type=Path, help="Archivo nuevo en un directorio privado fuera del clon.")
    args = parser.parse_args()
    destino = args.destino.expanduser().resolve()
    if destino.is_relative_to(Path(__file__).resolve().parents[1]):
        parser.error("Guarda el respaldo fuera del repositorio.")
    uppcoder.cargar_spark()
    uppcoder.configurar()
    uppcoder.verificar_url()
    from data.database import get_engine
    with get_engine(initialize_schema=False).connect() as db:
        uppcoder.verificar_instalacion(db)
    respaldar(make_url(os.environ["DATABASE_URL"]), destino)
    print(f"Respaldo sintético creado ({destino.stat().st_size} bytes).")


if __name__ == "__main__":
    main()

"""Crea SOLO la tabla sintética de informes de SPA, sin tocar producción.

Uso (desde raíz del repositorio):
    USAER_SPA_MODE=postgres-synthetic USAER_SPA_ROLE=owner DATABASE_URL=... \
        python tools/migrar_informes_spa.py

Requiere una base local marcada 'USAER SPA synthetic only'.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    if os.environ.get("USAER_SPA_MODE") != "postgres-synthetic" or os.environ.get("USAER_SPA_ROLE") != "owner":
        raise SystemExit("RECHAZADO: solo PostgreSQL sintético con rol propietario.")

    from piloto_spa.backend.main import verificar_base_piloto
    from data.database import Base, get_engine

    verificar_base_piloto()
    tabla = Base.metadata.tables["informes_educativos_spa"]
    engine = get_engine(initialize_schema=False)
    tabla.create(bind=engine, checkfirst=True)
    print("Tabla de informes SPA sintéticos disponible. Producción no modificada.")


if __name__ == "__main__":
    main()

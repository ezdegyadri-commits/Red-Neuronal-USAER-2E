"""Módulo main:app que carga el supervisor existente de Uppcoder."""
from pathlib import Path
import sys

raiz = Path(__file__).resolve().parent / "usaer2e"
sys.path.insert(0, str(raiz))

from deploy.uppcoder import cargar_spark, configurar

cargar_spark()
configurar()

from piloto_spa.backend.main import app

"""Script lanzador del Piloto SPA USAER 2E.

Configura las rutas y el directorio de trabajo automáticamente para evitar
ModuleNotFoundError sin importar desde dónde se ejecute la terminal.
"""
import os
import sys

# Fijar directorio raíz del proyecto
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
os.chdir(ROOT_DIR)

import uvicorn

if __name__ == "__main__":
    print("=" * 60)
    print("[USAER 02-E] - PILOTO SPA (React 18 + FastAPI)")
    print("=" * 60)
    print("Directorio:", ROOT_DIR)
    print("Servidor activo en: http://localhost:8000")
    print("Para detener el servidor presiona: Ctrl + C")
    print("=" * 60)
    uvicorn.run("piloto_spa.backend.main:app", host="127.0.0.1", port=8000, reload=False)

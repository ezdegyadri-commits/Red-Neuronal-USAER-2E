"""Script lanzador del Piloto SPA USAER 2E.

Configura las rutas y el directorio de trabajo automáticamente para evitar
ModuleNotFoundError sin importar desde dónde se ejecute la terminal.
"""
import os
import sys

import os
import sys
import threading
import time
import webbrowser

# Fijar directorio raíz del proyecto
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
os.chdir(ROOT_DIR)

import uvicorn

def abrir_navegador_auto():
    """Abre el navegador automáticamente una vez que el servidor esté listo."""
    time.sleep(1.2)
    try:
        webbrowser.open("http://localhost:8000")
    except Exception:
        pass

if __name__ == "__main__":
    print("=" * 60)
    print("[USAER 02-E] - PILOTO SPA (React 18 + FastAPI)")
    print("=" * 60)
    print("Directorio:", ROOT_DIR)
    print("Servidor activo en: http://localhost:8000")
    print("Dirección alternativa: http://127.0.0.1:8000")
    print("Para detener el servidor presiona: Ctrl + C")
    print("=" * 60)
    
    # Lanzar navegador automáticamente
    threading.Thread(target=abrir_navegador_auto, daemon=True).start()
    
    uvicorn.run("piloto_spa.backend.main:app", host="0.0.0.0", port=8000, reload=False)

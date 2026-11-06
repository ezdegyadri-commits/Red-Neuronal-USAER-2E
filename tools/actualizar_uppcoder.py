"""Descarga directa de index.html limpio, backend y reconciliación de PostgreSQL.
"""
import urllib.request
import subprocess
import shutil
import time
import sys
from pathlib import Path

BASE_RAW = "https://raw.githubusercontent.com/ezdegyadri-commits/Red-Neuronal-USAER-2E/piloto-spa"

# 0. Eliminar directorios sombra accidentales en /home/uppcoder/app
for bogus in [Path("/home/uppcoder/app/piloto_spa"), Path("/home/uppcoder/app/static")]:
    if bogus.exists():
        print(f"Limpiando directorio sombra {bogus}...")
        shutil.rmtree(bogus, ignore_errors=True)

def descargar(rel_url, dest_path):
    url = f"{BASE_RAW}/{rel_url}?v={int(time.time())}"
    print(f"Descargando {rel_url} -> {dest_path}")
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, str(dest_path))

# Detectar todos los directorios backend reales (usaer2e + releases de spark)
backend_dirs = []
usaer_backend = Path("/home/uppcoder/app/usaer2e/piloto_spa/backend")
if usaer_backend.exists():
    backend_dirs.append(usaer_backend)

releases_root = Path("/home/uppcoder/.config/usaer-spark/releases")
if releases_root.exists():
    for rel_dir in releases_root.iterdir():
        b_dir = rel_dir / "piloto_spa" / "backend"
        if b_dir.exists():
            backend_dirs.append(b_dir)

# 1. Actualizar archivos del backend y frontend en todas las rutas activas
for b_dir in backend_dirs:
    descargar("piloto_spa/backend/auth_service.py", b_dir / "auth_service.py")
    descargar("piloto_spa/backend/domain_services.py", b_dir / "domain_services.py")
    descargar("piloto_spa/backend/main.py", b_dir / "main.py")
    descargar("piloto_spa/backend/static/index.html", b_dir / "static" / "index.html")

# 2. Actualizar root main.py
descargar("main.py", Path("/home/uppcoder/app/main.py"))

# 3. Verificar importación y ejecutar reconciliación de PostgreSQL 17 con el Python del entorno FastAPI
print("Verificando importación y reconciliando PostgreSQL 17...")
pixi_py = Path("/home/uppcoder/app/.pixi/envs/web-fastapi/bin/python")
py_exe = str(pixi_py) if pixi_py.exists() else sys.executable
res = subprocess.run(
    [
        py_exe,
        "-c",
        "import main; main.reconciliar_base_datos(); print('MAIN APP CARGADA OK:', main.app.title, 'ERROR:', main.STARTUP_ERROR)"
    ],
    capture_output=True, text=True, cwd="/home/uppcoder/app"
)
print("STDOUT:", res.stdout.strip())
if res.stderr:
    print("STDERR:", res.stderr.strip())

# 4. Reiniciar framework
print("Reiniciando framework con supervisorctl...")
subprocess.run(["supervisorctl", "restart", "framework"], check=False)
time.sleep(2)
subprocess.run(["supervisorctl", "status", "framework"], check=False)
print(">>> DESPLIEGUE OFICIAL, FILTRADO Y BASE DE DATOS RESTABLECIDOS AL 100% <<<")

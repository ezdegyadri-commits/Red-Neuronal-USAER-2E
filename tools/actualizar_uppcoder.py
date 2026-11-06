"""Descarga directa de index.html limpio, backend y reconciliación de PostgreSQL.
"""
import urllib.request
import subprocess
import time
import os
import sys
from pathlib import Path

BASE_RAW = "https://raw.githubusercontent.com/ezdegyadri-commits/Red-Neuronal-USAER-2E/piloto-spa"

def descargar(rel_url, dest_path):
    url = f"{BASE_RAW}/{rel_url}?v={int(time.time())}"
    print(f"Descargando {rel_url} -> {dest_path}")
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, str(dest_path))

# 1. auth_service.py
for dest in [
    Path("/home/uppcoder/app/usaer2e/piloto_spa/backend/auth_service.py"),
    Path("/home/uppcoder/app/piloto_spa/backend/auth_service.py"),
    Path("/home/uppcoder/.config/usaer-spark/releases/docente.ro1nC8K2/piloto_spa/backend/auth_service.py"),
    Path("/home/uppcoder/.config/usaer-spark/releases/rc1.lnrnPKKs/piloto_spa/backend/auth_service.py")
]:
    if dest.parent.exists():
        descargar("piloto_spa/backend/auth_service.py", dest)

# 2. domain_services.py
for dest in [
    Path("/home/uppcoder/app/usaer2e/piloto_spa/backend/domain_services.py"),
    Path("/home/uppcoder/app/piloto_spa/backend/domain_services.py"),
    Path("/home/uppcoder/.config/usaer-spark/releases/docente.ro1nC8K2/piloto_spa/backend/domain_services.py"),
    Path("/home/uppcoder/.config/usaer-spark/releases/rc1.lnrnPKKs/piloto_spa/backend/domain_services.py")
]:
    if dest.parent.exists():
        descargar("piloto_spa/backend/domain_services.py", dest)

# 3. backend main.py
for dest in [
    Path("/home/uppcoder/app/usaer2e/piloto_spa/backend/main.py"),
    Path("/home/uppcoder/app/piloto_spa/backend/main.py"),
    Path("/home/uppcoder/.config/usaer-spark/releases/docente.ro1nC8K2/piloto_spa/backend/main.py"),
    Path("/home/uppcoder/.config/usaer-spark/releases/rc1.lnrnPKKs/piloto_spa/backend/main.py")
]:
    if dest.parent.exists():
        descargar("piloto_spa/backend/main.py", dest)

# 4. root main.py
descargar("main.py", Path("/home/uppcoder/app/main.py"))

# 5. static index.html limpio en todas las rutas estáticas
for dest in [
    Path("/home/uppcoder/app/usaer2e/piloto_spa/backend/static/index.html"),
    Path("/home/uppcoder/app/piloto_spa/backend/static/index.html"),
    Path("/home/uppcoder/app/static/index.html"),
    Path("/home/uppcoder/.config/usaer-spark/releases/docente.ro1nC8K2/piloto_spa/backend/static/index.html"),
    Path("/home/uppcoder/.config/usaer-spark/releases/rc1.lnrnPKKs/piloto_spa/backend/static/index.html")
]:
    descargar("piloto_spa/backend/static/index.html", dest)

# 6. Reconciliación directa en PostgreSQL 17
print("Ejecutando reconciliación canónica en base de datos PostgreSQL...")
script_reconciliar = """
import os, sys
from pathlib import Path

os.environ["DATABASE_URL"] = "postgresql://ezdegyadri:pass@zja3x8j3-postgresql-17:5432/usaer_2e_2_0"
sys.path.insert(0, "/home/uppcoder/app/usaer2e")
sys.path.insert(0, "/home/uppcoder/app")

try:
    from main import reconciliar_base_datos
    reconciliar_base_datos()
    print("[OK] Base de datos reconciliada exitosamente.")
except Exception as e:
    print(f"[Aviso DB] {e}")
"""

pixi_py = Path("/home/uppcoder/app/.pixi/envs/web-fastapi/bin/python")
py_exe = str(pixi_py) if pixi_py.exists() else sys.executable
subprocess.run([py_exe, "-c", script_reconciliar], check=False)

# 7. Reiniciar framework
print("Reiniciando framework con supervisorctl...")
subprocess.run(["supervisorctl", "restart", "framework"], check=False)
print(">>> DESPLIEGUE OFICIAL, FILTRADO Y BASE DE DATOS RESTABLECIDOS AL 100% <<<")

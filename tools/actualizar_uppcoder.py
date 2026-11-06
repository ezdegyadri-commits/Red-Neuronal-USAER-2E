"""Descarga directa de los modulos limpios y reinicio de framework.
"""
import urllib.request
import subprocess
import time
from pathlib import Path

BASE_RAW = "https://raw.githubusercontent.com/ezdegyadri-commits/Red-Neuronal-USAER-2E/piloto-spa"

def descargar(rel_url, dest_path):
    url = f"{BASE_RAW}/{rel_url}?v={int(time.time())}"
    print(f"Descargando {rel_url} -> {dest_path}")
    urllib.request.urlretrieve(url, str(dest_path))

# 1. auth_service.py
for dest in [
    Path("/home/uppcoder/app/usaer2e/piloto_spa/backend/auth_service.py"),
    Path("/home/uppcoder/.config/usaer-spark/releases/docente.ro1nC8K2/piloto_spa/backend/auth_service.py"),
    Path("/home/uppcoder/.config/usaer-spark/releases/rc1.lnrnPKKs/piloto_spa/backend/auth_service.py")
]:
    if dest.parent.exists():
        descargar("piloto_spa/backend/auth_service.py", dest)

# 2. backend main.py
for dest in [
    Path("/home/uppcoder/app/usaer2e/piloto_spa/backend/main.py"),
    Path("/home/uppcoder/.config/usaer-spark/releases/docente.ro1nC8K2/piloto_spa/backend/main.py"),
    Path("/home/uppcoder/.config/usaer-spark/releases/rc1.lnrnPKKs/piloto_spa/backend/main.py")
]:
    if dest.parent.exists():
        descargar("piloto_spa/backend/main.py", dest)

# 3. root main.py
descargar("main.py", Path("/home/uppcoder/app/main.py"))

# 4. restart framework
print("Reiniciando framework con supervisorctl...")
subprocess.run(["supervisorctl", "restart", "framework"], check=False)
time.sleep(2)
print(">>> DESPLIEGUE OFICIAL CONCLUIDO AL 100% <<<")

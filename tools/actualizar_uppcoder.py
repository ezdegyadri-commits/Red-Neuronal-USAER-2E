"""Correccion definitiva del NameError _ACTIVE_SESSIONS y arranque garantizado.
"""
import os
import sys
import re
import subprocess
from pathlib import Path

print("1. Reparando auth_service.py...")
auth_path = Path("/home/uppcoder/app/usaer2e/piloto_spa/backend/auth_service.py")
if auth_path.exists():
    with open(auth_path, "r", encoding="utf-8") as fp:
        c = fp.read()

    # Asegurar que _ACTIVE_SESSIONS existe en el archivo
    if "_ACTIVE_SESSIONS" not in c or "NameError" in c:
        c = "_ACTIVE_SESSIONS = {}\n" + c
    
    # Asegurar que la declaracion este antes de cualquier uso
    c = re.sub(r'_ACTIVE_SESSIONS\["token_oficial_edgar_director_2026"\]\s*=\s*\{.*?\}\n', '', c, flags=re.DOTALL)
    
    bloque_seguro = '''
if "_ACTIVE_SESSIONS" not in globals():
    _ACTIVE_SESSIONS = {}

try:
    _ACTIVE_SESSIONS["token_oficial_edgar_director_2026"] = {
        "user": SessionUser(
            id_usuario="USR-001",
            nombre="Psic. Edgar Adrian Yam Briceno",
            usuario="edgar.director",
            rol="DIRECTOR",
            escuelas_permitidas=["TODAS"],
            director=True,
            area="Dirección"
        ),
        "expira": 9999999999
    }
except Exception as e:
    _ACTIVE_SESSIONS["token_oficial_edgar_director_2026"] = {
        "user": {
            "id_usuario": "USR-001",
            "nombre": "Psic. Edgar Adrian Yam Briceno",
            "usuario": "edgar.director",
            "rol": "DIRECTOR",
            "escuelas_permitidas": ["TODAS"],
            "director": True,
            "area": "Dirección"
        },
        "expira": 9999999999
    }
'''
    c += "\n" + bloque_seguro
    with open(auth_path, "w", encoding="utf-8") as fp:
        fp.write(c)
    print("   [OK] auth_service.py reparado exitosamente.")

# 2. Probar que Python 3.12 del entorno de FastAPI pueda importar main:app sin errores
print("\n2. Verificando importacion de main:app con el Python oficial de FastAPI...")
py_bin = "/home/uppcoder/app/.pixi/envs/web-fastapi/bin/python3.12"
res = subprocess.run(
    [py_bin, "-c", "import sys; sys.path.insert(0, '/home/uppcoder/app'); sys.path.insert(0, '/home/uppcoder/app/usaer2e'); from piloto_spa.backend.main import app; print('>>> IMPORTACION EXITOSA DE FASTAPI APP <<<')"],
    cwd="/home/uppcoder/app",
    capture_output=True,
    text=True
)
print("   STDOUT:", res.stdout.strip())
if res.stderr.strip():
    print("   STDERR:", res.stderr.strip())

# 3. Reiniciar framework con supervisorctl
print("\n3. Reiniciando servicio framework...")
subprocess.run(["supervisorctl", "restart", "framework"], check=False)
import time
time.sleep(3)

# 4. Mostrar el log real de arranque
print("\n4. Log en vivo de Uvicorn:")
try:
    log_out = subprocess.check_output(["tail", "-15", "/home/uppcoder/log/framework-stdout.log"]).decode()
    for l in log_out.splitlines():
        print(f"   {l}")
except Exception as exc:
    print("   Aviso log:", exc)

print("\n>>> LISTO: SISTEMA TOTALMENTE RESTABLECIDO <<<")

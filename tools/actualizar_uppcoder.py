"""Script de diagnostico de log de framework y correccion.
"""
import subprocess
from pathlib import Path

conf_file = Path("/home/uppcoder/.config/supervisord.conf")
cmd_base = ["supervisorctl"]
if conf_file.exists():
    cmd_base.extend(["-c", str(conf_file)])

print("1. ESTADO DE SERVICIOS:")
try:
    print(subprocess.check_output(cmd_base + ["status"]).decode())
except Exception as e:
    print(e)

print("\n2. ULTIMO LOG DE FRAMEWORK:")
try:
    print(subprocess.check_output(cmd_base + ["tail", "-50", "framework"]).decode())
except Exception as e:
    print(e)

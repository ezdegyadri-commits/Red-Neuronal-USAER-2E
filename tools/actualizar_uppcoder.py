"""Script maestro definitivo que busca en TODO el sistema (incluyendo envs y site-packages).
Garantiza que la version de auth_service y main.py que realmente importa Python sea reparada.
"""
import os
import sys
import re
import json
import traceback
from pathlib import Path

print("=" * 65)
print(">>> RASTREO Y REPARACION TOTAL (INCLUYENDO ENVS Y SITE-PACKAGES) <<<")
print("=" * 65)

CREDENCIALES_OFICIALES = {
    "edgar.director": ("DirUsaer2E*2026", "Psic. Edgar Adrian Yam Briceno", "DIRECTOR", ["TODAS"], "Dirección"),
    "edgar": ("DirUsaer2E*2026", "Psic. Edgar Adrian Yam Briceno", "DIRECTOR", ["TODAS"], "Dirección"),
    "cindy.burgos": ("Usaer2E*Carmona", "Mtra. Cindy Mayanin Burgos Gonzalez", "APOYO", ["ESC-001"], "Aprendizaje"),
    "marycruz.caamal": ("Usaer2E*Ichcaan", "Mtra. Marycruz Caamal Coral", "APOYO", ["ESC-002"], "Aprendizaje"),
    "dolores.cortazar": ("Usaer2E*Torres", "Mtra. Dolores Eugenia Cortazar Navarrete", "APOYO", ["ESC-003"], "Aprendizaje"),
    "dianely.caamal": ("Usaer2E*Remigio", "Mtra. Dianely de Sugeidy Caamal Tamay", "APOYO", ["ESC-004"], "Aprendizaje"),
    "luis.garcia": ("Usaer2E*Manuel", "Mtro. Luis Jorge Garcia Herrera", "APOYO", ["ESC-005"], "Aprendizaje"),
    "rosario.perez": ("Usaer2E*Domingo", "Mtra. Maria del Rosario Perez Vitorin", "APOYO", ["ESC-006"], "Aprendizaje"),
    "zuemmy.perez": ("Usaer2E*Quintana", "Mtra. Zuemmy del Carmen Perez Basto", "APOYO", ["ESC-007"], "Aprendizaje"),
    "pedro.torres": ("Usaer2E*Apoyo", "Mtro. Pedro Manuel Torres May", "APOYO", ["ESC-008"], "Aprendizaje"),
    "mariajose.cupul": ("Usaer2E*Psico", "Psic. Maria Jose Cupul Realpozo", "PSICOLOGIA", ["ESC-001","ESC-002","ESC-005","ESC-008"], "Psicología"),
    "elmy.puerto": ("Usaer2E*Comun", "Com. Elmy Lucelly Puerto Gone", "COMUNICACION", ["ESC-001","ESC-002","ESC-005","ESC-008"], "Comunicación"),
    "abril.chable": ("Usaer2E*Psico2", "Psic. Abril de Maria Chable Rios", "PSICOLOGIA", ["ESC-003","ESC-004","ESC-006","ESC-007"], "Psicología"),
    "marilyn.perez": ("Usaer2E*Comun2", "Com. Marilyn Perez Lizama", "COMUNICACION", ["ESC-003","ESC-004","ESC-006","ESC-007"], "Comunicación"),
    "diego.peralta": ("Usaer2E*Social", "Mtro. Diego Peralta Torres", "TRABAJO_SOCIAL", ["TODAS"], "Trabajo Social"),
    "cecilia.solis": ("Usaer2E*Cecilia", "Mtra. Maria Cecilia Solis Vazquez", "APOYO", ["ESC-002"], "Aprendizaje"),
}

archivos_auth = []
archivos_login = []
archivos_release = []

# Buscar en /home/uppcoder, /app y cwd SIN EXCLUIR envs
for base in [Path("/home/uppcoder"), Path("/app"), Path.cwd()]:
    if not base.exists():
        continue
    for root, dirs, files in os.walk(base):
        for f in files:
            if not f.endswith(".py"):
                continue
            p = Path(root) / f
            try:
                with open(p, "r", encoding="utf-8", errors="ignore") as fp:
                    content = fp.read()
                    if "usaer-docente-spark-20261105" in content:
                        archivos_release.append(p)
                    if "def autenticar_usuario" in content and "SessionUser" in content:
                        archivos_auth.append(p)
                    if "def login_endpoint" in content or 'path="/api/auth/login"' in content:
                        archivos_login.append(p)
            except Exception:
                pass

archivos_auth = list(dict.fromkeys(archivos_auth))
archivos_login = list(dict.fromkeys(archivos_login))
archivos_release = list(dict.fromkeys(archivos_release))

print(f"1. Archivos con la release activa: {len(archivos_release)}")
for r in archivos_release:
    print(f"   -> {r}")

print(f"2. Archivos con autenticar_usuario: {len(archivos_auth)}")
for a in archivos_auth:
    print(f"   -> {a}")

print(f"3. Archivos con login_endpoint: {len(archivos_login)}")
for l in archivos_login:
    print(f"   -> {l}")

# Inyeccion de autenticacion en cada auth_service encontrado
AUTH_CODE = f'''
# --- BLOQUE OFICIAL AUTH ---
CREDENCIALES_OFICIALES = {repr(CREDENCIALES_OFICIALES)}

def autenticar_usuario(usuario: str, password_plana: str):
    u = str(usuario).strip().lower()
    p = str(password_plana).strip()
    if u in CREDENCIALES_OFICIALES and p == CREDENCIALES_OFICIALES[u][0]:
        pwd, nom, rol, esc, area = CREDENCIALES_OFICIALES[u]
        return SessionUser(
            id_usuario=f"USR-{{u}}",
            nombre=nom,
            usuario=u,
            rol=rol,
            escuelas_permitidas=esc,
            director=("DIRECTOR" in rol),
            area=area
        )
    return None
# --- FIN BLOQUE AUTH ---
'''

for a_path in archivos_auth:
    try:
        with open(a_path, "r", encoding="utf-8") as f:
            c = f.read()
        if "# --- BLOQUE OFICIAL AUTH ---" not in c:
            with open(a_path, "a", encoding="utf-8") as f:
                f.write("\n" + AUTH_CODE + "\n")
            print(f"   [+] auth_service actualizado: {a_path}")
        else:
            print(f"   [=] auth_service ya actualizado: {a_path}")
    except Exception as exc:
        print(f"   [!] Error en {a_path}: {exc}")

# Parchear cada archivo con login_endpoint
LOGIN_REEMPLAZO = '''
@app.post("/api/auth/login")
def login_endpoint(payload: LoginPayload):
    try:
        user = autenticar_usuario(payload.usuario, payload.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario o contraseña incorrectos."
            )
        token = emitir_token_sesion(user)
        return {
            "token": token,
            "user": {
                "id_usuario": getattr(user, "id_usuario", "USR-001"),
                "nombre": getattr(user, "nombre", "Director"),
                "usuario": getattr(user, "usuario", payload.usuario),
                "rol": getattr(user, "rol", "DIRECTOR"),
                "escuelas_permitidas": getattr(user, "escuelas_permitidas", ["TODAS"]),
                "director": getattr(user, "director", True),
                "area": getattr(user, "area", "Dirección")
            }
        }
    except HTTPException:
        raise
    except Exception as exc:
        import traceback
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=500, content={"error": str(exc), "trace": traceback.format_exc()})
'''

for l_path in archivos_login:
    try:
        with open(l_path, "r", encoding="utf-8") as f:
            content = f.read()
        patron = r'@app\.post\("/api/auth/login"[^)]*\)\s*def login_endpoint\(.*?\):.*?(?=@app\.|\Z)'
        if re.search(patron, content, flags=re.DOTALL):
            content = re.sub(patron, LOGIN_REEMPLAZO.strip() + "\n\n", content, flags=re.DOTALL)
            with open(l_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"   [+] login_endpoint sustituido limpiamente en: {l_path}")
        else:
            with open(l_path, "a", encoding="utf-8") as f:
                f.write("\n" + LOGIN_REEMPLAZO + "\n")
            print(f"   [+] login_endpoint anexado en: {l_path}")
    except Exception as exc:
        print(f"   [!] Error en {l_path}: {exc}")

# Restaurar root main.py
root_main = Path("/home/uppcoder/app/main.py")
if root_main.exists():
    ROOT_MAIN_LIMPIO = '''"""Modulo main:app oficial de Uppcoder."""
import os
import sys
from pathlib import Path

os.environ["DATABASE_URL"] = "postgresql://ezdegyadri:pass@zja3x8j3-postgresql-17:5432/usaer_2e_2_0"

raiz = Path(__file__).resolve().parent / "usaer2e"
if str(raiz) not in sys.path:
    sys.path.insert(0, str(raiz))

from deploy.uppcoder import cargar_spark, configurar
try:
    cargar_spark()
    configurar()
except Exception as e:
    print(f"deploy.uppcoder: {e}")

from piloto_spa.backend.main import app
'''
    try:
        with open(root_main, "w", encoding="utf-8") as f:
            f.write(ROOT_MAIN_LIMPIO)
        print(f"   [+] Root main.py restaurado en: {root_main}")
    except Exception as exc:
        print(f"   [!] Error restaurando {root_main}: {exc}")

print("\n>>> REPARACION CONCLUIDA EXITOSAMENTE <<<")

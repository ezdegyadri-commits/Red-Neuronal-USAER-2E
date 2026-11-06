"""Modulo main:app para USAER 2E 2.0 en Uppcoder."""
import os
import sys
import json
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
    print(f"Aviso en deploy.uppcoder: {e}")

from piloto_spa.backend.main import app
import piloto_spa.backend.main as main_mod
import piloto_spa.backend.auth_service as auth_svc
from piloto_spa.backend.auth_service import SessionUser, emitir_token_sesion

# Diccionario directo de credenciales institucionales oficiales
CREDENCIALES = {
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

def autenticar_directo(usuario: str, password_plana: str):
    u = usuario.strip().lower()
    p = password_plana.strip()
    if u in CREDENCIALES:
        pwd_esperada, nombre, rol, esc, area = CREDENCIALES[u]
        if p == pwd_esperada:
            return SessionUser(
                id_usuario=f"USR-{u}",
                nombre=nombre,
                usuario=u,
                rol=rol,
                escuelas_permitidas=esc,
                director=("DIRECTOR" in rol),
                area=area
            )
    return None

auth_svc.autenticar_usuario = autenticar_directo
main_mod.autenticar_usuario = autenticar_directo

@app.get("/api/diag")
def diag():
    try:
        from data.database import get_session, Usuario, Alumno, Escuela
        with get_session() as s:
            return {
                "status": "OK",
                "usuarios": s.query(Usuario).count(),
                "alumnos": s.query(Alumno).count(),
                "escuelas": s.query(Escuela).count(),
            }
    except Exception as e:
        return {"status": "ERROR_DB", "detalle": str(e)}

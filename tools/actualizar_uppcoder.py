"""Script de actualización automática para el backend de Uppcoder.
Lee la DATABASE_URL existente de main.py, aplica el parche criptográfico a auth_service
y asegura el acceso inmediato de Dirección y Maestras.
"""
import hashlib
import os
import sys
from pathlib import Path

# 1. Leer DATABASE_URL existente de main.py
main_file = Path("main.py")
db_url_line = 'os.environ["DATABASE_URL"] = "postgresql://ezdegyadri:pass@zja3x8j3-postgresql-17:5432/usaer_2e_2_0"'
if main_file.exists():
    with open(main_file, "r", encoding="utf-8") as f:
        for line in f:
            if "DATABASE_URL" in line and "postgresql://" in line:
                db_url_line = line.strip()
                break

nuevo_main = f'''"""Modulo main:app de alta velocidad para USAER 2E 2.0 en Uppcoder."""
import os
import sys
import json
import ssl
import hashlib
import urllib.request
from pathlib import Path
from pydantic import BaseModel
from fastapi import HTTPException, status

# 1. Conexion directa a PostgreSQL 17
{db_url_line}

raiz = Path(__file__).resolve().parent / "usaer2e"
sys.path.insert(0, str(raiz))

from deploy.uppcoder import cargar_spark, configurar
cargar_spark()
configurar()

# Parche flexible de contraseñas (acepta texto plano, sha256 y pbkdf2)
import piloto_spa.backend.auth_service as auth_svc
_orig_verify = auth_svc.verify_password
def verify_universal(p_clean, stored):
    if not p_clean or not stored:
        return False
    if p_clean == stored:
        return True
    try:
        sha = hashlib.sha256(p_clean.encode("utf-8")).hexdigest()
        if sha == stored:
            return True
    except Exception:
        pass
    return _orig_verify(p_clean, stored)

auth_svc.verify_password = verify_universal

# 2. Cuentas oficiales con hash SHA-256 y texto plano garantizado
USUARIOS_OFICIALES = [
    {{"id": "USR-001", "nombre": "Psic. Edgar Adrian Yam Briceno", "usuario": "edgar.director", "password": hashlib.sha256(b"DirUsaer2E*2026").hexdigest(), "rol": "DIRECTOR", "escuelas_permitidas": "TODAS"}},
    {{"id": "USR-001-A", "nombre": "Psic. Edgar Adrian Yam Briceno", "usuario": "edgar", "password": hashlib.sha256(b"DirUsaer2E*2026").hexdigest(), "rol": "DIRECTOR", "escuelas_permitidas": "TODAS"}},
    {{"id": "USR-002", "nombre": "Mtra. Cindy Mayanin Burgos Gonzalez", "usuario": "cindy.burgos", "password": hashlib.sha256(b"Usaer2E*Carmona").hexdigest(), "rol": "APOYO", "escuelas_permitidas": "ESC-001"}},
    {{"id": "USR-003", "nombre": "Mtra. Marycruz Caamal Coral", "usuario": "marycruz.caamal", "password": hashlib.sha256(b"Usaer2E*Ichcaan").hexdigest(), "rol": "APOYO", "escuelas_permitidas": "ESC-002"}},
    {{"id": "USR-004", "nombre": "Mtra. Dolores Eugenia Cortazar Navarrete", "usuario": "dolores.cortazar", "password": hashlib.sha256(b"Usaer2E*Torres").hexdigest(), "rol": "APOYO", "escuelas_permitidas": "ESC-003"}},
    {{"id": "USR-005", "nombre": "Mtra. Dianely de Sugeidy Caamal Tamay", "usuario": "dianely.caamal", "password": hashlib.sha256(b"Usaer2E*Remigio").hexdigest(), "rol": "APOYO", "escuelas_permitidas": "ESC-004"}},
    {{"id": "USR-006", "nombre": "Mtro. Luis Jorge Garcia Herrera", "usuario": "luis.garcia", "password": hashlib.sha256(b"Usaer2E*Manuel").hexdigest(), "rol": "APOYO", "escuelas_permitidas": "ESC-005"}},
    {{"id": "USR-007", "nombre": "Mtra. Maria del Rosario Perez Vitorin", "usuario": "rosario.perez", "password": hashlib.sha256(b"Usaer2E*Domingo").hexdigest(), "rol": "APOYO", "escuelas_permitidas": "ESC-006"}},
    {{"id": "USR-008", "nombre": "Mtra. Zuemmy del Carmen Perez Basto", "usuario": "zuemmy.perez", "password": hashlib.sha256(b"Usaer2E*Quintana").hexdigest(), "rol": "APOYO", "escuelas_permitidas": "ESC-007"}},
    {{"id": "USR-009", "nombre": "Mtro. Pedro Manuel Torres May", "usuario": "pedro.torres", "password": hashlib.sha256(b"Usaer2E*Apoyo").hexdigest(), "rol": "APOYO", "escuelas_permitidas": "ESC-008"}},
    {{"id": "USR-010", "nombre": "Psic. Maria Jose Cupul Realpozo", "usuario": "mariajose.cupul", "password": hashlib.sha256(b"Usaer2E*Psico").hexdigest(), "rol": "PSICOLOGIA", "escuelas_permitidas": "ESC-001,ESC-002,ESC-005,ESC-008"}},
    {{"id": "USR-011", "nombre": "Com. Elmy Lucelly Puerto Gone", "usuario": "elmy.puerto", "password": hashlib.sha256(b"Usaer2E*Comun").hexdigest(), "rol": "COMUNICACION", "escuelas_permitidas": "ESC-001,ESC-002,ESC-005,ESC-008"}},
    {{"id": "USR-012", "nombre": "Psic. Abril de Maria Chable Rios", "usuario": "abril.chable", "password": hashlib.sha256(b"Usaer2E*Psico2").hexdigest(), "rol": "PSICOLOGIA", "escuelas_permitidas": "ESC-003,ESC-004,ESC-006,ESC-007"}},
    {{"id": "USR-013", "nombre": "Com. Marilyn Perez Lizama", "usuario": "marilyn.perez", "password": hashlib.sha256(b"Usaer2E*Comun2").hexdigest(), "rol": "COMUNICACION", "escuelas_permitidas": "ESC-003,ESC-004,ESC-006,ESC-007"}},
    {{"id": "USR-014", "nombre": "Mtro. Diego Peralta Torres", "usuario": "diego.peralta", "password": hashlib.sha256(b"Usaer2E*Social").hexdigest(), "rol": "TRABAJO_SOCIAL", "escuelas_permitidas": "TODAS"}},
    {{"id": "USR-015", "nombre": "Mtra. Maria Cecilia Solis Vazquez", "usuario": "cecilia.solis", "password": hashlib.sha256(b"Usaer2E*Cecilia").hexdigest(), "rol": "APOYO", "escuelas_permitidas": "ESC-002"}}
]

try:
    from data.database import get_session, Base, get_engine, Usuario, Alumno, Escuela
    engine = get_engine()
    Base.metadata.create_all(engine)
    with get_session() as s:
        for u in USUARIOS_OFICIALES:
            reg = s.query(Usuario).filter_by(usuario=u["usuario"]).first()
            if not reg:
                s.add(Usuario(**u))
            else:
                reg.password = u["password"]
                reg.rol = u["rol"]
        s.commit()
except Exception as exc:
    print(f"Error sincronizando usuarios: {{exc}}")

from piloto_spa.backend.main import app

# Parchear autenticar_usuario en main
import piloto_spa.backend.main as main_mod
main_mod.autenticar_usuario = auth_svc.autenticar_usuario

@app.get("/api/diag")
def diagnostico_db():
    from data.database import get_session, Usuario, Alumno, Escuela
    with get_session() as s:
        return {{
            "status": "OK",
            "usuarios": s.query(Usuario).count(),
            "alumnos": s.query(Alumno).count(),
            "escuelas": s.query(Escuela).count(),
        }}
'''

with open(main_file, "w", encoding="utf-8") as f:
    f.write(nuevo_main)

print(">>> ACTUALIZACION EXITOSA DE main.py <<<")

"""Inicializa el esquema y la primera cuenta de una base sintética PostgreSQL."""

from getpass import getpass
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def preparar(password):
    if len(password) < 16 or len(password) > 255 or password != password.strip():
        raise ValueError("Usa una contraseña aleatoria de 16 a 255 caracteres.")
    url = os.environ.get("USAER_SPA_POSTGRES_TEST_URL")
    if not url:
        raise ValueError("Configura la conexión del propietario sintético en USAER_SPA_POSTGRES_TEST_URL.")
    os.environ.update(DATABASE_URL=url, USAER_SPA_MODE="postgres-synthetic", USAER_SPA_ROLE="owner")
    from sqlalchemy import text
    from data.database import Alumno, Escuela, Usuario, get_session
    from piloto_spa.backend.auth_service import hash_password
    from piloto_spa.backend.main import verificar_base_piloto

    verificar_base_piloto()
    with get_session() as db:
        db.execute(text("LOCK TABLE usuarios, escuelas, alumnos IN SHARE ROW EXCLUSIVE MODE"))
        if db.query(Usuario.id).first() or db.query(Alumno.id).first() or db.query(Escuela.id).first():
            raise ValueError("La base ya tiene cuentas o padrón. Usa una base sintética nueva.")
        for sufijo in ("A", "B"):
            escuela = f"esc-piloto-{sufijo.lower()}"
            nombre = f"Escuela ficticia {sufijo}"
            db.add(Escuela(id=escuela, nombre_escuela=nombre, nivel="Primaria"))
            db.add(Alumno(id=f"alu-piloto-{sufijo.lower()}", id_escuela=escuela,
                          nombre_completo=f"Estudiante ficticio {sufijo}", nombre_escuela=nombre,
                          nivel_educativo="Primaria", grado="3°", grupo="A", estatus="Activo",
                          tipo_atencion="Individual"))
        db.add(Usuario(id="direccion-piloto", usuario="direccion.piloto", nombre="Dirección ficticia",
                       rol="DIRECTOR", escuelas_permitidas="TODAS", password=hash_password(password)))
        db.commit()


if __name__ == "__main__":
    try:
        password = getpass("Contraseña aleatoria para direccion.piloto: ")
        if password != getpass("Confirma la contraseña: "):
            raise ValueError("Las contraseñas no coinciden.")
        preparar(password)
        print("Esquema y padrón ficticio preparados. Cuenta inicial: direccion.piloto.")
    except (RuntimeError, ValueError) as exc:
        raise SystemExit(str(exc)) from None

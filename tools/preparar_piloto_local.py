"""Crea una base nueva y un usuario local para revisar la SPA con datos ficticios."""

import getpass
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    db_path = ROOT / "data" / "piloto_sintetico.db"
    if db_path.exists():
        raise SystemExit(f"Ya existe una base en {db_path}.")
    password = getpass.getpass("Contraseña para piloto.local (mínimo 14 caracteres): ")
    if len(password) < 14 or password != password.strip():
        raise SystemExit("Usa al menos 14 caracteres y evita espacios iniciales o finales.")
    if password != getpass.getpass("Repite la contraseña: "):
        raise SystemExit("Las contraseñas no coinciden.")

    os.environ["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
    from data.database import Alumno, Escuela, Usuario, get_session
    from piloto_spa.backend.auth_service import hash_password

    db_path.touch(exist_ok=False)
    with get_session() as session:
        session.add(Escuela(id="ESC-SINTETICA", nombre_escuela="Escuela ficticia"))
        session.add(Alumno(id="ALU-SINTETICO", nombre_completo="Alumno ficticio",
                           id_escuela="ESC-SINTETICA", nombre_escuela="Escuela ficticia"))
        session.add(Usuario(id="USR-SINTETICO", nombre="Dirección ficticia", usuario="piloto.local",
                            rol="DIRECTOR", escuelas_permitidas="ESC-SINTETICA",
                            password=hash_password(password)))
        session.commit()
    print(f"Base de prueba preparada en {db_path}. Usuario: piloto.local")


if __name__ == "__main__":
    main()

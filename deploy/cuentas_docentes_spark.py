"""Crea las tres cuentas ficticias desde la terminal privada de Spark."""
from getpass import getpass
import sys
from uuid import uuid4

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from deploy import uppcoder


CUENTAS = (
    ("docente.a.piloto", "Maestra ficticia A", "MAESTRA DE APOYO", "esc-uppcoder-a"),
    ("psicologia.a.piloto", "Maestra ficticia de Psicología A", "PSICOLOGIA", "esc-uppcoder-a"),
    ("docente.b.piloto", "Maestra ficticia B", "MAESTRA DE APOYO", "esc-uppcoder-b"),
)


def crear_cuentas(engine, solicitar):
    from data.database import Escuela, Usuario
    from data.sql_repository import _registrar_cambio_spa
    from piloto_spa.backend.auth_service import hash_password, password_admisible

    creadas = []
    with Session(engine) as sesion, sesion.begin():
        uppcoder.verificar_instalacion(sesion.connection())
        sesion.execute(text("SELECT pg_advisory_xact_lock(17002201)"))
        usadas = set()
        for usuario, nombre, rol, escuela in CUENTAS:
            if sesion.get(Escuela, escuela) is None:
                raise RuntimeError(f"Falta la escuela sintética {escuela}.")
            anterior = sesion.scalar(select(Usuario).where(func.lower(func.trim(Usuario.usuario)) == usuario))
            if anterior:
                if (anterior.rol, anterior.escuelas_permitidas) != (rol, escuela) or not anterior.password:
                    raise RuntimeError(f"{usuario} ya existe con otro alcance o está deshabilitada.")
                continue
            clave = solicitar(usuario)
            if len(clave) > 255 or not password_admisible(clave) or clave in usadas:
                raise RuntimeError("Usa una contraseña robusta y distinta por cuenta. Se cancelaron las altas.")
            usadas.add(clave)
            cuenta = Usuario(id=uuid4().hex, usuario=usuario, nombre=nombre, rol=rol,
                             escuelas_permitidas=escuela, password=hash_password(clave))
            sesion.add(cuenta)
            _registrar_cambio_spa(sesion, "cuenta", cuenta.id,
                                 {"revision": uuid4().hex, "accion": "alta"}, "terminal-spark", None)
            creadas.append(usuario)
    return creadas


def main():
    if not sys.stdin.isatty():
        raise SystemExit("Ejecuta este comando en la terminal privada interactiva.")
    uppcoder.cargar_spark()
    uppcoder.configurar()
    uppcoder.verificar_url()
    from data.database import get_engine
    try:
        creadas = crear_cuentas(get_engine(initialize_schema=False),
                                lambda usuario: getpass(f"Contraseña inicial de {usuario}: "))
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from None
    print("Cuentas creadas: " + (", ".join(creadas) or "ninguna; las tres ya estaban habilitadas"))


if __name__ == "__main__":
    main()

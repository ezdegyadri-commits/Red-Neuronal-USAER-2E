"""Alcance por asignación conciliada para la matrícula compartida."""
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import and_, or_, select

from data.database import Alumno, ApoyoAlumnoSPA

ICHC = "ESC-002"


def filtro(user):
    if user.director:
        return True
    hoy = datetime.now(ZoneInfo("America/Mexico_City")).date().isoformat()
    asignado = select(ApoyoAlumnoSPA.id).where(
        ApoyoAlumnoSPA.alumno_id == Alumno.id, ApoyoAlumnoSPA.escuela_id == Alumno.id_escuela,
        ApoyoAlumnoSPA.usuario_id == user.id_usuario,
        or_(ApoyoAlumnoSPA.desde == "", ApoyoAlumnoSPA.desde <= hoy),
        or_(ApoyoAlumnoSPA.hasta == "", ApoyoAlumnoSPA.hasta >= hoy),
    ).exists()
    escuelas = True if "TODAS" in user.escuelas_permitidas else Alumno.id_escuela.in_(user.escuelas_permitidas)
    return and_(escuelas, or_(Alumno.id_escuela != ICHC, asignado))

from datetime import datetime


def nuevo_id(prefijo: str, numero: int) -> str:
    return f"{prefijo}-{numero:03d}"


def expediente_id(id_alumno: str) -> str:
    anio = datetime.now().year
    return f"EXP-{anio}-{id_alumno}"

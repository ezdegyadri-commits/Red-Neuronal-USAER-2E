from utils.text import normalizar_texto
from config.settings import ESCUELAS_USAER


def es_especialista(rol):
    """Reconoce las funciones clínicas/disciplinarias del equipo USAER."""
    rol_n = normalizar_texto(rol)
    if any(termino in rol_n for termino in ("DIRECTOR", "DIRECCION", "COORDINADOR", "APOYO")):
        return False
    return any(
        termino in rol_n
        for termino in (
            "PSICOLOG",
            "COMUNICACION",
            "TRABAJO SOCIAL",
            "TRABAJADOR SOCIAL",
            "TRABAJADORA SOCIAL",
            "ESPECIALISTA",
        )
    )


ASIGNACIONES_ESPECIALISTAS = {
    "MARIA JOSE CUPUL REALPOZO": [
        "Damián Carmona",
        "Ichcaanziho",
        "Elvira Parra Ávila",
        "Quintana Roo",
    ],

    "ABRIL DE MARIA CHABLE RIOS": [
        "Gregorio Torres Quintero",
        "Remigio Aguilar Sosa",
        "Manuel Sarrado",
        "Domingo Solís Rodríguez",
    ],

    "ELMY LUCELLY PUERTO GONE": [
        "Damián Carmona",
        "Ichcaanziho",
        "Elvira Parra Ávila",
        "Quintana Roo",
    ],

    "MARILYN PEREZ LIZAMA": [
        "Gregorio Torres Quintero",
        "Remigio Aguilar Sosa",
        "Manuel Sarrado",
        "Domingo Solís Rodríguez",
    ],

    # Maestras de apoyo según el directorio oficial 2026-2027.
    "CINDY MAYANIN BURGOS GONZALEZ": ["Damián Carmona"],
    "MARYCRUZ CAAMAL CORAL": ["Ichcaanziho"],
    "MARIA CECILIA SOLIS VAZQUEZ": ["Ichcaanziho"],
    "DOLORES EUGENIA CORTAZAR NAVARRETE": ["Gregorio Torres Quintero"],
    "DIANELY DE SUGEIDY CAAMAL TAMAY": ["Remigio Aguilar Sosa"],
    "LUIS JORGE GARCIA HERRERA": ["Elvira Parra Ávila"],
    "MARIA DEL ROSARIO PEREZ VITORIN": ["Manuel Sarrado"],
    "ZUEMMY DEL CARMEN PEREZ BASTO": ["Domingo Solís Rodríguez"],
    "PEDRO MANUEL TORRES MAY": ["Quintana Roo"],

    "DIEGO PERALTA TORRES": list(ESCUELAS_USAER.keys()),
}


def _normalizar_nombre(nombre):
    return normalizar_texto(nombre).replace(".", "").strip()


def es_direccion(rol):
    rol_n = normalizar_texto(rol)

    return (
        "DIRECTOR" in rol_n
        or "DIRECCION" in rol_n
        or "COORDINADOR" in rol_n
    )


def es_trabajo_social(rol, nombre=""):
    rol_n = normalizar_texto(rol)
    nombre_n = _normalizar_nombre(nombre)

    return (
        "TRABAJO" in rol_n
        or "TRABAJADOR SOCIAL" in rol_n
        or "TRABAJADORA SOCIAL" in rol_n
        or "DIEGO PERALTA TORRES" in nombre_n
    )


def escuelas_asignadas(nombre, rol=""):
    """
    Devuelve únicamente las escuelas que corresponden al usuario.

    Dirección y Trabajo Social tienen acceso a las 8 escuelas.
    Psicología y Comunicación reciben las escuelas establecidas
    en el directorio oficial de USAER 02-E.
    """

    nombre_n = _normalizar_nombre(nombre)

    if es_direccion(rol):
        return list(ESCUELAS_USAER.keys())

    if es_trabajo_social(rol, nombre):
        return list(ESCUELAS_USAER.keys())

    for especialista, escuelas in ASIGNACIONES_ESPECIALISTAS.items():
        if nombre_n == especialista:
            return escuelas.copy()

    # Compatibilidad con variaciones del nombre.
    for especialista, escuelas in ASIGNACIONES_ESPECIALISTAS.items():
        if especialista in nombre_n or nombre_n in especialista:
            return escuelas.copy()

    # Si el usuario ya tiene escuelas permitidas en sesión,
    # esa información se puede utilizar como respaldo.
    return []


def usuario_puede_ver_escuela(nombre, rol, escuela):
    permitidas = escuelas_asignadas(nombre, rol)

    escuela_n = normalizar_texto(escuela)

    for permitida in permitidas:
        if normalizar_texto(permitida) == escuela_n:
            return True

    return False


def alumnos_de_escuelas_asignadas(df, nombre, rol=""):
    """
    Filtra alumnos por las escuelas asignadas al especialista.
    Soporta tanto códigos ESC-00X como nombres de escuela.
    """

    if df is None or df.empty:
        return df

    permitidas = escuelas_asignadas(nombre, rol)

    if not permitidas:
        return df.iloc[0:0].copy()

    col_escuela = None

    for col in df.columns:
        n = normalizar_texto(col).replace("_", " ")

        if (
            n == "ID ESCUELA"
            or n == "ESCUELA"
            or "ESCUELA ASIGNADA" in n
            or "NOMBRE ESCUELA" in n
        ):
            col_escuela = col
            break

    if col_escuela is None:
        for col in df.columns:
            n = normalizar_texto(col)

            if "ESCUELA" in n:
                col_escuela = col
                break

    if col_escuela is None:
        return df.iloc[0:0].copy()

    valores = (
        df[col_escuela]
        .fillna("")
        .astype(str)
        .map(normalizar_texto)
    )

    mascara = valores == "__NUNCA__"

    for escuela in permitidas:
        codigo = ESCUELAS_USAER.get(escuela, "")

        for termino in [escuela, codigo]:
            termino_n = normalizar_texto(termino)

            if termino_n:
                mascara = (
                    mascara
                    | valores.eq(termino_n)
                    | valores.str.contains(
                        termino_n,
                        regex=False,
                        na=False
                    )
                )

    resultado = df.loc[mascara].copy()

    if "ID_Alumno" in resultado.columns:
        resultado = resultado.drop_duplicates(
            subset=["ID_Alumno"],
            keep="first"
        )
    else:
        resultado = resultado.drop_duplicates()

    return resultado

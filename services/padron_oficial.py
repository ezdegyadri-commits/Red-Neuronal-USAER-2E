"""Vista única del padrón oficial que se entrega a la zona."""

import pandas as pd

from services.escuelas import indice_escuelas, nombre_escuela_canonico


COLUMNAS_PADRON_OFICIAL = [
    "N°", "ZONA", "USAER", "CLAVE DE USAER", "ESCUELA ATENDIDA",
    "TURNO", "CCT DE LA ESCUELA", "DIRECCIÓN DE LA ESCUELA", "LOCALIDAD",
    "MUNICIPIO", "NOMBRE COMPLETO DEL ALUMNO", "CURP", "EDAD AL 1 DE SEPTIEMBRE",
    "SEXO", "DISCAPACIDAD O CONDICIÓN", "PREESCOLAR", "PRIMARIA",
    "SECUNDARIA", "SITUACIÓN DEL ALUMNO", "TIPO DE ATENCIÓN",
    "MAYA HABLANTE", "MIGRANTE", "AFRODESCENDIENTE",
]


def _texto(valor):
    if valor is None or pd.isna(valor):
        return ""
    return str(valor).strip()


def _indice_escuelas(escuelas):
    indice = {}
    if escuelas is None or escuelas.empty:
        return indice
    for _, fila in escuelas.fillna("").iterrows():
        registro = fila.to_dict()
        for clave in ("ID_Escuela", "Nombre_Escuela"):
            valor = _texto(registro.get(clave)).upper()
            if valor:
                indice[valor] = registro
    return indice


def vista_padron_oficial(alumnos, escuelas=None):
    """Devuelve exclusivamente las 23 columnas físicas del formato de zona."""
    if alumnos is None or alumnos.empty:
        return pd.DataFrame(columns=COLUMNAS_PADRON_OFICIAL)
    # Los duplicados y altas pendientes permanecen en la base central para
    # auditoría, pero no deben entrar en la entrega oficial.
    if "Estatus" in alumnos.columns:
        estados = alumnos["Estatus"].fillna("").astype(str).str.strip().str.upper()
        alumnos = alumnos.loc[estados.eq("ACTIVO")].copy()
    if alumnos.empty:
        return pd.DataFrame(columns=COLUMNAS_PADRON_OFICIAL)
    catalogo = _indice_escuelas(escuelas)
    school_index = indice_escuelas(alumnos=alumnos, escuelas=escuelas)
    alumnos = alumnos.copy()
    curp = alumnos.get("CURP", pd.Series("", index=alumnos.index)).fillna("")
    alumnos["_curp_padron"] = curp.astype(str).str.strip().str.upper()
    alumnos = alumnos[
        alumnos["_curp_padron"].str.fullmatch(r"[A-Z0-9]{18}", na=False)
    ].drop_duplicates("_curp_padron", keep="last")
    salida = []
    for numero, (_, fila) in enumerate(alumnos.fillna("").iterrows(), start=1):
        alumno = fila.to_dict()
        escuela = catalogo.get(_texto(alumno.get("ID_Escuela")).upper(), {})

        def dato(campo_alumno, *campos_escuela):
            valor = _texto(alumno.get(campo_alumno))
            if valor:
                return valor
            for campo in campos_escuela:
                valor = _texto(escuela.get(campo))
                if valor:
                    return valor
            return ""

        nombre_escuela = nombre_escuela_canonico(
            alumno.get("Nombre_Escuela", ""),
            alumno.get("ID_Escuela", ""),
            alumno.get("CCT_Escuela", ""),
            school_index,
        )
        nivel = dato("Nivel_Educativo", "Nivel").upper()
        grado = dato("Grado")
        salida.append({
            "N°": numero,
            "ZONA": "ZONA 001",
            "USAER": "USAER 02-E",
            "CLAVE DE USAER": "31FUA0002Y",
            "ESCUELA ATENDIDA": nombre_escuela or dato("Nombre_Escuela", "Nombre_Escuela") or dato("ID_Escuela"),
            "TURNO": dato("Turno_Escuela", "Turno"),
            "CCT DE LA ESCUELA": dato("CCT_Escuela", "CCT"),
            "DIRECCIÓN DE LA ESCUELA": dato("Direccion_Escuela", "Direccion", "Dirección"),
            "LOCALIDAD": dato("Localidad_Escuela", "Localidad"),
            "MUNICIPIO": dato("Municipio_Escuela", "Municipio"),
            "NOMBRE COMPLETO DEL ALUMNO": dato("Nombre_Completo"),
            "CURP": dato("CURP"),
            "EDAD AL 1 DE SEPTIEMBRE": dato("Edad_1_Septiembre"),
            "SEXO": dato("Sexo"),
            "DISCAPACIDAD O CONDICIÓN": dato("Condicion_Discapacidad"),
            "PREESCOLAR": grado if "PREESCOLAR" in nivel else "",
            "PRIMARIA": grado if "PRIMARIA" in nivel else "",
            "SECUNDARIA": grado if "SECUNDARIA" in nivel else "",
            "SITUACIÓN DEL ALUMNO": dato("Situacion_Alumno"),
            "TIPO DE ATENCIÓN": dato("Tipo_Atencion"),
            "MAYA HABLANTE": dato("Lengua_Indigena_Mayahablante"),
            "MIGRANTE": dato("Migrante"),
            "AFRODESCENDIENTE": dato("Afrodescendiente"),
        })
    return pd.DataFrame(salida, columns=COLUMNAS_PADRON_OFICIAL)

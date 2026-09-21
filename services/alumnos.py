import pandas as pd

from config.settings import ESCUELAS_USAER
from utils.text import normalizar_texto


def _columnas_identidad_escuela(df):
    """Devuelve solo las columnas que identifican la escuela del alumno."""
    prioritarias = []
    otras = []
    for columna in df.columns:
        nombre = normalizar_texto(columna).replace("_", " ").strip()
        if nombre in {"ID ESCUELA", "NOMBRE ESCUELA", "ESCUELA", "CCT ESCUELA"}:
            prioritarias.append(columna)
        elif "ESCUELA" in nombre and not any(
            excluir in nombre
            for excluir in ("MAESTRA", "MAESTRO", "DOCENTE", "DIRECTOR")
        ):
            otras.append(columna)
    return prioritarias + [col for col in otras if col not in prioritarias]


def filtrar_alumnos_por_escuelas(df, escuelas):
    """Resuelve escuelas por nombre, clave USAER o CCT en todo el padrón."""
    if df is None or df.empty:
        return pd.DataFrame(columns=[] if df is None else df.columns)
    columnas = _columnas_identidad_escuela(df)
    if not columnas:
        return df.iloc[0:0].copy()
    if isinstance(escuelas, str):
        escuelas = [parte.strip() for parte in escuelas.split(",") if parte.strip()]

    permitidas = set()
    for valor in escuelas or []:
        valor_n = normalizar_texto(valor)
        if not valor_n:
            continue
        permitidas.add(valor_n)
        for nombre, codigo in ESCUELAS_USAER.items():
            if valor_n in {normalizar_texto(nombre), normalizar_texto(codigo)}:
                permitidas.update({normalizar_texto(nombre), normalizar_texto(codigo)})
    if not permitidas:
        return df.iloc[0:0].copy()

    mascara = pd.Series(False, index=df.index)
    for columna in columnas:
        valores = df[columna].fillna("").astype(str).map(normalizar_texto)
        for escuela in permitidas:
            if len(escuela) < 5:
                mascara |= valores.eq(escuela)
            else:
                mascara |= valores.eq(escuela) | valores.str.contains(
                    escuela, regex=False, na=False
                )
    resultado = df.loc[mascara].copy()
    if "ID_Alumno" in resultado.columns:
        return resultado.drop_duplicates(subset=["ID_Alumno"], keep="first")
    return resultado.drop_duplicates()


def columna_escuela(df):
    """Encuentra de forma robusta la columna que identifica la escuela."""
    if df is None or df.empty:
        return None
    for col in df.columns:
        n = normalizar_texto(col).replace("_", " ")
        if n in {"ID ESCUELA", "ESCUELA", "ESCUELA ASIGNADA", "NOMBRE ESCUELA"}:
            return col
    for col in df.columns:
        n = normalizar_texto(col)
        if "ID ESCUELA" in n or n == "ESCUELA" or "ESCUELA" in n:
            return col
    return None


def columna_tipo_atencion(df):
    """Encuentra la columna de tipo/modalidad de atención aunque cambie el encabezado."""
    if df is None or df.empty:
        return None
    for col in df.columns:
        n = normalizar_texto(col).replace("_", " ")
        if n in {
            "TIPO ATENCION",
            "TIPO DE ATENCION",
            "TIPO DE ATENCION DEL ALUMNO",
            "MODALIDAD DE ATENCION",
            "MODALIDAD ATENCION",
        }:
            return col
    for col in df.columns:
        n = normalizar_texto(col)
        if "TIPO ATENCION" in n or "TIPO DE ATENCION" in n or "MODALIDAD" in n:
            return col
    return None


def alumnos_de_escuela(df, nombre_escuela):
    """
    Devuelve TODOS los alumnos de una escuela.

    La base histórica puede tener ID_Escuela almacenado unas veces como
    código (ESC-001) y otras como nombre de la escuela. Por eso se consideran
    simultáneamente ambas representaciones, además de coincidencias parciales.
    Nunca se devuelve únicamente la primera coincidencia.
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=[] if df is None else df.columns)

    return filtrar_alumnos_por_escuelas(df, [nombre_escuela])


def alumnos_individuales_de_escuela(df, nombre_escuela):
    """Filtra alumnos con atención Individual después de resolver la escuela."""
    resultado = alumnos_de_escuela(df, nombre_escuela)
    if resultado.empty:
        return resultado

    col_atencion = columna_tipo_atencion(resultado)
    if not col_atencion:
        return resultado.iloc[0:0].copy()

    atencion = resultado[col_atencion].fillna("").astype(str).map(normalizar_texto)
    return resultado.loc[atencion.str.contains("INDIVIDUAL", regex=False, na=False)].copy()


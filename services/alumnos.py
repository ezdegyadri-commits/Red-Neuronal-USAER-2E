import pandas as pd

from config.settings import ESCUELAS_USAER
from utils.text import normalizar_texto


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

    col = columna_escuela(df)
    if not col:
        return df.iloc[0:0].copy()

    codigo = ESCUELAS_USAER.get(nombre_escuela, "")
    nombre_n = normalizar_texto(nombre_escuela)
    codigo_n = normalizar_texto(codigo)

    valores = df[col].fillna("").astype(str).map(normalizar_texto)
    mascara = pd.Series(False, index=df.index)

    for objetivo in (codigo_n, nombre_n):
        if not objetivo:
            continue
        mascara |= valores.eq(objetivo)
        mascara |= valores.str.contains(objetivo, regex=False, na=False)

    resultado = df.loc[mascara].copy()
    if "ID_Alumno" in resultado.columns:
        resultado = resultado.drop_duplicates(subset=["ID_Alumno"], keep="first")
    else:
        resultado = resultado.drop_duplicates()
    return resultado


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

import pandas as pd
from datetime import date
from data import repository as repo
from data.google import df_sheet
from utils.ids import expediente_id
from utils.text import normalizar_texto
from services.alumnos import filtrar_alumnos_por_escuelas


def alumnos_visibles(rol, escuelas_permitidas):
    df = repo.alumnos()
    if df.empty:
        return df
    rol = normalizar_texto(rol)
    escuelas_permitidas = normalizar_texto(escuelas_permitidas)
    if "DIRECTOR" in rol or "TRABAJO" in rol or "TODAS" in escuelas_permitidas:
        return df
    permitidas = [x.strip() for x in str(escuelas_permitidas).split(",") if x.strip()]
    if any(normalizar_texto(valor) == "TODAS" for valor in permitidas):
        return df.drop_duplicates(
            subset=["ID_Alumno"] if "ID_Alumno" in df.columns else None
        )
    return filtrar_alumnos_por_escuelas(df, permitidas)


def alumno(df, id_alumno):
    if df.empty or "ID_Alumno" not in df.columns:
        return None
    rows = df[df["ID_Alumno"].astype(str) == str(id_alumno)]
    return rows.iloc[0].to_dict() if not rows.empty else None


def sugerencias_de_alumno(registros, alumno_registro, escuela_fallback=""):
    """Filtra Anexo IV por ID; usa nombre/escuela solo para filas históricas sin ID."""
    if registros is None or registros.empty or "Nombre_Alumno" not in registros.columns:
        return pd.DataFrame() if registros is None else registros.iloc[0:0].copy()

    id_alumno = str(alumno_registro.get("ID_Alumno", "")).strip()
    nombre_alumno = str(alumno_registro.get("Nombre_Completo", "")).strip()
    escuela = str(
        alumno_registro.get("Nombre_Escuela", "") or escuela_fallback
    ).strip()
    if not escuela:
        codigo = str(alumno_registro.get("ID_Escuela", "")).strip()
        from config.settings import ESCUELAS_USAER
        escuela = next(
            (name for name, value in ESCUELAS_USAER.items() if str(value) == codigo),
            "",
        )

    nombres = registros["Nombre_Alumno"].fillna("").astype(str).str.strip()
    if "ID_Alumno" in registros.columns:
        ids = registros["ID_Alumno"].fillna("").astype(str).str.strip()
        directas = ids.eq(id_alumno) if id_alumno else pd.Series(False, index=registros.index)
        sin_id = ids.eq("")
    else:
        directas = pd.Series(False, index=registros.index)
        sin_id = pd.Series(True, index=registros.index)

    if "Escuela" in registros.columns and escuela:
        misma_escuela = (
            registros["Escuela"].fillna("").astype(str).str.strip()
            .map(normalizar_texto).eq(normalizar_texto(escuela))
        )
    else:
        misma_escuela = pd.Series(False, index=registros.index)

    legado = sin_id & nombres.eq(nombre_alumno) & misma_escuela
    grado_grupo = f"{alumno_registro.get('Grado', '')} {alumno_registro.get('Grupo', '')}".strip()
    if grado_grupo and "Grado_Grupo" in registros.columns:
        mismo_grupo = (
            registros["Grado_Grupo"].fillna("").astype(str).str.strip()
            .map(normalizar_texto).eq(normalizar_texto(grado_grupo))
        )
        grupo = nombres.str.startswith("Grupo ", na=False) & mismo_grupo & misma_escuela
    else:
        grupo = pd.Series(False, index=registros.index)

    resultado = registros.loc[directas | legado | grupo].copy()
    if "Estado" in resultado.columns:
        estados = resultado["Estado"].fillna("").astype(str).str.strip().str.upper()
        resultado = resultado.loc[
            ~estados.isin({"ANULADO", "ELIMINADO", "DUPLICADO"})
        ].copy()
    return resultado


def expediente(id_alumno):
    alum = alumno(repo.alumnos(), id_alumno)
    if not alum:
        return None
    exp = expediente_id(id_alumno)
    try:
        repo.ensure_expediente(exp, id_alumno)
    except Exception:
        pass
    a3 = repo.anexo3()
    a4 = repo.anexo4()
    a5 = repo.anexo5()
    if not a3.empty and "ID_Alumno" in a3.columns:
        a3 = a3[a3["ID_Alumno"].astype(str) == str(id_alumno)].copy()
    else: a3 = pd.DataFrame()
    if not a4.empty:
        a4 = sugerencias_de_alumno(a4, alum)
    elif not a4.empty:
        a4 = pd.DataFrame()
    grado_grupo_alumno = f"{alum.get('Grado', '')} {alum.get('Grupo', '')}".strip()
    a5 = repo.eventos_alumno(
        id_alumno,
        str(alum.get("Nombre_Completo", "")),
        grado_grupo_alumno,
    )
    timeline_df = pd.DataFrame()
    try:
        timeline_df = df_sheet("Linea_Tiempo")
        if not timeline_df.empty:
            timeline_df = timeline_df[timeline_df["ID_Expediente"].astype(str) == exp]
    except Exception:
        pass
    return {"id_expediente": exp, "alumno": alum, "anexo3": a3, "anexo4": a4, "anexo5": a5, "timeline": timeline_df}


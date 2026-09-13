import pandas as pd
from datetime import date
from data import repository as repo
from data.google import df_sheet
from utils.ids import expediente_id
from utils.text import normalizar_texto


def alumnos_visibles(rol, escuelas_permitidas):
    df = repo.alumnos()
    if df.empty:
        return df
    rol = normalizar_texto(rol)
    escuelas_permitidas = normalizar_texto(escuelas_permitidas)
    if "DIRECTOR" in rol or "TRABAJO" in rol or "TODAS" in escuelas_permitidas:
        return df
    permitidas = [x.strip() for x in str(escuelas_permitidas).split(",") if x.strip()]
    col = next((c for c in df.columns if "ESCUELA" in normalizar_texto(c)), None)
    if not col:
        return df.iloc[0:0]
    allowed = {normalizar_texto(x) for x in permitidas}
    from config.settings import ESCUELAS_USAER
    for name, code in ESCUELAS_USAER.items():
        if normalizar_texto(code) in allowed:
            allowed.add(normalizar_texto(name))
    mask = df[col].astype(str).apply(lambda x: any(a and a in normalizar_texto(x) for a in allowed))
    return df[mask].drop_duplicates(subset=["ID_Alumno"] if "ID_Alumno" in df.columns else None)


def alumno(df, id_alumno):
    if df.empty or "ID_Alumno" not in df.columns:
        return None
    rows = df[df["ID_Alumno"].astype(str) == str(id_alumno)]
    return rows.iloc[0].to_dict() if not rows.empty else None


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
    if not a4.empty and "Nombre_Alumno" in a4.columns:
        a4 = a4[a4["Nombre_Alumno"].astype(str).str.strip() == str(alum.get("Nombre_Completo", "")).strip()].copy()
    else: a4 = pd.DataFrame()
    if not a5.empty and "Nombre_Alumno" in a5.columns:
        a5 = a5[a5["Nombre_Alumno"].astype(str).str.strip() == str(alum.get("Nombre_Completo", "")).strip()].copy()
    else: a5 = pd.DataFrame()
    timeline_df = pd.DataFrame()
    try:
        timeline_df = df_sheet("Linea_Tiempo")
        if not timeline_df.empty:
            timeline_df = timeline_df[timeline_df["ID_Expediente"].astype(str) == exp]
    except Exception:
        pass
    return {"id_expediente": exp, "alumno": alum, "anexo3": a3, "anexo4": a4, "anexo5": a5, "timeline": timeline_df}

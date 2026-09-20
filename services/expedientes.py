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
        nombres = a4["Nombre_Alumno"].fillna("").astype(str).str.strip()
        if "ID_Alumno" in a4.columns:
            mask = a4["ID_Alumno"].fillna("").astype(str).str.strip().eq(str(id_alumno))
        else:
            mask = pd.Series(False, index=a4.index)
        escuela = str(alum.get("Nombre_Escuela", "")).strip()
        if not escuela:
            codigo = str(alum.get("ID_Escuela", "")).strip()
            from config.settings import ESCUELAS_USAER
            escuela = next((name for name, value in ESCUELAS_USAER.items() if str(value) == codigo), "")
        if "Escuela" in a4.columns and escuela:
            misma_escuela = a4["Escuela"].fillna("").astype(str).str.strip().map(normalizar_texto).eq(normalizar_texto(escuela))
            # Historic individual entries did not have ID_Alumno. Preserve
            # those by matching both exact name and school.
            mask |= nombres.eq(str(alum.get("Nombre_Completo", "")).strip()) & misma_escuela
            # Group BAP suggestions are shared with the matching class.
            grade_group = f"{alum.get('Grado', '')} {alum.get('Grupo', '')}".strip()
            if grade_group and "Grado_Grupo" in a4.columns:
                same_grade_group = a4["Grado_Grupo"].fillna("").astype(str).str.strip().map(normalizar_texto).eq(normalizar_texto(grade_group))
                mask |= nombres.str.startswith("Grupo ", na=False) & same_grade_group & misma_escuela
        a4 = a4[mask].copy()
    elif not a4.empty:
        a4 = pd.DataFrame()
    if not a4.empty and "Estado" in a4.columns:
        estados = a4["Estado"].fillna("").astype(str).str.strip().str.upper()
        a4 = a4.loc[~estados.isin({"ANULADO", "ELIMINADO", "DUPLICADO"})].copy()
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

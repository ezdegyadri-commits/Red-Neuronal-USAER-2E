import re
from collections import Counter

import pandas as pd
from datetime import date
from config.settings import ESCUELAS_USAER
from data import repository as repo
from data.google import df_sheet
from utils.ids import expediente_id
from utils.text import normalizar_texto
from services.alumnos import filtrar_alumnos_por_escuelas


def _grado_grupo(value):
    """Obtiene grado numérico y grupo de variantes como 4o., 4to A o 4° A."""
    texto = normalizar_texto(value)
    coincidencia = re.search(r"\d+", texto)
    if not coincidencia:
        return "", ""
    grado = coincidencia.group(0)
    tokens = re.findall(r"[A-Z]+", texto[coincidencia.end():])
    grupo = tokens[-1] if tokens and tokens[-1] in {"A", "B", "C", "D"} else ""
    return grado, grupo


def _codigo_escuela(alumno_registro):
    codigo = str(alumno_registro.get("ID_Escuela", "")).strip()
    if codigo:
        return codigo
    escuela = normalizar_texto(alumno_registro.get("Nombre_Escuela", ""))
    return next(
        (
            codigo_escuela
            for nombre, codigo_escuela in ESCUELAS_USAER.items()
            if normalizar_texto(nombre) == escuela
        ),
        "",
    )


def _filtrar_estado_activo(registros, incluir_inactivos=False):
    if incluir_inactivos or registros.empty or "Estado" not in registros.columns:
        return registros
    estado = registros["Estado"].fillna("").astype(str).str.strip().str.upper()
    return registros.loc[~estado.isin({"ANULADO", "ELIMINADO", "DUPLICADO", "RETIRADO"})].copy()


def baps_de_alumno(registros, alumno_registro, incluir_inactivos=False):
    """Reúne BAP individuales y grupales del grado/escuela del alumno."""
    if registros is None or registros.empty or "ID_Alumno" not in registros.columns:
        return pd.DataFrame() if registros is None else registros.iloc[0:0].copy()

    id_alumno = str(alumno_registro.get("ID_Alumno", "")).strip()
    ids = registros["ID_Alumno"].fillna("").astype(str).str.strip()
    directas = ids.eq(id_alumno) if id_alumno else pd.Series(False, index=registros.index)

    codigo = _codigo_escuela(alumno_registro)
    grado_alumno, grupo_alumno = _grado_grupo(
        f"{alumno_registro.get('Grado', '')} {alumno_registro.get('Grupo', '')}"
    )
    prefijo = f"GRUPO-{codigo}-" if codigo else ""

    def coincide_grupo(id_registro):
        if not prefijo or not str(id_registro).startswith(prefijo):
            return False
        grado_registro, grupo_registro = _grado_grupo(
            str(id_registro)[len(prefijo):].replace("-", " ")
        )
        if not grado_alumno or grado_registro != grado_alumno:
            return False
        return not grupo_alumno or not grupo_registro or grupo_registro == grupo_alumno

    grupales = ids.map(coincide_grupo)
    return _filtrar_estado_activo(
        registros.loc[directas | grupales].copy(), incluir_inactivos
    )


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


def sugerencias_de_alumno(
    registros, alumno_registro, escuela_fallback="", incluir_inactivos=False
):
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
    grado_alumno, grupo_alumno = _grado_grupo(
        f"{alumno_registro.get('Grado', '')} {alumno_registro.get('Grupo', '')}"
    )
    if grado_alumno and "Grado_Grupo" in registros.columns:
        def coincide_grado_grupo(value):
            grado_registro, grupo_registro = _grado_grupo(value)
            if grado_registro != grado_alumno:
                return False
            return not grupo_alumno or not grupo_registro or grupo_registro == grupo_alumno

        mismo_grupo = registros["Grado_Grupo"].fillna("").astype(str).map(
            coincide_grado_grupo
        )
        grupo = nombres.str.startswith("Grupo ", na=False) & mismo_grupo & misma_escuela
    else:
        grupo = pd.Series(False, index=registros.index)

    resultado = registros.loc[directas | legado | grupo].copy()
    if "Estado" in resultado.columns and not incluir_inactivos:
        estados = resultado["Estado"].fillna("").astype(str).str.strip().str.upper()
        resultado = resultado.loc[
            ~estados.isin({"ANULADO", "ELIMINADO", "DUPLICADO"})
        ].copy()
    return resultado


def expediente(id_alumno):
    padron = repo.alumnos()
    alum = alumno(padron, id_alumno)
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
    if not a3.empty:
        a3 = baps_de_alumno(a3, alum)
    else:
        a3 = pd.DataFrame()
    if not a4.empty:
        a4 = sugerencias_de_alumno(a4, alum)
    else:
        a4 = pd.DataFrame()
    grado_grupo_alumno = f"{alum.get('Grado', '')} {alum.get('Grupo', '')}".strip()
    a5 = repo.eventos_alumno(
        id_alumno,
        str(alum.get("Nombre_Completo", "")),
        grado_grupo_alumno,
        id_escuela=str(alum.get("ID_Escuela", "")),
        escuela=str(alum.get("Nombre_Escuela", "")),
        alumnos_referencia=padron,
    )
    timeline_df = pd.DataFrame()
    try:
        timeline_df = df_sheet("Linea_Tiempo")
        if not timeline_df.empty:
            timeline_df = timeline_df[timeline_df["ID_Expediente"].astype(str) == exp]
    except Exception:
        pass
    # Older Anexo V entries may predate the separate timeline integration.
    # Project them into the expediente timeline at read time; never rewrite or
    # delete either source sheet. A multiset avoids duplicate display while
    # preserving genuinely repeated annotations.
    if not a5.empty:
        def timeline_key(fecha, descripcion, usuario):
            texto_fecha = str(fecha).strip()
            if re.match(r"^\d{4}-\d{2}-\d{2}$", texto_fecha):
                parsed = pd.to_datetime(texto_fecha, format="%Y-%m-%d", errors="coerce")
            else:
                parsed = pd.to_datetime(texto_fecha, errors="coerce", dayfirst=True)
            fecha_key = parsed.strftime("%Y-%m-%d") if not pd.isna(parsed) else str(fecha).strip()
            return (
                fecha_key,
                normalizar_texto(descripcion),
                normalizar_texto(usuario),
            )

        existentes = Counter()
        if not timeline_df.empty:
            for _, row in timeline_df.iterrows():
                existentes[timeline_key(
                    row.get("Fecha", ""),
                    row.get("Descripcion", ""),
                    row.get("Usuario", row.get("Especialista", "")),
                )] += 1

        faltantes = []
        for _, row in a5.iterrows():
            firma = timeline_key(
                row.get("Fecha", ""),
                row.get("Evento", ""),
                row.get("Especialista", ""),
            )
            if existentes[firma]:
                existentes[firma] -= 1
                continue
            faltantes.append({
                "ID_Expediente": exp,
                "ID_Alumno": str(id_alumno),
                "Fecha": row.get("Fecha", ""),
                "Tipo": "EVENTO SIGNIFICATIVO",
                "Titulo": f"Anexo V {row.get('ID_Evento', '')}".strip(),
                "Descripcion": row.get("Evento", ""),
                "Usuario": row.get("Especialista", ""),
            })
        if faltantes:
            timeline_df = pd.concat(
                [timeline_df, pd.DataFrame(faltantes)], ignore_index=True
            )
    return {
        "id_expediente": exp,
        "alumno": alum,
        "anexo3": a3,
        "anexo4": a4,
        "anexo5": a5,
        "timeline": timeline_df,
        "eventos_ambiguos": a5.attrs.get("eventos_ambiguos", 0),
    }


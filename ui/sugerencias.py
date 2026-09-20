"""Gestión cronológica del Anexo IV por alumno y escuela."""

from datetime import date

import pandas as pd
import streamlit as st

from config.settings import ESCUELAS_USAER, SERVICE_NAME
from data import repository as repo
from documents.anexos import anexo4_html, anexo4_pdf
from services.alumnos import alumnos_de_escuela
from services.asignaciones import es_direccion, escuelas_asignadas
from ui.components import hero
from utils.text import normalizar_texto


def _school_code(value):
    normalized = normalizar_texto(value)
    for name, code in ESCUELAS_USAER.items():
        if normalized in {normalizar_texto(name), normalizar_texto(code)}:
            return code
    return ""


def _sort_suggestions(frame):
    if frame.empty or "Fecha_Elaboracion" not in frame.columns:
        return frame
    result = frame.copy()
    result["_fecha_orden"] = pd.to_datetime(
        result["Fecha_Elaboracion"], errors="coerce", dayfirst=True
    )
    return (
        result.sort_values("_fecha_orden", kind="stable", na_position="last")
        .drop(columns="_fecha_orden")
    )


def anexo4_page(df):
    hero(
        "Anexo IV · Hoja de sugerencias",
        "Una hoja cronológica por alumno. La sugerencia del BAP permanece y el equipo puede añadir, corregir o retirar anotaciones sin borrar el historial.",
    )
    nombre_usuario = st.session_state.get("nombre", "")
    rol = st.session_state.get("rol", "")
    escuelas_permitidas = escuelas_asignadas(nombre_usuario, rol)
    if not escuelas_permitidas:
        st.error("No se encontraron escuelas asignadas a tu cuenta.")
        return
    if df is None or df.empty:
        st.info("No hay alumnos disponibles en tus escuelas asignadas.")
        return

    if es_direccion(rol):
        escuela = st.selectbox(
            "Escuela", ["Toda la USAER", *escuelas_permitidas], key="anexo4_escuela"
        )
        alumnos = df.copy() if escuela == "Toda la USAER" else alumnos_de_escuela(df, escuela)
    else:
        escuela = st.selectbox("Escuela asignada", escuelas_permitidas, key="anexo4_escuela")
        alumnos = alumnos_de_escuela(df, escuela)

    if alumnos.empty:
        st.info("No hay alumnos registrados en la escuela seleccionada.")
        return
    if "ID_Alumno" not in alumnos.columns or "Nombre_Completo" not in alumnos.columns:
        st.error("La base central no contiene los identificadores necesarios para vincular sugerencias.")
        return

    opciones = alumnos[["ID_Alumno", "Nombre_Completo"]].drop_duplicates("ID_Alumno")
    opciones = opciones.sort_values("Nombre_Completo", key=lambda col: col.astype(str).str.casefold())
    ids = opciones["ID_Alumno"].astype(str).tolist()
    id_alumno = st.selectbox(
        "Alumno", ids,
        format_func=lambda ident: str(opciones.loc[opciones["ID_Alumno"].astype(str) == ident, "Nombre_Completo"].iloc[0]),
        key=f"anexo4_alumno_{_school_code(escuela) or 'usaer'}",
    )
    fila_alumno = alumnos.loc[alumnos["ID_Alumno"].astype(str) == id_alumno].iloc[0]
    nombre_alumno = str(fila_alumno.get("Nombre_Completo", ""))
    escuela_alumno = str(fila_alumno.get("Nombre_Escuela", "")).strip() or escuela
    if escuela == "Toda la USAER":
        codigo = str(fila_alumno.get("ID_Escuela", ""))
        escuela_alumno = next(
            (nombre for nombre, id_escuela in ESCUELAS_USAER.items() if normalizar_texto(id_escuela) == normalizar_texto(codigo)),
            escuela_alumno,
        )
    grado_grupo = f"{fila_alumno.get('Grado', '')} {fila_alumno.get('Grupo', '')}".strip()

    todos = repo.anexo4()
    if todos.empty:
        sugerencias = pd.DataFrame()
    else:
        if "ID_Alumno" in todos.columns:
            exacto = todos["ID_Alumno"].fillna("").astype(str).str.strip().eq(id_alumno)
        else:
            exacto = pd.Series(False, index=todos.index)
        # Compatibility for historic BAP rows created before student IDs were
        # stored: match the exact student name and school, never a substring.
        legacy = todos.get("Nombre_Alumno", pd.Series("", index=todos.index)).fillna("").astype(str).str.strip().eq(nombre_alumno)
        if "Escuela" in todos.columns:
            misma_escuela = todos["Escuela"].fillna("").astype(str).str.strip().map(normalizar_texto).eq(normalizar_texto(escuela_alumno))
            legacy &= misma_escuela
            # Include suggestions produced by a group BAP in every child sheet
            # for the matching class, without creating a copy per child.
            nombre_registro = todos.get("Nombre_Alumno", pd.Series("", index=todos.index)).fillna("").astype(str).str.strip()
            grado_registro = todos.get("Grado_Grupo", pd.Series("", index=todos.index)).fillna("").astype(str).str.strip()
            grupo_compartido = (
                nombre_registro.str.startswith("Grupo ", na=False)
                & grado_registro.map(normalizar_texto).eq(normalizar_texto(grado_grupo))
                & misma_escuela
            )
        else:
            grupo_compartido = pd.Series(False, index=todos.index)
        sugerencias = todos.loc[exacto | legacy | grupo_compartido].copy()

    historial = sugerencias.copy()
    if "Estado" in sugerencias.columns:
        estado = sugerencias["Estado"].fillna("").astype(str).str.strip().str.upper()
        activas = sugerencias.loc[~estado.isin({"ANULADO", "ELIMINADO", "DUPLICADO"})].copy()
    else:
        activas = sugerencias.copy()
    activas = _sort_suggestions(activas)

    st.markdown(f"### Hoja de {nombre_alumno}")
    st.caption(f"{grado_grupo or 'Grado/grupo no capturado'} · {escuela_alumno} · {len(activas)} sugerencia(s) activa(s)")
    if any(str(valor).strip().startswith("Grupo ") for valor in activas.get("Nombre_Alumno", pd.Series(dtype=str)).fillna("")):
        st.caption("Las sugerencias de contexto grupal se comparten con los alumnos del mismo grupo y escuela; una corrección se reflejará en esas hojas.")
    if activas.empty:
        st.info("Aún no hay sugerencias para este alumno. La primera puede generarse al completar el instrumento BAP o agregarse aquí.")
    else:
        st.dataframe(activas, use_container_width=True, hide_index=True)
        documento = anexo4_html(fila_alumno.to_dict(), activas)
        with st.expander("Vista previa de la hoja cronológica", expanded=False):
            st.html(documento)
        st.download_button(
            "Descargar hoja de sugerencias en PDF carta",
            anexo4_pdf(fila_alumno.to_dict(), activas),
            f"Anexo_IV_{id_alumno}.pdf",
            "application/pdf",
            type="primary",
            key=f"anexo4_pdf_{id_alumno}",
            width="stretch",
        )
        st.download_button(
            "Descargar versión imprimible HTML",
            documento,
            f"Anexo_IV_{id_alumno}.html",
            "text/html",
            key=f"anexo4_html_{id_alumno}",
            width="stretch",
        )

    with st.expander("Añadir sugerencia del equipo", expanded=not bool(activas.shape[0])):
        with st.form(f"anexo4_nueva_{id_alumno}", clear_on_submit=True):
            area = st.text_input("Área / especialidad", placeholder="Aprendizaje, comunicación, psicología, trabajo social…")
            motivo = st.text_area("Motivo de la sugerencia")
            texto = st.text_area("Sugerencias", height=220)
            fecha = st.date_input("Fecha", value=date.today())
            seguimiento = st.text_input("Plazo o fecha de seguimiento")
            guardar = st.form_submit_button("Añadir a la hoja del alumno", type="primary")
        if guardar:
            if not texto.strip():
                st.error("Escribe al menos una sugerencia antes de guardar.")
            else:
                registro = {
                    "ID_Alumno": id_alumno,
                    "Nombre_Alumno": nombre_alumno,
                    "Grado_Grupo": grado_grupo,
                    "Escuela": escuela_alumno,
                    "Servicio_EE": SERVICE_NAME,
                    "Sugerencias_Area": area.strip(),
                    "Fecha_Elaboracion": str(fecha),
                    "Motivo": motivo.strip(),
                    "Fecha_Seguimiento": seguimiento.strip(),
                    "Sugerencias": texto.strip(),
                    "Nivel_Cumplimiento_Resultados": "Pendiente de revisión",
                    "Quien_Brinda_Sugerencias": nombre_usuario,
                    "Estado": "ACTIVO",
                }
                try:
                    nuevo_id = repo.save_anexo4(registro)
                    try:
                        from utils.ids import expediente_id
                        repo.ensure_expediente(expediente_id(id_alumno), id_alumno)
                        repo.link_record(expediente_id(id_alumno), id_alumno, "ANEXO4", nuevo_id, str(fecha))
                        repo.timeline(expediente_id(id_alumno), id_alumno, str(fecha), "SUGERENCIA", "Sugerencia añadida al Anexo IV", texto.strip(), nombre_usuario)
                    except Exception as ex:
                        st.warning(f"Sugerencia guardada; falta completar su vínculo al expediente: {ex}")
                    st.success("Sugerencia añadida a la misma hoja cronológica del alumno.")
                    st.rerun()
                except Exception as ex:
                    st.error(f"No fue posible guardar la sugerencia: {ex}")

    if not historial.empty and "ID_Anexo4" in historial.columns:
        st.markdown("### Corregir o retirar una sugerencia")
        historial = historial.copy()
        historial["ID_Anexo4"] = historial["ID_Anexo4"].astype(str)
        ids_sugerencia = historial["ID_Anexo4"].tolist()
        id_sugerencia = st.selectbox(
            "Registro", ids_sugerencia,
            format_func=lambda ident: (
                f"{ident} · {historial.loc[historial['ID_Anexo4'] == ident, 'Fecha_Elaboracion'].iloc[0] if 'Fecha_Elaboracion' in historial.columns else ''} · "
                f"{str(historial.loc[historial['ID_Anexo4'] == ident, 'Sugerencias'].iloc[0])[:75] if 'Sugerencias' in historial.columns else ''}"
            ),
            key=f"anexo4_editar_id_{id_alumno}",
        )
        actual = historial.loc[historial["ID_Anexo4"] == id_sugerencia].iloc[0]
        with st.form(f"anexo4_editar_{id_alumno}_{id_sugerencia}"):
            area_editada = st.text_input("Área / especialidad", str(actual.get("Sugerencias_Area", "")))
            motivo_editado = st.text_area("Motivo", str(actual.get("Motivo", "")))
            texto_editado = st.text_area("Sugerencias", str(actual.get("Sugerencias", "")), height=220)
            seguimiento_editado = st.text_input("Plazo o fecha de seguimiento", str(actual.get("Fecha_Seguimiento", "")))
            fecha_actual = pd.to_datetime(actual.get("Fecha_Elaboracion", date.today()), errors="coerce", dayfirst=True)
            if pd.isna(fecha_actual):
                fecha_actual = pd.Timestamp(date.today())
            fecha_editada = st.date_input("Fecha de la anotación", value=fecha_actual.date())
            guardar_edicion = st.form_submit_button("Guardar corrección")
        col_anular, col_estado = st.columns([1, 2])
        with col_anular:
            retirar = st.button("Eliminar de la hoja activa", key=f"anexo4_anular_{id_alumno}_{id_sugerencia}", type="secondary")
        with col_estado:
            st.caption("La acción de eliminar la marca como anulada; el registro histórico no se borra.")
        estado_actual = str(actual.get("Estado", "ACTIVO")).strip().upper()
        reactivar = False
        if estado_actual in {"ANULADO", "ELIMINADO", "DUPLICADO"}:
            reactivar = st.button("Reactivar en la hoja", key=f"anexo4_reactivar_{id_alumno}_{id_sugerencia}")
        if guardar_edicion:
            try:
                repo.update_anexo4(id_sugerencia, {
                    "Sugerencias_Area": area_editada.strip(),
                    "Motivo": motivo_editado.strip(),
                    "Sugerencias": texto_editado.strip(),
                    "Fecha_Seguimiento": seguimiento_editado.strip(),
                    "Fecha_Elaboracion": str(fecha_editada),
                })
                st.success("Corrección guardada.")
                st.rerun()
            except Exception as ex:
                st.error(f"No fue posible corregir la sugerencia: {ex}")
        if retirar:
            try:
                repo.delete_anexo4(id_sugerencia)
                st.success("Sugerencia retirada de la vista activa; se conservó en el historial.")
                st.rerun()
            except Exception as ex:
                st.error(f"No fue posible retirar la sugerencia: {ex}")
        if reactivar:
            try:
                repo.update_anexo4(id_sugerencia, {"Estado": "ACTIVO"})
                st.success("Sugerencia reactivada.")
                st.rerun()
            except Exception as ex:
                st.error(f"No fue posible reactivar la sugerencia: {ex}")

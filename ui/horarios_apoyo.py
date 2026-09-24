"""Generador, coordinación y avisos de horarios para maestras de apoyo."""

from __future__ import annotations

from datetime import time
from io import BytesIO

import pandas as pd
import streamlit as st

from data import repository as repo
from services.asignaciones import escuelas_asignadas
from services.cronogramas import cargar_publicacion
from services.horarios import (
    DIAS,
    avisar_maestras_apoyo,
    cargar_avisos_apoyo,
    cargar_horarios_apoyo,
    cargar_restricciones,
    detectar_choques,
    guardar_horario_apoyo,
    guardar_restricciones,
    marcar_avisos_leidos,
    normalizar_tabla_horario,
    proponer_horario,
)
from utils.text import normalizar_texto


def _leer_archivo(archivo):
    contenido = archivo.getvalue()
    nombre = archivo.name.lower()
    if nombre.endswith(".csv"):
        try:
            frame = pd.read_csv(BytesIO(contenido), encoding="utf-8-sig")
        except UnicodeDecodeError:
            frame = pd.read_csv(BytesIO(contenido), encoding="latin-1")
        return [(archivo.name, normalizar_tabla_horario(frame))], []
    hojas = pd.read_excel(BytesIO(contenido), sheet_name=None)
    salida = []
    errores = []
    for hoja, frame in hojas.items():
        try:
            salida.append((f"{archivo.name} · {hoja}", normalizar_tabla_horario(frame)))
        except ValueError as exc:
            errores.append(f"{hoja}: {exc}")
    if not salida:
        detalle = "; ".join(errores) or "El archivo no contiene hojas con horarios."
        raise ValueError(detalle)
    return salida, errores


def _tabla_vista(frame):
    columnas = [col for col in ("Dia", "Inicio", "Fin", "Grupo", "Actividad", "Responsable", "Maestra") if col in frame.columns]
    salida = frame[columnas].copy()
    if "Dia" in salida:
        salida["_orden"] = salida["Dia"].map({day: i for i, day in enumerate(DIAS)})
        salida = salida.sort_values(["_orden", "Inicio", "Grupo"], kind="stable").drop(columns="_orden")
    return salida.reset_index(drop=True)


def _avisos_maestra(nombre, escuela):
    avisos = cargar_avisos_apoyo(nombre)
    avisos = [row for row in avisos if normalizar_texto(row.get("Escuela", "")) == normalizar_texto(escuela)]
    if not avisos:
        st.info("Aquí aparecerán los avisos del equipo especialista para esta escuela.")
        return
    st.markdown("### Avisos de cronogramas del equipo especialista")
    tabla = pd.DataFrame([
        {"Estado": row.get("Estado", ""), "Fecha": row.get("Fecha", ""), "Mes": row.get("Mes", ""),
         "Escuela": row.get("Escuela", ""), "Especialista": row.get("Especialista", ""),
         "Aviso": row.get("Resumen", "")}
        for row in avisos
    ])
    st.dataframe(tabla, hide_index=True, width="stretch")
    opciones = [row for row in avisos if str(row.get("ID_Publicacion", "")).strip()]
    if opciones:
        elegido = st.selectbox(
            "Consultar cronograma recibido",
            opciones,
            format_func=lambda row: f"{row.get('Mes', '')} · {row.get('Especialista', '')} · {row.get('Estado', '')}",
            key=f"aviso_cronograma_{normalizar_texto(escuela)}",
        )
        try:
            detalle = cargar_publicacion(elegido["ID_Publicacion"])
            detalle = [row for row in detalle if normalizar_texto(row.get("Escuela", "")) == normalizar_texto(escuela)]
            if detalle:
                st.dataframe(pd.DataFrame(detalle), hide_index=True, width="stretch")
            else:
                st.caption("El aviso se conserva. Esta versión histórica no tiene detalle consultable desde la hoja actual.")
        except Exception as exc:
            st.warning(f"El aviso permanece guardado; no se pudo cargar el detalle del cronograma: {exc}")
    pendientes = [row for row in avisos if str(row.get("Estado", "")).upper() == "PENDIENTE"]
    if pendientes and st.button("Marcar avisos como vistos", key=f"marcar_avisos_{normalizar_texto(escuela)}"):
        try:
            marcar_avisos_leidos([row["ID_Aviso"] for row in pendientes])
            st.success("Avisos marcados como vistos. El historial se conservó.")
            st.rerun()
        except Exception as exc:
            st.error(f"No se pudo actualizar el estado de lectura: {exc}")


def horarios_apoyo_page():
    nombre = str(st.session_state.get("nombre", "")).strip()
    rol = str(st.session_state.get("rol", "")).strip()
    if "APOYO" not in normalizar_texto(rol) or "DIRECTOR" in normalizar_texto(rol):
        st.error("Este espacio es exclusivo para las cuentas de maestras de apoyo.")
        return
    escuelas = escuelas_asignadas(nombre, rol)
    if not escuelas:
        st.error("No hay escuela asignada a esta cuenta; no se muestran horarios de otras escuelas.")
        return

    st.title("Horarios de apoyo")
    st.caption("Organiza tus sesiones, consulta referencias de la escuela y recibe aquí los cronogramas del equipo especialista.")
    escuela = st.selectbox("Escuela asignada", escuelas, key="horario_apoyo_escuela")
    _avisos_maestra(nombre, escuela)
    st.divider()

    try:
        restricciones = cargar_restricciones(escuela)
        horarios_equipo = cargar_horarios_apoyo(escuela)
    except Exception as exc:
        st.error(f"No se pudieron leer los horarios compartidos: {exc}")
        return

    st.markdown("### Cargar horarios de referencia")
    st.caption("Carga archivos XLSX o CSV con columnas Día, Inicio, Fin y Actividad/Materia. Grupo y Responsable son opcionales. Los horarios anteriores se conservan como historial.")
    plantilla = pd.DataFrame([{"Día": "Lunes", "Inicio": "08:00", "Fin": "08:50", "Actividad": "Inglés", "Grupo": "2A", "Responsable": ""}])
    st.download_button("Descargar plantilla de horario", plantilla.to_csv(index=False).encode("utf-8-sig"), "Plantilla_horario_escolar.csv", "text/csv", key="plantilla_horario_apoyo")
    archivos = st.file_uploader(
        "Horarios de materias, docentes y otras maestras de apoyo",
        type=["xlsx", "xls", "csv"], accept_multiple_files=True, key="carga_restricciones_horario",
    )
    preparados = []
    errores = []
    for archivo in archivos or []:
        try:
            hojas_validas, avisos_hojas = _leer_archivo(archivo)
            preparados.extend(hojas_validas)
            errores.extend(f"{archivo.name} · {aviso}" for aviso in avisos_hojas)
        except Exception as exc:
            errores.append(f"{archivo.name}: {exc}")
    if errores:
        for error in errores:
            st.warning(error)
    if preparados:
        vista_carga = pd.concat([
            frame.assign(Archivo=origen) for origen, frame in preparados
        ], ignore_index=True)
        st.dataframe(vista_carga, hide_index=True, width="stretch")
        if st.button("Guardar horarios de referencia para esta escuela", type="primary", key="guardar_restricciones_horario"):
            try:
                total = 0
                for origen, frame in preparados:
                    _, cuenta = guardar_restricciones(escuela, nombre, origen, frame)
                    total += cuenta
                st.success(f"Se añadieron {total} bloques de referencia. Las versiones sustituidas permanecen en el historial.")
                st.rerun()
            except Exception as exc:
                st.error(f"No se pudieron guardar todos los horarios: {exc}. Los registros guardados se conservan; revisa el historial antes de reintentar.")

    if not restricciones.empty:
        st.markdown("#### Horarios de referencia activos")
        st.dataframe(_tabla_vista(restricciones), hide_index=True, width="stretch")
    if not horarios_equipo.empty:
        st.markdown("#### Horarios guardados de otras maestras de esta escuela")
        colegas = horarios_equipo.loc[horarios_equipo["Maestra"].astype(str).ne(nombre)].copy() if "Maestra" in horarios_equipo else horarios_equipo.iloc[0:0]
        if colegas.empty:
            st.caption("Aún no hay horarios de otras maestras disponibles.")
        else:
            colegas_opciones = sorted(colegas["Maestra"].dropna().astype(str).unique().tolist())
            colega = st.selectbox("Consultar horario de una colega", colegas_opciones, key=f"horario_colega_{normalizar_texto(escuela)}")
            st.dataframe(_tabla_vista(colegas.loc[colegas["Maestra"].astype(str).eq(colega)]), hide_index=True, width="stretch")

    st.divider()
    st.markdown("### Proponer mi horario semanal")
    c1, c2, c3 = st.columns(3)
    with c1:
        grupos_texto = st.text_input("Grados y grupos", placeholder="1A, 2A, 3B", key="horario_grupos")
        sesiones = st.number_input("Sesiones por grupo a la semana", min_value=1, max_value=10, value=2, key="horario_sesiones")
    with c2:
        hora_inicio = st.time_input("Inicio de la jornada", value=time(8, 0), key="horario_inicio")
        hora_fin = st.time_input("Fin de la jornada", value=time(13, 0), key="horario_fin")
    with c3:
        duracion = st.number_input("Duración de cada sesión (minutos)", min_value=15, max_value=180, value=50, step=5, key="horario_duracion")
        st.caption("La propuesta evita cruces con los horarios cargados y con sesiones de apoyo del mismo grupo.")

    proposal_key = f"propuesta_horario_apoyo_{normalizar_texto(nombre)}_{normalizar_texto(escuela)}"
    if st.button("Generar propuesta de horario", type="primary", key=f"generar_{proposal_key}"):
        try:
            grupos = [parte.strip() for parte in grupos_texto.split(",") if parte.strip()]
            propuesta, origen = proponer_horario(
                grupos, int(sesiones), int(duracion), hora_inicio, hora_fin,
                restricciones, horarios_equipo, maestra=nombre,
            )
            st.session_state[proposal_key] = propuesta
            st.session_state[proposal_key + "_origen"] = origen
        except Exception as exc:
            st.error(f"No se pudo proponer el horario: {exc}")

    propuesta = st.session_state.get(proposal_key)
    if propuesta is not None:
        st.info(f"Borrador: {st.session_state.get(proposal_key + '_origen', 'editable')}. Revisa y ajusta las sesiones antes de guardar.")
        version_editor = st.session_state.get(proposal_key + "_version", 0)
        editada = st.data_editor(
            propuesta,
            num_rows="dynamic", hide_index=True, width="stretch",
            column_config={
                "Dia": st.column_config.SelectboxColumn("Día", options=list(DIAS)),
                "Inicio": st.column_config.TextColumn("Inicio · HH:MM"),
                "Fin": st.column_config.TextColumn("Fin · HH:MM"),
                "Grupo": st.column_config.TextColumn("Grupo"),
                "Actividad": st.column_config.TextColumn("Actividad", width="large"),
                "Maestra": st.column_config.TextColumn("Maestra", disabled=True),
            },
            key=f"editor_horario_apoyo_{normalizar_texto(escuela)}_{version_editor}",
        )
        conflictos = detectar_choques(editada.to_dict("records"), restricciones, horarios_equipo)
        if not conflictos.empty:
            st.error("Hay cruces; corrígelos antes de guardar.")
            st.dataframe(conflictos, hide_index=True, width="stretch")
        if st.button("Guardar mi horario en la base central", type="primary", disabled=not conflictos.empty, key=f"guardar_{proposal_key}"):
            try:
                guardar_horario_apoyo(nombre, escuela, editada)
                st.success("Horario guardado. La versión anterior permanece en el historial.")
                st.session_state.pop(proposal_key, None)
                st.rerun()
            except Exception as exc:
                st.error(f"No se pudo guardar el horario: {exc}")

    propio = horarios_equipo.loc[horarios_equipo["Maestra"].astype(str).eq(nombre)].copy() if not horarios_equipo.empty and "Maestra" in horarios_equipo.columns else pd.DataFrame()
    if not propio.empty:
        st.markdown("### Mi horario guardado")
        st.dataframe(_tabla_vista(propio), hide_index=True, width="stretch")


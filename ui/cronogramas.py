"""Interfaz del generador mensual de cronogramas para el equipo especialista."""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from documents.cronogramas import generar_cronograma_pdf, guardar_pdf_drive
from services.cronogramas import (
    DIAS_INHABILES,
    cargar_agenda,
    cargar_agenda_global,
    fechas_habiles,
    guardar_agenda,
    perfil_especialista,
)
from services.horarios import avisar_maestras_apoyo


MESES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)
ESCUELA_JUNTA = "Junta General (Sede)"


def _mes_actual() -> date:
    return date.today().replace(day=1)


def _meses_disponibles():
    actual = _mes_actual()
    opciones = []
    for desplazamiento in range(-12, 19):
        numero = actual.year * 12 + actual.month - 1 + desplazamiento
        anio, mes_cero = divmod(numero, 12)
        mes = mes_cero + 1
        llave = f"{anio:04d}-{mes:02d}"
        opciones.append((llave, f"{MESES[mes - 1].capitalize()} {anio}"))
    return opciones


def _firma_drive(firma_id: str) -> bytes | None:
    if not firma_id:
        return None
    from data.google import drive_service
    return drive_service().files().get_media(fileId=firma_id).execute()


def _firma_drive_segura(firma_id: str) -> bytes | None:
    try:
        return _firma_drive(firma_id) if firma_id else None
    except Exception:
        return None


def _recursos_firma(perfil: dict):
    """Carga firmas opcionales de Drive sin incluir identificadores en el código fuente."""
    firmas = st.secrets.get("CRONOGRAMAS_FIRMAS", {})
    if isinstance(firmas, str):
        try:
            firmas = json.loads(firmas)
        except json.JSONDecodeError:
            firmas = {}
    clave = re.sub(r"[^A-Z0-9]+", "_", perfil["nombre"].upper()).strip("_")
    firma_id = str(firmas.get(perfil["nombre"], firmas.get(clave, ""))).strip() if hasattr(firmas, "get") else ""
    firma_especialista = _firma_drive_segura(firma_id)

    sello_id = str(st.secrets.get("CRONOGRAMAS_SELLO_ID", "")).strip()
    firma_direccion_id = str(st.secrets.get("CRONOGRAMAS_FIRMA_DIRECCION_ID", "")).strip()
    firma_direccion = _firma_drive_segura(firma_direccion_id)
    sello = _firma_drive_segura(sello_id)
    if firma_direccion is None:
        try:
            firma_direccion = (Path(__file__).resolve().parents[1] / "firma.png").read_bytes()
        except OSError:
            pass
    if sello is None:
        try:
            sello = (Path(__file__).resolve().parents[1] / "sello.png").read_bytes()
        except OSError:
            pass
    return firma_especialista, firma_direccion, sello


def cronogramas_page():
    nombre = str(st.session_state.get("nombre", "")).strip()
    rol = str(st.session_state.get("rol", "")).strip()
    perfil = perfil_especialista(nombre, rol)
    if not perfil:
        st.error("Este apartado es exclusivo para las cuentas autorizadas del equipo especialista y de Dirección.")
        return

    st.title("Cronograma mensual" if perfil["area"] != "Dirección" else "Cronograma de Dirección")
    st.caption(f"{perfil['nombre']} · {perfil['area']} · USAER 02-E")
    if perfil["area"] == "Dirección":
        st.write("Genera tu propio cronograma y consulta el calendario consolidado de todo el equipo. Al publicar, las maestras de apoyo de las escuelas incluidas reciben el aviso en Horarios de apoyo.")
    else:
        st.write("Selecciona una escuela y describe la actividad de cada día hábil. Las agendas anteriores se conservan al guardar una nueva versión.")

    meses = _meses_disponibles()
    llaves = [llave for llave, _ in meses]
    indice = llaves.index(_mes_actual().strftime("%Y-%m")) if _mes_actual().strftime("%Y-%m") in llaves else 12
    mes = st.selectbox(
        "Mes del cronograma",
        llaves,
        index=indice,
        format_func=lambda llave: next(etiqueta for valor, etiqueta in meses if valor == llave),
        key="cronograma_mes",
    )
    fechas = fechas_habiles(mes)
    editor_key = f"cronograma_editor_{perfil['nombre']}_{mes}"

    try:
        agenda_guardada = cargar_agenda(perfil["nombre"], mes)
    except Exception as exc:
        st.error(f"No se pudo leer el historial del cronograma: {exc}")
        st.info("El libro de Cronogramas debe estar compartido con la cuenta de servicio configurada en la plataforma.")
        return

    filas_iniciales = []
    for fecha in fechas:
        guardada = agenda_guardada.get(fecha.isoformat(), {})
        filas_iniciales.append({
            "Fecha": fecha,
            "Escuela": guardada.get("escuela", ""),
            "Actividad": guardada.get("actividad", ""),
        })
    editor_inicial = pd.DataFrame(filas_iniciales, columns=["Fecha", "Escuela", "Actividad"])
    opciones_escuela = [*perfil["escuelas"], ESCUELA_JUNTA]

    with st.form(f"form_cronograma_{perfil['nombre']}_{mes}"):
        tabla = st.data_editor(
            editor_inicial,
            key=editor_key,
            hide_index=True,
            num_rows="fixed",
            width="stretch",
            disabled=["Fecha"],
            column_config={
                "Fecha": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"),
                "Escuela": st.column_config.SelectboxColumn(
                    "Escuela", options=["", *opciones_escuela],
                    help="Solo aparecen las escuelas del ámbito asignado al especialista.",
                ),
                "Actividad": st.column_config.TextColumn(
                    "Actividad", width="large", help="Describe la actividad prevista para ese día.",
                ),
            },
        )
        enviar = st.form_submit_button("Guardar cronograma y generar PDF", type="primary", width="stretch")

    for iso, motivo in DIAS_INHABILES.items():
        if iso.startswith(mes):
            st.caption(f"{date.fromisoformat(iso).strftime('%d/%m/%Y')}: {motivo} (día excluido del calendario).")

    if enviar:
        agenda = []
        for _, fila in tabla.iterrows():
            fecha = fila.get("Fecha")
            escuela = "" if pd.isna(fila.get("Escuela")) else str(fila.get("Escuela", "")).strip()
            actividad = "" if pd.isna(fila.get("Actividad")) else str(fila.get("Actividad", "")).strip()
            agenda.append({
                "fecha": fecha.isoformat() if hasattr(fecha, "isoformat") else str(fecha),
                "escuela": escuela,
                "actividad": actividad,
            })
        try:
            with st.spinner("Guardando la agenda y preparando el PDF..."):
                resultado = guardar_agenda(perfil["nombre"], perfil["area"], mes, perfil["escuelas"], agenda)
                st.session_state["cronograma_publicacion_pendiente"] = {
                    "id": resultado.get("publicacion_id", ""),
                    "especialista": perfil["nombre"],
                    "mes": mes,
                    "agenda": agenda,
                }
                try:
                    notificadas = avisar_maestras_apoyo(
                        resultado.get("publicacion_id", ""), perfil["nombre"], mes, agenda
                    )
                    aviso_notificaciones = (
                        f"Se avisó a {notificadas} maestra(s) de apoyo."
                        if notificadas else
                        "El cronograma se guardó; no se encontraron cuentas de maestras de apoyo asignadas a esas escuelas."
                    )
                    st.session_state["cronograma_publicacion_pendiente"] = None
                except Exception as aviso_exc:
                    aviso_notificaciones = f"El cronograma se guardó, pero no se pudieron registrar los avisos: {aviso_exc}"
                filas_pdf = [
                    {"fecha": date.fromisoformat(item["fecha"]).strftime("%d/%m/%Y"),
                     "escuela": item["escuela"], "actividad": item["actividad"]}
                    for item in agenda
                    if item["escuela"].strip() and item["actividad"].strip()
                ]
                firma_esp, firma_dir, sello = _recursos_firma(perfil)
                pdf_bytes = generar_cronograma_pdf(
                    perfil, next(etiqueta for llave, etiqueta in meses if llave == mes),
                    filas_pdf, firma_esp, firma_dir, sello,
                )
                sello_tiempo = datetime.now(ZoneInfo("America/Mexico_City")).strftime("%Y%m%d_%H%M%S")
                nombre_archivo = f"Cronograma_{perfil['nombre']}_{mes}_{sello_tiempo}.pdf"
                st.session_state["cronograma_pdf"] = pdf_bytes
                st.session_state["cronograma_pdf_nombre"] = nombre_archivo
                st.session_state["cronograma_pdf_mes"] = mes
                st.session_state["cronograma_pdf_firma_especialista"] = bool(
                    firma_esp or (perfil["area"] == "Dirección" and firma_dir)
                )
                st.session_state["cronograma_pdf_mensaje"] = f"Cronograma guardado: {resultado['filas']} actividades."
                st.session_state["cronograma_pdf_aviso_historial"] = resultado.get("aviso", "")
                st.session_state["cronograma_pdf_aviso_notificaciones"] = aviso_notificaciones
                st.session_state["cronograma_pdf_drive_url"] = ""
                st.session_state["cronograma_pdf_drive_aviso"] = ""
                try:
                    st.session_state["cronograma_pdf_drive_url"] = guardar_pdf_drive(pdf_bytes, nombre_archivo)
                except Exception as drive_exc:
                    st.session_state["cronograma_pdf_drive_aviso"] = (
                        "La agenda quedó guardada y el PDF está listo para descargar, "
                        f"pero no se guardó en Drive: {drive_exc}"
                    )
            st.rerun()
        except Exception as exc:
            st.error(f"No se pudo completar el guardado del cronograma: {exc}")

    if st.session_state.get("cronograma_pdf"):
        st.success(st.session_state.get("cronograma_pdf_mensaje", "PDF generado."))
        if not st.session_state.get("cronograma_pdf_firma_especialista"):
            st.warning(
                "No está configurada la imagen de firma personal de esta cuenta. "
                "El PDF conserva el espacio para firma; el visto bueno y el sello se agregan "
                "si sus imágenes están disponibles en la configuración."
            )
        if st.session_state.get("cronograma_pdf_aviso_historial"):
            st.warning(st.session_state["cronograma_pdf_aviso_historial"])
        if st.session_state.get("cronograma_pdf_aviso_notificaciones"):
            st.info(st.session_state["cronograma_pdf_aviso_notificaciones"])
        pendiente = st.session_state.get("cronograma_publicacion_pendiente")
        if pendiente and pendiente.get("especialista") == perfil["nombre"]:
            if st.button("Reintentar aviso a maestras de apoyo", key="reintentar_aviso_cronograma"):
                try:
                    notificadas = avisar_maestras_apoyo(
                        pendiente["id"], pendiente["especialista"], pendiente["mes"], pendiente["agenda"]
                    )
                    st.session_state["cronograma_pdf_aviso_notificaciones"] = f"Aviso registrado para {notificadas} maestra(s) de apoyo."
                    st.session_state["cronograma_publicacion_pendiente"] = None
                    st.rerun()
                except Exception as exc:
                    st.error(f"No fue posible registrar los avisos: {exc}")
        if st.session_state.get("cronograma_pdf_drive_aviso"):
            st.warning(st.session_state["cronograma_pdf_drive_aviso"])
        st.download_button(
            "Descargar PDF oficial",
            data=st.session_state["cronograma_pdf"],
            file_name=st.session_state.get("cronograma_pdf_nombre", "Cronograma.pdf"),
            mime="application/pdf",
            type="primary",
            width="stretch",
        )
        drive_url = st.session_state.get("cronograma_pdf_drive_url", "")
        if drive_url:
            st.markdown(f"[Abrir copia guardada en Drive]({drive_url})")

    with st.expander("Calendario de todo el equipo", expanded=perfil["area"] == "Dirección"):
        st.caption("Consulta las actividades publicadas por especialistas y Dirección para el mes seleccionado.")
        if st.button("Consultar agenda global del mes", key="consultar_agenda_global"):
            try:
                global_rows = cargar_agenda_global(mes)
                st.session_state["cronograma_global"] = global_rows
                st.session_state["cronograma_global_mes"] = mes
            except Exception as exc:
                st.error(f"No se pudo consultar el calendario global: {exc}")
        if st.session_state.get("cronograma_global_mes") == mes:
            global_rows = st.session_state.get("cronograma_global", [])
            if global_rows:
                vista = pd.DataFrame(global_rows)
                vista["Fecha"] = pd.to_datetime(vista["Fecha"]).dt.strftime("%d/%m/%Y")
                st.dataframe(vista, hide_index=True, width="stretch")
            else:
                st.info("No hay actividades guardadas para este mes.")


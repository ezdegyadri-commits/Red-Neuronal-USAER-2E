"""Calendario informativo compartido y publicación exclusiva de Dirección."""
import calendar
from datetime import date, datetime
from zoneinfo import ZoneInfo
from uuid import uuid4

import streamlit as st

from services.calendario_eventos import cargar_eventos, calendario_base, guardar_evento
from services.cronogramas import perfil_especialista


def eventos_mes(mes):
    try:
        return cargar_eventos(mes)
    except Exception:
        # Las actividades oficiales siguen disponibles si falla la base central.
        st.caption("Los eventos nuevos de Dirección no están disponibles por ahora.")
        return [e for e in calendario_base()["eventos"] if e["Fecha"].startswith(mes + "-")]


def ventana_eventos(fecha, eventos):
    items = [e for e in eventos if e["Fecha"] == fecha]
    if not items:
        return
    with st.popover(f"📌 {len(items)} aviso{'s' if len(items) != 1 else ''}", width="stretch"):
        st.caption(date.fromisoformat(fecha).strftime("%d/%m/%Y") + " · Informativo, no bloquea tu planeación")
        for e in items:
            st.write(e["Titulo"])
            if e.get("Origen") == "SEGEY":
                st.caption("SEGEY · Dirección de Educación Especial")
            elif e.get("Detalle"):
                st.caption(e["Detalle"])


def pendientes_mes(mes):
    for e in calendario_base().get("pendientes", []):
        if e["mes"] == mes:
            st.caption(f"Por definir: {e['titulo']} (sin fecha asignada).")


def calendario_informativo(mes):
    st.markdown("#### Actividades del mes · USAER")
    st.caption("Abre los avisos del día para ver los detalles. No modifican tu horario.")
    eventos = eventos_mes(mes)
    anio, numero = map(int, mes.split("-"))
    for col, nombre in zip(st.columns(7), ("Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb")):
        col.caption(nombre)
    for semana in calendar.Calendar(firstweekday=6).monthdatescalendar(anio, numero):
        for col, fecha in zip(st.columns(7), semana):
            with col:
                with st.container(border=True):
                    if fecha.month == numero:
                        st.write(str(fecha.day))
                        ventana_eventos(fecha.isoformat(), eventos)
                    else:
                        st.caption("—")
    pendientes_mes(mes)


def eventos_direccion():
    perfil = perfil_especialista(st.session_state.get("nombre", ""), st.session_state.get("rol", ""))
    if not perfil or perfil["area"] != "Dirección":
        st.error("Apartado exclusivo de Dirección.")
        return
    st.subheader("Publicar actividades para todo el equipo")
    st.caption("Visibles para especialistas y maestras de apoyo. Son avisos informativos, no bloqueos.")
    hoy = datetime.now(ZoneInfo("America/Mexico_City")).date()
    mes_fecha = st.date_input("Mes de actividades", value=hoy.replace(day=1), key="eventos_director_mes")
    mes = mes_fecha.strftime("%Y-%m")
    try:
        eventos = cargar_eventos(mes)
    except Exception:
        st.info("No se pudieron consultar los eventos. Reintenta en un momento.")
        return
    seleccionado = st.selectbox("Añadir o actualizar", [None, *eventos],
        format_func=lambda e: "Nueva actividad" if e is None else f"{e['Fecha'][8:]} · {e['Titulo']}",
        key="evento_director_elegido")
    identificador = seleccionado["ID_Evento"] if seleccionado else st.session_state.setdefault("evento_director_nuevo_id", uuid4().hex)
    version = seleccionado.get("Revision", "base") if seleccionado else "nuevo"
    with st.form(f"publicar_evento_{identificador}_{version}"):
        fecha = st.date_input("Fecha de la actividad", value=date.fromisoformat(seleccionado["Fecha"]) if seleccionado else mes_fecha)
        titulo = st.text_input("Actividad", value=seleccionado["Titulo"] if seleccionado else "", max_chars=300)
        detalle = st.text_area("Detalles (opcional)", value=seleccionado.get("Detalle", "") if seleccionado else "", max_chars=3000)
        publicar = st.form_submit_button("Publicar actividad para todos", type="primary", width="stretch")
    if publicar:
        try:
            guardar_evento(fecha, titulo, detalle, identificador, seleccionado.get("Revision", "base") if seleccionado else None)
            st.session_state.pop("evento_director_nuevo_id", None)
            st.success("Actividad publicada para todo el equipo.")
        except (ValueError, PermissionError) as exc:
            st.info(str(exc))
        except Exception:
            st.error("No se pudo publicar la actividad. Inténtalo de nuevo.")
    calendario_informativo(mes)

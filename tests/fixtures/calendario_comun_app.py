from types import SimpleNamespace
from unittest.mock import patch

import streamlit as st

from services import calendario_eventos as eventos, cronogramas
from ui.calendario_eventos import eventos_direccion, calendario_informativo
from ui.cronogramas import _calendario_mes
from ui import horarios_apoyo as apoyo

st.set_page_config(layout="wide")
modo = st.radio("Perfil de prueba", ["Dirección", "Especialista", "Apoyo"])
st.session_state.setdefault("eventos_simulados", [])


def anexar(rows, **kwargs):
    for row in rows:
        st.session_state["eventos_simulados"].append(dict(zip(eventos.HEADERS, row)))


ws = SimpleNamespace(row_values=lambda n: eventos.HEADERS, append_rows=anexar)
visitas = [
    {"Fecha": "2026-10-02", "Especialista": "María José Cupul Realpozo", "Área": "Psicología", "Escuela": "Ichcaanziho", "Actividad": "Evaluación"},
    {"Fecha": "2026-10-03", "Especialista": "Abril de María Chable Ríos", "Área": "Psicología", "Escuela": "Domingo Solís Rodríguez", "Actividad": "No mostrar"},
]
with patch.object(eventos, "_eventos_guardados", side_effect=lambda: st.session_state["eventos_simulados"]), \
     patch.object(eventos, "ensure_headers", return_value=ws), \
     patch.object(cronogramas, "cargar_visitas_escuela", return_value=visitas), \
     patch.object(apoyo, "cargar_avisos_apoyo", return_value=[]):
    if modo == "Dirección":
        st.session_state["nombre"] = "Psic. Edgar Adrián Yam Briceño MD"
        st.session_state["rol"] = "DIRECTOR"
        perfil = cronogramas.perfil_especialista(st.session_state["nombre"], st.session_state["rol"])
        _calendario_mes("2026-10", {}, perfil["escuelas"], "director_prueba", lugares=cronogramas.lugares_cronograma(perfil))
        eventos_direccion()
    elif modo == "Especialista":
        st.session_state["nombre"] = "Abril de María Chable Ríos"
        st.session_state["rol"] = "Psicología"
        _calendario_mes("2026-10", {}, ["Gregorio Torres Quintero"], "especialista_prueba")
    else:
        st.session_state["nombre"] = "Marycruz Caamal Coral"
        st.session_state["rol"] = "APOYO"
        apoyo._avisos_maestra(st.session_state["nombre"], "Ichcaanziho")

from types import SimpleNamespace
from unittest.mock import patch

import streamlit as st

from services import calendario_eventos as eventos, cronogramas
from ui.calendario_eventos import eventos_direccion, calendario_informativo
from ui import calendario_eventos as ui_eventos
from ui.cronogramas import _calendario_mes
from ui import horarios_apoyo as apoyo

st.set_page_config(layout="wide")
modo = st.radio("Perfil de prueba", ["Dirección", "Especialista", "Apoyo"])
st.session_state['autenticado']=True
st.session_state.setdefault("eventos_simulados", [])


def anexar(rows, **kwargs):
    for row in rows:
        st.session_state["eventos_simulados"].append(dict(zip(eventos.HEADERS, row)))


ws = SimpleNamespace(row_values=lambda n: eventos.HEADERS, append_rows=anexar)
visitas = [
    {"Fecha": "2026-10-02", "Especialista": "Especialista ficticio", "Área": "Psicología", "Escuela": "Escuela ficticia 1", "Actividad": "Evaluación ficticia"},
    {"Fecha": "2026-10-03", "Especialista": "Otro especialista ficticio", "Área": "Psicología", "Escuela": "Escuela ficticia 2", "Actividad": "No mostrar"},
]
def perfil_mock(nombre,rol):
    area='Dirección' if rol=='DIRECTOR' else 'Psicología'
    return {'nombre':nombre,'area':area,'escuelas':['Escuela ficticia '+str(i) for i in range(1,9 if rol=='DIRECTOR' else 5)]}
def resumir_mock(rows,escuela):
    return [{'Fecha':'02/10/2026','Día':'Viernes','Especialista':r['Especialista'],'Área':r['Área'],'Actividad':r['Actividad']} for r in rows if r['Escuela']==escuela]
with patch.object(eventos, "_eventos_guardados", side_effect=lambda: st.session_state["eventos_simulados"]), \
     patch.object(eventos, "ensure_headers", return_value=ws), \
     patch.object(cronogramas, "cargar_visitas_escuela", return_value=visitas), \
     patch.object(apoyo, "cargar_avisos_apoyo", return_value=[]), \
     patch.object(cronogramas,'perfil_especialista',side_effect=perfil_mock), \
     patch.object(eventos,'perfil_especialista',side_effect=perfil_mock), \
     patch.object(ui_eventos,'perfil_especialista',side_effect=perfil_mock), \
     patch.object(cronogramas,'resumir_visitas_escuela',side_effect=resumir_mock):
    if modo == "Dirección":
        st.session_state["nombre"] = "Director ficticio"
        st.session_state["rol"] = "DIRECTOR"
        perfil = cronogramas.perfil_especialista(st.session_state["nombre"], st.session_state["rol"])
        _calendario_mes("2026-10", {}, perfil["escuelas"], "director_prueba", lugares=cronogramas.lugares_cronograma(perfil))
        eventos_direccion()
    elif modo == "Especialista":
        st.session_state["nombre"] = "Especialista ficticio"
        st.session_state["rol"] = "Psicología"
        _calendario_mes("2026-10", {}, ["Escuela ficticia 1"], "especialista_prueba")
    else:
        st.session_state["nombre"] = "Docente ficticia"
        st.session_state["rol"] = "APOYO"
        apoyo._avisos_maestra(st.session_state["nombre"], "Escuela ficticia 1")

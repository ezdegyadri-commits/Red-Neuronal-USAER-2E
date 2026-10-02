from unittest.mock import patch
import streamlit as st
from ui import cronogramas as ui

st.session_state["nombre"] = "María José Cupul Realpozo"
st.session_state["rol"] = "Psicología"
with patch.object(ui, "cargar_agenda", return_value={}), \
     patch.object(ui, "meses_con_cronograma", return_value=[]), \
     patch.object(ui, "cargar_agenda_global", return_value=[]):
    ui.cronogramas_page()

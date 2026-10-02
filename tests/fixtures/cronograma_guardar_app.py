from unittest.mock import patch
import streamlit as st
from ui import cronogramas as ui

st.session_state["nombre"] = "Abril de María Chable Ríos"
st.session_state["rol"] = "Psicología"
st.session_state.setdefault("cronograma_pdf_drive_aviso", "invalid_grant")
saved = {"2026-10-01": {"escuela": "Gregorio Torres Quintero", "actividad": "Acompañamiento"}}
with patch.object(ui, "cargar_agenda", return_value=saved), \
     patch.object(ui, "cargar_agenda_global", return_value=[{"Especialista": st.session_state["nombre"], "ID_Publicacion": "actual"}]), \
     patch.object(ui, "guardar_agenda", return_value={"filas": 1, "publicacion_id": "actual"}), \
     patch.object(ui, "avisar_maestras_apoyo", return_value=2), \
     patch.object(ui, "_recursos_firma", return_value=(b"firma", None, None)), \
     patch.object(ui, "_perfil_profesional", side_effect=lambda p: p), \
     patch.object(ui, "generar_cronograma_pdf", return_value=b"%PDF-test"):
    ui.cronogramas_page()

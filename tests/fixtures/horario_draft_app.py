import pandas as pd
import streamlit as st
from ui.horarios_apoyo import _cuadricula_horario

st.session_state.setdefault("nombre", "Marycruz")
st.session_state.setdefault("rol", "APOYO")
_cuadricula_horario("Marycruz", "Ichcaanziho", pd.DataFrame(), pd.DataFrame())

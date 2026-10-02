import streamlit as st
from ui.cronogramas import _calendario_mes

with st.form("calendar"):
    _calendario_mes("2026-10", {}, ["Ichcaanziho"], "test")
    st.form_submit_button("Guardar")

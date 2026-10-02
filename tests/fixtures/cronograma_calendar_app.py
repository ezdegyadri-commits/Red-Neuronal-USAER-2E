import streamlit as st
from ui.cronogramas import _calendario_mes

agenda = _calendario_mes("2026-10", {}, ["Ichcaanziho"], "test")
st.json(agenda)

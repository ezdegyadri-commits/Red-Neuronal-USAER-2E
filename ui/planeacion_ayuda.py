"""Guías públicas del producto, sin datos de alumnos ni lecturas externas."""
from pathlib import Path
import streamlit as st

def panel(area):
    nombre='guia_planeacion_apoyo.md' if area=='Aprendizaje' else 'guia_planeacion_paradocente.md'
    path=Path(__file__).resolve().parents[1]/'docs'/nombre
    try:contenido=path.read_text(encoding='utf-8')
    except OSError:
        st.info('La guía no está disponible en este momento. Tu planeación se conserva.');return
    with st.expander('Guía paso a paso · Mi formato',expanded=True):
        st.markdown(contenido)
        st.download_button('Descargar guía para compartir',contenido,file_name=nombre,mime='text/markdown',key='guia_planeacion_'+area)

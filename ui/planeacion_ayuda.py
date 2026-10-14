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
        guia_pdf = Path(__file__).resolve().parents[1]/'docs'/'Guia_Rapida_Planeacion_USAER_02E.pdf'
        if guia_pdf.exists():
            st.download_button('Guía rápida de la vista anterior (PDF)',
                               guia_pdf.read_bytes(),
                               file_name='Guia_Rapida_Planeacion_USAER_02E.pdf',
                               mime='application/pdf',
                               key='guia_pdf_'+area,
                               type='primary')
            st.caption('El PDF describe el recorrido anterior, que sigue disponible. Las instrucciones del formato vivo se encuentran a continuación y en la descarga de texto.')
        st.markdown(contenido)
        st.download_button('Descargar guía en texto (.md)',contenido,file_name=nombre,mime='text/markdown',key='guia_planeacion_'+area)

"""QA nativa local: sin credenciales, sin red institucional y sin datos de alumnos."""
from unittest.mock import patch
import streamlit as st
from tests.test_planeacion_completa import documento
from services import planeacion_papel as papel
from ui.planeacion_papel import editor
from tests.test_sintesis_nee_movimiento_interno import fuente

st.set_page_config(layout='wide',page_title='QA · NEE de EPP')
st.caption('PRUEBA LOCAL · SOLO DATOS FICTICIOS · NO MODIFICA LA PLATAFORMA')
if 'qa_doc' not in st.session_state:
    d=documento()
    d['metadatos'].update(modalidad_planeacion='individual',fuentes=[fuente('A1')])
    d['tablas']['aprendizajes']=[{'Necesidades educativas específicas':'Texto previo que debe conservarse.',
                                'Aprendizaje y/u objetivo':'','Descriptor de logro':'','_fila_manual':True}]
    st.session_state.qa_doc=d


def recibir(event):
    with patch.object(papel.s,'autorizar',return_value={'area':'Aprendizaje','cuenta':'cuenta-ficticia','director':False}):
        st.session_state.qa_doc=papel.aplicar(st.session_state.qa_doc,event)
    st.session_state.qa_nonce=event['nonce']


with patch.object(papel.s,'autorizar',return_value={'area':'Aprendizaje','cuenta':'cuenta-ficticia','director':False}):
    spec=papel.hoja(st.session_state.qa_doc)
editor(key='qa_nee_native',hoja=spec,guardado='PRUEBA LOCAL',aceptado_nonce=st.session_state.get('qa_nonce'),on_edicion=recibir)

"""Comprobación visual local: solo memoria y datos ficticios; sin repositorios."""
from pathlib import Path
from copy import deepcopy
import streamlit as st
import streamlit.components.v1 as components
from services import planeacion as s,planeacion_papel as papel
from services.planeacion_limpieza import normalizar
from tests.test_planeacion_completa import documento

st.set_page_config(layout='wide')
s.autorizar=lambda *a,**k:{'cuenta':'cuenta-ficticia'}
s.identidad=lambda:{'cuenta':'cuenta-ficticia'}
if 'doc' not in st.session_state:
    d=documento();d['metadatos']['modalidad_planeacion']='individual'
    d['datos']['Alumnos'][0]['NEE registrada']='Necesita fortalecer la atención sostenida.'
    d['tablas']['aprendizajes']=[{'Necesidades educativas específicas':'[III · E1] BAP_Fisicas: {"Item_1":{"pregunta":"Pregunta ficticia","frecuencia":"Siempre"}}','Aprendizaje y/u objetivo':'','Descriptor de logro':''}]
    st.session_state.doc=normalizar(d);st.session_state.historia=[]
def guardar(d,estado='BORRADOR'):
    nuevo=deepcopy(d);nuevo['estado']=estado
    st.session_state.historia.append(nuevo);st.session_state.doc=nuevo
    return nuevo
s.guardar=guardar
st.caption('DEMOSTRACIÓN · ALUMNOS FICTICIOS · SIN BASE DE DATOS')
editor=components.declare_component('qa_planeacion_clara',path=str(Path(__file__).parents[1]/'ui'/'planeacion_papel_component'))
event=editor(hoja=papel.hoja(st.session_state.doc),aceptado=st.session_state.pop('aceptado',False),key='hoja',default=None)
if event and event['nonce']!=st.session_state.get('ultimo'):
    st.session_state.doc=papel.aplicar(st.session_state.doc,event)
    st.session_state.ultimo=event['nonce'];st.session_state.aceptado=True
    if event['accion']=='corregir':st.info('Destino solicitado: '+event['panel'])
    st.rerun()
from ui.planeacion_borradores import controles
from documents.planeacion_papel import generar_pdf
controles('demo',st.session_state.doc,generar_pdf,lambda:st.session_state.pop('doc',None))

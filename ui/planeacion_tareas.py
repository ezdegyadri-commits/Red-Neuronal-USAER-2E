"""Propuestas desacopladas: la espera de IA no mantiene ocupado el evento UI."""
import streamlit as st
from ai.documento_json import enviar


def _generar(solicitud,doc,config):
    from ai.planeacion import conexion_trabajo
    from ai.planeacion_completa import generar_completa
    with conexion_trabajo(config):
        return generar_completa(solicitud['resumen'],doc['formato'],doc['datos']['Función'],solicitud['contexto'],solicitud['ajustes'],solicitud['aliases'],solicitud['evidencias'])


def iniciar(prefix,solicitud,doc):
    from ai.planeacion import configuracion_trabajo
    from services import planeacion as s
    from services.planeacion_edicion import huella
    s.autorizar(doc,True)
    key=prefix+'_ia_trabajo'
    if key in st.session_state:return
    st.session_state[key]={'future':enviar(_generar,solicitud,doc,configuracion_trabajo()),'solicitud':solicitud,
        'cuenta':s.identidad()['cuenta'],'documento':doc['id'],'huella':huella(st.session_state[prefix+'_doc']),'revision':doc.get('revision','')}


def recoger(prefix,doc):
    from services import planeacion as s
    key=prefix+'_ia_trabajo';job=st.session_state.get(key)
    if not job or not job['future'].done():return None
    if (job['cuenta'],job['documento'])!=(s.identidad()['cuenta'],doc['id']):return None
    st.session_state.pop(key,None)
    return {**job,'respuesta':job['future'].result()}


@st.fragment(run_every=2)
def estado(prefix):
    job=st.session_state.get(prefix+'_ia_trabajo')
    if not job:return
    from services import planeacion as s
    if job['cuenta']!=s.identidad()['cuenta']:return
    if job['future'].done():st.rerun(scope='app')
    st.status('Preparando actividades con las evidencias revisadas. Puedes seguir editando; la respuesta llegará como propuesta.',state='running')

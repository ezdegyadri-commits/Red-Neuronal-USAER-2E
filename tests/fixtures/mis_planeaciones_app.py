"""Demostración aislada de navegación: datos ficticios y sin conexión a Google."""
from copy import deepcopy
from unittest.mock import patch
import pandas as pd
import streamlit as st
from services import planeacion as s
from tests.test_planeacion_panel import documento,ACTOR,ALUMNO
from ui import planeacion as u
from ui import mis_planeaciones as ui

st.set_page_config(layout='wide')
st.session_state.update(autenticado=True,usuario=ACTOR['cuenta'],nombre=ACTOR['nombre'],rol=ACTOR['rol'],escuelas_permitidas='E1')
docs=[]
for i in range(3):
    d=documento('XXI' if i==2 and st.session_state.get('qa_pi') else 'XXIII');d['id']='ficticio-'+str(i);d['revision']='r'+str(i)
    d['guardado_en']='2026-10-28T10:00:0'+str(i)
    d['datos']['Alumnos'][0]['Nombre del alumno']='ALUMNO FICTICIO '+str(i)
    d['metadatos']['modalidad_planeacion']='individual'
    if i==2:
        d['cuenta']='apoyo-otro'
        if d['formato']!='XXI':d['metadatos'].update(modalidad_planeacion='grupal',vista_formato='guia')
    if d['id'] in st.session_state.get('qa_eliminados',[]):d['metadatos']['borrador_eliminado']=True
    docs.append(d)

actor={**ACTOR,'area':'Comunicación'} if st.session_state.get('qa_especialista') else ACTOR

def abrir(prefix,doc):
    st.session_state[prefix+'_doc']=deepcopy(doc)
    st.session_state[prefix+'_pending']=False

def autorizado(doc,*_,**__):
    if doc['id'] not in {d['id'] for d in docs}:raise PermissionError('Fuera del entorno ficticio')
    return actor

def renderer(prefix):
    st.write('EDITOR '+st.session_state[prefix+'_doc']['id'])
    if st.button('Añadir texto ficticio pendiente',key='qa_editar'):
        st.session_state[prefix+'_doc']['textos']['Evaluación']='TEXTO PENDIENTE PROTEGIDO'
        st.session_state[prefix+'_pending']=True

def eliminar(doc):
    st.session_state['qa_eliminados']=st.session_state.get('qa_eliminados',[])+[doc['id']]


def renderer_equipo(prefix,doc):st.write('EDITOR COMPARTIDO '+doc['id'])

with patch.object(s,'identidad',return_value=actor),patch.object(s,'padron_autorizado',return_value=pd.DataFrame([ALUMNO])),\
     patch.object(s,'listar',return_value=deepcopy(docs[:2])),patch.object(s,'compartidos',return_value=[deepcopy(docs[2])]),\
     patch.object(s,'eliminar_borrador',side_effect=eliminar),patch.object(s,'autorizar',side_effect=autorizado),patch.object(u,'_prefix',return_value='planeacion_qa'),\
     patch.object(u,'_open',side_effect=abrir),patch('documents.planeacion_papel.preparar_descarga',return_value=lambda:b'PDF ficticio'),\
     patch('ui.planeacion_anexo_compartido.panel',side_effect=renderer_equipo),\
     patch('ui.planeacion_pendientes.panel'),patch('ui.guardado_asincrono.acuses'),\
     patch('ui.planeacion_simple._recuperar'),patch('ui.planeacion_borradores.papelera'):
    if st.session_state.get('qa_inicio') and st.session_state.get('navegacion_principal')!='Planeación e intervención':ui.inicio()
    else:ui.pagina(renderer)

"""Demostración local de colaboración. Sin credenciales, Sheets, Drive ni IA."""
from copy import deepcopy
import streamlit as st
import pandas as pd
from tests.test_planeacion_acceso_equipo import grupal
from tests.test_planeacion_panel import ACTOR, ALUMNO
from services import planeacion as s
from services.planeacion_colaboracion import aportar
from ui import planeacion_viva as ui

st.set_page_config(layout='wide')
st.caption('PRUEBA AISLADA · TODOS LOS DATOS SON FICTICIOS · SIN BASE DE DATOS')
area=st.selectbox('Perfil de prueba',['Comunicación','Psicología','Trabajo Social','Aprendizaje'])
fallo=st.checkbox('Simular fallo de guardado')
actor={**ACTOR,'area':area,'cuenta':'cuenta-'+area}
st.session_state.update(autenticado=True,usuario=actor['cuenta'],nombre='Profesional ficticio',rol=area)
if 'f_docs' not in st.session_state:
    d=grupal();d.update(guardado_en='2026-10-19T10:00:00-06:00',revision='ficticia-1')
    d['datos']['Alumnos'][0]['Grupo']=''
    st.session_state['f_docs']=[d]
s.identidad=lambda:actor
s.autorizar=lambda *a,**k:actor
s.compartidos=lambda documento=None:deepcopy(st.session_state['f_docs'])
s.padron_autorizado=lambda:pd.DataFrame([ALUMNO])
s.listar=lambda *a:[]
s.refrescar=lambda:None
def guardar(doc,filas,obs):
    if fallo:raise RuntimeError('Fallo simulado: tu aportación sigue pendiente.')
    nuevo=aportar(st.session_state['f_docs'][0],actor,filas,obs)
    nuevo['guardado_en']='guardado-ficticio-confirmado'
    st.session_state['f_docs']=[nuevo]
    return deepcopy(nuevo)
s.guardar_aportacion=guardar
from ui import planeacion as u
st.session_state.setdefault(u._prefix()+'_submodulo','equipo')
ui.pagina()

"""Prueba local de reutilización: proveedor y guardado ficticios."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from copy import deepcopy
import streamlit as st
import ui.planeacion as u

u.servicio.identidad=lambda: {'director':False,'cuenta':'ficticia'}
if 'p_doc' not in st.session_state:
    st.session_state['p_doc']={'formato':'XXIII','datos':{'Función':'Aprendizaje','Alumnos':[]},
        'metadatos':{'resumen_educativo':'','Propuestas IA revisadas':[]},
        'tablas':{'aprendizajes':[],'dosificacion':[]}}
    st.session_state['p_generation']=1
    st.session_state['calls']=0

def generar(*args,**kwargs):
    st.session_state['calls']+=1
    return {'observaciones':'Propuesta ficticia para revisar el flujo.','faltantes':[],
        'propuestas':[{'necesidad':'Participación documentada','objetivo':'El alumno participa con apoyo visual.',
            'descriptor':'Se observa su participación.','actividad':'1. Presentar tarjetas. 2. Elegir. 3. Compartir.',
            'contexto':'Aula','temporalidad':'Sesión propuesta de 15 minutos','recursos':'Tarjetas',
            'evaluacion':'Observar la respuesta.','fundamento':'Apoyo a la participación.',
            'fuentes':['SEGEY-USAER'],'referentes':[]}]}

def guardar(prefix,**kwargs):
    st.session_state['saved']=deepcopy(st.session_state[prefix+'_doc'])
    st.session_state[prefix+'_pending']=False
    return True

u.proponer=generar
u._persist=guardar
if st.button('Volver a abrir el borrador') and 'saved' in st.session_state:
    u._open('p',st.session_state['saved'])
u._ai('p',st.session_state['p_doc'])
st.metric('Solicitudes ficticias',st.session_state['calls'])

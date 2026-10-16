"""Prueba visual del editor v2: memoria ficticia, sin Sheets, Drive ni IA."""
from copy import deepcopy
from datetime import date
import streamlit as st
from services import planeacion as servicio,planeacion_papel as papel
from services.planeacion_modelo import crear_plantilla
from ui.planeacion_papel import editor

st.set_page_config(layout='wide')
st.caption('PRUEBA AISLADA · DATOS FICTICIOS · SIN BASE DE DATOS')
modo=st.radio('Formato de prueba',['Individual','Grupal'],horizontal=True)
fallo=st.toggle('Simular fallo de guardado')
actor={'cuenta':'cuenta-ficticia','area':'Aprendizaje','director':False}
servicio.autorizar=lambda *a,**k:actor
servicio.identidad=lambda:actor
key='prueba_'+modo
if key not in st.session_state:
    alumno={'ID_Alumno':'F1','Nombre_Completo':'Alumno ficticio','ID_Escuela':'E1','Nombre_Escuela':'Escuela ficticia',
            'Grado':'5°','Grupo':'A','Situacion_Alumno':'RI','ID_Maestro_Regular':'Docente ficticio'}
    doc=crear_plantilla('XXIII',['F1'],[alumno],autor='Maestra ficticia',funcion='Aprendizaje',fecha=date(2026,10,15))
    doc.update(id=key,cuenta=actor['cuenta'],revision='inicial',guardado_en='confirmado-ficticio')
    doc['metadatos'].update(modalidad_planeacion=modo.lower(),vista_formato='guia' if modo=='Grupal' else 'trimestral')
    doc['tablas']['aprendizajes']=[{'Necesidades educativas específicas':'Requiere apoyos visuales para comprender consignas.',
        'Aprendizaje y/u objetivo':'Comprende una consigna breve con apoyos.','Descriptor de logro':'Realiza dos pasos con apoyo visual.'}]
    doc['tablas']['dosificacion']=[{'Contextos':'Aula regular','Actividades':'Actividad ficticia con tarjetas.',
        'Temporalidad':'Una sesión','Recursos':'Tarjetas'}]
    st.session_state[key]={'doc':doc,'nonce':'','versiones':0,'pendiente':False}
state=st.session_state[key]
if state['pendiente'] and not fallo:
    state['pendiente']=False;state['versiones']+=1;state['doc']['guardado_en']='confirmado-ficticio-'+str(state['versiones'])
st.caption('Versiones ficticias confirmadas: '+str(state['versiones']))
event=editor(key=key+'_editor',hoja=papel.hoja(state['doc']),aceptado_nonce=state['nonce'],
             guardado='' if state['pendiente'] else state['doc'].get('guardado_en',''))
if event and event.get('nonce')!=state['nonce']:
    state['doc']=deepcopy(papel.aplicar(state['doc'],event));state['nonce']=event['nonce']
    state['pendiente']=fallo
    if not fallo:
        state['versiones']+=1;state['doc']['guardado_en']='confirmado-ficticio-'+str(state['versiones'])
    st.rerun()

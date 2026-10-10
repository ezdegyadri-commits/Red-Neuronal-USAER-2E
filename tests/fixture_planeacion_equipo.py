"""Entorno aislado de revisión, sin conexión a datos reales ni IA."""
from copy import deepcopy
import streamlit as st
import pandas as pd
from services import planeacion as s
from ui.planeacion import _planeacion_page_clasica as planeacion_page
st.set_page_config(layout='wide')
area=st.selectbox('Perfil de demostración',['Psicología','Comunicación','Trabajo Social','Dirección'])
actor={'cuenta':'demo-'+area,'nombre':'Autor de demostración','director':area=='Dirección','area':area,'rol':area,'perfil':{'area':area,'escuelas':['Escuela de demostración']}}
st.session_state.update(autenticado=True,usuario=actor['cuenta'],nombre=actor['nombre'],rol=area)
alumno={'ID_Alumno':'A1','Nombre_Completo':'Alumno de demostración','ID_Escuela':'E1','Nombre_Escuela':'Escuela de demostración','CCT_Escuela':'TEST','Grado':'3','Grupo':'A','Tipo_Atencion':'Grupal'}
s.identidad=lambda:actor
s.padron_autorizado=lambda:pd.DataFrame([alumno])
s.repo.escuelas=lambda:pd.DataFrame([{'ID_Escuela':'E1','Nombre_Escuela':'Escuela de demostración','CCT':'TEST'}])
s.evidencias=lambda doc:([],[])
if 'versiones_demo' not in st.session_state:st.session_state.versiones_demo=[]
def listar(todas=False):
    docs=st.session_state.versiones_demo
    docs=[d for d in docs if actor['director'] or d['cuenta']==actor['cuenta']]
    return docs if todas else list({d['id']:d for d in docs}.values())
def guardar(doc,estado='BORRADOR',observaciones=None):
    nuevo=deepcopy(doc);nuevo.update(estado=estado,revision=str(len(st.session_state.versiones_demo)+1),guardado_en='2026-10-06T09:30:00')
    st.session_state.versiones_demo.append(nuevo);return nuevo
s.listar=listar;s.guardar=guardar;s.refrescar=lambda:None
s.versiones_actuales=lambda:st.session_state.versiones_demo
planeacion_page()

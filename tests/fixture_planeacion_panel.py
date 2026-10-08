"""Solo pruebas locales: repositorio ficticio, sin Google ni Gemini."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import streamlit as st
import pandas as pd
from services import planeacion as s
ALUMNO={'ID_Alumno':'A1','Nombre_Completo':'Alumno ficticio','ID_Escuela':'E1','Nombre_Escuela':'Escuela de prueba','CCT_Escuela':'TEST','Grado':'1','Grupo':'B','Tipo_Atencion':'Individual'}
ACTOR={'cuenta':'prueba','nombre':'Autor ficticio','director':False,'area':'Aprendizaje','rol':'APOYO','perfil':None}
from ui.planeacion import planeacion_page
st.set_page_config(layout='wide')
rol_prueba=st.selectbox('Perfil ficticio',['Apoyo','Dirección','Trabajo Social'])
if rol_prueba!='Apoyo':
    ACTOR={**ACTOR,'cuenta':'director' if rol_prueba=='Dirección' else 'diego','nombre':'Director ficticio' if rol_prueba=='Dirección' else 'Trabajador social ficticio','director':rol_prueba=='Dirección','area':rol_prueba}
st.session_state.update(autenticado=True,usuario='prueba',nombre='Autor ficticio',rol='APOYO',escuelas_permitidas='Escuela de prueba')
s.identidad=lambda:ACTOR
s.padron_autorizado=lambda:pd.DataFrame([ALUMNO])
s.repo.escuelas=lambda:pd.DataFrame([{'ID_Escuela':'E1','Nombre_Escuela':'Escuela de prueba','CCT':'TEST'}])
if 'fixture_versions' not in st.session_state:st.session_state.fixture_versions=[]
def listar(todas_versiones=False):
    docs=st.session_state.fixture_versions
    return docs if todas_versiones else list({d['id']:d for d in docs}.values())
def guardar(doc,estado='BORRADOR',observaciones=None):
    from copy import deepcopy
    saved=deepcopy(doc);saved.update(estado=estado,revision=str(len(st.session_state.fixture_versions)+1),guardado_en='2026-10-04T21:30:00')
    st.session_state.fixture_versions.append(saved);return saved
s.listar=listar;s.guardar=guardar;s.refrescar=lambda:None;s.evidencias=lambda d:([],[])
s.versiones_actuales=lambda:st.session_state.fixture_versions
planeacion_page()

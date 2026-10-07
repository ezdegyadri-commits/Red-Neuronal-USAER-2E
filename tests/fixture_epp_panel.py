"""Entorno ficticio y aislado; no accede a Google, alumnos reales ni Gemini."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from copy import deepcopy
import streamlit as st
import pandas as pd
from services import epp as s
from services.epp_modelo import campos
from ui import epp as ui

st.set_page_config(layout='wide')
from ui.theme import inject
inject()
area=st.selectbox('Perfil ficticio',['Aprendizaje','Psicología','Comunicación','Trabajo Social','Dirección'])
who={'cuenta':'docente-ficticia' if area=='Aprendizaje' else 'cuenta-'+area,'nombre':'Profesional ficticio',
    'area':area,'rol':'MAESTRO DE APOYO' if area=='Aprendizaje' else area,'director':area=='Dirección','perfil':None}
alumno={'ID_Alumno':'FICTICIO-A1','Nombre_Completo':'Alumno de prueba','ID_Escuela':'E1','Nombre_Escuela':'Escuela ficticia',
    'CCT_Escuela':'TEST','Grado':'3','Grupo':'A','Tipo_Atencion':'Individual','Edad_1_Septiembre':9}
st.session_state.setdefault('qa_epp_rows',[])
st.session_state.setdefault('qa_ai_calls',0)
class Sheet:
    def append_rows(self,rows,value_input_option):
        assert value_input_option=='RAW'
        st.session_state['qa_epp_rows'].extend(deepcopy(rows))
s.actor=lambda:who
s.planes.padron_autorizado=lambda:pd.DataFrame([alumno])
s.df_sheet=lambda name:pd.DataFrame(st.session_state['qa_epp_rows'],columns=s.HEADERS)
s.clear_cache=lambda *args:None
s.hoja=lambda:Sheet()
s.retry_google=lambda f:f()
s.recientes=lambda:{}
if not st.session_state['qa_epp_rows']:
    previous=who
    s.actor=lambda:{**previous,'area':'Aprendizaje','cuenta':'docente-ficticia','rol':'MAESTRO DE APOYO','director':False}
    s.crear('FICTICIO-A1','2026-2027')
    s.actor=lambda:who
def fake_generate(summary,target):
    st.session_state['qa_ai_calls']+=1
    return {'campos':{f:'EV1: Hallazgo educativo ficticio para revisión.' for f in campos(target)},'nee':[],'bap':[], 'faltantes':['Confirmar con el equipo.']}
ui.generar=fake_generate
s.contexto=lambda d:{'ficticio':True}
s.resumen=lambda *args:'EV1: Hallazgos educativos ficticios y sin identificadores.'
ui.epp_page()

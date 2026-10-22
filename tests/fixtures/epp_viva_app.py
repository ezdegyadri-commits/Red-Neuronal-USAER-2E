"""Solo pruebas con matrícula ficticia; todas las conexiones externas sustituidas."""
from copy import deepcopy
import streamlit as st
import pandas as pd
from services import epp as s
from tests.test_epp import ACTOR,ALUMNO
from ui import epp_viva as ui,planeacion_papel as editor
st.set_page_config(layout='wide')
area=st.session_state.get('qa_area',st.query_params.get('area','Aprendizaje'))
who={**ACTOR,'area':area,'cuenta':'docente-ficticia' if area=='Aprendizaje' else 'ficticio-'+area,'rol':'MAESTRO DE APOYO' if area=='Aprendizaje' else area}
st.session_state.setdefault('qa_rows',[])
s.actor=lambda:who
s.planes.padron_autorizado=lambda:pd.DataFrame([ALUMNO,{**ALUMNO,'ID_Alumno':'FICTICIO-A2','Nombre_Completo':'Otro alumno ficticio','Grado':'1°','Grupo':'B','Tipo_Atencion':'Grupal'},{**ALUMNO,'ID_Alumno':'FICTICIO-A3','Nombre_Completo':'Tercer alumno ficticio','Grado':'1','Grupo':'','Tipo_Atencion':'Grupal'}])
s.df_sheet=lambda *args:pd.DataFrame(st.session_state['qa_rows'],columns=s.HEADERS)
s.clear_cache=lambda *args:None
s.recientes=lambda:{}
class Sheet:
    def append_rows(self,rows,value_input_option):st.session_state.qa_rows.extend(deepcopy(rows))
s.hoja=lambda:Sheet()
s.retry_google=lambda f:f()
from services import planeacion_estabilidad as estabilidad
estabilidad.reservar_escritura=lambda:None
if not st.session_state.qa_rows:
    s.actor=lambda:ACTOR
    s.crear(ALUMNO['ID_Alumno'],'2026-2027')
    s.actor=lambda:who
def fake_editor(**kw):
    st.session_state.qa_spec=kw['hoja']
    return st.session_state.get('qa_event')
if st.query_params.get('editor')=='1':
    import hashlib
    base='epp_'+hashlib.sha256(who['cuenta'].encode()).hexdigest()[:12]
    st.session_state.setdefault(base+'_viva_abierta',ui.abrir(s.listar()[0]))
elif not st.session_state.get('qa_editor_real'):editor.editor=fake_editor
ui.page()

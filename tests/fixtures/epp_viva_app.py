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
if st.session_state.get('qa_conclusion_test'):
    from services.epp_modelo import AREAS, campos, vacia
    from tests.test_epp_conclusion_visible import propuesta
    import ai.epp
    def generar_qa(*args):
        if st.session_state.get('qa_cambia_durante_ia'):
            actual=s.listar()[0];v=deepcopy(actual['partes']['Psicología']['contenido'])
            v['campos'][campos('Psicología')[0]]='Hallazgo nuevo durante generación QA'
            s.actor=lambda:{**ACTOR,'area':'Psicología','cuenta':'ficticio-Psicología','rol':'Psicología'}
            try:s.guardar(actual,'Psicología',v,actual['partes']['Psicología']['revision'])
            finally:s.actor=lambda:who
        return propuesta()
    ai.epp.generar=generar_qa
    s.contexto=lambda doc:{'metadatos':{'fuentes':[]},'datos':{'Alumnos':[]}}
    s.planes.resumen_previo=lambda plan,parts:'\n'.join(f['referencia']+': '+f['texto'] for f in parts)
    if not st.session_state.get('qa_sembrada'):
        d=s.listar()[0]
        for a in AREAS:
            s.actor=lambda a=a:{**ACTOR,'area':a,'cuenta':ACTOR['cuenta'] if a=='Aprendizaje' else 'ficticio-'+a,'rol':'MAESTRO DE APOYO' if a=='Aprendizaje' else a}
            v=vacia(a);v['campos'][campos(a)[0]]='Hallazgos documentados QA de '+a
            s.guardar(d,a,v,'')
        st.session_state.qa_sembrada=True
    s.actor=lambda:who
def fake_editor(**kw):
    st.session_state.qa_spec=kw['hoja']
    return st.session_state.get('qa_event')
if st.query_params.get('editor')=='1':
    import hashlib
    base='epp_'+hashlib.sha256(who['cuenta'].encode()).hexdigest()[:12]
    st.session_state.setdefault(base+'_viva_abierta',ui.abrir(s.listar()[0]))
elif not st.session_state.get('qa_editor_real'):editor.editor=fake_editor
if st.query_params.get('principal')=='1':
    from ui import epp as pagina_epp
    from unittest.mock import patch
    with patch('ui.archivo_expediente.boton'):
        pagina_epp.epp_page()
else:ui.page()

"""Aplicación aislada de pruebas: sin Sheets, archivos reales ni proveedores IA."""
from copy import deepcopy
from unittest.mock import patch
import streamlit as st
from services.epp_modelo import vacia,campos
from services import epp_instrumentos as motor,epp
from ui import epp_instrumentos as ui
st.session_state.setdefault('qa_ai_calls',0)
if 'qa_value' not in st.session_state:
    v=vacia('Aprendizaje');v['campos']['5.1. Competencia curricular']='Redacción previa'
    c=motor.plantilla('XIV');c['fecha']='2026-10-22';c['respuestas']['1']['respuesta']='Sí'
    v['aplicaciones_en_curso']={'XIV':c};st.session_state.qa_value=v
doc={'id':'EPP-FICTICIA','alumno':'FICTICIO','ciclo':'2026-2027','partes':{'Aprendizaje':{'contenido':st.session_state.qa_value}}}
def guardar(v,manual):st.session_state.qa_value=deepcopy(v);return True
class Archivo:
    name='informe-ficticio.docx'
    def getvalue(self):return b'datos-ficticios-no-documento-real'
def generar(*args):
    st.session_state.qa_ai_calls+=1
    return {'campos':{f:'EV1: Propuesta ficticia revisable.' for f in campos('Aprendizaje')},'nee':[],'bap':[],'faltantes':[]}
with patch('services.materiales_planeacion.leer_material',return_value={'texto':'Hallazgos de una evaluación profesional ficticia.','avisos':[]}),patch.object(epp,'contexto',return_value={}),patch.object(epp,'resumen',return_value='EV1: Hallazgo sin identificadores para revisión.'),patch('ai.epp.generar',side_effect=generar):
    if st.session_state.get('qa_modo','digital')=='digital':ui.digital(doc,'Aprendizaje','qa',lambda:st.session_state.qa_value,guardar,nombre=motor.DEFINICIONES['XIV']['nombre'])
    else:
        with patch.object(ui.st,'file_uploader',return_value=Archivo()):ui.externo(doc,'Aprendizaje','qa',lambda:st.session_state.qa_value,guardar)

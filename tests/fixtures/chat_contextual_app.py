"""Chat de prueba: fuentes ficticias, IA simulada y persistencia local."""
from copy import deepcopy
from concurrent.futures import Future
from unittest.mock import patch
import streamlit as st
from services import planeacion as s,planeacion_chat_contextual as chat
from tests.test_memoria_chat_contextual import ejemplo
from tests.test_planeacion_panel import ACTOR
st.set_page_config(layout='wide')
st.session_state.update(usuario=ACTOR['cuenta'],autenticado=True,rol='APOYO')
seleccion=st.radio('Documento ficticio',['Uno','Dos'],horizontal=True)
prefix='qa_chat_'+seleccion
if prefix+'_doc' not in st.session_state:
    d=ejemplo();d['id']='qa-'+seleccion
    if seleccion=='Dos':
        d['datos']['Alumnos'][0]['ID_Alumno']='A2';d['datos']['Alumnos'][0]['Nombre del alumno']='OTRO ALUMNO FICTICIO'
        d['metadatos']['fuentes']=[]
    st.session_state[prefix+'_doc']=d

def persist(prefix,automatic=True):
    st.session_state['qa_guardados']=st.session_state.get('qa_guardados',0)+1
    st.session_state.setdefault('qa_base',{})[st.session_state[prefix+'_doc']['id']]=deepcopy(st.session_state[prefix+'_doc'])

def enviar(fn,*args):
    future=Future()
    req=args[1]
    key=next(k for k,v in req['destinos'].items() if v['ruta'][-1]=='Actividades')
    response={'respuesta':'Propongo una actividad más corta con apoyo visual.','faltantes':[],
        'cambios':[{'destino':key,'texto':'Agrupar tres fichas por su sonido inicial con ayuda visual.','evidencias':[req['memoria']['hechos'][0]['id']],'referentes':['R1']}]}
    future.set_result(chat.validar(response,req));return future

st.markdown('### Formato individual ficticio')
st.write(st.session_state[prefix+'_doc']['tablas']['dosificacion'][0]['Actividades'])
with patch.object(s,'autorizar',return_value=ACTOR),patch.object(s,'identidad',return_value=ACTOR),\
     patch('ui.planeacion_memoria.actualizar',return_value=True),\
     patch('services.curriculo.contexto_ia',return_value={'referentes_por_grado':[{'id':'R1','pda':'Relaciona sonidos iniciales.','fuente':'SEP','pagina_pdf':20}]}),\
     patch('ai.planeacion.configuracion_trabajo',return_value={'gemini':'ficticia'}),patch('ai.documento_json.enviar',side_effect=enviar):
    from ui.planeacion_chat import render_asistente_dialogo
    render_asistente_dialogo(prefix,persist)

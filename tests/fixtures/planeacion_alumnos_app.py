"""Solo documento, alumnos y persistencia ficticios; nunca conecta a Google."""
from copy import deepcopy
from unittest.mock import patch
import streamlit as st
from ui.planeacion_alumnos import panel
from ui import planeacion as ui
from services import planeacion as s
from tests.test_planeacion_alumnos import raiz,padron,ACTOR

st.session_state.setdefault('qa_doc',raiz())
st.session_state.setdefault('qa_envios',0)
def abrir(prefix,doc):st.session_state[prefix+'_doc']=deepcopy(doc)
def guardar(prefix):
    st.session_state.qa_envios+=1
    st.session_state.qa_doc_id=st.session_state[prefix+'_doc']['id']
    return True
with patch.object(s,'autorizar',return_value=ACTOR),patch.object(s,'padron_autorizado',side_effect=padron),patch.object(s,'preparar_contexto',side_effect=lambda d:d),patch.object(s,'refrescar_matricula'),patch.object(ui,'_open',side_effect=abrir),patch.object(ui,'_persist',side_effect=guardar):
    panel('qa')

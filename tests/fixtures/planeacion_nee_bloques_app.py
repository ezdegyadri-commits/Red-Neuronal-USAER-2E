"""Captura de varios bloques, sin cuentas, base central ni servicios externos."""
from copy import deepcopy
import streamlit as st
from tests.test_planeacion_intervenciones_nee import ejemplo
from ui.planeacion_intervenciones_nee import panel

if 'qa_doc' not in st.session_state:st.session_state.qa_doc=ejemplo(st.session_state.get('qa_area','Aprendizaje'))
st.session_state.setdefault('qa_guardados',0)
def abrir(prefix,doc):st.session_state[prefix+'_doc']=deepcopy(doc)
def persistir(prefix,automatic=False):st.session_state.qa_guardados+=1;return True
panel('qa',persistir,abrir)

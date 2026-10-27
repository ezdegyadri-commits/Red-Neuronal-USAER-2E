"""Prueba visual aislada: simula tres segundos de red, sin Google ni IA."""
from copy import deepcopy
import time
import streamlit as st
import pandas as pd
from tests.test_planeacion_panel import documento,ACTOR,ALUMNO
from services import planeacion as s
from ui import planeacion as ui
from ui.planeacion_papel import presentar
from ui.interacciones_rapidas import activar

st.set_page_config(layout='wide')
st.caption('Prueba local · datos ficticios · red simulada de tres segundos')
activar()
s.identidad=lambda:ACTOR
s.padron_autorizado=lambda:pd.DataFrame([ALUMNO])
s.precargar_docentes_regulares=lambda d:d
s.compartidos=lambda documento=None:[]
registros=st.session_state.setdefault('qa_envios',[])
def guardar(doc,estado='BORRADOR'):
    time.sleep(3)
    saved=deepcopy(doc);saved.update(revision='revision-'+str(len(registros)+1),guardado_en='fecha de prueba',estado=estado)
    registros.append(saved);return saved
s.guardar=guardar
st.session_state.setdefault('p_doc',documento())
presentar('p')
st.caption('Envíos confirmados en la prueba: '+str(len(registros)))

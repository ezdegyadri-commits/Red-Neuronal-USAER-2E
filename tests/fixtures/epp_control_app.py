"""Programación EPP de un equipo ficticio, persistencia simulada en memoria."""
from copy import deepcopy
from unittest.mock import patch,Mock
import streamlit as st
import pandas as pd
from services import epp,epp_programacion as s
from ui.epp_programacion import panel
st.set_page_config(layout='wide')
area=st.radio('Perfil ficticio',['Aprendizaje','Comunicación'])
actor={'cuenta':'ficticia-'+area,'area':area,'rol':'APOYO' if area=='Aprendizaje' else 'COMUNICACION','director':False}
frame=pd.DataFrame([{'ID_Alumno':'A1','ID_Escuela':'E1','Nombre_Completo':'Alumno de prueba','Nombre_Escuela':'Escuela ficticia'}])
st.session_state.setdefault('control_ficticio',[])
ws=Mock()
ws.row_values.return_value=s.HEADERS
ws.append_rows.side_effect=lambda values,**kw:st.session_state.control_ficticio.extend(dict(zip(s.HEADERS,row)) for row in values)
with patch.object(epp,'actor',return_value=actor),patch.object(epp,'puede_crear',return_value=area=='Aprendizaje'),patch.object(epp.planes,'padron_autorizado',return_value=frame),patch.object(epp,'alumno_autorizado',return_value=frame.iloc[0].to_dict()),patch.object(s,'_rows',side_effect=lambda:deepcopy(st.session_state.control_ficticio)),patch.object(s,'clear_cache'),patch.object(s,'ensure_headers',return_value=ws):
    panel('prueba')

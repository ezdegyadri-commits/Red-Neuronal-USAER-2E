"""Consulta estadística con nombres de alumnos y claves exclusivamente ficticios."""
from unittest.mock import patch
import pandas as pd
import streamlit as st
from data import repository as repo
from ui.estadisticas import estadisticas_page

st.set_page_config(layout='wide')
st.session_state.update(autenticado=True, usuario='qa-sexto',
    nombre='Mtra. Marycruz Caamal Coral', rol='APOYO', escuelas_permitidas='ESC-002')
rows = [dict(ID_Alumno=f'QA-SEXTO-{i}', Nombre_Completo=f'Alumno ficticio {i}',
    CURP=f'NO-OFICIAL-SEXTO-{i}', ID_Escuela='ESC-002', Nombre_Escuela='Ichcaanziho',
    Grado='6o.', Grupo='B', Estatus='Activo', Tipo_Atencion='Individual' if i < 2 else 'Grupal',
    **{'Maestra de Apoyo': ['Marycruz Caamal Coral', 'Mary Cruz Caamal Coral',
        'Mtra. Marycruz Caamal'][i % 3]}) for i in range(9)]
rows += [{**rows[0], 'ID_Alumno':'QA-AJENO-CECI', 'CURP':'NO-OFICIAL-CECI',
    'Maestra de Apoyo':'María Cecilia Solís Vázquez'},
    {**rows[0], 'ID_Alumno':'QA-AJENO-DIANELY', 'CURP':'NO-OFICIAL-DIANELY',
    'ID_Escuela':'ESC-004', 'Nombre_Escuela':'Remigio Aguilar Sosa',
    'Maestra de Apoyo':'Mtra. Dianely de Sugeidy Caamal Tamay'}]
with patch.object(repo, 'read', return_value=pd.DataFrame(rows)), \
        patch.object(repo, 'escuelas', return_value=pd.DataFrame()), \
        patch.object(repo, 'anexo4', return_value=pd.DataFrame()):
    estadisticas_page(None)

"""Regresión de captura histórica y reciente. Solo alumnos ficticios, sin red."""
from unittest.mock import patch
import pandas as pd
import streamlit as st
from data import repository as repo
from ui.estadisticas import estadisticas_page
from tests.test_estadistica_remigio import padron_ficticio,NOMBRE

st.set_page_config(layout='wide')
st.session_state.update(autenticado=True,usuario='qa-remigio',nombre=NOMBRE,rol='APOYO',escuelas_permitidas='Remigio Aguilar Sosa')
with patch.object(repo,'read',return_value=padron_ficticio()),patch.object(repo,'escuelas',return_value=pd.DataFrame()),patch.object(repo,'anexo4',return_value=pd.DataFrame()):
    estadisticas_page(None)

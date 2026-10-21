"""Sesiones ficticias: sin secretos, Sheets, usuarios reales ni red."""
from unittest.mock import patch
import streamlit as st
from services.sesiones_recuperables import Sesiones
from tests.test_continuidad_integracion import Memoria
from ui import sesiones_recuperables as ui,auth
st.set_page_config(layout='wide')
st.session_state.setdefault('diario_ficticio',[])
store=Memoria();store.registros=st.session_state.diario_ficticio
s=Sesiones(b'secreto-sintetico-ui',store)
with patch.object(ui,'servicio',return_value=s),patch('services.sesiones_recuperables.servicio',return_value=s),patch.object(auth,'escuelas_asignadas',return_value=[]):
    ui.recuperar()
    if not st.session_state.get('autenticado'):
        if st.button('Ingresar ficticia'):auth.start_session(store.cuenta);st.rerun()
    else:
        st.success('Cuenta: '+st.session_state.usuario)
        if st.button('Cerrar acceso de prueba'):auth._cerrar()

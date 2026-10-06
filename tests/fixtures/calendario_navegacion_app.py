"""Prueba de calendario común aislada: sin Google ni publicaciones reales."""
from types import SimpleNamespace
from unittest.mock import patch
import streamlit as st
from services import calendario_eventos as s
from ui import calendario_eventos as ui
st.set_page_config(layout='wide')
perfil=st.radio('Perfil ficticio',['Dirección','Psicología','Comunicación','Trabajo Social','Apoyo'])
nombres={area:'Persona ficticia '+area for area in ['Dirección','Psicología','Comunicación','Trabajo Social','Apoyo']}
st.session_state.update(autenticado=True,nombre=nombres[perfil],rol='DIRECTOR' if perfil=='Dirección' else 'APOYO' if perfil=='Apoyo' else perfil)
st.session_state.setdefault('eventos_ficticios',[])
def append(rows,**kw):st.session_state.eventos_ficticios.extend(dict(zip(s.HEADERS,r)) for r in rows)
ws=SimpleNamespace(row_values=lambda _:s.HEADERS,append_rows=append)
def perfil_mock(nombre,rol):
    return {'nombre':nombre,'area':'Dirección','escuelas':['Escuela ficticia '+str(i) for i in range(1,9)]} if rol=='DIRECTOR' else None
with patch.object(s,'_eventos_guardados',side_effect=lambda:st.session_state.eventos_ficticios),patch.object(s,'ensure_headers',return_value=ws),patch.object(s,'perfil_especialista',side_effect=perfil_mock),patch.object(ui,'perfil_especialista',side_effect=perfil_mock):
    ui.calendario_page()

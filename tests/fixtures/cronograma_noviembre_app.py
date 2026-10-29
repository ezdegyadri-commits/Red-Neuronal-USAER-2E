"""Cronograma propio ficticio sin conexiones ni firmas reales."""
from datetime import date
from unittest.mock import patch
import streamlit as st
from ui import cronogramas as ui

st.set_page_config(layout='wide')
nombre=st.session_state.get('qa_nombre','Diego Peralta Torres')
rol=st.session_state.get('qa_rol','Trabajo Social')
st.session_state.update(nombre=nombre,rol=rol,autenticado=True)
mes='2026-11';dia='2026-11-03'
st.session_state.setdefault('cronograma_mes_'+nombre,mes)
editor='cronograma_editor_'+nombre+'_'+mes
st.session_state.setdefault(editor+'_editable',False)
saved={dia:{'escuela':'Damián Carmona','actividad':'Seguimiento educativo ficticio'}}
def guardar(nombre,area,mes,escuelas,agenda):
    st.session_state['qa_guardado']={'nombre':nombre,'area':area,'mes':mes,'escuelas':escuelas,'agenda':agenda}
    return {'filas':len(agenda),'publicacion_id':'qa-publicacion'}
with patch.object(ui,'cargar_agenda',return_value=saved),patch.object(ui,'cargar_borrador',return_value=None), \
     patch.object(ui,'guardar_borrador',return_value='qa'),patch.object(ui,'meses_con_cronograma',return_value=[mes]), \
     patch.object(ui,'eventos_mes',return_value={}),patch.object(ui,'ventana_eventos'),patch.object(ui,'pendientes_mes'), \
     patch.object(ui,'_avisos_automaticos'),patch.object(ui,'_recuperar_cronogramas'), \
     patch.object(ui,'guardar_agenda',side_effect=guardar),patch.object(ui,'avisar_maestras_apoyo',return_value=0), \
     patch.object(ui,'_recursos_firma',return_value=(None,None,None)),patch.object(ui,'_perfil_profesional',side_effect=lambda p:p), \
     patch.object(ui,'generar_cronograma_pdf',return_value=b'%PDF-ficticio'), \
     patch.object(ui,'cargar_agenda_global',return_value=[{'Especialista':nombre,'ID_Publicacion':'qa-publicacion'}]):
    ui.cronogramas_page()

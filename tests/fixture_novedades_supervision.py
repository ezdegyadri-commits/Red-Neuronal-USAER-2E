"""Datos ficticios; no consulta Google ni Gemini."""
import streamlit as st
from services import novedades_supervision as s
from tests.test_novedades_supervision import documento
from ui.novedades_supervision import novedades_page
st.set_page_config(layout='wide')
rol=st.radio('Perfil ficticio',['Dirección','Apoyo'])
s.identidad=lambda:{'director':rol=='Dirección','cuenta':'cuenta-ficticia'}
st.session_state.setdefault('vistos_ficticios',[])
def leer(hoja):
    return [documento(),{**documento('__SOURCE__'),'Enlace':'https://drive.google.com/drive/folders/demo'}] if hoja==s.HOJA else st.session_state.vistos_ficticios
s._leer=leer;s.refrescar=lambda:None
def marcar(ident,version):st.session_state.vistos_ficticios.append({'Cuenta':'cuenta-ficticia','Documento':ident,'Modificado_En':version})
s.marcar_revisado=marcar
novedades_page()

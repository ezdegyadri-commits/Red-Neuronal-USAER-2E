import streamlit as st
from config.settings import PAGE_TITLE
from data import repository as repo
from services.expedientes import alumnos_visibles
from ui.theme import inject
from ui.auth import login, logout
from ui.pages import inicio, expedientes_page, alta_page, bap_page, eventos_page, documentos_page, direccion_page, visitas_page

st.set_page_config(page_title=PAGE_TITLE, page_icon="◈", layout="wide", initial_sidebar_state="expanded")
inject()

if not st.session_state.get("autenticado"):
    login()
    st.stop()

cabecera_izquierda, cabecera_derecha = st.columns([5, 1])
with cabecera_derecha:
    logout("cerrar_sesion_principal")

rol=st.session_state.get("rol","")
escuelas=st.session_state.get("escuelas_permitidas","")

authorized = alumnos_visibles(rol, escuelas)

with st.sidebar:
    st.markdown("<div class='brand'><h1>USAE 02-E</h1><p>Gestión integral de intervención educativa</p></div>",unsafe_allow_html=True)
    st.caption(f"Sesión: {st.session_state.get('nombre','')}")
    st.divider()
    menu=["Inicio","Expedientes","Evaluación BAP","Eventos significativos","Documentos"]
    if "DIRECTOR" in rol.upper(): menu += ["Panel de Dirección","Constancias de visita","Alta de alumnos"]
    elif "APOYO" in rol.upper(): menu += ["Alta de alumnos"]
    else: menu += ["Constancias de visita"]
    page=st.radio("Navegación",menu,label_visibility="collapsed")

try:
    repo.ensure_integrated_sheets()
except Exception:
    pass

if page=="Inicio": inicio(authorized)
elif page=="Expedientes": expedientes_page(authorized)
elif page=="Evaluación BAP": bap_page(authorized)
elif page=="Eventos significativos": eventos_page(authorized)
elif page=="Documentos": documentos_page(authorized)
elif page=="Panel de Dirección": direccion_page(authorized)
elif page=="Constancias de visita": visitas_page(authorized)
elif page=="Alta de alumnos": alta_page(authorized)

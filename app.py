import streamlit as st
from config.settings import PAGE_TITLE
from data import repository as repo
from services.expedientes import alumnos_visibles
from services.asignaciones import es_especialista, puede_dar_alta_alumnos
from services.cronogramas import perfil_especialista
from ui.theme import inject
from ui.mobile_install import install_metadata, installation_help
from ui.passkeys import configure_passkey
from ui.escritura import activar_revision
from ui.auth import login, logout
from ui.pages import inicio, expedientes_page, alta_page, bap_page, eventos_page, documentos_page, direccion_page, visitas_page, derivacion_page
from ui.oficios import oficios_comision_page
from ui.direccion_oficios import configuracion_oficios_direccion
from ui.direccion_rapida import direccion_page_rapida
from ui.sugerencias import anexo4_page
from ui.estadisticas import estadisticas_page
from ui.cronogramas import cronogramas_page, cronogramas_direccion
from ui.horarios_apoyo import horarios_apoyo_page, horarios_apoyo_direccion
from ui.calendario_eventos import eventos_direccion
from ui.tramites import tramites_page
from services.tramites import gestor as gestor_tramites, puede_solicitar
from ui.planeacion import planeacion_page, direccion_panel

st.set_page_config(page_title=PAGE_TITLE, page_icon="◈", layout="wide", initial_sidebar_state="expanded")
inject()
# Instaladores móviles 1.0.0 disponibles en ingreso y barra lateral.
install_metadata()

if not st.session_state.get("autenticado"):
    login()
    st.stop()

activar_revision()

cabecera_izquierda, cabecera_derecha = st.columns([5, 1])
with cabecera_derecha:
    logout("cerrar_sesion_principal")

rol=st.session_state.get("rol","")
escuelas=st.session_state.get("escuelas_permitidas","")

with st.sidebar:
    st.markdown("<div class='brand'><h1>USAER 02E</h1><p>Gestión integral de intervención educativa</p></div>",unsafe_allow_html=True)
    st.caption(f"Sesión: {st.session_state.get('nombre','')}")
    installation_help()
    configure_passkey()
    st.divider()
    menu=["Inicio","Expedientes","Anexo III BAP","Anexo IV Hoja de sugerencias","Anexo V Eventos significativos","Estadística","Documentos"]
    if gestor_tramites() or puede_solicitar():
        menu += ["Trámites"]
    perfil_cronograma = perfil_especialista(st.session_state.get("nombre", ""), rol)
    if perfil_cronograma or "APOYO" in rol.upper():
        menu += ["Planeación e intervención"]
    if perfil_cronograma and perfil_cronograma["area"] != "Dirección":
        menu += ["Cronograma mensual"]
    if "DIRECTOR" in rol.upper():
        menu += ["Panel de Dirección", "Constancias de visita"]
        if puede_dar_alta_alumnos(st.session_state.get("nombre", ""), rol):
            menu += ["Alta de alumnos"]
    elif "APOYO" in rol.upper():
        menu += ["Horarios de apoyo"]
        if puede_dar_alta_alumnos(st.session_state.get("nombre", ""), rol):
            menu += ["Alta de alumnos"]
        menu += ["Oficios de comisión", "Anexo VII Derivación"]
    else: menu += ["Constancias de visita", "Anexo VII Derivación"]
    grupos_menu = {
        "Inicio": "🏠 Inicio",
        "Expedientes": "📁 Expedientes",
        "Anexo III BAP": "🧭 Captura · Anexo III BAP",
        "Anexo IV Hoja de sugerencias": "📝 Anexo IV · Hoja de sugerencias",
        "Anexo V Eventos significativos": "📌 Anexo V · Hoja de eventos significativos",
        "Estadística": "📊 Consulta · Estadística y listado nominal",
        "Documentos": "📄 Consulta · Documentos",
        "Cronograma mensual": "🗓️ Equipo especialista · Cronograma",
        "Horarios de apoyo": "🕒 Maestras de apoyo · Horarios y avisos",
        "Panel de Dirección": "⚙️ Dirección · Panel",
        "Trámites": "📨 Trámites · Solicitudes de expedientes",
        "Constancias de visita": "🗓️ Equipo · Constancias de visita",
        "Alta de alumnos": "➕ Captura · Alta de alumnos",
        "Oficios de comisión": "🧾 Apoyo · Oficios de comisión",
        "Anexo VII Derivación": "🔎 Derivación · Anexo VII",
    }
    page=st.radio(
        "Ir al apartado",
        menu,
        format_func=lambda apartado: grupos_menu.get(apartado, apartado),
        label_visibility="collapsed",
        key="navegacion_principal",
    )

# No se lee el padrón central en módulos que no lo necesitan.
if page in {"Inicio", "Expedientes", "Anexo III BAP", "Anexo IV Hoja de sugerencias", "Anexo V Eventos significativos", "Estadística", "Documentos", "Alta de alumnos"}:
    authorized = alumnos_visibles(rol, escuelas, st.session_state.get("nombre", ""))
else:
    authorized = None

if page=="Inicio": inicio(authorized)
elif page=="Expedientes": expedientes_page(authorized)
elif page=="Anexo III BAP": bap_page(authorized)
elif page=="Anexo IV Hoja de sugerencias": anexo4_page(authorized)
elif page=="Anexo V Eventos significativos": eventos_page(authorized)
elif page=="Estadística": estadisticas_page(authorized)
elif page=="Documentos": documentos_page(authorized)
elif page=="Cronograma mensual": cronogramas_page()
elif page=="Horarios de apoyo": horarios_apoyo_page()
elif page=="Trámites": tramites_page()
elif page=="Planeación e intervención": planeacion_page()
elif page=="Panel de Dirección":
    direccion_page_rapida(authorized)
    with st.expander("Planes de intervención y planeaciones del equipo"):
        if st.checkbox("Consultar entregas y revisar",key="consultar_planeaciones_director"):
            direccion_panel()
    horarios_apoyo_direccion()
    st.divider()
    configuracion_oficios_direccion()
    st.divider()
    st.subheader("Cronogramas del equipo")
    st.caption("Desde aquí puedes elaborar tu propio cronograma y consultar los publicados por Psicología, Comunicación y Trabajo Social.")
    if st.button("Mi cronograma y calendarios del equipo", type="primary", key="abrir_cronograma_direccion"):
        st.session_state["mostrar_cronograma_direccion"] = True
    if st.session_state.get("mostrar_cronograma_direccion"):
        if st.button("Cerrar cronogramas", key="cerrar_cronograma_direccion"):
            st.session_state["mostrar_cronograma_direccion"] = False
            st.rerun()
        elaborar, consulta, actividades = st.tabs(["Mi cronograma de Dirección", "Revisar cronogramas del equipo", "Actividades para todos"])
        with consulta:
            cronogramas_direccion()
        with elaborar:
            cronogramas_page()
        with actividades:
            eventos_direccion()
elif page=="Constancias de visita": visitas_page(authorized)
elif page=="Alta de alumnos": alta_page(authorized)
elif page=="Oficios de comisión": oficios_comision_page()
elif page=="Anexo VII Derivación": derivacion_page(authorized)

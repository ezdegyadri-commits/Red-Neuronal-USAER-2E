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
from services.tramites import gestor as gestor_tramites, puede_solicitar
from ui.sidebar import TITULOS_SIMPLIFICADOS

st.set_page_config(page_title=PAGE_TITLE, page_icon="◈", layout="wide", initial_sidebar_state="collapsed")
inject()
from ui.interacciones_rapidas import activar as activar_respuesta_local
activar_respuesta_local()
# Instaladores móviles 1.0.0 disponibles en ingreso.
install_metadata()

from ui.sesiones_recuperables import recuperar as recuperar_sesion
recuperar_sesion()

# El acceso directo también identifica la cuenta antes de ofrecer escuelas.
if st.query_params.get("p") in ("docentes", "docentes_primaria", "maestros_regulares") or st.query_params.get("form") in ("docentes", "docentes_primaria"):
    if not st.session_state.get('autenticado'):
        login()
        st.stop()
    from ui.docentes_regulares_form import formulario_publico_docentes
    formulario_publico_docentes()
    st.stop()

if not st.session_state.get("autenticado"):
    login()
    st.stop()

activar_revision()

rol = st.session_state.get("rol", "")
escuelas = st.session_state.get("escuelas_permitidas", "")
nombre_usuario = st.session_state.get("nombre", "")

# Cabecera superior minimalista y limpia
cabecera_izq, cabecera_der = st.columns([7.2, 2.8])
with cabecera_izq:
    st.markdown(
        f"<div style='padding:0.25rem 0;display:flex;align-items:center;gap:0.85rem;flex-wrap:wrap;'>"
        f"<span style='font-size:1.18rem;font-weight:800;color:var(--bs-primary-dark);display:inline-flex;align-items:center;gap:0.4rem;'><span style='color:#D97706;'>◈</span> USAER 02-E</span>"
        f"<span style='font-size:0.7rem;font-weight:750;letter-spacing:0.08em;text-transform:uppercase;color:#94A3B8;padding:2px 8px;background:rgba(15,23,42,0.04);border-radius:6px;'>Zona 001</span>"
        f"<span class='user-badge'><span class='status-dot'></span> {nombre_usuario} <span style='color:var(--bs-secondary-color);font-weight:400;'>· {rol}</span></span>"
        f"</div>",
        unsafe_allow_html=True,
    )
with cabecera_der:
    c_tools, c_logout = st.columns([1.1, 1.3])
    with c_tools:
        with st.popover("⚙️ Accesos"):
            if st.toggle('Instalación y acceso con huella',key='abrir_herramientas_acceso'):
                configure_passkey()
                installation_help()
            st.link_button("◈ Suite TEA", "https://deeply-howler-8m5y7.ship.place/", use_container_width=True)
    with c_logout:
        logout("cerrar_sesion_principal")

# Determinación de módulos permitidos según rol
menu = ["Inicio", "Expedientes", "Anexo III BAP", "Anexo IV Hoja de sugerencias", "Anexo V Eventos significativos", "Estadística", "Documentos", "Calendario de actividades"]
if gestor_tramites() or puede_solicitar():
    menu += ["Trámites"]
perfil_cronograma = perfil_especialista(st.session_state.get("nombre", ""), rol)
if perfil_cronograma or "APOYO" in rol.upper():
    menu += ["Planeación e intervención", "EPP", "Juntas académicas", "Metas personales"]
if perfil_cronograma and perfil_cronograma["area"] != "Dirección":
    menu += ["Cronograma mensual"]
if "DIRECTOR" in rol.upper():
    menu += ["Panel de Dirección", "Maestros de primaria", "Novedades de supervisión", "Constancias de visita"]
    if puede_dar_alta_alumnos(st.session_state.get("nombre", ""), rol):
        menu += ["Alta de alumnos"]
elif "APOYO" in rol.upper():
    menu += ["Horarios de apoyo", "Maestros de primaria"]
    if puede_dar_alta_alumnos(st.session_state.get("nombre", ""), rol):
        menu += ["Alta de alumnos"]
    menu += ["Oficios de comisión", "Anexo VII Derivación"]
else:
    menu += ["Constancias de visita", "Anexo VII Derivación"]

if "navegacion_principal" not in st.session_state or st.session_state["navegacion_principal"] not in menu:
    st.session_state["navegacion_principal"] = "Inicio"

page = st.session_state["navegacion_principal"]

from ui.contenido_modulo import mostrar as mostrar_modulo
mostrar_modulo(page,rol,escuelas,menu)

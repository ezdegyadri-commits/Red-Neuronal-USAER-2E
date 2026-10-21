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
from ui.calendario_eventos import eventos_direccion, calendario_page
from ui.tramites import tramites_page
from services.tramites import gestor as gestor_tramites, puede_solicitar
from ui.planeacion import planeacion_page, direccion_panel
from ui.epp import epp_page
from ui.novedades_supervision import novedades_page
from ui.sidebar import TITULOS_SIMPLIFICADOS
from ui.hub import pagina_central_hub

st.set_page_config(page_title=PAGE_TITLE, page_icon="◈", layout="wide", initial_sidebar_state="collapsed")
inject()
# Instaladores móviles 1.0.0 disponibles en ingreso.
install_metadata()

# Acceso público directo para maestros y directores de primarias regulares
if st.query_params.get("p") in ("docentes", "docentes_primaria", "maestros_regulares") or st.query_params.get("form") in ("docentes", "docentes_primaria"):
    from ui.docentes_regulares_form import formulario_publico_docentes
    formulario_publico_docentes()
    st.stop()

from ui.sesiones_recuperables import recuperar as recuperar_sesion
recuperar_sesion()

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
    menu += ["Planeación e intervención", "EPP"]
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

# No se lee el padrón central en módulos que no lo necesitan.
if page in {"Inicio", "Expedientes", "Anexo III BAP", "Anexo IV Hoja de sugerencias", "Anexo V Eventos significativos", "Estadística", "Documentos", "Alta de alumnos"}:
    authorized = alumnos_visibles(rol, escuelas, st.session_state.get("nombre", ""))
else:
    authorized = None

# Barra superior fluida de retorno hacia el Centro de Control
if page != "Inicio":
    c_back, c_bc = st.columns([2.3, 7.7])
    with c_back:
        if st.button("← Centro de Control", key="btn_volver_al_hub", use_container_width=True):
            st.session_state["navegacion_principal"] = "Inicio"
            st.rerun()
    with c_bc:
        titulo_modulo = TITULOS_SIMPLIFICADOS.get(page, page)
        st.markdown(
            f"<div class='module-breadcrumb'>"
            f"<span>USAER 02-E</span>"
            f"<span style='color:var(--bs-muted-color);'>›</span>"
            f"<strong>{titulo_modulo}</strong>"
            f"</div>",
            unsafe_allow_html=True,
        )

if page=="Inicio":
    pagina_central_hub(authorized, menu, rol, st.session_state.get("nombre", ""))
elif page=="Expedientes": expedientes_page(authorized)
elif page=="Anexo III BAP": bap_page(authorized)
elif page=="Anexo IV Hoja de sugerencias": anexo4_page(authorized)
elif page=="Anexo V Eventos significativos": eventos_page(authorized)
elif page=="Estadística": estadisticas_page(authorized)
elif page=="Documentos": documentos_page(authorized)
elif page=="Calendario de actividades": calendario_page()
elif page=="Cronograma mensual": cronogramas_page()
elif page=="Horarios de apoyo": horarios_apoyo_page()
elif page=="Trámites": tramites_page()
elif page=="Planeación e intervención": planeacion_page()
elif page=="EPP": epp_page()
elif page=="Novedades de supervisión": novedades_page()
elif page=="Panel de Dirección":
    direccion_page_rapida(authorized)
    with st.expander("Novedades de supervisión · ATP"):
        if st.checkbox("Consultar documentos y novedades",key="consultar_novedades_director"):
            novedades_page()
    with st.expander("Planes de intervención y planeaciones del equipo"):
        if st.checkbox("Consultar entregas y revisar",key="consultar_planeaciones_director"):
            direccion_panel()
    horarios_apoyo_direccion()
    st.divider()
    with st.expander("Directorio de Maestros de Grupo (7 Primarias)"):
        from ui.docentes_regulares_form import vista_docentes_regulares_admin
        vista_docentes_regulares_admin()
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
elif page=="Maestros de primaria":
    from ui.docentes_regulares_form import vista_docentes_regulares_admin
    vista_docentes_regulares_admin()
elif page=="Constancias de visita": visitas_page(authorized)
elif page=="Alta de alumnos": alta_page(authorized)
elif page=="Oficios de comisión": oficios_comision_page()
elif page=="Anexo VII Derivación": derivacion_page(authorized)

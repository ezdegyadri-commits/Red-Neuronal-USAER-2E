import hmac
import streamlit as st
from data.repository import usuarios
from services.asignaciones import escuelas_asignadas
from utils.text import normalizar_texto
from ui.mobile_install import installation_help
from ui.passkeys import login_passkey


def start_session(match):
    """Both login methods use the same server-side permissions and assignments."""
    nombre = str(match.get("Nombre", ""))
    rol = str(match.get("Rol", ""))
    escuelas = str(match.get("Escuelas_Permitidas", ""))
    oficiales = escuelas_asignadas(nombre, rol)
    if oficiales:
        escuelas = ",".join(oficiales)
    st.session_state.update({"autenticado": True, "usuario": str(match.get("Usuario", "")),
        "nombre": nombre, "rol": rol, "escuelas_permitidas": escuelas})
    st.session_state.pop("passkey_pending", None)


def login():
    with st.container(key="institutional_login"):
        _login_content()


def _login_content():
    st.markdown(
        "<div style='text-align:center;margin-bottom:1.6rem;'>"
        "<div class='badge' style='margin-bottom:0.6rem;'>Zona Escolar 001 · Yucatán</div>"
        "<h2 style='font-size:1.9rem;margin:0 0 0.35rem;letter-spacing:-0.025em;color:var(--bs-primary-dark);'>USAER 02-E</h2>"
        "<p style='color:var(--bs-secondary-color);font-size:0.92rem;margin:0;'>Plataforma institucional de gestión e intervención</p>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown("<div style='font-weight:600;font-size:1rem;color:var(--bs-primary-dark);margin-bottom:0.6rem;'>Acceso del equipo</div>", unsafe_allow_html=True)
    login_passkey(start_session)
    with st.form("login"):
        user = st.text_input("Usuario", placeholder="Tu usuario institucional")
        password = st.text_input("Contraseña", type="password", placeholder="••••••••")
        ok = st.form_submit_button("Ingresar a la plataforma", type="primary", use_container_width=True)
    if ok:
        df = usuarios()
        match = None
        if not df.empty:
            for _, r in df.iterrows():
                if hmac.compare_digest(str(r.get("Usuario", "")), user) and hmac.compare_digest(str(r.get("Password", "")), password):
                    match = r
                    break
        if match is None:
            st.error("Usuario o contraseña incorrectos.")
        else:
            start_session(match)
            st.rerun()
    installation_help()
    st.markdown("<p class='institution-footnote' style='text-align:center;'>USAER 02-E · Zona 001 · Yucatán<br>Información educativa de uso exclusivo del personal autorizado.</p>", unsafe_allow_html=True)


def logout(key="cerrar_sesion"):
    """Muestra un cierre de sesión en el contenedor actual."""
    if st.button("Cerrar sesión", key=key, use_container_width=True):
        for k in [
            "autenticado",
            "nombre",
            "rol",
            "escuelas_permitidas",
            "selected_alumno",
            "usuario",
            "passkey_pending",
        ]:
            st.session_state.pop(k, None)
        st.rerun()

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
    st.markdown("<div style='max-width:620px;margin:8vh auto'><div class='hero'><h1>USAER 02E</h1><p>Gestión integral de la intervención educativa</p></div>", unsafe_allow_html=True)
    login_passkey(start_session)
    with st.form("login"):
        user = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        ok = st.form_submit_button("Ingresar", type="primary", use_container_width=True)
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
    st.markdown("</div>", unsafe_allow_html=True)
    installation_help()


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

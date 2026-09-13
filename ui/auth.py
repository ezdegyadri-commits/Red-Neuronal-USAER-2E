import hmac
import streamlit as st
from data.repository import usuarios
from utils.text import normalizar_texto


def login():
    st.markdown("<div style='max-width:620px;margin:8vh auto'><div class='hero'><h1>USAE 02-E</h1><p>Gestión integral de la intervención educativa</p></div>", unsafe_allow_html=True)
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
            st.session_state.update({"autenticado": True, "nombre": str(match.get("Nombre", "")), "rol": str(match.get("Rol", "")), "escuelas_permitidas": str(match.get("Escuelas_Permitidas", ""))})
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def logout():
    if st.sidebar.button("Cerrar sesión", use_container_width=True):
        for k in ["autenticado","nombre","rol","escuelas_permitidas","selected_alumno"]:
            st.session_state.pop(k, None)
        st.rerun()

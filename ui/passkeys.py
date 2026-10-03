"""Opt-in, account-bound passkeys. Keep the normal login always available."""
import time
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
from data.passkeys import GooglePasskeyStore, registry_lock
from services.passkeys import begin, finish_authentication, finish_registration, TTL

component = components.declare_component("usaer_passkey", path=str(Path(__file__).with_name("passkey_component")))


def _render(pending, key):
    return component(kind=pending["kind"], request=pending["request"],
                     options=pending["options"], key=key, default=None)


def login_passkey(start_session):
    state = st.session_state
    # No Sheet read or biometric prompt until the person presses the HTML button.
    if time.time() < state.get("passkey_cooldown", 0):
        st.caption("Inténtalo en un minuto o usa tu contraseña.")
        return
    pending = state.get("passkey_pending")
    if not pending or pending["kind"] != "authenticate" or pending["expires"] < time.time():
        pending = begin(state, "authenticate")
    response = _render(pending, "passkey_login")
    if response and response.get("request") == pending["request"]:
        if response.get("error"):
            state.pop("passkey_pending", None)
            st.rerun()
            return
        try:
            with registry_lock():
                user = finish_authentication(state, response, GooglePasskeyStore())
            start_session(user)
            state["passkey_attempts"] = 0
            st.rerun()
        except Exception:
            state.pop("passkey_pending", None)
            attempts = state.get("passkey_attempts", 0) + 1
            state["passkey_attempts"] = attempts
            if attempts >= 3:
                state["passkey_cooldown"] = time.time() + 60
                state["passkey_attempts"] = 0
            st.info("No se completó el acceso. Usa tu contraseña o inténtalo de nuevo.")
            if st.button("Volver a intentar", key="passkey_retry"):
                st.rerun()


def configure_passkey():
    with st.expander("Acceso con huella o rostro", expanded=False):
        username = st.session_state.get("usuario")
        if not username:
            st.caption("Cierra sesión y entra nuevamente para activar el acceso seguro.")
            return
        st.caption("Actívalo solo en un dispositivo personal. El teléfono puede pedir huella, rostro o su código de desbloqueo.")
        with st.form("passkey_enroll"):
            password = st.text_input("Confirma tu contraseña para activar", type="password")
            enroll = st.form_submit_button("Activar en este dispositivo", use_container_width=True)
        if enroll:
            try:
                with registry_lock():
                    begin(st.session_state, "register", GooglePasskeyStore(), username, password)
            except Exception:
                st.session_state.pop("passkey_pending", None)
                st.info("No se pudo activar. Revisa tu contraseña e inténtalo de nuevo.")
        pending = st.session_state.get("passkey_pending")
        if pending and pending["kind"] == "register":
            response = _render(pending, "passkey_register")
            if response and response.get("request") == pending["request"]:
                if response.get("error"):
                    st.session_state.pop("passkey_pending", None)
                else:
                    try:
                        with registry_lock():
                            finish_registration(st.session_state, response, GooglePasskeyStore())
                        st.success("Acceso activado. La próxima vez usa «Entrar con huella o rostro».")
                    except Exception:
                        st.session_state.pop("passkey_pending", None)
                        st.info("No se guardó la activación. Puedes seguir usando tu contraseña.")
        with st.popover("Desactivar mis llaves de acceso", use_container_width=True):
            st.caption("Desactiva todas tus llaves en la plataforma. Tu contraseña y tus registros se conservan.")
            if st.button("Confirmar desactivación", key="revoke_passkeys", use_container_width=True):
                try:
                    with registry_lock():
                        GooglePasskeyStore().revoke_own(username)
                    st.session_state.pop("passkey_pending", None)
                    st.success("Llaves desactivadas.")
                except Exception:
                    st.info("No se pudo confirmar la desactivación. Inténtalo nuevamente.")

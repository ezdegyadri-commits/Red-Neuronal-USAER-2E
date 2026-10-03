"""Same-origin installation metadata; no new accounts, cache or data storage."""
from pathlib import Path


def installation_html():
    return (Path(__file__).with_name("mobile_install.html")).read_text(encoding="utf-8")


def install_controls():
    # The component may be sandboxed by a future Streamlit version. The visible
    # manual instructions remain usable when parent access is unavailable.
    import streamlit.components.v1 as components
    components.html(installation_html(), height=62, scrolling=False)


def installation_help():
    import streamlit as st
    with st.expander("Instalar USAER 02E en mi teléfono", expanded=False):
        install_controls()
        st.markdown(
            "**iPhone:** abre este enlace en Safari, toca Compartir y "
            "Añadir a pantalla de inicio. Activa «Abrir como app» si aparece.\n\n"
            "**Android:** abre este enlace en Chrome y elige Instalar aplicación "
            "o Añadir a pantalla de inicio en el menú."
        )
        st.caption("Usa tu cuenta habitual. Requiere internet; instalarla no activa rostro o huella.")


def install_metadata():
    # Initialize metadata on every connection, including installed app launches.
    # No private data or credentials are passed to JavaScript.
    import streamlit.components.v1 as components
    components.html(installation_html(), height=0, scrolling=False)

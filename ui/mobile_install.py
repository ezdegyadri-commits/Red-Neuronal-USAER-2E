"""Same-origin installation metadata; no new accounts, cache or data storage."""
from pathlib import Path
import hashlib

PORTAL_URL = "https://red-neuronal-usaer-2e.streamlit.app/"
APK_NAME = "USAER-02E-Android-1.0.0.apk"
APK_SHA256 = "f9e745024683a696685deb38e32f5b6545d9c5a8efa1666b412e08a63958ec04"
APK_URL = "https://raw.githubusercontent.com/ezdegyadri-commits/Red-Neuronal-USAER-2E/c30d390a04e5d3fb21ba877cb625b13a0fa0d510/mobile/downloads/" + APK_NAME
APK_PATH = Path(__file__).resolve().parents[1] / "static" / APK_NAME


def android_apk():
    """Only serve the exact public, signed release; no accounts/data involved."""
    payload = APK_PATH.read_bytes()
    if hashlib.sha256(payload).hexdigest() != APK_SHA256:
        raise ValueError("APK integrity mismatch")
    return payload


def installation_html():
    return (Path(__file__).with_name("mobile_install.html")).read_text(encoding="utf-8")


def install_controls():
    # The component may be sandboxed by a future Streamlit version. The visible
    # manual instructions remain usable when parent access is unavailable.
    import streamlit.components.v1 as components
    components.html(installation_html(), height=62, scrolling=False)


def installation_help():
    import streamlit as st
    st.markdown("### Instalar en mi teléfono")
    try:
        payload = android_apk()
    except (OSError, ValueError):
        # A missing/bad local asset must not disable the rest of the platform.
        st.link_button("Descargar APK para Android", APK_URL, use_container_width=True)
    else:
        st.download_button("Descargar APK para Android", data=payload,
            file_name=APK_NAME, mime="application/vnd.android.package-archive",
            key="usaer_android_apk", use_container_width=True, on_click="ignore")
    with st.popover("Instalar en iPhone / iPad", use_container_width=True):
        st.markdown(
            "1. Abre la plataforma en **Safari**.\n"
            "2. Toca **Compartir → Añadir a pantalla de inicio**.\n"
            "3. Confirma **USAER 02E** y toca **Añadir**."
        )
        st.link_button("Abrir enlace de la plataforma", PORTAL_URL, use_container_width=True)
        st.caption("En iPhone se instala desde Safari, sin archivo IPA ni perfiles adicionales.")
    st.caption("Sin pagos. Usa tu cuenta habitual y conexión a internet.")
    with st.expander("Ayuda de instalación", expanded=False):
        install_controls()
        st.markdown(
            "**Android:** abre el APK descargado y confirma la instalación. "
            "Si te lo pide, permite a tu navegador instalar este archivo; "
            "después puedes desactivar ese permiso. No desactives Play Protect.\n\n"
            "**Huella o rostro:** entra con tu cuenta y activa tu llave desde "
            "«Acceso con huella o rostro» en la barra lateral."
        )


def install_metadata():
    # Initialize metadata on every connection, including installed app launches.
    # No private data or credentials are passed to JavaScript.
    import streamlit.components.v1 as components
    components.html(installation_html(), height=0, scrolling=False)

"""Configuración compartida para Streamlit Cloud y Render, sin archivos privados nuevos."""
import os

def secreto(name,default=None):
    aliases={"credenciales_json":"USAER_GOOGLE_CREDENTIALS_JSON","token_json":"USAER_GOOGLE_TOKEN_JSON"}
    value=os.environ.get(name,os.environ.get(aliases.get(name,name)))
    if value is not None:return value
    if name=="credenciales_json" and os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        from pathlib import Path
        return Path(os.environ["GOOGLE_APPLICATION_CREDENTIALS"]).read_text(encoding="utf-8")
    try:
        import streamlit as st
        return st.secrets.get(name,default)
    except (FileNotFoundError,KeyError):return default

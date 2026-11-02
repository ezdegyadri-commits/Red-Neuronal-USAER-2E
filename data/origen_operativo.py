"""Streamlit conserva su base vigente mientras SQL se valida por separado."""
import os

def usar_sql():
    if os.getenv('DISABLE_SQL','').strip().lower() in {'1','true','yes'}:return False
    source=os.getenv('USAER_STREAMLIT_DATA_SOURCE')
    if source is None:
        try:
            import streamlit as st
            source=st.secrets.get('USAER_STREAMLIT_DATA_SOURCE','central')
        except (FileNotFoundError,KeyError):source='central'
    source=str(source or 'central').strip().lower()
    if source not in {'central','postgresql'}:raise ValueError('Origen operativo no reconocido; no se cambiará la base de escritura.')
    return source=='postgresql'

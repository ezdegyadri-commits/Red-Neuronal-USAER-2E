"""Aviso persistente; no modifica capturas, bases, widgets ni navegación."""
import streamlit as st
ERROR_CONEXION='Error de conexión: Tus datos están a salvo, intenta guardar de nuevo'
def avisar(prefix):
    st.session_state[prefix+'_conexion_error']=True
    # Streamlit prohíbe dibujar elementos desde ciertos callbacks de fragmento.
    try:
        from streamlit.runtime.scriptrunner_utils.script_run_context import ThreadState
        if ThreadState.get().in_fragment_callback:return
    except Exception:pass
    st.error(ERROR_CONEXION)
def mostrar(prefix):
    if st.session_state.get(prefix+'_conexion_error'):st.error(ERROR_CONEXION)
def confirmado(prefix):
    st.session_state.pop(prefix+'_conexion_error',None)

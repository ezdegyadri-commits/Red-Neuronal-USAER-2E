"""Activar la base central sin descartar documentos o trabajos pendientes."""
import threading
import streamlit as st
from data.origen_operativo import usar_sql
VERSION='C1'
_lock=threading.RLock()
_aplicada=False

def preparar():
    global _aplicada
    from data import repository as repo
    with _lock:
        # También sustituye la función que conservaba el módulo importado antes
        # del despliegue. Los métodos existentes resuelven este global al llamarse.
        repo.usar_sql=usar_sql
        if not _aplicada:
            repo.clear_alumnos_cache()
            _aplicada=True
    state=st.session_state
    if state.get('_operacion_activada')!=VERSION:
        # Solo una proyección de lectura. Nunca _doc, _value, _cola, _pending,
        # _trabajo_io, eventos, selecciones, filtros ni credenciales de sesión.
        for key in list(state):
            if key.startswith('_padron_autorizado_'):state.pop(key,None)
        state['_operacion_activada']=VERSION

"""Sondeos colaborativos sin bloquear el hilo de edición ni pisar un borrador."""
import streamlit as st
from services import planeacion as s
from services.trabajos_documento import enviar


def consultar(key, operacion, *args, firma=None):
    state=st.session_state;cuenta=s.identidad()['cuenta'];job=state.get(key)
    if job:
        if job['cuenta']!=cuenta:raise PermissionError('La consulta pendiente pertenece a otra cuenta.')
        if job.get('firma')!=firma:
            # Una respuesta iniciada antes de cambiar la versión no puede
            # volver a ocultar los aportes que ya llegaron al documento.
            state.pop(key);job=None
    if job:
        if not job['future'].done():return None
        state.pop(key)
        return job['future'].result()
    state[key]={'cuenta':cuenta,'firma':firma,'future':enviar(s.identidad(),state.get('escuelas_permitidas',''),operacion,*args)}
    return None

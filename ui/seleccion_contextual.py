"""Selección reversible de contexto: no pedir elegir la única opción disponible."""
import streamlit as st


def elegir(label,opciones,*,key,format_func=str,**kwargs):
    valores=list(opciones)
    from services.navegacion_planeaciones import habilitada
    if habilitada() and len(valores)==1:
        st.session_state[key]=valores[0]
        st.caption(label+': '+str(format_func(valores[0])))
        return valores[0]
    return st.selectbox(label,valores,key=key,format_func=format_func,**kwargs)

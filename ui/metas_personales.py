"""Formato de junta con captura única y recuperación por docente y escuela."""
from copy import deepcopy
import json
import time
import streamlit as st
from services import metas_personales as s


def _guardar_pendiente(key,manual=False):
    if not st.session_state.get(key+'_pending'):return True
    if not manual and (st.session_state.get(key+'_requiere_accion') or time.monotonic()-st.session_state.get(key+'_ultimo_intento',0)<15):return False
    captura=st.session_state[key+'_borrador']
    if captura.get('Cuenta')!=s.identidad()['cuenta']:raise PermissionError('La captura no corresponde a la cuenta activa.')
    st.session_state[key+'_ultimo_intento']=time.monotonic()
    try:
        doc=st.session_state.get(key+'_doc',{})
        extra={'periodo':captura['Periodo']} if 'Periodo' in captura else {}
        nuevo=s.guardar(captura['ID_Escuela'],captura['Fecha_Sesion'],captura['Filas'],doc.get('Revision',''),**extra)
        st.session_state[key+'_doc']=nuevo;st.session_state[key+'_pending']=False
        st.session_state[key+'_borrador'].update({k:deepcopy(nuevo[k]) for k in ('Filas','Periodo','Area') if k in nuevo})
        st.session_state.pop(key+'_error',None);st.session_state.pop(key+'_requiere_accion',None)
        return True
    except Exception as exc:
        st.session_state[key+'_error']=str(exc) if isinstance(exc,(ValueError,PermissionError,RuntimeError)) else 'La base central no confirmó el guardado. Puedes reintentar o descargar el respaldo.'
        from data.google import GoogleTemporal
        st.session_state[key+'_requiere_accion']=isinstance(exc,(ValueError,PermissionError,RuntimeError)) and not isinstance(exc,GoogleTemporal)
        return False


@st.fragment(run_every=15)
def _estado_guardado(key):
    # Continuar los envíos de otras escuelas/sesiones sin bloquear la captura actual.
    try:cuenta=s.identidad()['cuenta']
    except PermissionError:
        st.caption('Se requiere recuperar la sesión para confirmar el guardado. La captura pendiente no se descartó.');return
    for k,v in list(st.session_state.items()):
        if k.startswith('metas_') and k.endswith('_pending') and v and st.session_state.get(k[:-8]+'_borrador',{}).get('Cuenta')==cuenta:
            _guardar_pendiente(k[:-8])
    if st.session_state.get(key+'_pending'):
        st.warning(st.session_state.get(key+'_error','Metas pendientes de envío agrupado. Conserva esta pestaña abierta o confirma con Guardar metas.'))
    elif st.session_state.get(key+'_doc'):
        st.caption('Guardado confirmado · '+st.session_state[key+'_doc'].get('Guardado_En',''))
    else:st.caption('Formato listo para comenzar.')


def proteger_salida(key):
    """No descartar metas pendientes al cerrar una sesión compartida."""
    cuenta=str(st.session_state.get('usuario',''))
    keys=[k[:-8] for k,v in list(st.session_state.items()) if k.startswith('metas_') and k.endswith('_pending') and v and st.session_state.get(k[:-8]+'_borrador',{}).get('Cuenta')==cuenta]
    if not keys:return True
    st.warning('Hay metas personales sin confirmación central. Guarda o descarga cada respaldo antes de cerrar.')
    for p in keys:
        st.download_button('Respaldar metas pendientes',json.dumps(st.session_state[p+'_borrador'],ensure_ascii=False,indent=2),file_name='metas-pendientes.json',mime='application/json',key=key+'_'+p+'_respaldo')
    if st.button('Reintentar guardado de metas',key=key+'_reintentar_metas'):
        resultados=[_guardar_pendiente(p,manual=True) for p in keys]
        if all(resultados):st.success('Metas guardadas. Ya puedes cerrar sesión.');return True
    return st.checkbox('Ya descargué los respaldos de metas; continuar al cierre',key=key+'_metas_respaldadas')




def page(fecha_sesion=None):
    from ui.metas_instrumento import page as instrumento
    return instrumento(fecha_sesion)

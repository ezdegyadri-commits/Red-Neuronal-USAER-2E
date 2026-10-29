"""Acuses de Planeación: actualizar la UI solo desde el hilo de su sesión."""
from copy import deepcopy
import time
from uuid import uuid4
import streamlit as st
from services import planeacion as s
from services.trabajos_documento import enviar
from services.planeacion_guardado_estado import diagnostico
from services.reintentos_edicion import programar


def _en_callback_fragmento() -> bool:
    try:
        from streamlit.runtime.scriptrunner_utils.script_run_context import ThreadState
        return bool(ThreadState.get().in_fragment_callback)
    except Exception:
        return False


def _fallo(prefix, exc):
    st.session_state[prefix+'_pending']=True
    detalle=programar(st.session_state,prefix,diagnostico(exc))
    st.session_state[prefix+'_guardado_diagnostico']=detalle
    st.session_state[prefix+'_error']=detalle['causa']
    st.session_state[prefix+'_io_error_nonce']=st.session_state.get(prefix+'_papel_nonce',st.session_state.get(prefix+'_nonce',''))
    if _en_callback_fragmento():
        st.session_state[prefix+'_toast_pendiente']='No se confirmó el envío. Tu edición sigue disponible; consulta el aviso de guardado.'
    else:
        st.toast('No se confirmó el envío. Tu edición sigue disponible; consulta el aviso de guardado.',icon='⚠️')


def persistir(prefix, estado=None, automatic=False, aporte=False):
    state=st.session_state
    actor={**s.identidad(),'origen_editor':state.setdefault(prefix+'_origen_io',uuid4().hex)}
    doc=state[prefix+'_doc']
    key=prefix+'_trabajo_io';job=state.get(key)
    if job:
        if (job['cuenta'],job['documento'])!=(actor['cuenta'],doc['id']):
            raise PermissionError('El envío pendiente pertenece a otra cuenta o documento.')
        if not job['future'].done():return False
        state.pop(key)
        try:
            saved=job['future'].result()  # done(): nunca espera una petición remota.
            if aporte:
                igual=state[prefix+'_filas']==job['filas'] and state.get(prefix+'_obs','')==job['obs']
                state[prefix+'_doc']=saved
            else:
                from services.planeacion_compartida import _tres_vias
                igual=doc==job['enviado'] and state.get(prefix+'_estado_pendiente',job['estado'])==job['estado']
                state[prefix+'_doc']=saved if igual else _tres_vias(job['enviado'],doc,saved)
            state[prefix+'_pending']=not igual
            for suffix in ('_error','_guardado_diagnostico','_retry_at','_pdf','_io_error_nonce','_fallos_io'):
                state.pop(prefix+suffix,None)
            if igual:
                state.pop(prefix+'_estado_pendiente',None)
                if job['nonce']:
                    state[prefix+('_ack' if aporte else '_papel_aceptado')]=job['nonce']
                    if not aporte:state[prefix+'_papel_legacy']=True
                return True
            # El acuse anterior no confirma la escritura posterior del usuario.
            return False
        except Exception as exc:
            _fallo(prefix,exc);return False
    state[prefix+'_pending']=True
    intervalo=15 if aporte or doc['metadatos'].get('vista_formato')=='guia' else 60
    if automatic and (time.monotonic()<state.get(prefix+'_retry_at',0) or time.monotonic()-state.get(prefix+'_last_attempt',0)<intervalo):return False
    if not automatic:state.pop(prefix+'_fallos_io',None)
    estado=estado or state.get(prefix+'_estado_pendiente') or doc.get('estado','BORRADOR')
    snapshot=deepcopy(doc)
    job={'cuenta':actor['cuenta'],'documento':doc['id'],'enviado':snapshot,'estado':estado,
         'nonce':state.get(prefix+('_nonce' if aporte else '_papel_nonce'),'')}
    try:
        if aporte:
            job.update(filas=deepcopy(state[prefix+'_filas']),obs=state.get(prefix+'_obs',''))
            future=enviar(actor,state.get('escuelas_permitidas',''),s.guardar_aportacion,snapshot,job['filas'],job['obs'])
        else:
            future=enviar(actor,state.get('escuelas_permitidas',''),s.guardar,snapshot,estado)
            state[prefix+'_estado_pendiente']=estado
        job['future']=future;state[key]=job
        state[prefix+'_last_attempt']=time.monotonic()
    except Exception as exc:_fallo(prefix,exc)
    return False


@st.fragment(run_every=1)
def acuses(prefix, aporte=False):
    """Solo consulta un Future local; ningún tick hace lecturas de Sheets."""
    if st.session_state.get(prefix+'_toast_pendiente') and not _en_callback_fragmento():
        st.toast(st.session_state.pop(prefix+'_toast_pendiente'),icon='⚠️')
    if prefix+'_trabajo_io' not in st.session_state:return
    persistir(prefix,automatic=True,aporte=aporte)
    if prefix+'_trabajo_io' not in st.session_state:
        # Un acuse necesita actualizar la hoja y el indicador de cierre de sesión.
        st.rerun(scope='app')

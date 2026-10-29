"""Una captura EPP puede seguir editándose durante la escritura remota."""
from copy import deepcopy
import time
import streamlit as st
from services import epp as s, epp_papel as papel
from services.trabajos_documento import enviar
from services.planeacion_guardado_estado import diagnostico
from services.reintentos_edicion import programar


def _escribir(doc, cola):
    resultado={};error=None
    for area,item in cola.items():
        try:
            saved=s.guardar_cambios(doc,area,item['base'],papel.contenido(doc,area),item['revision'])
            resultado[area]=saved;doc['partes'][area]=saved
        except Exception as exc:
            error=exc;break
    return resultado,error


def _en_callback_fragmento() -> bool:
    try:
        from streamlit.runtime.scriptrunner_utils.script_run_context import ThreadState
        return bool(ThreadState.get().in_fragment_callback)
    except Exception:
        return False


def guardar(p,manual=False):
    state=st.session_state;cuenta=s.actor()['cuenta'];key=p+'_trabajo_io'
    cola=state.get(p+'_cola',{});doc=state[p+'_doc'];job=state.get(key)
    if job:
        if (job['cuenta'],job['documento'])!=(cuenta,doc['id']):raise PermissionError('El envío EPP pertenece a otra cuenta o informe.')
        if not job['future'].done():return False
        state.pop(key)
        try:
            resultados,error=job['future'].result()
            for area,saved in resultados.items():
                local=papel.contenido(doc,area);sent=papel.contenido(job['enviado'],area)
                merged=s.combinar(sent,local,saved['contenido'])
                doc['partes'][area]={**saved,'contenido':merged}
                if local==sent:cola.pop(area,None)
                else:cola[area]={'base':deepcopy(saved['contenido']),'revision':saved['revision']}
            if error:raise error
            state.pop(p+'_diagnostico',None);state.pop(p+'_reintentar_en',None);state.pop(p+'_io_error_nonce',None);state.pop(p+'_fallos_io',None)
            state[p+'_pending']=bool(cola)
            if not cola:
                state.pop(p+'_huella_pendiente',None)
                state[p+'_aceptado']=job['nonce']
                state[p+'_agrupar_hasta']=time.monotonic()+30
                return True
            return False
        except Exception as exc:
            detalle=programar(state,p,diagnostico(exc),fecha='_reintentar_en');state[p+'_diagnostico']=detalle
            state[p+'_io_error_nonce']=state.get(p+'_nonce','')
            state[p+'_pending']=bool(cola)
            if _en_callback_fragmento():
                state[p+'_toast_pendiente']='No se confirmó toda la EPP. Tu captura se conserva; consulta el aviso.'
            else:
                st.toast('No se confirmó toda la EPP. Tu captura se conserva; consulta el aviso.',icon='⚠️')
            return False
    if not cola:return True
    if state.get(p+'_cuenta',cuenta)!=cuenta:raise PermissionError('La captura EPP pertenece a otra cuenta.')
    if not manual and time.monotonic()<max(state.get(p+'_reintentar_en',0),state.get(p+'_agrupar_hasta',0)):return False
    if manual:state.pop(p+'_fallos_io',None)
    try:
        future=enviar(s.actor(),state.get('escuelas_permitidas',''),_escribir,doc,cola)
        state[key]={'cuenta':cuenta,'documento':doc['id'],'enviado':deepcopy(doc),'future':future,'nonce':state.get(p+'_nonce','')}
    except Exception as exc:
        state[p+'_diagnostico']=programar(state,p,diagnostico(exc),fecha='_reintentar_en')
        state[p+'_io_error_nonce']=state.get(p+'_nonce','')
    return False


@st.fragment(run_every=1)
def acuses(p):
    if st.session_state.get(p+'_toast_pendiente') and not _en_callback_fragmento():
        st.toast(st.session_state.pop(p+'_toast_pendiente'),icon='⚠️')
    if p+'_trabajo_io' not in st.session_state:return
    guardar(p)
    if p+'_trabajo_io' not in st.session_state:st.rerun(scope='app')

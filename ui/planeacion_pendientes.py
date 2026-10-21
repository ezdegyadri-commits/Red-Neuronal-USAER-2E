"""Cola de sesión: navegar no descarta ni declara persistida una edición."""
from copy import deepcopy
import hashlib
import json
import streamlit as st
import time


def raiz(prefix):
    return st.session_state.get(prefix+'_raiz',prefix.rsplit('_',1)[0])


def pendientes(base):
    return [k[:-4] for k,v in list(st.session_state.items())
            if k.startswith(base+'_') and k.endswith('_doc') and isinstance(v,dict)
            and v.get('id') and st.session_state.get(k[:-4]+'_pending')]


def conservar(prefix,base):
    """Protege la edición antes de reutilizar su espacio para otro documento."""
    payload={s:deepcopy(st.session_state[prefix+s]) for s in
             ('_doc','_filas','_obs','_pending','_error','_retry_at','_last_attempt','_estado_pendiente',
              '_intento','_intervalo','_papel_nonce','_papel_aceptado')
             if prefix+s in st.session_state}
    firma=hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True,default=str).encode()).hexdigest()[:24]
    destino=base+'_envio_'+firma
    for s,valor in payload.items():st.session_state[destino+s]=valor
    st.session_state[destino+'_pending']=True
    st.session_state[destino+'_origen']=prefix
    st.session_state[destino+'_raiz']=base
    # No es un acuse: sigue pendiente en destino, sin tocar el documento central.
    st.session_state[prefix+'_pending']=False
    return destino


def reintentar(base):
    from ui import planeacion as u
    activo=st.session_state.get(base+'_activa') if not st.session_state.get(base+'_viva_entrada') else None
    lista=[p for p in pendientes(base) if p!=activo and time.monotonic()>=st.session_state.get(p+'_retry_at',0)]
    lista.sort(key=lambda p:max(st.session_state.get(p+'_last_attempt',0),st.session_state.get(p+'_intento',0)))
    for prefix in lista[:2]:u._guardar_edicion_pendiente(prefix,automatic=True)
    return [p for p in pendientes(base) if p!=activo]


@st.fragment(run_every=15)
def panel(base):
    lista=reintentar(base)
    if not lista:return
    st.info('Hay ediciones pendientes de envío. Puedes abrir otra planeación: '
            'se conservan en esta sesión y se reintentan por separado. '
            'No cierres esta pestaña sin confirmar su guardado o descargar el respaldo.')
    with st.expander('Ver ediciones pendientes y respaldos',expanded=False):
        for prefix in lista:
            doc=st.session_state[prefix+'_doc'];datos=doc.get('datos',{})
            grados=', '.join(sorted({str(a.get('Grado',''))+' '+str(a.get('Grupo','')) for a in datos.get('Alumnos',[])}))
            st.write(' · '.join(filter(None,[datos.get('Escuela regular'),grados,datos.get('Periodo') or doc.get('formato')])))
            st.caption(st.session_state.get(prefix+'_error','Pendiente de confirmación del servidor.'))
            respaldo=doc if prefix+'_filas' not in st.session_state else {'documento':doc,'filas':st.session_state[prefix+'_filas'],'observaciones':st.session_state.get(prefix+'_obs','')}
            st.download_button('Descargar respaldo de esta edición',json.dumps(respaldo,ensure_ascii=False,indent=2),
                file_name='planeacion-pendiente-'+doc['id']+'.json',mime='application/json',key=prefix+'_cola_respaldo')
            if st.button('Continuar esta edición',key=prefix+'_cola_continuar'):
                st.session_state[base+'_activa']=prefix
                st.session_state[base+'_viva_entrada']=False
                st.rerun(scope='app')

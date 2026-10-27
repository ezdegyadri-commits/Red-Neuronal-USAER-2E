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
             ('_doc','_filas','_filas_retiradas','_obs','_pending','_error','_retry_at','_last_attempt','_estado_pendiente',
              '_intento','_intervalo','_papel_nonce','_papel_aceptado','_guardado_diagnostico')
             if prefix+s in st.session_state}
    firma=hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True,default=str).encode()).hexdigest()[:24]
    destino=base+'_envio_'+firma
    for s,valor in payload.items():st.session_state[destino+s]=valor
    # Un Future no se copia: su acuse sigue al mismo borrador conservado.
    if prefix+'_trabajo_io' in st.session_state:
        st.session_state[destino+'_trabajo_io']=st.session_state.pop(prefix+'_trabajo_io')
    st.session_state[destino+'_pending']=True
    st.session_state[destino+'_origen']=prefix
    st.session_state[destino+'_raiz']=base
    # No es un acuse: sigue pendiente en destino, sin tocar el documento central.
    st.session_state[prefix+'_pending']=False
    return destino


def controles_guardado(prefix,key):
    """Diagnóstico y recuperación visibles tanto en el módulo como al salir."""
    doc=st.session_state.get(prefix+'_doc')
    if not doc:return
    detalle=st.session_state.get(prefix+'_guardado_diagnostico')
    if detalle:
        st.warning(detalle['causa'])
        st.caption(detalle['accion'])
    elif st.session_state.get(prefix+'_error'):
        st.warning(st.session_state[prefix+'_error'])
        st.caption('Descarga el respaldo antes de cerrar. Puedes reintentar sin crear otra planeación.')
    else:st.caption('Hay una edición pendiente de confirmación central; esto no equivale a un guardado confirmado.')
    respaldo=doc if prefix+'_filas' not in st.session_state else {
        'documento':doc,'filas':st.session_state[prefix+'_filas'],'observaciones':st.session_state.get(prefix+'_obs',''),
        'filas_retiradas':st.session_state.get(prefix+'_filas_retiradas',[]),'cuenta_aporte':st.session_state.get('usuario','')}
    if prefix+'_filas' in st.session_state:
        try:
            from services.planeacion import identidad
            respaldo['area_aporte']=identidad()['area']
        except PermissionError:respaldo['area_aporte']=''
    st.download_button('Descargar respaldo pendiente',json.dumps(respaldo,ensure_ascii=False,indent=2),
        file_name='planeacion-pendiente-'+doc['id']+'.json',mime='application/json',key=key+'_respaldo')
    if detalle and detalle.get('tipo')=='archivado' and st.button('Restaurar este borrador y reintentar',key=key+'_restaurar'):
        from services import planeacion as s
        from ui.planeacion import _guardar_edicion_pendiente
        try:
            versiones=[d for d in s.versiones_actuales() if d['id']==doc['id']]
            if not versiones:raise ValueError('No se encontró la versión central; conserva el respaldo y vuelve a intentar.')
            if versiones[-1]['metadatos'].get('borrador_eliminado'):s.restaurar_borrador(versiones[-1])
            # Mantener la revisión base local: el guardado normal debe conciliar,
            # no reemplazar a ciegas el documento restaurado.
            if _guardar_edicion_pendiente(prefix):st.success('Borrador restaurado y edición guardada en la base central.')
        except Exception as exc:
            from services.planeacion_guardado_estado import diagnostico
            st.session_state[prefix+'_guardado_diagnostico']=diagnostico(exc)
            st.error(st.session_state[prefix+'_guardado_diagnostico']['causa'])
    if st.button('Reintentar guardado',key=key+'_reintentar'):
        from ui.planeacion import _guardar_edicion_pendiente
        if _guardar_edicion_pendiente(prefix):st.success('Guardado confirmado. La edición ya está en la base central.')


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
            controles_guardado(prefix,prefix+'_cola_diagnostico')
            respaldo=doc if prefix+'_filas' not in st.session_state else {'documento':doc,'filas':st.session_state[prefix+'_filas'],'observaciones':st.session_state.get(prefix+'_obs','')}
            st.download_button('Descargar respaldo de esta edición',json.dumps(respaldo,ensure_ascii=False,indent=2),
                file_name='planeacion-pendiente-'+doc['id']+'.json',mime='application/json',key=prefix+'_cola_respaldo')
            if st.button('Continuar esta edición',key=prefix+'_cola_continuar'):
                st.session_state[base+'_activa']=prefix
                st.session_state[base+'_viva_entrada']=False
                st.rerun(scope='app')

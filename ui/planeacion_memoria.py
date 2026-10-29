"""Consulta asíncrona del expediente y revisión contextual, sin bloquear el editor."""
from copy import deepcopy
import time
import streamlit as st
from services import planeacion as s,memoria_pedagogica as memoria


@st.fragment(run_every=2)
def _espera(prefix):
    job=st.session_state.get(prefix+'_memoria_trabajo')
    if job and job['future'].done():st.rerun(scope='app')
    st.status('Consultando EPP, avances y registros del equipo… Puedes seguir editando.',state='running')


def actualizar(prefix):
    doc=st.session_state[prefix+'_doc'];actor=s.autorizar(doc)
    if doc.get('metadatos',{}).get('modalidad_planeacion')!='individual':return True
    key=prefix+'_memoria_trabajo';job=st.session_state.get(key);scope=(doc['id'],actor['cuenta'])
    if job and job['scope']!=scope:st.session_state.pop(key,None);job=None
    if job:
        if not job['future'].done():_espera(prefix);return False
        st.session_state.pop(key,None)
        try:
            fresh=job['future'].result();s.autorizar(fresh)
            if fresh['id']!=doc['id']:raise PermissionError('El contexto cambió.')
            result=deepcopy(st.session_state[prefix+'_doc'])
            for campo in ('fuentes','fuentes_pendientes','version_contexto','contexto_cargado','catalogo_nee_actual'):
                if campo in fresh['metadatos']:result['metadatos'][campo]=deepcopy(fresh['metadatos'][campo])
            st.session_state[prefix+'_doc']=result
            st.session_state.pop(prefix+'_memoria_error',None)
        except Exception:
            st.session_state[prefix+'_memoria_error']='No se completó la consulta de todos los antecedentes. Se conserva la última copia; puedes editar y reintentar.'
        st.session_state[prefix+'_memoria_consulta']=(scope,time.monotonic())
    check=st.session_state.get(prefix+'_memoria_consulta')
    if not check or check[0]!=scope or time.monotonic()-check[1]>120:
        from services.trabajos_documento import enviar
        try:
            future=enviar(actor,st.session_state.get('escuelas_permitidas',''),s.preparar_contexto,doc)
            st.session_state[key]={'scope':scope,'future':future}
            _espera(prefix);return False
        except Exception:
            st.session_state[prefix+'_memoria_error']='La consulta está ocupada. Tu documento sigue editable; reintenta en unos momentos.'
            return False
    if st.session_state.get(prefix+'_memoria_error'):st.warning(st.session_state[prefix+'_memoria_error'])
    return True


def panel(prefix,aid,persist):
    doc=st.session_state[prefix+'_doc'];mem=memoria.construir(doc,aid)
    conflictos=[c for c in mem['conflictos'] if not c['resuelta']]
    exp=st.expander('Memoria del alumno · '+str(len(mem['hechos']))+' hallazgos'+(' · revisar contradicciones' if conflictos else ''),expanded=bool(conflictos))
    with exp:
        st.caption('Evidencia documentada, referentes oficiales e instrucciones docentes se mantienen separados. Un plan anterior no acredita un logro.')
        for r in mem['hechos']:
            st.write(r['texto']);st.caption(r['tipo']+' · '+(r['fecha'] or 'Fecha no registrada')+' · '+r['temporalidad']+' · '+r['referencia'])
        for text in mem['faltantes']:st.info(text)
        if conflictos:
            st.warning('Hay señales de información contradictoria. Confirma qué registro describe mejor el desempeño actual; el sistema no decidirá por fecha o longitud.')
            with st.form(prefix+'_memoria_resolver_'+str(aid)):
                decisiones=[]
                for c in conflictos:
                    labels={r['id']:(r.get('fecha') or 'Sin fecha')+' · '+r['texto'] for r in c['registros']}
                    choice=st.radio('Desempeño actual · '+c['competencia'],list(labels),index=None,format_func=labels.get,key=prefix+'_memoria_'+c['id'])
                    decisiones.append((c['id'],choice))
                if st.form_submit_button('Confirmar información actual'):
                    try:
                        result=doc
                        for cid,fuente in decisiones:
                            if fuente:result=memoria.resolver(result,cid,fuente)
                        st.session_state[prefix+'_doc']=result;persist(prefix,automatic=True);st.rerun()
                    except (ValueError,PermissionError) as exc:st.warning(str(exc))
        if st.button('Actualizar antecedentes',key=prefix+'_memoria_refresh_'+str(aid)):
            st.session_state.pop(prefix+'_memoria_consulta',None);st.rerun()
    return mem

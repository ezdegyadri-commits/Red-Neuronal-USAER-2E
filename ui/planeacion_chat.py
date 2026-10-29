"""Chat contextual compacto: propuestas revisables junto al formato individual."""
from copy import deepcopy
import streamlit as st
from services import planeacion as s,planeacion_chat_contextual as chat


@st.fragment(run_every=2)
def _estado(key):
    job=st.session_state.get(key)
    if not job:return
    if job['future'].done():st.rerun(scope='app')
    st.status('Preparando ajustes con la memoria del alumno… Tu documento sigue editable.',state='running')


def _guardar(prefix,result,persist):
    st.session_state[prefix+'_doc']=result
    st.session_state.pop(prefix+'_pdf',None)
    persist(prefix,automatic=True)


def render_asistente_dialogo(prefix,persist,expandido=True):
    doc=st.session_state[prefix+'_doc']
    if doc.get('metadatos',{}).get('modalidad_planeacion')!='individual':
        st.caption('El chat contextual se abre desde la planeación individual del alumno.');return
    s.autorizar(doc,True)
    from ui.planeacion_memoria import actualizar,panel
    ready=actualizar(prefix);doc=st.session_state[prefix+'_doc']
    alumnos={str(a['ID_Alumno']):a['Nombre del alumno'] for a in doc['datos']['Alumnos']}
    from ui.seleccion_contextual import elegir
    aid=elegir('Alumno de la conversación',list(alumnos),format_func=alumnos.get,key=prefix+'_chat_alumno_'+doc['id'])
    state=chat.conversacion(doc,aid);base=prefix+'_chat_'+doc['id']+'_'+aid;jobkey=base+'_trabajo'
    memoria=panel(prefix,aid,persist)
    st.markdown('**Asistente pedagógico**')
    for m in state['mensajes'][-6:]:
        with st.chat_message(m['rol']):
            st.write(m['texto'])
            if m.get('rol')=='user':st.caption(m.get('tipo','Instrucción temporal')+(' · incorporada al expediente' if m.get('confirmada') else ' · no es un hallazgo confirmado'))
    if len(state['mensajes'])>6:
        with st.expander('Conversación anterior'):
            for m in state['mensajes'][:-6]:st.write(('Docente: ' if m['rol']=='user' else 'Asistente: ')+m['texto'])
    job=st.session_state.get(jobkey)
    if job and job['future'].done():
        st.session_state.pop(jobkey,None)
        try:
            respuesta=job['future'].result()
            _guardar(prefix,chat.adjuntar_respuesta(st.session_state[prefix+'_doc'],job['peticion'],respuesta),persist)
            st.rerun()
        except (ValueError,PermissionError,RuntimeError) as exc:st.warning(str(exc))
        except Exception:st.warning('No se completó la propuesta. Tu conversación y el formato se conservan; puedes reintentar con una indicación.')
    job=st.session_state.get(jobkey)
    if job:_estado(jobkey)
    with st.expander('Uso de la indicación y contexto que analizará la IA'):
        tipo=st.radio('Esta aportación es',chat.TIPOS,key=base+'_tipo')
        st.caption('Una observación pendiente solo se incorporará al expediente si la confirmas expresamente. No se envían archivos completos.')
        st.write({'hallazgos':[r['texto'] for r in memoria['hechos']],'faltantes':memoria['faltantes']})
    consent=st.checkbox('Permitir propuestas con la IA institucional usando este contexto minimizado',key=base+'_consent')
    texto=st.chat_input('Indica qué necesitas ajustar...',key=base+'_input',disabled=bool(job) or not ready)
    if texto:
        try:
            result,turn=chat.registrar(st.session_state[prefix+'_doc'],aid,texto,tipo)
            _guardar(prefix,result,persist)
            if not consent:
                st.info('La indicación quedó conservada. Autoriza el uso de la IA para pedir una propuesta; no se envió información.')
            else:
                peticion=chat.preparar(result,aid,turn['id'])
                from ai.documento_json import enviar
                from ai.planeacion import configuracion_trabajo
                st.session_state[jobkey]={'peticion':peticion,'future':enviar(chat.generar_autorizado,result,peticion,configuracion_trabajo(),s.identidad(),st.session_state.get('escuelas_permitidas',''))}
                st.rerun()
        except (ValueError,PermissionError,RuntimeError) as exc:st.warning(str(exc))
    state=chat.conversacion(st.session_state[prefix+'_doc'],aid)
    sin_respuesta=[m for m in state['mensajes'] if m['rol']=='user' and not any(a.get('turno')==m['id'] for a in state['mensajes'])]
    if sin_respuesta and consent and not st.session_state.get(jobkey) and ready:
        if st.button('Solicitar propuesta para la última indicación',key=base+'_reintentar'):
            try:
                result=st.session_state[prefix+'_doc'];peticion=chat.preparar(result,aid,sin_respuesta[-1]['id'])
                from ai.documento_json import enviar
                from ai.planeacion import configuracion_trabajo
                st.session_state[jobkey]={'peticion':peticion,'future':enviar(chat.generar_autorizado,result,peticion,configuracion_trabajo(),s.identidad(),st.session_state.get('escuelas_permitidas',''))}
                st.rerun()
            except (ValueError,PermissionError,RuntimeError) as exc:st.warning(str(exc))
    p=state.get('pendiente')
    if p:
        respuesta=p['respuesta']
        if respuesta.get('provisional'):st.info('Propuesta provisional: faltan datos por confirmar. No representa un resultado de evaluación.')
        for falta in respuesta.get('faltantes',[]):st.info(falta)
        changes=respuesta['cambios'];ediciones={}
        if changes:
            st.caption('Solo cambiarán estos apartados. NEE confirmadas y otras celdas se conservan.')
            with st.form(base+'_revisar_'+p['peticion']['turno']):
                for c in changes:
                    t=p['peticion']['destinos'][c['destino']]
                    st.caption(t['apartado']+' · Antes: '+(t['anterior'][:300] or 'Vacío'))
                    ediciones[c['destino']]=st.text_area(t['apartado'],value=c['texto'],key=base+'_edicion_'+p['peticion']['turno']+'_'+c['destino'])
                aceptar=st.form_submit_button('Aceptar cambios',type='primary')
            if aceptar:
                try:_guardar(prefix,chat.aplicar(st.session_state[prefix+'_doc'],aid,ediciones),persist);st.toast('Cambios incorporados al borrador.');st.rerun()
                except (ValueError,PermissionError) as exc:st.warning(str(exc))
            with st.expander('Fundamento de los cambios'):
                for c in changes:
                    st.write({'apartado':p['peticion']['destinos'][c['destino']]['apartado'],'evidencias':c['evidencias'],'referentes':[r for r in p['peticion'].get('fundamento_curricular',[]) if r['id'] in c['referentes']]})
        with st.expander('Revisión de los 14 indicadores y coherencia'):
            st.caption('Comprobación orientativa de la propuesta. La valoración pedagógica corresponde al equipo; no certifica cumplimiento.')
            st.dataframe(p.get('revision_calidad',[]),hide_index=True)
            for alerta in p.get('alertas',[]):st.warning(alerta)
        if st.button('Descartar propuesta',key=base+'_descartar'):
            _guardar(prefix,chat.descartar(st.session_state[prefix+'_doc'],aid),persist);st.rerun()
    obskey=base+'_observacion_trabajo'
    obsjob=st.session_state.get(obskey)
    if obsjob:
        if obsjob['future'].done():
            st.session_state.pop(obskey,None)
            try:
                completed=obsjob['future'].result()
                result=deepcopy(st.session_state[prefix+'_doc']);actual=chat.conversacion(result,aid)
                confirmado=next(m for m in chat.conversacion(completed,aid)['mensajes'] if m['id']==obsjob['turno'])
                for m in actual['mensajes']:
                    if m['id']==confirmado['id']:m.update({k:v for k,v in confirmado.items() if k in ('confirmada','evento','confirmada_por')})
                result['metadatos'].setdefault('chat_contextual',{})[aid]=actual
                _guardar(prefix,result,persist);st.toast('Observación incorporada con fecha y autoría.');st.rerun()
            except Exception:st.warning('No se confirmó la incorporación. La observación se conserva como pendiente y puede reintentarse.')
        else:_estado(obskey)
    pendientes=[m for m in state['mensajes'] if m['rol']=='user' and m.get('tipo')=='Observación pendiente' and not m.get('confirmada')]
    if pendientes:
        with st.expander('Incorporar una observación al expediente'):
            porid={m['id']:m for m in pendientes}
            mid=elegir('Observación a confirmar',list(porid),format_func=lambda i:porid[i]['texto'][:120],key=base+'_observar')
            confirmar=st.checkbox('Confirmo esta observación y su incorporación permanente al expediente',key=base+'_confirmar_'+mid)
            if st.button('Incorporar observación confirmada',disabled=not confirmar or bool(obsjob),key=base+'_expediente'):
                try:
                    from services.trabajos_documento import enviar
                    future=enviar(s.identidad(),st.session_state.get('escuelas_permitidas',''),chat.confirmar_observacion,st.session_state[prefix+'_doc'],aid,mid)
                    st.session_state[obskey]={'future':future,'turno':mid};st.rerun()
                except Exception:st.warning('No se confirmó la incorporación. Se conserva como pendiente; reintenta sin volver a capturarla.')

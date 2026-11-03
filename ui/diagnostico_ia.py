"""Comprobación autorizada para Dirección; usa únicamente un caso ficticio."""
import time
import streamlit as st
from services import diagnostico_ia as prueba

@st.fragment(run_every=2)
def _estado():
    job=st.session_state.get('_qa_ia_trabajo')
    if not job:return
    if job['future'].done():
        st.session_state.pop('_qa_ia_trabajo',None)
        try:
            st.session_state['_qa_ia_resultado']=job['future'].result()
            st.session_state['_qa_ia_segundos']=round(time.monotonic()-job['inicio'],2)
            st.session_state.pop('_qa_ia_error',None)
        except Exception as exc:
            from ui.planeacion_progreso import mensaje_error
            st.session_state['_qa_ia_error']=mensaje_error(exc)
        st.rerun(scope='app')
    st.status('Solicitando una estrategia con el caso ficticio…',state='running')

def pagina():
    from services.planeacion import identidad
    if not identidad().get('director'):
        st.error('Esta comprobación está reservada a Dirección.');return
    st.title('Prueba de IA con datos ficticios')
    st.caption('Mismo transporte, configuración y rol pedagógico de Planeación. No consulta expedientes ni modifica documentos.')
    st.info(prueba.CASO_FICTICIO)
    job=st.session_state.get('_qa_ia_trabajo')
    ultima=st.session_state.get('_qa_ia_ultima',0)
    espera=max(0,60-(time.monotonic()-ultima))
    if st.button('Solicitar estrategia de prueba',type='primary',disabled=bool(job) or espera>0,key='qa_ia_solicitar'):
        from ai.documento_json import enviar
        from ai.planeacion import configuracion_trabajo
        inicio=time.monotonic()
        st.session_state['_qa_ia_trabajo']={'future':enviar(prueba.generar,configuracion_trabajo()),'inicio':inicio}
        st.session_state['_qa_ia_ultima']=inicio
        st.session_state.pop('_qa_ia_resultado',None)
        st.rerun()
    if job:_estado()
    if st.session_state.get('_qa_ia_error'):st.error(st.session_state['_qa_ia_error'])
    if value:=st.session_state.get('_qa_ia_resultado'):
        st.success('Respuesta de IA recibida y validada · caso ficticio')
        st.caption('Tiempo de respuesta: '+str(st.session_state['_qa_ia_segundos'])+' s')
        for k,v in value.items():
            st.subheader(k.replace('_',' ').capitalize());st.write(v)
    if st.button('Volver a USAER',key='qa_ia_volver'):
        st.query_params.pop('diagnostico_ia',None);st.rerun()

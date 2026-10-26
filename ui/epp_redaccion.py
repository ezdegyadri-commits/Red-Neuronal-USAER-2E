"""Un asistente abierto bajo demanda; nada se transmite ni aplica al abrirlo."""
import streamlit as st
from services import epp_redaccion as servicio

def mostrar(prefix,doc,area,campo,aplicar):
    key=prefix+'_redactor_'+campo
    base=st.session_state.get(prefix+'_value',{}).get('campos',{}).get(campo,doc['partes'].get(area,{}).get('contenido',{}).get('campos',{}).get(campo,''))
    st.session_state[key+'_abierto']=True
    def cerrar():
        st.session_state[key+'_abierto']=False
        st.session_state.pop(prefix+'_redactor',None)
    @st.dialog('Asistente de redacción · '+campo,width='large',on_dismiss=cerrar)
    def dialogo():
        if st.button('Volver al apartado',key=key+'_cerrar'):
            cerrar();st.rerun(scope='app')
        ideas=st.text_area('Tus ideas u observaciones (opcional si ya hay resultados)',key=key+'_ideas',max_chars=3000)
        if st.button('Preparar texto para revisión',key=key+'_preparar'):
            try:
                st.session_state[key+'_resumen']=servicio.preparar(doc,area,campo,ideas)
                st.session_state[key+'_texto']=st.session_state[key+'_resumen']
                st.session_state.pop(key+'_propuesta',None)
                st.session_state.pop(key+'_consent',None)
            except (ValueError,PermissionError) as exc:st.warning(str(exc))
        if key+'_resumen' not in st.session_state:return
        resumen=st.text_area('Resumen que se enviará: retira nombres, domicilios y contactos',value=st.session_state[key+'_resumen'],key=key+'_texto',max_chars=10000)
        check=st.checkbox('Revisé el resumen y autorizo enviarlo a IA',key=key+'_consent')
        if st.button('Proponer redacción',disabled=not check,key=key+'_generar'):
            try:
                with st.spinner('Redactando a partir de tus hallazgos…'):
                    st.session_state[key+'_propuesta']=servicio.generar(resumen,campo)
                    st.session_state[key+'_resultado']=st.session_state[key+'_propuesta']
            except Exception:st.warning('No se completó la redacción. Tu texto se conserva y puedes continuar escribiendo.')
        if key+'_propuesta' not in st.session_state:return
        propuesta=st.text_area('Propuesta editable',value=st.session_state[key+'_propuesta'],key=key+'_resultado',max_chars=6000)
        def incorporar():
            try:aplicar(st.session_state[key+'_resultado'],base);st.session_state[key+'_aplicada']=True
            except (ValueError,RuntimeError,PermissionError) as exc:st.session_state[key+'_error']=str(exc)
        st.button('Usar esta redacción en el apartado',key=key+'_usar',on_click=incorporar,type='primary')
        if st.session_state.pop(key+'_aplicada',False):
            cerrar();st.rerun(scope='app')
        if st.session_state.get(key+'_error'):st.warning(st.session_state[key+'_error'])
    dialogo()

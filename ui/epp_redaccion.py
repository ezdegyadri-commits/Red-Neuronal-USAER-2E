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
                    st.session_state[key+'_propuesta']=servicio.generar(resumen,campo,area=area)
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


def mostrar_maestro(prefix, doc, area, aplicar):
    """Asistente maestro de redacción para el área activa: redacta cualquier apartado con un solo botón."""
    from services.epp_modelo import campos as campos_func
    from services.epp_colaborativa import omitido
    
    campos_lista = [c for c in campos_func(area) if not omitido(st.session_state.get(prefix+'_value',{}), c)]
    if not campos_lista:
        campos_lista = campos_func(area)
    if not campos_lista:
        st.info('Esta área no contiene campos textuales de redacción directa.')
        return

    key = prefix + '_redactor_maestro'
    st.session_state[key + '_abierto'] = True

    def cerrar():
        st.session_state[key + '_abierto'] = False
        st.session_state.pop(prefix + '_redactor_maestro_abierto', None)

    @st.dialog('✨ Asistente Maestro de Redacción · ' + area, width='large', on_dismiss=cerrar)
    def dialogo_maestro():
        c_top1, c_top2 = st.columns([0.72, 0.28])
        with c_top1:
            st.caption(f'Asistente inteligente para el área de **{area}**. Selecciona el apartado que deseas enriquecer:')
            motor_sel = st.radio(
                "Motor de IA",
                ["Gemini Pro (Google)", "ChatGPT (OpenAI)"],
                horizontal=True,
                key=key + "_motor_sel"
            )
            if "Gemini" in motor_sel:
                st.session_state['epp_motor'] = 'Gemini (Google)'
                st.session_state['planeacion_modelo_preferido'] = 'gemini-2.5-pro'
            else:
                st.session_state['epp_motor'] = 'ChatGPT (OpenAI)'
        with c_top2:
            if st.button('Volver al formato', key=key+'_cerrar_btn', width='stretch'):
                cerrar(); st.rerun(scope='app')

        campo = st.selectbox(
            'Apartado a redactar / enriquecer:',
            campos_lista,
            key=key + '_campo_sel'
        )

        base = st.session_state.get(prefix+'_value',{}).get('campos',{}).get(campo, doc['partes'].get(area,{}).get('contenido',{}).get('campos',{}).get(campo,''))
        k_campo = key + '_' + campo

        evals_area = doc.get('partes', {}).get(area, {}).get('contenido', {}).get('evaluaciones', [])
        insts_txt = str(doc.get('partes', {}).get(area, {}).get('contenido', {}).get('instrumentos', '') or '').strip()
        if evals_area or insts_txt:
            total_ev = len(evals_area)
            desc_ev = f"{total_ev} prueba(s) cargada(s) en la plataforma" if total_ev else ""
            desc_ins = insts_txt.replace('\n', ', ')[:120] if insts_txt else ""
            info_txt = " • ".join(filter(None, [desc_ins, desc_ev]))
            st.info(f"🔗 **Instrumentos vinculados ({area}):** {info_txt}\n\n*El asistente redactará tomando en cuenta estos hallazgos automáticamente.*")

        ideas = st.text_area('Tus ideas u observaciones complementarias (opcional si ya hay resultados de instrumentos)', key=k_campo+'_ideas', max_chars=3000)
        if st.button('Preparar texto para revisión', key=k_campo+'_preparar'):
            try:
                st.session_state[k_campo+'_resumen'] = servicio.preparar(doc, area, campo, ideas)
                st.session_state[k_campo+'_texto'] = st.session_state[k_campo+'_resumen']
                st.session_state.pop(k_campo+'_propuesta', None)
                st.session_state.pop(k_campo+'_consent', None)
            except (ValueError, PermissionError) as exc:
                st.warning(str(exc))

        if k_campo + '_resumen' not in st.session_state:
            return

        resumen = st.text_area('Resumen que se enviará: retira nombres, domicilios y contactos', value=st.session_state[k_campo+'_resumen'], key=k_campo+'_texto', max_chars=10000)
        check = st.checkbox('Revisé el resumen y autorizo enviarlo a IA', key=k_campo+'_consent')
        if st.button('Proponer redacción', disabled=not check, key=k_campo+'_generar'):
            try:
                with st.spinner('Redactando a partir de tus hallazgos…'):
                    st.session_state[k_campo+'_propuesta'] = servicio.generar(resumen, campo, area=area)
                    st.session_state[k_campo+'_resultado'] = st.session_state[k_campo+'_propuesta']
            except Exception:
                st.warning('No se completó la redacción. Tu texto se conserva y puedes continuar escribiendo.')

        if k_campo + '_propuesta' not in st.session_state:
            return

        st.text_area('Propuesta editable', value=st.session_state[k_campo+'_propuesta'], key=k_campo+'_resultado', max_chars=6000)

        def incorporar():
            try:
                aplicar(campo, st.session_state[k_campo+'_resultado'], base)
                st.session_state[k_campo+'_aplicada'] = True
            except (ValueError, RuntimeError, PermissionError) as exc:
                st.session_state[k_campo+'_error'] = str(exc)

        st.button('Usar esta redacción en el apartado', key=k_campo+'_usar', on_click=incorporar, type='primary')
        if st.session_state.pop(k_campo+'_aplicada', False):
            cerrar(); st.rerun(scope='app')
        if st.session_state.get(k_campo+'_error'):
            st.warning(st.session_state[k_campo+'_error'])

    dialogo_maestro()


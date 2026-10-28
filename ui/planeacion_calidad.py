"""Revisión opcional conectada a la misma hoja y su historial."""
import pandas as pd
import streamlit as st
from services import planeacion_calidad as calidad


@st.fragment(run_every=2)
def _revision_ia(prefix):
    from services.planeacion_edicion import huella
    from services import planeacion as s
    key=prefix+'_calidad_ia';job=st.session_state.get(key+'_trabajo')
    if job:
        if job['cuenta']!=s.identidad()['cuenta']:return
        if not job['future'].done():st.status('Contrastando las relaciones pedagógicas… Puedes seguir editando.',state='running');return
        st.session_state.pop(key+'_trabajo',None)
        try:st.session_state[key+'_resultado']={**job['peticion'],**job['future'].result()}
        except Exception:st.warning('No se completó la revisión. Tu planeación permanece intacta; puedes revisarla con los indicadores o reintentar.');return
    result=st.session_state.get(key+'_resultado')
    if not result:return
    doc=st.session_state[prefix+'_doc']
    if result['huella']!=huella(doc):st.caption('Esta revisión corresponde a una versión anterior. Vuelve a analizar para considerar tus cambios.');return
    st.caption('Sugerencias de IA para revisión profesional; no son una calificación ni cambian tu formato.')
    for r in result['observaciones']:st.info(f"Indicador {r['indicador']} · {r['apartado']}\n\n{r['hallazgo']}\n\nSugerencia: {r['sugerencia']}")


def panel(prefix):
    from ui import planeacion as u
    doc=st.session_state[prefix+'_doc']
    with st.expander('Revisión pedagógica · 14 indicadores de Zona 001',expanded=False):
        for alerta in calidad.alertas_coherencia(doc):st.info(alerta)
        st.caption('Las comprobaciones de datos no son calificaciones pedagógicas. Valora cada indicador de 0 a 3 cuando corresponda: no lo realiza, insuficiente, suficiente y satisfactorio. No es un requisito para guardar.')
        rows=calidad.revisar(doc);valoracion=doc['metadatos'].get('revision_pedagogica',{})
        for row in rows:row['Valoración docente']=valoracion.get('indicadores',{}).get(str(row['Número']))
        key=prefix+'_calidad_'+doc['id']
        edited=st.data_editor(pd.DataFrame(rows),hide_index=True,disabled=['Número','Indicador','Comprobación estructural','Sugerencia'],
            column_config={'Valoración docente':st.column_config.SelectboxColumn(options=[0,1,2,3])},key=key+'_tabla',width='stretch')
        coherencia=st.selectbox('Coherencia NEE–apoyos–PDA–actividades–evaluación',[None,0,1,2,3],format_func=lambda v:'Pendiente de valoración profesional' if v is None else str(v),index=[None,0,1,2,3].index(valoracion.get('coherencia')),key=key+'_coherencia')
        if st.button('Conservar mi revisión en esta planeación',key=key+'_guardar'):
            from copy import deepcopy
            from services.planeacion_edicion import huella
            nuevo=deepcopy(st.session_state[prefix+'_doc'])
            nuevo['metadatos']['revision_pedagogica']={'indicadores':{str(r['Número']):None if pd.isna(r['Valoración docente']) else int(r['Valoración docente']) for r in edited.to_dict('records')},'coherencia':coherencia,'version_revisada':huella(doc)}
            u._open(prefix,nuevo);u._persist(prefix,background=True)
            st.caption('Revisión incorporada al borrador; espera la confirmación del guardado.')
        if st.toggle('Contrastar coherencia con IA · opcional',key=key+'_activar_ia'):
            try:
                peticion=calidad.preparar_ia(doc)
                st.text_area('Datos pedagógicos que se enviarán, sin fichas personales',value=peticion['resumen'],height=120,disabled=True,key=key+'_resumen_'+peticion['huella'][:12])
                confirmo=st.checkbox('Revisé el resumen sin identificadores y autorizo este análisis',key=key+'_consentimiento')
                if st.button('Analizar coherencia',key=key+'_analizar',disabled=not confirmo or prefix+'_calidad_ia_trabajo' in st.session_state):
                    from ai.documento_json import enviar
                    from ai.epp_contextual import configuracion
                    from services import planeacion as s
                    st.session_state[prefix+'_calidad_ia_trabajo']={'future':enviar(calidad.analizar_ia,peticion,configuracion()),'peticion':peticion,'cuenta':s.identidad()['cuenta']}
                _revision_ia(prefix)
            except (ValueError,PermissionError,RuntimeError) as exc:st.caption(str(exc))

    from services.planeacion_intervenciones_nee import aplica,bloques,editar
    if aplica(doc):
        with st.expander('Conectar NEE, PDA y descriptor observable',expanded=False):
            lista=bloques(doc)
            if not lista:st.caption('Selecciona primero las NEE confirmadas en el formato. Cada una conserva sus propios apartados.');return
            byid={r['id']:r for r in lista};alumnos={r['ID_Alumno']:r['Nombre del alumno'] for r in doc['datos']['Alumnos']}
            bid=st.selectbox('NEE que vas a trabajar',list(byid),format_func=lambda i:alumnos[byid[i]['alumno']]+' · '+byid[i]['campos']['NEE'],key=prefix+'_pedagogia_nee')
            b=byid[bid];k=prefix+'_pedagogia_'+bid
            referentes={r['id']:r for r in doc['metadatos'].get('curriculo',{}).get('registros',[])}
            if referentes:
                rid=st.selectbox('PDA oficial vinculado',[None,*referentes],format_func=lambda r:'Selecciona un referente para revisar' if r is None else referentes[r]['pda'],key=k+'_pda')
                if rid and st.button('Confirmar este PDA para la NEE',key=k+'_confirmar_pda'):
                    nuevo=editar(st.session_state[prefix+'_doc'],bid,'Aprendizaje y/u objetivo',referentes[rid]['pda'])
                    nuevo['metadatos'].setdefault('pda_confirmados_nee',{})[bid]={'id':rid,'texto_oficial':referentes[rid]['pda'],'tipo':'Oficial','fuente':referentes[rid].get('fuente','')}
                    u._open(prefix,nuevo);u._persist(prefix,background=True);st.rerun()
            else:st.info('No hay PDA oficial verificable vinculado. Selecciónalo en Referentes o escribe y confirma tu propuesta contextualizada en el apartado correspondiente. No se inventará un PDA oficial.')
            verbo=st.selectbox('Acción observable',['identifica','reconoce','clasifica','forma','expresa','ordena','mantiene','sigue','compara','resuelve','solicita','participa'],key=k+'_verbo')
            complemento=st.text_input('Qué hará, con qué condiciones o apoyos',max_chars=500,key=k+'_complemento',placeholder='dos palabras entre tres tarjetas con apoyo visual')
            if complemento.strip():
                try:
                    propuesta=calidad.descriptor(alumnos[b['alumno']],verbo,complemento)
                    st.write(propuesta)
                    if st.button('Aceptar descriptor en esta NEE',key=k+'_descriptor'):
                        actual=st.session_state[prefix+'_doc']
                        if next(r for r in bloques(actual) if r['id']==bid)['campos']!=b['campos']:raise ValueError('El apartado cambió. Revisa de nuevo antes de aplicar.')
                        nuevo=editar(actual,bid,'Descriptor de logro',propuesta)
                        u._open(prefix,nuevo);u._persist(prefix,background=True);st.rerun()
                except ValueError as exc:st.warning(str(exc))

    from services.planeacion_periodo import es_anual,agregar_seguimiento
    if es_anual(doc):
        with st.expander('Periodos internos de seguimiento de la hoja anual',expanded=False):
            for r in doc['metadatos'].get('periodos_seguimiento',[]):st.write(r['inicio']+' → '+r['fin']+' · '+r['proposito'])
            a,b=st.columns(2)
            inicio=a.date_input('Inicio del seguimiento',value=None,key=prefix+'_seguimiento_inicio')
            fin=b.date_input('Fin del seguimiento',value=None,key=prefix+'_seguimiento_fin')
            proposito=st.text_input('Propósito del seguimiento',max_chars=600,key=prefix+'_seguimiento_proposito')
            if st.button('Añadir periodo a esta misma hoja',disabled=not inicio or not fin or not proposito.strip(),key=prefix+'_seguimiento_agregar'):
                try:
                    nuevo=agregar_seguimiento(st.session_state[prefix+'_doc'],inicio,fin,proposito)
                    u._open(prefix,nuevo);u._persist(prefix,background=True);st.rerun()
                except ValueError as exc:st.warning(str(exc))

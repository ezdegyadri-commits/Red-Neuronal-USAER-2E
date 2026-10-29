"""Preparación local opcional, con vista previa y aplicación explícita."""
import streamlit as st
from services import planeacion_local as local,planeacion_edicion as ed


def panel(prefix):
    doc=st.session_state[prefix+'_doc']
    incorporadas=st.session_state.pop(prefix+'_actividades_locales_integradas',None)
    if incorporadas:
        st.success(f'{incorporadas} actividad(es) local(es) se incorporaron al borrador. Las encontrarás en «Organización de las actividades de aprendizaje» → columna «Actividades».')
    st.markdown('#### Si prefieres continuar sin IA')
    st.caption('Prepara una propuesta local, revísala y pulsa «Incorporar actividades locales a mi formato». Luego cierra este panel para editar las actividades directamente en la hoja.')
    contexto=None
    if doc['formato']!='XXI':
        from services.planeacion_modelo import FORMATOS
        contextos=FORMATOS[doc['formato']]['contextos']
        contexto=st.selectbox('Contexto de las actividades sin IA',contextos,key=prefix+'_local_contexto')
    if st.button('Preparar actividades con mis datos · sin IA',key=prefix+'_local_preparar',width='stretch'):
        try:
            enfoque=doc['metadatos'].get('configuracion_generacion',{}).get('enfoque','')
            st.session_state[prefix+'_local_propuesta']=local.preparar(doc,enfoque,contexto_actividad=contexto)
        except (ValueError,PermissionError,RuntimeError) as exc:st.info(str(exc))
    propuesta=st.session_state.get(prefix+'_local_propuesta')
    if not propuesta:return
    if propuesta['huella']!=ed.huella(doc):
        st.caption('La planeación cambió. Vuelve a preparar las actividades locales para conservar tus cambios.');return
    with st.expander('Revisar propuestas con los datos cargados · sin IA',expanded=True):
        st.caption('Preparación por reglas y secuencias educativas locales, no por Gemini. Usa antecedentes propios y referentes seleccionados; cuando faltan antecedentes individuales lo indica. No diagnostica ni rellena NEE, resultados, firmas o acuerdos realizados.')
        rows={r['id']:r for r in propuesta['propuestas']}
        aplicadas=set(doc['metadatos'].get('actividades_locales_aplicadas',[]))
        disponibles=[i for i in rows if i not in aplicadas]
        if not disponibles:st.info('Estas propuestas ya fueron incorporadas o retiradas. Se conservan tus ediciones; no se duplicarán.');return
        ids=st.multiselect('Propuestas locales por incorporar',disponibles,default=disponibles,
            format_func=lambda i:rows[i]['nombre']+' · '+rows[i]['campo'],key=prefix+'_local_elegidas_'+propuesta['huella'][:12])
        for i in ids:
            with st.expander('Propuesta · '+rows[i]['nombre']+' · '+rows[i]['campo']):
                if rows[i].get('contexto'):st.caption('Contexto: '+rows[i]['contexto'])
                st.write(rows[i]['actividad']);st.caption('Recursos propuestos: '+rows[i]['recursos'])
                if rows[i].get('orientacion'):st.caption(rows[i]['orientacion'])
        confirmar=st.checkbox('Revisé estas propuestas y su pertinencia; las completaré y ajustaré en el formato',key=prefix+'_local_confirmar_'+propuesta['huella'][:12])
        if st.button('Incorporar actividades locales a mi formato',disabled=not ids or not confirmar,key=prefix+'_local_aplicar'):
            try:
                from ui import planeacion as u
                from ui.planeacion_simple import PASOS
                actual=st.session_state[prefix+'_doc']
                nuevo=local.aplicar(actual,propuesta,ids)
                st.session_state[prefix+'_actividades_locales_integradas']=len(ids)
                u._open(prefix,nuevo);u._persist(prefix)
                st.session_state[prefix.rsplit('_',1)[0]+'_paso_pendiente']=PASOS[2]
                st.session_state.pop(prefix+'_local_propuesta',None);st.rerun()
            except (ValueError,PermissionError,RuntimeError) as exc:st.warning(str(exc))


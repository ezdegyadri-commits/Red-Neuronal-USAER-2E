"""La misma hoja XIX, con escritura exclusiva de la columna del especialista."""
from copy import deepcopy
import streamlit as st
from services import planeacion as s,planeacion_papel as papel
from services.planeacion_colaboracion import aportar


def panel(prefix,doc):
    from ui.planeacion_papel import editor
    from ui.planeacion_colaboracion import _guardar,_estado,_cambio
    actor=s.identidad();base=prefix+'_'+doc['id']+'_'+actor['area']
    if base+'_doc' not in st.session_state:
        previo=doc['metadatos'].get('aportaciones_equipo',{}).get(actor['area'],{})
        st.session_state[base+'_doc']=deepcopy(doc)
        st.session_state[base+'_filas']=deepcopy(previo.get('filas',[]))
        st.session_state[base+'_obs']=previo.get('observaciones','')
    actual=st.session_state[base+'_doc']
    preview=aportar(actual,actor,st.session_state[base+'_filas'],st.session_state[base+'_obs'])
    # La revisión temporal del preview no participa en su huella: debe ser estable.
    previo=actual['metadatos'].get('aportaciones_equipo',{}).get(actor['area'],{})
    preview['metadatos']['aportaciones_equipo'][actor['area']]['revision']=previo.get('revision','local')
    preview['metadatos']['aportaciones_equipo'][actor['area']]['fecha']=previo.get('fecha','')
    st.caption('Escribe directamente en la columna '+actor['area']+'. Las demás áreas se ven aquí mismo y están protegidas. La maestra de apoyo conserva la coordinación del formato.')
    event=editor(hoja=papel.hoja(preview,colaborativa=True),
        guardado=actual.get('guardado_en','') if not st.session_state.get(base+'_pending') else '',
        aceptado=st.session_state.pop(base+'_legacy_ack',False),
        aceptado_nonce=st.session_state.get(base+'_ack',''),
        rechazado=st.session_state.get(base+'_rechazado',''),
        error=st.session_state.get(base+'_error_hoja',''),key=base+'_hoja',default=None)
    if event and event.get('nonce')!=st.session_state.get(base+'_nonce'):
        try:
            filas=papel.aplicar_aporte(preview,event)
            st.session_state[base+'_nonce']=event['nonce']
            if filas!=st.session_state[base+'_filas'] or event.get('accion')=='guardar':
                st.session_state[base+'_filas']=filas;st.session_state[base+'_pending']=True
                _guardar(base,automatic=event.get('accion')=='autoguardar')
            # Recibir el evento no equivale a guardarlo: el cliente conserva
            # su respaldo mientras el guardado esté pendiente o en reintento.
            if not st.session_state.get(base+'_pending'):
                st.session_state[base+'_ack']=event['nonce']
                st.session_state[base+'_legacy_ack']=True
            st.session_state.pop(base+'_rechazado',None)
            st.session_state.pop(base+'_error_hoja',None)
            if event.get('accion')=='inicio':
                if st.session_state.get(base+'_pending'):_guardar(base)
                if not st.session_state.get(base+'_pending'):st.session_state[prefix+'_cerrado']=doc['id']
            st.rerun()
        except (ValueError,PermissionError,RuntimeError) as exc:
            st.session_state[base+'_nonce']=event.get('nonce')
            st.session_state[base+'_rechazado']=event.get('nonce')
            st.session_state[base+'_error_hoja']=str(exc)
            st.rerun()
    st.text_area('Observaciones de mi área',value=st.session_state[base+'_obs'],key=base+'_notas',on_change=_cambio,args=(base,base+'_notas'))
    if st.button('Guardar mi aportación',key=base+'_save'):_guardar(base)
    _estado(base)
    import json
    st.download_button('Respaldo de mi aportación',json.dumps({'documento':doc['id'],'area':actor['area'],
        'filas':st.session_state[base+'_filas'],'observaciones':st.session_state[base+'_obs']},ensure_ascii=False),
        file_name='aporte-'+doc['id']+'.json',mime='application/json',key=base+'_backup')
    if st.button('Actualizar aportaciones del equipo',key=base+'_refresh'):
        if st.session_state.get(base+'_pending'):_guardar(base)
        if not st.session_state.get(base+'_pending'):
            s.refrescar()
            reciente=next((d for d in s.compartidos() if d['id']==doc['id']),None)
            if reciente:st.session_state[base+'_doc']=reciente;st.rerun()
    with st.expander('Reutilizar actividades de mi formato de especialista'):
        candidatos=[d for d in s.listar() if d['datos']['ID_Escuela']==doc['datos']['ID_Escuela'] and d['datos']['Función']==actor['area']]
        if candidatos:
            from services.planeacion_compartida import etiqueta
            porid={d['id']:d for d in candidatos}
            did=st.selectbox('Planeación de mi área con actividades revisadas',list(porid),format_func=lambda i:etiqueta(porid[i]),key=base+'_origen')
            st.caption('Reutiliza solo actividades vinculadas a los mismos alumnos. Puedes editarlas o borrarlas después; no se modificará el documento de origen.')
            if st.button('Proponer mi aporte con esas actividades',key=base+'_usar'):
                from services.planeacion_colaboracion import COLUMNAS
                origen=porid[did];propios={a['ID_Alumno'] for a in origen['datos']['Alumnos']};rows=deepcopy(st.session_state[base+'_filas'])
                for a in doc['datos']['Alumnos']:
                    if a['ID_Alumno'] not in propios:continue
                    textos=[r.get('Actividades','') for r in origen['tablas'].get('dosificacion',[]) if r.get('Actividades') and
                        (a['ID_Alumno'] in (r.get('_alumnos_locales') or r.get('_alumnos_planeacion') or []) or propios=={a['ID_Alumno']})]
                    if not textos:continue
                    row=next((r for r in rows if r['ID_Alumno']==a['ID_Alumno']),None)
                    if row is None:row={k:'' for k in COLUMNAS};row['ID_Alumno']=a['ID_Alumno'];rows.append(row)
                    if not row.get('Texto en formato') and not row.get('Actividad / cómo trabajar'):row['Texto en formato']='\n\n'.join(textos)[:4000]
                st.session_state[base+'_filas']=rows;_guardar(base);st.rerun()
        else:st.caption('Tu formato de especialista conserva las conexiones al expediente, PDA, DUA y propuestas de IA en «Mi formato».')

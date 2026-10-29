"""La misma hoja XIX, con escritura exclusiva de la columna del especialista."""
from copy import deepcopy
import streamlit as st
from services import planeacion as s,planeacion_papel as papel
from services.planeacion_colaboracion import aportar


def _preview(base,actor):
    actual=st.session_state[base+'_doc']
    preview=aportar(actual,actor,st.session_state[base+'_filas'],st.session_state[base+'_obs'])
    previo=actual['metadatos'].get('aportaciones_equipo',{}).get(actor['area'],{})
    preview['metadatos']['aportaciones_equipo'][actor['area']]['revision']=previo.get('revision','local')
    preview['metadatos']['aportaciones_equipo'][actor['area']]['fecha']=previo.get('fecha','')
    return preview


def recibir_edicion(base,event):
    """Valida y guarda el parche antes del único render del fragmento."""
    from ui.planeacion_colaboracion import _guardar
    if event.get('nonce')==st.session_state.get(base+'_nonce'):
        if event.get('accion')=='guardar' and st.session_state.get(base+'_pending'):_guardar(base,background=True)
        return
    try:
        filas,obs=papel.aplicar_aporte(_preview(base,s.identidad()),event,con_observaciones=True)
        st.session_state[base+'_nonce']=event['nonce']
        if filas!=st.session_state[base+'_filas'] or obs!=st.session_state[base+'_obs'] or event['accion']=='guardar':
            st.session_state[base+'_filas']=filas;st.session_state[base+'_obs']=obs
            _guardar(base,automatic=event['accion']=='autoguardar',background=True)
        if not st.session_state.get(base+'_pending'):st.session_state[base+'_ack']=event['nonce']
        st.session_state.pop(base+'_rechazado',None)
        st.session_state.pop(base+'_error_hoja',None)
    except (ValueError,PermissionError,RuntimeError) as exc:
        st.session_state[base+'_nonce']=event.get('nonce')
        st.session_state[base+'_rechazado']=event.get('nonce')
        st.session_state[base+'_error_hoja']=str(exc)


@st.fragment(run_every=10)
def panel(prefix,doc):
    from ui.planeacion_papel import editor,refrescar_editor,lectura_equipo
    from ui.planeacion_colaboracion import _guardar
    actor=s.identidad();base=prefix+'_'+doc['id']+'_'+actor['area']
    existente=st.session_state.get(base+'_doc')
    if existente and doc.get('guardado_en','')<existente.get('guardado_en',''):
        doc=existente  # El listado puede seguir en caché después de un guardado.
    if base+'_doc' not in st.session_state or (not st.session_state.get(base+'_pending') and doc.get('revision')!=st.session_state.get(base+'_doc',{}).get('revision')):
        previo=doc['metadatos'].get('aportaciones_equipo',{}).get(actor['area'],{})
        st.session_state[base+'_doc']=deepcopy(doc)
        st.session_state[base+'_filas']=deepcopy(previo.get('filas',[]))
        st.session_state[base+'_obs']=previo.get('observaciones','')
    actual=st.session_state[base+'_doc']
    st.session_state[base+'_intervalo']=15
    try:
        reciente=lectura_equipo(base,doc['id'],background=True)
        if reciente:
            from services.planeacion_compartida import actualizar_lectura
            actual=actualizar_lectura(actual,reciente,actor['area'])
            st.session_state[base+'_doc']=actual
    except Exception:
        st.caption('No se pudo actualizar el equipo en este momento. Tu hoja permanece abierta; se reintentará.')
    propio=actual['metadatos'].get('aportaciones_equipo',{}).get(actor['area'],{})
    if actor['area'] in actual['metadatos'].get('unificacion_grupal',{}).get('conflictos_area',[]) or propio and propio.get('cuenta')!=actor['cuenta']:
        st.warning('Los aportes de esta columna se conservaron, pero su autoría requiere revisión de Dirección. La hoja queda disponible para lectura; no se reemplazará trabajo de otra cuenta.')
        editor(hoja=papel.hoja(actual,colaborativa=True),key=base+'_hoja',default=None)
        import json
        st.download_button('Respaldar mi texto pendiente',json.dumps({'filas':st.session_state[base+'_filas'],'observaciones':st.session_state[base+'_obs']},ensure_ascii=False),file_name='aporte-pendiente.json',key=base+'_respaldo_conflicto')
        if st.button('Regresar a los grupos',key=base+'_volver_conflicto'):
            st.session_state.pop(prefix+'_abierto',None);st.rerun(scope='app')
        return
    activos={str(a['ID_Alumno']) for a in actual['datos']['Alumnos']}
    retirados=[r for r in st.session_state[base+'_filas'] if str(r.get('ID_Alumno')) not in activos]
    if retirados:
        respaldo=st.session_state.setdefault(base+'_filas_retiradas',[])
        for r in retirados:
            if r not in respaldo:respaldo.append(deepcopy(r))
        st.session_state[base+'_filas']=[r for r in st.session_state[base+'_filas'] if str(r.get('ID_Alumno')) in activos]
        st.caption('Las aportaciones de alumnos con baja o traslado se conservan en el historial y en tu respaldo; ya no se editan en la matrícula activa.')
    if st.session_state.get(base+'_pending'):_guardar(base,automatic=True,background=True)
    actual=st.session_state[base+'_doc']
    preview=_preview(base,actor)
    st.caption('Escribe en '+actor['area']+'. Tu hoja permanece abierta mientras se guardan los cambios y se reciben los aportes del equipo. Usa «Guardar planeación» para confirmar ahora.')
    event=editor(hoja=papel.hoja(preview,colaborativa=True),
        guardado=actual.get('guardado_en','') if not st.session_state.get(base+'_pending') else '',
        aceptado=st.session_state.pop(base+'_legacy_ack',False),
        aceptado_nonce=st.session_state.get(base+'_ack',''),
        rechazado=st.session_state.get(base+'_rechazado',''),
        error=st.session_state.get(base+'_error_hoja',''),key=base+'_hoja',default=None,
        error_guardado_nonce=st.session_state.get(base+'_io_error_nonce',''),
        error_guardado=st.session_state.get(base+'_error',''),
        on_edicion=lambda event:recibir_edicion(base,event))
    if event and event.get('nonce')!=st.session_state.get(base+'_nonce'):
        try:
            filas,obs=papel.aplicar_aporte(preview,event,con_observaciones=True)
            st.session_state[base+'_nonce']=event['nonce']
            if filas!=st.session_state[base+'_filas'] or obs!=st.session_state[base+'_obs'] or event.get('accion')=='guardar' or event.get('accion')=='inicio' and st.session_state.get(base+'_pending'):
                st.session_state[base+'_filas']=filas;st.session_state[base+'_obs']=obs;st.session_state[base+'_pending']=True
                _guardar(base,automatic=event.get('accion')=='autoguardar',background=True)
            # Recibir el evento no equivale a guardarlo: el cliente conserva
            # su respaldo mientras el guardado esté pendiente o en reintento.
            if not st.session_state.get(base+'_pending'):
                st.session_state[base+'_ack']=event['nonce']
                st.session_state[base+'_legacy_ack']=True
            st.session_state.pop(base+'_rechazado',None)
            st.session_state.pop(base+'_error_hoja',None)
            if event.get('accion')=='inicio':
                from services.navegacion_planeaciones import habilitada
                if not st.session_state.get(base+'_pending') or habilitada():
                    # El parche ya está en la cola por ID; navegar no lo descarta.
                    st.session_state.pop(prefix+'_abierto',None)
                    st.rerun(scope='app')
            refrescar_editor()
        except (ValueError,PermissionError,RuntimeError) as exc:
            st.session_state[base+'_nonce']=event.get('nonce')
            st.session_state[base+'_rechazado']=event.get('nonce')
            st.session_state[base+'_error_hoja']=str(exc)
            refrescar_editor()
    if st.session_state.get(base+'_error'):st.warning(st.session_state[base+'_error'])
    elif st.session_state.get(base+'_pending'):st.caption('Guardado pendiente de confirmación. Puedes seguir escribiendo; conserva esta pestaña abierta.')
    else:st.caption('Guardado confirmado · '+actual.get('guardado_en','sin cambios')[:19])
    import json
    st.download_button('Respaldo de mi aportación',json.dumps({'documento':doc['id'],'area':actor['area'],
        'filas':st.session_state[base+'_filas'],'filas_retiradas':st.session_state.get(base+'_filas_retiradas',[]),'observaciones':st.session_state[base+'_obs']},ensure_ascii=False),
        file_name='aporte-'+doc['id']+'.json',mime='application/json',key=base+'_backup')
    c_b1, c_b2 = st.columns(2)
    with c_b1:
        if st.button('Actualizar aportaciones del equipo',key=base+'_refresh'):
            if st.session_state.get(base+'_pending'):_guardar(base)
            if not st.session_state.get(base+'_pending'):
                s.refrescar()
                reciente=next((d for d in s.compartidos() if d['id']==doc['id']),None)
                if reciente:st.session_state[base+'_doc']=reciente;refrescar_editor()
    with c_b2:
        if st.button('Volver a los grupos compartidos',key=base+'_volver_lista'):
            st.session_state.pop(prefix+'_abierto',None);st.rerun(scope='app')
    with st.expander('Reutilizar actividades de mi formato de especialista'):
        if st.button('Consultar actividades de mi área',key=base+'_consultar_origen'):
            st.session_state[base+'_candidatos']=[d for d in s.listar() if d['datos']['ID_Escuela']==doc['datos']['ID_Escuela'] and d['datos']['Función']==actor['area']]
        candidatos=st.session_state.get(base+'_candidatos',[])
        if candidatos:
            from services.planeacion_compartida import etiqueta
            porid={d['id']:d for d in candidatos}
            did=st.selectbox('Planeación de mi área con actividades revisadas',list(porid),format_func=lambda i:etiqueta(porid[i]),key=base+'_origen')
            st.caption('Reutiliza solo actividades vinculadas a los mismos alumnos. Puedes editarlas o borrarlas después; no se modificará el documento de origen.')
            if st.button('Proponer mi aporte con esas actividades',key=base+'_usar'):
                from services.planeacion_colaboracion import COLUMNAS
                origen=porid[did];s.autorizar(origen)
                propios={a['ID_Alumno'] for a in origen['datos']['Alumnos']};rows=deepcopy(st.session_state[base+'_filas'])
                for a in doc['datos']['Alumnos']:
                    if a['ID_Alumno'] not in propios:continue
                    textos=[r.get('Actividades','') for r in origen['tablas'].get('dosificacion',[]) if r.get('Actividades') and
                        (a['ID_Alumno'] in (r.get('_alumnos_locales') or r.get('_alumnos_planeacion') or []) or propios=={a['ID_Alumno']})]
                    if not textos:continue
                    row=next((r for r in rows if r['ID_Alumno']==a['ID_Alumno']),None)
                    if row is None:row={k:'' for k in COLUMNAS};row['ID_Alumno']=a['ID_Alumno'];rows.append(row)
                    if not row.get('Texto en formato') and not row.get('Actividad / cómo trabajar'):row['Texto en formato']='\n\n'.join(textos)[:4000]
                st.session_state[base+'_filas']=rows;_guardar(base);refrescar_editor()
        else:st.caption('Tu formato de especialista conserva las conexiones al expediente, PDA, DUA y propuestas de IA en «Mi formato».')

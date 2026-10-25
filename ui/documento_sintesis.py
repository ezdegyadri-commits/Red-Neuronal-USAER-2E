"""Previsualización textual breve; nunca muestra el escaneo ni su transcripción íntegra."""
import streamlit as st
from uuid import uuid4
from services.documento_sintesis import sintetizar


def _registros_guardados(saved,did,sha):
    from copy import deepcopy
    from services.nee_documentales import identificar
    if not saved:return []
    if 'nee_registros' in saved:return deepcopy(saved['nee_registros'])
    # Las necesidades legadas ya fueron revisadas; no se vuelven a capturar ni
    # se inventan páginas que no se registraron en la versión anterior.
    return [{'id':identificar(did,sha,'legado:'+str(i)),'texto':texto,'fundamento':texto,
        'pagina':'','area':'','estado':'Validada','origen':'Validación histórica'}
        for i,texto in enumerate(saved.get('necesidades',[]))]


def vista(texto, key, seleccionar=False):
    propuesta = sintetizar(texto)
    st.caption(propuesta['aviso'])
    resumen = st.text_area('Síntesis del documento · revisa y corrige', value=propuesta['resumen'],
                           max_chars=1200, height=100, key=key+'_sintesis')
    needs = []
    if seleccionar:
        needs = st.multiselect('NEE expresadas en la EPP · selecciona solo las que corresponden al alumno',
                               propuesta['necesidades'], key=key+'_nee')
        if not propuesta['necesidades']:
            st.info('No se identificaron enunciados explícitos de NEE. No se deducirán de una condición o diagnóstico. Revisa la EPP y captura sus necesidades en la conclusión educativa.')
    st.caption('El original se conserva; esta vista breve no sustituye su revisión. La extracción puede omitir tablas, manuscritos o páginas no legibles.')
    return {'resumen': resumen, 'necesidades': needs}


def archivado(did, row, data, key):
    """OCR solo a petición; el índice revisado se guarda aparte del original."""
    from services import documentos_sintesis as servicio
    from services.materiales_planeacion import leer_material
    k=key+'_'+did
    educativo=row.get('Tipo') in servicio.EDUCATIVOS
    try:
        saved=servicio.listar().get(did)
    except Exception:
        saved=None
        st.warning('No se pudo consultar la síntesis guardada. El original y las revisiones anteriores se conservan; reintenta la consulta.')
    if saved:
        st.caption('Síntesis conservada en el expediente · '+str(saved.get('Fecha',''))[:16])
        st.write(saved['resumen'])
        for necesidad in saved['necesidades']:st.write('• '+necesidad)
        st.caption('Disponible como antecedente revisado: actualiza los antecedentes en Planeación o EPP. No sustituye la valoración profesional.' if educativo else
            'Conservada para consulta del expediente; los documentos de identidad o administrativos no se usan como resultados educativos.')
        if st.button('Revisar o corregir síntesis y NEE guardadas',key=k+'_recuperar'):
            st.session_state[k+'_lectura']={'texto':'','avisos':[]}
            st.session_state[k+'_sintesis']=saved['resumen']
            st.session_state[k+'_registros']=_registros_guardados(saved,did,row.get('SHA256',''))
            st.session_state[k+'_base']=saved.get('Revision','')
            st.session_state[k+'_edicion']=uuid4().hex
            st.session_state.pop(k+'_editor',None)
            st.session_state[k+'_revisada']=False
    if st.button('Preparar vista previa sintetizada', key=k+'_leer'):
        try:
            with st.spinner('Preparando síntesis local del documento…'):
                read=leer_material(row['Nombre'],data() if callable(data) else data)
            st.session_state[k+'_lectura']=read
            from services.nee_documentales import detectar
            anteriores=_registros_guardados(saved,did,row.get('SHA256',read.get('id','')))
            propuestas=detectar(read['texto'],did,row.get('SHA256',read.get('id','')))
            from services.nee_documentales import clave
            st.session_state[k+'_registros']=anteriores+[r for r in propuestas if clave(r['texto']) not in {clave(a['texto']) for a in anteriores}]
            st.session_state[k+'_base']=saved.get('Revision','') if saved else ''
            st.session_state[k+'_edicion']=uuid4().hex
            st.session_state.pop(k+'_editor',None)
            st.session_state.pop(k+'_sintesis',None)
            st.session_state[k+'_revisada']=False
        except Exception:
            st.warning('No se pudo preparar la síntesis. El original sigue disponible; intenta una copia más clara o selecciona un intervalo menor en Materiales.')
    read=st.session_state.get(k+'_lectura')
    if not read:return
    for aviso in read.get('avisos',[]):st.caption(aviso)
    import json
    unica=row.get('Tipo')=='EPP' and row.get('Ambito')=='individual' and len(json.loads(row.get('ID_Alumnos_JSON','[]')))==1
    value=vista(read['texto'],k)
    if unica:
        import pandas as pd
        from services.nee_documentales import ESTADOS
        st.caption('Revisa cada propuesta: corrige su redacción y fundamento, añade omitidas o marca Descartada. Solo Validada alimenta el selector del alumno; no se infieren necesidades de un diagnóstico.')
        cols=['id','texto','fundamento','pagina','area','estado','origen']
        rows=st.session_state.get(k+'_registros',[])
        if not rows:st.info('No se detectaron NEE suficientemente explícitas en la lectura disponible. Puedes añadirlas con su fundamento tras revisar el original, o continuar la planeación manualmente. No se completarán con suposiciones.')
        frame=pd.DataFrame([{c:r.get(c,'') for c in cols} for r in rows],columns=cols)
        edit=st.data_editor(frame,hide_index=True,num_rows='dynamic',width='stretch',key=k+'_editor_'+str(st.session_state.get(k+'_edicion',0)),
            disabled=['id','origen'],column_config={'id':None,
                'texto':st.column_config.TextColumn('NEE propuesta',max_chars=600,width='large'),
                'fundamento':st.column_config.TextColumn('Fundamento en la EPP',max_chars=1000,width='large'),
                'pagina':st.column_config.TextColumn('Página / sección',max_chars=40),
                'area':st.column_config.TextColumn('Área pedagógica',max_chars=100),
                'estado':st.column_config.SelectboxColumn('Estado',options=list(ESTADOS),default='Detectada',required=True),
                'origen':st.column_config.TextColumn('Origen')})
        value['nee_registros']=edit.fillna('').to_dict('records')
        st.download_button('Respaldar mi revisión de NEE',json.dumps(value,ensure_ascii=False,indent=2),file_name='revision-nee.json',mime='application/json',key=k+'_respaldo')
    review=st.checkbox('Revisé la síntesis y las NEE seleccionadas contra el original y corresponden a este alumno o contexto',key=k+'_revisada')
    if st.button('Guardar síntesis y vincular las NEE seleccionadas' if unica else 'Guardar síntesis revisada',
                 disabled=not review or not value['resumen'].strip(),key=k+'_guardar'):
        try:
            rev=servicio.guardar(did,value,revision_esperada=st.session_state.get(k+'_base',''))
            st.session_state[k+'_base']=rev
            try:
                confirmado=servicio.listar().get(did)
                if confirmado and confirmado.get('Revision')==rev:
                    st.session_state[k+'_registros']=_registros_guardados(confirmado,did,row.get('SHA256',''))
                    st.session_state[k+'_edicion']=str(rev)
            except Exception:
                st.caption('Guardado confirmado; la vista del catálogo se podrá recuperar al consultar de nuevo el documento.')
            st.success('Síntesis guardada y vinculada por alumno. Actualiza los antecedentes en Planeación o EPP para recuperarla; el original no cambió.' if educativo else
                'Síntesis guardada para consulta del expediente, sin modificar el original ni incorporarla como resultado educativo.')
        except Exception as exc:
            st.warning(str(exc) if isinstance(exc,(ValueError,PermissionError,RuntimeError)) else 'No se confirmó la síntesis. El original permanece archivado; vuelve a intentar sin cargarlo otra vez.')

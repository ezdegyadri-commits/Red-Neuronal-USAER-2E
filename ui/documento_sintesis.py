"""Previsualización textual breve; nunca muestra el escaneo ni su transcripción íntegra."""
import streamlit as st
from services.documento_sintesis import sintetizar


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
    if st.button('Preparar vista previa sintetizada', key=k+'_leer'):
        try:
            with st.spinner('Preparando síntesis local del documento…'):
                read=leer_material(row['Nombre'],data() if callable(data) else data)
            st.session_state[k+'_lectura']=read
        except Exception:
            st.warning('No se pudo preparar la síntesis. El original sigue disponible; intenta una copia más clara o selecciona un intervalo menor en Materiales.')
    read=st.session_state.get(k+'_lectura')
    if not read:return
    for aviso in read.get('avisos',[]):st.caption(aviso)
    import json
    unica=row.get('Tipo')=='EPP' and row.get('Ambito')=='individual' and len(json.loads(row.get('ID_Alumnos_JSON','[]')))==1
    value=vista(read['texto'],k,seleccionar=unica)
    review=st.checkbox('Revisé la síntesis y las NEE seleccionadas contra el original y corresponden a este alumno o contexto',key=k+'_revisada')
    if st.button('Guardar síntesis y vincular las NEE seleccionadas' if unica else 'Guardar síntesis revisada',
                 disabled=not review or not value['resumen'].strip(),key=k+'_guardar'):
        try:
            servicio.guardar(did,value)
            st.success('Síntesis guardada. Las NEE seleccionadas estarán disponibles al actualizar los antecedentes de la planeación del alumno.' if unica else 'Síntesis guardada sin cambiar el documento original.')
        except Exception as exc:
            st.warning(str(exc) if isinstance(exc,(ValueError,PermissionError,RuntimeError)) else 'No se confirmó la síntesis. El original permanece archivado; vuelve a intentar sin cargarlo otra vez.')

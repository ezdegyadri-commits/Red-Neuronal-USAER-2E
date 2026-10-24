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
            st.success('Síntesis guardada y vinculada por alumno. Actualiza los antecedentes en Planeación o EPP para recuperarla; el original no cambió.' if educativo else
                'Síntesis guardada para consulta del expediente, sin modificar el original ni incorporarla como resultado educativo.')
        except Exception as exc:
            st.warning(str(exc) if isinstance(exc,(ValueError,PermissionError,RuntimeError)) else 'No se confirmó la síntesis. El original permanece archivado; vuelve a intentar sin cargarlo otra vez.')

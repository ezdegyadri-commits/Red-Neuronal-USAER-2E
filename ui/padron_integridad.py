"""Herramienta opcional de Dirección: consulta y exportación privada del diagnóstico."""
import json
import streamlit as st


def panel():
    from services.asignaciones import es_direccion
    if not es_direccion(st.session_state.get('rol','')):return
    with st.expander('Dirección · revisar integridad del padrón',expanded=False):
        st.caption('Consulta de sólo lectura. No da de baja alumnos, no modifica escuelas y no fusiona documentos.')
        if st.button('Preparar diagnóstico de integridad',key='padron_integridad_revisar'):
            from data import repository as repo
            from services import padron_integridad as motor,planeacion
            try:
                with st.status('Revisando referencias y nomenclaturas…',expanded=False):
                    alumnos=repo.alumnos().fillna('').to_dict('records');escuelas=repo.escuelas().fillna('').to_dict('records')
                    catalogo_vacio=not escuelas
                    if catalogo_vacio:
                        from config.settings import ESCUELAS_USAER
                        escuelas=[{'ID_Escuela':eid,'Nombre_Escuela':n,'Fuente':'Configuración institucional; CCT por verificar'} for n,eid in ESCUELAS_USAER.items()]
                    reporte=motor.diagnosticar(alumnos,escuelas,planeacion.versiones_actuales())
                    if catalogo_vacio:reporte['avisos'].append({'tipo':'Catálogo Escuelas vacío','registro':'Escuelas','detalle':'Se cotejaron IDs contra la configuración institucional. Confirmar CCT antes de cualquier migración.'})
                    st.session_state['padron_integridad_diagnostico']={'cuenta':st.session_state.get('usuario'),'reporte':reporte}
            except Exception:st.warning('No se completó la lectura. Se conserva la última revisión; el padrón no cambió.')
        guardado=st.session_state.get('padron_integridad_diagnostico')
        if not guardado or guardado['cuenta']!=st.session_state.get('usuario'):return
        r=guardado['reporte'];st.write(r['conteos'])
        st.caption(str(len(r['avisos']))+' observaciones · '+str(len(r['cambios_propuestos']))+' normalizaciones propuestas para revisión')
        if r['avisos']:st.dataframe(r['avisos'],hide_index=True,width='stretch')
        st.download_button('Descargar diagnóstico y equivalencias',json.dumps(r,ensure_ascii=False,indent=2),file_name='diagnostico-integridad.json',mime='application/json',key='padron_integridad_descargar')

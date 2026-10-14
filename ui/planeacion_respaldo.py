"""Opciones aditivas para seguir planeando sin esperar una generación de IA."""
import streamlit as st


def _ir(prefix, base, destino, sin_ia):
    # El selector de pasos ya se dibujó: se usa su transición pendiente canónica
    # en vez de modificar directamente el estado de un widget instanciado.
    st.session_state[base+'_paso_pendiente'] = destino
    if sin_ia:
        st.session_state[prefix+'_continuidad_doc'] = st.session_state[prefix+'_doc']['id']
    else:
        st.session_state.pop(prefix+'_continuidad_doc', None)


def acceso(prefix, base, destino):
    st.caption('La IA es opcional. Puedes completar, guardar y descargar el mismo formato aunque no responda.')
    st.button('Continuar sin IA · abrir mi formato', key=prefix+'_continuar_sin_ia',
              on_click=_ir, args=(prefix, base, destino, True), use_container_width=True)


def _autollenar(prefix):
    from services.planeacion_respaldo import autollenar
    from ui import planeacion as u
    try:
        actual = st.session_state[prefix+'_doc']
        preparado = autollenar(actual)
        # Abrir un formato o repetir el botón no debe producir nuevas versiones.
        if preparado != actual:
            u._open(prefix, preparado)
            confirmado = u._persist(prefix)
        else:
            confirmado = not st.session_state.get(prefix+'_pending', False)
        st.session_state[prefix+'_autollenado_local'] = (
            'Información disponible incorporada. Revisa los antecedentes y completa las actividades.'
            if confirmado else
            'La información está en tu edición, pero el guardado sigue pendiente. Usa Guardar borrador y conserva el respaldo.')
    except Exception:
        # No exponer contenido educativo ni payloads del proveedor en el mensaje.
        st.session_state[prefix+'_autollenado_local'] = (
            'No se confirmó el autollenado. Tu borrador se conserva; puedes seguir editando y descargar el respaldo.')


def informacion(prefix, base, destino_ia):
    doc = st.session_state[prefix+'_doc']
    if st.session_state.get(prefix+'_continuidad_doc') == doc['id']:
        st.info('Estás trabajando sin IA. El formato, guardado, recuperación y PDF siguen disponibles. La revisión profesional se conserva.')
        st.button('Volver a preparar con IA', key=prefix+'_volver_ia',
                  on_click=_ir, args=(prefix, base, destino_ia, False))
    with st.expander('Información del expediente y referentes · sin IA'):
        st.caption('Alumno, escuela y periodo ya provienen de tu selección. El autollenado usa solo antecedentes vinculados y referentes elegidos; no inventa NEE, objetivos, actividades ni resultados.')
        st.button('Autollenar información disponible · sin IA', key=prefix+'_autollenar_local',
                  on_click=_autollenar, args=(prefix,))
        mensaje = st.session_state.get(prefix+'_autollenado_local')
        if mensaje: st.caption(mensaje)
        if doc['metadatos'].get('fuentes_pendientes'):
            st.warning('Hay fuentes que no pudieron leerse. Se conserva la información anterior; revisa el expediente antes de darla por completa.')
        st.markdown('**Antecedentes y apoyos documentados**')
        st.write(doc['metadatos'].get('necesidades_confirmadas') or 'Sin antecedentes vinculados disponibles. Completa el formato con información documentada.')
        st.markdown('**Referentes y adaptaciones seleccionadas**')
        st.write(doc['metadatos'].get('referente_curricular') or 'Sin referentes seleccionados todavía. Conserva el acceso a las herramientas curriculares existentes.')
        st.caption('Estos antecedentes son información de consulta, no una conclusión de EPP. Puedes editar las celdas del formato y conservar las herramientas actuales para revisar el resumen.')

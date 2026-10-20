"""Ayuda opcional: guardar no genera, generar no reemplaza la redacción."""
import streamlit as st
import logging
from services import planeacion as s,planeacion_generacion as g
from services.planeacion_papel import huella
from services.planeacion_propuesta import conservar_redaccion,aplicar


def panel(prefix):
    from ui import planeacion as u
    from ui.planeacion_papel import refrescar_editor
    from ui.planeacion_cero_friccion import _asistencia
    doc=st.session_state[prefix+'_doc'];s.autorizar(doc,True)
    st.subheader('Actividades para esta planeación')
    st.caption('La propuesta aparecerá aquí antes de añadirla al formato. Tu redacción actual se conserva.')
    key=prefix+'_asistente'
    config={**g.configuracion(doc),**doc['metadatos'].get('configuracion_generacion',{})}
    with st.form(key+'_ajustes',clear_on_submit=False):
        enfoque=st.text_area('Qué deseas trabajar (opcional)',value=config.get('enfoque',''),key=key+'_enfoque')
        apoyos=st.text_area('Apoyos DUA o recursos disponibles (opcional)',value=config.get('apoyos',''),key=key+'_apoyos')
        motor=st.radio('Preparar actividades',['Con mis datos, sin IA','Con IA'],horizontal=True,key=key+'_motor')
        preparar=st.form_submit_button('Preparar propuesta',type='primary')
    config={**config,'enfoque':enfoque,'apoyos':apoyos}
    if preparar:
        st.session_state.pop(key+'_propuesta',None)
        st.session_state.pop(key+'_solicitud',None)
        try:
            if motor=='Con IA':
                sol=g.preparar_solicitud(doc,config)
                st.session_state[key+'_solicitud']={'sol':sol,'config':config,'base':huella(doc)}
            else:
                from services import planeacion_local as local
                p=local.preparar(doc,enfoque)
                candidate=local.aplicar(doc,p,[r['id'] for r in p['propuestas']])
                st.session_state[key+'_propuesta']={'base':huella(doc),'documento':conservar_redaccion(doc,candidate)}
        except (ValueError,PermissionError,RuntimeError) as exc:st.warning(str(exc))
        except Exception as exc:
            logging.getLogger(__name__).warning('No se pudo preparar la ayuda: %s',type(exc).__name__)
            st.warning('No se pudo preparar la ayuda ahora. Tu hoja se conserva; puedes seguir editando y guardar sin IA.')
    solicitud=st.session_state.get(key+'_solicitud')
    if solicitud:
        st.caption('Revisa el resumen educativo. No se envían archivos originales ni el padrón; no incluyas datos identificadores.')
        st.text(solicitud['sol']['resumen'])
        consentimiento=st.checkbox('Revisé este resumen y autorizo enviarlo a la IA',key=key+'_consent_'+solicitud['sol']['huella'])
        if st.button('Generar actividades con este resumen',disabled=not consentimiento,key=key+'_generar'):
            try:
                if solicitud['base']!=huella(doc):raise ValueError('Tu hoja cambió. Prepara una nueva propuesta; tu edición se conserva.')
                candidate,preview,aviso=_asistencia(doc,'Proponer actividades con IA',solicitud['config'],solicitud['sol'],True)
                if preview:raise ValueError('Los antecedentes cambiaron. Revisa una nueva propuesta antes de enviarla.')
                if candidate==doc:st.info(aviso or 'No hay actividades nuevas. Puedes continuar escribiendo sin IA.')
                else:st.session_state[key+'_propuesta']={'base':huella(doc),'documento':conservar_redaccion(doc,candidate)}
            except Exception:
                st.warning('No se completó la propuesta con IA. Tu hoja sigue editable; puedes preparar actividades con tus datos, sin IA.')
    propuesta=st.session_state.get(key+'_propuesta')
    if not propuesta:return
    candidate=propuesta['documento'];nuevas=0
    for tabla,rows in candidate['tablas'].items():
        for row in rows:
            if row in doc['tablas'].get(tabla,[]):continue
            nuevas+=1
            st.text('\n'.join(str(v) for k,v in row.items() if not k.startswith('_') and str(v).strip()))
    if not nuevas:
        st.info('No hay filas nuevas para añadir. Puedes editar directamente las actividades existentes.');return
    st.caption('Se añadirán al formato, sin sustituir lo que ya escribiste. Después podrás editar o retirar las filas.')
    a,b=st.columns(2)
    if a.button('Añadir propuesta a mi formato',type='primary',key=key+'_aplicar'):
        try:
            if st.session_state.get(prefix+'_pending') and not u._persist(prefix):
                st.warning('Primero necesitamos confirmar tu edición pendiente. No se cambió la propuesta.');return
            result=aplicar(st.session_state[prefix+'_doc'],propuesta)
            u._open(prefix,result);u._persist(prefix)
            st.session_state.pop(key+'_propuesta',None);st.session_state.pop(key+'_solicitud',None)
            st.session_state.pop(prefix+'_papel_panel',None);st.rerun(scope='app')
        except (ValueError,PermissionError,RuntimeError) as exc:st.warning(str(exc))
    if b.button('Descartar propuesta',key=key+'_descartar'):
        st.session_state.pop(key+'_propuesta',None);st.session_state.pop(key+'_solicitud',None);refrescar_editor()

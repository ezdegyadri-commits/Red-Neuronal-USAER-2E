"""Generación visible, editable y recuperable, sin IA durante cada edición."""
from copy import deepcopy
import streamlit as st
from services import planeacion_generacion as g
from ai.planeacion_completa import generar_completa
from ai.planeacion import modelo_configurado, configuracion_modelo


def _ajuste(prefix,key,campo,persist):
    doc=deepcopy(st.session_state[prefix+'_doc']);valor=st.session_state[key]
    if hasattr(valor,'isoformat'):valor=valor.isoformat()
    doc['metadatos'].setdefault('configuracion_generacion',g.configuracion(doc))[campo]=valor
    st.session_state[prefix+'_doc']=doc
    st.session_state.pop(prefix+'_pdf',None)
    persist(prefix,automatic=True)


def _resumen(prefix,key,persist):
    doc=deepcopy(st.session_state[prefix+'_doc'])
    doc['metadatos']['resumen_ia_completo']=st.session_state[key]
    st.session_state[prefix+'_doc']=doc
    consentimiento=f'{prefix}_{st.session_state.get(prefix+"_generation",0)}_generar_consent'
    if consentimiento in st.session_state:st.session_state[consentimiento]=False
    persist(prefix,automatic=True)


def panel_generacion(prefix,persist,abrir):
    doc=st.session_state[prefix+'_doc']
    if doc['formato'] not in ('XXIII','XXV'):return
    st.markdown('#### Generar mi planeación trimestral')
    conexion=configuracion_modelo()
    st.caption('Motor de IA: '+conexion['efectivo']+'. Solo se solicita al pulsar Generar; editar o ver el PDF no consume IA.')
    if conexion['migrado']:
        st.info('Se actualizó la configuración heredada '+conexion['solicitado']+' a '+conexion['efectivo']+'. Se conserva el proveedor y la clave; no se activó facturación.')
    st.caption('Configura las sesiones y ajustes. El sistema reúne la información documentada, propone actividades y completa el formato; después puedes editarlo. No redacta resultados futuros ni coloca firmas automáticamente.')
    ajustes=doc['metadatos'].get('configuracion_generacion',g.configuracion(doc))
    generation=st.session_state.get(prefix+'_generation',0);base=f'{prefix}_{generation}_generar'
    with st.expander('Configurar sesiones y apoyos',expanded=not bool(doc['metadatos'].get('generacion_completa'))):
        izquierda,derecha=st.columns(2)
        desde,hasta=doc['datos']['Periodo'].split(' / ')
        from datetime import date
        key=base+'_inicio'
        inicio=izquierda.date_input('Primera fecha propuesta',value=date.fromisoformat(ajustes['inicio']),min_value=date.fromisoformat(desde),max_value=date.fromisoformat(hasta),key=key,on_change=_ajuste,args=(prefix,key,'inicio',persist))
        key=base+'_duracion'
        duracion=derecha.number_input('Duración de cada sesión (minutos)',min_value=15,max_value=180,value=int(ajustes['duracion']),step=5,key=key,on_change=_ajuste,args=(prefix,key,'duracion',persist))
        key=base+'_sesiones'
        sesiones=izquierda.number_input('Sesiones a organizar en el trimestre',min_value=1,max_value=36,value=int(ajustes['sesiones']),key=key,on_change=_ajuste,args=(prefix,key,'sesiones',persist))
        key=base+'_dias'
        dias=derecha.multiselect('Días para proponer las sesiones',list(g.DIAS),default=ajustes['dias'],key=key,on_change=_ajuste,args=(prefix,key,'dias',persist))
        key=base+'_enfoque'
        enfoque=st.text_area('Qué deseas priorizar (opcional)',value=ajustes.get('enfoque',''),placeholder='Ejemplo: comunicar necesidades en el aula, con apoyos visuales.',max_chars=1500,key=key,on_change=_ajuste,args=(prefix,key,'enfoque',persist))
        key=base+'_apoyos'
        apoyos=st.text_area('Ajustes, recursos disponibles o apoyos que deseas conservar',value=ajustes.get('apoyos',''),max_chars=1500,key=key,on_change=_ajuste,args=(prefix,key,'apoyos',persist))
        grado_key=base+'_grado'
        grado=izquierda.selectbox('Grado de referencia para los contenidos',[None,1,2,3,4,5,6],index=[None,1,2,3,4,5,6].index(ajustes.get('grado_referencia')),format_func=lambda n:'Por elegir' if n is None else str(n)+'°',key=grado_key,on_change=_ajuste,args=(prefix,grado_key,'grado_referencia',persist))
        campo_key=base+'_campo'
        campo=derecha.selectbox('Campo para fundamentar las actividades',list(g.CAMPOS),index=list(g.CAMPOS).index(ajustes.get('campo_referencia','Lenguajes')),key=campo_key,on_change=_ajuste,args=(prefix,campo_key,'campo_referencia',persist))
        st.caption('El sistema propone referentes exactos del catálogo por tema y grado elegido. Puedes cambiar a un grado anterior sin modificar el padrón. Los referentes sugeridos requieren revisión y siguen siendo editables.')
        st.caption('Las fechas evitan fines de semana, CTE y suspensiones del calendario cargado. Son propuestas: no reservan espacios ni sustituyen la revisión de tu horario o cronograma.')
    ajustes={**ajustes,'inicio':inicio.isoformat(),'duracion':duracion,'sesiones':sesiones,'dias':dias,'enfoque':enfoque,'apoyos':apoyos,'grado_referencia':grado,'campo_referencia':campo}
    solicitud=None
    try:solicitud=g.preparar_solicitud(st.session_state[prefix+'_doc'],ajustes)
    except (ValueError,PermissionError) as exc:st.info(str(exc))
    if solicitud:
        with st.expander('Revisar la información que analizará la IA'):
            st.caption('Este es el resumen educativo, no los archivos originales. Corrige nombres o datos que puedan identificar a alguien. Los referentes oficiales y ajustes revisados se envían por separado; nunca el padrón.')
            key=base+'_resumen'
            st.text_area('Resumen educativo que analizará la IA',value=solicitud['resumen'],height=180,max_chars=12000,key=key,on_change=_resumen,args=(prefix,key,persist))
            st.caption('Evidencias vinculadas: '+', '.join(solicitud['evidencias']))
        consentimiento=st.checkbox('Revisé el resumen y los ajustes: no identifican a las personas. Solicitar propuestas educativas con IA.',key=base+'_consent')
    else:consentimiento=False
    previo=doc['metadatos'].get('generacion_completa',{})
    coincide=bool(solicitud and previo.get('huella')==solicitud['huella'] and previo.get('motor')==modelo_configurado())
    etiqueta='Generar mi planeación trimestral con IA'
    if coincide:st.caption('La generación para esta información ya está guardada. Puedes recuperar el resultado sin hacer otra solicitud de IA.')
    if st.button('Recuperar la generación guardada' if coincide else etiqueta,type='primary',disabled=not consentimiento or not solicitud,key=base+'_button',use_container_width=True):
        try:
            actual=deepcopy(st.session_state[prefix+'_doc'])
            actual['metadatos']['configuracion_generacion']=deepcopy(ajustes)
            solicitud=g.preparar_solicitud(actual,ajustes)
            if coincide:respuesta=previo['resultado']
            else:
                with st.spinner('Analizando la información documentada y preparando el formato…'):
                    respuesta=generar_completa(solicitud['resumen'],actual['formato'],actual['datos']['Función'],solicitud['contexto'],solicitud['ajustes'],solicitud['aliases'],solicitud['evidencias'])
            if not respuesta['unidades']:
                st.info(respuesta['observaciones'] or 'Falta información para sostener actividades.')
                for pregunta in respuesta['faltantes']:st.caption(pregunta)
            else:
                generado=g.ensamblar(actual,respuesta,solicitud)
                generado['metadatos']['generacion_completa']['motor']=modelo_configurado()
                if previo:
                    st.session_state[prefix+'_propuesta_pendiente']={'respuesta':respuesta,'solicitud':solicitud,'revision':actual.get('revision','')}
                    st.rerun()
                else:abrir(prefix,generado);persist(prefix);st.rerun()
        except (ValueError,PermissionError,RuntimeError) as exc:st.info(str(exc))
    pendiente=st.session_state.get(prefix+'_propuesta_pendiente')
    if pendiente:
        st.markdown('##### Revisar antes de actualizar el borrador')
        st.caption('Se conservan las ediciones y eliminaciones de sesiones registradas desde la última generación. Solo se sustituyen las partes que siguen iguales a su versión automática.')
        for unidad in pendiente['respuesta']['unidades']:
            with st.expander('Nueva propuesta · '+unidad['objetivo']):st.write(unidad['actividad'])
        st.caption('Tu borrador actual sigue intacto; puedes compararlo con la vista previa de abajo.')
        if st.button('Aplicar actualización conservando mis ediciones',key=base+'_apply'):
            try:
                actual=st.session_state[prefix+'_doc']
                if actual.get('revision','')!=pendiente['revision']:raise ValueError('Cambió el borrador. Revisa o genera una nueva propuesta antes de aplicar.')
                generado=g.ensamblar(actual,pendiente['respuesta'],pendiente['solicitud'])
                generado['metadatos']['generacion_completa']['motor']=modelo_configurado()
                abrir(prefix,generado);persist(prefix)
                st.session_state.pop(prefix+'_propuesta_pendiente',None);st.rerun()
            except (ValueError,PermissionError,RuntimeError) as exc:st.info(str(exc))
        if st.button('Conservar mi borrador sin aplicar la propuesta',key=base+'_cancel'):
            st.session_state.pop(prefix+'_propuesta_pendiente',None);st.rerun()
    diagnostico=st.session_state.get('planeacion_ia_diagnostico')
    if diagnostico:st.caption('Diagnóstico de IA: '+str(diagnostico.get('codigo') or diagnostico.get('tipo'))+' · Modelo: '+str(diagnostico.get('motor',''))+' · Tu borrador se conserva.')
    if previo:
        st.success('Formato preparado como borrador editable. Revisa actividades, destinatarios, apoyos y fechas antes de compartir con Dirección.')
        for pregunta in previo.get('pendientes',[]):st.caption('Por confirmar: '+pregunta)

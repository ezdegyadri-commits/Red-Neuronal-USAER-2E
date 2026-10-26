"""Ayuda opcional: guardar no genera, generar no reemplaza la redacción."""
import streamlit as st
import logging
from services import planeacion as s,planeacion_generacion as g
from services.planeacion_papel import huella
from services.planeacion_propuesta import conservar_redaccion,aplicar
from services import planeacion_rapida as rapido
from services.planeacion_modelo import FORMATOS


def panel(prefix):
    from ui import planeacion as u
    from ui.planeacion_papel import refrescar_editor
    from ui.planeacion_cero_friccion import _asistencia
    doc=st.session_state[prefix+'_doc'];s.autorizar(doc,True)
    st.subheader('Actividades para esta planeación')
    st.caption('La propuesta aparecerá aquí antes de añadirla al formato. Tu redacción actual se conserva.')
    key=prefix+'_asistente'
    config={**g.configuracion(doc),**doc['metadatos'].get('configuracion_generacion',{})}
    estado=rapido.estado(doc);defaults=estado['defaults']
    # Claves por documento: las preferencias de otro alumno no se trasladan.
    widgets=key+'_'+doc['id']
    st.markdown('**Datos ya conectados**')
    st.caption(str(len(doc['datos']['Alumnos']))+' alumno(s) · '+str(len(estado['fuentes']))+' antecedentes vinculados. No necesitas volver a capturarlos.')
    with st.expander('Consultar NEE, BAP y referentes disponibles',expanded=False):
        st.markdown('**Necesidades educativas específicas**')
        for texto in estado['nee']:st.text(texto)
        if not estado['nee']:st.caption('No hay una NEE redactada disponible. No se sustituirá por respuestas del instrumento BAPSE.')
        st.markdown('**Barreras documentadas — distintas de las NEE**')
        for row in estado['bap']:st.text(row.get(rapido.BARRERA,'')+' · '+row['fuente'])
        if not estado['bap']:st.caption('Sin BAP explícitas vinculadas; no se inferirán del instrumento.')
        registros=doc['metadatos'].get('curriculo',{}).get('registros',[])
        st.caption(str(len(registros))+' referentes curriculares ya vinculados. Se conservan los PDA seleccionados, sin inventar referentes oficiales.')
        for registro in registros:
            st.text('Contenido: '+str(registro.get('contenido',''))+'\nPDA: '+str(registro.get('pda','')))
        for fuente in estado['fuentes']:st.caption(str(fuente['tipo'])+' · '+str(fuente['referencia']))
    for aviso in estado['avisos']:st.info(aviso)
    st.markdown('**Prepara actividades distintas para tus alumnos**')
    a,b=st.columns(2)
    cantidad=a.selectbox('Cantidad de actividades',list(range(1,9)),index=2,key=widgets+'_cantidad')
    selecciones={**defaults}
    selecciones['duracion']=b.selectbox('Minutos por actividad',[15,20,30,45,60],index=[15,20,30,45,60].index(defaults['duracion']),key=widgets+'_duracion')
    selecciones['contextos']=st.multiselect('Contextos de intervención',FORMATOS[doc['formato']]['contextos'],default=defaults['contextos'],key=widgets+'_contextos')
    selecciones['tematica']=st.text_input('Temática o interés del alumno (opcional)',value=defaults['tematica'],max_chars=300,placeholder='Se utilizarán sus necesidades y antecedentes si lo dejas vacío',key=widgets+'_tematica')
    with st.expander('Personalizar apoyos y otros detalles (opcional)',expanded=False):
        st.caption('Las opciones ya están sugeridas con los datos del alumno. Modifícalas solo si lo necesitas.')
        selecciones['prioridades']=st.multiselect('Qué vamos a trabajar',estado['permitidas'],default=defaults['prioridades'],format_func=lambda p:rapido.PRIORIDADES[p][0],key=widgets+'_prioridades')
        selecciones['apoyos']=st.multiselect('Apoyos para participar y responder',list(rapido.APOYOS),default=defaults['apoyos'],format_func=lambda p:rapido.APOYOS[p][0],key=widgets+'_apoyos')
        selecciones['metodo']=st.selectbox('Cómo lo trabajaremos',list(rapido.METODOS),index=list(rapido.METODOS).index(defaults['metodo']),format_func=lambda p:rapido.METODOS[p],key=widgets+'_metodo')
        a,b=st.columns(2)
        selecciones['frecuencia']=b.selectbox('Frecuencia propuesta',rapido.FRECUENCIAS,index=rapido.FRECUENCIAS.index(defaults['frecuencia']),key=widgets+'_frecuencia')
        selecciones['acuerdos']=st.multiselect('Acuerdos CTE registrados',list(estado['acuerdos']),default=defaults['acuerdos'],format_func=lambda p:estado['acuerdos'][p]['texto'],key=widgets+'_acuerdos',disabled=not estado['acuerdos'])
        if not estado['acuerdos']:st.caption('No hay acuerdos de CTE explícitos y verificados vinculados a esta planeación.')
        selecciones['completar']=st.checkbox('Completar apartados vacíos al preparar sin IA',value=defaults['completar'],key=widgets+'_completar')
        st.caption('El autollenado es opcional: no se recuperarán campos que retiraste sin que lo solicites.')
        motor=st.radio('Preparar actividades',['Con mis datos, sin IA','Con IA'],index=1,horizontal=True,key=key+'_motor')
    errores=rapido.validar(doc,selecciones)
    for error in errores:st.warning(error)
    preparar=st.button('Preparar propuesta',type='primary',disabled=bool(errores),key=widgets+'_preparar',use_container_width=True)
    if not errores:config={**config,**rapido.orientaciones(doc,selecciones),'duracion':selecciones['duracion'],
        'sesiones':cantidad,'actividades_solicitadas':cantidad,'contextos_solicitados':selecciones['contextos']}
    if preparar:
        st.session_state.pop(key+'_propuesta',None)
        st.session_state.pop(key+'_solicitud',None)
        try:
            if motor=='Con IA':
                sol=g.preparar_solicitud(doc,config)
                st.session_state[key+'_solicitud']={'sol':sol,'config':config,'base':huella(doc),'selecciones':selecciones}
            else:
                candidate=rapido.ensamblar(doc,selecciones)
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
                else:
                    candidate['metadatos']['preparacion_rapida']={'selecciones':solicitud['selecciones'],'requiere_revision':True,'motor':'IA'}
                    st.session_state[key+'_propuesta']={'base':huella(doc),'documento':conservar_redaccion(doc,candidate)}
            except Exception as exc:
                from ui.planeacion_progreso import mostrar_error
                mostrar_error(exc)
    propuesta=st.session_state.get(key+'_propuesta')
    if not propuesta:return
    st.markdown('**Revisa la propuesta**')
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

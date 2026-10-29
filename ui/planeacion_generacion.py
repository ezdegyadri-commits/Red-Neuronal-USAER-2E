"""Generación visible, editable y recuperable, sin IA durante cada edición."""
from copy import deepcopy
import streamlit as st
from ui.planeacion_pendientes import raiz
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


def _prioridades(prefix,key,campo,persist):
    doc=deepcopy(st.session_state[prefix+'_doc'])
    config=doc['metadatos'].setdefault('configuracion_generacion',g.configuracion(doc))
    config[campo]=st.session_state[key]
    # La orientación se guarda por separado; no sustituye redacción previa.
    st.session_state[prefix+'_doc']=doc
    persist(prefix,automatic=True)


def _revision(prefix,compact):
    if compact:
        from ui.planeacion_simple import PASOS
        st.session_state[raiz(prefix)+'_paso_pendiente']=PASOS[2]


def panel_generacion(prefix,persist,abrir,compact=False):
    doc=st.session_state[prefix+'_doc']
    if doc['formato'] not in ('XXIII','XXV'):return
    integradas=st.session_state.pop(prefix+'_actividades_integradas',None)
    if integradas:
        destino='los apartados «Actividades y evaluación» de cada NEE' if doc['metadatos'].get('intervenciones_nee') else '«Organización de las actividades de aprendizaje» → columna «Actividades»'
        st.success(f'{integradas} propuesta(s) ya están en el borrador, en {destino}. No tienes que copiarlas: edítalas ahí y guarda la hoja.')
    if not compact:st.markdown('#### Generar mi planeación trimestral')
    conexion=configuracion_modelo()
    if not compact:st.caption('Motor de IA: '+conexion['efectivo']+'. Solo se solicita al pulsar Generar; editar o ver el PDF no consume IA.')
    if conexion['migrado']:
        st.info('Se actualizó la configuración heredada '+conexion['solicitado']+' a '+conexion['efectivo']+'. Se conserva el proveedor y la clave; no se activó facturación.')
    st.caption('Configura las sesiones y ajustes. El sistema reúne la información documentada, propone actividades y completa el formato; después puedes editarlo. No redacta resultados futuros ni coloca firmas automáticamente.')
    if compact:
        st.markdown('**Para añadir actividades con IA**\n\n1. Revisa el resumen y marca la confirmación.\n2. Pulsa **Generar e integrar actividades al formato**.\n3. Si es una actualización, revisa la vista previa y pulsa **Aplicar actualización conservando mis ediciones**.\n4. Cierra este panel: las actividades están en **Organización de las actividades de aprendizaje → Actividades**. No copies ni pegues; edítalas ahí y guarda la hoja.')
    ajustes={**g.configuracion(doc),**doc['metadatos'].get('configuracion_generacion',{})}
    generation=st.session_state.get(prefix+'_generation',0);base=f'{prefix}_{generation}_generar'
    col_mot1, col_mot2 = st.columns([0.72, 0.28])
    with col_mot1:
        motor_plan = st.radio(
            "Motor de IA",
            ["Gemini Pro (Google)", "Gemini Flash (Google)", "ChatGPT (OpenAI)"],
            horizontal=True,
            key=base + "_motor_ia"
        )
        if "Gemini Pro" in motor_plan:
            st.session_state['planeacion_motor'] = 'Gemini (Google)'
            st.session_state['planeacion_modelo_preferido'] = 'gemini-2.5-pro'
        elif "Gemini Flash" in motor_plan:
            st.session_state['planeacion_motor'] = 'Gemini (Google)'
            st.session_state['planeacion_modelo_preferido'] = 'gemini-3.8-flash'
        else:
            st.session_state['planeacion_motor'] = 'ChatGPT (OpenAI)'
            has_sec = False
            try:
                has_sec = bool(st.secrets.get("OPENAI_API_KEY"))
            except Exception:
                has_sec = False
            if not has_sec:
                st.text_input(
                    "OpenAI API Key (ChatGPT Plus)",
                    type="password",
                    key="planeacion_openai_key",
                    help="Tu clave se usará en esta sesión para generar propuestas con GPT-4o.",
                )
    from datetime import date
    inicio=date.fromisoformat(ajustes['inicio']);duracion=ajustes['duracion'];sesiones=ajustes['sesiones']
    dias=ajustes['dias'];enfoque=ajustes.get('enfoque','');apoyos=ajustes.get('apoyos','')
    grado=ajustes.get('grado_referencia');campo=ajustes.get('campo_referencia','Lenguajes')
    if compact:
        act_actual = ajustes.get('actividades_solicitadas', min(15, int(sesiones)))
        st.caption(f"{sesiones} sesiones · {act_actual} actividades progresivas · {duracion} min · {', '.join(dias)} · desde {inicio.isoformat()}")
        st.caption(f"Referencia sugerida: {grado}° · {campo}." if grado else f"Referencia sugerida del grupo · {campo}.")
        key=base+'_enfoque'
        enfoque=st.text_area('Barrera prioritaria (opcional)' if doc['datos']['Función']=='Trabajo Social' else '¿Qué quieres priorizar? (opcional)',value=enfoque,max_chars=1500,key=key,on_change=_ajuste,args=(prefix,key,'enfoque',persist))
        if doc['datos']['Función']=='Psicología':
            from services.planeacion_equipo import COMPETENCIAS
            st.caption('Competencias a priorizar, según la evidencia (opcional):')
            prioridades=[]
            for i,competencia in enumerate(COMPETENCIAS):
                key=base+'_competencia_'+str(i)
                if st.checkbox(competencia,value=competencia in ajustes.get('competencias_priorizadas',[]),key=key):prioridades.append(competencia)
            if prioridades!=ajustes.get('competencias_priorizadas',[]):
                doc=deepcopy(st.session_state[prefix+'_doc'])
                doc['metadatos'].setdefault('configuracion_generacion',g.configuracion(doc))['competencias_priorizadas']=prioridades
                st.session_state[prefix+'_doc']=doc;persist(prefix,automatic=True)
            ajustes={**ajustes,'competencias_priorizadas':prioridades}
        if doc['datos']['Función']=='Trabajo Social':
            key=base+'_contextos'
            contextos=st.multiselect('¿En qué contextos trabajarás? (opcional)',['Aula regular','Escuela','Familia','Comunidad'],default=ajustes.get('contextos_priorizados',[]),key=key,on_change=_prioridades,args=(prefix,key,'contextos_priorizados',persist))
            ajustes={**ajustes,'contextos_priorizados':contextos}
        configurar=st.toggle('Cambiar sesiones, apoyos o referencia',key=base+'_cambiar')
    else:configurar=True
    if configurar:
      with st.expander('Configurar sesiones y apoyos',expanded=True):
        izquierda,derecha=st.columns(2)
        desde,hasta=doc['datos']['Periodo'].split(' / ')
        from datetime import date
        key=base+'_inicio'
        inicio=izquierda.date_input('Primera fecha propuesta',value=date.fromisoformat(ajustes['inicio']),min_value=date.fromisoformat(desde),max_value=date.fromisoformat(hasta),key=key,on_change=_ajuste,args=(prefix,key,'inicio',persist))
        key=base+'_duracion'
        duracion=derecha.number_input('Duración de cada sesión (minutos)',min_value=15,max_value=180,value=int(ajustes['duracion']),step=5,key=key,on_change=_ajuste,args=(prefix,key,'duracion',persist))
        col_ses1, col_ses2 = izquierda.columns(2)
        key=base+'_sesiones'
        sesiones=col_ses1.number_input('Sesiones en el trimestre',min_value=1,max_value=36,value=int(ajustes['sesiones']),key=key,on_change=_ajuste,args=(prefix,key,'sesiones',persist))
        key_act=base+'_actividades_solicitadas'
        act_def = min(int(sesiones), max(10, int(ajustes.get('actividades_solicitadas', min(15, int(sesiones))))))
        actividades_solicitadas = col_ses2.number_input('Actividades distintas',min_value=1,max_value=24,value=act_def,step=1,key=key_act,on_change=_ajuste,args=(prefix,key_act,'actividades_solicitadas',persist),help='Define cuántas actividades progresivas distintas generar para cubrir el trimestre (ej. 10 a 15).')
        key=base+'_dias'
        dias=derecha.multiselect('Días para proponer las sesiones',list(g.DIAS),default=ajustes['dias'],key=key,on_change=_ajuste,args=(prefix,key,'dias',persist))
        if not compact:
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
    ajustes={**ajustes,'inicio':inicio.isoformat(),'duracion':duracion,'sesiones':sesiones,'actividades_solicitadas':actividades_solicitadas if 'actividades_solicitadas' in locals() else ajustes.get('actividades_solicitadas',min(12,int(sesiones))),'dias':dias,'enfoque':enfoque,'apoyos':apoyos,'grado_referencia':grado,'campo_referencia':campo}
    # Los servicios existentes ya admiten un enfoque educativo. Sin cambiar su
    # contrato, presentar las prioridades opcionales como orientación, no hallazgos.
    orientaciones=[]
    if ajustes.get('competencias_priorizadas'):orientaciones.append('Competencias a priorizar si la evidencia lo permite: '+', '.join(ajustes['competencias_priorizadas']))
    if ajustes.get('contextos_priorizados'):orientaciones.append('Contextos priorizados: '+', '.join(ajustes['contextos_priorizados']))
    ajustes_solicitud={**ajustes,'enfoque':(enfoque+'\n'+'\n'.join(orientaciones)).strip()}
    solicitud=None
    falta_evidencia=False
    try:solicitud=g.preparar_solicitud(st.session_state[prefix+'_doc'],ajustes_solicitud)
    except (ValueError,PermissionError) as exc:
        msg=str(exc)
        if 'evidencia' in msg.lower():falta_evidencia=True
        st.info(msg)
    from ui.planeacion_chat import render_asistente_dialogo
    render_asistente_dialogo(prefix,persist,expandido=not solicitud or falta_evidencia)
    if solicitud:
        with st.expander('Ver qué se envía' if compact else 'Revisar la información que analizará la IA'):
            st.caption('Este es el resumen educativo, no los archivos originales. Corrige nombres o datos que puedan identificar a alguien. Los referentes oficiales y ajustes revisados se envían por separado; nunca el padrón.')
            key=base+'_resumen'
            st.text_area('Resumen educativo que analizará la IA',value=solicitud['resumen'],height=180,max_chars=60000,key=key,on_change=_resumen,args=(prefix,key,persist))
            st.caption('Evidencias vinculadas: '+', '.join(solicitud['evidencias']))
        consentimiento=st.checkbox('Revisé el resumen y los ajustes: no identifican a las personas. Solicitar propuestas educativas con IA.',key=base+'_consent')
    else:consentimiento=False
    previo=doc['metadatos'].get('generacion_completa',{})
    from ui import planeacion_tareas as tareas
    from services.planeacion_edicion import huella
    coincide=bool(solicitud and previo.get('huella')==solicitud['huella'] and previo.get('motor')==modelo_configurado())
    etiqueta='Generar e integrar actividades al formato' if compact else 'Generar mi planeación trimestral con IA'
    if coincide:st.caption('La generación para esta información ya está guardada. Puedes recuperar el resultado sin hacer otra solicitud de IA.')
    recuperada=None
    if st.button('Recuperar la generación guardada' if coincide else etiqueta,type='primary',disabled=not consentimiento or not solicitud or prefix+'_ia_trabajo' in st.session_state,key=base+'_button',width='stretch'):
        try:
            actual=deepcopy(st.session_state[prefix+'_doc'])
            actual['metadatos']['configuracion_generacion']=deepcopy(ajustes)
            solicitud=g.preparar_solicitud(actual,ajustes_solicitud)
            if coincide:recuperada={'respuesta':previo['resultado'],'solicitud':solicitud,'huella':huella(actual),'revision':actual.get('revision','')}
            else:tareas.iniciar(prefix,solicitud,actual)
        except (ValueError,PermissionError,RuntimeError) as exc:st.warning(str(exc))
    try:
        lista=recuperada or tareas.recoger(prefix,st.session_state[prefix+'_doc'])
        if lista:
            respuesta=lista['respuesta'];solicitud=lista['solicitud'];actual=deepcopy(st.session_state[prefix+'_doc'])
            if not respuesta['unidades']:
                st.info(respuesta['observaciones'] or 'Falta información para sostener actividades.')
                for pregunta in respuesta['faltantes']:st.caption(pregunta)
            else:
                if previo or lista['huella']!=huella(actual):
                    st.session_state[prefix+'_propuesta_pendiente']={'respuesta':respuesta,'solicitud':solicitud,'revision':lista['revision'],'huella':lista['huella']}
                    st.rerun()
                else:
                    generado=g.ensamblar(actual,respuesta,solicitud)
                    generado['metadatos']['generacion_completa']['motor']=modelo_configurado()
                    generado['metadatos']['configuracion_generacion']=deepcopy(ajustes)
                    st.session_state[prefix+'_actividades_integradas']=len(respuesta['unidades'])
                    abrir(prefix,generado);persist(prefix);_revision(prefix,compact);st.rerun()
    except (ValueError,PermissionError,RuntimeError) as exc:st.warning(str(exc))
    tareas.estado(prefix)
    pendiente=st.session_state.get(prefix+'_propuesta_pendiente')
    if pendiente:
        st.markdown('##### Revisar antes de actualizar el borrador')
        st.caption('Se conservan las ediciones y eliminaciones de sesiones registradas desde la última generación. Solo se sustituyen las partes que siguen iguales a su versión automática.')
        unidades_disponibles=pendiente['respuesta'].get('unidades',[])
        for i,unidad in enumerate(unidades_disponibles):
            with st.expander(f"Propuesta {i+1} · {unidad.get('objetivo','')}",expanded=True):
                st.markdown(f"**Actividad:**\n{unidad.get('actividad','')}")
                c_ap,c_rec=st.columns(2)
                c_ap.markdown(f"**Apoyos y ajustes:**\n{unidad.get('apoyos','')}")
                c_rec.markdown(f"**Recursos accesibles:**\n{unidad.get('recursos','')}")
                st.caption(f"Indicador observable / evaluación: {unidad.get('evaluacion','')}")
                check_key=f'{base}_inc_unidad_{i}'
                if check_key not in st.session_state:st.session_state[check_key]=True
                incluir=st.checkbox('✅ Incluir esta propuesta en mi formato',key=check_key)
                if not incluir:
                    motivo_key=f'{base}_motivo_{i}'
                    motivo=st.selectbox('¿Por qué no es adecuada? (opcional)',[
                        'Elige un motivo...',
                        'Demasiado compleja para su nivel actual',
                        'Muy básica o infantil para su edad cronológica',
                        'Material no disponible en el aula',
                        'No corresponde a su nivel real de lectoescritura/cálculo',
                        'Enfocar en otra habilidad prioritaria'
                    ],key=motivo_key)
                    if motivo!='Elige un motivo...':
                        st.info(f'Retroalimentación registrada: {motivo}. Puedes ajustar "¿Qué deseas priorizar?" arriba para solicitar una alternativa orientada.')
        st.caption('Tu borrador actual sigue intacto; puedes compararlo con la vista previa de abajo.')
        if st.button('Aplicar actualización conservando mis ediciones',key=base+'_apply'):
            try:
                actual=st.session_state[prefix+'_doc']
                if actual.get('revision','')!=pendiente['revision']:raise ValueError('Cambió el borrador. Revisa o genera una nueva propuesta antes de aplicar.')
                if pendiente.get('huella') and pendiente['huella']!=huella(actual):raise ValueError('Editaste el documento durante la generación. Tu texto se conserva; genera otra propuesta con la información actual.')
                seleccionadas=[u for i,u in enumerate(unidades_disponibles) if st.session_state.get(f'{base}_inc_unidad_{i}',True)]
                if not seleccionadas:raise ValueError('Selecciona al menos una propuesta para integrar al formato, o pulsa «Conservar mi borrador».')
                resp_filtrada=deepcopy(pendiente['respuesta'])
                resp_filtrada['unidades']=seleccionadas
                generado=g.ensamblar(actual,resp_filtrada,pendiente['solicitud'])
                generado['metadatos']['generacion_completa']['motor']=modelo_configurado()
                generado['metadatos']['configuracion_generacion']=deepcopy(st.session_state[prefix+'_doc'].get('metadatos',{}).get('configuracion_generacion',{}))
                st.session_state[prefix+'_actividades_integradas']=len(seleccionadas)
                abrir(prefix,generado);persist(prefix);_revision(prefix,compact)
                st.session_state.pop(prefix+'_propuesta_pendiente',None);st.rerun()
            except (ValueError,PermissionError,RuntimeError) as exc:st.info(str(exc))
        if st.button('Conservar mi borrador sin aplicar la propuesta',key=base+'_cancel'):
            st.session_state.pop(prefix+'_propuesta_pendiente',None);st.rerun()
    diagnostico=st.session_state.get('planeacion_ia_diagnostico')
    if diagnostico:st.caption('Diagnóstico de IA: '+str(diagnostico.get('codigo') or diagnostico.get('tipo'))+' · Modelo: '+str(diagnostico.get('motor',''))+' · Tu borrador se conserva.')
    if previo:
        st.success('Formato preparado como borrador editable. Revisa actividades, destinatarios, apoyos y fechas antes de compartir con Dirección.')
        for pregunta in previo.get('pendientes',[]):st.caption('Aspecto a considerar: '+pregunta)


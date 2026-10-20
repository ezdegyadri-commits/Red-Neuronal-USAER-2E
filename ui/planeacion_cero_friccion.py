"""Una captura, sobre la hoja tradicional, y un solo envío explícito al final."""
import json
import streamlit as st
from services import planeacion as s, planeacion_papel as papel
from services import planeacion_cero_friccion as flujo
from services.planeacion_modelo import FORMATOS


def _celda(c,key):
    if not c['editable']:
        st.text(c['value'] or '—')
        return c['value']
    if c.get('opciones'):
        opciones=c['opciones'];value=c['value'] if c['value'] in opciones else opciones[0]
        return st.selectbox(c['label'],opciones,index=opciones.index(value),key=key)
    if c.get('nota'):st.caption(c['nota'])
    return st.text_area(c['label'],value=c['value'],height=140,key=key)


def _conexiones(doc,key):
    from services import curriculo as cur, planeacion_generacion as g
    config={**g.configuracion(doc),**doc['metadatos'].get('configuracion_generacion',{})}
    old=doc['metadatos'].get('curriculo',{})
    with st.expander('Expediente, referentes oficiales y apoyos DUA',expanded=False):
        st.caption('Se conservan las fuentes conectadas por alumno. Una BAP del contexto no equivale a una NEE.')
        from services.planeacion_generacion import fuentes_pertinentes
        for fuente in fuentes_pertinentes(doc):
            with st.expander(str(fuente.get('referencia','Antecedente'))+' · '+str(fuente.get('fecha',''))):
                st.text(fuente.get('texto',''))
        actualizar=st.checkbox('Actualizar antecedentes del expediente al guardar',key=key+'_actualizar_fuentes')
        campos=st.multiselect('Campos formativos',list(cur.CAMPOS),default=cur.campos_seleccionados(old),key=key+'_campos')
        # Dentro del form no hay callbacks: todos los campos se confirman juntos.
        # El selector contiene el catálogo completo y permite buscar por grado y campo.
        catalogo=cur.catalogo()['registros'];porid={r['id']:r for r in catalogo}
        ids=st.multiselect('Contenidos y PDA · busca por grado, campo o palabras',list(porid),
            default=[r['id'] for r in old.get('registros',[]) if r['id'] in porid],max_selections=6,
            format_func=lambda i:f"{porid[i]['grado']}° · {porid[i]['campo']} · {porid[i]['contenido']} · {porid[i]['pda']}",key=key+'_pda')
        for i in ids:
            r=porid[i];st.caption(r['fuente']+' · página PDF '+str(r['pagina_pdf']))
        st.caption('El campo de cada PDA elegido se conecta automáticamente; no tienes que seleccionarlo de nuevo.')
        campos=list(dict.fromkeys(campos+[porid[i]['campo'] for i in ids]))
        ejes=st.multiselect('Ejes articuladores',list(cur.EJES),default=old.get('ejes',[]),key=key+'_ejes')
        contexto=st.text_area('Contextualización de la escuela',value=old.get('contexto_local',''),key=key+'_contexto')
        apoyos=st.text_area('Apoyos DUA y ajustes para participar, comprender y expresarse',value=config.get('apoyos',''),key=key+'_dua')
        enfoque=st.text_area('Prioridad de la intervención (opcional)',value=config.get('enfoque',''),key=key+'_enfoque')
        st.caption('Las adaptaciones docentes previas siguen vinculadas al PDA. No se cambia el texto oficial del catálogo.')
    return {**config,'apoyos':apoyos,'enfoque':enfoque},(campos,ejes,ids,contexto),actualizar


def _asistencia(doc,accion,config,preview,consent):
    """Nunca envía a IA información diferente de la vista previa consentida."""
    from services import planeacion_generacion as g
    if accion in ('Solo guardar','Guardar y enviar a Dirección'):return doc,None,None
    if accion=='Completar apartados vacíos con mis datos':
        from services.planeacion_apartados import proponer
        return proponer(doc),None,'Se completaron solo los apartados con sustento disponible. Revisa las propuestas en tu hoja.'
    if accion=='Proponer actividades sin IA':
        from services import planeacion_local as local
        propuesta=local.preparar(doc,config.get('enfoque',''))
        if consent and preview and preview.get('tipo')=='local' and preview['propuestas']==propuesta['propuestas']:
            return local.aplicar(doc,propuesta,[r['id'] for r in propuesta['propuestas']]),None,'Las propuestas revisadas se añadieron a Actividades. Puedes editarlas o eliminarlas.'
        return doc,{'tipo':'local',**propuesta},'Revisa las propuestas sin IA y confírmalas con el mismo botón Guardar Planeación.'
    if doc['formato'] not in ('XXIII','XXV'):raise ValueError('La propuesta completa se prepara en el formato trimestral XXIII o XXV.')
    solicitud=g.preparar_solicitud(doc,config)
    if not consent or not preview or preview['huella']!=solicitud['huella']:
        return doc,solicitud,'Tu edición se guardará. Revisa el resumen de IA y confirma su envío con el mismo botón Guardar Planeación.'
    from ai.planeacion_completa import generar_completa
    from ai.planeacion import modelo_configurado
    respuesta=generar_completa(solicitud['resumen'],doc['formato'],doc['datos']['Función'],
        solicitud['contexto'],solicitud['ajustes'],solicitud['aliases'],solicitud['evidencias'])
    if not respuesta['unidades']:return doc,None,'La IA no produjo actividades sustentadas. Tu edición se conserva y puedes continuar sin IA.'
    result=g.ensamblar(doc,respuesta,solicitud)
    result['metadatos']['generacion_completa']['motor']=modelo_configurado()
    return result,None,'Las actividades propuestas ya están en Organización de las actividades de aprendizaje. Todo queda editable.'


def hoja(prefix,volver=None):
    from ui import planeacion as u
    doc=st.session_state[prefix+'_doc'];s.autorizar(doc,True)
    if not flujo.aplica(doc):raise PermissionError('Continúa este documento en la hoja grupal compartida.')
    spec=papel.hoja(doc);generation=st.session_state.get(prefix+'_captura_generation',0)
    key=f'{prefix}_{doc["id"]}_captura_{generation}'
    if aviso:=st.session_state.pop(prefix+'_captura_aviso',None):st.success(aviso)
    if error:=st.session_state.get(prefix+'_error'):st.warning(error)
    st.caption('Edita sobre tu formato. Los cambios se envían juntos al pulsar Guardar Planeación; no se guardan campo por campo. Guarda antes de cambiar de pantalla o cerrar la sesión.')
    if doc.get('guardado_en'):st.caption('Último guardado confirmado: '+doc['guardado_en'][:19].replace('T',' '))
    cambios={};nuevas={};retirar={};preview=st.session_state.get(prefix+'_captura_preview')
    st.html('<style>.st-key-'+key+'_hoja{font-family:Georgia,"Times New Roman",serif;background:#fff;color:#172b32} .st-key-'+key+'_hoja textarea{font-family:Georgia,"Times New Roman",serif;line-height:1.5} .st-key-'+key+'_hoja h3{text-align:center}</style>')
    with st.form(key+'_form',clear_on_submit=False):
        with st.container(border=True,key=key+'_hoja'):
            st.markdown('### '+spec['titulo'])
            for row in spec['header']:
                for col,value in zip(st.columns(len(row)),row):
                    with col:st.text(value if isinstance(value,str) else value.get('value',''))
            for table in spec['tables']:
                if table['title']:st.markdown('#### '+table['title'])
                with st.expander(table.get('collapsed') or ('Escala de valoración · al finalizar el trimestre' if table['id']=='escala_trimestral' else 'Resultados al finalizar'),expanded=False) if table.get('collapsed') or table['id'] in ('escala_trimestral','evaluacion_final') else st.container():
                    for i,row in enumerate(table['rows']):
                        with st.container(border=True):
                            for col,c in zip(st.columns(table.get('widths') or [1]*len(row)),row):
                                with col:
                                    value=_celda(c,key+'_'+c['id'])
                                    if c['editable'] and value!=c['value']:cambios[c['id']]=value
                            if table['id'] in doc['tablas'] and table.get('delete'):
                                index=table.get('indices',list(range(len(table['rows']))))[i]
                                if index not in table.get('protected',[]) and st.checkbox('Quitar esta fila al guardar',key=key+'_retirar_'+table['id']+'_'+str(index)):
                                    retirar.setdefault(table['id'],[]).append(index)
                            elif table['id']=='escala_trimestral' and st.checkbox('Quitar este indicador al guardar',key=key+'_retirar_escala_'+str(i)):
                                retirar.setdefault('escala_trimestral',[]).append(i)
                    if table['id'] in doc['tablas'] and table.get('add'):
                        with st.expander('Añadir una fila a '+table['id'],expanded=False):
                            headers=FORMATOS[doc['formato']]['tablas'][table['id']]
                            nuevas[table['id']]={}
                            for col,h in zip(st.columns(len(headers)),headers):
                                with col:nuevas[table['id']][h]=st.text_area(h,key=key+'_nuevo_'+table['id']+'_'+h)
            with st.expander('Evaluación, observaciones y acuerdos complementarios',expanded=False):
                for c in spec['textos']:
                    value=_celda(c,key+'_'+c['id'])
                    if c['editable'] and value!=c['value']:cambios[c['id']]=value
                if doc['metadatos'].get('modalidad_planeacion')=='individual':
                    alumno_extra=st.selectbox('Añadir indicador de valoración para',
                        ['']+[a['ID_Alumno'] for a in doc['datos']['Alumnos']],
                        format_func=lambda i:next((a['Nombre del alumno'] for a in doc['datos']['Alumnos'] if a['ID_Alumno']==i),'No añadir'),key=key+'_escala_alumno')
                    indicador_extra=st.text_area('Nuevo indicador de logro (opcional)',key=key+'_escala_indicador')
                else:alumno_extra=indicador_extra=''
            config,referentes,actualizar_fuentes=_conexiones(doc,key)
            with st.expander('Ayuda para completar el formato · opcional',expanded=False):
                opciones=['Solo guardar','Completar apartados vacíos con mis datos','Proponer actividades sin IA']
                if doc['formato'] in ('XXIII','XXV'):opciones.append('Proponer actividades con IA')
                opciones.append('Guardar y enviar a Dirección')
                elegida='Proponer actividades sin IA' if preview and preview.get('tipo')=='local' else 'Proponer actividades con IA' if preview else 'Solo guardar'
                accion=st.selectbox('Al guardar quiero',opciones,index=opciones.index(elegida),key=key+'_accion')
                st.caption('Si eliges IA, primero verás el resumen educativo. No se envían archivos originales ni el padrón. Si falla, podrás seguir planeando.')
                if preview and preview.get('tipo')=='local':
                    for p in preview['propuestas']:
                        st.text(p['actividad']);st.caption(p['orientacion']);st.caption('Recursos: '+p['recursos'])
                elif preview:
                    st.text(preview['resumen'])
                    st.caption('Evidencias: '+', '.join(preview['evidencias']))
                label='Revisé las propuestas locales y autorizo incorporarlas a mi formato' if preview and preview.get('tipo')=='local' else 'Revisé este resumen y autorizo enviarlo sin datos que identifiquen personas'
                consent=st.checkbox(label,disabled=not preview,key=key+'_consent')
            st.caption(spec['firma']+' · '+spec['vobo']+' (sin firmas automáticas)')
        guardar=st.form_submit_button('Guardar Planeación',type='primary',use_container_width=True)
    if guardar:
        try:
            current=flujo.capturar(doc,spec,cambios,nuevas,retirar)
            st.session_state[prefix+'_doc']=current;st.session_state[prefix+'_pending']=True
            if alumno_extra and indicador_extra.strip():
                from services.planeacion_evaluacion import cambiar_fila,editar,filas
                current=cambiar_fila(current,alumno=alumno_extra)
                current=editar(current,len(filas(current))-1,'Indicador de logro',indicador_extra)
            from services.curriculo import vincular
            campos,ejes,ids,contexto=referentes
            if campos:current=vincular(current,campos,ejes,ids,contexto)
            elif current['metadatos'].get('curriculo'):
                current['metadatos'].pop('curriculo')
            current['metadatos']['configuracion_generacion']=config
            # Proteger la captura antes de cualquier llamada opcional o validación.
            st.session_state[prefix+'_doc']=current;st.session_state[prefix+'_pending']=True
            preview_next=None;notice=None;aviso_fuentes=''
            if actualizar_fuentes:
                try:
                    s.refrescar_evidencias();current=s.preparar_contexto(current)
                except Exception:aviso_fuentes='No se confirmó la actualización del expediente. Se conservaron los antecedentes anteriores. '
            try:current,preview_next,notice=_asistencia(current,accion,config,preview,consent)
            except Exception:
                notice='No se pudo completar la ayuda opcional. Tu edición se conserva; puedes continuar sin IA.'
            st.session_state[prefix+'_doc']=current
            estado='ENVIADO' if accion=='Guardar y enviar a Dirección' else 'BORRADOR'
            if u._persist(prefix,estado):
                st.session_state[prefix+'_captura_preview']=preview_next
                st.session_state[prefix+'_captura_generation']=generation+1
                st.session_state[prefix+'_captura_aviso']=aviso_fuentes+(notice or 'Planeación guardada. Puedes seguir editando.')
                st.toast('Planeación guardada');st.rerun()
            else:st.warning('No se confirmó el guardado. Tu captura enviada permanece en esta sesión; vuelve a pulsar Guardar Planeación.')
        except (ValueError,PermissionError,RuntimeError) as exc:st.warning(str(exc))
    with st.expander('Descargas, expediente y navegación',expanded=False):
        st.caption('Las descargas corresponden al último envío del formulario. Guarda antes de descargar o regresar.')
        from documents.planeacion_papel import generar_pdf
        snapshot=st.session_state[prefix+'_doc']
        st.download_button('Descargar respaldo editable',json.dumps(snapshot,ensure_ascii=False,indent=2),file_name='planeacion-'+doc['id']+'.json',mime='application/json',key=prefix+'_captura_respaldo')
        try:
            pdf=u._pdf_sesion(prefix,snapshot,provider=generar_pdf)
            st.download_button('Descargar PDF',pdf,file_name='planeacion-'+doc['id']+'.pdf',mime='application/pdf',key=prefix+'_captura_pdf')
            from ui.archivo_expediente import boton
            boton([a['ID_Alumno'] for a in snapshot['datos']['Alumnos']],'Plan de intervención' if doc['formato']=='XXI' else 'Planeación del servicio',pdf,'planeacion-'+doc['id']+'.pdf',prefix+'_captura_archivo',doc['id'],doc['datos']['Curso escolar'],disabled=bool(st.session_state.get(prefix+'_pending')))
        except Exception:st.caption('La descarga PDF no está disponible ahora. Tu captura se conserva.')
        if st.button('Regresar al inicio del módulo',key=prefix+'_captura_volver',disabled=bool(st.session_state.get(prefix+'_pending'))):
            if volver:volver()
            else:st.session_state[prefix.rsplit('_',1)[0]+'_viva_entrada']=True
            st.rerun()

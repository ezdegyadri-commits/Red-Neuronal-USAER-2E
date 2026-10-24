"""Una captura, sobre la hoja tradicional, y un solo envío explícito al final."""
import json
import streamlit as st
from ui.planeacion_pendientes import raiz
from services import planeacion as s, planeacion_papel as papel
from services import planeacion_cero_friccion as flujo
from services.planeacion_modelo import FORMATOS


def _celda(c, key):
    if not c['editable']:
        st.markdown(
            f"<div style='background:#f8fafc; padding:8px 10px; border-radius:6px; border:1px solid #e2e8f0; font-size:0.88rem; min-height:42px; color:#334155; line-height:1.4;'>{c['value'] or '—'}</div>",
            unsafe_allow_html=True,
        )
        return c['value']
    if c.get('opciones'):
        opciones = c['opciones']
        value = c['value'] if c['value'] in opciones else opciones[0]
        return st.selectbox(c['label'], opciones, index=opciones.index(value), key=key)
    if c.get('tipo')=='fecha':
        from datetime import date
        valor=st.date_input(c['label'],value=date.fromisoformat(c['fecha_iso']) if c['fecha_iso'] else None,format='DD/MM/YYYY',key=key)
        return valor.strftime('%d/%m/%Y') if valor else c['value']
    if c.get('nota'):
        st.caption('💡 ' + c['nota'])
    label_lower = c['label'].lower()
    h = 115 if any(k in label_lower for k in ['actividad', 'aprendizaje', 'apoyo', 'ajuste', 'barrera']) else 85
    value=st.text_area(c['label'], value=c['value'], height=h, key=key)
    if c.get('sugerencias_nee'):
        opciones=c['sugerencias_nee']
        chosen=st.selectbox('Añadir NEE vinculada a EPP',range(-1,len(opciones)),format_func=lambda i:'No añadir' if i<0 else opciones[i]['texto']+' · '+opciones[i]['referencia'],key=key+'_nee_epp')
        if chosen>=0 and opciones[chosen]['texto'] not in value.splitlines():value=(value+'\n'+opciones[chosen]['texto']).strip()
    return value


def _conexiones(doc, key):
    from services import curriculo as cur, planeacion_generacion as g
    config = {**g.configuracion(doc), **doc['metadatos'].get('configuracion_generacion', {})}
    old = doc['metadatos'].get('curriculo', {})
    with st.expander('Expediente, referentes oficiales y apoyos DUA', expanded=False):
        st.markdown("""
        <div style="background: #f0fdf4; border-left: 4px solid #16a34a; padding: 10px 14px; border-radius: 6px; margin-bottom: 14px;">
            <div style="font-weight: 600; font-size: 0.9rem; color: #166534;">Vinculación con Expediente del Alumno, Catálogo Oficial NEM y DUA</div>
            <div style="font-size: 0.8rem; color: #15803d; margin-top: 2px;">
                La información seleccionada alimenta los objetivos y secuencias de actividades. Se conservan las fuentes conectadas por alumno.
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.caption('Se conservan las fuentes conectadas por alumno. Una BAP del contexto no equivale a una NEE.')
        from services.planeacion_generacion import fuentes_pertinentes
        for fuente in fuentes_pertinentes(doc):
            with st.expander(str(fuente.get('referencia', 'Antecedente')) + ' · ' + str(fuente.get('fecha', ''))):
                st.text(fuente.get('texto', ''))
        actualizar = st.checkbox('Actualizar antecedentes del expediente al guardar', key=key+'_actualizar_fuentes')
        
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            campos = st.multiselect('Campos formativos', list(cur.CAMPOS), default=cur.campos_seleccionados(old), key=key+'_campos')
        with col_c2:
            ejes = st.multiselect('Ejes articuladores', list(cur.EJES), default=old.get('ejes', []), key=key+'_ejes')
            
        catalogo = cur.catalogo()['registros']
        porid = {r['id']: r for r in catalogo}
        ids = st.multiselect(
            'Contenidos y PDA · busca por grado, campo o palabras',
            list(porid),
            default=[r['id'] for r in old.get('registros', []) if r['id'] in porid],
            max_selections=6,
            format_func=lambda i: f"{porid[i]['grado']}° · {porid[i]['campo']} · {porid[i]['contenido']} · {porid[i]['pda']}",
            key=key+'_pda'
        )
        for i in ids:
            r = porid[i]
            st.caption(r['fuente'] + ' · página PDF ' + str(r['pagina_pdf']))
        st.caption('El campo de cada PDA elegido se conecta automáticamente; no tienes que seleccionarlo de nuevo.')
        campos = list(dict.fromkeys(campos + [porid[i]['campo'] for i in ids]))
        
        contexto = st.text_area('Contextualización de la escuela', value=old.get('contexto_local', ''), key=key+'_contexto')
        apoyos = st.text_area('Apoyos DUA y ajustes para participar, comprender y expresarse', value=config.get('apoyos', ''), key=key+'_dua')
        enfoque = st.text_area('Prioridad de la intervención (opcional)', value=config.get('enfoque', ''), key=key+'_enfoque')
        st.caption('Las adaptaciones docentes previas siguen vinculadas al PDA. No se cambia el texto oficial del catálogo.')
    return {**config, 'apoyos': apoyos, 'enfoque': enfoque}, (campos, ejes, ids, contexto), actualizar


def _asistencia(doc, accion, config, preview, consent):
    """Nunca envía a IA información diferente de la vista previa consentida."""
    from services import planeacion_generacion as g
    if accion in ('Solo guardar', 'Guardar y enviar a Dirección'):
        return doc, None, None
    if accion == 'Completar apartados vacíos con mis datos':
        from services.planeacion_apartados import proponer
        return proponer(doc), None, 'Se completaron solo los apartados con sustento disponible. Revisa las propuestas en tu hoja.'
    if accion == 'Proponer actividades sin IA':
        from services import planeacion_local as local
        propuesta = local.preparar(doc, config.get('enfoque', ''))
        if consent and preview and preview.get('tipo') == 'local' and preview['propuestas'] == propuesta['propuestas']:
            return local.aplicar(doc, propuesta, [r['id'] for r in propuesta['propuestas']]), None, 'Las propuestas revisadas se añadieron a Actividades. Puedes editarlas o eliminarlas.'
        return doc, {'tipo': 'local', **propuesta}, 'Revisa las propuestas sin IA y confírmalas con el mismo botón Guardar Planeación.'
    if doc['formato'] not in ('XXIII', 'XXV'):
        raise ValueError('La propuesta completa se prepara en el formato trimestral XXIII o XXV.')
    solicitud = g.preparar_solicitud(doc, config)
    if not consent or not preview or preview['huella'] != solicitud['huella']:
        return doc, solicitud, 'Tu edición se guardará. Revisa el resumen de IA y confirma su envío con el mismo botón Guardar Planeación.'
    from ai.planeacion import modelo_configurado
    from ui.planeacion_progreso import generar
    respuesta = generar(solicitud,doc)
    if not respuesta['unidades']:
        return doc, None, 'La IA no produjo actividades sustentadas. Tu edición se conserva y puedes continuar sin IA.'
    result = g.ensamblar(doc, respuesta, solicitud)
    result['metadatos']['generacion_completa']['motor'] = modelo_configurado()
    return result, None, 'Las actividades propuestas ya están en Organización de las actividades de aprendizaje. Todo queda editable.'


def hoja(prefix, volver=None):
    from ui import planeacion as u
    doc = st.session_state[prefix+'_doc']
    s.autorizar(doc, True)
    if not flujo.aplica(doc):
        raise PermissionError('Continúa este documento en la hoja grupal compartida.')
    spec = papel.hoja(doc)
    generation = st.session_state.get(prefix+'_captura_generation', 0)
    key = f'{prefix}_{doc["id"]}_captura_{generation}'
    if aviso := st.session_state.pop(prefix+'_captura_aviso', None):
        st.success(aviso)
    if error := st.session_state.get(prefix+'_error'):
        st.warning(error)
        
    st.caption('Edita sobre tu formato. Los cambios se envían juntos al pulsar Guardar Planeación; no se guardan campo por campo. Guarda antes de cambiar de pantalla o cerrar la sesión.')
    if doc.get('guardado_en'):
        st.caption('Último guardado confirmado: ' + doc['guardado_en'][:19].replace('T', ' '))
        
    cambios = {}
    nuevas = {}
    retirar = {}
    preview = st.session_state.get(prefix+'_captura_preview')
    
    st.html(f"""
    <style>
    .st-key-{key}_hoja {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        background: #ffffff;
        color: #0f172a;
        border-radius: 14px;
        box-shadow: 0 4px 20px -2px rgba(15, 23, 42, 0.08);
        padding: 10px 6px;
    }}
    .st-key-{key}_hoja textarea {{
        font-family: inherit;
        font-size: 0.88rem;
        line-height: 1.45;
        border-radius: 8px;
    }}
    .meta-box-item {{
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 8px 12px;
        margin-bottom: 6px;
    }}
    .meta-label-item {{
        font-size: 0.72rem;
        text-transform: uppercase;
        color: #64748b;
        font-weight: 600;
        letter-spacing: 0.03em;
    }}
    .meta-val-item {{
        font-size: 0.88rem;
        color: #0f172a;
        font-weight: 600;
        margin-top: 1px;
    }}
    .th-table-header {{
        background: #f1f5f9;
        border-top: 2px solid #0f766e;
        border-bottom: 1px solid #cbd5e1;
        padding: 8px 6px;
        font-weight: 600;
        font-size: 0.82rem;
        color: #0f766e;
        text-align: center;
        border-radius: 4px 4px 0 0;
    }}
    </style>
    """)
    
    with st.form(key+'_form', clear_on_submit=False):
        with st.container(border=True, key=key+'_hoja'):
            # Membrete Oficial Institucional
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #042f2e 0%, #0f766e 100%); color: white; padding: 18px 24px; border-radius: 10px; margin-bottom: 16px; box-shadow: 0 4px 12px rgba(15, 118, 110, 0.15);">
                <div style="font-size: 0.72rem; letter-spacing: 0.08em; text-transform: uppercase; opacity: 0.85; font-weight: 600;">
                    Secretaría de Educación de Yucatán · Dirección de Educación Especial · USAER 02E
                </div>
                <div style="font-size: 1.3rem; font-weight: 700; margin-top: 4px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
                    {spec['titulo']}
                </div>
                <div style="font-size: 0.82rem; opacity: 0.9; margin-top: 4px;">
                    Formato Oficial · Ciclo Escolar {doc['datos'].get('Curso escolar', '')} · {doc['datos'].get('Trimestre', '')}º Trimestre
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Cuadrícula institucional de datos administrativos
            for row in spec['header']:
                cols = st.columns(len(row))
                for col, val in zip(cols, row):
                    raw_text = val if isinstance(val, str) else val.get('value', '')
                    parts = raw_text.split(':', 1)
                    lbl = parts[0].strip() if len(parts) > 1 else ''
                    val_text = parts[1].strip() if len(parts) > 1 else raw_text
                    with col:
                        st.markdown(f"""
                        <div class="meta-box-item">
                            <div class="meta-label-item">{lbl}</div>
                            <div class="meta-val-item">{val_text}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
            # Tablas Oficiales en Formato Vivo
            for table in spec['tables']:
                if table['title']:
                    st.markdown(f"""
                    <div style="margin-top: 22px; margin-bottom: 8px; border-left: 4px solid #0f766e; padding-left: 10px;">
                        <h4 style="margin: 0; color: #0f172a; font-size: 1.05rem; font-weight: 700;">{table['title']}</h4>
                    </div>
                    """, unsafe_allow_html=True)
                
                is_collapsible = table.get('collapsed') or table['id'] in ('escala_trimestral', 'evaluacion_final')
                exp_title = table.get('collapsed') or ('Escala de valoración · al finalizar el trimestre' if table['id'] == 'escala_trimestral' else 'Resultados al finalizar')
                
                table_ctx = st.expander(exp_title, expanded=False) if is_collapsible else st.container()
                with table_ctx:
                    # Encabezados de columna estilizados
                    if table.get('headers') and table['rows']:
                        col_widths = table.get('widths') or [1] * len(table['headers'])
                        h_cols = st.columns(col_widths)
                        for c_head, h_text in zip(h_cols, table['headers']):
                            c_head.markdown(f"""
                            <div class="th-table-header">
                                {h_text}
                            </div>
                            """, unsafe_allow_html=True)
                            
                    # Filas editables
                    for i, row in enumerate(table['rows']):
                        with st.container():
                            cols = st.columns(table.get('widths') or [1] * len(row))
                            for col, c in zip(cols, row):
                                with col:
                                    value = _celda(c, key + '_' + c['id'])
                                    if c['editable'] and value != c['value']:
                                        cambios[c['id']] = value
                            
                            # Opciones discretas para quitar fila
                            if table['id'] in doc['tablas'] and table.get('delete'):
                                index = table.get('indices', list(range(len(table['rows']))))[i]
                                if index not in table.get('protected', []):
                                    col_del, _ = st.columns([3, 4])
                                    with col_del:
                                        if st.checkbox('Quitar esta fila al guardar', key=key+'_retirar_'+table['id']+'_'+str(index)):
                                            retirar.setdefault(table['id'], []).append(index)
                            elif table['id'] == 'escala_trimestral':
                                col_del, _ = st.columns([3, 4])
                                with col_del:
                                    if st.checkbox('Quitar este indicador al guardar', key=key+'_retirar_escala_'+str(i)):
                                        retirar.setdefault('escala_trimestral', []).append(i)
                                        
                    # Añadir nueva fila
                    if table['id'] in doc['tablas'] and table.get('add'):
                        with st.expander('➕ Añadir una fila a ' + table['id'], expanded=False):
                            headers = FORMATOS[doc['formato']]['tablas'][table['id']]
                            nuevas[table['id']] = {}
                            for col, h in zip(st.columns(len(headers)), headers):
                                with col:
                                    nuevas[table['id']][h] = st.text_area(h, key=key+'_nuevo_'+table['id']+'_'+h, height=80)
                                    
            # Evaluaciones complementarias
            with st.expander('Evaluación, observaciones y acuerdos complementarios', expanded=False):
                for c in spec['textos']:
                    value = _celda(c, key + '_' + c['id'])
                    if c['editable'] and value != c['value']:
                        cambios[c['id']] = value
                if doc['metadatos'].get('modalidad_planeacion') == 'individual':
                    alumno_extra = st.selectbox(
                        'Añadir indicador de valoración para',
                        [''] + [a['ID_Alumno'] for a in doc['datos']['Alumnos']],
                        format_func=lambda i: next((a['Nombre del alumno'] for a in doc['datos']['Alumnos'] if a['ID_Alumno'] == i), 'No añadir'),
                        key=key+'_escala_alumno',
                    )
                    indicador_extra = st.text_area('Nuevo indicador de logro (opcional)', key=key+'_escala_indicador', height=75)
                else:
                    alumno_extra = indicador_extra = ''
                    
            # Conexión con Expediente, PDA y DUA
            config, referentes, actualizar_fuentes = _conexiones(doc, key)
            
            # Asistente Inteligente y Opciones de Guardado
            with st.expander('Ayuda para completar el formato · opcional', expanded=bool(preview)):
                st.markdown("""
                <div style="background: #f8fafc; border-left: 4px solid #0f766e; padding: 10px 14px; border-radius: 6px; margin-bottom: 12px;">
                    <div style="font-weight: 600; font-size: 0.9rem; color: #0f766e;">Asistente Pedagógico y Acciones de Envío</div>
                    <div style="font-size: 0.8rem; color: #475569; margin-top: 2px;">
                        Elige si deseas guardar tu captura tal como está, autocompletar con base en el diagnóstico, o generar propuestas contextualizadas con DUA.
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                opciones = ['Solo guardar', 'Completar apartados vacíos con mis datos', 'Proponer actividades sin IA']
                if doc['formato'] in ('XXIII', 'XXV'):
                    opciones.append('Proponer actividades con IA')
                opciones.append('Guardar y enviar a Dirección')
                elegida = 'Proponer actividades sin IA' if preview and preview.get('tipo') == 'local' else 'Proponer actividades con IA' if preview else 'Solo guardar'
                accion = st.selectbox('Al guardar quiero', opciones, index=opciones.index(elegida), key=key+'_accion')
                st.caption('Si eliges IA, primero verás el resumen educativo. No se envían archivos originales ni el padrón. Si falla, podrás seguir planeando.')
                
                if preview and preview.get('tipo') == 'local':
                    st.markdown("<div style='background:#f0fdf4; border:1px solid #bbf7d0; border-radius:8px; padding:12px; margin:10px 0;'>", unsafe_allow_html=True)
                    st.markdown("<strong style='color:#166534;'>Propuestas locales preparadas para incorporar:</strong>", unsafe_allow_html=True)
                    for p in preview['propuestas']:
                        st.markdown(f"**Actividad:** {p['actividad']}")
                        st.caption(f"Orientación: {p['orientacion']} · Recursos: {p['recursos']}")
                    st.markdown("</div>", unsafe_allow_html=True)
                elif preview:
                    st.markdown("<div style='background:#f0fdfa; border:1px solid #99f6e4; border-radius:8px; padding:12px; margin:10px 0;'>", unsafe_allow_html=True)
                    st.markdown("<strong style='color:#0f766e;'>Resumen pedagógico para generación con IA:</strong>", unsafe_allow_html=True)
                    st.text(preview['resumen'])
                    st.caption('Evidencias: ' + ', '.join(preview['evidencias']))
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                label = 'Revisé las propuestas locales y autorizo incorporarlas a mi formato' if preview and preview.get('tipo') == 'local' else 'Revisé este resumen y autorizo enviarlo sin datos que identifiquen personas'
                consent = st.checkbox(label, disabled=not preview, key=key+'_consent')
                
            # Firmas institucionales
            st.markdown(f"""
            <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 16px; margin-top: 14px; font-size: 0.85rem; color: #475569;">
                <strong>Elaboró:</strong> {spec['firma']} &nbsp;·&nbsp; <strong>Vo.Bo.:</strong> {spec['vobo']} <span style="opacity: 0.7;">(sin firmas automáticas)</span>
            </div>
            """, unsafe_allow_html=True)
            
        st.markdown("<div style='margin-top: 14px;'></div>", unsafe_allow_html=True)
        guardar = st.form_submit_button('Guardar Planeación', type='primary', use_container_width=True)
        migrar = st.form_submit_button('Guardar y abrir la hoja de edición directa', use_container_width=True)
        guardar = guardar or migrar
        if migrar:accion = 'Solo guardar'
        
    if guardar:
        try:
            current = flujo.capturar(doc, spec, cambios, nuevas, retirar)
            st.session_state[prefix+'_doc'] = current
            st.session_state[prefix+'_pending'] = True
            if alumno_extra and indicador_extra.strip():
                from services.planeacion_evaluacion import cambiar_fila, editar, filas
                current = cambiar_fila(current, alumno=alumno_extra)
                current = editar(current, len(filas(current)) - 1, 'Indicador de logro', indicador_extra)
            from services.curriculo import vincular
            campos, ejes, ids, contexto = referentes
            if campos:
                current = vincular(current, campos, ejes, ids, contexto)
            elif current['metadatos'].get('curriculo'):
                current['metadatos'].pop('curriculo')
            current['metadatos']['configuracion_generacion'] = config
            st.session_state[prefix+'_doc'] = current
            st.session_state[prefix+'_pending'] = True
            preview_next = None
            notice = None
            aviso_fuentes = ''
            if actualizar_fuentes:
                try:
                    s.refrescar_evidencias()
                    current = s.preparar_contexto(current)
                except Exception:
                    aviso_fuentes = 'No se confirmó la actualización del expediente. Se conservaron los antecedentes anteriores. '
            try:
                current, preview_next, notice = _asistencia(current, accion, config, preview, consent)
            except Exception as exc:
                from ui.planeacion_progreso import mensaje_error
                notice = mensaje_error(exc)
            st.session_state[prefix+'_doc'] = current
            estado = 'ENVIADO' if accion == 'Guardar y enviar a Dirección' else 'BORRADOR'
            if u._persist(prefix, estado):
                if migrar:st.session_state[prefix+'_editor_directo']=True
                st.session_state[prefix+'_captura_preview'] = preview_next
                st.session_state[prefix+'_captura_generation'] = generation + 1
                st.session_state[prefix+'_captura_aviso'] = aviso_fuentes + (notice or 'Planeación guardada. Puedes seguir editando.')
                st.toast('Planeación guardada')
                st.rerun()
            else:
                st.warning('No se confirmó el guardado. Tu captura enviada permanece en esta sesión; vuelve a pulsar Guardar Planeación.')
        except (ValueError, PermissionError, RuntimeError) as exc:
            st.warning(str(exc))
            
    with st.expander('Descargas, expediente y navegación', expanded=False):
        st.caption('Las descargas corresponden al último envío del formulario. Guarda antes de descargar o regresar.')
        from documents.planeacion_papel import generar_pdf
        snapshot = st.session_state[prefix+'_doc']
        c_d1, c_d2 = st.columns(2)
        with c_d1:
            st.download_button('Descargar respaldo editable', json.dumps(snapshot, ensure_ascii=False, indent=2), file_name='planeacion-'+doc['id']+'.json', mime='application/json', key=prefix+'_captura_respaldo', use_container_width=True)
        with c_d2:
            try:
                pdf = u._pdf_sesion(prefix, snapshot, provider=generar_pdf)
                st.download_button('Descargar PDF', pdf, file_name='planeacion-'+doc['id']+'.pdf', mime='application/pdf', key=prefix+'_captura_pdf', use_container_width=True)
                from ui.archivo_expediente import boton
                boton([a['ID_Alumno'] for a in snapshot['datos']['Alumnos']], 'Plan de intervención' if doc['formato'] == 'XXI' else 'Planeación del servicio', pdf, 'planeacion-'+doc['id']+'.pdf', prefix+'_captura_archivo', doc['id'], doc['datos']['Curso escolar'], disabled=bool(st.session_state.get(prefix+'_pending')))
            except Exception:
                st.caption('La descarga PDF no está disponible ahora. Tu captura se conserva.')
        if st.button('Regresar al inicio del módulo', key=prefix+'_captura_volver', use_container_width=True):
            if volver:
                volver()
            else:
                st.session_state[raiz(prefix)+'_viva_entrada'] = True
            st.rerun()

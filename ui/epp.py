"""Formato Vivo Minimalista para la Evaluación Psicopedagógica (EPP).

Permite trabajar directamente sobre el informe oficial (Anexos XVII y XVIII del Manual USAER):
- Carga o registro ágil de pruebas (escaneos OCR o entrada directa del catálogo normativo SEGEY).
- Distribución automática de hallazgos en los campos correspondientes.
- Propuesta automática de NEE con fórmula oficial SEGEY: [Necesita + verbo observable + contenido].
- Edición y vaciado inmediato de cualquier campo propuesto sobre el formato vivo.
"""
from copy import deepcopy
import hashlib
import json
import pandas as pd
import streamlit as st
from services import epp as s
from services.epp_modelo import (
    AREAS, SECCIONES, campos, vacia, NEE, BAP, FAMILIA, HISTORIA, GENERALES, pendientes, conclusion_vigente
)
from services.materiales_planeacion import TIPOS, leer_material
from documents.epp import generar_pdf
from ai.epp import generar
from services.epp_entrada import precargar, huella_instrumentos, entrada_directa
from services.epp_analisis import (
    identificar_instrumento_y_areas, distribuir_hallazgos_en_epp, proponer_nee_segey, incorporar_prueba_a_epp,
    ensamblar_epp_completa_desde_documento
)

CATALOGO_INSTRUMENTOS_SEGEY = {
    'Psicología': [
        'Escala Wechsler de Inteligencia para Niños (WISC-IV)',
        'Evaluación Neuropsicológica Infantil (ENI)',
        'Test de Matrices Progresivas Raven (Escala Coloreada)',
        'Test de Matrices Progresivas Raven (Escala General)',
        'Prueba Visomotora Bender',
        'Test de la Figura Compleja (Rey)',
        'Test de Desarrollo de la Percepción Visual (Frostig)',
        'Dibujo de la Figura Humana (DFH)',
        'Test CREA (Inteligencia Creativa - para Aptitudes Sobresalientes)',
        'Baterías de Socialización (BAS 1, 2 y 3)',
        'Evaluación de la Conducta Adaptativa (ABAS-II)',
        'Escala de Maduración Social de Vineland',
        'Escala Vanderbilt / Conners (para indicadores de TDAH)'
    ],
    'Comunicación': [
        'Evaluación cualitativa del lenguaje (Flores)',
        'Evaluación de la articulación de sonidos del habla (Laiz)',
        'Evaluación de la comunicación y el lenguaje (SEGEY, 2014)',
        'Matriz de Comunicación / Mapa comunicativo (Bove & Perkins)',
        'Inventario de dificultades auditivas en el hogar (CHILD)',
        'Test SIFTER de detección de riesgo educativo'
    ],
    'Trabajo Social': [
        'Estudio Social (Anexo XII)',
        'Cuestionario de Identificación de BAP Sociofamiliar (Anexo XI)',
        'Entrevista a Padres de Familia (Anexo Xa)',
        'Constancia de Visita Domiciliaria (Anexo XXX)',
        'Constancia de Visita Institucional (Anexo XXIX)'
    ],
    'Aprendizaje': [
        'Evaluación de competencia curricular por grado escolar',
        'Estilo de Aprendizaje y Motivación para Aprender (Anexo XIV)',
        'Estilo de Enseñanza del docente regular (Anexo XIII)',
        'Entrevista al Alumno (Anexo X)',
        'Inventario de Habilidades Básicas (Macotela & Romay)',
        'Evaluación de lectura y matemáticas funcionales'
    ]
}

# Formato de observación disponible en el propio manual; no añade baremos.
CATALOGO_INSTRUMENTOS_SEGEY['Psicología'].append('Guía para la Observación de la Autodirección (Anexo XVI)')


def _guardar_aplicacion(prefix,value,manual):
    st.session_state[prefix+'_value']=deepcopy(value)
    st.session_state[prefix+'_pending']=True
    if manual:_save(prefix)
    return not st.session_state.get(prefix+'_pending')


def _save(prefix):
    """Guarda el apartado en curso en el repositorio canónico."""
    try:
        doc=st.session_state[prefix+'_doc'];area=st.session_state[prefix+'_area']
        value=st.session_state[prefix+'_value'];revision=doc['partes'].get(area,{}).get('revision','')
        if value.get('validada'):
            saved=s.guardar(doc,area,value,revision)
        else:
            base=doc['partes'].get(area,{}).get('contenido',vacia(area))
            saved=s.guardar_cambios(doc,area,base,value,revision)
        doc['partes'][area]=saved
        st.session_state[prefix+'_value']=deepcopy(saved['contenido'])
        st.session_state.pop(prefix+'_error',None)
        st.session_state[prefix+'_pending']=False
        st.session_state[prefix+'_saved']=saved['fecha']
    except Exception as exc:
        st.session_state[prefix+'_pending']=True
        st.session_state[prefix+'_error']=str(exc) if isinstance(exc,(ValueError,PermissionError,RuntimeError)) else 'No se confirmó el guardado. Tu texto sigue en esta sesión: descarga el respaldo y vuelve a intentar.'


def _field(prefix, key, section, field):
    """Actualiza un campo específico del apartado activo y guarda."""
    value = st.session_state[prefix + '_value']
    if section:
        value.setdefault(section, {})[field] = st.session_state[key]
    else:
        value[field] = st.session_state[key]
    if section == 'generales':
        value['generales_editados'] = sorted(set(value.get('generales_editados', [])) | {field})
    if field != 'validada':
        value['validada'] = False
    _save(prefix)


def _clear_field(prefix, field, section=None):
    """Vacía inmediatamente un campo propuesto y persiste el cambio."""
    value = st.session_state[prefix + '_value']
    if section:
        value.setdefault(section, {})[field] = ''
    else:
        value[field] = ''
    key = prefix + '_field_' + (section or '') + field
    if key in st.session_state:
        st.session_state[key] = ''
    value['validada'] = False
    _save(prefix)
    st.rerun()


def _table(prefix, key, name, base):
    """Actualiza una tabla de datos interactiva (NEE, BAP, Familia, Historia)."""
    rows = deepcopy(base)
    edits = st.session_state.get(key, {})
    for n, updates in edits.get('edited_rows', {}).items():
        rows[int(n)].update(updates)
    rows = [r for i, r in enumerate(rows) if i not in edits.get('deleted_rows', [])]
    rows.extend(edits.get('added_rows', []))
    st.session_state[prefix + '_value'][name] = rows
    st.session_state[prefix + '_value']['validada'] = False
    _save(prefix)


def _grid(prefix, name, headers):
    """Renderiza el editor interactivo de tabla."""
    base = deepcopy(st.session_state[prefix + '_value'].get(name, []))
    key = prefix + '_table_' + name
    basekey = key + '_base'
    if basekey not in st.session_state:
        st.session_state[basekey] = base
    st.data_editor(
        pd.DataFrame(st.session_state[basekey], columns=headers).fillna(''),
        num_rows='dynamic',
        hide_index=True,
        use_container_width=True,
        key=key,
        on_change=_table,
        args=(prefix, key, name, st.session_state[basekey])
    )


def _abrir(prefix, doc, area):
    """Carga en session_state el apartado especificado con sus datos."""
    for k in list(st.session_state):
        if k.startswith(prefix + '_field_') or k.startswith(prefix + '_table_'):
            del st.session_state[k]
    st.session_state[prefix + '_doc'] = deepcopy(doc)
    st.session_state[prefix + '_area'] = area
    st.session_state[prefix + '_value'] = deepcopy(doc['partes'].get(area, {}).get('contenido', vacia(area)))
    if area == 'Aprendizaje':
        original = st.session_state[prefix + '_value']
        filled = precargar(original, s.alumno_autorizado(doc['alumno']))
        st.session_state[prefix + '_value'] = filled
        if filled != original:
            _save(prefix)



def _text(prefix, field, section=None, height=100):
    key = prefix + '_field_' + (section or '') + field
    value = st.session_state[prefix + '_value']
    text = value.get(section, {}).get(field, '') if section else value.get(field, '')
    labels = {'instrumentos': 'Instrumentos aplicados por mi área', 'fecha_aplicacion': 'Fecha(s) de aplicación',
              'sintesis': 'Síntesis de mi área y aspectos por confirmar'}
    st.text_area(labels.get(field, field), value=text, key=key, height=height, on_change=_field, args=(prefix, key, section, field))


def _render_field(doc, actor_area, can_edit_concl, is_director, target_area, field_name, section=None, height=95, prefix=''):
    """Renderiza un campo en el Formato Vivo:
    - Editable directamente si el usuario pertenece al área (o coordinadora en Conclusión / Director).
    - Vista colaborativa de lectura en vivo si pertenece a otra área.
    """
    is_editable = not is_director and ((target_area == actor_area) or (target_area == 'Conclusión' and can_edit_concl))
    
    if is_editable:
        edit_prefix = prefix + '_edit_' + doc['id'] + '_' + target_area
        if edit_prefix + '_doc' not in st.session_state:
            _abrir(edit_prefix, doc, target_area)

        value = st.session_state[edit_prefix + '_value']
        current_text = value.get(section, {}).get(field_name, '') if section else value.get(field_name, '')
        key = edit_prefix + '_field_' + (section or '') + field_name

        if current_text and str(current_text).strip():
            c_lbl, c_clr = st.columns([0.84, 0.16])
            with c_lbl:
                st.markdown(f"**{field_name}**")
            with c_clr:
                if st.button("🗑️ Vaciar", key=f"clr_{key}", help=f"Eliminar texto propuesto de {field_name}"):
                    _clear_field(edit_prefix, field_name, section)
        else:
            st.markdown(f"**{field_name}**")

        st.text_area(
            label=field_name,
            value=current_text,
            key=key,
            height=height,
            label_visibility="collapsed",
            on_change=_field,
            args=(edit_prefix, key, section, field_name),
            placeholder=f"Observaciones y hallazgos documentados para {field_name}..."
        )
    else:
        part = doc.get('partes', {}).get(target_area, {})
        cont = part.get('contenido', {})
        text = cont.get(section, {}).get(field_name, '') if section else cont.get('campos', {}).get(field_name, '')
        author = part.get('autor', target_area)
        validated = cont.get('validada', False)
        
        st.markdown(f"**{field_name}** &nbsp; <small style='color:#6c757d;'>({target_area} · {author} {'✅' if validated else '✏️'})</small>", unsafe_allow_html=True)
        if text and str(text).strip():
            st.info(text.strip())
        else:
            st.caption(f"*(Pendiente de aportar por {target_area})*")


def _pagina_papel_nativa():
    """Nuevas aperturas en el formato vivo; conservar sesiones guiadas en curso."""
    a=s.actor();prefix='epp_'+hashlib.sha256(a['cuenta'].encode()).hexdigest()[:12]
    if any(k.startswith(prefix+'_edit_') and k.endswith('_value') for k in st.session_state):
        st.caption('Se conserva tu edición guiada en curso. Las nuevas sesiones abrirán el formato vivo.')
        return _pagina_guiada()
    from ui.epp_viva import page
    return page()


def epp_page():
    a = s.actor()
    st.title('Evaluación Psicopedagógica · Formato Vivo')
    st.caption('Un solo informe vivo e interdisciplinario. Anexos XVII y XVIII del Manual USAER. Capturar una vez y reutilizar en equipo.')

    prefix = 'epp_' + hashlib.sha256(a['cuenta'].encode()).hexdigest()[:12]
    from ui.epp_programacion import panel as control_programacion
    control_programacion(prefix)

    try:
        docs = s.listar(True)
    except Exception:
        st.error('No fue posible consultar las EPP. No se modificó ningún documento.')
        return

    frame = s.planes.padron_autorizado()
    names = {str(r['ID_Alumno']): str(r['Nombre_Completo']) + ' · ' + str(r.get('Nombre_Escuela', '')) for r in frame.to_dict('records')}
    selected_key = prefix + '_selected'

    # Iniciar EPP nueva (Maestra de apoyo / Director)
    if s.puede_crear():
        with st.expander('➕ Iniciar una EPP nueva para un alumno'):
            if not frame.empty:
                labels = {str(r['ID_Alumno']): str(r['Nombre_Completo']) + ' · ' + str(r.get('Nombre_Escuela', '')) for r in frame.to_dict('records')}
                id_alumno = st.selectbox('Alumno de mi matrícula', list(labels), format_func=labels.get, key=prefix + '_nuevo_alumno')
                ciclo = st.text_input('Ciclo escolar', '2026-2027', key=prefix + '_nuevo_ciclo')
                if st.button('Crear EPP y guardar', key=prefix + '_crear'):
                    try:
                        s.crear(id_alumno, ciclo)
                        st.rerun()
                    except Exception as exc:
                        st.error(str(exc) if isinstance(exc, (ValueError, PermissionError)) else 'No se confirmó la creación.')

    if a['area'] in ('Psicología', 'Comunicación', 'Trabajo Social') and not a['director']:
        schools = {str(r['ID_Escuela']): str(r.get('Nombre_Escuela', '')) for r in frame.to_dict('records') if str(r.get('ID_Escuela', '')).strip()}
        if not schools:
            st.info('No hay escuelas asignadas disponibles para consultar EPP.')
            return
        school = st.selectbox('Escuela asignada', sorted(schools, key=lambda i: schools[i]), format_func=schools.get, key=prefix + '_escuela')
        ids = set(frame.loc[frame['ID_Escuela'].astype(str).eq(school), 'ID_Alumno'].astype(str))
        docs = [d for d in docs if d['alumno'] in ids and d['partes']['META']['estado'] != 'ELIMINADO']
        if not docs:
            st.info('Todavía no hay EPP iniciadas en esta escuela. Cuando la maestra de apoyo cree una, aparecerá aquí.')
            return
        selected_key = prefix + '_selected_escuela_' + school

    if not docs:
        st.caption('Aún no hay EPP en tus escuelas asignadas. La maestra de apoyo puede iniciar una.')
        return

    col_sel, col_ref = st.columns([0.8, 0.2])
    with col_sel:
        by_id = {d['id']: d for d in docs}
        selected = st.selectbox(
            'Alumno con EPP iniciada',
            list(by_id),
            format_func=lambda i: names.get(by_id[i]['alumno'], '') + ' · ' + by_id[i]['ciclo'] + (' · Retirado' if by_id[i]['partes']['META']['estado'] == 'ELIMINADO' else ''),
            key=selected_key
        )
    with col_ref:
        st.write("")
        if st.button('🔄 Sincronizar', key=prefix + '_refresh', help='Recargar aportaciones del equipo'):
            from data.google import clear_cache
            clear_cache(s.HOJA)
            # Una consulta del equipo no puede descartar aplicaciones o texto pendiente.
            st.rerun()

    doc = by_id[selected]
    s.autorizar(doc)

    if doc['partes']['META']['estado'] == 'ELIMINADO':
        st.warning('EPP retirada. Su historial se conserva.')
        if s.puede_crear() and doc['partes']['META']['cuenta'] == a['cuenta'] and st.button('Recuperar EPP', key=prefix + '_restore'):
            s.retirar(doc, True)
            st.rerun()
        return

    student = s.alumno_autorizado(doc['alumno'])
    is_coordinator = s.es_coordinadora(doc)
    can_edit_concl = is_coordinator or a['director']

    # --- ENCABEZADO Y PARTICIPACIÓN DEL EQUIPO ---
    st.markdown(f"## {names.get(doc['alumno'], 'Alumno')}")
    st.caption(
        f"**Grado y grupo:** {student.get('Grado', '')}° {student.get('Grupo', '')} · "
        f"**Escuela:** {student.get('Nombre_Escuela', '')} (CCT: {student.get('CCT_Escuela', '')}) · "
        f"**Condición:** {student.get('Condicion_Discapacidad', 'Por confirmar')} · "
        f"**Ciclo:** {doc['ciclo']}"
    )

    # Cinta horizontal de participación del equipo
    ribbon_cols = st.columns(5)
    icons = {'Aprendizaje': '📘', 'Psicología': '🧠', 'Comunicación': '🗣️', 'Trabajo Social': '🤝', 'Conclusión': '⚖️'}
    for idx, area_key in enumerate((*AREAS, 'Conclusión')):
        with ribbon_cols[idx]:
            parte_data = doc['partes'].get(area_key, {})
            val = parte_data.get('contenido', {}).get('validada', False)
            author = parte_data.get('autor', 'Pendiente')
            status_badge = "✅ Revisada" if val else "✏️ Borrador"
            active_style = "border: 2px solid #1f77b4; border-radius: 8px; padding: 6px;" if (area_key == a['area'] or (area_key == 'Conclusión' and can_edit_concl)) else "border: 1px solid #e0e0e0; border-radius: 8px; padding: 6px;"
            st.markdown(
                f"<div style='{active_style} text-align: center; font-size: 0.85rem;'>"
                f"<div><strong>{icons.get(area_key, '')} {area_key}</strong></div>"
                f"<div style='color: #666; font-size: 0.75rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;'>{author}</div>"
                f"<div>{status_badge}</div>"
                f"</div>",
                unsafe_allow_html=True
            )
    st.write("")

    # --- 📄 DIGITALIZADOR Y ENSAMBLADOR INTELIGENTE DE EPP COMPLETA ---
    with st.expander("📥 Subir documento escaneado de la EPP (PDF / Foto) y ensamblar en formato oficial", expanded=False):
        st.markdown(
            """
            <div style='background-color: #f7fafc; border-left: 4px solid #3182ce; padding: 10px 14px; border-radius: 6px; margin-bottom: 12px;'>
                <strong>Capturar una vez y reutilizar:</strong> Sube aquí un expediente o informe escaneado de la EPP (PDF, Word o imagen de hasta 32 MB). 
                La plataforma extraerá los hallazgos de cada disciplina, los distribuirá en sus apartados correspondientes del Manual USAER (Anexos XVII y XVIII) 
                y formulará la propuesta oficial SEGEY de NEE y BAP para validación del equipo colegiado.
            </div>
            """,
            unsafe_allow_html=True
        )
        col_up_scan, col_btn_scan = st.columns([0.68, 0.32])
        with col_up_scan:
            scan_file = st.file_uploader(
                "Documento escaneado de la EPP",
                type=['pdf', 'png', 'jpg', 'jpeg', 'webp', 'docx'],
                key=prefix + '_epp_full_scan_file',
                help="Sube un archivo PDF o imagen escaneada con la evaluación psicopedagógica del alumno."
            )
        with col_btn_scan:
            st.write("")
            st.write("")
            btn_ensamblar = st.button(
                "⚡ Leer y ensamblar en EPP",
                disabled=not scan_file,
                key=prefix + '_btn_ensamblar_scan',
                use_container_width=True
            )
        if scan_file and btn_ensamblar:
            try:
                with st.spinner("Leyendo y transcribiendo documento escaneado..."):
                    read = leer_material(scan_file.name, scan_file.getvalue())
                    texto_extraido = read.get('texto', '')
                if not texto_extraido.strip():
                    st.error("No se pudo extraer texto legible del documento cargado. Si es una imagen o escaneo, asegúrate de que sea nítido.")
                else:
                    with st.spinner("Analizando y ensamblando apartados oficiales de la EPP..."):
                        res_ens = ensamblar_epp_completa_desde_documento(doc, texto_extraido, scan_file.name)

                        # Actualizar session_state de las áreas abiertas
                        for area_k in (*AREAS, 'Conclusión'):
                            p_k = prefix + '_edit_' + doc['id'] + '_' + area_k
                            if p_k + '_value' in st.session_state:
                                st.session_state[p_k + '_value'] = deepcopy(doc['partes'][area_k]['contenido'])
                                _save(p_k)

                        # Guardar el documento completo
                        if user_work_area:
                            _save(edit_active_prefix)
                        if can_edit_concl and 'Conclusión' in doc['partes']:
                            _save(prefix + '_edit_' + doc['id'] + '_Conclusión')

                        # Invalidar caché PDF para que refleje lo nuevo
                        st.session_state.pop(prefix + '_pdf_bytes_' + doc['id'], None)

                        st.success(
                            f"✅ **EPP ensamblada exitosamente a partir de {scan_file.name}:**\n\n"
                            f"• **Áreas actualizadas:** {', '.join(res_ens['areas_ensambladas'])}\n"
                            f"• **Campos modificados:** {res_ens['campos_modificados_totales']}\n"
                            f"• **Instrumentos detectados:** {', '.join(res_ens['instrumentos_detectados']) or 'Evaluación diagnóstica'}\n"
                            f"• **Propuesta de NEE:** {res_ens['total_nee']} necesidades formuladas bajo esquema SEGEY.\n\n"
                            f"Los apartados están listos en el Formato Vivo para revisión del equipo."
                        )
                        st.rerun()
            except Exception as exc:
                st.error(f"Error al procesar el escaneo: {exc}")

    st.write("")

    # Determinar qué área edita este usuario
    user_work_area = a['area'] if a['area'] in AREAS and not a['director'] else ('Aprendizaje' if a['director'] else None)
    if is_coordinator and not user_work_area:
        user_work_area = 'Aprendizaje'

    edit_active_prefix = prefix + '_edit_' + doc['id'] + '_' + (user_work_area or 'Aprendizaje')
    if edit_active_prefix + '_doc' not in st.session_state and user_work_area:
        _abrir(edit_active_prefix, doc, user_work_area)

    # --- ⚡ CENTRO ÁGIL DE EVALUACIÓN Y PRUEBAS ---
    if user_work_area and not a['director']:
        with st.container():
            st.markdown(
                f"""
                <div style='background: linear-gradient(135deg, #f0f7ff 0%, #e6f0fa 100%); border-left: 5px solid #2b6cb0; padding: 12px 16px; border-radius: 8px; margin-bottom: 16px;'>
                    <h4 style='margin:0; color:#1a365d;'>⚡ Centro Ágil de Evaluación · {user_work_area}</h4>
                    <span style='font-size:0.85rem; color:#4a5568;'>Aplica formatos con reglas verificadas o revisa una evaluación externa. Los resultados se integran a tu área; la conclusión y NEE requieren revisión del equipo.</span>
                </div>
                """,
                unsafe_allow_html=True
            )

            tab_scan, tab_direct = st.tabs(['📷 Subir escaneo o prueba (PDF / Foto)', '✍️ Aplicar / Registrar prueba directamente'])

            with tab_scan:
                from ui.epp_instrumentos import externo
                externo(doc,user_work_area,edit_active_prefix+'_scan',
                    lambda:st.session_state[edit_active_prefix+'_value'],
                    lambda value,manual:_guardar_aplicacion(edit_active_prefix,value,manual))

            with tab_direct:
                cat_area = CATALOGO_INSTRUMENTOS_SEGEY.get(user_work_area, [])
                col_d1, col_d2 = st.columns([0.65, 0.35])
                with col_d1:
                    inst_sel = st.selectbox('Instrumento del catálogo normativo SEGEY (Tabla 14)', ['(Personalizado / Otro instrumento)'] + cat_area, key=edit_active_prefix + '_sel_cat')
                    if inst_sel.startswith('(Personalizado'):
                        nombre_inst_directo = st.text_input('Nombre de la prueba aplicada', placeholder='Ej. Batería psicopedagógica informal...', key=edit_active_prefix + '_inst_custom')
                    else:
                        nombre_inst_directo = inst_sel
                with col_d2:
                    fecha_dir = st.date_input('Fecha de aplicación', value=None,format='DD/MM/YYYY',key=edit_active_prefix + '_fecha_dir')

                from ui.epp_instrumentos import digital
                digital(doc,user_work_area,edit_active_prefix+'_aplicar',
                    lambda:st.session_state[edit_active_prefix+'_value'],
                    lambda value,manual:_guardar_aplicacion(edit_active_prefix,value,manual),
                    nombre=nombre_inst_directo or None)
                st.caption('O registra a continuación resultados previamente obtenidos por el profesional; no se simula la corrección de una prueba externa.')

                obs_directas = st.text_area(
                    'Resultados, observaciones y puntuaciones obtenidas',
                    placeholder='Escribe o pega aquí los hallazgos documentados de la prueba...',
                    height=120,
                    key=edit_active_prefix + '_obs_directas'
                )

                if st.button('⚡ Incorporar hallazgos al Formato Vivo', disabled=not obs_directas.strip() or not fecha_dir, key=edit_active_prefix + '_btn_direct_fill'):
                    try:
                        res_inc = incorporar_prueba_a_epp(
                            doc,
                            user_work_area,
                            obs_directas,
                            nombre_instrumento=nombre_inst_directo,
                            fecha_aplicacion=fecha_dir.isoformat(),
                            auto_actualizar_conclusion=can_edit_concl
                        )
                        st.session_state[edit_active_prefix + '_value'] = deepcopy(doc['partes'][user_work_area]['contenido'])
                        _save(edit_active_prefix)

                        if can_edit_concl and 'Conclusión' in doc['partes']:
                            prefix_concl = prefix + '_edit_' + doc['id'] + '_Conclusión'
                            if prefix_concl + '_doc' in st.session_state:
                                st.session_state[prefix_concl + '_value'] = deepcopy(doc['partes']['Conclusión']['contenido'])
                                _save(prefix_concl)

                        st.success(f"✨ Se incorporó: **{res_inc['instrumento']}**. Los campos correspondientes se actualizaron en el Formato Vivo.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Error al incorporar la prueba: {exc}")

    st.write("")
    st.markdown("---")

    # Barra superior de guardado rápido y estado
    if user_work_area:
        is_val = st.session_state[edit_active_prefix + '_value'].get('validada', False)
        c_status, c_save_top = st.columns([0.72, 0.28])
        with c_status:
            if is_val:
                st.markdown(f"<div style='padding:6px 0;'><span style='color:#2e7d32; font-weight:600;'>✅ Tu área ({user_work_area}) está validada</span></div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='padding:6px 0;'><span style='color:#1565c0; font-weight:500;'>✏️ Editando: <strong>{user_work_area}</strong> (borrador activo)</span></div>", unsafe_allow_html=True)
        with c_save_top:
            if st.button("💾 Guardar cambios de mi área", key=prefix + '_quick_save_top', use_container_width=True):
                _save(edit_active_prefix)
                if can_edit_concl and 'Conclusión' in doc['partes']:
                    _save(prefix + '_edit_' + doc['id'] + '_Conclusión')
                st.session_state.pop(prefix + '_pdf_bytes_' + doc['id'], None)
                st.toast("Borrador guardado correctamente.", icon="💾")

    # =========================================================================
    # EL FORMATO VIVO: ANEXOS XVII Y XVIII DEL MANUAL USAER
    # =========================================================================
    st.markdown("### 📄 Formato Vivo · Informe de Evaluación Psicopedagógica")
    st.caption("Trabaja directamente sobre cada sección del documento oficial. Los campos con bordes son editables para tu función; los demás reflejan el avance en vivo del equipo.")

    # Selector de modo de trabajo: Agilidad, minimalismo y cero sobrecarga
    vistas = [f"🎯 Mi área ({user_work_area})", "⚖️ Conclusión y NEE", "👁️ Ver informe completo"] if user_work_area else ["⚖️ Conclusión y NEE", "👁️ Ver informe completo"]
    vista_activa = st.radio(
        "Modo de trabajo:",
        vistas,
        index=0,
        horizontal=True,
        key=prefix + '_vista_modo',
        help="Elige si deseas enfocarte únicamente en los apartados de tu función o revisar todo el informe."
    )
    modo_area = vista_activa.startswith("🎯 Mi área")
    modo_concl = vista_activa.startswith("⚖️ Conclusión")
    modo_todo = vista_activa.startswith("👁️ Ver informe")

    # -------------------------------------------------------------------------
    # 1. DATOS DE IDENTIFICACIÓN Y MOTIVO
    # -------------------------------------------------------------------------
    if modo_todo or (modo_area and (user_work_area == 'Aprendizaje' or a['director'])):
        with st.expander("1. Datos de identificación y motivo de evaluación", expanded=True):
            col_m1, col_m2 = st.columns([0.65, 0.35])
            with col_m1:
                _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Aprendizaje', 'Motivo de evaluación', section='generales', height=80, prefix=prefix)
            with col_m2:
                generales=doc['partes'].get('Aprendizaje',{}).get('contenido',{}).get('generales',{})
                st.markdown('**Fecha inicial:** '+str(generales.get('Fecha inicial de evaluación') or 'Por confirmar'))
                st.markdown('**Fecha final:** '+str(generales.get('Fecha final de evaluación') or 'Por confirmar'))
                st.markdown(f"**Maestra de apoyo:** {doc['partes'].get('Aprendizaje', {}).get('autor', 'Por asignar')}")

            if user_work_area == 'Aprendizaje' or a['director']:
                with st.expander("📋 Datos generales complementarios (Domicilio, padres, escolaridad)"):
                    edit_apr = prefix + '_edit_' + doc['id'] + '_Aprendizaje'
                    if edit_apr + '_doc' not in st.session_state:
                        _abrir(edit_apr, doc, 'Aprendizaje')
                    for f in GENERALES:
                        if f != 'Motivo de evaluación':
                            _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Aprendizaje', f, section='generales', height=65, prefix=prefix)

                with st.expander("🏫 Historia escolar previa"):
                    edit_apr = prefix + '_edit_' + doc['id'] + '_Aprendizaje'
                    if edit_apr + '_doc' not in st.session_state:
                        _abrir(edit_apr, doc, 'Aprendizaje')
                    _grid(edit_apr, 'historia', HISTORIA)

    # -------------------------------------------------------------------------
    # 2. INFORMACIÓN INICIAL Y DE SALUD
    # -------------------------------------------------------------------------
    if modo_todo or (modo_area and (user_work_area == 'Trabajo Social' or a['director'])):
        with st.expander("2. Información inicial y de salud (Trabajo Social)", expanded=True):
            st.caption("Datos perinatales, desarrollo temprano y condiciones de salud actuales.")
            c2_1, c2_2 = st.columns(2)
            with c2_1:
                _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Trabajo Social', '2.1. Embarazo', prefix=prefix)
                _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Trabajo Social', '2.2. Parto', prefix=prefix)
            with c2_2:
                _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Trabajo Social', '2.3. Apariencia física', prefix=prefix)
                _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Trabajo Social', '2.4. Salud', prefix=prefix)

    # -------------------------------------------------------------------------
    # 3. FUNCIONAMIENTO INTELECTUAL
    # -------------------------------------------------------------------------
    if modo_todo or (modo_area and (user_work_area == 'Psicología' or a['director'])):
        with st.expander("3. Funcionamiento intelectual (Psicología)", expanded=True):
            st.caption("Atención, memoria, percepción, razonamiento lógico y cociente intelectual.")
            c3_1, c3_2 = st.columns(2)
            with c3_1:
                _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Psicología', '3.1. Atención', prefix=prefix)
                _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Psicología', '3.2. Memoria', prefix=prefix)
                _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Psicología', '3.3. Percepción', prefix=prefix)
            with c3_2:
                _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Psicología', '3.4. Razonamiento', prefix=prefix)
                _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Psicología', '3.5. Cociente intelectual', prefix=prefix)
                _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Psicología', '3.6. Etapa de desarrollo', prefix=prefix)
            _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Psicología', '3.7. Creatividad (AS)', prefix=prefix)

    # -------------------------------------------------------------------------
    # 4. CONDUCTA ADAPTATIVA (INTERDISCIPLINARIA)
    # -------------------------------------------------------------------------
    if modo_todo or modo_area:
        with st.expander("4. Conducta adaptativa (Comunicación · Aprendizaje · Psicología · Trabajo Social)", expanded=True):
            if modo_todo or (modo_area and (user_work_area in ('Comunicación', 'Aprendizaje') or a['director'])):
                st.markdown("#### 🗣️ 4.1. Comunicación y Lenguaje")
                c4_com1, c4_com2 = st.columns(2)
                with c4_com1:
                    _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Comunicación', '4.1. Comunicación y lenguaje: intención comunicativa', prefix=prefix)
                    _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Comunicación', '4.1. Lenguaje oral: fonológico', prefix=prefix)
                    _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Comunicación', '4.1. Lenguaje oral: morfosintáctico', prefix=prefix)
                    _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Comunicación', '4.1. Sistema de comunicación alternativo', prefix=prefix)
                with c4_com2:
                    _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Comunicación', '4.1. Lenguaje oral: semántico', prefix=prefix)
                    _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Comunicación', '4.1. Lenguaje oral: pragmático', prefix=prefix)
                    _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Comunicación', '4.1. Comprensión expresiva', prefix=prefix)
                    _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Comunicación', '4.1. Comprensión receptiva', prefix=prefix)

            if modo_todo or (modo_area and (user_work_area == 'Aprendizaje' or a['director'])):
                st.markdown("#### 📘 4.1. Habilidades Conceptuales y Académicas Funcionales")
                c4_apr1, c4_apr2 = st.columns(2)
                with c4_apr1:
                    _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Aprendizaje', '4.1. Lectura y escritura funcional', prefix=prefix)
                    _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Aprendizaje', '4.1. Matemáticas funcionales', prefix=prefix)
                with c4_apr2:
                    _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Aprendizaje', '4.1. Conceptos relativos al dinero', prefix=prefix)
                    _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Aprendizaje', '4.1. Orientación temporal', prefix=prefix)
                    _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Aprendizaje', '4.1. Orientación espacial', prefix=prefix)

            if modo_todo or (modo_area and (user_work_area == 'Psicología' or a['director'])):
                st.markdown("#### 🧠 4.2. Habilidades Sociales, Afectivas y de Autorregulación")
                c4_psi1, c4_psi2 = st.columns(2)
                with c4_psi1:
                    _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Psicología', '4.1. Autodirección', prefix=prefix)
                    _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Psicología', '4.2. Relaciones interpersonales', prefix=prefix)
                    _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Psicología', '4.2. Cumplimiento de normas', prefix=prefix)
                    _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Psicología', '4.2. Responsabilidad', prefix=prefix)
                with c4_psi2:
                    _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Psicología', '4.2. Autoestima', prefix=prefix)
                    _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Psicología', '4.2. Autoconcepto', prefix=prefix)
                    _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Psicología', '4.2. Identificación y autorregulación de emociones', prefix=prefix)
                    _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Psicología', '4.2. Autodeterminación', prefix=prefix)

            if modo_todo or (modo_area and (user_work_area in ('Psicología', 'Trabajo Social') or a['director'])):
                st.markdown("#### 🤝 4.3. Habilidades Prácticas, Vida Diaria y Psicomotricidad")
                c4_pra1, c4_pra2 = st.columns(2)
                with c4_pra1:
                    _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Psicología', '4.3. Noción corporal', prefix=prefix)
                    _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Psicología', '4.3. Coordinación motriz fina', prefix=prefix)
                    _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Psicología', '4.3. Coordinación motriz gruesa', prefix=prefix)
                    _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Psicología', '4.3. Movilidad, equilibrio y desplazamiento', prefix=prefix)
                with c4_pra2:
                    _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Trabajo Social', '4.3. Autocuidado', prefix=prefix)
                    _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Trabajo Social', '4.3. Actividades en la casa', prefix=prefix)
                    _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Trabajo Social', '4.3. Utilización de la comunidad', prefix=prefix)
                    _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Trabajo Social', '4.3. Salud y seguridad', prefix=prefix)
                    _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Trabajo Social', '4.3. Ocio y tiempo libre', prefix=prefix)

    # -------------------------------------------------------------------------
    # 5. FUNCIONAMIENTO ACADÉMICO
    # -------------------------------------------------------------------------
    if modo_todo or (modo_area and (user_work_area == 'Aprendizaje' or a['director'])):
        with st.expander("5. Funcionamiento académico (Aprendizaje)", expanded=True):
            st.caption("Nivel de logro en los Procesos de Desarrollo de Aprendizaje (PDA) y canales de aprendizaje.")
            _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Aprendizaje', '5.1. Competencia curricular', height=110, prefix=prefix)
            _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Aprendizaje', '5.2. Estilo de aprendizaje', height=100, prefix=prefix)

    # -------------------------------------------------------------------------
    # 6. CONTEXTOS DEL ALUMNO
    # -------------------------------------------------------------------------
    if modo_todo or (modo_area and (user_work_area in ('Aprendizaje', 'Trabajo Social') or a['director'])):
        with st.expander("6. Contextos escolar, sociofamiliar y social", expanded=True):
            st.caption("Interacciones en el aula regular, dinámica del hogar y entorno social.")
            c6_1, c6_2 = st.columns(2)
            with c6_1:
                _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Aprendizaje', '6.1. Contexto escolar', prefix=prefix)
                _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Aprendizaje', '6.1. Historia escolar', prefix=prefix)
            with c6_2:
                _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Trabajo Social', '6.2. Contexto familiar', prefix=prefix)
                _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Trabajo Social', '6.3. Contexto social', prefix=prefix)

            if user_work_area == 'Trabajo Social' or a['director']:
                with st.expander("👨‍👩‍👧 Composición familiar (permanece privada)"):
                    edit_ts = prefix + '_edit_' + doc['id'] + '_Trabajo Social'
                    if edit_ts + '_doc' not in st.session_state:
                        _abrir(edit_ts, doc, 'Trabajo Social')
                    _grid(edit_ts, 'familia', FAMILIA)

    # -------------------------------------------------------------------------
    # 7. CONCLUSIÓN INTERDISCIPLINARIA, NEE (SEGEY) Y BAP
    # -------------------------------------------------------------------------
    if modo_todo or modo_concl or can_edit_concl:
        with st.expander("7. Conclusión interdisciplinaria, determinación de NEE y BAP", expanded=True):
            st.markdown(
                """
                <div style='background-color: #fff9db; border-left: 4px solid #f59f00; padding: 10px 14px; border-radius: 6px; margin-bottom: 12px;'>
                    <strong>Fórmula oficial SEGEY (pp. 150-151):</strong><br>
                    • <strong>NEE:</strong> <code>[Necesita + verbo observable + contenido pedagógico / apoyo]</code>.<br>
                    • <strong>BAP:</strong> Barreras del entorno en contextos Áulico, Escolar, Familiar y Social (no etiquetas del alumno).
                </div>
                """,
                unsafe_allow_html=True
            )

            edit_concl = prefix + '_edit_' + doc['id'] + '_Conclusión'
            if can_edit_concl and edit_concl + '_doc' not in st.session_state:
                _abrir(edit_concl, doc, 'Conclusión')

            if can_edit_concl:
                col_b1, col_b2 = st.columns([0.7, 0.3])
                with col_b1:
                    if st.button("🎯 Generar propuesta de NEE oficial SEGEY y Acuerdos Interdisciplinarios", key=prefix + '_btn_gen_nee_vivo'):
                        prop = proponer_nee_segey(doc)
                        val_c = st.session_state[edit_concl + '_value']
                        for k, v in prop['campos'].items():
                            if not str(val_c.get('campos', {}).get(k, '')).strip():
                                val_c.setdefault('campos', {})[k] = v
                        val_c['nee'] = prop['nee']
                        val_c['bap'] = prop['bap']
                        val_c['validada'] = False
                        _save(edit_concl)
                        st.success("✨ Propuesta oficial de NEE y BAP ensamblada con base en los hallazgos de las 4 áreas.")
                        st.rerun()
                with col_b2:
                    st.caption("Sincroniza y redacta automáticamente según los hallazgos del equipo.")

            # Campos de conclusión
            _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Conclusión', '7.1. Conclusión', height=100, prefix=prefix)
            _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Conclusión', 'Énfasis de atención acordado', height=75, prefix=prefix)
            _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Conclusión', 'Asociación educativa sustentada', height=75, prefix=prefix)
            _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Conclusión', 'Acuerdos y apoyos del equipo', height=90, prefix=prefix)

            st.markdown("#### 🎯 Necesidades Educativas Específicas (NEE)")
            if can_edit_concl:
                st.caption("Puedes editar, añadir o retirar filas directamente en la tabla:")
                _grid(edit_concl, 'nee', NEE)
            else:
                nees = doc['partes'].get('Conclusión', {}).get('contenido', {}).get('nee', [])
                if any(any(str(r.get(k, '')).strip() for k in NEE) for r in nees):
                    df_nee = pd.DataFrame(nees)[[c for c in NEE if c in pd.DataFrame(nees).columns]].fillna('')
                    st.dataframe(df_nee, hide_index=True, use_container_width=True)
                else:
                    st.caption("*(La maestra de apoyo integrará las NEE acordadas por el equipo)*")

            st.markdown("#### 🚧 Barreras para el Aprendizaje y la Participación (BAP)")
            if can_edit_concl:
                st.caption("Barreras identificadas por contexto:")
                _grid(edit_concl, 'bap', BAP)
            else:
                baps = doc['partes'].get('Conclusión', {}).get('contenido', {}).get('bap', [])
                if any(any(str(r.get(k, '')).strip() for k in BAP) for r in baps):
                    df_bap = pd.DataFrame(baps)[[c for c in BAP if c in pd.DataFrame(baps).columns]].fillna('')
                    st.dataframe(df_bap, hide_index=True, use_container_width=True)
                else:
                    st.caption("*(BAP pendientes de integración)*")

    # -------------------------------------------------------------------------
    # INSTRUMENTOS Y SÍNTESIS DE MI ÁREA
    # -------------------------------------------------------------------------
    if user_work_area:
        with st.expander(f"📋 Instrumentos aplicados y síntesis de mi área ({user_work_area})"):
            val_area = st.session_state[edit_active_prefix + '_value']
            
            c_inst1, c_inst2 = st.columns([0.7, 0.3])
            with c_inst1:
                inst_text = val_area.get('instrumentos', '')
                key_inst = edit_active_prefix + '_inst_applied'
                st.text_area('Instrumentos aplicados por mi área', value=inst_text, key=key_inst, height=90, on_change=_field, args=(edit_active_prefix, key_inst, None, 'instrumentos'))
            with c_inst2:
                cat_area = CATALOGO_INSTRUMENTOS_SEGEY.get(user_work_area, [])
                if cat_area:
                    st.caption('Agregar rápidamente del catálogo:')
                    add_inst = st.selectbox('Prueba oficial', ['-- Seleccionar --'] + cat_area, key=edit_active_prefix + '_quick_add_inst')
                    if add_inst != '-- Seleccionar --' and st.button('➕ Agregar', key=edit_active_prefix + '_btn_quick_inst'):
                        prev_txt = str(val_area.get('instrumentos', '') or '').strip()
                        if add_inst not in prev_txt:
                            val_area['instrumentos'] = (prev_txt + '\n• ' + add_inst).strip() if prev_txt else '• ' + add_inst
                            val_area['validada'] = False
                            _save(edit_active_prefix)
                            st.rerun()

            key_sint = edit_active_prefix + '_sintesis_applied'
            st.text_area(
                'Síntesis de mi área y aspectos por confirmar',
                value=val_area.get('sintesis', ''),
                key=key_sint,
                height=100,
                on_change=_field,
                args=(edit_active_prefix, key_sint, None, 'sintesis'),
                placeholder='Escribe la síntesis general de tu evaluación y recomendaciones específicas...'
            )

            # Evaluaciones archivadas
            evals = val_area.get('evaluaciones', [])
            if evals:
                st.markdown(f"**Pruebas registradas en esta área ({len(evals)}):**")
                for ev in evals:
                    with st.expander(f"📄 {ev.get('nombre', 'Evaluación')} · {ev['id'][:8]}"):
                        from services.documento_sintesis import sintetizar
                        st.write(sintetizar(ev['texto'])['resumen'])
                        if st.button('Retirar esta prueba de mi área', key=edit_active_prefix + '_rm_ev_' + ev['id']):
                            val_area['evaluaciones'] = [e for e in val_area['evaluaciones'] if e['id'] != ev['id']]
                            val_area['validada'] = False
                            _save(edit_active_prefix)
                            st.rerun()

    # --- BARRA DE ACCIONES PRINCIPAL ---
    st.write("")
    st.markdown("---")
    act_col1, act_col2, act_col3, act_col4 = st.columns([0.25, 0.25, 0.25, 0.25])

    with act_col1:
        if user_work_area and st.button("💾 Guardar borrador", key=prefix + '_main_save', use_container_width=True):
            _save(edit_active_prefix)
            if can_edit_concl and 'Conclusión' in doc['partes']:
                _save(prefix + '_edit_' + doc['id'] + '_Conclusión')
            st.session_state.pop(prefix + '_pdf_bytes_' + doc['id'], None)
            st.success("Borrador guardado exitosamente.")

    with act_col2:
        if user_work_area:
            val_actual = st.session_state[edit_active_prefix + '_value'].get('validada', False)
            btn_txt = "✅ Área validada" if val_actual else "Confirmar revisión de mi área"
            if st.button(btn_txt, key=prefix + '_main_validate', use_container_width=True):
                st.session_state[edit_active_prefix + '_value']['validada'] = True
                _save(edit_active_prefix)
                st.session_state.pop(prefix + '_pdf_bytes_' + doc['id'], None)
                st.success(f"Área {user_work_area} confirmada y validada.")
                st.rerun()
        elif can_edit_concl:
            if st.button("✅ Validar conclusión acordada", key=prefix + '_concl_validate', use_container_width=True):
                st.session_state[prefix + '_edit_' + doc['id'] + '_Conclusión_value']['validada'] = True
                _save(prefix + '_edit_' + doc['id'] + '_Conclusión')
                st.session_state.pop(prefix + '_pdf_bytes_' + doc['id'], None)
                st.success("Conclusión interdisciplinaria validada.")
                st.rerun()

    pdf_key = prefix + '_pdf_bytes_' + doc['id']
    pdf_bytes = st.session_state.get(pdf_key)

    with act_col3:
        if not pdf_bytes:
            if st.button("📄 Generar PDF oficial", key=prefix + '_btn_prep_pdf', use_container_width=True):
                try:
                    with st.spinner("Construyendo PDF oficial..."):
                        pdf_bytes = generar_pdf(doc, student)
                        st.session_state[pdf_key] = pdf_bytes
                        st.rerun()
                except Exception as exc:
                    st.error(f"Pendiente de datos: {exc}")
        else:
            st.download_button(
                "⬇️ Descargar EPP oficial (firmas y sello)",
                pdf_bytes,
                file_name=f"EPP-{student.get('Nombre_Completo', 'Alumno')[:20].replace(' ', '_')}-{doc['ciclo']}.pdf",
                mime="application/pdf",
                key=prefix + '_main_pdf_download',
                help="Descarga el Informe Oficial de Evaluación Psicopedagógica (Anexos XVII y XVIII) con firmas del equipo, firma de Dirección y sello oficial de USAER 02-E.",
                use_container_width=True
            )

    with act_col4:
        if pdf_bytes:
            try:
                from ui.archivo_expediente import boton
                boton([doc['alumno']], 'EPP', pdf_bytes, f"EPP-{doc['id'][:8]}.pdf", prefix + '_btn_archivar_exp', doc['id'], doc['ciclo'], 'EPP concluida')
            except Exception:
                pass
        else:
            st.caption("Genera el PDF para archivar al expediente.")

    # Estado de guardado en pie de página
    if edit_active_prefix + '_error' in st.session_state:
        st.error(st.session_state[edit_active_prefix + '_error'])
    elif edit_active_prefix + '_saved' in st.session_state:
        st.caption(f"Último guardado confirmado: {st.session_state[edit_active_prefix + '_saved'][:19]}")

    # Respaldos de seguridad JSON
    with st.expander("📦 Respaldo y recuperación técnica de seguridad (JSON)"):
        if user_work_area:
            env = {'informe': doc['id'], 'area': user_work_area, 'contenido': st.session_state[edit_active_prefix + '_value']}
            st.download_button(
                f"Descargar respaldo de {user_work_area} (.json)",
                json.dumps(env, ensure_ascii=False, indent=2),
                file_name=f"epp-{doc['id'][:8]}-{user_work_area}.json",
                mime='application/json',
                key=prefix + '_backup_json'
            )
            up_back = st.file_uploader(f"Restaurar respaldo de {user_work_area}", type=['json'], key=prefix + '_restore_up')
            if up_back and st.button("Restaurar mi área", key=prefix + '_btn_restore'):
                try:
                    data = json.loads(up_back.getvalue())
                    if data.get('informe') == doc['id'] and data.get('area') == user_work_area:
                        from services.epp_modelo import validar_parte
                        rec = validar_parte(user_work_area, data['contenido'])
                        rec['validada'] = False
                        st.session_state[edit_active_prefix + '_value'] = rec
                        _save(edit_active_prefix)
                        st.success("Respaldo restaurado correctamente.")
                        st.rerun()
                    else:
                        st.error("El respaldo no corresponde a este alumno o área.")
                except Exception as e:
                    st.error(f"Error al leer respaldo: {e}")

        if s.puede_crear() and doc['partes']['META']['cuenta'] == a['cuenta']:
            st.write("")
            conf_del = st.checkbox("Confirmo retirar esta EPP del listado vigente", key=prefix + '_chk_del')
            if st.button("Retirar EPP", disabled=not conf_del, key=prefix + '_btn_del'):
                s.retirar(doc)
                st.rerun()

# Compatibilidad con fixtures de prueba y llamadas previas
def _pagina_guiada():
    a=s.actor()
    st.title('Evaluación psicopedagógica · Trabajo en equipo')
    st.caption('Un alumno, un informe. Cada profesional aporta y revisa sus hallazgos; la maestra de apoyo coordina la integración. Anexos XVII y XVIII del Manual USAER.')
    st.info('La IA ayuda a redactar a partir de hallazgos documentados. No aplica ni califica pruebas, ni emite diagnósticos clínicos. La conclusión educativa, NEE y apoyos requieren acuerdo del equipo.')
    prefix='epp_'+hashlib.sha256(a['cuenta'].encode()).hexdigest()[:12]
    from ui.epp_programacion import panel as control_programacion
    control_programacion(prefix)
    try:docs=s.listar(True)
    except Exception:
        st.error('No fue posible consultar las EPP. No se modificó ningún documento.');return
    if s.puede_crear():
        with st.expander('Iniciar una EPP nueva'):
            frame=s.planes.padron_autorizado()
            if not frame.empty:
                labels={str(r['ID_Alumno']):str(r['Nombre_Completo'])+' · '+str(r.get('Nombre_Escuela','')) for r in frame.to_dict('records')}
                id_alumno=st.selectbox('Alumno de mi matrícula',list(labels),format_func=labels.get,key=prefix+'_nuevo_alumno')
                ciclo=st.text_input('Ciclo escolar','2026-2027',key=prefix+'_nuevo_ciclo')
                if st.button('Crear EPP y guardar',key=prefix+'_crear'):
                    try:s.crear(id_alumno,ciclo);st.rerun()
                    except Exception as exc:st.error(str(exc) if isinstance(exc,(ValueError,PermissionError)) else 'No se confirmó la creación; actualiza el listado antes de intentar de nuevo.')
    if st.button('Actualizar aportaciones del equipo',key=prefix+'_refresh'):
        from data.google import clear_cache
        clear_cache(s.HOJA)
        # No borrar el editor ni capturas sin confirmación al pedir información.
        st.rerun()
    frame=s.planes.padron_autorizado()
    names={str(r['ID_Alumno']):str(r['Nombre_Completo'])+' · '+str(r.get('Nombre_Escuela','')) for r in frame.to_dict('records')}
    selected_key=prefix+'_selected'
    if a['area'] in ('Psicología','Comunicación','Trabajo Social') and not a['director']:
        # El padrón ya está autorizado en servidor. El filtro no amplía escuelas ni
        # crea informes: abre las mismas identidades iniciadas por las maestras.
        schools={str(r['ID_Escuela']):str(r.get('Nombre_Escuela','')) for r in frame.to_dict('records')
            if str(r.get('ID_Escuela','')).strip()}
        if not schools:
            st.info('No hay escuelas asignadas disponibles para consultar EPP.');return
        school=st.selectbox('Escuela asignada',sorted(schools,key=lambda i:schools[i]),
            format_func=schools.get,key=prefix+'_escuela')
        ids=set(frame.loc[frame['ID_Escuela'].astype(str).eq(school),'ID_Alumno'].astype(str))
        docs=[d for d in docs if d['alumno'] in ids and d['partes']['META']['estado']!='ELIMINADO']
        st.caption('Solo aparecen alumnos de esta escuela con EPP iniciada por su maestra de apoyo. Las aportaciones se integran en el mismo informe compartido.')
        if not docs:
            st.info('Todavía no hay EPP iniciadas en esta escuela. Cuando su maestra de apoyo cree una, aparecerá aquí; puedes usar Actualizar aportaciones del equipo.');return
        selected_key=prefix+'_selected_escuela_'+school
    if not docs:st.caption('Aún no hay EPP en tus escuelas asignadas. La maestra de apoyo puede iniciar una.');return
    by_id={d['id']:d for d in docs}
    selected=st.selectbox('Alumno con EPP iniciada' if selected_key!=prefix+'_selected' else 'Informe compartido',list(by_id),format_func=lambda i:names.get(by_id[i]['alumno'],'')+' · '+by_id[i]['ciclo']+(' · Retirado' if by_id[i]['partes']['META']['estado']=='ELIMINADO' else ''),key=selected_key)
    doc=by_id[selected];s.autorizar(doc)
    if doc['partes']['META']['estado']=='ELIMINADO':
        st.warning('EPP retirada. Su historial se conserva.')
        if s.puede_crear() and doc['partes']['META']['cuenta']==a['cuenta'] and st.button('Recuperar EPP',key=prefix+'_restore'):
            s.retirar(doc,True);st.rerun()
        return
    st.subheader(names[doc['alumno']])
    student=s.alumno_autorizado(doc['alumno'])
    st.caption('Datos del registro: grado '+str(student.get('Grado',''))+' · grupo '+str(student.get('Grupo',''))+
        ' · CCT '+str(student.get('CCT_Escuela',''))+' · condición registrada: '+str(student.get('Condicion_Discapacidad','Por confirmar')))
    status=[{'Área':area,'Profesional':doc['partes'].get(area,{}).get('autor','Por aportar'),
        'Estado':'Revisada' if doc['partes'].get(area,{}).get('contenido',{}).get('validada') else 'Borrador / pendiente'} for area in AREAS]
    st.dataframe(pd.DataFrame(status),hide_index=True,use_container_width=True)
    editable=[a['area']] if a['area'] in AREAS and not a['director'] else []
    if s.es_coordinadora(doc):editable.append('Conclusión')
    work,preview=st.columns([1.1,1],gap='large')
    with work:
        if editable:
            area=st.selectbox('Mis apartados',editable,key=prefix+'_area_select_'+selected)
            edit=prefix+'_edit_'+selected+'_'+area
            if edit+'_doc' not in st.session_state:_abrir(edit,doc,area)
            local=st.session_state[edit+'_doc']
            value=st.session_state[edit+'_value']
            st.caption('Los cambios de texto se guardan al salir del campo. Si falla la conexión, se muestra un aviso; conserva un respaldo antes de cerrar.')
            if area!='Conclusión':
                from ui.epp_instrumentos import digital
                with st.expander('Aplicar formatos digitales y resumir sus respuestas'):
                    digital(doc,area,edit+'_digital',lambda:st.session_state[edit+'_value'],lambda value,manual:_guardar_aplicacion(edit,value,manual))
                _text(edit,'instrumentos')
                cat_area = CATALOGO_INSTRUMENTOS_SEGEY.get(area, [])
                if cat_area:
                    with st.expander('📋 Catálogo de instrumentos normativos (Manual SEGEY · Tabla 14)'):
                        st.caption('Selecciona instrumentos oficiales de '+area+' para agregarlos a tu lista:')
                        elegidos = st.multiselect('Instrumentos oficiales de '+area, cat_area, key=edit+'_cat_inst_sel')
                        if elegidos and st.button('➕ Agregar a mis instrumentos aplicados', key=edit+'_cat_inst_btn'):
                            previo = str(value.get('instrumentos', '') or '').strip()
                            nuevos = [i for i in elegidos if i not in previo]
                            if nuevos:
                                nuevo_txt = (previo + '\n• ' + '\n• '.join(nuevos)).strip() if previo else '• ' + '\n• '.join(nuevos)
                                value['instrumentos'] = nuevo_txt
                                value['validada'] = False
                                _save(edit)
                                st.rerun()
                _text(edit,'fecha_aplicacion')
                with st.expander('Aplicar o registrar un instrumento aquí'):
                    st.caption('Entrada directa de observaciones y resultados documentados según el manual.')
                    if cat_area:
                        sug_dir = st.selectbox('Sugerencia de catálogo normativo', ['(Escribir o mantener personalizado)'] + cat_area, key=edit+'_sug_dir_inst')
                        if sug_dir != '(Escribir o mantener personalizado)' and not value.get('aplicacion_en_curso',{}).get('Instrumento o técnica aplicada'):
                            value.setdefault('aplicacion_en_curso',{})['Instrumento o técnica aplicada'] = sug_dir
                    direct_fields=['Instrumento o técnica aplicada','Fecha de aplicación (AAAA-MM-DD)',
                        'Cómo se aplicó y apoyos utilizados','Resultados y observaciones documentadas',
                        'Limitaciones y aspectos por confirmar']
                    value.setdefault('aplicacion_en_curso',dict.fromkeys(direct_fields,''))
                    st.caption('Este registro en curso se guarda al salir de cada campo, separado del informe.')
                    for f in direct_fields:_text(edit,f,'aplicacion_en_curso',height=100)
                    checked=st.checkbox('Revisé los resultados de esta aplicación y corresponden a este alumno',key=edit+'_direct_review')
                    if st.button('Incorporar instrumento aplicado',disabled=not checked,key=edit+'_direct_apply'):
                        try:
                            ev=entrada_directa(value['aplicacion_en_curso'])
                            if not any(e['id']==ev['id'] for e in value['evaluaciones']):value['evaluaciones'].append(ev)
                            value['validada']=False;_save(edit)
                            if edit+'_error' not in st.session_state:st.rerun()
                        except ValueError as exc:st.warning(str(exc))
                with st.expander('Cargar mis evaluaciones y revisar la lectura'):
                    st.caption('Hasta 32 MB; transcripción local. No se envían archivos originales a IA. Copia únicamente los hallazgos de este alumno, no cuadernillos completos ni pruebas con datos de terceros.')
                    upload=st.file_uploader('Evaluación de mi área',type=TIPOS,key=edit+'_upload')
                    if upload:
                        if upload.name.rsplit('.',1)[-1].lower() in ('pdf','png','jpg','jpeg') and len(upload.getvalue())<=5*1024*1024:
                            from ui.archivo_expediente import boton
                            confirma_archivo=st.checkbox('El archivo original corresponde solo a este alumno; revisé que no contiene datos de terceros',key=edit+'_archivo_solo_alumno')
                            tipo_archivo={'Aprendizaje':'Competencia curricular','Psicología':'Estudio psicológico','Comunicación':'Evaluación de comunicación y lenguaje','Trabajo Social':'Estudio social'}.get(area,'Otro documento educativo')
                            boton([doc['alumno']],tipo_archivo,upload.getvalue,upload.name,edit+'_archivar_evaluacion',doc['id'],doc['ciclo'],'EPP iniciada',disabled=not confirma_archivo)
                        else:st.caption('La lectura conserva su límite actual. Para archivar el original, usa PDF/JPG/PNG de hasta 5 MB en el expediente.')
                    if upload and st.button('Leer evaluación',key=edit+'_read'):
                        try:
                            read=leer_material(upload.name,upload.getvalue())
                            st.session_state[edit+'_transcripcion']=read['texto']
                            st.session_state[edit+'_avisos']=read['avisos']
                        except Exception as exc:st.warning(str(exc) if isinstance(exc,ValueError) else 'No se pudo transcribir. Usa un documento con texto o una imagen más clara.')
                    if edit+'_transcripcion' in st.session_state:
                        for warning in st.session_state.get(edit+'_avisos',[]):st.caption(warning)
                        from ui.documento_sintesis import vista
                        trans=vista(st.session_state[edit+'_transcripcion'],edit+'_texto_upload')['resumen']
                        reviewed=st.checkbox('Confirmo que estos hallazgos corresponden exclusivamente al alumno de esta EPP',key=edit+'_review_upload')
                        if st.button('Guardar evaluación revisada',disabled=not reviewed or not trans.strip(),key=edit+'_apply_upload'):
                            digest=hashlib.sha256(trans.encode()).hexdigest()
                            if not any(e['id']==digest for e in value['evaluaciones']):
                                value['evaluaciones'].append({'id':digest,'texto':trans,'nombre':'Evaluación de '+area})
                                value['validada']=False;_save(edit)
                                if edit+'_error' not in st.session_state:st.rerun()
                for ev in value['evaluaciones']:
                    with st.expander('Evaluación incorporada · '+ev['id'][:8]):
                        from services.documento_sintesis import sintetizar
                        st.write(sintetizar(ev['texto'])['resumen'])
                        if st.button('Retirar esta evaluación de mi área',key=edit+'_remove_'+ev['id']):
                            value['evaluaciones']=[e for e in value['evaluaciones'] if e['id']!=ev['id']]
                            value['validada']=False;_save(edit);st.rerun()
            with st.expander('Preparar mis apartados con IA'):
                ready=bool(value.get('evaluaciones')) if area!='Conclusión' else any(
                    any(t.strip() for t in doc['partes'].get(other,{}).get('contenido',{}).get('campos',{}).values()) for other in AREAS)
                if not ready:st.info('Primero incorpora los resultados de un instrumento, por carga o entrada directa.' if area!='Conclusión' else 'Primero reúne los hallazgos del equipo.')
                if st.button('Reunir expediente y evaluaciones',disabled=not ready,key=edit+'_context'):
                    try:
                        plan=s.contexto(doc)
                        st.session_state[edit+'_resumen']=s.resumen(doc,area,value,plan)
                        st.session_state[edit+'_fuente_resumen']=huella_instrumentos(doc,area,value)
                        st.session_state.pop(edit+'_resumen_ia',None)
                        st.session_state.pop(edit+'_consent',None)
                    except Exception:st.error('No se pudo reunir el contexto completo. No se enviaron datos a IA; intenta actualizar.')
                if edit+'_resumen' in st.session_state:
                    stale=st.session_state.get(edit+'_fuente_resumen')!=huella_instrumentos(doc,area,value)
                    if stale:st.warning('Cambiaron los instrumentos o las aportaciones del equipo. Vuelve a reunir el expediente y revisa el resumen actualizado.')
                    text=st.text_area('Resumen educativo a enviar: retira datos que identifiquen a alumnos o familiares',value=st.session_state[edit+'_resumen'],height=200,max_chars=12000,key=edit+'_resumen_ia')
                    consent=st.checkbox('Revisé el resumen: sin nombres, CURP, domicilios ni contactos. Autorizo analizar estos hallazgos en Gemini.',key=edit+'_consent')
                    replace=st.checkbox('Sustituir los textos de mi área por un nuevo borrador; conservar evaluaciones e historial',key=edit+'_replace')
                    if st.button('Proponer conclusión interdisciplinaria' if area=='Conclusión' else 'Generar mis apartados',disabled=not ready or stale or not consent or not replace,key=edit+'_generate'):
                        try:
                            from ai.planeacion import modelo_configurado
                            fingerprint=hashlib.sha256((doc['id']+area+modelo_configurado()+text).encode()).hexdigest()
                            if value.get('huella_ia')==fingerprint:
                                st.info('La propuesta para este resumen ya está guardada. Se conservan tus ediciones sin consumir otra solicitud de IA.')
                            else:
                                with st.spinner('Redactando con base en los hallazgos revisados…'):result=generar(text,area)
                                value['campos']=result['campos'];value['validada']=False
                                if area=='Conclusión':value['nee']=result['nee'];value['bap']=result['bap']
                                value['pendientes_ia']=result['faltantes'];value['huella_ia']=fingerprint
                                value['fuentes_analisis']=[{'id':e['id'],'nombre':e['nombre']} for e in value.get('evaluaciones',[])]
                                value['huella_instrumentos_analizados']=huella_instrumentos(doc,area,value)
                                _save(edit)
                                if edit+'_error' not in st.session_state:_abrir(edit,st.session_state[edit+'_doc'],area);st.rerun()
                        except (ValueError,RuntimeError) as exc:st.warning(str(exc))
            if area=='Aprendizaje':
                with st.expander('Datos generales editables'):
                    st.caption('Se precargan los datos disponibles del registro de este alumno. Los campos vacíos están por confirmar; tus correcciones se conservan, incluso si dejas un campo vacío.')
                    for f in GENERALES:_text(edit,f,'generales')
                with st.expander('Historia escolar'):_grid(edit,'historia',HISTORIA)
            if area=='Trabajo Social':
                with st.expander('Composición familiar (permanece privada; no se incluye en el resumen automático de IA)'):_grid(edit,'familia',FAMILIA)
            if area=='Conclusión':
                for f in campos(area):_text(edit,f,'campos')
            else:
                for title,areas in SECCIONES.items():
                    if area not in areas:continue
                    with st.expander(title,expanded=title.startswith('5.')):
                        st.caption('Describe lo observado, fortalezas y apoyos que necesita. Si no se evaluó un aspecto, no inventes un resultado; registra por qué en la síntesis de tu área.')
                        if area == 'Comunicación' and '4. Conducta adaptativa' in title:
                            st.info('📌 Orientación Manual SEGEY (p. 145):\n• Con lenguaje oral: describe Fonológico, Morfosintáctico, Semántico y Pragmático.\n• Sin lenguaje oral: describe Intención comunicativa, SAAC y Comprensión expresiva/receptiva.')
                        elif area == 'Psicología' and '3. Funcionamiento intelectual' in title:
                            st.caption('💡 Nota Manual SEGEY: Creatividad aplica específicamente para alumnos evaluados por Aptitudes Sobresalientes (AS).')
                        for f in areas[area]:_text(edit,f,'campos')
            if area=='Conclusión':
                st.caption('Manual SEGEY (p. 150-151): NEE = [Necesita + verbo observable + qué]. BAP = [Barreras del entorno en contextos Áulico, Escolar, Familiar y Social; no etiquetas del alumno].')
                _grid(edit,'nee',NEE);_grid(edit,'bap',BAP)
            else:_text(edit,'sintesis',height=150)
            for p in value.get('pendientes_ia',[]):st.caption('Por confirmar: '+p)
            if value.get('huella_instrumentos_analizados'):
                st.caption('Apartados propuestos a partir de instrumentos; siempre sujetos a revisión profesional.')
                if value['huella_instrumentos_analizados']!=huella_instrumentos(doc,area,value):
                    st.warning('Los resultados cambiaron después del análisis. Revisa o regenera los apartados antes de confirmarlos.')
            if st.button('Guardar mi borrador',key=edit+'_save'):_save(edit)
            if st.button('Confirmar revisión de mi área' if area!='Conclusión' else 'Validar conclusión acordada por el equipo',key=edit+'_validate'):
                if area=='Conclusión':
                    # Los campos de esta edición se conservan, pero se validan contra las áreas actuales.
                    actual=next(d for d in s.listar() if d['id']==doc['id'])
                    for other in AREAS:
                        if other in actual['partes']:st.session_state[edit+'_doc']['partes'][other]=deepcopy(actual['partes'][other])
                value['validada']=True;_save(edit)
            if edit+'_error' in st.session_state:st.error(st.session_state[edit+'_error'])
            elif edit+'_saved' in st.session_state:st.caption('Guardado confirmado: '+st.session_state[edit+'_saved'][:19])
            envelope={'informe':doc['id'],'area':area,'contenido':value}
            st.download_button('Respaldar mi edición antes de salir',json.dumps(envelope,ensure_ascii=False,indent=2),file_name='epp-'+doc['id'][:12]+'-'+area+'.json',mime='application/json',key=edit+'_backup')
            with st.expander('Recuperar mi respaldo editable'):
                backup=st.file_uploader('Respaldo de esta área (.json)',type=['json'],key=edit+'_restore_file')
                if backup and st.button('Recuperar y guardar mi área',key=edit+'_restore'):
                    try:
                        if backup.size>50000:raise ValueError('Respaldo demasiado extenso.')
                        from services.epp_modelo import validar_parte
                        envelope=json.loads(backup.getvalue())
                        if envelope.get('informe')!=doc['id'] or envelope.get('area')!=area:
                            raise ValueError('El respaldo corresponde a otro alumno, ciclo o área. No se incorporó su contenido.')
                        recovered=validar_parte(area,envelope['contenido'])
                        recovered['validada']=False
                        st.session_state[edit+'_value']=recovered;_save(edit)
                        if edit+'_error' not in st.session_state:_abrir(edit,st.session_state[edit+'_doc'],area);st.rerun()
                    except (ValueError,TypeError) as exc:st.warning(str(exc))
            with st.expander('Vaciar mis apartados (conservar historial)'):
                confirm=st.checkbox('Retirar mis textos y evaluaciones del informe actual',key=edit+'_clear_confirm')
                if st.button('Vaciar solamente mi área',disabled=not confirm,key=edit+'_clear'):
                    st.session_state[edit+'_value']=vacia(area);_save(edit)
                    if edit+'_error' not in st.session_state:_abrir(edit,st.session_state[edit+'_doc'],area);st.rerun()
            # La vista usa los campos de esta sesión y las aportaciones compartidas más recientes.
            doc=deepcopy(doc);doc['partes'][area]={**st.session_state[edit+'_doc']['partes'].get(area,{}), 'contenido':deepcopy(st.session_state[edit+'_value']),'fecha':st.session_state.get(edit+'_saved',''),'autor':a['nombre']}
            if edit+'_error' in st.session_state:doc['partes'][area]['contenido']['validada']=False
        else:st.caption('Puedes consultar el informe compartido. Cada integrante edita solamente su área.')
        if s.puede_crear() and doc['partes']['META']['cuenta']==a['cuenta']:
            with st.expander('Retirar EPP completa (recuperable)'):
                confirm=st.checkbox('Confirmo retirar el informe completo del listado vigente',key=prefix+'_retirar_confirm_'+selected)
                if st.button('Retirar EPP',disabled=not confirm,key=prefix+'_retirar_'+selected):s.retirar(doc);st.rerun()
    with preview:
        st.subheader('Informe único · Vista previa')
        for p in pendientes(doc):st.caption('Por completar: '+p)
        if not conclusion_vigente(doc):st.caption('Conclusión pendiente de revisión o hay hallazgos más recientes. No es un diagnóstico automático.')
        try:
            pdf=generar_pdf(doc,s.alumno_autorizado(doc['alumno']))
            from ui.planeacion import _preview
            _preview(prefix+'_preview_'+selected,pdf)
            st.download_button('Descargar informe único en PDF',pdf,file_name='EPP-'+doc['id'][:12]+'.pdf',mime='application/pdf',key=prefix+'_pdf_'+selected)
            from ui.archivo_expediente import boton
            boton([doc['alumno']],'EPP',pdf,'EPP-'+doc['id'][:12]+'.pdf',prefix+'_archivar_'+selected,doc['id'],doc['ciclo'],'EPP iniciada')
        except Exception:st.info('No se pudo actualizar el PDF. Los apartados guardados permanecen intactos.')


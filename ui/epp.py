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
from services.epp_entrada import precargar, huella_instrumentos
from services.epp_analisis import (
    identificar_instrumento_y_areas, distribuir_hallazgos_en_epp, proponer_nee_segey, incorporar_prueba_a_epp
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


def _save(prefix):
    """Guarda el apartado en curso en el repositorio canónico."""
    try:
        doc = st.session_state[prefix + '_doc']
        area = st.session_state[prefix + '_area']
        value = st.session_state[prefix + '_value']
        revision = doc['partes'].get(area, {}).get('revision', '')
        saved = s.guardar(doc, area, value, revision)
        doc['partes'][area] = saved
        st.session_state[prefix + '_value'] = deepcopy(saved['contenido'])
        st.session_state.pop(prefix + '_error', None)
        st.session_state[prefix + '_saved'] = saved['fecha']
    except Exception as exc:
        st.session_state[prefix + '_error'] = str(exc) if isinstance(exc, (ValueError, PermissionError, RuntimeError)) else 'No se confirmó el guardado. Tu texto sigue en esta sesión.'


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


def _render_field(doc, actor_area, can_edit_concl, is_director, target_area, field_name, section=None, height=95, prefix=''):
    """Renderiza un campo en el Formato Vivo:
    - Editable directamente si el usuario pertenece al área (o coordinadora en Conclusión / Director).
    - Vista colaborativa de lectura en vivo si pertenece a otra área.
    """
    is_editable = (target_area == actor_area) or (target_area == 'Conclusión' and can_edit_concl) or is_director
    
    if is_editable:
        edit_prefix = prefix + '_edit_' + doc['id'] + '_' + target_area
        if edit_prefix + '_doc' not in st.session_state:
            _abrir(edit_prefix, doc, target_area)

        value = st.session_state[edit_prefix + '_value']
        current_text = value.get(section, {}).get(field_name, '') if section else value.get(field_name, '')
        key = edit_prefix + '_field_' + (section or '') + field_name

        c_lbl, c_clr = st.columns([0.84, 0.16])
        with c_lbl:
            st.markdown(f"**{field_name}**")
        with c_clr:
            if current_text and str(current_text).strip():
                if st.button("🗑️ Vaciar", key=f"clr_{key}", help=f"Eliminar texto propuesto de {field_name}"):
                    _clear_field(edit_prefix, field_name, section)

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

    # Iniciar EPP nueva (Maestra de apoyo / Director)
    if s.puede_crear():
        with st.expander('➕ Iniciar una EPP nueva para un alumno'):
            frame = s.planes.padron_autorizado()
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

    # Filtro por escuela para especialistas
    frame = s.planes.padron_autorizado()
    names = {str(r['ID_Alumno']): str(r['Nombre_Completo']) + ' · ' + str(r.get('Nombre_Escuela', '')) for r in frame.to_dict('records')}
    selected_key = prefix + '_selected'

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
            for k in list(st.session_state):
                if k.startswith(prefix + '_edit_'):
                    del st.session_state[k]
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
    is_coordinator = s.puede_crear() and doc['partes']['META']['cuenta'] == a['cuenta']
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

    # Determinar qué área edita este usuario
    user_work_area = a['area'] if a['area'] in AREAS and not a['director'] else ('Aprendizaje' if a['director'] else None)
    if is_coordinator and not user_work_area:
        user_work_area = 'Aprendizaje'

    edit_active_prefix = prefix + '_edit_' + doc['id'] + '_' + (user_work_area or 'Aprendizaje')
    if edit_active_prefix + '_doc' not in st.session_state and user_work_area:
        _abrir(edit_active_prefix, doc, user_work_area)

    # --- ⚡ CENTRO ÁGIL DE EVALUACIÓN Y PRUEBAS ---
    if user_work_area:
        with st.container():
            st.markdown(
                f"""
                <div style='background: linear-gradient(135deg, #f0f7ff 0%, #e6f0fa 100%); border-left: 5px solid #2b6cb0; padding: 12px 16px; border-radius: 8px; margin-bottom: 16px;'>
                    <h4 style='margin:0; color:#1a365d;'>⚡ Centro Ágil de Evaluación · {user_work_area}</h4>
                    <span style='font-size:0.85rem; color:#4a5568;'>Sube el escaneo de tu prueba (PDF/Foto) o regístrala aquí. El sistema distribuirá los hallazgos en tu informe vivo y actualizará la propuesta de NEE.</span>
                </div>
                """,
                unsafe_allow_html=True
            )

            tab_scan, tab_direct = st.tabs(['📷 Subir escaneo o prueba (PDF / Foto)', '✍️ Aplicar / Registrar prueba directamente'])

            with tab_scan:
                col_u1, col_u2 = st.columns([0.7, 0.3])
                with col_u1:
                    upload = st.file_uploader('Documento de prueba aplicada (PDF, PNG, JPG)', type=TIPOS, key=edit_active_prefix + '_upload_scan')
                with col_u2:
                    st.write("")
                    st.caption('Reconocimiento automático de instrumentos SEGEY y llenado de apartados.')

                if upload:
                    if st.button('⚡ Analizar prueba y auto-llenar Formato Vivo', key=edit_active_prefix + '_btn_scan_fill'):
                        try:
                            with st.spinner('Extrayendo texto y analizando hallazgos de la prueba...'):
                                read = leer_material(upload.name, upload.getvalue())
                                trans_text = read.get('texto', '').strip()
                                if not trans_text:
                                    st.warning('No se pudo extraer texto del archivo subido. Asegúrate de que sea legible.')
                                else:
                                    res_inc = incorporar_prueba_a_epp(
                                        doc,
                                        user_work_area,
                                        trans_text,
                                        auto_actualizar_conclusion=can_edit_concl
                                    )
                                    # Sincronizar en session_state y guardar
                                    st.session_state[edit_active_prefix + '_value'] = deepcopy(doc['partes'][user_work_area]['contenido'])
                                    _save(edit_active_prefix)

                                    if can_edit_concl and 'Conclusión' in doc['partes']:
                                        prefix_concl = prefix + '_edit_' + doc['id'] + '_Conclusión'
                                        if prefix_concl + '_doc' in st.session_state:
                                            st.session_state[prefix_concl + '_value'] = deepcopy(doc['partes']['Conclusión']['contenido'])
                                            _save(prefix_concl)

                                    st.success(f"✨ Se detectó: **{res_inc['instrumento']}**. Se completaron los apartados correspondientes en el Formato Vivo.")
                                    st.rerun()
                        except Exception as exc:
                            st.error(f"Error al procesar la prueba: {exc}")

                    # Archivar copia opcional en expediente digital
                    if len(upload.getvalue()) <= 5 * 1024 * 1024:
                        from ui.archivo_expediente import boton
                        tipo_arc = {'Aprendizaje': 'Competencia curricular', 'Psicología': 'Estudio psicológico', 'Comunicación': 'Evaluación de comunicación y lenguaje', 'Trabajo Social': 'Estudio social'}.get(user_work_area, 'Evaluación psicopedagógica')
                        boton([doc['alumno']], tipo_arc, upload.getvalue, upload.name, edit_active_prefix + '_archivar_scan', doc['id'], doc['ciclo'], 'EPP iniciada')

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
                    fecha_dir = st.text_input('Fecha de aplicación', value='2026-10-22', key=edit_active_prefix + '_fecha_dir')

                obs_directas = st.text_area(
                    'Resultados, observaciones y puntuaciones obtenidas',
                    placeholder='Escribe o pega aquí los hallazgos documentados de la prueba...',
                    height=120,
                    key=edit_active_prefix + '_obs_directas'
                )

                if st.button('⚡ Incorporar hallazgos al Formato Vivo', disabled=not obs_directas.strip(), key=edit_active_prefix + '_btn_direct_fill'):
                    try:
                        res_inc = incorporar_prueba_a_epp(
                            doc,
                            user_work_area,
                            obs_directas,
                            nombre_instrumento=nombre_inst_directo,
                            fecha_aplicacion=fecha_dir,
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

    # =========================================================================
    # EL FORMATO VIVO: ANEXOS XVII Y XVIII DEL MANUAL USAER
    # =========================================================================
    st.markdown("### 📄 Formato Vivo · Informe de Evaluación Psicopedagógica")
    st.caption("Trabaja directamente sobre cada sección del documento oficial. Los campos con bordes son editables para tu función; los demás reflejan el avance en vivo del equipo.")

    # -------------------------------------------------------------------------
    # 1. DATOS DE IDENTIFICACIÓN Y MOTIVO
    # -------------------------------------------------------------------------
    with st.expander("1. Datos de identificación y motivo de evaluación", expanded=True):
        col_m1, col_m2 = st.columns([0.65, 0.35])
        with col_m1:
            _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Aprendizaje', 'Motivo de evaluación', section='generales', height=80, prefix=prefix)
        with col_m2:
            st.markdown(f"**Fecha inicial:** {student.get('Fecha_Ingreso', 'Octubre 2026')}")
            st.markdown(f"**Fecha final:** Noviembre 2026")
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
    with st.expander("4. Conducta adaptativa (Comunicación · Aprendizaje · Psicología · Trabajo Social)", expanded=True):
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

        st.markdown("#### 📘 4.1. Habilidades Conceptuales y Académicas Funcionales")
        c4_apr1, c4_apr2 = st.columns(2)
        with c4_apr1:
            _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Aprendizaje', '4.1. Lectura y escritura funcional', prefix=prefix)
            _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Aprendizaje', '4.1. Matemáticas funcionales', prefix=prefix)
        with c4_apr2:
            _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Aprendizaje', '4.1. Conceptos relativos al dinero', prefix=prefix)
            _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Aprendizaje', '4.1. Orientación temporal', prefix=prefix)
            _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Aprendizaje', '4.1. Orientación espacial', prefix=prefix)

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
    with st.expander("5. Funcionamiento académico (Aprendizaje)", expanded=True):
        st.caption("Nivel de logro en los Procesos de Desarrollo de Aprendizaje (PDA) y canales de aprendizaje.")
        _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Aprendizaje', '5.1. Competencia curricular', height=110, prefix=prefix)
        _render_field(doc, user_work_area, can_edit_concl, a['director'], 'Aprendizaje', '5.2. Estilo de aprendizaje', height=100, prefix=prefix)

    # -------------------------------------------------------------------------
    # 6. CONTEXTOS DEL ALUMNO
    # -------------------------------------------------------------------------
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
                        st.write(ev['texto'])
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
            st.success("Borrador guardado exitosamente.")

    with act_col2:
        if user_work_area:
            val_actual = st.session_state[edit_active_prefix + '_value'].get('validada', False)
            btn_txt = "✅ Área validada" if val_actual else "Confirmar revisión de mi área"
            if st.button(btn_txt, key=prefix + '_main_validate', use_container_width=True):
                st.session_state[edit_active_prefix + '_value']['validada'] = True
                _save(edit_active_prefix)
                st.success(f"Área {user_work_area} confirmada y validada.")
                st.rerun()
        elif can_edit_concl:
            if st.button("✅ Validar conclusión acordada", key=prefix + '_concl_validate', use_container_width=True):
                st.session_state[prefix + '_edit_' + doc['id'] + '_Conclusión_value']['validada'] = True
                _save(prefix + '_edit_' + doc['id'] + '_Conclusión')
                st.success("Conclusión interdisciplinaria validada.")
                st.rerun()

    with act_col3:
        try:
            pdf_bytes = generar_pdf(doc, student)
            st.download_button(
                "📄 Descargar PDF oficial",
                pdf_bytes,
                file_name=f"EPP-{student.get('Nombre_Completo', 'Alumno')[:20].replace(' ', '_')}-{doc['ciclo']}.pdf",
                mime="application/pdf",
                key=prefix + '_main_pdf_download',
                use_container_width=True
            )
        except Exception:
            st.button("📄 PDF pendiente de datos", disabled=True, key=prefix + '_pdf_dis', use_container_width=True)

    with act_col4:
        try:
            from ui.archivo_expediente import boton
            boton([doc['alumno']], 'EPP', pdf_bytes, f"EPP-{doc['id'][:8]}.pdf", prefix + '_btn_archivar_exp', doc['id'], doc['ciclo'], 'EPP concluida')
        except Exception:
            pass

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

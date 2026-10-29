"""Ayuda pedagógica inteligente: metáfora del automóvil (1 clic, conducción segura y 4 contextos Zona 001)."""
import streamlit as st
import logging
from services import planeacion as s, planeacion_generacion as g
from services.planeacion_papel import huella
from services.planeacion_propuesta import conservar_redaccion, aplicar
from services import planeacion_rapida as rapido
from services.planeacion_modelo import FORMATOS


def panel(prefix):
    from ui import planeacion as u
    from ui.planeacion_papel import refrescar_editor
    from ui.planeacion_cero_friccion import _asistencia
    doc = st.session_state[prefix+'_doc']
    s.autorizar(doc, True)
    
    key = prefix + '_asistente'
    widgets = key + '_' + doc['id']
    config = {**g.configuracion(doc), **doc['metadatos'].get('configuracion_generacion', {})}
    estado = rapido.estado(doc)
    defaults = estado['defaults']
    
    st.subheader('Actividades para esta planeación')
    if doc.get('metadatos',{}).get('modalidad_planeacion')=='individual':
        from ui.planeacion_memoria import actualizar,panel as panel_memoria
        if not actualizar(prefix):return
        doc=st.session_state[prefix+'_doc']
        for alumno in doc['datos']['Alumnos']:panel_memoria(prefix,str(alumno['ID_Alumno']),u._persist)
    
    # ── METÁFORA DEL AUTOMÓVIL: TABLERO DE CONDUCCIÓN PEDAGÓGICA ──
    alumnos_nombres = ', '.join(a.get('Nombre del alumno', 'Alumno') for a in doc['datos'].get('Alumnos', [])) or 'Alumno asignado'
    ctx_total = len(FORMATOS[doc['formato']]['contextos'])
    
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #f0fdf4 0%, #e0f2fe 100%); border: 1px solid #bbf7d0; border-radius: 10px; padding: 12px 16px; margin-bottom: 12px;">
        <div style="display: flex; align-items: center; justify-content: space-between;">
            <div>
                <span style="font-weight: 700; color: #166534; font-size: 0.95rem;">🚗 Conducción Pedagógica USAER 2E · Zona 001</span>
                <span style="background: #dcfce7; color: #15803d; font-size: 0.75rem; font-weight: 600; padding: 2px 8px; border-radius: 12px; margin-left: 8px;">Propuesta para revisión docente</span>
            </div>
            <div style="font-size: 0.8rem; color: #0369a1; font-weight: 500;">
                {ctx_total} contextos oficiales
            </div>
        </div>
        <div style="font-size: 0.84rem; color: #334155; margin-top: 4px;">
            <strong>{alumnos_nombres}</strong> · {len(estado['fuentes'])} antecedentes (EPP, BAP, CTE) listos. No necesitas recapturar nada.
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Controles de configuración
    selecciones = {**defaults}
    
    # Botón de 1 Clic Directo (Piloto Inteligente)
    errores_base = rapido.validar(doc, selecciones)
    btn_col1, btn_col2 = st.columns([3, 2])
    with btn_col1:
        generar_1clic = st.button('⚡ Generar planeación inteligente (1 clic)', type='primary',
                                  disabled=bool(errores_base), key=widgets+'_1clic',
                                  help='Genera actividades balanceadas en los 4 contextos con apoyos DUA y referentes NEM',
                                  width='stretch')
    with btn_col2:
        generar_local = st.button('📋 Ensamblar sin IA (local)', key=widgets+'_local_btn',
                                  help='Ensambla con tus antecedentes y plantillas locales verificadas',
                                  width='stretch')

    # Expander de ajustes opcionales para quien desee afinar detalles
    with st.expander('⚙️ Ajustes opcionales de conducción', expanded=False):
        st.caption('Los parámetros ya están preconfigurados con los antecedentes del alumno. Modifícalos solo si lo deseas.')
        c1, c2 = st.columns(2)
        cantidad = c1.selectbox('Cantidad de actividades', list(range(1, 9)), index=min(2, len(list(range(1, 9)))-1), key=widgets+'_cantidad')
        selecciones['duracion'] = c2.selectbox('Minutos por actividad', [15, 20, 30, 45, 60], index=[15, 20, 30, 45, 60].index(defaults['duracion']), key=widgets+'_duracion')
        selecciones['contextos'] = st.multiselect('Contextos de intervención', FORMATOS[doc['formato']]['contextos'], default=defaults['contextos'], key=widgets+'_contextos')
        selecciones['tematica'] = st.text_input('Temática o interés del alumno (opcional)', value=defaults['tematica'], max_chars=300, placeholder='Se utilizarán sus necesidades y antecedentes si lo dejas vacío', key=widgets+'_tematica')
        selecciones['prioridades'] = st.multiselect('Qué vamos a trabajar', estado['permitidas'], default=defaults['prioridades'], format_func=lambda p: rapido.PRIORIDADES[p][0], key=widgets+'_prioridades')
        selecciones['apoyos'] = st.multiselect('Apoyos para participar y responder', list(rapido.APOYOS), default=defaults['apoyos'], format_func=lambda p: rapido.APOYOS[p][0], key=widgets+'_apoyos')
        selecciones['metodo'] = st.selectbox('Cómo lo trabajaremos', list(rapido.METODOS), index=list(rapido.METODOS).index(defaults['metodo']), format_func=lambda p: rapido.METODOS[p], key=widgets+'_metodo')
        selecciones['frecuencia'] = st.selectbox('Frecuencia propuesta', rapido.FRECUENCIAS, index=rapido.FRECUENCIAS.index(defaults['frecuencia']), key=widgets+'_frecuencia')
        selecciones['acuerdos'] = st.multiselect('Acuerdos CTE registrados', list(estado['acuerdos']), default=defaults['acuerdos'], format_func=lambda p: estado['acuerdos'][p]['texto'], key=widgets+'_acuerdos', disabled=not estado['acuerdos'])
        selecciones['completar'] = st.checkbox('Completar apartados vacíos al preparar sin IA', value=defaults['completar'], key=widgets+'_completar')
        motor = st.radio('Preparar actividades', ['Con mis datos, sin IA', 'Con IA'], index=1, horizontal=True, key=key+'_motor')
        preparar_manual = st.button('Preparar propuesta', disabled=bool(rapido.validar(doc, selecciones)), key=widgets+'_preparar')

    with st.expander('Consultar NEE, BAP y referentes conectados', expanded=False):
        for texto in estado['nee']: st.text(texto)
        if not estado['nee']: st.caption('Sin NEE explícita previa; se formulará a partir de los antecedentes de la EPP.')
        for row in estado['bap']: st.text(row.get(rapido.BARRERA, '') + ' · ' + row.get('fuente', ''))
        registros = doc['metadatos'].get('curriculo', {}).get('registros', [])
        st.caption(f"{len(registros)} referentes curriculares NEM vinculados.")
        for r in registros:
            st.text(f"Contenido: {r.get('contenido','')}\nPDA: {r.get('pda','')}")

    for aviso in estado['avisos']: st.info(aviso)
    errores = rapido.validar(doc, selecciones)
    for error in errores: st.warning(error)

    if not errores:
        config = {**config, **rapido.orientaciones(doc, selecciones), 'duracion': selecciones['duracion'],
                  'sesiones': cantidad, 'actividades_solicitadas': cantidad, 'contextos_solicitados': selecciones['contextos']}

    # ── EJECUCIÓN INTELIGENTE EN 1 CLIC ──
    if generar_1clic or (generar_local) or preparar_manual:
        st.session_state.pop(key+'_propuesta', None)
        st.session_state.pop(key+'_solicitud', None)
        usar_ia = (motor == 'Con IA') if preparar_manual else (generar_1clic)
        try:
            if usar_ia:
                sol = g.preparar_solicitud(doc, config)
                st.session_state[key+'_solicitud'] = {'sol': sol, 'config': config, 'base': huella(doc), 'selecciones': selecciones}
                if generar_1clic:
                    # En 1 clic se ejecuta directamente la asistencia sin pantallas intermedias
                    with st.spinner('Conduciendo propuesta pedagógica con DUA y referentes NEM...'):
                        candidate, preview, aviso = _asistencia(doc, 'Proponer actividades con IA', config, sol, True)
                    if candidate and candidate != doc:
                        candidate['metadatos']['preparacion_rapida'] = {'selecciones': selecciones, 'requiere_revision': True, 'motor': 'IA'}
                        st.session_state[key+'_propuesta'] = {'base': huella(doc), 'documento': conservar_redaccion(doc, candidate)}
                        st.rerun(scope='app')
                    elif aviso:
                        st.info(aviso)
            else:
                candidate = rapido.ensamblar(doc, selecciones)
                st.session_state[key+'_propuesta'] = {'base': huella(doc), 'documento': conservar_redaccion(doc, candidate)}
                if generar_local:
                    st.rerun(scope='app')
        except (ValueError, PermissionError, RuntimeError) as exc:
            st.warning(str(exc))
        except Exception as exc:
            logging.getLogger(__name__).warning('No se pudo preparar la propuesta: %s', type(exc).__name__)
            st.warning('No se pudo generar la propuesta en este momento. Tu hoja se conserva.')

    # Soporte para el flujo por pasos (compatibilidad con tests)
    solicitud = st.session_state.get(key+'_solicitud')
    if solicitud and not st.session_state.get(key+'_propuesta') and not generar_1clic:
        st.caption('Resumen pedagógico preparado (sin datos identificadores):')
        st.text(solicitud['sol']['resumen'])
        consentimiento = st.checkbox('Revisé este resumen y autorizo enviarlo a la IA', key=key+'_consent_'+solicitud['sol']['huella'])
        if st.button('Generar actividades con este resumen', disabled=not consentimiento, key=key+'_generar'):
            try:
                if solicitud['base'] != huella(doc):
                    raise ValueError('Tu hoja cambió. Prepara una nueva propuesta; tu edición se conserva.')
                with st.spinner('Generando propuesta con IA...'):
                    candidate, preview, aviso = _asistencia(doc, 'Proponer actividades con IA', solicitud['config'], solicitud['sol'], True)
                if candidate == doc:
                    st.info(aviso or 'No hay actividades nuevas. Puedes continuar escribiendo sin IA.')
                else:
                    candidate['metadatos']['preparacion_rapida'] = {'selecciones': solicitud['selecciones'], 'requiere_revision': True, 'motor': 'IA'}
                    st.session_state[key+'_propuesta'] = {'base': huella(doc), 'documento': conservar_redaccion(doc, candidate)}
                    st.rerun(scope='app')
            except Exception as exc:
                from ui.planeacion_progreso import mostrar_error
                mostrar_error(exc)

    # ── PRESENTACIÓN LIMPIA DE LA PROPUESTA (FORMATO VIVO) ──
    propuesta = st.session_state.get(key+'_propuesta')
    if not propuesta:
        return
        
    st.markdown('### 🎯 Propuesta Pedagógica Generada')
    candidate = propuesta['documento']
    nuevas = 0
    
    iconos_ctx = {'aula de apoyo': '🏫', 'aula regular': '👥', 'escuela': '🏛️', 'familia': '🏡', 'comunidad': '🤝'}
    
    for tabla, rows in candidate['tablas'].items():
        for row in rows:
            if row in doc['tablas'].get(tabla, []):
                continue
            nuevas += 1
            ctx = str(row.get('Contextos', row.get('Contexto', ''))).lower().strip()
            icono = next((v for k, v in iconos_ctx.items() if k in ctx), '📌')
            
            with st.container():
                st.markdown(f"**{icono} {row.get('Contextos', row.get('Contexto', 'Actividad'))}**")
                lineas = [f"{k}: {v}" for k, v in row.items() if not k.startswith('_') and str(v).strip() and k not in ('Contextos', 'Contexto')]
                st.text('\n'.join(str(v) for k, v in row.items() if not k.startswith('_') and str(v).strip()))

    if not nuevas:
        st.info('No hay filas nuevas para añadir. Puedes editar directamente en el formato.'); return

    st.caption('Se añadirán a tu formato vivo tradicional sin sustituir lo que ya escribiste.')
    act_col1, act_col2 = st.columns(2)
    if act_col1.button('Añadir propuesta a mi formato', type='primary', key=key+'_aplicar', width='stretch'):
        try:
            if st.session_state.get(prefix+'_pending') and not u._persist(prefix):
                st.warning('Primero necesitamos confirmar tu edición pendiente.'); return
            result = aplicar(st.session_state[prefix+'_doc'], propuesta)
            u._open(prefix, result)
            u._persist(prefix)
            st.session_state.pop(key+'_propuesta', None)
            st.session_state.pop(key+'_solicitud', None)
            st.session_state.pop(prefix+'_papel_panel', None)
            st.rerun(scope='app')
        except (ValueError, PermissionError, RuntimeError) as exc:
            st.warning(str(exc))
            
    if act_col2.button('Descartar propuesta', key=key+'_descartar', width='stretch'):
        st.session_state.pop(key+'_propuesta', None)
        st.session_state.pop(key+'_solicitud', None)
        refrescar_editor()

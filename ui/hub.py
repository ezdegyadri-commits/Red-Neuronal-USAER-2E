"""Centro de Control Central (Hub / Launchpad) para USAER 02-E.

Proporciona una experiencia de navegación fluida, ágil e interactiva,
con dock de accesos rápidos, vista previa dinámica al pasar el cursor (hover)
y filtrado inmediato por categorías.
"""
NAV_VERSION='2026-10-28-documentos-v1'
import streamlit as st
from data import repository as repo

MODULOS_INFO = {
    "Expedientes": {
        "titulo": "Expedientes Únicos",
        "categoria": "GENERAL",
        "icono": "📁",
        "badge": "Alumnado",
        "color": "#0F4C5C",
        "color_bg": "#E6F4F7",
        "desc": "Consulta integral, trayectoria y seguimiento psicopedagógico de cada alumno.",
        "tags": ["Trayectoria", "Seguimiento", "Expediente 360°"],
    },
    "Anexo III BAP": {
        "titulo": "Anexo III · Barreras (BAP)",
        "categoria": "ANEXOS",
        "icono": "🛡️",
        "badge": "Inclusión",
        "color": "#D97706",
        "color_bg": "#FFFBEB",
        "desc": "Detección oficial de barreras, recursos y apoyos específicos requeridos.",
        "tags": ["Barreras", "Apoyos", "Inclusión"],
    },
    "Anexo IV Hoja de sugerencias": {
        "titulo": "Anexo IV · Sugerencias",
        "categoria": "ANEXOS",
        "icono": "💡",
        "badge": "Pedagógico",
        "color": "#0D9488",
        "color_bg": "#F0FDFA",
        "desc": "Recomendaciones prácticas dirigidas a docentes regulares y familia.",
        "tags": ["Docentes", "Familias", "Estrategias"],
    },
    "Anexo V Eventos significativos": {
        "titulo": "Anexo V · Eventos",
        "categoria": "ANEXOS",
        "icono": "📌",
        "badge": "Bitácora",
        "color": "#2563EB",
        "color_bg": "#EFF6FF",
        "desc": "Registro cronológico de acuerdos, entrevistas y situaciones relevantes.",
        "tags": ["Bitácora", "Acuerdos", "Entrevistas"],
    },
    "Anexo VII Derivación": {
        "titulo": "Anexo VII · Derivación",
        "categoria": "ANEXOS",
        "icono": "↗️",
        "badge": "Canalización",
        "color": "#7C3AED",
        "color_bg": "#F5F3FF",
        "desc": "Formato oficial para la derivación y canalización de alumnos.",
        "tags": ["Canalización", "Protocolo Oficial"],
    },
    "Planeación e intervención": {
        "titulo": "Planeación e Intervención",
        "categoria": "ADMINISTRACIÓN",
        "icono": "🎯",
        "badge": "Intervención",
        "color": "#0D9488",
        "color_bg": "#F0FDFA",
        "desc": "Diseño de planeaciones colaborativas, ajustes razonables y seguimiento formativo.",
        "tags": ["ZDP e IA", "Colaboración", "Anexos XIX y XXIII"],
    },
    "Juntas académicas": {
        "titulo": "Juntas académicas",
        "categoria": "ADMINISTRACIÓN",
        "icono": "🗂️",
        "badge": "Materiales por fecha",
        "color": "#0D9488",
        "color_bg": "#F0FDFA",
        "desc": "Metas, instrumento de planeación y cuadro de metodologías vivos por sesión.",
        "tags": ["Juntas", "Metas", "Metodologías"],
    },
    "Metas personales": {
        "titulo": "Metas e instrumento de planeación",
        "categoria": "ADMINISTRACIÓN",
        "icono": "📝",
        "badge": "Junta académica",
        "color": "#0D9488",
        "color_bg": "#F0FDFA",
        "desc": "Elige un alumno, registra metas y recursos y valora tu planeación con la rúbrica.",
        "tags": ["Metas", "Apoyos", "Ajustes razonables"],
    },
    "EPP": {
        "titulo": "Evaluación Psicopedagógica",
        "categoria": "ADMINISTRACIÓN",
        "icono": "📋",
        "badge": "Diagnóstico",
        "color": "#0284C7",
        "color_bg": "#F0F9FF",
        "desc": "Informes de evaluación multidisciplinaria y determinación de apoyos.",
        "tags": ["Evaluación", "Diagnóstico", "Multidisciplinario"],
    },
    "Estadística": {
        "titulo": "Estadística y Listado Nominal",
        "categoria": "ADMINISTRACIÓN",
        "icono": "📊",
        "badge": "Métricas",
        "color": "#059669",
        "color_bg": "#ECFDF5",
        "desc": "Distribución por escuela, grado, condición y exportación de reportes.",
        "tags": ["Padrón Nominal", "Métricas", "Exportación Excel"],
    },
    "Documentos": {
        "titulo": "Documentos Oficiales",
        "categoria": "ADMINISTRACIÓN",
        "icono": "📄",
        "badge": "Formatos",
        "color": "#475569",
        "color_bg": "#F1F5F9",
        "desc": "Biblioteca de formatos normativos, manuales y circulares de USAER.",
        "tags": ["Normativa", "Manuales", "Formatos Oficiales"],
    },
    "Calendario de actividades": {
        "titulo": "Calendario de Actividades",
        "categoria": "ADMINISTRACIÓN",
        "icono": "📅",
        "badge": "Agenda",
        "color": "#EA580C",
        "color_bg": "#FFF7ED",
        "desc": "Programación mensual, sesiones de CTE, visitas escolares y fechas límite.",
        "tags": ["CTE", "Fechas Límite", "Cronología"],
    },
    "Trámites": {
        "titulo": "Trámites y Solicitudes",
        "categoria": "ADMINISTRACIÓN",
        "icono": "📝",
        "badge": "Gestión",
        "color": "#0891B2",
        "color_bg": "#ECFEFF",
        "desc": "Movimientos de matrícula, solicitudes de baja y traslado de expedientes.",
        "tags": ["Altas y Bajas", "Traslados", "Gestión Escolar"],
    },
    "Cronograma mensual": {
        "titulo": "Cronograma de Especialistas",
        "categoria": "ADMINISTRACIÓN",
        "icono": "⏱️",
        "badge": "Organización",
        "color": "#4F46E5",
        "color_bg": "#EEF2FF",
        "desc": "Programación de visitas de Psicología, Comunicación y Trabajo Social.",
        "tags": ["Psicología", "Comunicación", "Trabajo Social"],
    },
    "Horarios de apoyo": {
        "titulo": "Horarios y Avisos de Apoyo",
        "categoria": "ADMINISTRACIÓN",
        "icono": "⏰",
        "badge": "Docencia",
        "color": "#0D9488",
        "color_bg": "#F0FDFA",
        "desc": "Distribución semanal de atención en escuelas primarias y avisos directos.",
        "tags": ["Atención en Escuelas", "Avisos"],
    },
    "Panel de Dirección": {
        "titulo": "Panel de Dirección",
        "categoria": "ADMINISTRACIÓN",
        "icono": "🏢",
        "badge": "Supervisión",
        "color": "#0F172A",
        "color_bg": "#F8FAFC",
        "desc": "Consola directiva: supervisión de planeaciones, oficios y seguimiento.",
        "tags": ["Supervisión", "Revisión General", "Control"],
    },
    "Maestros de primaria": {
        "titulo": "Directorio de Maestros Regulares",
        "categoria": "ADMINISTRACIÓN",
        "icono": "🏫",
        "badge": "Directorio",
        "color": "#D97706",
        "color_bg": "#FFFBEB",
        "desc": "Docentes regulares de las 7 escuelas primarias atendidas por grado y grupo.",
        "tags": ["7 Primarias", "Directorio Docente"],
    },
    "Novedades de supervisión": {
        "titulo": "Novedades de Supervisión",
        "categoria": "ADMINISTRACIÓN",
        "icono": "🔔",
        "badge": "Zona 001",
        "color": "#DC2626",
        "color_bg": "#FEF2F2",
        "desc": "Avisos de inspección, lineamientos pedagógicos y comunicaciones de ATP.",
        "tags": ["Zona 001", "ATP", "Circulares"],
    },
    "Constancias de visita": {
        "titulo": "Constancias de Visita",
        "categoria": "ADMINISTRACIÓN",
        "icono": "📜",
        "badge": "Acompañamiento",
        "color": "#059669",
        "color_bg": "#ECFDF5",
        "desc": "Generación y firmado de constancias de visita y acompañamiento técnico.",
        "tags": ["Acompañamiento", "Firmas"],
    },
    "Alta de alumnos": {
        "titulo": "Alta de Alumnos",
        "categoria": "ADMINISTRACIÓN",
        "icono": "👤➕",
        "badge": "Padrón",
        "color": "#2563EB",
        "color_bg": "#EFF6FF",
        "desc": "Registro formal de nuevos alumnos en el padrón activo de USAER 02-E.",
        "tags": ["Nuevo Ingreso", "Padrón Activo"],
    },
    "Oficios de comisión": {
        "titulo": "Oficios de Comisión",
        "categoria": "ADMINISTRACIÓN",
        "icono": "📑",
        "badge": "Oficios",
        "color": "#475569",
        "color_bg": "#F1F5F9",
        "desc": "Generación ágil y resguardo oficial de oficios de comisión de servicio.",
        "tags": ["Comisiones", "Resguardo"],
    },
}


def _ir_a_modulo(modulo):
    st.session_state["navegacion_principal"] = modulo


def render_hub_card(modulo_key):
    """Renderiza una tarjeta táctil unificada con vista previa al pasar el cursor."""
    info = MODULOS_INFO.get(modulo_key, {
        "titulo": modulo_key,
        "icono": "◈",
        "badge": "Módulo",
        "color": "#0F4C5C",
        "color_bg": "#E6F4F7",
        "desc": "Accede a las herramientas de este apartado.",
        "tags": ["Acceso Directo"],
    })

    chips_html = "".join(f'<span class="hub-chip">{tag}</span>' for tag in info.get("tags", []))

    with st.container(border=True, key=f"hub_card_{modulo_key}"):
        st.markdown(
            f"""
            <div class="hub-tile-header">
                <div class="hub-tile-icon" style="background-color: {info['color_bg']}; color: {info['color']};">
                    {info['icono']}
                </div>
                <span class="hub-tile-badge">{info['badge']}</span>
            </div>
            <div class="hub-tile-title">{info['titulo']}</div>
            <div class="hub-tile-desc">{info['desc']}</div>
            <div class="hub-preview-chips">
                {chips_html}
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.button(
            f"Entrar a {info['titulo']} →",
            key=f"hub_goto_{modulo_key}",
            on_click=_ir_a_modulo,
            args=(modulo_key,),
            width='stretch',
        )


def pagina_central_hub(df_alumnos, menu_permitido, rol, nombre_usuario):
    from services.navegacion_planeaciones import habilitada
    if 'Planeación e intervención' in menu_permitido and habilitada() and not st.session_state.get('_navegacion_documentos_anterior'):
        from ui.mis_planeaciones import inicio
        inicio()
        otros=st.expander('Todos los módulos',key='inicio_todos_modulos',on_change='rerun')
        if otros.open:
            with otros:_pagina_modulos(df_alumnos,menu_permitido,rol,nombre_usuario)
        return
    _pagina_modulos(df_alumnos,menu_permitido,rol,nombre_usuario)


def _pagina_modulos(df_alumnos, menu_permitido, rol, nombre_usuario):
    """Página Central / Launchpad: Centro de navegación fluido y visual."""
    total_alumnos = len(df_alumnos) if df_alumnos is not None else 0

    # Hero Banner Central con identidad institucional
    st.markdown(
        f"""
        <div class="hub-hero">
            <div class="hub-hero-badge">Centro de Control · USAER 02-E · Zona 001</div>
            <h1>Espacio Central de Trabajo</h1>
            <p>Pasa el cursor sobre cualquier módulo para previsualizarlo o utiliza el dock rápido para ingresar de inmediato.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 1. DOCK INTERACTIVO DE ACCESOS RÁPIDOS (Floating Dock)
    dock_destacados = [m for m in ["Expedientes", "Planeación e intervención", "Anexo III BAP", "Anexo IV Hoja de sugerencias", "Anexo V Eventos significativos", "EPP", "Calendario de actividades", "Estadística"] if m in menu_permitido]
    if dock_destacados:
        st.markdown("<div style='text-align:center;font-size:0.75rem;font-weight:750;letter-spacing:0.08em;text-transform:uppercase;color:var(--bs-muted-color);margin-bottom:0.4rem;'>⚡ Accesos Rápidos Frecuentes</div>", unsafe_allow_html=True)
        cols_dock = st.columns(len(dock_destacados))
        for idx, mod in enumerate(dock_destacados):
            info = MODULOS_INFO.get(mod, {"icono": "◈", "titulo": mod})
            with cols_dock[idx]:
                if st.button(
                    f"{info['icono']}\n{info['titulo'].split('·')[-1].strip()[:14]}",
                    key=f"hub_dock_btn_{mod}",
                    help=f"{info['titulo']}: {info.get('desc', '')}",
                    on_click=_ir_a_modulo,
                    args=(mod,),
                    width='stretch',
                ):
                    pass

    st.write("")

    # 2. FILTRADO ÁGIL: CATEGORÍAS & BUSCADOR INMEDIATO
    c_cat, c_busc = st.columns([6.8, 3.2])
    with c_cat:
        categoria_tab = st.pills(
            "Categoría",
            ["🌟 Todos", "📁 Alumnado", "🛡️ Anexos Oficiales", "🎯 Planeación y EPP", "📊 Gestión y Tiempos"],
            default="🌟 Todos",
            label_visibility="collapsed",
            key="hub_cat_pills",
        )
    with c_busc:
        busqueda = st.text_input(
            "Buscar módulo...",
            placeholder="🔍 Buscar módulo o formato...",
            label_visibility="collapsed",
            key="hub_search_input",
        ).strip().lower()

    # Mapeo de módulos a categorías
    categorias_map = {
        "📁 Alumnado": {"Expedientes", "Alta de alumnos"},
        "🛡️ Anexos Oficiales": {"Anexo III BAP", "Anexo IV Hoja de sugerencias", "Anexo V Eventos significativos", "Anexo VII Derivación"},
        "🎯 Planeación y EPP": {"Planeación e intervención", "EPP", "Metas personales", "Juntas académicas"},
        "📊 Gestión y Tiempos": {"Estadística", "Documentos", "Calendario de actividades", "Trámites", "Cronograma mensual", "Horarios de apoyo", "Panel de Dirección", "Maestros de primaria", "Novedades de supervisión", "Constancias de visita", "Oficios de comisión"},
    }

    # Filtrar módulos según categoría y búsqueda
    modulos_visibles = [m for m in menu_permitido if m in MODULOS_INFO and m != "Inicio"]

    if categoria_tab and categoria_tab != "🌟 Todos":
        permitidos_cat = categorias_map.get(categoria_tab, set())
        modulos_visibles = [m for m in modulos_visibles if m in permitidos_cat]

    if busqueda:
        modulos_visibles = [
            m for m in modulos_visibles
            if busqueda in MODULOS_INFO[m]["titulo"].lower()
            or busqueda in MODULOS_INFO[m]["desc"].lower()
            or any(busqueda in tag.lower() for tag in MODULOS_INFO[m].get("tags", []))
        ]

    # 3. REJILLA FLUIDA DE TARJETAS UNIFICADAS
    if not modulos_visibles:
        st.info(f"No se encontraron módulos coincidentes con «{busqueda}». Intenta con otra búsqueda.")
    else:
        for i in range(0, len(modulos_visibles), 3):
            fila = modulos_visibles[i:i+3]
            cols = st.columns(3)
            for j, mod in enumerate(fila):
                with cols[j]:
                    render_hub_card(mod)

    # 4. INSTRUMENTO EXTERNO OFICIAL (Suite TEA)
    if not categoria_tab or categoria_tab in ("🌟 Todos", "🎯 Planeación y EPP"):
        st.markdown("<div class='hub-section-title'><span>🧩</span> EVALUACIÓN PSICOMÉTRICA ESPECIALIZADA</div>", unsafe_allow_html=True)
        c_tea1, c_tea2 = st.columns([3.8, 1.2])
        with c_tea1:
            st.markdown(
                """
                <div class="hub-tile" style="margin-bottom:0;">
                    <div class="hub-tile-header">
                        <div class="hub-tile-icon" style="background-color: #FFFBEB; color: #D97706;">◈</div>
                        <span class="hub-tile-badge">Psicología y Educación Especial</span>
                    </div>
                    <div class="hub-tile-title">Suite Psicométrica TEA (M-CHAT-R/F™ & Protocolo USAER)</div>
                    <div class="hub-tile-desc">Herramienta digital especializada de cribado y baremación automática con informe clínico oficial listo para anexar.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c_tea2:
            st.write("")
            st.link_button("Abrir Suite TEA ◈", "https://deeply-howler-8m5y7.ship.place/", type="primary", width='stretch')

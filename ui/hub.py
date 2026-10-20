"""Centro de Control Central (Hub / Launchpad) para USAER 02-E.

Proporciona una experiencia de navegación fluida, táctil y de alta gama,
permitiendo acceder a todos los módulos educativos y administrativos
desde un único panel visual sin fricciones.
"""
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
    },
    "Anexo III BAP": {
        "titulo": "Anexo III · Barreras (BAP)",
        "categoria": "ANEXOS",
        "icono": "🛡️",
        "badge": "Inclusión",
        "color": "#D97706",
        "color_bg": "#FFFBEB",
        "desc": "Detección oficial de barreras, recursos y apoyos específicos requeridos.",
    },
    "Anexo IV Hoja de sugerencias": {
        "titulo": "Anexo IV · Sugerencias",
        "categoria": "ANEXOS",
        "icono": "💡",
        "badge": "Pedagógico",
        "color": "#0D9488",
        "color_bg": "#F0FDFA",
        "desc": "Recomendaciones prácticas dirigidas a docentes regulares y familia.",
    },
    "Anexo V Eventos significativos": {
        "titulo": "Anexo V · Eventos",
        "categoria": "ANEXOS",
        "icono": "📌",
        "badge": "Bitácora",
        "color": "#2563EB",
        "color_bg": "#EFF6FF",
        "desc": "Registro cronológico de acuerdos, entrevistas y situaciones relevantes.",
    },
    "Anexo VII Derivación": {
        "titulo": "Anexo VII · Derivación",
        "categoria": "ANEXOS",
        "icono": "↗️",
        "badge": "Canalización",
        "color": "#7C3AED",
        "color_bg": "#F5F3FF",
        "desc": "Formato oficial para la derivación y canalización de alumnos.",
    },
    "Planeación e intervención": {
        "titulo": "Planeación e Intervención",
        "categoria": "ADMINISTRACIÓN",
        "icono": "🎯",
        "badge": "Intervención",
        "color": "#0D9488",
        "color_bg": "#F0FDFA",
        "desc": "Diseño de planeaciones colaborativas, ajustes razonables y seguimiento formativo.",
    },
    "EPP": {
        "titulo": "Evaluación Psicopedagógica",
        "categoria": "ADMINISTRACIÓN",
        "icono": "📋",
        "badge": "Diagnóstico",
        "color": "#0284C7",
        "color_bg": "#F0F9FF",
        "desc": "Informes de evaluación multidisciplinaria y determinación de apoyos.",
    },
    "Estadística": {
        "titulo": "Estadística y Listado Nominal",
        "categoria": "ADMINISTRACIÓN",
        "icono": "📊",
        "badge": "Métricas",
        "color": "#059669",
        "color_bg": "#ECFDF5",
        "desc": "Distribución por escuela, grado, condición y exportación de reportes.",
    },
    "Documentos": {
        "titulo": "Documentos Oficiales",
        "categoria": "ADMINISTRACIÓN",
        "icono": "📄",
        "badge": "Formatos",
        "color": "#475569",
        "color_bg": "#F1F5F9",
        "desc": "Biblioteca de formatos normativos, manuales y circulares de USAER.",
    },
    "Calendario de actividades": {
        "titulo": "Calendario de Actividades",
        "categoria": "ADMINISTRACIÓN",
        "icono": "📅",
        "badge": "Agenda",
        "color": "#EA580C",
        "color_bg": "#FFF7ED",
        "desc": "Programación mensual, sesiones de CTE, visitas escolares y fechas límite.",
    },
    "Trámites": {
        "titulo": "Trámites y Solicitudes",
        "categoria": "ADMINISTRACIÓN",
        "icono": "📝",
        "badge": "Gestión",
        "color": "#0891B2",
        "color_bg": "#ECFEFF",
        "desc": "Movimientos de matrícula, solicitudes de baja y traslado de expedientes.",
    },
    "Cronograma mensual": {
        "titulo": "Cronograma de Especialistas",
        "categoria": "ADMINISTRACIÓN",
        "icono": "⏱️",
        "badge": "Organización",
        "color": "#4F46E5",
        "color_bg": "#EEF2FF",
        "desc": "Programación de visitas de Psicología, Comunicación y Trabajo Social.",
    },
    "Horarios de apoyo": {
        "titulo": "Horarios y Avisos de Apoyo",
        "categoria": "ADMINISTRACIÓN",
        "icono": "⏰",
        "badge": "Docencia",
        "color": "#0D9488",
        "color_bg": "#F0FDFA",
        "desc": "Distribución semanal de atención en escuelas primarias y avisos directos.",
    },
    "Panel de Dirección": {
        "titulo": "Panel de Dirección",
        "categoria": "ADMINISTRACIÓN",
        "icono": "🏢",
        "badge": "Supervisión",
        "color": "#0F172A",
        "color_bg": "#F8FAFC",
        "desc": "Consola directiva: supervisión de planeaciones, oficios y seguimiento.",
    },
    "Maestros de primaria": {
        "titulo": "Directorio de Maestros Regulares",
        "categoria": "ADMINISTRACIÓN",
        "icono": "🏫",
        "badge": "Directorio",
        "color": "#D97706",
        "color_bg": "#FFFBEB",
        "desc": "Docentes regulares de las 7 escuelas primarias atendidas por grado y grupo.",
    },
    "Novedades de supervisión": {
        "titulo": "Novedades de Supervisión",
        "categoria": "ADMINISTRACIÓN",
        "icono": "🔔",
        "badge": "Zona 001",
        "color": "#DC2626",
        "color_bg": "#FEF2F2",
        "desc": "Avisos de inspección, lineamientos pedagógicos y comunicaciones de ATP.",
    },
    "Constancias de visita": {
        "titulo": "Constancias de Visita",
        "categoria": "ADMINISTRACIÓN",
        "icono": "📜",
        "badge": "Acompañamiento",
        "color": "#059669",
        "color_bg": "#ECFDF5",
        "desc": "Generación y firmado de constancias de visita y acompañamiento técnico.",
    },
    "Alta de alumnos": {
        "titulo": "Alta de Alumnos",
        "categoria": "ADMINISTRACIÓN",
        "icono": "👤➕",
        "badge": "Padrón",
        "color": "#2563EB",
        "color_bg": "#EFF6FF",
        "desc": "Registro formal de nuevos alumnos en el padrón activo de USAER 02-E.",
    },
    "Oficios de comisión": {
        "titulo": "Oficios de Comisión",
        "categoria": "ADMINISTRACIÓN",
        "icono": "📑",
        "badge": "Oficios",
        "color": "#475569",
        "color_bg": "#F1F5F9",
        "desc": "Generación ágil y resguardo oficial de oficios de comisión de servicio.",
    },
}


def _ir_a_modulo(modulo):
    st.session_state["navegacion_principal"] = modulo


def render_hub_card(modulo_key):
    """Renderiza una tarjeta táctil interactiva para un módulo."""
    info = MODULOS_INFO.get(modulo_key, {
        "titulo": modulo_key,
        "icono": "◈",
        "badge": "Módulo",
        "color": "#0F4C5C",
        "color_bg": "#E6F4F7",
        "desc": "Accede a las herramientas de este apartado.",
    })

    st.markdown(
        f"""
        <div class="hub-tile">
            <div class="hub-tile-header">
                <div class="hub-tile-icon" style="background-color: {info['color_bg']}; color: {info['color']};">
                    {info['icono']}
                </div>
                <span class="hub-tile-badge">{info['badge']}</span>
            </div>
            <div class="hub-tile-title">{info['titulo']}</div>
            <div class="hub-tile-desc">{info['desc']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.button(
        f"Abrir {info['titulo']} →",
        key=f"hub_goto_{modulo_key}",
        on_click=_ir_a_modulo,
        args=(modulo_key,),
        use_container_width=True,
    )


def pagina_central_hub(df_alumnos, menu_permitido, rol, nombre_usuario):
    """Página Central / Launchpad: Centro de navegación fluido y visual."""
    total_alumnos = len(df_alumnos) if df_alumnos is not None else 0

    # Hero Banner Central con identidad institucional y métricas de un vistazo
    st.markdown(
        f"""
        <div class="hub-hero">
            <div class="hub-hero-badge">Centro de Control · USAER 02-E · Zona 001</div>
            <h1>Bienvenido al Espacio Central</h1>
            <p>Selecciona cualquier módulo para comenzar a trabajar. La información se encuentra conectada: capturar una vez, reutilizar siempre.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Métricas de pulso rápido
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(
            f"""
            <div class="hub-metric-card">
                <div class="hub-metric-num">{total_alumnos}</div>
                <div class="hub-metric-label">Alumnos en tu Ámbito</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with m2:
        num_a3 = len(repo.anexo3()) if hasattr(repo, "anexo3") else 0
        st.markdown(
            f"""
            <div class="hub-metric-card">
                <div class="hub-metric-num">{num_a3}</div>
                <div class="hub-metric-label">Instrumentos BAP</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with m3:
        num_a4 = len(repo.anexo4()) if hasattr(repo, "anexo4") else 0
        st.markdown(
            f"""
            <div class="hub-metric-card">
                <div class="hub-metric-num">{num_a4}</div>
                <div class="hub-metric-label">Hojas de Sugerencias</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with m4:
        num_a5 = len(repo.anexo5()) if hasattr(repo, "anexo5") else 0
        st.markdown(
            f"""
            <div class="hub-metric-card">
                <div class="hub-metric-num">{num_a5}</div>
                <div class="hub-metric-label">Eventos Significativos</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.write("")

    # 1. BLOQUE GENERAL
    items_general = [m for m in ["Expedientes"] if m in menu_permitido]
    if items_general:
        st.markdown("<div class='hub-section-title'><span>📁</span> EXPEDIENTES Y ALUMNADO</div>", unsafe_allow_html=True)
        cols_gen = st.columns(max(len(items_general), 1))
        for idx, mod in enumerate(items_general):
            with cols_gen[idx]:
                render_hub_card(mod)

    # 2. BLOQUE ANEXOS
    items_anexos = [m for m in ["Anexo III BAP", "Anexo IV Hoja de sugerencias", "Anexo V Eventos significativos", "Anexo VII Derivación"] if m in menu_permitido]
    if items_anexos:
        st.markdown("<div class='hub-section-title'><span>🛡️</span> ANEXOS OFICIALES E INTERVENCIÓN</div>", unsafe_allow_html=True)
        # Rejilla fluida de 3 columnas
        for i in range(0, len(items_anexos), 3):
            fila = items_anexos[i:i+3]
            cols = st.columns(3)
            for j, mod in enumerate(fila):
                with cols[j]:
                    render_hub_card(mod)

    # 3. BLOQUE ADMINISTRACIÓN Y PLANEACIÓN
    items_admin = [m for m in menu_permitido if m not in {"Inicio", "Expedientes", "Anexo III BAP", "Anexo IV Hoja de sugerencias", "Anexo V Eventos significativos", "Anexo VII Derivación"}]
    if items_admin:
        st.markdown("<div class='hub-section-title'><span>📊</span> GESTIÓN, PLANEACIÓN Y SEGUIMIENTO</div>", unsafe_allow_html=True)
        for i in range(0, len(items_admin), 3):
            fila = items_admin[i:i+3]
            cols = st.columns(3)
            for j, mod in enumerate(fila):
                with cols[j]:
                    render_hub_card(mod)

    # 4. INSTRUMENTO EXTERNO OFICIAL (Suite TEA)
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
        st.link_button("Abrir Suite TEA ◈", "https://deeply-howler-8m5y7.ship.place/", type="primary", use_container_width=True)

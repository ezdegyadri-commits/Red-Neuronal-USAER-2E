"""Módulo de navegación lateral (Sidebar) SaaS Premium para USAER 02-E."""
import streamlit as st

TITULOS_SIMPLIFICADOS = {
    "Inicio": "Inicio",
    "Expedientes": "Expedientes",
    "Anexo III BAP": "Anexo III (BAP)",
    "Anexo IV Hoja de sugerencias": "Anexo IV (Sugerencias)",
    "Anexo V Eventos significativos": "Anexo V (Eventos)",
    "Anexo VII Derivación": "Anexo VII (Derivación)",
    "Estadística": "Estadística",
    "Documentos": "Documentos",
    "Calendario de actividades": "Calendario",
    "Trámites": "Trámites",
    "Planeación e intervención": "Planeación e intervención",
    "EPP": "EPP",
    "Cronograma mensual": "Cronograma mensual",
    "Horarios de apoyo": "Horarios de apoyo",
    "Panel de Dirección": "Panel de Dirección",
    "Maestros de primaria": "Maestros de primaria",
    "Novedades de supervisión": "Novedades de supervisión",
    "Constancias de visita": "Constancias de visita",
    "Alta de alumnos": "Alta de alumnos",
    "Oficios de comisión": "Oficios de comisión",
}

ICONOS_MENU = {
    "Inicio": "🏠",
    "Expedientes": "📁",
    "Anexo III BAP": "🛡️",
    "Anexo IV Hoja de sugerencias": "💡",
    "Anexo V Eventos significativos": "📌",
    "Anexo VII Derivación": "↗️",
    "Estadística": "📊",
    "Documentos": "📄",
    "Calendario de actividades": "📅",
    "Trámites": "📝",
    "Planeación e intervención": "🎯",
    "EPP": "📋",
    "Cronograma mensual": "⏱️",
    "Horarios de apoyo": "⏰",
    "Panel de Dirección": "🏢",
    "Maestros de primaria": "🏫",
    "Novedades de supervisión": "🔔",
    "Constancias de visita": "📜",
    "Alta de alumnos": "👤➕",
    "Oficios de comisión": "📑",
}


def obtener_bloques_menu(menu_permitido):
    """Divide el menú de la sesión en los 3 bloques principales requeridos:
    1. GENERAL: Inicio, Expedientes.
    2. ANEXOS: Anexo III (BAP), Anexo IV (Sugerencias), Anexo V (Eventos), Anexo VII (Derivación).
    3. ADMINISTRACIÓN: Estadística, Documentos, Calendario, Trámites y módulos según rol.
    """
    bloques = [
        ("GENERAL", [opc for opc in ["Inicio", "Expedientes"] if opc in menu_permitido]),
        ("ANEXOS", [opc for opc in ["Anexo III BAP", "Anexo IV Hoja de sugerencias", "Anexo V Eventos significativos", "Anexo VII Derivación"] if opc in menu_permitido]),
        ("ADMINISTRACIÓN", [opc for opc in menu_permitido if opc not in {"Inicio", "Expedientes", "Anexo III BAP", "Anexo IV Hoja de sugerencias", "Anexo V Eventos significativos", "Anexo VII Derivación"}]),
    ]
    return bloques


def render_sidebar_navigation(menu_permitido):
    """Renderiza el menú lateral táctil, accesible y categorizado con 0 radio buttons."""
    if "navegacion_principal" not in st.session_state or st.session_state["navegacion_principal"] not in menu_permitido:
        st.session_state["navegacion_principal"] = "Inicio"

    def _navegar_a(apartado_destino):
        st.session_state["navegacion_principal"] = apartado_destino

    pagina_actual = st.session_state["navegacion_principal"]
    bloques = obtener_bloques_menu(menu_permitido)

    for nombre_categoria, items_categoria in bloques:
        if items_categoria:
            st.markdown(f"<div class='nav-category-header'>{nombre_categoria}</div>", unsafe_allow_html=True)
            for item in items_categoria:
                es_activo = (item == pagina_actual)
                ico = ICONOS_MENU.get(item, "◈")
                titulo = TITULOS_SIMPLIFICADOS.get(item, item)
                st.button(
                    f"{ico}  {titulo}",
                    key=f"nav_btn_{item}",
                    on_click=_navegar_a,
                    args=(item,),
                    use_container_width=True,
                    type="primary" if es_activo else "secondary",
                )

    return st.session_state["navegacion_principal"]

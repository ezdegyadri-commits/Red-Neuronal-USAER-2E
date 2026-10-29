"""Cada módulo actualiza su contenido sin reconstruir la cabecera global."""
import streamlit as st
from services.expedientes import alumnos_visibles
from ui.sidebar import titulo_modulo as nombre_modulo


@st.fragment
def mostrar(page,rol,escuelas,menu):
    if st.session_state.get('navegacion_principal')!=page:
        st.rerun(scope='app')
    # No se lee el padrón central en módulos que no lo necesitan.
    if page in {"Expedientes", "Anexo III BAP", "Anexo IV Hoja de sugerencias", "Anexo V Eventos significativos", "Estadística", "Documentos", "Alta de alumnos"}:
        try:
            authorized = alumnos_visibles(rol, escuelas, st.session_state.get("nombre", ""))
        except Exception:
            st.warning('No se pudo completar la consulta del módulo. No se borraron registros. Puedes volver al Centro de Control sin recargar ni cerrar la sesión.')
            if st.button('Volver al Centro de Control',key='carga_volver_inicio'):
                st.session_state['navegacion_principal']='Inicio';st.rerun()
            if st.button('Reintentar consulta',key='carga_reintentar'):st.rerun()
            st.stop()
    else:
        authorized = None

    # Barra superior fluida de retorno hacia el Centro de Control
    def volver_al_inicio():
        st.session_state['navegacion_principal']='Inicio'

    if page != "Inicio":
        c_back, c_bc = st.columns([2.3, 7.7])
        with c_back:
            st.button("← Centro de Control", key="btn_volver_al_hub", use_container_width=True,on_click=volver_al_inicio)
        with c_bc:
            titulo_modulo = nombre_modulo(page)
            st.markdown(
                f"<div class='module-breadcrumb'>"
                f"<span>USAER 02-E</span>"
                f"<span style='color:var(--bs-muted-color);'>›</span>"
                f"<strong>{titulo_modulo}</strong>"
                f"</div>",
                unsafe_allow_html=True,
            )

    if page=="Inicio":
        from ui.hub import pagina_central_hub
        pagina_central_hub(authorized, menu, rol, st.session_state.get("nombre", ""))
    elif page=="Expedientes":
        from ui.pages import expedientes_page
        expedientes_page(authorized)
    elif page=="Anexo III BAP":
        from ui.pages import bap_page
        bap_page(authorized)
    elif page=="Anexo IV Hoja de sugerencias":
        from ui.sugerencias import anexo4_page
        anexo4_page(authorized)
    elif page=="Anexo V Eventos significativos":
        from ui.pages import eventos_page
        eventos_page(authorized)
    elif page=="Estadística":
        from ui.estadisticas import estadisticas_page
        estadisticas_page(authorized)
    elif page=="Documentos":
        from ui.pages import documentos_page
        documentos_page(authorized)
    elif page=="Calendario de actividades":
        from ui.calendario_eventos import calendario_page
        calendario_page()
    elif page=="Cronograma mensual":
        from ui.cronogramas import cronogramas_page
        cronogramas_page()
    elif page=="Horarios de apoyo":
        from ui.horarios_apoyo import horarios_apoyo_page
        horarios_apoyo_page()
    elif page=="Trámites":
        from ui.tramites import tramites_page
        tramites_page()
    elif page=="Planeación e intervención":
        from ui.planeacion import planeacion_page
        planeacion_page()
    elif page=="EPP":
        from ui.epp_acceso import epp_page
        epp_page()
    elif page=="Metas personales":
        from ui.metas_personales import page as metas_page
        metas_page()
    elif page=="Juntas académicas":
        from ui.juntas_academicas import page as juntas_page
        juntas_page()
    elif page=="Novedades de supervisión":
        from ui.novedades_supervision import novedades_page
        novedades_page()
    elif page=="Panel de Dirección":
        from ui.direccion_rapida import direccion_page_rapida
        from ui.horarios_apoyo import horarios_apoyo_direccion
        from ui.direccion_oficios import configuracion_oficios_direccion
        direccion_page_rapida(authorized)
        with st.expander("Novedades de supervisión · ATP"):
            if st.checkbox("Consultar documentos y novedades",key="consultar_novedades_director"):
                from ui.novedades_supervision import novedades_page
                novedades_page()
        with st.expander("Planes de intervención y planeaciones del equipo"):
            if st.checkbox("Consultar entregas y revisar",key="consultar_planeaciones_director"):
                from ui.planeacion import direccion_panel
                direccion_panel()
        horarios_apoyo_direccion()
        st.divider()
        with st.expander("Directorio de Maestros de Grupo (7 Primarias)"):
            from ui.docentes_regulares_form import vista_docentes_regulares_admin
            vista_docentes_regulares_admin()
        st.divider()
        configuracion_oficios_direccion()
        st.divider()
        st.subheader("Cronogramas del equipo")
        st.caption("Desde aquí puedes elaborar tu propio cronograma y consultar los publicados por Psicología, Comunicación y Trabajo Social.")
        if st.button("Mi cronograma y calendarios del equipo", type="primary", key="abrir_cronograma_direccion"):
            st.session_state["mostrar_cronograma_direccion"] = True
        if st.session_state.get("mostrar_cronograma_direccion"):
            if st.button("Cerrar cronogramas", key="cerrar_cronograma_direccion"):
                st.session_state["mostrar_cronograma_direccion"] = False
                st.rerun()
            elaborar, consulta, actividades = st.tabs(["Mi cronograma de Dirección", "Revisar cronogramas del equipo", "Actividades para todos"])
            with consulta:
                from ui.cronogramas import cronogramas_direccion
                cronogramas_direccion()
            with elaborar:
                from ui.cronogramas import cronogramas_page
                cronogramas_page()
            with actividades:
                from ui.calendario_eventos import eventos_direccion
                eventos_direccion()
    elif page=="Maestros de primaria":
        from ui.docentes_regulares_form import vista_docentes_regulares_admin
        vista_docentes_regulares_admin()
    elif page=="Constancias de visita":
        from ui.pages import visitas_page
        visitas_page(authorized)
    elif page=="Alta de alumnos":
        from ui.pages import alta_page
        alta_page(authorized)
    elif page=="Oficios de comisión":
        from ui.oficios import oficios_comision_page
        oficios_comision_page()
    elif page=="Anexo VII Derivación":
        from ui.pages import derivacion_page
        derivacion_page(authorized)

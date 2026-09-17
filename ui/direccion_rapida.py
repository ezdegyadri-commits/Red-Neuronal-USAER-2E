import streamlit as st

from data import repository as repo
from documents.reportes import generar_formato_personal, generar_padron_usaer
from ui.components import hero, card


def direccion_page_rapida(_df=None):
    """Panel directivo ágil: solo consulta datos pesados cuando se solicitan."""
    hero(
        "Panel de Dirección",
        "Consulta indicadores y genera reportes solo cuando los necesites."
    )
    st.success("Panel listo. Los reportes se preparan bajo demanda para responder con rapidez.")

    col_padron, col_personal, col_control = st.columns(3)
    with col_padron:
        if st.button("Preparar padrón de alumnos", use_container_width=True):
            try:
                alumnos = repo.alumnos()
                escuelas = repo.escuelas()
                st.session_state["padron_usaer_archivo"] = generar_padron_usaer(
                    alumnos, escuelas
                )
            except Exception as ex:
                st.error(f"No se pudo preparar el padrón: {ex}")
    with col_personal:
        if st.button("Preparar formato de personal", use_container_width=True):
            try:
                alumnos = repo.alumnos()
                escuelas = repo.escuelas()
                personal = repo.personal()
                asignaciones = repo.asignaciones()
                st.session_state["personal_usaer_archivo"] = generar_formato_personal(
                    personal, escuelas, alumnos, asignaciones
                )
            except Exception as ex:
                st.error(f"No se pudo preparar el formato de personal: {ex}")
    with col_control:
        if st.button("Cargar control de oficios", use_container_width=True):
            try:
                st.session_state["control_oficios_usaer"] = repo.oficios_comision()
            except Exception as ex:
                st.error(f"No fue posible cargar el control: {ex}")

    padron = st.session_state.get("padron_usaer_archivo")
    if padron:
        st.download_button(
            "Descargar padrón USAER",
            data=padron,
            file_name="Padron_USAER_02E_2026_2027.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
        )

    personal = st.session_state.get("personal_usaer_archivo")
    if personal:
        st.download_button(
            "Descargar formato de personal",
            data=personal,
            file_name="Personal_USAER_02E_2026_2027.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
        )

    oficios = st.session_state.get("control_oficios_usaer")
    if oficios is not None:
        st.divider()
        st.markdown("### Control de oficios de comisión")
        if oficios.empty:
            st.info("Aún no se han generado oficios de comisión.")
        else:
            columnas = [
                "Folio", "Fecha_Emision", "Fecha_Comision", "Maestra_Apoyo",
                "Escuela", "Asunto", "Destino", "Horario", "Estado",
            ]
            disponibles = [columna for columna in columnas if columna in oficios.columns]
            control = oficios[disponibles].copy()
            if "Fecha_Emision" in control.columns:
                control = control.sort_values("Fecha_Emision", ascending=False)
            st.dataframe(control, use_container_width=True, hide_index=True)
            st.download_button(
                "Descargar concentrado de oficios (CSV)",
                data=control.to_csv(index=False).encode("utf-8-sig"),
                file_name="Control_oficios_comision_USAER_02E.csv",
                mime="text/csv",
            )

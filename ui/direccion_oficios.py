from datetime import date

import streamlit as st

from data import repository as repo


def configuracion_oficios_direccion():
    st.divider()
    st.markdown("### Configuración de oficios de comisión")
    st.caption(
        "Define una sola vez la fecha, el destino y el horario. Las maestras y "
        "maestros de apoyo únicamente recibirán el enlace de descarga."
    )
    try:
        configuracion = repo.configuracion_oficios_actual()
    except Exception:
        configuracion = {}

    fecha_predefinida = date.today()
    try:
        fecha_predefinida = date.fromisoformat(
            str(configuracion.get("Fecha_Comision", ""))
        )
    except (TypeError, ValueError):
        pass

    asuntos = [
        "COMISIÓN DE SERVICIO",
        "JUNTA ACADÉMICA",
        "REUNIÓN DE TRABAJO",
        "CAPACITACIÓN",
    ]
    asunto_actual = str(configuracion.get("Asunto", "COMISIÓN DE SERVICIO"))
    indice_asunto = asuntos.index(asunto_actual) if asunto_actual in asuntos else 0

    with st.form("configuracion_oficios_direccion"):
        fecha_oficio = st.date_input(
            "Fecha de la comisión", value=fecha_predefinida
        )
        asunto_oficio = st.selectbox("Asunto", asuntos, index=indice_asunto)
        destino_oficio = st.text_input(
            "Destino o actividad de la comisión",
            value=str(configuracion.get("Destino", "")),
        )
        horario_oficio = st.text_input(
            "Horario o indicación",
            value=str(configuracion.get("Horario", "en su horario laboral")),
        )
        guardar = st.form_submit_button(
            "Publicar configuración de oficios", type="primary"
        )

    if guardar:
        if not destino_oficio.strip():
            st.error("Indica el destino o actividad antes de publicar.")
            return
        try:
            repo.guardar_configuracion_oficios({
                "Fecha_Comision": str(fecha_oficio),
                "Asunto": asunto_oficio,
                "Destino": destino_oficio.strip(),
                "Horario": horario_oficio.strip() or "en su horario laboral",
                "Actualizado_Por": st.session_state.get("nombre", ""),
                "Actualizado_En": str(date.today()),
            })
            st.success("Configuración publicada para las maestras y maestros de apoyo.")
        except Exception as ex:
            st.error(f"No fue posible guardar la configuración: {ex}")

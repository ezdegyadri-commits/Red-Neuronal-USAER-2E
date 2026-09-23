from datetime import date
import json

import streamlit as st

from config.settings import ESCUELAS_USAER
from data import repository as repo
from documents.oficios import datos_oficio_escuela, generar_oficio_comision
from services.asignaciones import es_direccion
from utils.text import normalizar_texto


def configuracion_oficios_direccion():
    if not es_direccion(st.session_state.get("rol", "")):
        st.error("La configuración y emisión de oficios está reservada a Dirección.")
        return
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

    st.divider()
    st.markdown("### Generador de oficios de comisión")
    st.caption("La numeración automática inicia en 022. Los folios 001–021 quedan reservados para registrar oficios previos manualmente.")
    try:
        personal = repo.personal().fillna("")
    except Exception as ex:
        personal = None
        st.error(f"No fue posible consultar el directorio de personal: {ex}")

    apoyos = []
    if personal is not None and not personal.empty and "Nombre_Completo" in personal.columns:
        if "Rol" in personal.columns:
            mascara = personal["Rol"].astype(str).map(normalizar_texto).str.contains("APOYO", regex=False)
            apoyos = sorted(
                personal.loc[mascara, "Nombre_Completo"].fillna("").astype(str).str.strip().loc[lambda serie: serie.ne("")].unique().tolist()
            )
    escuelas = list(ESCUELAS_USAER)
    with st.form("director_generador_oficios"):
        modo_folio = st.radio(
            "Asignación del folio",
            ["Automático (desde 022)", "Capturar oficio previo (001–021)"],
            horizontal=True,
            key="dir_oficio_modo_folio",
        )
        folio_manual = None
        if modo_folio == "Capturar oficio previo (001–021)":
            folio_manual = st.number_input(
                "Folio previo", min_value=1, max_value=21, value=1, step=1,
                key="dir_oficio_folio_manual",
            )
        col_personal, col_escuela = st.columns(2)
        with col_personal:
            maestra = (
                st.selectbox("Maestra/o de apoyo", apoyos)
                if apoyos
                else st.text_input("Nombre de la maestra o maestro de apoyo")
            )
        with col_escuela:
            escuela = st.selectbox("Escuela de comisión", escuelas, key="dir_oficio_escuela")
        fecha_comision = st.date_input("Fecha de la comisión", value=date.today(), key="dir_oficio_fecha")
        asunto = st.selectbox(
            "Asunto del oficio",
            ["COMISIÓN DE SERVICIO", "JUNTA ACADÉMICA", "REUNIÓN DE TRABAJO", "CAPACITACIÓN"],
            key="dir_oficio_asunto",
        )
        destino = st.text_input("Destino o actividad", key="dir_oficio_destino")
        horario = st.text_input("Horario o indicación", value="en su horario laboral", key="dir_oficio_horario")
        generar = st.form_submit_button(
            "Registrar oficio previo" if folio_manual is not None else "Generar oficio y asignar folio",
            type="primary", width="stretch",
        )

    if generar:
        st.session_state.pop("oficio_director_actual", None)
        if not str(maestra).strip() or not destino.strip():
            st.error("Indica la persona comisionada y el destino antes de generar el oficio.")
        else:
            clave = json.dumps(
                [str(maestra).strip(), escuela, str(fecha_comision), asunto, destino.strip(), horario.strip()],
                ensure_ascii=False,
            )
            try:
                catalogo = repo.escuelas().fillna("")
                registro_escuela = {}
                codigo = ESCUELAS_USAER.get(escuela, "")
                if not catalogo.empty:
                    for _, fila in catalogo.iterrows():
                        posible = fila.to_dict()
                        if (
                            normalizar_texto(posible.get("Nombre_Escuela", "")) == normalizar_texto(escuela)
                            or normalizar_texto(posible.get("ID_Escuela", "")) == normalizar_texto(codigo)
                        ):
                            registro_escuela = posible
                            break
                datos_escuela = datos_oficio_escuela(escuela, registro_escuela)
                registro = repo.guardar_oficio_comision({
                    "Clave_Operacion": clave,
                    "Fecha_Emision": str(date.today()),
                    "Fecha_Comision": str(fecha_comision),
                    "Escuela": escuela,
                    "ID_Escuela": codigo,
                    "Maestra_Apoyo": str(maestra).strip(),
                    "Director_Escuela": str(datos_escuela.get("Director_Escuela", datos_escuela.get("Director", ""))),
                    "Asunto": asunto,
                    "Destino": destino.strip(),
                    "Horario": horario.strip() or "en su horario laboral",
                    "Estado": "GENERADO",
                }, folio_manual=folio_manual)
                st.session_state["oficio_director_actual"] = registro
            except Exception as ex:
                st.error(f"No fue posible guardar el oficio ni asignar el folio: {ex}")

    registro_actual = st.session_state.get("oficio_director_actual")
    if registro_actual:
        try:
            folio = int(registro_actual.get("Folio", 0) or 0)
            st.success(f"Oficio registrado con folio {folio:03d}.")
            st.download_button(
                f"Descargar oficio PDF · folio {folio:03d}",
                data=generar_oficio_comision(registro_actual),
                file_name=f"Oficio_Comision_{folio:03d}.pdf",
                mime="application/pdf",
                type="primary",
                width="stretch",
                key=f"oficio_director_descargar_{registro_actual.get('ID_Oficio', folio)}",
            )
        except Exception as ex:
            st.error(f"El oficio se guardó, pero no se pudo preparar el PDF: {ex}")

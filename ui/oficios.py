import json
from datetime import date

import pandas as pd
import streamlit as st

from config.settings import ESCUELAS_USAER
from data import repository as repo
from documents.oficios import datos_oficio_escuela, generar_oficio_comision
from services.asignaciones import escuelas_asignadas
from utils.text import normalizar_texto
from ui.components import hero


def oficios_comision_page():
    hero(
        "Oficios de comisión",
        "Descarga el oficio configurado por Dirección para tus escuelas asignadas."
    )
    rol = st.session_state.get("rol", "")
    nombre = st.session_state.get("nombre", "").strip()
    if "APOYO" not in normalizar_texto(rol):
        st.error("Este módulo está disponible únicamente para maestras y maestros de apoyo.")
        return

    escuelas_permitidas = escuelas_asignadas(nombre, rol)
    if not escuelas_permitidas:
        st.error("Tu cuenta no tiene escuelas asignadas para generar oficios.")
        return

    try:
        configuracion = repo.configuracion_oficios_actual()
    except Exception as ex:
        st.error(f"No fue posible consultar la configuración de Dirección: {ex}")
        return
    if not configuracion:
        st.info(
            "Dirección aún no ha definido la fecha, destino y horario de la comisión. "
            "Cuando lo haga, el enlace de descarga aparecerá aquí."
        )
        return

    escuela = st.selectbox("Escuela asignada", escuelas_permitidas, key="oficio_escuela")
    fecha_comision = str(configuracion.get("Fecha_Comision", "")).strip()
    if not fecha_comision:
        st.info("Dirección aún no ha programado la fecha de comisión.")
        return
    st.caption(f"Oficio programado para el {fecha_comision}.")

    try:
        escuelas_catalogo = repo.escuelas().fillna("")
    except Exception:
        escuelas_catalogo = pd.DataFrame()

    datos_catalogo = {}
    if not escuelas_catalogo.empty:
        codigo = ESCUELAS_USAER.get(escuela, "")
        for _, fila in escuelas_catalogo.iterrows():
            datos = fila.to_dict()
            if (
                normalizar_texto(datos.get("Nombre_Escuela", "")) == normalizar_texto(escuela)
                or normalizar_texto(datos.get("ID_Escuela", "")) == normalizar_texto(codigo)
            ):
                datos_catalogo = datos
                break

    datos_escuela = datos_oficio_escuela(escuela, datos_catalogo)
    director = str(
        datos_escuela.get("Director_Escuela")
        or datos_escuela.get("Director")
        or datos_escuela.get("Directora")
        or ""
    ).strip()
    nivel = str(
        datos_escuela.get("Nivel_Escuela") or datos_escuela.get("Nivel") or "primaria"
    ).strip()

    clave = json.dumps(
        [
            nombre, escuela, fecha_comision,
            str(configuracion.get("Asunto", "")),
            str(configuracion.get("Destino", "")),
            str(configuracion.get("Horario", "")),
        ],
        ensure_ascii=False,
    )
    clave_sesion = f"oficio_pdf_{normalizar_texto(nombre)}_{normalizar_texto(escuela)}"
    if st.session_state.get(f"{clave_sesion}_clave") != clave:
        registro_base = {
            "Clave_Operacion": clave,
            "Fecha_Emision": str(date.today()),
            "Fecha_Comision": fecha_comision,
            "Escuela": escuela,
            "ID_Escuela": ESCUELAS_USAER.get(escuela, ""),
            "Maestra_Apoyo": nombre,
            "Director_Escuela": director,
            "Nivel_Escuela": nivel,
            "Asunto": str(configuracion.get("Asunto", "COMISIÓN DE SERVICIO")),
            "Destino": str(configuracion.get("Destino", "")),
            "Horario": str(configuracion.get("Horario", "")),
            "Estado": "GENERADO",
        }
        try:
            registro = repo.guardar_oficio_comision(registro_base)
        except Exception:
            registro = dict(registro_base)
            registro["Folio"] = 0
            st.warning(
                "El oficio está listo para descargar. El registro de seguimiento "
                "se reintentará cuando se restablezca la conexión."
            )
        try:
            st.session_state[clave_sesion] = generar_oficio_comision(registro)
            st.session_state[f"{clave_sesion}_folio"] = registro.get("Folio", 0)
            st.session_state[f"{clave_sesion}_clave"] = clave
        except Exception as ex:
            st.error(f"No fue posible preparar el PDF: {ex}")
            return

    pdf = st.session_state.get(clave_sesion)
    if pdf:
        folio = st.session_state.get(f"{clave_sesion}_folio", 0)
        etiqueta = f"Descargar oficio - {fecha_comision}"
        if folio:
            etiqueta += f" (folio {int(folio):03d})"
        st.download_button(
            etiqueta,
            data=pdf,
            file_name=f"Oficio_Comision_{int(folio):03d}.pdf" if folio else "Oficio_Comision.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True,
        )

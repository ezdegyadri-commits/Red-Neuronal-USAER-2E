import streamlit as st
import pandas as pd

from data import repository as repo
from documents.reportes import generar_formato_personal, generar_padron_usaer
from services.padron_oficial import vista_padron_oficial
from services.alumnos import alumnos_de_escuela
from services.asignaciones import es_direccion, escuelas_asignadas
from ui.components import hero, card
from ui.relatorias import generador_relatorias_director
from utils.text import normalizar_texto


def _control_expedientes_director(df):
    """Vista de control de anexos vinculados; no modifica registros del padrón."""
    st.divider()
    st.markdown("### Control de expedientes · solo Dirección")
    rol = st.session_state.get("rol", "")
    nombre = st.session_state.get("nombre", "")
    if not es_direccion(rol):
        st.error("Este control está reservado a Dirección.")
        return
    escuelas = escuelas_asignadas(nombre, rol)
    if df is None or df.empty or not escuelas:
        st.info("No hay alumnos o escuelas disponibles para el control.")
        return
    escuela = st.selectbox(
        "Escuela para revisar",
        ["Toda la USAER", *escuelas],
        key="control_expedientes_escuela",
    )
    if st.button("Actualizar control de anexos", key="control_expedientes_actualizar"):
        try:
            alumnos = df.copy() if escuela == "Toda la USAER" else alumnos_de_escuela(df, escuela)
            a3, a4, a5 = repo.anexo3(), repo.anexo4(), repo.anexo5()

            def conteo_por_alumno(frame):
                if frame.empty or "ID_Alumno" not in frame.columns:
                    return {}
                registros = frame.copy()
                if "Estado" in registros.columns:
                    estado = registros["Estado"].fillna("").astype(str).str.strip().str.upper()
                    registros = registros.loc[~estado.isin({"ANULADO", "ELIMINADO", "DUPLICADO", "RETIRADO"})]
                ids = registros["ID_Alumno"].fillna("").astype(str).str.strip()
                return ids.loc[ids.ne("")].value_counts().to_dict()

            conteos = [conteo_por_alumno(frame) for frame in (a3, a4, a5)]
            tabla = []
            for fila in alumnos.to_dict("records"):
                ident = str(fila.get("ID_Alumno", "")).strip()
                if not ident:
                    continue
                valores = [int(conteo.get(ident, 0)) for conteo in conteos]
                tabla.append({
                    "Alumno": fila.get("Nombre_Completo", ""),
                    "Grado y grupo": f"{fila.get('Grado', '')} {fila.get('Grupo', '')}".strip(),
                    "Anexo III vinculado": valores[0],
                    "Anexo IV vinculado": valores[1],
                    "Anexo V vinculado": valores[2],
                    "Escuela": fila.get("Nombre_Escuela", escuela),
                })
            st.session_state["control_expedientes_tabla"] = tabla
            st.session_state["control_expedientes_ambito"] = escuela
        except Exception as ex:
            st.error(f"No fue posible actualizar el control de expedientes: {ex}")

    tabla = st.session_state.get("control_expedientes_tabla")
    if tabla is not None and st.session_state.get("control_expedientes_ambito") == escuela:
        st.caption(
            "Conteos de registros activos vinculados directamente por ID_Alumno. "
            "Las capturas grupales sin ID individual no se atribuyen a cada alumno."
        )
        st.dataframe(tabla, hide_index=True, width="stretch")
        st.download_button(
            "Descargar control como CSV",
            data=pd.DataFrame(tabla).to_csv(index=False).encode("utf-8-sig"),
            file_name=f"Control_expedientes_{normalizar_texto(escuela).replace(' ', '_')}.csv",
            mime="text/csv",
            width="stretch",
            key=f"descargar_control_expedientes_{normalizar_texto(escuela)}",
        )


def direccion_page_rapida(_df=None):
    """Panel directivo ágil: solo consulta datos pesados cuando se solicitan."""
    hero(
        "Panel de Dirección",
        "Consulta indicadores y genera reportes solo cuando los necesites."
    )
    st.success("Panel listo. Los reportes se preparan bajo demanda para responder con rapidez.")

    col_padron, col_personal, col_control = st.columns(3)
    with col_padron:
        if st.button("Generar padrón oficial de alumnos USAER", type="primary", width="stretch"):
            try:
                with st.spinner("Leyendo la base central y preparando el padrón oficial..."):
                    alumnos = repo.alumnos()
                    escuelas = repo.escuelas()
                    if alumnos.empty:
                        st.error("La base central no contiene alumnos para el padrón.")
                    else:
                        st.session_state["padron_usaer_archivo"] = generar_padron_usaer(
                            alumnos, escuelas
                        )
                        st.session_state["padron_usaer_vista"] = vista_padron_oficial(
                            alumnos, escuelas
                        )
                        st.session_state["padron_usaer_total"] = len(alumnos)
            except Exception as ex:
                st.error(f"No se pudo generar el padrón oficial: {ex}")
    with col_personal:
        if st.button("Generar formato oficial de personal", type="primary", width="stretch"):
            try:
                st.session_state.pop("personal_usaer_archivo", None)
                st.session_state.pop("personal_usaer_total", None)
                alumnos = repo.alumnos()
                escuelas = repo.escuelas()
                personal = repo.personal_para_formato()
                if personal.empty:
                    st.error(
                        "No hay respuestas en la hoja del formulario de personal "
                        "ni registros en la base central."
                    )
                else:
                    asignaciones = repo.asignaciones()
                    st.session_state["personal_usaer_archivo"] = generar_formato_personal(
                        personal, escuelas, alumnos, asignaciones
                    )
                    st.session_state["personal_usaer_total"] = len(personal)
                    if not personal["Rol"].map(lambda rol: "DIRECTOR" in str(rol).upper()).any():
                        st.warning(
                            "La hoja de respuestas no incluye el registro del Director; "
                            "el formato se generó con los registros disponibles."
                        )
            except Exception as ex:
                st.error(f"No se pudo preparar el formato de personal: {ex}")
    with col_control:
        if st.button("Cargar control de oficios", width="stretch"):
            try:
                st.session_state["control_oficios_usaer"] = repo.oficios_comision()
            except Exception as ex:
                st.error(f"No fue posible cargar el control: {ex}")

    padron = st.session_state.get("padron_usaer_archivo")
    if padron:
        st.markdown("### Padrón oficial que se entregará a la zona")
        st.caption(
            "La vista contiene únicamente los campos del formato oficial; "
            "la información interna de los expedientes se conserva sin cambios."
        )
        st.dataframe(
            st.session_state.get("padron_usaer_vista"),
            use_container_width=True,
            hide_index=True,
        )
        st.download_button(
            "Descargar padrón USAER",
            data=padron,
            file_name="Padron_USAER_02E_2026_2027.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
        )

    personal = st.session_state.get("personal_usaer_archivo")
    if personal:
        st.success(
            f"Formato de personal listo con "
            f"{st.session_state.get('personal_usaer_total', 0)} registros."
        )
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


    generador_relatorias_director()
    _control_expedientes_director(_df)

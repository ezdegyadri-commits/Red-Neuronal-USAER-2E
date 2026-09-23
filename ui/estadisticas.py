"""Estadística descriptiva de alumnos, acotada por asignación y rol."""

import pandas as pd
import streamlit as st

from data import repository as repo
from services.escuelas import indice_escuelas, nombre_escuela_canonico
from services.alumnos import alumnos_de_escuela
from services.asignaciones import es_direccion, es_especialista, escuelas_asignadas
from documents.listados import listado_alumnos_html, listado_alumnos_pdf
from ui.components import hero
from utils.text import normalizar_texto


def _serie(frame, column, missing="(Sin dato)"):
    if column not in frame.columns:
        return pd.Series([missing] * len(frame), index=frame.index, dtype="object")
    values = frame[column].fillna("").astype(str).str.strip()
    return values.mask(values.eq(""), missing)


def _tabla_frecuencias(values, total):
    counts = values.value_counts(dropna=False).rename_axis("Categoría").reset_index(name="Alumnos")
    if not counts.empty:
        counts["Porcentaje"] = (counts["Alumnos"] / max(total, 1) * 100).round(1)
    return counts


def _show_distribution(frame, column, title, total):
    st.markdown(f"#### {title}")
    frequencies = _tabla_frecuencias(_serie(frame, column), total)
    if frequencies.empty:
        st.info("Sin datos para este apartado.")
        return
    st.dataframe(frequencies, hide_index=True, use_container_width=True)
    st.bar_chart(frequencies.set_index("Categoría")[["Alumnos"]])


def estadisticas_page(df):
    hero(
        "Estadística de alumnos",
        "Indicadores descriptivos calculados sobre los alumnos visibles según tu función y las escuelas asignadas.",
    )
    nombre = st.session_state.get("nombre", "")
    rol = st.session_state.get("rol", "")
    asignadas = escuelas_asignadas(nombre, rol)
    if not asignadas:
        st.error("No se encontraron escuelas asignadas a tu cuenta; por seguridad no se muestran estadísticas.")
        return
    if df is None or df.empty:
        st.info("No hay alumnos disponibles en tu ámbito de acceso.")
        return

    if es_direccion(rol):
        opciones = ["Toda la USAER", *asignadas]
        seleccion = st.selectbox("Ámbito", opciones, key="estadisticas_ambito")
        muestra = df.copy() if seleccion == "Toda la USAER" else alumnos_de_escuela(df, seleccion)
    else:
        seleccion = st.selectbox("Escuela asignada", asignadas, key="estadisticas_ambito")
        muestra = alumnos_de_escuela(df, seleccion)
    if "ID_Alumno" in muestra.columns:
        muestra = muestra.drop_duplicates(subset=["ID_Alumno"], keep="first")
    total = len(muestra)
    if not total:
        st.info("No hay alumnos en el ámbito seleccionado.")
        return

    sexo = _serie(muestra, "Sexo", "").map(normalizar_texto)
    hombres = int(sexo.isin({"H", "HOMBRE", "MASCULINO"}).sum())
    mujeres = int(sexo.isin({"M", "MUJER", "FEMENINO", "F"}).sum())
    edades = pd.to_numeric(muestra.get("Edad_1_Septiembre", pd.Series(index=muestra.index, dtype="object")), errors="coerce")
    edades_validas = edades.dropna()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Alumnos", total)
    c2.metric("Hombres", f"{hombres} ({hombres / total:.0%})")
    c3.metric("Mujeres", f"{mujeres} ({mujeres / total:.0%})")
    c4.metric("Sexo sin dato", int(total - hombres - mujeres))
    a1, a2, a3 = st.columns(3)
    a1.metric("Edad promedio", f"{edades_validas.mean():.1f}" if not edades_validas.empty else "Sin dato")
    a2.metric("Edad mínima", int(edades_validas.min()) if not edades_validas.empty else "Sin dato")
    a3.metric("Edad máxima", int(edades_validas.max()) if not edades_validas.empty else "Sin dato")
    st.caption(f"Ámbito: {seleccion}. Las edades registradas corresponden al corte del 1 de septiembre indicado en el padrón.")

    st.markdown("### Listado nominal para impresión")
    st.caption(
        "El listado incluye nombre, edad, condición y grado. Las maestras ven "
        "su escuela; el equipo especialista puede elegir una de sus escuelas asignadas."
    )
    listado = muestra.copy()
    if es_especialista(rol):
        funcion_filtro = st.selectbox(
            "Filtrar alumnos por función especialista registrada",
            ["Toda la escuela", "Psicología", "Comunicación", "Trabajo Social"],
            key=f"listado_funcion_{normalizar_texto(seleccion)}",
        )
        if funcion_filtro != "Toda la escuela":
            registros_sugerencias = repo.anexo4()
            ids_funcion = set()
            if (
                not registros_sugerencias.empty
                and {"ID_Alumno", "Sugerencias_Area"}.issubset(registros_sugerencias.columns)
            ):
                area = registros_sugerencias["Sugerencias_Area"].fillna("").astype(str).map(normalizar_texto)
                token_funcion = normalizar_texto(funcion_filtro)
                ids_funcion = set(
                    registros_sugerencias.loc[
                        area.str.contains(token_funcion, regex=False, na=False), "ID_Alumno"
                    ].fillna("").astype(str).str.strip()
                ) - {""}
            listado = listado.loc[
                listado.get("ID_Alumno", pd.Series(index=listado.index, dtype="object"))
                .fillna("").astype(str).str.strip().isin(ids_funcion)
            ].copy()
            st.caption(
                "El filtro muestra alumnos con una anotación de Anexo IV vinculada "
                "directamente y clasificada en esa función; no sustituye el padrón "
                "completo de la escuela ni incluye anotaciones grupales sin ID de alumno."
            )

    firma_nombre = (
        nombre
        if "APOYO" in normalizar_texto(rol)
        else ""
    )
    if listado.empty:
        st.info("No hay alumnos en el filtro de función seleccionado.")
    vista_listado = listado_alumnos_html(listado, seleccion, firma_nombre)
    with st.expander("Vista previa del formato oficial", expanded=True):
        st.html(vista_listado)
    st.download_button(
        "Descargar listado nominal en PDF carta",
        data=listado_alumnos_pdf(listado, seleccion, firma_nombre),
        file_name="Listado_nominal_USAER.pdf",
        mime="application/pdf",
        width="stretch",
        key=f"listado_nominal_pdf_{normalizar_texto(seleccion)}",
    )
    with st.expander("Editar o actualizar datos de un alumno"):
        st.caption(
            "Los cambios se guardan en la base central y se reflejan en los demás "
            "procesos. Por seguridad, aquí solo puedes seleccionar alumnos de tu ámbito; "
            "la escuela y las asignaciones de personal se administran por separado."
        )
        alumnos_editables = listado[
            listado.get("ID_Alumno", pd.Series(index=listado.index, dtype="object"))
            .fillna("").astype(str).str.strip().ne("")
        ].copy()
        if alumnos_editables.empty:
            st.info("No hay alumnos con identificador central disponibles para editar.")
        else:
            alumnos_editables = alumnos_editables.drop_duplicates("ID_Alumno", keep="first")
            ids_editables = alumnos_editables["ID_Alumno"].astype(str).tolist()
            fila_por_id = {
                str(row["ID_Alumno"]): row
                for row in alumnos_editables.to_dict("records")
            }
            id_edicion = st.selectbox(
                "Alumno",
                ids_editables,
                format_func=lambda alumno_id: (
                    f"{fila_por_id[alumno_id].get('Nombre_Completo', 'Sin nombre')} · {alumno_id}"
                ),
                key=f"alumno_a_editar_{normalizar_texto(seleccion)}",
            )
            actual = fila_por_id[id_edicion]
            campos = [
                ("Nombre_Completo", "Nombre completo"),
                ("CURP", "CURP"),
                ("Edad_1_Septiembre", "Edad al 1 de septiembre"),
                ("Sexo", "Sexo"),
                ("Situacion_Alumno", "Situación del alumno"),
                ("Nivel_Educativo", "Nivel educativo"),
                ("Grado", "Grado"),
                ("Grupo", "Grupo"),
                ("Condicion_Discapacidad", "Discapacidad o condición"),
                ("Estatus", "Estatus del expediente"),
                ("Tipo_Atencion", "Tipo de atención"),
                ("Lengua_Indigena_Mayahablante", "Lengua indígena / maya hablante"),
                ("Afrodescendiente", "Afrodescendiente"),
                ("Migrante", "Migrante"),
                ("Condiciones_Adicionales", "Condiciones adicionales"),
            ]
            with st.form(f"editar_alumno_{id_edicion}"):
                valores = {}
                columnas = st.columns(2)
                for indice, (campo, etiqueta) in enumerate(campos):
                    valor = actual.get(campo, "")
                    valor = "" if pd.isna(valor) else str(valor)
                    with columnas[indice % 2]:
                        valores[campo] = st.text_input(etiqueta, value=valor, key=f"edicion_{id_edicion}_{campo}")
                guardar = st.form_submit_button("Guardar cambios en la base central", type="primary", width="stretch")
            if guardar:
                valores["Nombre_Completo"] = valores["Nombre_Completo"].strip()
                edad = valores["Edad_1_Septiembre"].strip()
                if not valores["Nombre_Completo"]:
                    st.error("El nombre del alumno no puede quedar vacío.")
                elif edad and not edad.isdigit():
                    st.error("La edad debe ser un número entero o quedar vacía.")
                else:
                    if edad:
                        valores["Edad_1_Septiembre"] = int(edad)
                    try:
                        from data import repository as repo
                        repo.update_alumno(id_edicion, valores, ids_editables)
                        st.success("Datos actualizados en la base central. Se recargará la información de la plataforma.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"No se pudo actualizar el alumno: {exc}")

    st.markdown("### Distribuciones")
    left, right = st.columns(2)
    with left:
        _show_distribution(muestra, "Sexo", "Sexo registrado", total)
        _show_distribution(muestra, "Condicion_Discapacidad", "Discapacidad o condición", total)
        _show_distribution(muestra, "Tipo_Atencion", "Tipo de atención", total)
        _show_distribution(muestra, "Situacion_Alumno", "Situación del alumno", total)
    with right:
        _show_distribution(muestra, "Nivel_Educativo", "Nivel educativo", total)
        _show_distribution(muestra, "Grado", "Grado", total)
        _show_distribution(muestra, "Grupo", "Grupo", total)
        _show_distribution(muestra, "Estatus", "Estatus del expediente", total)

    if seleccion == "Toda la USAER" and es_direccion(rol):
        st.markdown("### Alumnos por escuela")
        school_index = indice_escuelas(alumnos=muestra)
        escuela_values = pd.Series(
            [
                nombre_escuela_canonico(
                    row.get("Nombre_Escuela", ""),
                    row.get("ID_Escuela", ""),
                    row.get("CCT_Escuela", ""),
                    school_index,
                )
                for row in muestra.to_dict("records")
            ],
            index=muestra.index,
            dtype="object",
        ).replace("", "(Sin dato)")
        escuelas = _tabla_frecuencias(escuela_values, total)
        st.dataframe(escuelas, hide_index=True, use_container_width=True)
        st.bar_chart(escuelas.set_index("Categoría")[["Alumnos"]])

    st.markdown("### Edad")
    edades_frame = pd.DataFrame({"Edad": edades_validas.astype(int)})
    if edades_frame.empty:
        st.info("No hay edades capturadas para elaborar la distribución.")
    else:
        edad_frecuencias = _tabla_frecuencias(edades_frame["Edad"].astype(str), total)
        st.dataframe(edad_frecuencias, hide_index=True, use_container_width=True)
        st.bar_chart(edad_frecuencias.set_index("Categoría")[["Alumnos"]])

    st.markdown("### Condiciones adicionales reportadas")
    if "Condiciones_Adicionales" in muestra.columns:
        adicionales = muestra["Condiciones_Adicionales"].fillna("").astype(str).str.strip()
        adicionales = adicionales[adicionales.ne("")]
        if adicionales.empty:
            st.info("No hay condiciones adicionales capturadas.")
        else:
            st.dataframe(_tabla_frecuencias(adicionales, total), hide_index=True, use_container_width=True)
    else:
        st.info("La base central aún no tiene el campo de condiciones adicionales.")

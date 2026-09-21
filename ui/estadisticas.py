"""Estadística descriptiva de alumnos, acotada por asignación y rol."""

import pandas as pd
import streamlit as st

from services.escuelas import indice_escuelas, nombre_escuela_canonico
from services.alumnos import alumnos_de_escuela
from services.asignaciones import es_direccion, escuelas_asignadas
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

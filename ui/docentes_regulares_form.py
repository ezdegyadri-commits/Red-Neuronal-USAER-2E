"""Formulario público y módulo administrativo para el registro de maestros de grupo de escuelas primarias."""
import streamlit as st
import pandas as pd
from services.docentes_regulares import (
    ESCUELAS_PRIMARIAS,
    GRADOS,
    GRUPOS,
    TURNOS,
    registrar_docente_regular,
    registrar_lote_docentes,
    listar_docentes_regulares,
    resumen_cobertura_escuelas,
)
from config.settings import SCHOOL_YEAR

URL_PUBLICA = "https://red-neuronal-usaer-2e.streamlit.app/?p=docentes"


def formulario_publico_docentes():
    """Vista pública (sin login) para que maestros y directores de primarias registren docentes de grupo."""
    st.markdown("""
    <style>
    .public-container {
        max-width: 820px;
        margin: 0 auto;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    .header-hero {
        background: linear-gradient(135deg, #042f2e 0%, #0f766e 100%);
        color: white;
        padding: 28px 24px;
        border-radius: 14px;
        text-align: center;
        box-shadow: 0 8px 24px -4px rgba(15, 118, 110, 0.25);
        margin-bottom: 24px;
    }
    .badge-hero {
        display: inline-block;
        background: rgba(255, 255, 255, 0.15);
        backdrop-filter: blur(8px);
        padding: 4px 14px;
        border-radius: 20px;
        font-size: 0.75rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        font-weight: 600;
        margin-bottom: 8px;
    }
    .title-hero {
        font-size: 1.65rem;
        font-weight: 700;
        margin: 0;
        line-height: 1.25;
    }
    .subtitle-hero {
        font-size: 0.95rem;
        opacity: 0.9;
        margin-top: 8px;
        max-width: 650px;
        margin-left: auto;
        margin-right: auto;
        line-height: 1.45;
    }
    .card-form {
        background: #ffffff;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        padding: 24px;
        box-shadow: 0 4px 16px -2px rgba(15, 23, 42, 0.06);
        margin-bottom: 20px;
    }
    .success-card {
        background: #f0fdf4;
        border: 1px solid #86efac;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        margin-bottom: 20px;
    }
    .footer-help {
        text-align: center;
        font-size: 0.8rem;
        color: #64748b;
        margin-top: 30px;
        padding-top: 15px;
        border-top: 1px solid #e2e8f0;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="public-container">
        <div class="header-hero">
            <div class="badge-hero">Secretaría de Educación de Yucatán · Zona 001</div>
            <h1 class="title-hero">Directorio de Maestros de Grupo · Primarias Regulares</h1>
            <div class="subtitle-hero">
                USAER 02E · Vinculación y Acompañamiento Pedagógico · Ciclo Escolar 2026 – 2027
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if aviso := st.session_state.pop("docente_guardado_aviso", None):
        st.markdown(f"""
        <div class="success-card">
            <div style="font-size: 2rem; margin-bottom: 8px;">✅</div>
            <h3 style="color: #166534; margin: 0; font-size: 1.25rem;">¡Registro guardado con éxito!</h3>
            <p style="color: #15803d; margin: 6px 0 0 0; font-size: 0.95rem;">{aviso}</p>
        </div>
        """, unsafe_allow_html=True)

    pestana_individual, pestana_plantilla = st.tabs([
        "👤 Registro Individual (Maestro/a de Grupo)",
        "🏫 Registro por Escuela Completa (Directores / Enlaces)",
    ])

    with pestana_individual:
        st.markdown("""
        <div style="font-size: 0.9rem; color: #475569; margin-bottom: 16px;">
            Completa tus datos como docente titular de grupo para vincular la atención educativa de los alumnos que reciben apoyo de la USAER 02E.
        </div>
        """, unsafe_allow_html=True)

        with st.form("form_docente_individual", clear_on_submit=False):
            col_esc, col_tur = st.columns([3, 2])
            with col_esc:
                escuela_sel = st.selectbox(
                    "1. Escuela Primaria Regular *",
                    ESCUELAS_PRIMARIAS,
                    index=0,
                    help="Selecciona tu escuela entre las 7 primarias atendidas por USAER 02E",
                )
            with col_tur:
                turno_sel = st.selectbox("Turno *", TURNOS, index=0)

            col_grd, col_grp = st.columns([1, 1])
            with col_grd:
                grado_sel = st.selectbox("2. Grado Escolar *", GRADOS, index=0)
            with col_grp:
                grupo_sel = st.selectbox("3. Grupo *", GRUPOS, index=0)

            nombre_docente = st.text_input(
                "4. Nombre Completo del Maestro(a) de Grupo *",
                placeholder="Ej. María Elena Pérez Gómez",
                help="Escribe tu nombre y apellidos tal como aparecen en los registros oficiales.",
            )

            col_tel, col_mail = st.columns(2)
            with col_tel:
                telefono = st.text_input(
                    "5. Teléfono WhatsApp (10 dígitos) - Opcional",
                    placeholder="Ej. 9991234567",
                    help="Para coordinación directa con el docente de apoyo y paradocentes de la USAER.",
                )
            with col_mail:
                email = st.text_input(
                    "6. Correo Electrónico - Opcional",
                    placeholder="Ej. maestro@educacionyucatan.gob.mx",
                )

            observaciones = st.text_area(
                "Observaciones o Comentarios adicionales (Opcional)",
                placeholder="Ej. Horario de atención a padres, días específicos, etc.",
                height=70,
            )

            guardar_btn = st.form_submit_button("💾 Guardar Mi Registro", type="primary", use_container_width=True)

        if guardar_btn:
            if not nombre_docente.strip():
                st.error("Por favor ingresa tu nombre completo.")
            else:
                try:
                    reg = registrar_docente_regular(
                        escuela=escuela_sel,
                        grado=grado_sel,
                        grupo=grupo_sel,
                        nombre_docente=nombre_docente.strip(),
                        turno=turno_sel,
                        telefono=telefono.strip(),
                        email=email.strip(),
                        observaciones=observaciones.strip(),
                    )
                    st.session_state["docente_guardado_aviso"] = (
                        f"Se registró a <strong>{reg['Nombre_Docente']}</strong> para <strong>{reg['Grado']} {reg['Grupo']}</strong> "
                        f"de la primaria <strong>{reg['Nombre_Escuela']}</strong> ({reg['Turno']}). ¡Muchas gracias!"
                    )
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar: {e}")

    with pestana_plantilla:
        st.markdown("""
        <div style="font-size: 0.9rem; color: #475569; margin-bottom: 16px;">
            Si eres Directivo o enlace de una de las 7 primarias, puedes capturar a los maestros de grupo de tu escuela en un solo paso.
        </div>
        """, unsafe_allow_html=True)

        col_p1, col_p2 = st.columns([3, 2])
        with col_p1:
            escuela_plantilla = st.selectbox("Escuela Primaria *", ESCUELAS_PRIMARIAS, key="plantilla_escuela")
        with col_p2:
            turno_plantilla = st.selectbox("Turno *", TURNOS, key="plantilla_turno")

        st.markdown("##### Grupos y Docentes")
        st.caption("Llena los nombres de los docentes para cada grado y grupo que tenga tu escuela:")

        filas_default = []
        for g in ["1°", "2°", "3°", "4°", "5°", "6°"]:
            for grp in ["A", "B"]:
                filas_default.append({"Grado": g, "Grupo": grp, "Nombre_Docente": "", "Telefono": ""})

        df_editor = st.data_editor(
            pd.DataFrame(filas_default),
            column_config={
                "Grado": st.column_config.SelectboxColumn("Grado", options=GRADOS, required=True, width="small"),
                "Grupo": st.column_config.SelectboxColumn("Grupo", options=GRUPOS, required=True, width="small"),
                "Nombre_Docente": st.column_config.TextColumn("Nombre Completo del Maestro(a)", required=True, width="large"),
                "Telefono": st.column_config.TextColumn("Teléfono (Opcional)", width="medium"),
            },
            num_rows="dynamic",
            use_container_width=True,
            key="editor_docentes_plantilla",
        )

        if st.button("💾 Guardar Plantilla de la Escuela", type="primary", use_container_width=True):
            registros_validos = []
            if isinstance(df_editor, pd.DataFrame):
                for _, row in df_editor.iterrows():
                    nom = str(row.get("Nombre_Docente", "") or "").strip()
                    if nom:
                        registros_validos.append({
                            "Grado": str(row.get("Grado", "")).strip(),
                            "Grupo": str(row.get("Grupo", "")).strip().upper(),
                            "Nombre_Docente": nom,
                            "Telefono": str(row.get("Telefono", "")).strip(),
                        })

            if not registros_validos:
                st.warning("No ingresaste nombres de docentes para guardar.")
            else:
                try:
                    guardados = registrar_lote_docentes(
                        escuela=escuela_plantilla,
                        turno=turno_plantilla,
                        lista_docentes=registros_validos,
                    )
                    st.session_state["docente_guardado_aviso"] = (
                        f"Se registraron exitosamente <strong>{len(guardados)} docentes</strong> "
                        f"de la primaria <strong>{escuela_plantilla}</strong> ({turno_plantilla})."
                    )
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar la plantilla: {e}")

    # Pie institucional
    st.markdown("""
    <div class="footer-help">
        <strong>USAER 02E · Dirección de Educación Especial de Yucatán</strong><br>
        Directorio y Vinculación Escolar · Para dudas o asistencia comunícate con la Dirección de la USAER 02E.
    </div>
    """, unsafe_allow_html=True)


def vista_docentes_regulares_admin():
    """Vista interna (para el Director y equipo USAER) para consultar y descargar el directorio de docentes regulares."""
    st.markdown("""
    <div style="background: linear-gradient(135deg, #042f2e 0%, #0f766e 100%); color: white; padding: 18px 24px; border-radius: 12px; margin-bottom: 20px;">
        <div style="font-size: 0.75rem; letter-spacing: 0.08em; text-transform: uppercase; opacity: 0.85; font-weight: 600;">
            Gestión Escolar · Vinculación Institucional
        </div>
        <h2 style="margin: 4px 0 0 0; font-size: 1.45rem; font-weight: 700;">Directorio de Maestros de Grupo de las 7 Primarias</h2>
        <div style="font-size: 0.85rem; opacity: 0.9; margin-top: 4px;">
            Consulta, seguimiento y descarga de los docentes frente a grupo registrados por grado y grupo.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Enlace para compartir
    st.markdown("#### 🔗 Enlace para Compartir con Directores y Maestros de Primaria")
    st.info(
        f"Comparte este enlace por WhatsApp o correo oficial con los directores de las 7 escuelas primarias o directamente con sus docentes de grupo:\n\n"
        f"👉 **`{URL_PUBLICA}`**"
    )

    c_c1, c_c2 = st.columns([1, 1])
    with c_c1:
        st.code(URL_PUBLICA, language=None)
    with c_c2:
        st.link_button("🌐 Abrir Formulario en Nueva Pestaña", URL_PUBLICA, use_container_width=True)

    st.divider()

    # Resumen de cobertura por escuela
    st.markdown("#### 📊 Cobertura por Escuela Primaria")
    cobertura = resumen_cobertura_escuelas()
    cols_metrics = st.columns(len(cobertura))
    for col, c in zip(cols_metrics, cobertura):
        with col:
            cant = c["Docentes_Registrados"]
            color = "#16a34a" if cant >= 6 else "#ca8a04" if cant > 0 else "#94a3b8"
            st.markdown(f"""
            <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-top: 3px solid {color}; border-radius: 8px; padding: 10px; text-align: center; margin-bottom: 10px;">
                <div style="font-size: 0.72rem; font-weight: 600; color: #64748b; height: 32px; overflow: hidden;">{c['Escuela']}</div>
                <div style="font-size: 1.4rem; font-weight: 700; color: #0f172a; margin-top: 2px;">{cant}</div>
                <div style="font-size: 0.7rem; color: #64748b;">grupos registrados</div>
            </div>
            """, unsafe_allow_html=True)

    # Filtro y tabla de docentes
    st.markdown("#### 📋 Listado Detallado de Docentes Registrados")
    escuelas_filtro = ["Todas las 7 escuelas"] + ESCUELAS_PRIMARIAS
    escuela_elegida = st.selectbox("Filtrar por Escuela", escuelas_filtro)
    
    filtro_arg = None if escuela_elegida == "Todas las 7 escuelas" else escuela_elegida
    docentes = listar_docentes_regulares(escuela=filtro_arg)

    if not docentes:
        st.warning(f"Aún no hay docentes registrados para {escuela_elegida.lower()}. Comparte el enlace para comenzar a recopilarlos.")
    else:
        df_mostrar = pd.DataFrame(docentes)
        columnas_orden = [
            "Nombre_Escuela",
            "Turno",
            "Grado",
            "Grupo",
            "Nombre_Docente",
            "Telefono",
            "Email",
            "Fecha_Registro",
        ]
        columnas_presentes = [c for c in columnas_orden if c in df_mostrar.columns]
        df_mostrar = df_mostrar[columnas_presentes].copy()

        st.dataframe(
            df_mostrar,
            column_config={
                "Nombre_Escuela": "Escuela Primaria",
                "Turno": "Turno",
                "Grado": "Grado",
                "Grupo": "Grupo",
                "Nombre_Docente": "Maestro(a) de Grupo",
                "Telefono": "Teléfono",
                "Email": "Correo",
                "Fecha_Registro": "Fecha Registro",
            },
            hide_index=True,
            use_container_width=True,
        )

        # Botones de exportación
        csv = df_mostrar.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Descargar Directorio en CSV (Excel)",
            csv,
            file_name=f"directorio_maestros_primaria_{filtro_arg or 'todas'}.csv",
            mime="text/csv",
            use_container_width=True,
        )

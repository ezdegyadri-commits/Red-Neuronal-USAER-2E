"""Formulario ultra simple para recopilar nombres de maestros de grupo de primaria."""
import streamlit as st
import pandas as pd
from services.docentes_regulares import (
    ESCUELAS_PRIMARIAS,
    GRADOS,
    GRUPOS,
    registrar_docente_regular,
    listar_docentes_regulares,
)

URL_PUBLICA = "https://red-neuronal-usaer-2e.streamlit.app/?p=docentes"


def formulario_publico_docentes():
    """Formulario directo y minimalista: Escuela -> Grado -> Grupo -> Nombre."""
    st.markdown("""
    <style>
    .simple-card {
        max-width: 620px;
        margin: 0 auto;
        background: #ffffff;
        border-radius: 14px;
        border: 1px solid #e2e8f0;
        padding: 24px 28px;
        box-shadow: 0 4px 20px -2px rgba(15, 23, 42, 0.08);
    }
    .header-box {
        text-align: center;
        margin-bottom: 20px;
    }
    .header-sub {
        font-size: 0.75rem;
        text-transform: uppercase;
        color: #0f766e;
        font-weight: 700;
        letter-spacing: 0.06em;
    }
    .header-title {
        font-size: 1.4rem;
        font-weight: 700;
        color: #0f172a;
        margin: 4px 0;
    }
    .header-desc {
        font-size: 0.88rem;
        color: #64748b;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="header-box">
        <div class="header-sub">USAER 02E · Zona 001</div>
        <div class="header-title">Maestros de Grupo de Primaria</div>
        <div class="header-desc">Registro rápido por grado y grupo</div>
    </div>
    """, unsafe_allow_html=True)

    if aviso := st.session_state.pop("docente_guardado_aviso", None):
        st.success(aviso)

    # Formulario minimalista de 4 campos
    with st.form("form_simple_docente", clear_on_submit=True):
        escuela = st.selectbox(
            "Escuela Primaria",
            ESCUELAS_PRIMARIAS,
            index=0,
            key="escuela_simple",
        )

        col_g1, col_g2 = st.columns(2)
        with col_g1:
            grado = st.selectbox("Grado", GRADOS, index=0, key="grado_simple")
        with col_g2:
            grupo = st.selectbox("Grupo", GRUPOS, index=0, key="grupo_simple")

        nombre = st.text_input(
            "Nombre completo del Maestro(a)",
            placeholder="Ej. Juan Pérez López",
            key="nombre_simple",
        )

        guardar = st.form_submit_button("Guardar Maestro(a)", type="primary", use_container_width=True)

    if guardar:
        if not nombre.strip():
            st.error("Escribe el nombre del maestro(a).")
        else:
            try:
                registrar_docente_regular(
                    escuela=escuela,
                    grado=grado,
                    grupo=grupo,
                    nombre_docente=nombre.strip(),
                )
                st.session_state["docente_guardado_aviso"] = (
                    f"✅ Guardado: {nombre.strip()} ({grado} {grupo} · {escuela})"
                )
                st.rerun()
            except Exception as e:
                st.error(f"Error al guardar: {e}")

    # Lista de los ya registrados en esa escuela para que vean lo que ya se capturó
    st.markdown("---")
    registrados = listar_docentes_regulares(escuela=escuela)
    if registrados:
        st.markdown(f"**Maestros registrados en {escuela}:**")
        df = pd.DataFrame(registrados)[["Grado", "Grupo", "Nombre_Docente"]].copy()
        df.columns = ["Grado", "Grupo", "Maestro(a)"]
        st.dataframe(df, hide_index=True, use_container_width=True)


def vista_docentes_regulares_admin():
    """Vista para consultar el directorio desde Dirección / USAER."""
    st.subheader("Directorio de Maestros de Grupo (7 Primarias)")
    
    st.markdown(f"**Enlace para compartir:** `{URL_PUBLICA}`")
    c1, c2 = st.columns([1, 1])
    with c1:
        st.code(URL_PUBLICA, language=None)
    with c2:
        st.link_button("🌐 Abrir Formulario", URL_PUBLICA, use_container_width=True)

    st.markdown("---")
    escuela_sel = st.selectbox("Selecciona Escuela Primaria", ["Todas"] + ESCUELAS_PRIMARIAS)
    filtro = None if escuela_sel == "Todas" else escuela_sel
    docentes = listar_docentes_regulares(escuela=filtro)

    if not docentes:
        st.info("Aún no hay maestros registrados.")
    else:
        df = pd.DataFrame(docentes)[["Nombre_Escuela", "Grado", "Grupo", "Nombre_Docente", "Fecha_Registro"]].copy()
        df.columns = ["Escuela", "Grado", "Grupo", "Maestro(a)", "Fecha de Captura"]
        st.dataframe(df, hide_index=True, use_container_width=True)
        
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Descargar en Excel (CSV)",
            csv,
            file_name=f"maestros_primaria_{filtro or 'todas'}.csv",
            mime="text/csv",
            use_container_width=True,
        )

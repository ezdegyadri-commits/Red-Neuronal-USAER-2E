"""Formulario ultra simple para recopilar nombres de maestros de grupo de primaria."""
import streamlit as st
import pandas as pd
from services.docentes_regulares import (
    GRADOS,
    GRUPOS,
    listar_docentes_regulares,
    escuelas_del_actor,
    guardar_docente_asignado,
    editar_docente_regular,
    TURNOS,
)

URL_PUBLICA = "https://red-neuronal-usaer-2e.streamlit.app/?p=docentes"


def formulario_publico_docentes():
    """Formulario directo y minimalista: Escuela -> Grado -> Grupo -> Nombre."""
    actor={'autenticado':st.session_state.get('autenticado',False),
           'cuenta':st.session_state.get('usuario',''),'nombre':st.session_state.get('nombre',''),
           'rol':st.session_state.get('rol',''),'escuelas_permitidas':st.session_state.get('escuelas_permitidas','')}
    try:permitidas=escuelas_del_actor(actor)
    except PermissionError as exc:st.info(str(exc));return
    if not permitidas:st.warning('Tu cuenta no tiene una escuela primaria asignada. Consulta con Dirección.');return
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

    if len(permitidas)==1:
        escuela=permitidas[0]
        st.info('Escuela asignada: '+escuela)
    else:
        if st.session_state.get('escuela_simple') not in permitidas:st.session_state['escuela_simple']=permitidas[0]
        escuela=st.selectbox('Escuela Primaria',permitidas,key='escuela_simple')
    # La escuela se fija fuera del formulario y se valida otra vez en servidor.
    with st.form("form_simple_docente", clear_on_submit=False):
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
                registro=guardar_docente_asignado(
                    actor,
                    escuela=escuela,
                    grado=grado,
                    grupo=grupo,
                    nombre_docente=nombre.strip(),
                )
                if registro['_guardado_central']:
                    st.session_state["docente_guardado_aviso"] = f"Guardado: {nombre.strip()} ({grado} {grupo} · {escuela})"
                    st.rerun()
                else:st.warning('El registro tiene respaldo local, pero no se confirmó en la base central. No cierres esta sesión; vuelve a intentar cuando se restablezca la conexión.')
            except Exception as e:
                st.error(f"Error al guardar: {e}")

    # Lista de los ya registrados en esa escuela para que vean lo que ya se capturó
    st.write("")
    registrados = listar_docentes_regulares(escuela=escuela)
    if registrados:
        st.markdown(f"**Maestros registrados en {escuela}:**")
        df = pd.DataFrame(registrados)[['Ciclo_Escolar',"Grado", "Grupo", "Nombre_Docente"]].copy()
        df.columns = ['Ciclo',"Grado", "Grupo", "Maestro(a)"]
        st.dataframe(df, hide_index=True, use_container_width=True)
        st.download_button('Descargar listado (CSV)',df.to_csv(index=False).encode('utf-8'),file_name='maestros-primaria.csv',mime='text/csv',key='descargar_docentes_asignados')
        with st.expander('Corregir un maestro registrado',expanded=False):
            porid={r['ID_Registro']:r for r in registrados}
            rid=st.selectbox('Maestro que deseas corregir',list(porid),format_func=lambda i:porid[i]['Grado']+' '+porid[i]['Grupo']+' · '+porid[i]['Nombre_Docente']+' · '+porid[i]['Ciclo_Escolar'],key='docente_corregir_'+escuela)
            r=porid[rid]
            with st.form('editar_docente_'+rid,clear_on_submit=False):
                nom=st.text_input('Nombre correcto',value=r['Nombre_Docente'])
                c1,c2,c3=st.columns(3)
                grd=c1.selectbox('Grado correcto',GRADOS,index=GRADOS.index(r['Grado']) if r['Grado'] in GRADOS else 0)
                grp=c2.selectbox('Grupo correcto',GRUPOS,index=GRUPOS.index(r['Grupo']) if r['Grupo'] in GRUPOS else 0)
                turno=c3.selectbox('Turno',TURNOS,index=TURNOS.index(r.get('Turno')) if r.get('Turno') in TURNOS else 0)
                corregir=st.form_submit_button('Guardar corrección',type='primary')
            if corregir:
                try:
                    guardado=editar_docente_regular(rid,{'Nombre_Docente':nom,'Grado':grd,'Grupo':grp,'Turno':turno},actor)
                    if guardado['_guardado_central']:
                        st.session_state['docente_guardado_aviso']='Corrección guardada. El registro anterior se conserva en el historial.'
                        st.rerun()
                    else:st.warning('Corrección respaldada localmente; falta confirmar su guardado central.')
                except (ValueError,PermissionError,RuntimeError) as exc:st.warning(str(exc))


def vista_docentes_regulares_admin():
    """Vista para consultar el directorio desde Dirección / USAER."""
    st.subheader('Maestros regulares · captura y correcciones')
    formulario_publico_docentes()

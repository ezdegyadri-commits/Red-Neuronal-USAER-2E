import json
from datetime import date
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from config.settings import ESCUELAS_USAER, BAP_ITEMS, BAP_FRECUENCIAS, SERVICE_NAME, SCHOOL_YEAR
from data import repository as repo
from services.expedientes import alumnos_visibles, expediente, alumno
from services.alumnos import alumnos_de_escuela, alumnos_individuales_de_escuela
from services.asignaciones import escuelas_asignadas, alumnos_de_escuelas_asignadas
from ai.engine import fallback, generar_sugerencias
from documents.anexos import anexo3_html, anexo4_html, anexo5_html, header_b64
from ui.components import hero, card
from utils.ids import expediente_id
from utils.text import normalizar_texto


def inicio(df):
    hero("Centro de gestión USAE", "Una sola plataforma para capturar, decidir, intervenir y dar seguimiento.")
    c1,c2,c3,c4=st.columns(4)
    with c1: card("Alumnos visibles",len(df))
    with c2: card("Anexos 3",len(repo.anexo3()))
    with c3: card("Sugerencias",len(repo.anexo4()))
    with c4: card("Eventos",len(repo.anexo5()))
    st.markdown("### Principio operativo")
    st.info("**Capturar una vez, reutilizar siempre.** El expediente es el eje: BAP → IA → sugerencia oficial → acción → evento → resultado → seguimiento.")
    st.markdown("### Ruta de trabajo")
    cols=st.columns(5)
    for c,t in zip(cols,["1. Expediente","2. BAP","3. IA + revisión","4. Seguimiento","5. Evidencia"]):
        with c: st.markdown(f"<div class='card'><span class='badge'>PROCESO</span><h4>{t}</h4><div class='muted'>La información permanece conectada.</div></div>",unsafe_allow_html=True)


def expedientes_page(df):
    hero("Expedientes únicos", "Selecciona un alumno para consultar toda su trazabilidad.")
    if df.empty: st.warning("No hay alumnos disponibles para tu ámbito de acceso."); return
    options=df[["ID_Alumno","Nombre_Completo"]].drop_duplicates().sort_values("Nombre_Completo")
    label=st.selectbox("Alumno", options["Nombre_Completo"].tolist(), key="exp_alumno")
    id_alumno=options.loc[options["Nombre_Completo"]==label,"ID_Alumno"].iloc[0]
    st.session_state["selected_alumno"]=id_alumno
    exp=expediente(id_alumno)
    a=exp["alumno"]
    c=st.columns(4)
    with c[0]: card("Expediente",exp["id_expediente"])
    with c[1]: card("Grado / grupo",f"{a.get('Grado','')} {a.get('Grupo','')}")
    with c[2]: card("Condición",a.get("Condicion_Discapacidad",""))
    with c[3]: card("Estatus",a.get("Estatus",""))
    tabs=st.tabs(["Resumen","Anexo 3","Anexo 4","Anexo 5","Línea de tiempo"])
    with tabs[0]:
        st.write({k:a.get(k,"") for k in ["Nombre_Completo","CURP","Grado","Grupo","ID_Escuela","Maestra de Apoyo","ID_Maestro_Regular","Condicion_Discapacidad","Tipo_Atencion","Estatus"]})
    with tabs[1]: st.dataframe(exp["anexo3"],use_container_width=True,hide_index=True)
    with tabs[2]:
        st.dataframe(exp["anexo4"],use_container_width=True,hide_index=True)
        if not exp["anexo4"].empty and st.button("Preparar Anexo 4 para impresión",key="prep4"):
            st.download_button("Descargar HTML oficial",anexo4_html(a,exp["anexo4"]),f"Anexo_IV_{id_alumno}.html","text/html")
    with tabs[3]:
        st.dataframe(exp["anexo5"],use_container_width=True,hide_index=True)
        if not exp["anexo5"].empty and st.button("Preparar Anexo 5 para impresión",key="prep5"):
            st.download_button("Descargar HTML oficial",anexo5_html(a,exp["anexo5"]),f"Anexo_V_{id_alumno}.html","text/html")
    with tabs[4]:
        tl=exp["timeline"]
        if tl.empty: st.info("El expediente todavía no tiene línea de tiempo integrada.")
        else:
            for _,r in tl.sort_values("Fecha",ascending=False).iterrows():
                st.markdown(f"**{r.get('Fecha','')} · {r.get('Tipo','')}** — {r.get('Titulo','')}\n\n{r.get('Descripcion','')}")
                st.divider()


def alta_page(df):
    hero("Alta de alumnos", "Registra nuevos expedientes sin duplicar información.")
    with st.form("alta"):
        nombre=st.text_input("Nombre completo")
        curp=st.text_input("CURP",max_chars=18)
        c1,c2=st.columns(2)
        with c1: grado=st.selectbox("Grado",["1ro","2do","3ro","4to","5to","6to"])
        with c2: grupo=st.selectbox("Grupo",["A","B","C","D"])
        escuela=st.selectbox("Escuela",list(ESCUELAS_USAER))
        apoyo=st.text_input("Maestra/o de apoyo")
        regular=st.text_input("Docente regular")
        condicion=st.selectbox("Condición / discapacidad",["Intelectual","Auditiva","Visual","Motora","TEA","TDAH","Aptitudes Sobresalientes","Dificultades severas de aprendizaje","Dificultades severas de conducta","Dificultades severas de comunicación","Ninguna"])
        tipo=st.selectbox("Tipo de atención",["Individual","Grupal"])
        save=st.form_submit_button("Crear expediente",type="primary")
    if save:
        if not nombre.strip() or not curp.strip(): st.error("Nombre y CURP son obligatorios."); return
        id_a=repo.save_alumno({"Nombre_Completo":nombre.strip(),"CURP":curp.strip().upper(),"Grado":grado,"Grupo":grupo,"ID_Escuela":ESCUELAS_USAER[escuela],"Maestra de Apoyo":apoyo,"ID_Maestro_Regular":regular,"Condicion_Discapacidad":condicion,"Estatus":"Activo","Tipo_Atencion":tipo})
        st.success(f"Expediente creado: {expediente_id(id_a)}")


def bap_page(df):
    hero(
        "Evaluación BAP → intervención",
        "La captura estructurada alimenta la IA; la decisión profesional queda en tus manos."
    )

    if df.empty:
        st.warning("No hay alumnos disponibles.")
        return

    modo = st.radio(
        "Tipo de evaluación",
        [
            "Individual (alumno específico)",
            "Grupal (contexto áulico)"
        ],
        horizontal=True,
        key="bap_modo"
    )

    nombre_usuario = st.session_state.get("nombre", "")
    rol_usuario = st.session_state.get("rol", "")
    opciones_escuela = escuelas_asignadas(nombre_usuario, rol_usuario)
    alumnos_asignados = alumnos_de_escuelas_asignadas(
        df, nombre_usuario, rol_usuario
    )

    if not opciones_escuela:
        st.error(
            "No tienes escuelas asignadas para realizar esta evaluación."
        )
        return

    if modo.startswith("Individual"):
        escuela = st.selectbox(
            "1. Escuela",
            opciones_escuela,
            key="bap_escuela_ind"
        )

        escuela_df = alumnos_individuales_de_escuela(
            alumnos_asignados, escuela
        )

        if escuela_df.empty:
            st.warning(
                "No hay alumnos con atención individual registrados "
                "en esta escuela."
            )
            return

        alumno_nombre = st.selectbox(
            "2. Alumno",
            escuela_df["Nombre_Completo"].astype(str).tolist(),
            key="bap_alumno_ind"
        )

        fila = escuela_df[
            escuela_df["Nombre_Completo"].astype(str) == alumno_nombre
        ].iloc[0]

        id_a = str(fila["ID_Alumno"])
        objetivo = alumno_nombre

        grado_grupo = (
            f"{fila.get('Grado', '')} "
            f"{fila.get('Grupo', '')}"
        ).strip()

        escuela_nombre = escuela
        contexto_base = {
            "tipo": "Individual",
            "alumno": fila.to_dict()
        }

    else:
        escuela = st.selectbox(
            "Escuela a observar",
            opciones_escuela,
            key="bap_escuela_grp"
        )

        c1, c2 = st.columns(2)

        with c1:
            grado = st.selectbox(
                "Grado",
                ["1ro", "2do", "3ro", "4to", "5to", "6to"],
                key="bap_grado_grp"
            )

        with c2:
            grupo = st.selectbox(
                "Grupo",
                ["A", "B", "C", "D"],
                key="bap_grupo_grp"
            )

        id_a = f"GRUPO-{ESCUELAS_USAER[escuela]}-{grado}-{grupo}"
        objetivo = f"Grupo {grado} {grupo} de la escuela {escuela}"
        grado_grupo = f"{grado} {grupo}"
        escuela_nombre = escuela

        contexto_base = {
            "tipo": "Grupal",
            "objetivo": objetivo,
            "escuela": escuela
        }

    st.markdown("### Instrumento de Observación — Anexo III")

    with st.form("bap_form_integrado", clear_on_submit=False):
        respuestas = {}

        for i, pregunta in enumerate(BAP_ITEMS, 1):
            c1, c2 = st.columns([3, 1])

            with c1:
                frecuencia = st.radio(
                    f"{i}. {pregunta}",
                    BAP_FRECUENCIAS,
                    index=1,
                    horizontal=True,
                    key=f"bap_freq_{modo}_{id_a}_{i}"
                )

            with c2:
                orientacion = st.checkbox(
                    "Requiere orientación",
                    key=f"bap_ori_{modo}_{id_a}_{i}"
                )

            respuestas[f"Item_{i}"] = {
                "pregunta": pregunta,
                "frecuencia": frecuencia,
                "orientacion": orientacion
            }

        observaciones = st.text_area(
            "Observaciones cualitativas / estrategias previas",
            height=120,
            key=f"bap_obs_{id_a}"
        )

        analizar = st.form_submit_button(
            "Analizar BAP con IA",
            type="primary"
        )

    if analizar:
        detectadas = [
            valor
            for valor in respuestas.values()
            if valor["frecuencia"] in ["Nunca", "Pocas veces"]
            or valor["orientacion"]
        ]

        contexto = {
            **contexto_base,
            "expediente": expediente_id(id_a),
            "grado_grupo": grado_grupo,
            "escuela": escuela_nombre,
            "bap": respuestas,
            "barreras_detectadas": detectadas,
            "observaciones": observaciones
        }

        with st.spinner(
            "Analizando barreras y preparando una propuesta profesional..."
        ):
            try:
                st.session_state["ai_draft"] = generar_sugerencias(contexto)
            except RuntimeError:
                # La operación continúa con una propuesta editable si el
                # proveedor de IA no está disponible temporalmente.
                st.session_state["ai_draft"] = fallback()
                st.warning(
                    "La IA no está disponible en este momento. "
                    "Se preparó una propuesta base que puedes editar y aprobar."
                )
            st.session_state["ai_context"] = contexto

    draft = st.session_state.get("ai_draft")

    if not draft:
        return

    st.markdown("### Propuesta de IA")
    st.caption(
        "La IA propone; el profesional decide. "
        "Nada se incorpora al expediente hasta que lo apruebes."
    )

    area = st.text_input(
        "Sugerencias del área",
        draft.get("area", "Aprendizaje"),
        key="draft_area"
    )

    motivo = st.text_area(
        "Motivo por el que se brindan las sugerencias",
        draft.get(
            "motivo",
            "Resultados del Anexo 3: Barreras identificadas en el contexto áulico"
        ),
        key="draft_motivo"
    )

    sugerencias = st.text_area(
        "Sugerencias",
        draft.get("sugerencias", ""),
        height=300,
        key="draft_sug"
    )

    seguimiento = st.text_input(
        "Fecha / plazo de seguimiento",
        draft.get("seguimiento", ""),
        key="draft_follow"
    )

    if st.button(
        "Aprobar → generar Anexo 3 y Anexo 4",
        type="primary",
        key="approve_bap"
    ):
        hoy = str(date.today())
        contexto = st.session_state.get("ai_context", {})
        respuestas_json = json.dumps(
            contexto.get("bap", {}),
            ensure_ascii=False
        )

        a3 = repo.save_anexo3({
            "Fecha": hoy,
            "ID_Alumno": id_a,
            "ID_Personal": st.session_state.get("nombre", ""),
            "BAP_Fisicas": respuestas_json,
            "BAP_Actitudinales": "",
            "BAP_Pedagogicas": "",
            "BAP_Organizativas": "",
            "Estatus_IA": "Procesado"
        })

        a4 = repo.save_anexo4({
            "Nombre_Alumno": objetivo,
            "Grado_Grupo": grado_grupo,
            "Escuela": escuela_nombre,
            "Servicio_EE": SERVICE_NAME,
            "Sugerencias_Area": area,
            "Fecha_Elaboracion": hoy,
            "Motivo": motivo,
            "Fecha_Seguimiento": seguimiento,
            "Sugerencias": sugerencias,
            "Nivel_Cumplimiento_Resultados": "Pendiente de revisión",
            "Quien_Brinda_Sugerencias": st.session_state.get("nombre", "")
        })

        try:
            repo.ensure_expediente(expediente_id(id_a), id_a)
            repo.link_record(expediente_id(id_a), id_a, "ANEXO3", a3, hoy)
            repo.link_record(expediente_id(id_a), id_a, "ANEXO4", a4, hoy)
            repo.timeline(
                expediente_id(id_a),
                id_a,
                hoy,
                "SUGERENCIA",
                "Anexo 4 aprobado",
                sugerencias,
                st.session_state.get("nombre", "")
            )
        except Exception as ex:
            st.warning(
                "Los formatos se guardaron. La vinculación adicional "
                f"no pudo completarse: {ex}"
            )

        st.session_state["last_anexo4"] = {
            "id": a4,
            "id_alumno": id_a,
            "nombre": objetivo,
            "sugerencias": sugerencias
        }
        st.session_state.pop("ai_draft", None)

        st.success(
            "Anexo 3 y Anexo 4 generados y vinculados al expediente."
        )

    last = st.session_state.get("last_anexo4")

    if last:
        st.divider()
        st.markdown("### Convertir la sugerencia en acción")
        st.info(
            "Este es el punto de conexión entre Anexo 4 y Anexo 5: "
            "puedes documentar inmediatamente qué se hizo y qué resultado produjo."
        )

        evento = st.text_area(
            "Acción / resultado observado",
            key="quick_event"
        )

        if st.button(
            "Registrar como evento de seguimiento",
            key="quick_event_btn"
        ):
            a = alumno(df, last["id_alumno"])

            eid = repo.save_anexo5({
                "Fecha": str(date.today()),
                "Nombre_Alumno": last["nombre"],
                "Grado_Grupo": (
                    f"{a.get('Grado', '')} {a.get('Grupo', '')}".strip()
                    if a else ""
                ),
                "Especialista": st.session_state.get("nombre", ""),
                "Evento": evento
            })

            try:
                repo.link_record(
                    expediente_id(last["id_alumno"]),
                    last["id_alumno"],
                    "ANEXO5",
                    eid,
                    str(date.today())
                )
                repo.timeline(
                    expediente_id(last["id_alumno"]),
                    last["id_alumno"],
                    str(date.today()),
                    "SEGUIMIENTO",
                    "Evento derivado de Anexo 4",
                    evento,
                    st.session_state.get("nombre", "")
                )
            except Exception:
                pass

            st.success(
                "La sugerencia ya tiene un evento de seguimiento asociado."
            )
def seguimiento_page(df):
    hero("Seguimiento y eventos", "Convierte una sugerencia aprobada en una acción documentada.")
    if df.empty: return
    opts=df[["ID_Alumno","Nombre_Completo"]].drop_duplicates().sort_values("Nombre_Completo")
    nombre=st.selectbox("Alumno",opts["Nombre_Completo"].tolist(),key="evt_alumno")
    id_a=opts.loc[opts["Nombre_Completo"]==nombre,"ID_Alumno"].iloc[0]; a=alumno(df,id_a)
    e=expediente(id_a)
    if e["anexo4"].empty: st.info("No hay sugerencias para convertir en seguimiento."); return
    st.dataframe(e["anexo4"][[c for c in ["ID_Anexo4","Fecha_Elaboracion","Sugerencias","Nivel_Cumplimiento_Resultados"] if c in e["anexo4"].columns]],use_container_width=True,hide_index=True)
    with st.form("evento"):
        fecha=st.date_input("Fecha",date.today())
        evento=st.text_area("Evento / resultado observado",height=180)
        especialista=st.text_input("Especialista",st.session_state.get("nombre",""))
        save=st.form_submit_button("Registrar evento",type="primary")
    if save:
        eid=repo.save_anexo5({"Fecha":str(fecha),"Nombre_Alumno":a.get("Nombre_Completo",""),"Grado_Grupo":f"{a.get('Grado','')} {a.get('Grupo','')}".strip(),"Especialista":especialista,"Evento":evento})
        try:
            repo.link_record(expediente_id(id_a),id_a,"ANEXO5",eid,str(fecha))
            repo.timeline(expediente_id(id_a),id_a,str(fecha),"SEGUIMIENTO","Evento registrado",evento,especialista)
        except Exception as ex: st.warning(f"Evento guardado; vínculo adicional pendiente: {ex}")
        st.success("Evento registrado en Anexo 5 y en la trazabilidad del expediente.")



def eventos_page(df):
    hero(
        "Eventos significativos — Anexo V",
        "Una hoja cronológica por alumno o grupo: registra, revisa la vista "
        "previa e imprime cuando esté lista."
    )

    nombre_usuario = st.session_state.get("nombre", "")
    rol_usuario = st.session_state.get("rol", "")
    rol_normalizado = normalizar_texto(rol_usuario)
    es_especialista = any(
        palabra in rol_normalizado
        for palabra in ("PSICOLOG", "COMUNICACI", "TRABAJO")
    )

    modo = st.radio(
        "¿Dónde ocurrió el evento?",
        ["Alumno individual", "Grupo / contexto áulico"],
        horizontal=True,
        key="evento_modo",
    )

    escuela = ""
    if modo == "Alumno individual":
        if df.empty:
            st.info("No hay alumnos disponibles en tus escuelas asignadas.")
            return

        alumnos_disponibles = df
        if es_especialista:
            escuelas = escuelas_asignadas(nombre_usuario, rol_usuario)
            if not escuelas:
                st.error("No tienes escuelas asignadas para registrar eventos.")
                return
            escuela = st.selectbox(
                "Escuela",
                escuelas,
                key="evento_escuela_individual",
            )
            alumnos_disponibles = alumnos_de_escuela(df, escuela)

        if alumnos_disponibles.empty:
            st.info("No hay alumnos registrados para la escuela seleccionada.")
            return

        opciones = (
            alumnos_disponibles[["ID_Alumno", "Nombre_Completo"]]
            .drop_duplicates()
            .sort_values("Nombre_Completo")
        )
        nombre = st.selectbox(
            "Alumno",
            opciones["Nombre_Completo"].astype(str).tolist(),
            key="evento_alumno",
        )
        id_alumno = str(
            opciones.loc[
                opciones["Nombre_Completo"].astype(str) == str(nombre),
                "ID_Alumno",
            ].iloc[0]
        )
        datos = alumno(alumnos_disponibles, id_alumno) or {}
        objetivo = str(datos.get("Nombre_Completo", nombre))
        grado_grupo = (
            f"{datos.get('Grado', '')} {datos.get('Grupo', '')}".strip()
        )
    else:
        escuelas = escuelas_asignadas(nombre_usuario, rol_usuario)
        if not escuelas:
            st.error("No tienes escuelas asignadas para registrar este evento.")
            return
        escuela = st.selectbox(
            "Escuela",
            escuelas,
            key="evento_escuela_grupo",
        )
        col_grado, col_grupo = st.columns(2)
        with col_grado:
            grado = st.selectbox(
                "Grado",
                ["1ro", "2do", "3ro", "4to", "5to", "6to"],
                key="evento_grado",
            )
        with col_grupo:
            grupo = st.selectbox(
                "Grupo", ["A", "B", "C", "D"], key="evento_grupo"
            )
        grado_grupo = f"{grado} {grupo}"
        id_alumno = f"GRUPO-{ESCUELAS_USAER[escuela]}-{grado}-{grupo}"
        objetivo = f"Grupo {grado_grupo} de la escuela {escuela}"
        datos = {"Nombre_Completo": objetivo}

    eventos_todos = repo.anexo5()
    if (
        eventos_todos.empty
        or "Nombre_Alumno" not in eventos_todos.columns
    ):
        eventos_registrados = pd.DataFrame()
    else:
        eventos_registrados = eventos_todos[
            eventos_todos["Nombre_Alumno"].astype(str) == objetivo
        ].copy()

    if not eventos_registrados.empty and "Fecha" in eventos_registrados.columns:
        eventos_registrados["_orden"] = pd.to_datetime(
            eventos_registrados["Fecha"],
            errors="coerce",
            dayfirst=True,
        )
        eventos_registrados = (
            eventos_registrados
            .sort_values("_orden", na_position="last")
            .drop(columns="_orden")
        )

    st.caption(
        f"Hoja de eventos de {objetivo}. "
        f"Registros guardados: {len(eventos_registrados)}."
    )

    fecha = st.date_input(
        "Fecha del evento",
        date.today(),
        key="evento_fecha",
    )
    evento = st.text_area(
        "¿Qué ocurrió? Incluye avances, acuerdos, apoyos y próximo paso.",
        height=180,
        placeholder=(
            "Ejemplo: Se observó mayor participación durante la lectura. "
            "Se acordó mantener el apoyo visual y revisar avances en dos semanas."
        ),
        key="evento_descripcion",
    )
    especialista = st.text_input(
        "Quien registra el evento",
        nombre_usuario,
        key="evento_especialista",
    )

    borrador = {
        "Fecha": str(fecha),
        "Nombre_Alumno": objetivo,
        "Grado_Grupo": grado_grupo,
        "Especialista": especialista.strip() or nombre_usuario,
        "Evento": evento.strip(),
    }
    vista_eventos = eventos_registrados.copy()
    if borrador["Evento"]:
        vista_eventos = pd.concat(
            [vista_eventos, pd.DataFrame([borrador])],
            ignore_index=True,
        )

    st.markdown("### Vista previa del Anexo V")
    st.caption(
        "La anotación actual aparece en esta vista antes de guardarla. "
        "Las anotaciones previas permanecen ordenadas cronológicamente."
    )
    components.html(
        anexo5_html(datos, vista_eventos),
        height=690,
        scrolling=True,
    )

    guardar = st.button(
        "Guardar evento en Anexo V",
        type="primary",
        use_container_width=True,
        key="guardar_evento_anexo5",
    )
    if not guardar:
        return
    if not borrador["Evento"]:
        st.error("Describe el evento antes de guardarlo.")
        return

    try:
        id_evento = repo.save_anexo5(borrador)
        repo.ensure_expediente(expediente_id(id_alumno), id_alumno)
        repo.link_record(
            expediente_id(id_alumno), id_alumno, "ANEXO5", id_evento, str(fecha)
        )
        repo.timeline(
            expediente_id(id_alumno),
            id_alumno,
            str(fecha),
            "SEGUIMIENTO",
            "Evento significativo registrado",
            borrador["Evento"],
            borrador["Especialista"],
        )
    except Exception as ex:
        st.error(f"No fue posible guardar el evento: {ex}")
        return

    documento_actualizado = pd.concat(
        [eventos_registrados, pd.DataFrame([borrador])],
        ignore_index=True,
    )
    st.success(
        "Evento guardado en su hoja Anexo V y vinculado al expediente concentrador."
    )
    st.download_button(
        "Descargar Anexo V para imprimir",
        anexo5_html(datos, documento_actualizado),
        f"Anexo_V_{id_alumno}.html",
        "text/html",
        use_container_width=True,
        key=f"imprimir_anexo5_{id_alumno}",
    )

def documentos_page(df):
    hero(
        "Expediente documental",
        "Aquí viven los Anexos III, IV y V generados. Elige un alumno o un grupo "
        "para consultar y descargar su expediente."
    )

    tipo = st.radio(
        "Tipo de expediente",
        ["Alumno individual", "Grupo / contexto áulico"],
        horizontal=True,
        key="documentos_tipo",
    )

    if tipo == "Alumno individual":
        if df.empty:
            st.info("No hay alumnos disponibles en tus escuelas asignadas.")
            return
        opciones = (
            df[["ID_Alumno", "Nombre_Completo"]]
            .drop_duplicates()
            .sort_values("Nombre_Completo")
        )
        nombre = st.selectbox(
            "Alumno",
            opciones["Nombre_Completo"].astype(str).tolist(),
            key="doc_alumno",
        )
        id_alumno = str(
            opciones.loc[
                opciones["Nombre_Completo"].astype(str) == str(nombre),
                "ID_Alumno",
            ].iloc[0]
        )
        expediente_actual = expediente(id_alumno)
        if not expediente_actual:
            st.info("Aún no hay documentos para este alumno.")
            return
        alumno_documento = expediente_actual["alumno"]
        a3 = expediente_actual["anexo3"]
        a4 = expediente_actual["anexo4"]
        a5 = expediente_actual["anexo5"]
        etiqueta = str(alumno_documento.get("Nombre_Completo", nombre))
        archivo_base = id_alumno
    else:
        a3_todos = repo.anexo3()
        a4_todos = repo.anexo4()
        a5_todos = repo.anexo5()
        grupos = set()
        for tabla in (a4_todos, a5_todos):
            if (
                not tabla.empty
                and "Nombre_Alumno" in tabla.columns
            ):
                grupos.update(
                    str(valor)
                    for valor in tabla["Nombre_Alumno"].dropna()
                    if str(valor).startswith("Grupo ")
                )
        grupos = sorted(grupos)
        if not grupos:
            st.info("Aún no hay anexos generados para grupos.")
            return
        etiqueta = st.selectbox(
            "Grupo",
            grupos,
            key="doc_grupo",
        )
        a4 = (
            a4_todos[
                a4_todos["Nombre_Alumno"].astype(str) == etiqueta
            ].copy()
            if not a4_todos.empty and "Nombre_Alumno" in a4_todos.columns
            else pd.DataFrame()
        )
        a5 = (
            a5_todos[
                a5_todos["Nombre_Alumno"].astype(str) == etiqueta
            ].copy()
            if not a5_todos.empty and "Nombre_Alumno" in a5_todos.columns
            else pd.DataFrame()
        )
        a3 = pd.DataFrame()
        archivo_base = etiqueta.replace(" ", "_")
        alumno_documento = {"Nombre_Completo": etiqueta}

        if not a4.empty:
            fila_grupo = a4.iloc[0]
            escuela = str(fila_grupo.get("Escuela", ""))
            grado_grupo = str(fila_grupo.get("Grado_Grupo", "")).split()
            codigo = ESCUELAS_USAER.get(escuela, "")
            if codigo and len(grado_grupo) >= 2 and not a3_todos.empty:
                id_grupo = (
                    f"GRUPO-{codigo}-{grado_grupo[0]}-{grado_grupo[1]}"
                )
                if "ID_Alumno" in a3_todos.columns:
                    a3 = a3_todos[
                        a3_todos["ID_Alumno"].astype(str) == id_grupo
                    ].copy()

    st.markdown(f"### Documentos de {etiqueta}")
    tabs = st.tabs(["Anexo III", "Anexo IV", "Anexo V"])

    with tabs[0]:
        if a3.empty:
            st.info("Todavía no hay un Anexo III para este expediente.")
        else:
            st.dataframe(a3, use_container_width=True, hide_index=True)
            st.download_button(
                "Descargar Anexo III",
                anexo3_html(alumno_documento, a3),
                f"Anexo_III_{archivo_base}.html",
                "text/html",
                use_container_width=True,
                key=f"descargar_a3_{archivo_base}",
            )

    with tabs[1]:
        if a4.empty:
            st.info("Todavía no hay un Anexo IV para este expediente.")
        else:
            st.dataframe(a4, use_container_width=True, hide_index=True)
            st.download_button(
                "Descargar Anexo IV",
                anexo4_html(alumno_documento, a4),
                f"Anexo_IV_{archivo_base}.html",
                "text/html",
                use_container_width=True,
                key=f"descargar_a4_{archivo_base}",
            )

    with tabs[2]:
        if a5.empty:
            st.info("Todavía no hay un Anexo V para este expediente.")
        else:
            st.dataframe(a5, use_container_width=True, hide_index=True)
            st.download_button(
                "Descargar Anexo V",
                anexo5_html(alumno_documento, a5),
                f"Anexo_V_{archivo_base}.html",
                "text/html",
                use_container_width=True,
                key=f"descargar_a5_{archivo_base}",
            )

def direccion_page(df):
    hero("Panel de Dirección", "Indicadores para gestionar la red, no solo consultar registros.")
    a3,a4,a5=repo.anexo3(),repo.anexo4(),repo.anexo5()
    c=st.columns(4)
    for box,title,val in zip(c,["Alumnos","Anexo 3","Anexo 4","Eventos"],[len(df),len(a3),len(a4),len(a5)]):
        with box: card(title,val)
    if not a4.empty and "Nivel_Cumplimiento_Resultados" in a4.columns:
        st.markdown("### Estado de sugerencias")
        st.dataframe(a4["Nivel_Cumplimiento_Resultados"].value_counts().rename_axis("Estado").reset_index(name="Cantidad"),use_container_width=True,hide_index=True)


def visitas_page(df):
    hero(
        "Constancias de visita",
        "Registra la actividad de campo y genera la constancia oficial."
    )

    nombre_usuario = str(
        st.session_state.get("nombre", "")
    ).strip()

    rol_usuario = str(
        st.session_state.get("rol", "")
    ).strip()

    escuelas_permitidas = escuelas_asignadas(
        nombre_usuario,
        rol_usuario
    )

    if not escuelas_permitidas:
        st.error(
            "No se encontraron escuelas asignadas para tu usuario. "
            "Verifica la configuración de tu sesión."
        )
        return

    st.success(
        f"Escuelas disponibles para {nombre_usuario}: "
        f"{len(escuelas_permitidas)}"
    )

    with st.form("form_constancia", clear_on_submit=False):

        col1, col2 = st.columns([2, 1])

        with col1:
            escuela_seleccionada = st.selectbox(
                "Escuela visitada",
                escuelas_permitidas,
                key="visita_escuela"
            )

        with col2:
            fecha_visita = st.date_input(
                "Fecha de la visita",
                date.today(),
                key="visita_fecha"
            )

        st.markdown(
            "### Motivo de la visita"
        )

        col_mot1, col_mot2 = st.columns(2)

        with col_mot1:
            motivos_izq = st.multiselect(
                "Actividades de seguimiento y apoyo",
                [
                    "Observación en grupo",
                    "Entrevista con...",
                    "Trabajo interdisciplinario",
                    "Sugerencias a Maestra(o)",
                    "Sugerencias a Padres de...",
                    "Valoración a...",
                    "Revaloración de sugerencias con...",
                    "Elaboración o actualización de EPP",
                ],
                key="visita_motivos_izq"
            )

        with col_mot2:
            motivos_der = st.multiselect(
                "Intervención y juntas",
                [
                    "Intervención en Grupo",
                    "Apoyo individual en aula",
                    "Elaboración del Plan de Intervención",
                    "Consejo Técnico Escolar",
                    "Junta del Servicio de Apoyo",
                    "Junta Académica del Servicio de Apoyo",
                    "Otros",
                ],
                key="visita_motivos_der"
            )

        detalles_motivos = st.text_input(
            "Especifica nombres o detalles del motivo (opcional)",
            key="visita_detalles"
        )

        descripcion_actividad = st.text_area(
            "Breve descripción de las actividades desarrolladas",
            height=140,
            key="visita_descripcion"
        )

        generar_acta = st.form_submit_button(
            "🖨️ Generar Constancia Oficial",
            type="primary",
            use_container_width=True
        )

    if not generar_acta:
        return

    # ---------------------------------------------------------
    # DATOS DE LA ESCUELA
    # ---------------------------------------------------------

    directorio_firmas = {
        "Damián Carmona": {
            "director": "Mtra. Maribel Vargas Arana",
            "apoyo": "Mtra. Cindy Mayanín Burgos González",
        },
        "Ichcaanziho": {
            "director": "Mtra. Rennaty Maribel Puga Jimenez",
            "apoyo": "Mtra. Marycruz Caamal Coral",
        },
        "Gregorio Torres Quintero": {
            "director": "Mtro. Elmer Ariel Ontiveros Requena",
            "apoyo": "Mtra. Dolores Eugenia Cortázar Navarrete",
        },
        "Remigio Aguilar Sosa": {
            "director": "Mtro. Carlos Esteban Heredia GCantón",
            "apoyo": "Mtra. Dianely de Sugeidy Caamal Tamay",
        },
        "Elvira Parra Ávila": {
            "director": "Mtro. Manuel Jesús Alcocer Vázquez",
            "apoyo": "Mtro. Luis Jorge García Herrera",
        },
        "Manuel Sarrado": {
            "director": "Mtro. José Alberto Reyna Martínez",
            "apoyo": "Mtra. María del Rosario Pérez Vitorin",
        },
        "Domingo Solís Rodríguez": {
            "director": "Mtra. Erika Basto Ek",
            "apoyo": "Mtra. Zuemmy del Carmen Pérez Basto",
        },
        "Quintana Roo": {
            "director": "Mtro. Jorge Adrián Cetina Cach",
            "apoyo": "Mtro. Pedro Manuel Torres May",
        },
    }

    datos_escuela = directorio_firmas.get(
        escuela_seleccionada
    )

    if not datos_escuela:
        st.error(
            "No se encontró la información de firmas de esta escuela."
        )
        return

    # ---------------------------------------------------------
    # ESPECIALIDAD
    # ---------------------------------------------------------

    rol_n = normalizar_texto(rol_usuario)

    if "PSICOLOG" in rol_n:
        especialidad = "Área de Psicología - USAER 02-E"
    elif "COMUNICACI" in rol_n:
        especialidad = "Área de Comunicación - USAER 02-E"
    elif "TRABAJO" in rol_n:
        especialidad = "Área de Trabajo Social - USAER 02-E"
    else:
        especialidad = rol_usuario or "USAER 02-E"

    # ---------------------------------------------------------
    # VALIDACIÓN FINAL DE SEGURIDAD
    # ---------------------------------------------------------

    if escuela_seleccionada not in escuelas_permitidas:
        st.error(
            "Acceso denegado: esta escuela no está asignada "
            "a tu usuario."
        )
        return

    motivos = motivos_izq + motivos_der
    motivos_completos = ", ".join(motivos)

    # ---------------------------------------------------------
    # GUARDAR EN REGISTRO_VISITAS
    # ---------------------------------------------------------

    try:
        id_visita = repo.save_visita({
            "Fecha": fecha_visita.strftime("%d/%m/%Y"),
            "Escuela": escuela_seleccionada,
            "Personal": nombre_usuario,
            "Motivo": motivos_completos,
            "Observaciones": descripcion_actividad,
            "Evidencia": detalles_motivos,
            "Estatus": "GENERADA",
        })

    except Exception as ex:
        st.error(
            f"No fue posible guardar la visita en la plataforma: {ex}"
        )
        return

    # ---------------------------------------------------------
    # FUNCIONES PARA MARCAR LAS OPCIONES
    # ---------------------------------------------------------

    def marca(opcion):
        return (
            "( X )"
            if opcion in motivos
            else "(    )"
        )

    def detalle(opcion, linea="________________________"):
        if detalles_motivos and opcion in motivos:
            return f"<b>{detalles_motivos}</b>"
        return linea

    # ---------------------------------------------------------
    # CONSTANCIA OFICIAL
    # ---------------------------------------------------------

    descripcion_html = (
        descripcion_actividad
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br>")
        if descripcion_actividad
        else "<br><br><br><br>"
    )

    encabezado_html = (
        '<div style="text-align:center; margin:0 0 18px;">'
        f'<img src="{header_b64()}" '
        'alt="Encabezado oficial de USAER 02-E" '
        'style="display:block; width:100%; max-width:720px; height:auto; margin:auto;">'
        '</div>'
    )

    html_constancia = f"""
<div style="
    background-color:white;
    color:black;
    padding:40px;
    font-family:Arial,sans-serif;
    max-width:800px;
    margin:auto;
">

{encabezado_html}

<h3 style="
    text-align:center;
    font-weight:bold;
    text-decoration:underline;
    margin-bottom:25px;
">
    Constancia de visita
</h3>

<div style="font-size:14px;margin-bottom:8px;">
    Servicio de educación especial que realiza la visita:
    <u>{especialidad}</u>
</div>

<div style="font-size:14px;margin-bottom:8px;">
    Curso escolar:
    <u>{SCHOOL_YEAR}</u>
    &nbsp;&nbsp;&nbsp;&nbsp;
    Fecha de la visita:
    <u>{fecha_visita.strftime("%d/%m/%Y")}</u>
    &nbsp;&nbsp;&nbsp;&nbsp;
    Hora:
    <u>de 7:00 a 12:00 hrs</u>
</div>

<div style="font-size:14px;margin-bottom:20px;">
    Escuela:
    <u>{escuela_seleccionada}</u>
    &nbsp;&nbsp;&nbsp;&nbsp;
    Localidad:
    <u>MÉRIDA</u>
</div>

<div style="font-size:14px;margin-bottom:5px;">
    <b>Motivo de la visita:</b>
</div>

<table style="
    width:100%;
    font-size:13px;
    margin-bottom:20px;
    border-collapse:collapse;
">

<tr>

<td style="
    width:50%;
    vertical-align:top;
    border:1px dashed #ccc;
    padding:6px;
    line-height:1.6;
">

{marca("Observación en grupo")}
Observación en grupo<br>

{marca("Entrevista con...")}
Entrevista con... {detalle("Entrevista con...")}<br>

{marca("Trabajo interdisciplinario")}
Trabajo interdisciplinario<br>

{marca("Sugerencias a Maestra(o)")}
Sugerencias a Maestra(o) {detalle("Sugerencias a Maestra(o)")}<br>

{marca("Sugerencias a Padres de...")}
Sugerencias a Padres de... {detalle("Sugerencias a Padres de...")}<br>

{marca("Valoración a...")}
Valoración a... {detalle("Valoración a...")}<br>

{marca("Revaloración de sugerencias con...")}
Revaloración de sugerencias con... {detalle("Revaloración de sugerencias con...")}<br>

{marca("Elaboración o actualización de EPP")}
Elaboración o actualización de EPP

</td>

<td style="
    width:50%;
    vertical-align:top;
    border:1px dashed #ccc;
    padding:6px;
    line-height:1.6;
">

{marca("Intervención en Grupo")}
Intervención en Grupo<br>

{marca("Apoyo individual en aula")}
Apoyo individual en aula<br>

{marca("Elaboración del Plan de Intervención")}
Elaboración del Plan de Intervención<br>

{marca("Consejo Técnico Escolar")}
Consejo Técnico Escolar<br>

{marca("Junta del Servicio de Apoyo")}
Junta del Servicio de Apoyo<br>

{marca("Junta Académica del Servicio de Apoyo")}
Junta Académica del Servicio de Apoyo<br>

{marca("Otros")}
Otros: {detalle("Otros")}

</td>

</tr>
</table>

<div style="
    font-size:14px;
    margin-bottom:10px;
">
    <b>Breve descripción de las actividades desarrolladas:</b>
</div>

<div style="
    font-size:14px;
    min-height:120px;
    line-height:1.6;
">
    {descripcion_html}
</div>

<table style="
    width:100%;
    font-size:12px;
    text-align:center;
    margin-top:50px;
">

<tr>

<td style="
    width:50%;
    padding-bottom:40px;
    padding-right:20px;
">

___________________________<br>

<b>{datos_escuela["director"]}</b><br>

Directora(or) de la primaria

</td>

<td style="
    width:50%;
    padding-bottom:40px;
    padding-left:20px;
">

___________________________<br>

<b>{datos_escuela["apoyo"]}</b><br>

Maestra(o) de apoyo

</td>

</tr>

<tr>

<td style="
    width:50%;
    padding-right:20px;
">

___________________________<br>

<b>Psic. Edgar Adrián Yam Briceño MD</b><br>

Director de la USAER 02-E

</td>

<td style="
    width:50%;
    padding-left:20px;
">

___________________________<br>

<b>{nombre_usuario}</b><br>

{especialidad}

</td>

</tr>

</table>

</div>
"""

    html_impresion = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">

<title>
Constancia de Visita - {escuela_seleccionada}
</title>

<style>

@media print {{

    @page {{
        margin:1cm;
    }}

    body {{
        -webkit-print-color-adjust:exact;
        print-color-adjust:exact;
    }}

    table td {{
        border:1px dashed #ccc !important;
    }}

}}

</style>

</head>

<body
    onload="window.print()"
    style="
        padding:0;
        margin:0;
        display:flex;
        justify-content:center;
    "
>

{html_constancia}

</body>
</html>
"""

    st.success(
        f"Constancia generada correctamente. Folio: {id_visita}"
    )

    st.markdown(
        html_constancia,
        unsafe_allow_html=True
    )

    st.download_button(
        label="🖨️ Descargar Constancia para Imprimir",
        data=html_impresion,
        file_name=(
            f"Constancia_Visita_"
            f"{escuela_seleccionada.replace(' ', '_')}_"
            f"{fecha_visita.strftime('%Y%m%d')}.html"
        ),
        mime="text/html",
        use_container_width=True,
    )

    st.caption(
        "La constancia también quedó registrada en "
        "Registro_Visitas."
    )

import json
from datetime import date
import pandas as pd
import streamlit as st
from config.settings import ESCUELAS_USAER, BAP_ITEMS, BAP_FRECUENCIAS, SERVICE_NAME, SCHOOL_YEAR
from data import repository as repo
from services.expedientes import alumnos_visibles, expediente, alumno
from services.alumnos import alumnos_individuales_de_escuela
from ai.engine import generar_sugerencias
from documents.anexos import anexo4_html, anexo5_html
from ui.components import hero, card
from utils.ids import expediente_id


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
    hero("Evaluación BAP → intervención", "La captura estructurada alimenta la IA; la decisión profesional queda en tus manos.")
    if df.empty:
        st.warning("No hay alumnos disponibles.")
        return

    modo = st.radio("Tipo de evaluación", ["Individual (alumno específico)", "Grupal (contexto áulico)"], horizontal=True, key="bap_modo")
    opciones_escuela = list(ESCUELAS_USAER)

    if modo.startswith("Individual"):
    escuela = st.selectbox(
        "1. Escuela",
        opciones_escuela,
        key="bap_escuela_ind"
    )

    escuela_df = alumnos_individuales_de_escuela(
        df,
        escuela
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
        escuela_df["Nombre_Completo"].astype(str)
        == alumno_nombre
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
        alumno_nombre = st.selectbox("2. Alumno", escuela_df["Nombre_Completo"].astype(str).tolist(), key="bap_alumno_ind")
        fila = escuela_df[escuela_df["Nombre_Completo"].astype(str) == alumno_nombre].iloc[0]
        id_a = str(fila["ID_Alumno"])
        objetivo = alumno_nombre
        grado_grupo = f"{fila.get('Grado','')} {fila.get('Grupo','')}".strip()
        escuela_nombre = escuela
        contexto_base = {"tipo": "Individual", "alumno": fila.to_dict()}
    else:
        escuela = st.selectbox("Escuela a observar", opciones_escuela, key="bap_escuela_grp")
        c1,c2=st.columns(2)
        with c1: grado=st.selectbox("Grado",["1ro","2do","3ro","4to","5to","6to"],key="bap_grado_grp")
        with c2: grupo=st.selectbox("Grupo",["A","B","C","D"],key="bap_grupo_grp")
        id_a=f"GRUPO-{ESCUELAS_USAER[escuela]}-{grado}-{grupo}"
        objetivo=f"Grupo {grado} {grupo} de la escuela {escuela}"
        grado_grupo=f"{grado} {grupo}"
        escuela_nombre=escuela
        contexto_base={"tipo":"Grupal","objetivo":objetivo,"escuela":escuela}

    st.markdown("### Instrumento de Observación — Anexo III")
    with st.form("bap_form_integrado", clear_on_submit=False):
        respuestas={}
        for i,pregunta in enumerate(BAP_ITEMS,1):
            c1,c2=st.columns([3,1])
            with c1:
                freq=st.radio(f"{i}. {pregunta}",BAP_FRECUENCIAS,index=1,horizontal=True,key=f"bap_freq_{modo}_{id_a}_{i}")
            with c2:
                ori=st.checkbox("Requiere orientación",key=f"bap_ori_{modo}_{id_a}_{i}")
            respuestas[f"Item_{i}"]={"pregunta":pregunta,"frecuencia":freq,"orientacion":ori}
        observaciones=st.text_area("Observaciones cualitativas / estrategias previas",height=120,key=f"bap_obs_{id_a}")
        analizar=st.form_submit_button("Analizar BAP con IA",type="primary")

    if analizar:
        detectadas=[v for v in respuestas.values() if v["frecuencia"] in ["Nunca","Pocas veces"] or v["orientacion"]]
        contexto={**contexto_base,"expediente":expediente_id(id_a),"grado_grupo":grado_grupo,"escuela":escuela_nombre,"bap":respuestas,"barreras_detectadas":detectadas,"observaciones":observaciones}
        with st.spinner("Analizando barreras y preparando una propuesta profesional..."):
            st.session_state["ai_draft"]=generar_sugerencias(contexto)
            st.session_state["ai_context"]=contexto

    draft=st.session_state.get("ai_draft")
    if not draft:
        return

    st.markdown("### Propuesta de IA")
    st.caption("La IA propone; el profesional decide. Nada se incorpora al expediente hasta que lo apruebes.")
    area=st.text_input("Sugerencias del área",draft.get("area","Aprendizaje"),key="draft_area")
    motivo=st.text_area("Motivo por el que se brindan las sugerencias",draft.get("motivo","Resultados del Anexo 3: Barreras identificadas en el contexto áulico"),key="draft_motivo")
    sugerencias=st.text_area("Sugerencias",draft.get("sugerencias",""),height=300,key="draft_sug")
    seguimiento=st.text_input("Fecha / plazo de seguimiento",draft.get("seguimiento",""),key="draft_follow")

    if st.button("Aprobar → generar Anexo 3 y Anexo 4",type="primary",key="approve_bap"):
        hoy=str(date.today())
        contexto=st.session_state.get("ai_context",{})
        respuestas_json=json.dumps(contexto.get("bap",{}),ensure_ascii=False)
        a3=repo.save_anexo3({"Fecha":hoy,"ID_Alumno":id_a,"ID_Personal":st.session_state.get("nombre",""),"BAP_Fisicas":respuestas_json,"BAP_Actitudinales":"","BAP_Pedagogicas":"","BAP_Organizativas":"","Estatus_IA":"Procesado"})
        a4=repo.save_anexo4({"Nombre_Alumno":objetivo,"Grado_Grupo":grado_grupo,"Escuela":escuela_nombre,"Servicio_EE":SERVICE_NAME,"Sugerencias_Area":area,"Fecha_Elaboracion":hoy,"Motivo":motivo,"Fecha_Seguimiento":seguimiento,"Sugerencias":sugerencias,"Nivel_Cumplimiento_Resultados":"Pendiente de revisión","Quien_Brinda_Sugerencias":st.session_state.get("nombre","")})
        try:
            repo.ensure_expediente(expediente_id(id_a),id_a)
            repo.link_record(expediente_id(id_a),id_a,"ANEXO3",a3,hoy)
            repo.link_record(expediente_id(id_a),id_a,"ANEXO4",a4,hoy)
            repo.timeline(expediente_id(id_a),id_a,hoy,"SUGERENCIA","Anexo 4 aprobado",sugerencias,st.session_state.get("nombre",""))
        except Exception as ex:
            st.warning(f"Los formatos se guardaron. La vinculación adicional no pudo completarse: {ex}")
        st.session_state["last_anexo4"]={"id":a4,"id_alumno":id_a,"nombre":objetivo,"sugerencias":sugerencias}
        st.session_state.pop("ai_draft",None)
        st.success("Anexo 3 y Anexo 4 generados y vinculados al expediente.")

    last=st.session_state.get("last_anexo4")
    if last:
        st.divider()
        st.markdown("### Convertir la sugerencia en acción")
        st.info("Este es el punto de conexión entre Anexo 4 y Anexo 5: puedes documentar inmediatamente qué se hizo y qué resultado produjo.")
        evento=st.text_area("Acción / resultado observado",key="quick_event")
        if st.button("Registrar como evento de seguimiento",key="quick_event_btn"):
            a=alumno(df,last["id_alumno"])
            eid=repo.save_anexo5({"Fecha":str(date.today()),"Nombre_Alumno":last["nombre"],"Grado_Grupo":(f"{a.get('Grado','')} {a.get('Grupo','')}".strip() if a else ''),"Especialista":st.session_state.get("nombre",""),"Evento":evento})
            try:
                repo.link_record(expediente_id(last["id_alumno"]),last["id_alumno"],"ANEXO5",eid,str(date.today()))
                repo.timeline(expediente_id(last["id_alumno"]),last["id_alumno"],str(date.today()),"SEGUIMIENTO","Evento derivado de Anexo 4",evento,st.session_state.get("nombre",""))
            except Exception:
                pass
            st.success("La sugerencia ya tiene un evento de seguimiento asociado.")

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


def documentos_page(df):
    hero("Documentos", "Genera las salidas oficiales desde los datos ya capturados.")
    if df.empty:return
    opts=df[["ID_Alumno","Nombre_Completo"]].drop_duplicates().sort_values("Nombre_Completo")
    nombre=st.selectbox("Alumno",opts["Nombre_Completo"].tolist(),key="doc_alumno")
    id_a=opts.loc[opts["Nombre_Completo"]==nombre,"ID_Alumno"].iloc[0]; e=expediente(id_a)
    if not e["anexo4"].empty: st.download_button("Descargar Anexo IV",anexo4_html(e["alumno"],e["anexo4"]),f"Anexo_IV_{id_a}.html","text/html")
    if not e["anexo5"].empty: st.download_button("Descargar Anexo V",anexo5_html(e["alumno"],e["anexo5"]),f"Anexo_V_{id_a}.html","text/html")


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
    hero("Constancias de visita", "Registra la actividad de campo y conserva evidencia en la plataforma.")
    st.info("Esta primera versión modular conserva el registro actual; la siguiente iteración puede mover el formato oficial de constancia a un generador independiente sin duplicar datos.")
    try: st.dataframe(repo.df_sheet("Registro_Visitas"),use_container_width=True,hide_index=True)
    except Exception: st.warning("La hoja Registro_Visitas no está disponible o requiere permisos.")

"""Generador, coordinación y avisos de horarios para maestras de apoyo."""

from __future__ import annotations

import html
import json
import re
from datetime import time
from io import BytesIO

import pandas as pd
import streamlit as st
from docx import Document

from data import repository as repo
from config.settings import SCHOOL_YEAR
from documents.horarios_apoyo import generar_horario_apoyo_pdf, generar_horario_apoyo_cuadricula_pdf
from services.asignaciones import escuelas_asignadas
from services.alumnos import filtrar_alumnos_por_escuelas
from services.cronogramas import cargar_publicacion
from services.horarios import (
    DIAS,
    avisar_maestras_apoyo,
    cargar_avisos_apoyo,
    cargar_horarios_apoyo,
    cargar_restricciones,
    detectar_choques,
    franjas_semanales,
    guardar_horario_apoyo,
    guardar_restricciones,
    marcar_avisos_leidos,
    normalizar_tabla_horario,
    proponer_horario,
)
from utils.text import normalizar_texto


TIPOS_ARCHIVO_HORARIOS = ["xlsx", "xls", "csv", "doc", "docx", "png", "jpg", "jpeg", "webp", "bmp", "tif", "tiff"]


def _alumnos_de_maestra(nombre, escuela):
    """Entrega IDs y nombres de la escuela, destacando los asignados a la cuenta."""
    todos = filtrar_alumnos_por_escuelas(repo.alumnos(), [escuela]).copy()
    if todos.empty:
        return todos, todos
    columna = "Maestra de Apoyo"
    if columna not in todos:
        return todos.iloc[0:0].copy(), todos
    nombre_n = normalizar_texto(nombre).replace(".", "")
    asignacion = todos[columna].fillna("").astype(str).map(
        lambda value: normalizar_texto(value).replace(".", "")
    )
    propios = todos.loc[asignacion.map(lambda value: bool(value) and
                              (value == nombre_n or value.endswith(nombre_n) or nombre_n.endswith(value)))].copy()
    return propios, todos


def _grupo_alumno(row):
    return f"{str(row.get('Grado', '')).strip()} {str(row.get('Grupo', '')).strip()}".strip()


def _leer_imagen_horario(archivo):
    """Propone filas de una imagen; siempre requieren revisión antes de guardarse."""
    from google.genai import types
    from ai.engine import client

    cli = client()
    if cli is None:
        raise RuntimeError("La lectura de imágenes no está configurada. Transcribe los bloques en la tabla inferior.")
    extension = archivo.name.rsplit(".", 1)[-1].lower()
    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
            "webp": "image/webp"}.get(extension)
    if not mime:
        raise ValueError("Para lectura asistida usa JPG, PNG o WebP; los demás formatos siguen disponibles como referencia.")
    from config.settings import GEMINI_MODEL
    prompt = (
        "Lee SOLO los bloques de este horario escolar. Devuelve un arreglo JSON, sin markdown, "
        "con un objeto por bloque y claves Día, Inicio, Fin, Grupo, Actividad, Responsable. "
        "Usa lunes a viernes y horas HH:MM en formato de 24 horas. Si no distingues un dato, "
        "déjalo vacío. No inventes grupos, materias ni horas. No incluyas encabezados vacíos."
    )
    response = cli.models.generate_content(
        model=GEMINI_MODEL,
        contents=[prompt, types.Part.from_bytes(data=archivo.getvalue(), mime_type=mime)],
        config={"temperature": 0},
    )
    texto = re.sub(r"^```(?:json)?\s*|\s*```$", "", (response.text or "").strip(), flags=re.I)
    datos = json.loads(texto)
    if not isinstance(datos, list) or not datos:
        raise ValueError("No se reconocieron bloques de horario. Usa la captura manual.")
    return normalizar_tabla_horario(pd.DataFrame(datos))


def _leer_archivo(archivo):
    contenido = archivo.getvalue()
    nombre = archivo.name.lower()
    if nombre.endswith(".csv"):
        try:
            frame = pd.read_csv(BytesIO(contenido), encoding="utf-8-sig")
        except UnicodeDecodeError:
            frame = pd.read_csv(BytesIO(contenido), encoding="latin-1")
        return [(archivo.name, normalizar_tabla_horario(frame))], []
    if nombre.endswith(".docx"):
        documento = Document(BytesIO(contenido))
        salida = []
        errores = []
        for indice, tabla in enumerate(documento.tables, start=1):
            filas = [[celda.text.strip() for celda in fila.cells] for fila in tabla.rows]
            if len(filas) < 2:
                continue
            encabezados = filas[0]
            if not any(encabezados):
                errores.append(f"Tabla {indice}: falta la fila de encabezados.")
                continue
            ancho = len(encabezados)
            frame = pd.DataFrame(
                [(fila + [""] * ancho)[:ancho] for fila in filas[1:]],
                columns=encabezados,
            )
            try:
                salida.append((f"{archivo.name} · Tabla {indice}", normalizar_tabla_horario(frame)))
            except ValueError as exc:
                errores.append(f"Tabla {indice}: {exc}")
        if not salida:
            detalle = "; ".join(errores) or "No contiene una tabla de horario que pueda convertirse automáticamente."
            raise ValueError(f"{detalle} Puedes usar el archivo como referencia y transcribirlo en la tabla de captura.")
        return salida, errores
    hojas = pd.read_excel(BytesIO(contenido), sheet_name=None)
    salida = []
    errores = []
    for hoja, frame in hojas.items():
        try:
            salida.append((f"{archivo.name} · {hoja}", normalizar_tabla_horario(frame)))
        except ValueError as exc:
            errores.append(f"{hoja}: {exc}")
    if not salida:
        detalle = "; ".join(errores) or "El archivo no contiene hojas con horarios."
        raise ValueError(detalle)
    return salida, errores


def _tabla_vista(frame):
    columnas = [col for col in ("Dia", "Inicio", "Fin", "Grupo", "Alumnos", "Modalidad", "Espacio", "Actividad", "Responsable", "Maestra") if col in frame.columns]
    salida = frame[columnas].copy()
    if "Dia" in salida:
        salida["_orden"] = salida["Dia"].map({day: i for i, day in enumerate(DIAS)})
        salida = salida.sort_values(["_orden", "Inicio", "Grupo"], kind="stable").drop(columns="_orden")
    return salida.reset_index(drop=True)


def _avisos_maestra(nombre, escuela):
    try:
        avisos = cargar_avisos_apoyo(nombre)
    except Exception:
        st.warning(
            "No se pudieron consultar los avisos de cronogramas en este momento. "
            "Puedes continuar con tus horarios; no se modificó ni eliminó información. "
            "Vuelve a intentarlo más tarde."
        )
        return
    avisos = [row for row in avisos if normalizar_texto(row.get("Escuela", "")) == normalizar_texto(escuela)]
    if not avisos:
        st.info("Aquí aparecerán los avisos del equipo especialista para esta escuela.")
        return
    st.markdown("### Avisos de cronogramas del equipo especialista")
    tabla = pd.DataFrame([
        {"Estado": row.get("Estado", ""), "Fecha": row.get("Fecha", ""), "Mes": row.get("Mes", ""),
         "Escuela": row.get("Escuela", ""), "Especialista": row.get("Especialista", ""),
         "Aviso": row.get("Resumen", "")}
        for row in avisos
    ])
    st.dataframe(tabla, hide_index=True, width="stretch")
    opciones = [row for row in avisos if str(row.get("ID_Publicacion", "")).strip()]
    if opciones:
        elegido = st.selectbox(
            "Consultar cronograma recibido",
            opciones,
            format_func=lambda row: f"{row.get('Mes', '')} · {row.get('Especialista', '')} · {row.get('Estado', '')}",
            key=f"aviso_cronograma_{normalizar_texto(escuela)}",
        )
        try:
            detalle = cargar_publicacion(elegido["ID_Publicacion"])
            detalle = [row for row in detalle if normalizar_texto(row.get("Escuela", "")) == normalizar_texto(escuela)]
            if detalle:
                st.dataframe(pd.DataFrame(detalle), hide_index=True, width="stretch")
            else:
                st.caption("El aviso se conserva. Esta versión histórica no tiene detalle consultable desde la hoja actual.")
        except Exception as exc:
            st.warning(f"El aviso permanece guardado; no se pudo cargar el detalle del cronograma: {exc}")
    pendientes = [row for row in avisos if str(row.get("Estado", "")).upper() == "PENDIENTE"]
    if pendientes and st.button("Marcar avisos como vistos", key=f"marcar_avisos_{normalizar_texto(escuela)}"):
        try:
            marcar_avisos_leidos([row["ID_Aviso"] for row in pendientes])
            st.success("Avisos marcados como vistos. El historial se conservó.")
            st.rerun()
        except Exception as exc:
            st.error(f"No se pudo actualizar el estado de lectura: {exc}")


def _cuadricula_horario(nombre, escuela, restricciones, horarios_equipo):
    """Editor visual semanal; conserva el borrador hasta que la docente guarde."""
    prefijo = f"cuadricula_{normalizar_texto(nombre)}_{normalizar_texto(escuela)}"
    clave_franjas, clave_filas = f"{prefijo}_franjas", f"{prefijo}_filas"
    st.markdown("### Mi plantilla semanal · lunes a viernes")
    st.caption("Elige cuánto dura cada módulo. Puedes escribir una duración repetida (60) o varias (60,60,30,60); la última se repite hasta terminar la jornada.")
    c1, c2, c3, c4 = st.columns([1, 1, 2, 1])
    with c1:
        inicio = st.time_input("Inicio", value=time(7, 0), key=f"{prefijo}_inicio")
    with c2:
        fin = st.time_input("Fin", value=time(13, 0), key=f"{prefijo}_fin")
    with c3:
        duraciones = st.text_input("Minutos por módulo", value="60", key=f"{prefijo}_duraciones")
    with c4:
        aplicar = st.button("Aplicar módulos", key=f"{prefijo}_aplicar", type="primary")
    if aplicar or clave_franjas not in st.session_state:
        try:
            st.session_state[clave_franjas] = franjas_semanales(inicio, fin, duraciones)
        except ValueError as exc:
            st.error(str(exc))
            return
    franjas = st.session_state[clave_franjas]
    borrador = st.session_state.setdefault(clave_filas, {})
    propia = (horarios_equipo.loc[horarios_equipo["Maestra"].astype(str).eq(nombre)].copy()
              if not horarios_equipo.empty and "Maestra" in horarios_equipo else pd.DataFrame())
    if not propia.empty and st.button("Cargar mi horario vigente para editarlo en esta plantilla", key=f"{prefijo}_cargar"):
        for item in propia.to_dict("records"):
            clave = f"{item.get('Dia')}|{item.get('Inicio')}|{item.get('Fin')}"
            borrador[clave] = item
        franjas_guardadas = sorted({(str(row["Inicio"]), str(row["Fin"]))
                                   for row in propia.to_dict("records")})
        if franjas_guardadas:
            st.session_state[clave_franjas] = franjas_guardadas
        st.session_state[f"{prefijo}_editor_version"] = st.session_state.get(f"{prefijo}_editor_version", 0) + 1
        st.rerun()

    filas = list(borrador.values())
    try:
        choques = detectar_choques(filas, restricciones, horarios_equipo) if filas else pd.DataFrame()
    except ValueError as exc:
        st.error(f"Hay una hora o día inválido en el borrador: {exc}")
        return
    celdas_conflicto = {(str(row["Día"]), str(row["Horario propuesto"]).replace("–", "|"))
                        for row in choques.to_dict("records")} if not choques.empty else set()
    dias = list(DIAS)
    tabla = ["<style>.horario-apoyo-grid{width:100%;min-width:850px;border-collapse:collapse;table-layout:fixed;font-family:Arial,sans-serif}"
             ".horario-apoyo-grid th{background:#d9eaf6;color:#173b57;padding:12px;border:1px solid #a9bfce;font-size:16px}"
             ".horario-apoyo-grid td{height:86px;vertical-align:top;border:1px solid #a9bfce;padding:9px;white-space:pre-wrap;overflow-wrap:anywhere;font-size:14px}"
             ".horario-apoyo-grid .hora{background:#f0f5f9;text-align:center;font-weight:bold;width:12%}"
             ".horario-apoyo-grid .ocupado{background:#eef8f1}.horario-apoyo-grid .choque{background:#ffe5e5}"
             ".horario-apoyo-grid .vacio{color:#8195a6}</style>",
             "<div style='overflow-x:auto'><table class='horario-apoyo-grid'><thead><tr><th>Hora</th>"]
    tabla.extend(f"<th>{html.escape(dia)}</th>" for dia in dias)
    tabla.append("</tr></thead><tbody>")
    for desde, hasta in franjas:
        tabla.append(f"<tr><td class='hora'>{html.escape(desde)}<br>–<br>{html.escape(hasta)}</td>")
        for dia in dias:
            item = borrador.get(f"{dia}|{desde}|{hasta}")
            conflicto = (dia, f"{desde}|{hasta}") in celdas_conflicto
            contenido = "\n".join(filter(None, (
                str(item.get("Grupo", "")).strip() if item else "",
                str(item.get("Alumnos", "")).strip() if item else "",
                str(item.get("Actividad", "")).strip() if item else "",
            ))) if item else ""
            clase = "choque" if conflicto else ("ocupado" if item else "vacio")
            tabla.append(f"<td class='{clase}'>{html.escape(contenido) if contenido else 'Sin capturar'}</td>")
        tabla.append("</tr>")
    tabla.append("</tbody></table></div>")
    st.markdown("".join(tabla), unsafe_allow_html=True)
    if not choques.empty:
        st.error("Se detectaron choques con materias u otros bloques. Revisa la tabla antes de guardar.")
        st.dataframe(choques, hide_index=True, width="stretch")
    fuera = [row for row in filas if (str(row.get("Inicio", "")), str(row.get("Fin", ""))) not in franjas]
    if fuera:
        st.warning(f"Hay {len(fuera)} bloque(s) de un diseño anterior fuera de las franjas visibles; se conservan en el borrador.")
        st.dataframe(pd.DataFrame(fuera), hide_index=True, width="stretch")

    st.markdown("#### Capturar o editar un espacio")
    dia_elegido = st.selectbox("Día", dias, key=f"{prefijo}_dia")
    franja_elegida = st.selectbox("Módulo", franjas,
                                format_func=lambda x: f"{x[0]} – {x[1]}", key=f"{prefijo}_modulo")
    desde, hasta = franja_elegida
    clave = f"{dia_elegido}|{desde}|{hasta}"
    actual = borrador.get(clave, {})
    version = st.session_state.get(f"{prefijo}_editor_version", 0)
    clave_editor = f"{prefijo}_{clave}_{version}"
    modo_inicial = 1 if str(actual.get("ID_Alumnos", "")).strip() else (0 if str(actual.get("Grupo", "")).strip() else 2)
    modo = st.radio("Qué atenderás en este espacio", ["Grado/grupo", "Alumno(s)", "Actividad libre"],
                    index=modo_inicial, horizontal=True, key=f"{clave_editor}_modo")
    try:
        propios, escuela_completa = _alumnos_de_maestra(nombre, escuela)
    except Exception as exc:
        st.error(f"No se pudo cargar el padrón de esta escuela: {exc}")
        return
    ampliar = False
    if modo == "Alumno(s)" and len(propios) < len(escuela_completa):
        ids_guardados = {x for x in str(actual.get("ID_Alumnos", "")).split(",") if x}
        ids_propios = set(propios.get("ID_Alumno", pd.Series(dtype=str)).fillna("").astype(str))
        ampliar = st.checkbox("Mostrar también alumnos de esta escuela sin asignación a mi nombre",
                             value=bool(ids_guardados - ids_propios),
                             help="Útil si un registro de la base central aún no tiene la maestra correcta.",
                             key=f"{clave_editor}_ampliar")
    visibles = escuela_completa if ampliar else propios
    opciones_grupo = sorted({_grupo_alumno(row) for row in escuela_completa.to_dict("records")
                             if _grupo_alumno(row)})
    grupo = ""
    ids = []
    if modo == "Grado/grupo":
        grupo_anterior = str(actual.get("Grupo", ""))
        opciones = ["", *opciones_grupo]
        grupo = st.selectbox("Grado y grupo", opciones,
                             index=opciones.index(grupo_anterior) if grupo_anterior in opciones else 0,
                             key=f"{clave_editor}_grupo")
    elif modo == "Alumno(s)":
        por_id = {str(row.get("ID_Alumno", "")): row for row in visibles.to_dict("records")
                  if str(row.get("ID_Alumno", "")).strip()}
        ids_previos = [x for x in str(actual.get("ID_Alumnos", "")).split(",") if x in por_id]
        ids = st.multiselect("Alumno o alumnos", list(por_id), default=ids_previos,
                             format_func=lambda x: f"{por_id[x].get('Nombre_Completo', '')} · {_grupo_alumno(por_id[x])} · {x}",
                             key=f"{clave_editor}_alumnos")
    actividad = st.text_area("Actividad o propósito (puedes redactarla libremente)",
                             value=str(actual.get("Actividad", "")),
                             key=f"{clave_editor}_actividad")
    c_modalidad, c_espacio = st.columns(2)
    with c_modalidad:
        modalidad = st.selectbox("Modalidad", ["Grupal", "Subgrupal", "Individual", "Otra"],
                                  key=f"{clave_editor}_modalidad")
    with c_espacio:
        espacio = st.selectbox("Espacio", ["Aula regular", "Aula de apoyo", "Otro"],
                               key=f"{clave_editor}_espacio")
    c_guardar, c_vaciar = st.columns(2)
    with c_guardar:
        if st.button("Añadir o actualizar este bloque", type="primary", key=f"{prefijo}_guardar_{clave}"):
            if modo == "Grado/grupo" and not grupo:
                st.warning("Selecciona el grado o grupo.")
            elif modo == "Alumno(s)" and not ids:
                st.warning("Selecciona al menos un alumno de la escuela.")
            elif modo == "Actividad libre" and not actividad.strip():
                st.warning("Escribe la actividad.")
            else:
                por_id = {str(row.get("ID_Alumno", "")): row for row in visibles.to_dict("records")}
                elegidos = [por_id[x] for x in ids]
                grupos = sorted({_grupo_alumno(row) for row in elegidos if _grupo_alumno(row)})
                borrador[clave] = {
                    "Dia": dia_elegido, "Inicio": desde, "Fin": hasta,
                    "Grupo": grupo or ", ".join(grupos),
                    "Alumnos": "; ".join(str(row.get("Nombre_Completo", "")) for row in elegidos),
                    "ID_Alumnos": ",".join(ids),
                    "Actividad": actividad.strip() or ("Atención individual" if len(ids) == 1 else "Atención de apoyo"),
                    "Modalidad": modalidad, "Espacio": espacio, "Maestra": nombre,
                }
                st.rerun()
    with c_vaciar:
        if actual and st.button("Quitar este bloque del borrador", key=f"{prefijo}_vaciar_{clave}"):
            borrador.pop(clave, None)
            st.session_state[f"{prefijo}_editor_version"] = version + 1
            st.rerun()

    confirmada = st.checkbox("Confirmo que revisé los bloques y que el horario está listo",
                             key=f"{prefijo}_confirmado")
    listo = bool(borrador) and confirmada and choques.empty and not fuera
    if listo:
        try:
            pdf = generar_horario_apoyo_cuadricula_pdf(escuela, nombre, filas, franjas)
            st.download_button("Descargar horario oficial horizontal (PDF)", pdf,
                               file_name=f"Horario_Semanal_{normalizar_texto(nombre).replace(' ', '_')}.pdf",
                               mime="application/pdf", key=f"{prefijo}_descargar")
        except Exception as exc:
            st.error(f"No se pudo preparar el PDF: {exc}")
            listo = False
    if st.button("Guardar esta versión en la base central", type="primary",
                 disabled=not listo, key=f"{prefijo}_publicar"):
        try:
            guardar_horario_apoyo(nombre, escuela, filas)
            st.success("Horario guardado. La versión anterior se conserva.")
            st.rerun()
        except Exception as exc:
            st.error(f"No se pudo guardar el horario: {exc}")


def horarios_apoyo_page():
    nombre = str(st.session_state.get("nombre", "")).strip()
    rol = str(st.session_state.get("rol", "")).strip()
    if "APOYO" not in normalizar_texto(rol) or "DIRECTOR" in normalizar_texto(rol):
        st.error("Este espacio es exclusivo para las cuentas de maestras de apoyo.")
        return
    escuelas = escuelas_asignadas(nombre, rol)
    if not escuelas:
        st.error("No hay escuela asignada a esta cuenta; no se muestran horarios de otras escuelas.")
        return

    st.title("Horarios de apoyo")
    st.caption("Organiza tus sesiones, consulta referencias de la escuela y recibe aquí los cronogramas del equipo especialista.")
    escuela = st.selectbox("Escuela asignada", escuelas, key="horario_apoyo_escuela")
    _avisos_maestra(nombre, escuela)
    st.divider()

    try:
        restricciones = cargar_restricciones(escuela)
        horarios_equipo = cargar_horarios_apoyo(escuela)
    except Exception as exc:
        st.error(f"No se pudieron leer los horarios compartidos: {exc}")
        return

    st.markdown("### Cargar horarios de referencia")
    st.caption("Carga Excel/CSV, documentos Word (.doc/.docx) o imágenes. Las tablas compatibles de .docx se leen automáticamente; las imágenes, .doc y formatos no tabulares se muestran como referencia para transcribir. Los horarios anteriores se conservan como historial.")
    plantilla = pd.DataFrame([{"Día": "Lunes", "Inicio": "08:00", "Fin": "08:50", "Actividad": "Inglés", "Grupo": "2A", "Responsable": ""}])
    st.download_button("Descargar plantilla de horario", plantilla.to_csv(index=False).encode("utf-8-sig"), "Plantilla_horario_escolar.csv", "text/csv", key="plantilla_horario_apoyo")
    archivos = st.file_uploader(
        "Horarios de materias, docentes y otras maestras de apoyo",
        type=TIPOS_ARCHIVO_HORARIOS, accept_multiple_files=True, key="carga_restricciones_horario",
    )
    preparados = []
    referencias = []
    errores = []
    for archivo in archivos or []:
        try:
            extension = archivo.name.rsplit(".", 1)[-1].lower() if "." in archivo.name else ""
            if extension in {"png", "jpg", "jpeg", "webp", "bmp", "tif", "tiff"}:
                referencias.append((archivo, "imagen"))
                continue
            if extension == "doc":
                referencias.append((archivo, "word_antiguo"))
                continue
            hojas_validas, avisos_hojas = _leer_archivo(archivo)
            preparados.extend(hojas_validas)
            errores.extend(f"{archivo.name} · {aviso}" for aviso in avisos_hojas)
        except Exception as exc:
            if archivo.name.lower().endswith(".docx"):
                referencias.append((archivo, "word"))
                errores.append(f"{archivo.name}: {exc}")
            else:
                errores.append(f"{archivo.name}: {exc}")
    for archivo, tipo in referencias:
        if tipo == "imagen":
            with st.expander(f"Vista de referencia: {archivo.name}"):
                st.image(archivo.getvalue(), caption=archivo.name, width="stretch")
                clave_imagen = f"bloques_imagen_{normalizar_texto(nombre)}_{normalizar_texto(escuela)}_{archivo.name}_{len(archivo.getvalue())}"
                if st.button("Leer bloques de esta imagen", key=f"leer_{clave_imagen}",
                             help="Envía la imagen al servicio de lectura configurado; revisa los datos detectados antes de guardarlos."):
                    try:
                        st.session_state[clave_imagen] = _leer_imagen_horario(archivo)
                    except Exception as exc:
                        st.warning(f"No se pudo leer esta imagen: {exc}")
                if clave_imagen in st.session_state:
                    st.caption("Revisa día, horas, grupo y materia detectados antes de guardar. Corrige aquí cualquier lectura errónea.")
                    revisado = st.data_editor(
                        st.session_state[clave_imagen], num_rows="dynamic", hide_index=True,
                        width="stretch", key=f"revision_{clave_imagen}",
                    )
                    try:
                        preparados.append((f"{archivo.name} · lectura revisada", normalizar_tabla_horario(revisado.rename(
                            columns={"Dia": "Día", "Actividad": "Materia"}
                        ))))
                    except ValueError as exc:
                        st.warning(f"Corrige las filas reconocidas: {exc}")
        elif tipo == "word":
            with st.expander(f"Texto de referencia: {archivo.name}"):
                documento = Document(BytesIO(archivo.getvalue()))
                texto = "\n".join(parrafo.text for parrafo in documento.paragraphs if parrafo.text.strip())
                st.text(texto or "El documento no contiene texto extraíble; usa la vista en Word y captura los bloques manualmente.")
        else:
            st.info(f"{archivo.name} está adjunto como referencia. Ábrelo en Word y transcribe sus bloques en la tabla de captura.")
    if errores:
        for error in errores:
            st.warning(error)
    captura_manual = None
    if referencias:
        st.info("Transcribe abajo los bloques de las imágenes o documentos sin tabla reconocible. Revisa los datos antes de guardarlos.")
        captura_manual = st.data_editor(
            pd.DataFrame([{"Día": "", "Inicio": "", "Fin": "", "Grupo": "", "Actividad": "", "Responsable": ""}]),
            num_rows="dynamic", hide_index=True, width="stretch",
            column_config={
                "Día": st.column_config.SelectboxColumn("Día", options=["", *DIAS]),
                "Inicio": st.column_config.TextColumn("Inicio · HH:MM"),
                "Fin": st.column_config.TextColumn("Fin · HH:MM"),
                "Grupo": st.column_config.TextColumn("Grupo"),
                "Actividad": st.column_config.TextColumn("Actividad / materia", width="large"),
                "Responsable": st.column_config.TextColumn("Responsable"),
            },
            key=f"captura_manual_horario_{normalizar_texto(escuela)}",
        )
    if preparados or referencias:
        vista_carga = pd.concat(
            [frame.assign(Archivo=origen) for origen, frame in preparados],
            ignore_index=True,
        ) if preparados else pd.DataFrame()
        if not vista_carga.empty:
            st.dataframe(vista_carga, hide_index=True, width="stretch")
        if st.button("Guardar horarios de referencia para esta escuela", type="primary", key="guardar_restricciones_horario"):
            try:
                total = 0
                filas_guardar = list(preparados)
                if captura_manual is not None:
                    captura = captura_manual.fillna("").astype(str)
                    captura = captura.loc[captura.apply(lambda fila: any(valor.strip() for valor in fila), axis=1)]
                    if not captura.empty:
                        filas_guardar.append(("Captura desde archivo de referencia", normalizar_tabla_horario(captura)))
                if not filas_guardar:
                    st.warning("No hay horarios transcritos para guardar todavía.")
                    st.stop()
                for origen, frame in filas_guardar:
                    _, cuenta = guardar_restricciones(escuela, nombre, origen, frame)
                    total += cuenta
                st.success(f"Se añadieron {total} bloques de referencia. Las versiones sustituidas permanecen en el historial.")
                st.rerun()
            except Exception as exc:
                st.error(f"No se pudieron guardar todos los horarios: {exc}. Los registros guardados se conservan; revisa el historial antes de reintentar.")

    if not restricciones.empty:
        st.markdown("#### Horarios de referencia activos")
        st.dataframe(_tabla_vista(restricciones), hide_index=True, width="stretch")
    if not horarios_equipo.empty:
        st.markdown("#### Horarios guardados de otras maestras de esta escuela")
        colegas = horarios_equipo.loc[horarios_equipo["Maestra"].astype(str).ne(nombre)].copy() if "Maestra" in horarios_equipo else horarios_equipo.iloc[0:0]
        if colegas.empty:
            st.caption("Aún no hay horarios de otras maestras disponibles.")
        else:
            colegas_opciones = sorted(colegas["Maestra"].dropna().astype(str).unique().tolist())
            colega = st.selectbox("Consultar horario de una colega", colegas_opciones, key=f"horario_colega_{normalizar_texto(escuela)}")
            st.dataframe(_tabla_vista(colegas.loc[colegas["Maestra"].astype(str).eq(colega)]), hide_index=True, width="stretch")

    st.divider()
    _cuadricula_horario(nombre, escuela, restricciones, horarios_equipo)
    st.divider()
    st.markdown("### Proponer mi horario semanal")
    c1, c2, c3 = st.columns(3)
    with c1:
        grupos_texto = st.text_input("Grados y grupos", placeholder="1A, 2A, 3B", key="horario_grupos")
        sesiones = st.number_input("Sesiones por grupo a la semana", min_value=1, max_value=10, value=2, key="horario_sesiones")
    with c2:
        hora_inicio = st.time_input("Inicio de la jornada", value=time(8, 0), key="horario_inicio")
        hora_fin = st.time_input("Fin de la jornada", value=time(13, 0), key="horario_fin")
    with c3:
        duracion = st.number_input("Duración de cada sesión (minutos)", min_value=15, max_value=180, value=50, step=5, key="horario_duracion")
        modalidad = st.selectbox(
            "Modalidad de atención",
            ["Grupal", "Subgrupal", "Individual"],
            key="horario_modalidad",
            help="El manual contempla atención grupal, subgrupal e individual.",
        )
        espacio = st.selectbox(
            "Espacio de atención",
            ["Aula regular", "Aula de apoyo", "Otro"],
            key="horario_espacio",
        )
        st.caption("La propuesta evita cruces con los horarios cargados y con sesiones de apoyo del mismo grupo.")

    proposal_key = f"propuesta_horario_apoyo_{normalizar_texto(nombre)}_{normalizar_texto(escuela)}"
    if st.button("Generar propuesta de horario", type="primary", key=f"generar_{proposal_key}"):
        try:
            grupos = [parte.strip() for parte in grupos_texto.split(",") if parte.strip()]
            propuesta, origen = proponer_horario(
                grupos, int(sesiones), int(duracion), hora_inicio, hora_fin,
                restricciones, horarios_equipo, maestra=nombre,
                modalidad=modalidad, espacio=espacio,
            )
            st.session_state[proposal_key] = propuesta
            st.session_state[proposal_key + "_origen"] = origen
        except Exception as exc:
            st.error(f"No se pudo proponer el horario: {exc}")

    propuesta = st.session_state.get(proposal_key)
    if propuesta is not None:
        st.info(f"Borrador: {st.session_state.get(proposal_key + '_origen', 'editable')}. Revisa y ajusta las sesiones antes de guardar.")
        version_editor = st.session_state.get(proposal_key + "_version", 0)
        editada = st.data_editor(
            propuesta,
            num_rows="dynamic", hide_index=True, width="stretch",
            column_config={
                "Dia": st.column_config.SelectboxColumn("Día", options=list(DIAS)),
                "Inicio": st.column_config.TextColumn("Inicio · HH:MM"),
                "Fin": st.column_config.TextColumn("Fin · HH:MM"),
                "Grupo": st.column_config.TextColumn("Grupo"),
                "Modalidad": st.column_config.SelectboxColumn(
                    "Modalidad", options=["", "Grupal", "Subgrupal", "Individual"],
                ),
                "Espacio": st.column_config.SelectboxColumn(
                    "Espacio", options=["", "Aula regular", "Aula de apoyo", "Otro"],
                ),
                "Actividad": st.column_config.TextColumn("Actividad", width="large"),
                "Maestra": st.column_config.TextColumn("Maestra", disabled=True),
            },
            key=f"editor_horario_apoyo_{normalizar_texto(escuela)}_{version_editor}",
        )
        conflictos = detectar_choques(editada.to_dict("records"), restricciones, horarios_equipo)
        incompletas = editada[["Modalidad", "Espacio"]].fillna("").astype(str).apply(
            lambda columna: columna.str.strip().eq("")
        ).any(axis=1)
        if incompletas.any():
            st.warning("Completa modalidad y espacio de atención en cada sesión para guardar el horario oficial.")
        if not conflictos.empty:
            st.error("Hay cruces; corrígelos antes de guardar.")
            st.dataframe(conflictos, hide_index=True, width="stretch")
        else:
            pdf_borrador = generar_horario_apoyo_pdf(escuela, nombre, editada.to_dict("records"))
            st.download_button(
                "Descargar vista previa del horario (PDF)",
                data=pdf_borrador,
                file_name=f"Horario_Apoyo_{normalizar_texto(nombre).replace(' ', '_')}.pdf",
                mime="application/pdf",
                key=f"descargar_borrador_{proposal_key}_{version_editor}",
            )
        if st.button("Guardar mi horario en la base central", type="primary", disabled=not conflictos.empty or incompletas.any(), key=f"guardar_{proposal_key}"):
            try:
                guardar_horario_apoyo(nombre, escuela, editada)
                st.success("Horario guardado. La versión anterior permanece en el historial.")
                st.session_state.pop(proposal_key, None)
                st.rerun()
            except Exception as exc:
                st.error(f"No se pudo guardar el horario: {exc}")

    propio = horarios_equipo.loc[horarios_equipo["Maestra"].astype(str).eq(nombre)].copy() if not horarios_equipo.empty and "Maestra" in horarios_equipo.columns else pd.DataFrame()
    if not propio.empty:
        st.markdown("### Mi horario guardado")
        propia_vista = _tabla_vista(propio)
        st.dataframe(propia_vista, hide_index=True, width="stretch")
        c_editar, c_descargar = st.columns(2)
        with c_editar:
            if st.button("Editar mi horario vigente", key=f"editar_horario_{normalizar_texto(escuela)}"):
                columnas_edicion = ["Dia", "Inicio", "Fin", "Grupo", "Modalidad", "Espacio", "Actividad", "Maestra"]
                borrador = propio.reindex(columns=columnas_edicion).fillna("").copy()
                borrador["Maestra"] = nombre
                st.session_state[proposal_key] = borrador
                st.session_state[proposal_key + "_origen"] = "horario guardado cargado para edición"
                st.session_state[proposal_key + "_version"] = st.session_state.get(proposal_key + "_version", 0) + 1
                st.rerun()
        with c_descargar:
            franjas_guardadas = sorted({(str(row["Inicio"]), str(row["Fin"]))
                                       for row in propio.to_dict("records")})
            pdf_guardado = generar_horario_apoyo_cuadricula_pdf(
                escuela, nombre, propio.to_dict("records"), franjas_guardadas,
            )
            st.download_button(
                "Descargar mi horario vigente (PDF oficial)",
                data=pdf_guardado,
                file_name=f"Horario_Apoyo_{normalizar_texto(nombre).replace(' ', '_')}_{normalizar_texto(escuela).replace(' ', '_')}.pdf",
                mime="application/pdf",
                type="primary",
                key=f"descargar_horario_{normalizar_texto(escuela)}",
            )
        st.caption(f"Ciclo escolar {SCHOOL_YEAR}. Cada guardado agrega una nueva versión y conserva la anterior.")


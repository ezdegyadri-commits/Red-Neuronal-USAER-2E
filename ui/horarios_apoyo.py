"""Generador, coordinación y avisos de horarios para maestras de apoyo."""

from __future__ import annotations

import html
import hashlib
import json
import re
from datetime import time
from io import BytesIO

import pandas as pd
import streamlit as st
from docx import Document

from data import repository as repo
from config.settings import ESCUELAS_USAER, SCHOOL_YEAR
from documents.horarios_apoyo import generar_horario_apoyo_cuadricula_pdf
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
    guardar_restricciones_lote,
    marcar_avisos_leidos,
    normalizar_tabla_horario,
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


def _clave_imagen_horario(nombre, escuela, archivo):
    """Separa lecturas por docente, escuela y contenido, no solo por nombre de archivo."""
    huella = hashlib.sha256(archivo.getvalue()).hexdigest()[:16]
    return f"bloques_imagen_{normalizar_texto(nombre)}_{normalizar_texto(escuela)}_{huella}"


def _limpiar_lectura_imagen(nombre, escuela, archivo):
    """Olvida solo la lectura temporal de una imagen; no toca horarios guardados."""
    clave = _clave_imagen_horario(nombre, escuela, archivo)
    for key in (clave, f"ocr_error_{clave}"):
        st.session_state.pop(key, None)


def _borrador_de_horario(filas):
    """Construye un borrador nuevo desde la versión vigente, sin mezclar residuos."""
    return {
        f"{item.get('Dia')}|{item.get('Inicio')}|{item.get('Fin')}": item
        for item in filas
    }


def _bloques_desde_ocr_tsv(datos, ancho_imagen, alto_imagen):
    """Interpreta filas sencillas de una tabla horaria a partir de cajas OCR."""
    dias = {
        "LUNES": "Lunes", "MARTES": "Martes", "MIERCOLES": "Miércoles",
        "JUEVES": "Jueves", "VIERNES": "Viernes",
    }
    palabras = []
    cantidad = len(datos.get("text", []))
    for indice in range(cantidad):
        texto = str(datos["text"][indice]).strip()
        try:
            confianza = float(datos.get("conf", [100] * cantidad)[indice])
            izquierda = int(datos["left"][indice])
            arriba = int(datos["top"][indice])
            ancho = int(datos["width"][indice])
            alto = int(datos["height"][indice])
        except (TypeError, ValueError, IndexError):
            continue
        if texto and confianza >= 10 and ancho >= 0 and alto > 0:
            palabras.append({"texto": texto, "x": izquierda + ancho / 2,
                             "y": arriba + alto / 2, "alto": alto})
    if not palabras:
        raise ValueError("No se detectó texto legible.")

    centros_dia = {}
    for palabra in palabras:
        dia = dias.get(normalizar_texto(palabra["texto"]).strip(".,;:"))
        if dia:
            centros_dia.setdefault(dia, []).append(palabra["x"])
    centros_dia = {dia: sum(xs) / len(xs) for dia, xs in centros_dia.items()}
    if len(centros_dia) < 2:
        raise ValueError("No se reconocieron suficientes encabezados de días para ordenar el horario.")
    columnas = sorted(centros_dia.items(), key=lambda item: item[1])
    centros_x = [x for _dia, x in columnas]
    alto_medio = sorted(p["alto"] for p in palabras)[len(palabras) // 2]
    tolerancia_y = max(12, alto_medio * 1.3)
    bandas = []
    for palabra in sorted(palabras, key=lambda p: p["y"]):
        if not bandas or palabra["y"] - bandas[-1]["y"] > tolerancia_y:
            bandas.append({"y": palabra["y"], "palabras": [palabra]})
        else:
            banda = bandas[-1]
            banda["palabras"].append(palabra)
            banda["y"] = sum(p["y"] for p in banda["palabras"]) / len(banda["palabras"])

    patron_hora = re.compile(r"(?<!\d)(\d{1,2})\s*[:.]\s*(\d{2})(?!\d)")
    filas_hora = []
    for banda in bandas:
        margen_izquierdo = [p for p in banda["palabras"] if p["x"] < centros_x[0]]
        texto_horas = " ".join(p["texto"] for p in sorted(margen_izquierdo, key=lambda p: p["x"]))
        texto_horas = re.sub(r"(?<=\d)[Oo](?=[:.]\d)|(?<=[:.])[Oo](?=\d)", "0", texto_horas)
        horas = [(int(h), int(m)) for h, m in patron_hora.findall(texto_horas)]
        if len(horas) >= 2:
            inicio, fin = horas[0], horas[1]
            if fin > inicio:
                filas_hora.append({"y": banda["y"], "inicio": inicio, "fin": fin})
    filas_hora.sort(key=lambda item: item["y"])
    if not filas_hora:
        raise ValueError("No se reconocieron módulos con hora de inicio y fin.")

    centros_tiempo = [
        sum(p["x"] for p in palabra["palabras"] if patron_hora.search(p["texto"])) / max(
            1, sum(1 for p in palabra["palabras"] if patron_hora.search(p["texto"]))
        )
        for palabra in bandas if patron_hora.search(" ".join(p["texto"] for p in palabra["palabras"]))
    ]
    centro_tiempo = sum(centros_tiempo) / len(centros_tiempo) if centros_tiempo else centros_x[0] / 2
    limites_x = [
        max(0, (centro_tiempo + centros_x[0]) / 2),
        *[(centros_x[i] + centros_x[i + 1]) / 2 for i in range(len(centros_x) - 1)],
        ancho_imagen,
    ]
    filas = []
    for indice, fila in enumerate(filas_hora):
        arriba = 0 if indice == 0 else (filas_hora[indice - 1]["y"] + fila["y"]) / 2
        abajo = alto_imagen if indice + 1 == len(filas_hora) else (fila["y"] + filas_hora[indice + 1]["y"]) / 2
        for columna, (dia, _centro) in enumerate(columnas):
            textos = [
                p["texto"] for p in palabras
                if limites_x[columna] <= p["x"] < limites_x[columna + 1]
                and arriba <= p["y"] < abajo
                and normalizar_texto(p["texto"]).strip(".,;:") not in dias
                and not patron_hora.search(p["texto"])
            ]
            actividad = " ".join(textos).strip()
            if actividad:
                filas.append({
                    "Día": dia,
                    "Inicio": f"{fila['inicio'][0]:02d}:{fila['inicio'][1]:02d}",
                    "Fin": f"{fila['fin'][0]:02d}:{fila['fin'][1]:02d}",
                    "Actividad": actividad,
                    "Grupo": "",
                    "Responsable": "",
                })
    if not filas:
        raise ValueError("No se encontraron actividades dentro de los módulos detectados.")
    return normalizar_tabla_horario(pd.DataFrame(filas))


def _leer_imagen_ocr_local(archivo):
    """Lee texto localmente con Tesseract; no usa servicios externos ni guarda datos."""
    try:
        from PIL import Image, ImageOps
        import pytesseract
        from pytesseract import Output
    except ImportError as exc:
        raise RuntimeError("El OCR local no está instalado todavía.") from exc
    imagen = ImageOps.exif_transpose(Image.open(BytesIO(archivo.getvalue()))).convert("RGB")
    try:
        orientacion = pytesseract.image_to_osd(imagen, output_type=Output.DICT)
        giro = int(orientacion.get("rotate", 0) or 0)
        if giro:
            imagen = imagen.rotate(360 - giro, expand=True)
    except Exception:
        # Algunas tablas tienen poco texto para estimar la orientación; se conserva la foto.
        pass
    datos = pytesseract.image_to_data(
        imagen, lang="spa+eng", config="--psm 6", output_type=Output.DICT,
    )
    return _bloques_desde_ocr_tsv(datos, imagen.width, imagen.height)


def _mensaje_ocr_corto(mensaje):
    texto = str(mensaje).upper()
    if "503" in texto or "UNAVAILABLE" in texto:
        return "IA ocupada (503); no cambió el horario. Prueba OCR local."
    if "429" in texto or "QUOTA" in texto or "RESOURCE_EXHAUSTED" in texto:
        return "Límite temporal (429); no cambió el horario. Usa OCR local o espera."
    if "OCR LOCAL" in texto and "NO ESTÁ INSTALADO" in texto:
        return "OCR local no disponible; prueba lectura con IA o captura manual."
    return "No se pudo leer el horario. Prueba otra opción o captura manualmente."


def _leer_imagenes_pendientes(imagenes, nombre, escuela):
    """Lee el conjunto de imágenes en una sola petición al modelo para reducir cuota."""
    errores = []
    pendientes = [archivo for archivo in imagenes
                  if _clave_imagen_horario(nombre, escuela, archivo) not in st.session_state
                  and f"ocr_error_{_clave_imagen_horario(nombre, escuela, archivo)}" not in st.session_state]
    if not pendientes:
        return 0, errores
    from google.genai import types
    from ai.engine import client
    from config.settings import GEMINI_MODEL
    cli = client()
    if cli is None:
        return 0, ["La lectura automática no está configurada; captura los bloques en la tabla manual."]
    contents = [
        "Lee los horarios de todas las imágenes adjuntas. Devuelve SOLO JSON válido con forma "
        '{"archivos":{"número::nombre de archivo":[{"Día":"Lunes","Inicio":"08:00",'
        '"Fin":"08:50","Grupo":"2A","Actividad":"Inglés","Responsable":""}]}}. '
        "No inventes datos; deja campos vacíos si no se distinguen. Horas HH:MM de 24 horas."
    ]
    claves = []
    for archivo in pendientes:
        ext = archivo.name.rsplit(".", 1)[-1].lower()
        mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
                "webp": "image/webp", "bmp": "image/bmp", "tif": "image/tiff", "tiff": "image/tiff"}.get(ext)
        if not mime:
            errores.append(f"{archivo.name}: formato no compatible para lectura automática.")
            continue
        etiqueta_archivo = f"{len(claves) + 1}::{archivo.name}"
        contents.extend([f"Archivo: {etiqueta_archivo}", types.Part.from_bytes(data=archivo.getvalue(), mime_type=mime)])
        claves.append((etiqueta_archivo, archivo))
    if not claves:
        return 0, errores
    try:
        response = cli.models.generate_content(
            model=GEMINI_MODEL, contents=contents,
            config={"temperature": 0, "response_mime_type": "application/json"},
        )
        raw = json.loads((response.text or "{}").strip())
        resultado = raw.get("archivos", raw) if isinstance(raw, dict) else {}
        leidas = 0
        for etiqueta_archivo, archivo in claves:
            filas = resultado.get(etiqueta_archivo, [])
            if not filas:
                errores.append(f"{archivo.name}: no se reconocieron bloques; puedes transcribirlos manualmente.")
                st.session_state[f"ocr_error_{_clave_imagen_horario(nombre, escuela, archivo)}"] = errores[-1]
                continue
            try:
                st.session_state[_clave_imagen_horario(nombre, escuela, archivo)] = normalizar_tabla_horario(pd.DataFrame(filas))
                leidas += 1
            except Exception as exc:
                errores.append(f"{archivo.name}: revisa la captura manual ({exc}).")
                st.session_state[f"ocr_error_{_clave_imagen_horario(nombre, escuela, archivo)}"] = errores[-1]
        return leidas, errores
    except Exception as exc:
        detalle = str(exc)
        if "503" in detalle or "UNAVAILABLE" in detalle.upper() or "HIGH DEMAND" in detalle.upper():
            causa = "El servicio de lectura está temporalmente saturado (503); no es un error de guardado."
        elif "429" in detalle or "QUOTA" in detalle.upper() or "RESOURCE_EXHAUSTED" in detalle.upper():
            causa = "El servicio alcanzó su límite de solicitudes (429); espera antes de volver a intentarlo."
        else:
            causa = "El servicio no pudo completar la lectura."
        aviso = f"{causa} No se guardó ni modificó ningún horario. Puedes reintentar manualmente o capturar los bloques en la tabla. Detalle: {detalle}"
        for _etiqueta_archivo, archivo in claves:
            st.session_state[f"ocr_error_{_clave_imagen_horario(nombre, escuela, archivo)}"] = aviso
        return 0, [aviso]


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
    c1, c2 = st.columns(2)
    with c1:
        inicio = st.time_input("Inicio", value=time(7, 0), key=f"{prefijo}_inicio")
    with c2:
        fin = st.time_input("Fin", value=time(13, 0), key=f"{prefijo}_fin")
    st.caption("Configura duraciones distintas por día, separadas por comas. El descanso indicado se replica durante toda la semana.")
    duraciones_por_dia = {}
    columnas_dias = st.columns(5)
    for dia, columna in zip(DIAS, columnas_dias):
        with columna:
            duraciones_por_dia[dia] = st.text_input(f"{dia} · minutos", value="60", key=f"{prefijo}_dur_{dia}")
    pausa_cols = st.columns([1, 1, 2])
    with pausa_cols[0]:
        descanso_inicio = st.text_input("Descanso desde · HH:MM", value="", key=f"{prefijo}_descanso_inicio", placeholder="10:00")
    with pausa_cols[1]:
        descanso_fin = st.text_input("Descanso hasta · HH:MM", value="", key=f"{prefijo}_descanso_fin", placeholder="10:30")
    try:
        franjas_por_dia = {dia: franjas_semanales(inicio, fin, duraciones_por_dia[dia]) for dia in DIAS}
    except ValueError as exc:
        st.error(str(exc))
        return
    pausas = {}
    if descanso_inicio or descanso_fin:
        try:
            from services.horarios import franjas_diarias
            for dia in DIAS:
                franjas_por_dia[dia], pausa_dia = franjas_diarias(inicio, fin, duraciones_por_dia[dia], descanso_inicio, descanso_fin)
                pausas.update(pausa_dia)
        except ValueError as exc:
            st.error(str(exc))
            return
    franjas = sorted({franja for diario in franjas_por_dia.values() for franja in diario})
    st.session_state[clave_franjas] = franjas
    borrador = st.session_state.setdefault(clave_filas, {})
    propia = (horarios_equipo.loc[horarios_equipo["Maestra"].astype(str).eq(nombre)].copy()
              if not horarios_equipo.empty and "Maestra" in horarios_equipo else pd.DataFrame())
    if not propia.empty and st.button("Cargar mi horario vigente para editarlo en esta plantilla", key=f"{prefijo}_cargar"):
        # Reemplaza el borrador completo; un merge deja bloques obsoletos "congelados".
        st.session_state[clave_filas] = _borrador_de_horario(propia.to_dict("records"))
        st.session_state[f"{prefijo}_editor_version"] = st.session_state.get(f"{prefijo}_editor_version", 0) + 1
        st.rerun()
    if borrador and st.button("Reiniciar borrador temporal", key=f"{prefijo}_reiniciar_borrador"):
        st.session_state[clave_filas] = {}
        st.session_state[f"{prefijo}_editor_version"] = st.session_state.get(f"{prefijo}_editor_version", 0) + 1
        st.info("Se limpió únicamente el borrador de esta sesión. El horario guardado y su historial siguen intactos.")
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
             ".horario-apoyo-grid .descanso{background:#fff1bf;color:#6f5200;text-align:center;font-weight:bold}"
             ".horario-apoyo-grid .inactivo{background:#f7f9fb;color:#c2cbd2;text-align:center}"
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
            descanso = (desde, hasta) in pausas and (desde, hasta) in franjas_por_dia[dia]
            clase = "descanso" if descanso else ("choque" if conflicto else ("ocupado" if item else ("vacio" if (desde, hasta) in franjas_por_dia[dia] else "inactivo")))
            etiqueta = "DESCANSO" if descanso else (html.escape(contenido) if contenido else ("Sin capturar" if (desde, hasta) in franjas_por_dia[dia] else "—"))
            tabla.append(f"<td class='{clase}'>{etiqueta}</td>")
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
    franjas_dia = [f for f in franjas_por_dia[dia_elegido] if f not in pausas]
    franja_elegida = st.selectbox("Módulo", franjas_dia,
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
    grupo_candidato = grupo or str(actual.get("Grupo", ""))
    if ids:
        grupos_alumnos = sorted({_grupo_alumno(row) for row in visibles.to_dict("records")
                                 if str(row.get("ID_Alumno", "")) in set(ids) and _grupo_alumno(row)})
        grupo_candidato = ", ".join(grupos_alumnos)
    candidato = {
        "Dia": dia_elegido, "Inicio": desde, "Fin": hasta,
        "Grupo": grupo_candidato,
        "ID_Alumnos": ",".join(ids) or str(actual.get("ID_Alumnos", "")),
        "Actividad": actividad.strip() or str(actual.get("Actividad", "")), "Maestra": nombre,
    }
    filas_en_vivo = [row for row in filas if not (row.get("Dia") == dia_elegido and row.get("Inicio") == desde and row.get("Fin") == hasta)]
    if candidato["Actividad"]:
        filas_en_vivo.append(candidato)
        try:
            choques_en_vivo = detectar_choques(filas_en_vivo, restricciones, horarios_equipo)
            horario_objetivo = f"{desde}–{hasta}"
            conflictos_bloque = [r for r in choques_en_vivo.to_dict("records") if r.get("Día") == dia_elegido and str(r.get("Horario propuesto", "")).replace(" ", "").replace("-", "–") == horario_objetivo]
            if conflictos_bloque:
                st.error("⚠️ Conflicto de horario en este módulo. Ajusta día/hora o revisa los horarios de referencia antes de guardar.")
                st.dataframe(pd.DataFrame(conflictos_bloque), hide_index=True, width="stretch")
            else:
                st.success("✓ Sin choque detectado en este módulo.")
        except Exception as exc:
            st.warning(f"No se pudo validar el módulo en vivo: {exc}")
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
            filas_pdf = filas + [
                {"Dia": dia, "Inicio": desde_pausa, "Fin": hasta_pausa,
                 "Grupo": "", "Alumnos": "", "Actividad": "DESCANSO"}
                for dia in DIAS for (desde_pausa, hasta_pausa), tipo in pausas.items()
            ]
            pdf = generar_horario_apoyo_cuadricula_pdf(escuela, nombre, filas_pdf, franjas)
            st.download_button("Generar y descargar horario oficial (PDF)", pdf,
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
    clave_identidad = f"{normalizar_texto(nombre)}_{normalizar_texto(escuela)}"
    if st.button("↻ Actualizar horarios guardados", key=f"actualizar_horarios_{clave_identidad}"):
        cargar_restricciones.clear()
        cargar_horarios_apoyo.clear()
        st.rerun()
    st.divider()

    try:
        restricciones = cargar_restricciones(escuela)
        horarios_equipo = cargar_horarios_apoyo(escuela)
    except Exception as exc:
        st.error(f"No se pudieron leer los horarios compartidos: {exc}")
        return

    st.markdown("### 📎 Horarios de referencia de la escuela")
    st.info("**1. Sube los archivos → 2. Revisa o completa los bloques → 3. Guarda.** Las imágenes necesitan lectura o captura antes de convertirse en horarios que permitan detectar choques. Los horarios anteriores se conservan.")
    plantilla = pd.DataFrame([{"Día": "Lunes", "Inicio": "08:00", "Fin": "08:50", "Actividad": "Inglés", "Grupo": "2A", "Responsable": ""}])
    st.download_button("Descargar plantilla de horario", plantilla.to_csv(index=False).encode("utf-8-sig"), "Plantilla_horario_escolar.csv", "text/csv", key="plantilla_horario_apoyo")
    clave_version_carga = f"version_carga_horario_{clave_identidad}"
    version_carga = st.session_state.get(clave_version_carga, 0)
    clave_uploader = f"carga_restricciones_horario_{clave_identidad}_{version_carga}"
    archivos = st.file_uploader(
        "Horarios de materias, docentes y otras maestras de apoyo",
        type=TIPOS_ARCHIVO_HORARIOS, accept_multiple_files=True, key=clave_uploader,
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
    imagenes = [archivo for archivo, tipo in referencias if tipo == "imagen"]
    if imagenes:
        st.markdown(f"#### 🖼️ {len(imagenes)} imagen(es) cargada(s)")
        hay_lectura_fallida = any(
            f"ocr_error_{_clave_imagen_horario(nombre, escuela, archivo)}" in st.session_state
            for archivo in imagenes
        )
        if st.button("🧹 Quitar esta carga y empezar de nuevo", key=f"limpiar_carga_{clave_identidad}_{version_carga}"):
            for archivo in imagenes:
                _limpiar_lectura_imagen(nombre, escuela, archivo)
            st.session_state[clave_version_carga] = version_carga + 1
            st.rerun()
        pendientes = [archivo for archivo in imagenes
                      if _clave_imagen_horario(nombre, escuela, archivo) not in st.session_state
                      and f"ocr_error_{_clave_imagen_horario(nombre, escuela, archivo)}" not in st.session_state]
        errores_guardados = [
            st.session_state.get(f"ocr_error_{_clave_imagen_horario(nombre, escuela, archivo)}")
            for archivo in imagenes
        ]
        for fallo in dict.fromkeys(error for error in errores_guardados if error):
            st.warning(fallo)
        if pendientes or hay_lectura_fallida:
            etiqueta = "↻ Reintentar lectura de imágenes" if hay_lectura_fallida else "✨ Analizar imágenes cargadas"
            st.info("La lectura automática inicia solo cuando la solicitas; así no se repite al editar otros campos ni al actualizar la página.")
        else:
            st.success("Las imágenes ya se analizaron. Comprueba y corrige los bloques antes de guardarlos.")
        if (pendientes or hay_lectura_fallida) and st.button(etiqueta, type="primary", key=f"analizar_imagenes_{clave_identidad}_{version_carga}"):
            if hay_lectura_fallida:
                for archivo in imagenes:
                    st.session_state.pop(f"ocr_error_{_clave_imagen_horario(nombre, escuela, archivo)}", None)
            with st.spinner("Reconociendo los bloques de horario. Podrás corregirlos antes de guardarlos…"):
                leidas, fallos = _leer_imagenes_pendientes(imagenes, nombre, escuela)
            for fallo in fallos:
                st.warning(fallo)
            if leidas:
                st.rerun()
        if (pendientes or hay_lectura_fallida) and st.button(
            "🔎 Probar OCR local", key=f"ocr_local_{clave_identidad}_{version_carga}"
        ):
            leidas_local = 0
            primer_fallo = ""
            with st.spinner("Leyendo texto en la imagen…"):
                for archivo in imagenes:
                    clave = _clave_imagen_horario(nombre, escuela, archivo)
                    if clave in st.session_state:
                        continue
                    try:
                        st.session_state[clave] = _leer_imagen_ocr_local(archivo)
                        st.session_state.pop(f"ocr_error_{clave}", None)
                        leidas_local += 1
                    except Exception as exc:
                        st.session_state[f"ocr_error_{clave}"] = str(exc)
                        primer_fallo = primer_fallo or str(exc)
            if leidas_local:
                st.success("Texto listo para revisar.")
                st.rerun()
            elif primer_fallo:
                st.warning(_mensaje_ocr_corto(primer_fallo))
    for archivo, tipo in referencias:
        if tipo == "imagen":
            clave_imagen = _clave_imagen_horario(nombre, escuela, archivo)
            with st.expander(f"Ver imagen: {archivo.name}"):
                st.image(archivo.getvalue(), caption=archivo.name, width="stretch")
            if clave_imagen in st.session_state:
                st.markdown(f"**Revisar bloques de {archivo.name}**")
                st.caption("Corrige día, horas, grupo y actividad. Solo estos bloques revisados se guardarán.")
                revisado = st.data_editor(
                    st.session_state[clave_imagen], num_rows="dynamic", hide_index=True,
                    width="stretch", key=f"revision_{clave_imagen}_{version_carga}",
                )
                try:
                    preparados.append((f"{archivo.name} · lectura revisada", normalizar_tabla_horario(revisado)))
                except ValueError as exc:
                    st.warning(f"Corrige las filas reconocidas en {archivo.name}: {exc}")
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
        st.markdown("#### ✍️ Captura manual (si falta algún bloque)")
        st.caption("Úsala cuando una imagen o documento no pueda leerse, o para añadir bloques omitidos. Una fila por día, hora y actividad.")
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
            st.markdown(f"#### ✅ Vista previa: {len(vista_carga)} bloque(s) listos para guardar")
            st.dataframe(vista_carga, hide_index=True, width="stretch")
        if st.button("💾 Guardar horarios de referencia revisados", type="primary", key="guardar_restricciones_horario"):
            try:
                total = 0
                filas_guardar = list(preparados)
                if captura_manual is not None:
                    captura = captura_manual.fillna("").astype(str)
                    captura = captura.loc[captura.apply(lambda fila: any(valor.strip() for valor in fila), axis=1)]
                    if not captura.empty:
                        filas_guardar.append(("Captura desde archivo de referencia", normalizar_tabla_horario(captura)))
                if not filas_guardar:
                    st.warning("Aún no hay bloques válidos. Analiza las imágenes con el botón indicado o captura al menos una fila completa en la tabla manual.")
                    st.stop()
                _, total = guardar_restricciones_lote(escuela, nombre, filas_guardar)
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
    propio = horarios_equipo.loc[horarios_equipo["Maestra"].astype(str).eq(nombre)].copy() if not horarios_equipo.empty and "Maestra" in horarios_equipo.columns else pd.DataFrame()
    if not propio.empty:
        st.markdown("### Mi horario vigente")
        propia_vista = _tabla_vista(propio)
        st.dataframe(propia_vista, hide_index=True, width="stretch")
        franjas_guardadas = sorted({(str(row["Inicio"]), str(row["Fin"]))
                                   for row in propio.to_dict("records")})
        try:
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
        except Exception as exc:
            st.error(f"No se pudo generar el PDF del horario vigente: {exc}")
        st.caption("Para modificarlo, usa «Cargar mi horario vigente para editarlo en esta plantilla». Cada nueva versión conserva la anterior.")
        st.caption(f"Ciclo escolar {SCHOOL_YEAR}. Cada guardado agrega una nueva versión y conserva la anterior.")


def horarios_apoyo_direccion():
    """Vista de supervisión directiva de horarios vigentes, sin mutar el historial."""
    rol = normalizar_texto(st.session_state.get("rol", ""))
    if "DIRECTOR" not in rol:
        st.error("La supervisión global de horarios está disponible solo para Dirección.")
        return

    st.subheader("Supervisión de horarios de apoyo")
    st.caption("Consulta los horarios vigentes de todas las escuelas y descarga cada versión oficial. El historial no se modifica desde esta vista.")
    escuelas = list(ESCUELAS_USAER.keys())
    escuela = st.selectbox("Escuela para supervisar", escuelas, key="direccion_horario_escuela")
    try:
        with st.spinner("Consultando horarios vigentes de la escuela..."):
            horarios = cargar_horarios_apoyo(escuela)
    except Exception as exc:
        st.error(f"No se pudieron consultar los horarios de {escuela}: {exc}")
        return

    if horarios.empty or "Maestra" not in horarios.columns:
        st.info("Aún no hay horarios de apoyo guardados para esta escuela.")
        return

    docentes = sorted(
        horarios["Maestra"].fillna("").astype(str).str.strip().loc[
            lambda serie: serie.ne("")
        ].unique()
    )
    st.metric("Docentes con horario vigente", len(docentes))
    docente = st.selectbox(
        "Docente de apoyo",
        docentes,
        key=f"direccion_horario_docente_{normalizar_texto(escuela)}",
    )
    filas = horarios.loc[horarios["Maestra"].astype(str).str.strip().eq(docente)].copy()
    st.dataframe(_tabla_vista(filas), hide_index=True, width="stretch")

    franjas = sorted({
        (str(row.get("Inicio", "")), str(row.get("Fin", "")))
        for row in filas.to_dict("records")
        if str(row.get("Inicio", "")).strip() and str(row.get("Fin", "")).strip()
    })
    try:
        pdf = generar_horario_apoyo_cuadricula_pdf(
            escuela, docente, filas.to_dict("records"), franjas,
        )
        st.download_button(
            "Descargar horario oficial supervisado (PDF)",
            data=pdf,
            file_name=f"Horario_Supervision_{normalizar_texto(docente).replace(' ', '_')}_{normalizar_texto(escuela).replace(' ', '_')}.pdf",
            mime="application/pdf",
            type="primary",
            key=f"direccion_descargar_horario_{normalizar_texto(escuela)}_{normalizar_texto(docente)}",
        )
    except Exception as exc:
        st.error(f"No se pudo generar el horario oficial de {docente}: {exc}")

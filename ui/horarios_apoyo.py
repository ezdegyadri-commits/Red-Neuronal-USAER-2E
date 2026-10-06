"""Generador, coordinación y avisos de horarios para maestras de apoyo."""

from __future__ import annotations

import html
import hashlib
import re
from difflib import SequenceMatcher
from difflib import SequenceMatcher
from datetime import time
from io import BytesIO

import pandas as pd
import streamlit as st
from docx import Document

from data import repository as repo
from config.settings import ESCUELAS_USAER, SCHOOL_YEAR
from documents.horarios_apoyo import generar_horario_apoyo_cuadricula_pdf
from services.asignaciones import escuelas_asignadas
from services.alumnos import filtrar_alumnos_por_docente_compartido, filtrar_alumnos_por_escuelas
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
    editar_referencia,
    _referencia_general,
    marcar_avisos_leidos,
    normalizar_tabla_horario,
    actualizar_bloques_borrador,
)
from utils.text import normalizar_texto


TIPOS_ARCHIVO_HORARIOS = ["xlsx", "xls", "csv", "doc", "docx", "pdf", "png", "jpg", "jpeg", "webp", "bmp", "tif", "tiff"]


def _alumnos_de_maestra(nombre, escuela):
    """Entrega alumnos de la docente; en escuela compartida no ofrece cuentas ajenas."""
    todos = filtrar_alumnos_por_escuelas(repo.alumnos(), [escuela]).copy()
    if todos.empty:
        return todos, todos
    if normalizar_texto(escuela) in {"ICHCAANZIHO", "ESC-002"}:
        propios = filtrar_alumnos_por_docente_compartido(todos, nombre)
        return propios, propios
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


def _clave_imagen_horario(nombre, escuela, archivo):
    """Separa lecturas por docente, escuela y contenido, no solo por nombre de archivo."""
    huella = hashlib.sha256(archivo.getvalue()).hexdigest()[:16]
    return f"bloques_imagen_{normalizar_texto(nombre)}_{normalizar_texto(escuela)}_{huella}"


def _limpiar_lectura_imagen(nombre, escuela, archivo):
    """Olvida solo la lectura temporal de una imagen; no toca horarios guardados."""
    clave = _clave_imagen_horario(nombre, escuela, archivo)
    for key in (clave, f"ocr_error_{clave}"):
        st.session_state.pop(key, None)


def _limpiar_borradores_imagen_sin_carga(nombre, escuela):
    """Retira solo borradores OCR ocultos cuando ya no hay archivos adjuntos."""
    prefijo = f"bloques_imagen_{normalizar_texto(nombre)}_{normalizar_texto(escuela)}_"
    for key in list(st.session_state.keys()):
        texto = str(key)
        if (texto.startswith(prefijo)
                or texto.removeprefix("ocr_error_").startswith(prefijo)
                or texto.removeprefix("revision_").startswith(prefijo)):
            st.session_state.pop(key, None)


def _borrador_de_horario(filas):
    """Construye un borrador nuevo desde la versión vigente, sin mezclar residuos."""
    return {
        f"{item.get('Dia')}|{item.get('Inicio')}|{item.get('Fin')}": item
        for item in filas
    }


def _interpretar_celda_horario(texto):
    """Separa el grado de la actividad aunque OCR omita la palabra «grado»."""
    original = " ".join(str(texto or "").split()).strip(" |·,;.-")
    clave = normalizar_texto(original)
    ordinales = {
        "PRIMERO": "1°", "PRIMER": "1°", "PRIMERA": "1°",
        "SEGUNDO": "2°", "SEGUNDA": "2°", "TERCERO": "3°",
        "TERCER": "3°", "TERCERA": "3°", "CUARTO": "4°",
        "CUARTA": "4°", "QUINTO": "5°", "QUINTA": "5°",
        "SEXTO": "6°", "SEXTA": "6°",
    }
    patron = re.compile(
        r"\b(PRIMER[OA]?|SEGUND[OA]|TERCER[OA]?|CUART[OA]|QUINT[OA]|SEXT[OA]"
        r"|[1-6]\s*(?:°|º|O)?)(?:\s+GRADO)?(?:\s*([A-F]))?\b"
    )
    coincidencia = patron.search(clave)
    if not coincidencia:
        return "", original or "Horario escolar"
    token_grado = coincidencia.group(1).replace(" ", "")
    grupo = ordinales.get(token_grado, "")
    if not grupo and token_grado[:1].isdigit():
        grupo = f"{token_grado[0]}°"
    if grupo and coincidencia.group(2):
        grupo += coincidencia.group(2)
    resto = (clave[:coincidencia.start()] + " " + clave[coincidencia.end():]).strip(" |·,;.-")
    return grupo, resto.title() if resto else "Clase regular"


def _materia_desde_titulo(texto):
    """Detecta la asignatura en títulos habituales de horarios escolares."""
    clave = normalizar_texto(texto)
    for tokens, etiqueta in (
        (("EDUCACION FISICA", "ED FISICA"), "Educación física"),
        (("INGLES",), "Inglés"),
        (("MAYA",), "Maya"),
        (("ARTES", "EDUCACION ARTISTICA"), "Artes"),
        (("CORO", "CANTOS"), "Coro y cantos"),
    ):
        if any(token in clave for token in tokens):
            return etiqueta
    return ""


def _celda_ocr_util(texto, grupo=""):
    """Evita que residuos de horas o puntuación se conviertan en actividades."""
    if grupo:
        return True
    letras = re.sub(r"[^A-Z]", "", normalizar_texto(texto))
    return len(letras) >= 3


def _normalizar_actividad_ocr(texto):
    """Corrige únicamente errores OCR muy cercanos a materias conocidas."""
    original = " ".join(str(texto or "").split()).strip(" |·,;.-")
    clave = normalizar_texto(original)
    canonicas = {
        "COROS Y CANTOS": "Coros y Cantos",
        "CORO Y CANTOS": "Coro y Cantos",
        "EDUCACION FISICA": "Educación física",
        "INGLES": "Inglés",
        "MAYA": "Maya",
        "ARTES": "Artes",
    }
    if clave in canonicas:
        return canonicas[clave]
    if len(clave) >= 8:
        mejor = max(canonicas, key=lambda etiqueta: SequenceMatcher(None, clave, etiqueta).ratio())
        if SequenceMatcher(None, clave, mejor).ratio() >= 0.84:
            return canonicas[mejor]
    return original


def _bloques_desde_ocr_tsv(datos, ancho_imagen, alto_imagen):
    """Interpreta tablas horarias aunque el OCR divida las horas y los encabezados."""
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
        # Los títulos de día impresos y subrayados a veces reciben baja confianza;
        # se mantienen para el reconocimiento, pero el resultado siempre es editable.
        if texto and confianza >= 0 and ancho >= 0 and alto > 0:
            palabras.append({"texto": texto, "x": izquierda + ancho / 2,
                             "y": arriba + alto / 2, "alto": alto})
    if not palabras:
        raise ValueError("No se detectó texto legible.")

    centros_dia = {}
    y_encabezados = []
    alias = {"LUN": "Lunes", "MAR": "Martes", "MIE": "Miércoles",
             "JUE": "Jueves", "VIE": "Viernes"}
    for palabra in palabras:
        clave_dia = normalizar_texto(palabra["texto"]).strip(".,;:")
        dia = dias.get(clave_dia)
        if dia is None:
            # Acepta abreviaturas comunes y errores pequeños de lectura en encabezados.
            dia = alias.get(clave_dia)
        if dia is None and len(clave_dia) >= 4:
            dia = next((valor for clave, valor in dias.items()
                        if clave.startswith(clave_dia)), None)
        if dia is None and len(clave_dia) >= 5:
            coincidencia = max(dias, key=lambda clave: SequenceMatcher(None, clave_dia, clave).ratio())
            if SequenceMatcher(None, clave_dia, coincidencia).ratio() >= 0.72:
                dia = dias[coincidencia]
        if dia:
            centros_dia.setdefault(dia, []).append(palabra["x"])
            y_encabezados.append(palabra["y"])
    centros_dia = {dia: sum(xs) / len(xs) for dia, xs in centros_dia.items()}
    if len(centros_dia) < 2:
        raise ValueError("No se reconocieron suficientes encabezados de días para ordenar el horario.")
    columnas = sorted(centros_dia.items(), key=lambda item: item[1])
    primer_encabezado = min(y_encabezados) if y_encabezados else 0
    titulo = " ".join(p["texto"] for p in palabras if p["y"] < primer_encabezado)
    materia = _materia_desde_titulo(titulo)
    centros_x = [x for _dia, x in columnas]
    alto_medio = sorted(p["alto"] for p in palabras)[len(palabras) // 2]
    tolerancia_y = max(18, alto_medio * 2.0)
    bandas = []
    for palabra in sorted(palabras, key=lambda p: p["y"]):
        if not bandas or palabra["y"] - bandas[-1]["y"] > tolerancia_y:
            bandas.append({"y": palabra["y"], "palabras": [palabra]})
        else:
            banda = bandas[-1]
            banda["palabras"].append(palabra)
            banda["y"] = sum(p["y"] for p in banda["palabras"]) / len(banda["palabras"])

    patron_hora = re.compile(r"(?<!\d)(\d{1,2})\s*[:.]\s*([0-5]?\d)(?!\d)")
    # Extrae horas de cada caja por separado: el guion y cada extremo suelen ser
    # palabras distintas en TSV, por lo que unir primero el texto de una línea falla.
    candidatos_hora = []
    for palabra in palabras:
        if palabra["x"] >= centros_x[0]:
            continue
        token = re.sub(r"(?<=\d)[Oo](?=[:.]\d)|(?<=[:.])[Oo](?=\d)", "0", palabra["texto"])
        for h, m in patron_hora.findall(token):
            hora = (int(h), int(m))
            if hora[0] <= 23:
                candidatos_hora.append({"y": palabra["y"], "x": palabra["x"], "hora": hora})
    grupos_hora = []
    tolerancia_hora = max(14, alto_medio * 1.6)
    for candidato in sorted(candidatos_hora, key=lambda item: item["y"]):
        if not grupos_hora or candidato["y"] - grupos_hora[-1]["y"] > tolerancia_hora:
            grupos_hora.append({"y": candidato["y"], "items": [candidato]})
        else:
            grupo = grupos_hora[-1]
            grupo["items"].append(candidato)
            grupo["y"] = sum(item["y"] for item in grupo["items"]) / len(grupo["items"])
    filas_hora = []
    for grupo in grupos_hora:
        horas = [item["hora"] for item in sorted(grupo["items"], key=lambda item: item["x"])]
        if len(horas) >= 2:
            inicio, fin = horas[0], horas[-1]
            if fin > inicio:
                filas_hora.append({"y": grupo["y"], "inicio": inicio, "fin": fin})
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
        # No mezclar el título, escuela ni encabezado de días dentro del primer módulo.
        arriba = ((max(y_encabezados) + fila["y"]) / 2 if indice == 0 and y_encabezados
                  else 0 if indice == 0
                  else (filas_hora[indice - 1]["y"] + fila["y"]) / 2)
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
                texto_celda = actividad
                grupo, actividad = _interpretar_celda_horario(texto_celda)
                if not _celda_ocr_util(texto_celda, grupo):
                    continue
                if grupo and actividad == "Clase regular" and materia:
                    actividad = materia
                actividad = _normalizar_actividad_ocr(actividad)
                filas.append({
                    "Día": dia,
                    "Inicio": f"{fila['inicio'][0]:02d}:{fila['inicio'][1]:02d}",
                    "Fin": f"{fila['fin'][0]:02d}:{fila['fin'][1]:02d}",
                    "Actividad": actividad,
                    "Grupo": grupo,
                    "Responsable": "",
                })
    if not filas:
        raise ValueError("No se encontraron actividades dentro de los módulos detectados.")
    return normalizar_tabla_horario(pd.DataFrame(filas))


def _lineas_cuadricula(imagen, eje):
    """Localiza bordes largos de la tabla; ignora letras y subrayados cortos."""
    gris = imagen.convert("L")
    ancho, alto = gris.size
    escala = 2 if max(ancho, alto) > 1800 else 1
    if escala == 2:
        gris = gris.resize((ancho // 2, alto // 2))
    ancho, alto = gris.size
    pixeles = gris.load()
    longitud = ancho if eje == "horizontal" else alto
    transversal = alto if eje == "horizontal" else ancho
    umbral = longitud * (0.58 if eje == "horizontal" else 0.50)
    candidatos = []
    for posicion in range(transversal):
        oscuros = sum(
            pixeles[paso, posicion] < 115 if eje == "horizontal"
            else pixeles[posicion, paso] < 115
            for paso in range(longitud)
        )
        if oscuros >= umbral:
            candidatos.append(posicion * escala)
    grupos = []
    for posicion in candidatos:
        if grupos and posicion - grupos[-1][-1] <= escala * 2:
            grupos[-1].append(posicion)
        else:
            grupos.append([posicion])
    return [round(sum(grupo) / len(grupo)) for grupo in grupos]


def _texto_celda_ocr(palabras, x0, y0, x1, y1):
    return " ".join(
        palabra["texto"] for palabra in sorted(
            (p for p in palabras if x0 + 3 < p["x"] < x1 - 3 and y0 + 3 < p["y"] < y1 - 3),
            key=lambda p: (round(p["y"] / 16), p["x"]),
        )
    ).strip()


def _bloques_desde_cuadricula(imagen, pytesseract, Output):
    """Lee cada celda de una tabla impresa usando sus bordes como coordenadas."""
    from PIL import ImageOps

    xs = _lineas_cuadricula(imagen, "vertical")
    ys = _lineas_cuadricula(imagen, "horizontal")
    if len(xs) < 3 or len(ys) < 3:
        raise ValueError("No se detectó una cuadrícula completa.")
    # Una tabla real presenta bordes alineados y al menos dos filas horarias.
    datos = pytesseract.image_to_data(
        ImageOps.autocontrast(imagen.convert("L")), lang="spa+eng",
        config="--psm 11", output_type=Output.DICT,
    )
    palabras = []
    for indice, texto in enumerate(datos.get("text", [])):
        texto = str(texto).strip()
        if not texto:
            continue
        try:
            x = int(datos["left"][indice]) + int(datos["width"][indice]) / 2
            y = int(datos["top"][indice]) + int(datos["height"][indice]) / 2
        except (KeyError, ValueError, IndexError):
            continue
        palabras.append({"texto": texto, "x": x, "y": y})

    cabeceras = []
    for columna in range(1, len(xs) - 1):
        texto = _texto_celda_ocr(palabras, xs[columna], ys[0], xs[columna + 1], ys[1])
        dia = _dia_desde_encabezado(texto)
        if not dia:
            recorte = imagen.crop((xs[columna] + 3, ys[0] + 3, xs[columna + 1] - 3, ys[1] - 3))
            dia = _dia_desde_encabezado(pytesseract.image_to_string(recorte, lang="spa+eng", config="--psm 7"))
        if dia:
            cabeceras.append((columna, dia))
    if not cabeceras:
        raise ValueError("No se reconocieron los encabezados de días.")

    titulo = pytesseract.image_to_string(
        imagen.crop((0, 0, imagen.width, max(1, ys[0]))),
        lang="spa+eng", config="--psm 6",
    )
    clave_titulo = normalizar_texto(titulo)
    materia = _materia_desde_titulo(clave_titulo) or "Clase regular"
    filas = []
    for renglon in range(1, len(ys) - 1):
        hora = _texto_celda_ocr(palabras, xs[0], ys[renglon], xs[1], ys[renglon + 1])
        intervalo = _hora_intervalo_matriz(hora)
        if not intervalo:
            recorte = imagen.crop((xs[0] + 3, ys[renglon] + 3, xs[1] - 3, ys[renglon + 1] - 3))
            intervalo = _hora_intervalo_matriz(
                pytesseract.image_to_string(recorte, lang="eng", config="--psm 6")
            )
        if not intervalo:
            continue
        for columna, dia in cabeceras:
            texto = _texto_celda_ocr(
                palabras, xs[columna], ys[renglon], xs[columna + 1], ys[renglon + 1]
            )
            if not texto:
                recorte = imagen.crop((xs[columna] + 3, ys[renglon] + 3,
                                       xs[columna + 1] - 3, ys[renglon + 1] - 3))
                texto = pytesseract.image_to_string(
                    recorte, lang="spa+eng", config="--psm 6"
                ).strip()
            if not texto:
                continue
            grupo, actividad = _interpretar_celda_horario(texto)
            if not _celda_ocr_util(texto, grupo):
                continue
            if grupo and actividad == "Clase regular":
                actividad = materia
            actividad = _normalizar_actividad_ocr(actividad)
            filas.append({
                "Día": dia, "Inicio": intervalo[0], "Fin": intervalo[1],
                "Grupo": grupo, "Actividad": actividad, "Responsable": "",
            })
    if not filas:
        raise ValueError("No se encontraron actividades en la cuadrícula.")
    return normalizar_tabla_horario(pd.DataFrame(filas))


def _leer_imagen_ocr_local(archivo):
    """Prueba variantes locales de la imagen; no usa servicios externos ni guarda datos."""
    try:
        from PIL import Image, ImageEnhance, ImageOps
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
    try:
        return _bloques_desde_cuadricula(imagen, pytesseract, Output)
    except ValueError:
        # Los diseños sin bordes siguen usando el lector flexible por posiciones.
        pass
    # Mejora fotos comprimidas y texto pequeño: primero original, después ampliadas,
    # con contraste y umbral. Se detiene en la primera lectura estructurada válida.
    escala = max(2, min(3, 1800 // max(1, imagen.width)))
    grande = imagen.resize((imagen.width * escala, imagen.height * escala), Image.Resampling.LANCZOS)
    gris = ImageOps.grayscale(grande)
    gris = ImageOps.autocontrast(gris)
    nitida = ImageEnhance.Sharpness(gris).enhance(1.7)
    umbral = nitida.point(lambda pixel: 255 if pixel > 165 else 0)
    variantes = [(imagen, "--psm 6"), (grande, "--psm 6"),
                 (nitida, "--psm 6"), (umbral, "--psm 6"), (nitida, "--psm 11")]
    ultimo_error = None
    datos_ampliados = None
    for preparada, configuracion in variantes:
        datos = pytesseract.image_to_data(
            preparada, lang="spa+eng", config=configuracion, output_type=Output.DICT,
        )
        if preparada is grande and configuracion == "--psm 6":
            datos_ampliados = datos
        try:
            return _bloques_desde_ocr_tsv(datos, preparada.width, preparada.height)
        except ValueError as exc:
            ultimo_error = exc
    # En algunas imágenes Tesseract lee bien la tabla pero pierde sus encabezados.
    # Recorta y amplía solo la franja superior para distinguir mejor los días.
    if datos_ampliados is not None:
        alto_encabezado = max(1, int(grande.height * 0.45))
        encabezado = grande.crop((0, 0, grande.width, alto_encabezado))
        escala_encabezado = 2
        encabezado = ImageOps.autocontrast(ImageOps.grayscale(encabezado)).resize(
            (encabezado.width * escala_encabezado, encabezado.height * escala_encabezado),
            Image.Resampling.LANCZOS,
        )
        for idioma in ("spa+eng", "eng"):
            for configuracion in ("--psm 6", "--psm 11"):
                datos_dias = pytesseract.image_to_data(
                    encabezado, lang=idioma, config=configuracion, output_type=Output.DICT,
                )
                combinados = {campo: list(datos_ampliados.get(campo, []))
                              for campo in ("text", "conf", "left", "top", "width", "height")}
                total = len(datos_dias.get("text", []))
                for indice in range(total):
                    combinados["text"].append(datos_dias["text"][indice])
                    combinados["conf"].append(datos_dias.get("conf", [100] * total)[indice])
                    for campo in ("left", "top", "width", "height"):
                        combinados[campo].append(round(int(datos_dias[campo][indice]) / escala_encabezado))
                try:
                    return _bloques_desde_ocr_tsv(combinados, grande.width, grande.height)
                except ValueError as exc:
                    ultimo_error = exc
    raise ValueError(str(ultimo_error or "No se reconocieron bloques de horario."))


def _mensaje_ocr_corto(mensaje):
    return "No se pudo leer una parte; revisa y completa los bloques en la tabla."


def _leer_imagenes_pendientes(imagenes, nombre, escuela):
    """Lee con Tesseract local; no consulta modelos externos ni genera cuotas."""
    errores = []
    pendientes = [archivo for archivo in imagenes
                  if _clave_imagen_horario(nombre, escuela, archivo) not in st.session_state
                  and f"ocr_error_{_clave_imagen_horario(nombre, escuela, archivo)}" not in st.session_state]
    if not pendientes:
        return 0, errores
    leidas = 0
    for archivo in pendientes:
        clave = _clave_imagen_horario(nombre, escuela, archivo)
        try:
            st.session_state[clave] = _leer_imagen_ocr_local(archivo)
            st.session_state.pop(f"ocr_error_{clave}", None)
            leidas += 1
        except Exception:
            st.session_state[f"ocr_error_{clave}"] = "No se reconocieron bloques; puedes corregir o capturar la tabla."
            errores.append(archivo.name)
    return leidas, errores


def _leer_imagen_horario(archivo):
    """Compatibilidad para lectores internos; utiliza únicamente OCR local."""
    return _leer_imagen_ocr_local(archivo)


def _dia_desde_encabezado(texto):
    clave = normalizar_texto(texto).strip(" .,:;\t")
    alias = {"LUN": "Lunes", "MAR": "Martes", "MIE": "Miércoles",
             "JUE": "Jueves", "VIE": "Viernes"}
    if clave in alias:
        return alias[clave]
    for dia in DIAS:
        if normalizar_texto(dia) == clave or normalizar_texto(dia).startswith(clave) and len(clave) >= 4:
            return dia
    if len(clave) >= 5:
        candidato = max(DIAS, key=lambda dia: SequenceMatcher(None, clave, normalizar_texto(dia)).ratio())
        if SequenceMatcher(None, clave, normalizar_texto(candidato)).ratio() >= 0.72:
            return candidato
    return ""


def _hora_intervalo_matriz(valor):
    texto = str(valor or "").replace("—", "-").replace("–", "-").replace("−", "-")
    horas = re.findall(r"(?<!\d)(\d{1,2}\s*[:.]\s*\d{2})(?!\d)", texto)
    if len(horas) < 2:
        return None
    try:
        inicio = normalizar_tabla_horario(pd.DataFrame([{
            "Día": "Lunes", "Inicio": horas[0], "Fin": horas[1], "Actividad": "x",
        }])).iloc[0]
    except (ValueError, IndexError):
        return None
    return str(inicio["Inicio"]), str(inicio["Fin"])


def _matriz_horario_a_frame(matriz):
    """Convierte una tabla semanal (días en columnas, horas en filas) a bloques."""
    filas = [[str(celda or "").strip() for celda in fila] for fila in matriz]
    if not filas:
        raise ValueError("La tabla no tiene contenido.")
    ancho = max(map(len, filas))
    filas = [(fila + [""] * ancho)[:ancho] for fila in filas]
    candidatos = []
    for indice, fila in enumerate(filas):
        dias_columna = {col: _dia_desde_encabezado(valor) for col, valor in enumerate(fila)}
        dias_columna = {col: dia for col, dia in dias_columna.items() if dia}
        tiene_hora = "HORA" in normalizar_texto(fila[0]) if fila else False
        if len(dias_columna) >= 2 or (len(dias_columna) == 1 and tiene_hora):
            candidatos.append((indice, dias_columna))
    if not candidatos:
        raise ValueError("No encontré una fila de encabezados con días de la semana.")
    encabezado, dias_columna = max(candidatos, key=lambda item: (len(item[1]), -item[0]))
    salida = []
    vistos = set()
    for fila in filas[encabezado + 1:]:
        intervalo = _hora_intervalo_matriz(fila[0])
        if not intervalo:
            continue
        inicio, fin = intervalo
        for columna, dia in dias_columna.items():
            celda = fila[columna].strip()
            if not celda:
                continue
            grupo, actividad = _interpretar_celda_horario(celda)
            llave = (dia, inicio, fin, normalizar_texto(celda))
            if llave in vistos:
                continue
            vistos.add(llave)
            salida.append({"Día": dia, "Inicio": inicio, "Fin": fin,
                           "Actividad": actividad, "Grupo": grupo, "Responsable": ""})
    if not salida:
        raise ValueError("No encontré celdas con actividad y horas válidas.")
    return normalizar_tabla_horario(pd.DataFrame(salida))


def _leer_pdf_horario(archivo):
    """Lee tablas de PDF directamente y usa OCR local para páginas escaneadas."""
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("La lectura de PDF no está instalada en este despliegue.") from exc
    documento = fitz.open(stream=archivo.getvalue(), filetype="pdf")
    salida, errores = [], []
    for numero, pagina in enumerate(documento, start=1):
        encontrados = []
        try:
            tablas = pagina.find_tables().tables
        except Exception:
            tablas = []
        for tabla in tablas:
            try:
                encontrados.append(_matriz_horario_a_frame(tabla.extract()))
            except ValueError:
                continue
        if not encontrados:
            pixmap = pagina.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            from types import SimpleNamespace
            pagina_imagen = SimpleNamespace(
                name=f"{archivo.name} · página {numero}.png",
                getvalue=lambda: pixmap.tobytes("png"),
            )
            try:
                encontrados.append(_leer_imagen_ocr_local(pagina_imagen))
            except Exception as exc:
                errores.append(f"Página {numero}: no se pudo reconocer; puedes revisar el PDF y completar la tabla.")
        salida.extend((f"{archivo.name} · Página {numero}", frame) for frame in encontrados)
    documento.close()
    if not salida:
        raise ValueError("No se reconocieron horarios en el PDF. Puedes usarlo como referencia y completar la tabla.")
    return salida, errores


def _leer_archivo(archivo):
    contenido = archivo.getvalue()
    nombre = archivo.name.lower()
    if nombre.endswith(".csv"):
        try:
            frame = pd.read_csv(BytesIO(contenido), encoding="utf-8-sig")
        except UnicodeDecodeError:
            frame = pd.read_csv(BytesIO(contenido), encoding="latin-1")
        return [(archivo.name, normalizar_tabla_horario(frame))], []
    if nombre.endswith(".pdf"):
        return _leer_pdf_horario(archivo)
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
                try:
                    salida.append((f"{archivo.name} · Tabla {indice}", _matriz_horario_a_frame(filas)))
                except ValueError:
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
            try:
                normalizada = normalizar_tabla_horario(frame)
            except ValueError:
                matriz = [frame.columns.tolist(), *frame.fillna("").astype(str).values.tolist()]
                normalizada = _matriz_horario_a_frame(matriz)
            salida.append((f"{archivo.name} · {hoja}", normalizada))
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
    from services.cronogramas import cargar_visitas_escuela, resumir_visitas_escuela
    from ui.cronogramas import _meses_disponibles, _mes_actual
    from ui.calendario_eventos import calendario_informativo
    meses = dict(_meses_disponibles())
    mes = st.selectbox("Mes de visitas y actividades", list(meses),
                       index=list(meses).index(_mes_actual().strftime("%Y-%m")),
                       format_func=meses.get, key=f"visitas_{normalizar_texto(nombre)}_{normalizar_texto(escuela)}")
    st.markdown("### Visitas del equipo especialista a mi escuela")
    st.caption(escuela + " · Solo se muestran las visitas del calendario actualizado.")
    try:
        visitas = resumir_visitas_escuela(cargar_visitas_escuela(escuela, mes), escuela)
        if visitas:
            st.dataframe(pd.DataFrame(visitas), hide_index=True, width="stretch")
        else:
            st.caption("Aún no hay visitas programadas para este mes.")
    except Exception:
        st.caption("Las visitas no están disponibles por ahora. Puedes continuar con tu horario.")
    calendario_informativo(mes)
    try:
        avisos = [row for row in cargar_avisos_apoyo(nombre)
                  if normalizar_texto(row.get("Escuela", "")) == normalizar_texto(escuela)
                  and row.get("Mes", "") == mes]
    except Exception:
        st.warning("No se pudieron actualizar los avisos; no se modificó ni eliminó información.")
        return
    pendientes = [row for row in avisos if str(row.get("Estado", "")).upper() == "PENDIENTE"]
    if pendientes:
        st.caption(f"{len(pendientes)} aviso(s) nuevo(s) de cronogramas para tu escuela.")
        if st.button("Marcar avisos como vistos", key=f"marcar_avisos_{normalizar_texto(escuela)}"):
            try:
                marcar_avisos_leidos([row["ID_Aviso"] for row in pendientes])
                st.rerun()
            except Exception:
                st.info("No se pudo marcar el aviso. El cronograma sigue guardado.")


def _persistir_plantilla(prefijo, nombre, escuela):
    """Solo escribe al cambiar un campo; nunca por refrescar la pantalla."""
    from services.borradores_horarios import guardar_borrador
    import json
    if not st.session_state.get(f"{prefijo}_recuperado"):
        return
    widgets = {}
    for key, value in st.session_state.items():
        if "|" in key and not any(key.endswith(f"_{st.session_state.get(f'{prefijo}_editor_version', 0)}_{campo}")
                                 for campo in ("modo", "grupo", "alumnos", "actividad", "modalidad", "espacio", "ampliar", "bloque_inicio", "bloque_fin", "semana")):
            continue
        if key.startswith(prefijo + "_") and (
                key in {f"{prefijo}_inicio", f"{prefijo}_fin", f"{prefijo}_descanso_inicio",
                        f"{prefijo}_descanso_fin", f"{prefijo}_dia", f"{prefijo}_modulo"}
                or key.startswith(f"{prefijo}_dur_")
                or key.endswith(("_modo", "_grupo", "_alumnos", "_actividad", "_modalidad", "_espacio", "_ampliar", "_bloque_inicio", "_bloque_fin", "_semana"))):
            widgets[key[len(prefijo) + 1:]] = value.isoformat() if isinstance(value, time) else value
    datos = {"widgets": widgets, "bloques": st.session_state.get(f"{prefijo}_filas", {}),
             "editor_version": st.session_state.get(f"{prefijo}_editor_version", 0)}
    firma = json.dumps(datos, ensure_ascii=False, sort_keys=True)
    if firma == st.session_state.get(f"{prefijo}_ultimo_guardado"):
        return
    try:
        guardar_borrador(nombre, escuela, datos)
        st.session_state[f"{prefijo}_ultimo_guardado"] = firma
        st.session_state.pop(f"{prefijo}_error_borrador", None)
    except Exception:
        st.session_state[f"{prefijo}_error_borrador"] = True


def _cuadricula_horario(nombre, escuela, restricciones, horarios_equipo):
    """Editor visual semanal; conserva el borrador hasta que la docente guarde."""
    prefijo = f"cuadricula_{normalizar_texto(nombre)}_{normalizar_texto(escuela)}"
    clave_franjas, clave_filas = f"{prefijo}_franjas", f"{prefijo}_filas"
    from services.borradores_horarios import cargar_borrador
    if not st.session_state.get(f"{prefijo}_recuperado"):
        try:
            datos = cargar_borrador(nombre, escuela)
            for sufijo, value in datos.get("widgets", {}).items():
                if sufijo in {"inicio", "fin"}:
                    value = time.fromisoformat(value)
                elif sufijo == "modulo" and isinstance(value, list):
                    value = tuple(value)
                st.session_state[f"{prefijo}_{sufijo}"] = value
            st.session_state[clave_filas] = datos.get("bloques", {})
            st.session_state[f"{prefijo}_editor_version"] = datos.get("editor_version", 0)
            st.session_state[f"{prefijo}_recuperado"] = True
        except Exception:
            st.warning("No se pudo recuperar el borrador. Reintenta para conservar tus cambios anteriores.")
            if st.button("Recuperar borrador", key=f"{prefijo}_recuperar"):
                st.rerun()
            return
    cambio = {"on_change": _persistir_plantilla, "args": (prefijo, nombre, escuela)}
    st.caption("Tu borrador y configuración se conservan al cerrar sesión. Guardarlo no publica el horario.")
    if st.session_state.get(f"{prefijo}_error_borrador"):
        st.warning("El último cambio sigue aquí, pero aún no se respaldó. Reintenta antes de salir.")
        if st.button("Respaldar borrador", key=f"{prefijo}_respaldar"):
            _persistir_plantilla(prefijo, nombre, escuela)
            st.rerun()
    st.markdown("### Mi plantilla semanal · lunes a viernes")
    st.caption("Elige cuánto dura cada módulo. Puedes escribir una duración repetida (60) o varias (60,60,30,60); la última se repite hasta terminar la jornada.")
    c1, c2 = st.columns(2)
    with c1:
        inicio = st.time_input("Inicio", value=time(7, 0), key=f"{prefijo}_inicio", **cambio)
    with c2:
        fin = st.time_input("Fin", value=time(13, 0), key=f"{prefijo}_fin", **cambio)
    st.caption("Configura duraciones distintas por día, separadas por comas. El descanso indicado se replica durante toda la semana.")
    duraciones_por_dia = {}
    columnas_dias = st.columns(5)
    for dia, columna in zip(DIAS, columnas_dias):
        with columna:
            duraciones_por_dia[dia] = st.text_input(f"{dia} · minutos", value="60", key=f"{prefijo}_dur_{dia}", **cambio)
    pausa_cols = st.columns([1, 1, 2])
    with pausa_cols[0]:
        descanso_inicio = st.text_input("Descanso desde · HH:MM", value="", key=f"{prefijo}_descanso_inicio", placeholder="10:00", **cambio)
    with pausa_cols[1]:
        descanso_fin = st.text_input("Descanso hasta · HH:MM", value="", key=f"{prefijo}_descanso_fin", placeholder="10:30", **cambio)
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
    borrador = st.session_state.setdefault(clave_filas, {})
    # Las franjas editadas se muestran y se imprimen aunque no coincidan con
    # la duración inicial. No se elimina ningún bloque al cambiar configuración.
    from services.horarios import _hora_minutos
    for dia in DIAS:
        ocupados=[(str(r['Inicio']),str(r['Fin'])) for r in borrador.values() if r.get('Dia')==dia]
        libres=[f for f in franjas_por_dia[dia] if f in pausas or not any(_hora_minutos(f[0])<_hora_minutos(o[1]) and _hora_minutos(o[0])<_hora_minutos(f[1]) for o in ocupados)]
        franjas_por_dia[dia]=sorted(set(libres+ocupados))
    franjas = sorted({franja for diario in franjas_por_dia.values() for franja in diario})
    st.session_state[clave_franjas] = franjas
    propia = (horarios_equipo.loc[horarios_equipo["Maestra"].astype(str).eq(nombre)].copy()
              if not horarios_equipo.empty and "Maestra" in horarios_equipo else pd.DataFrame())
    if not propia.empty and st.button("Cargar mi horario vigente para editarlo en esta plantilla", key=f"{prefijo}_cargar"):
        # Reemplaza el borrador completo; un merge deja bloques obsoletos "congelados".
        st.session_state[clave_filas] = _borrador_de_horario(propia.to_dict("records"))
        st.session_state[f"{prefijo}_editor_version"] = st.session_state.get(f"{prefijo}_editor_version", 0) + 1
        _persistir_plantilla(prefijo, nombre, escuela)
        st.rerun()
    if borrador and st.button("Reiniciar mi borrador (no borra el horario publicado)", key=f"{prefijo}_reiniciar_borrador"):
        st.session_state[clave_filas] = {}
        st.session_state[f"{prefijo}_editor_version"] = st.session_state.get(f"{prefijo}_editor_version", 0) + 1
        _persistir_plantilla(prefijo, nombre, escuela)
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
    fuera = [row for row in filas if _hora_minutos(row['Inicio'])<_hora_minutos(inicio) or _hora_minutos(row['Fin'])>_hora_minutos(fin)
             or (descanso_inicio and descanso_fin and _hora_minutos(row['Inicio'])<_hora_minutos(descanso_fin) and _hora_minutos(descanso_inicio)<_hora_minutos(row['Fin']))]
    if fuera:
        st.warning(f"Hay {len(fuera)} bloque(s) fuera de la jornada o dentro del descanso. Edítalos; tu borrador se conserva.")
        st.dataframe(pd.DataFrame(fuera), hide_index=True, width="stretch")

    st.markdown("#### Capturar o editar un espacio")
    dia_elegido = st.selectbox("Día", dias, key=f"{prefijo}_dia")
    franjas_dia = [f for f in franjas_por_dia[dia_elegido] if f not in pausas]
    if not franjas_dia:
        st.info("Este día solo tiene descanso; ajusta la jornada para añadir módulos.")
        return
    opciones_modulo=[*franjas_dia,('Nuevo bloque','')]
    if st.session_state.get(f"{prefijo}_modulo") not in opciones_modulo:
        st.session_state.pop(f"{prefijo}_modulo", None)
    franja_elegida = st.selectbox("Módulo", opciones_modulo,
                                format_func=lambda x: 'Nuevo bloque con horario libre' if not x[1] else f"{x[0]} – {x[1]}", key=f"{prefijo}_modulo")
    desde, hasta = franja_elegida
    clave = f"{dia_elegido}|{desde}|{hasta}"
    actual = borrador.get(clave, {})
    version = st.session_state.get(f"{prefijo}_editor_version", 0)
    clave_editor = f"{prefijo}_{clave}_{version}"
    c_desde,c_hasta=st.columns(2)
    desde_editado=c_desde.text_input('Inicio del bloque · HH:MM',value=desde if hasta else inicio.strftime('%H:%M'),key=clave_editor+'_bloque_inicio',**cambio)
    hasta_editado=c_hasta.text_input('Fin del bloque · HH:MM',value=hasta if hasta else fin.strftime('%H:%M'),key=clave_editor+'_bloque_fin',**cambio)
    semana=st.checkbox('La misma actividad de lunes a viernes, en este horario',key=clave_editor+'_semana',**cambio)
    dias_destino=list(DIAS) if semana else [dia_elegido]
    if semana:st.caption('Se repiten también el grupo o alumnos, la modalidad y el espacio. Se revisan las horas y choques de cada día.')
    reemplazar=st.checkbox('Reemplazar otros bloques que tengan exactamente este horario',key=clave_editor+'_reemplazar',help='No reemplaza bloques con horas distintas ni elimina registros publicados.') if semana else False
    modo_inicial = 1 if str(actual.get("ID_Alumnos", "")).strip() else (0 if str(actual.get("Grupo", "")).strip() else 2)
    modo = st.radio("Qué atenderás en este espacio", ["Grado/grupo", "Alumno(s)", "Actividad libre"],
                    index=modo_inicial, horizontal=True, key=f"{clave_editor}_modo", **cambio)
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
                             key=f"{clave_editor}_grupo", **cambio)
    elif modo == "Alumno(s)":
        por_id = {str(row.get("ID_Alumno", "")): row for row in visibles.to_dict("records")
                  if str(row.get("ID_Alumno", "")).strip()}
        ids_previos = [x for x in str(actual.get("ID_Alumnos", "")).split(",") if x in por_id]
        ids = st.multiselect("Alumno o alumnos", list(por_id), default=ids_previos,
                             format_func=lambda x: f"{por_id[x].get('Nombre_Completo', '')} · {_grupo_alumno(por_id[x])} · {x}",
                             key=f"{clave_editor}_alumnos", **cambio)
    actividad = st.text_area("Actividad o propósito (puedes redactarla libremente)",
                             value=str(actual.get("Actividad", "")),
                             key=f"{clave_editor}_actividad", **cambio)
    c_modalidad, c_espacio = st.columns(2)
    with c_modalidad:
        modalidad = st.selectbox("Modalidad", ["Grupal", "Subgrupal", "Individual", "Otra"],
                                  index=["Grupal", "Subgrupal", "Individual", "Otra"].index(actual.get("Modalidad", "Grupal")) if actual.get("Modalidad", "Grupal") in ["Grupal", "Subgrupal", "Individual", "Otra"] else 0,
                                  key=f"{clave_editor}_modalidad", **cambio)
    with c_espacio:
        espacio = st.selectbox("Espacio", ["Aula regular", "Aula de apoyo", "Otro"],
                               index=["Aula regular", "Aula de apoyo", "Otro"].index(actual.get("Espacio", "Aula regular")) if actual.get("Espacio", "Aula regular") in ["Aula regular", "Aula de apoyo", "Otro"] else 0,
                               key=f"{clave_editor}_espacio", **cambio)
    grupo_candidato = grupo
    if ids:
        grupos_alumnos = sorted({_grupo_alumno(row) for row in visibles.to_dict("records")
                                 if str(row.get("ID_Alumno", "")) in set(ids) and _grupo_alumno(row)})
        grupo_candidato = ", ".join(grupos_alumnos)
    candidato = {
        "Dia": dia_elegido, "Inicio": desde_editado, "Fin": hasta_editado,
        "Grupo": grupo_candidato,
        "ID_Alumnos": ",".join(ids),
        "Actividad": actividad.strip() or str(actual.get("Actividad", "")), "Maestra": nombre,
    }
    if candidato["Actividad"] or grupo or ids:
        try:
            vista_borrador=actualizar_bloques_borrador(borrador,clave,candidato,dias_destino,inicio,fin,descanso_inicio,descanso_fin,reemplazar)
            filas_en_vivo=list(vista_borrador.values())
            choques_en_vivo = detectar_choques(filas_en_vivo, restricciones, horarios_equipo)
            conflictos_bloque = [r for r in choques_en_vivo.to_dict("records") if r.get("Día") in dias_destino]
            if conflictos_bloque:
                st.error("⚠️ Conflicto de horario en este módulo. Ajusta día/hora o revisa los horarios de referencia antes de guardar.")
                st.dataframe(pd.DataFrame(conflictos_bloque), hide_index=True, width="stretch")
            else:
                st.success("✓ Sin choque detectado en este módulo.")
        except ValueError as exc:
            st.info(str(exc))
        except Exception:
            st.warning('No se pudo verificar el bloque. Tu borrador se conserva.')
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
                bloque = {
                    "Dia": dia_elegido, "Inicio": desde_editado, "Fin": hasta_editado,
                    "Grupo": grupo or ", ".join(grupos),
                    "Alumnos": "; ".join(str(row.get("Nombre_Completo", "")) for row in elegidos),
                    "ID_Alumnos": ",".join(ids),
                    "Actividad": actividad.strip() or ("Atención individual" if len(ids) == 1 else "Atención de apoyo"),
                    "Modalidad": modalidad, "Espacio": espacio, "Maestra": nombre,
                }
                try:
                    actualizado=actualizar_bloques_borrador(borrador,clave,bloque,dias_destino,inicio,fin,descanso_inicio,descanso_fin,reemplazar)
                    st.session_state[clave_filas]=actualizado
                    st.session_state[f'{prefijo}_editor_version']=version+1
                    _persistir_plantilla(prefijo, nombre, escuela)
                    st.rerun()
                except ValueError as exc:st.info(str(exc))
    with c_vaciar:
        if actual and st.button("Quitar este bloque del borrador", key=f"{prefijo}_vaciar_{clave}"):
            borrador.pop(clave, None)
            st.session_state[f"{prefijo}_editor_version"] = version + 1
            _persistir_plantilla(prefijo, nombre, escuela)
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
            pdf = generar_horario_apoyo_cuadricula_pdf(escuela, nombre, filas_pdf, franjas, franjas_por_dia)
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
    st.caption("Acepta Excel, CSV, Word, PDF e imágenes. El lector propone los bloques; revísalos antes de guardar.")
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
            elif archivo.name.lower().endswith(".pdf"):
                referencias.append((archivo, "pdf"))
                errores.append(f"{archivo.name}: {exc}")
            else:
                errores.append(f"{archivo.name}: {exc}")
    imagenes = [archivo for archivo, tipo in referencias if tipo == "imagen"]
    if not imagenes:
        _limpiar_borradores_imagen_sin_carga(nombre, escuela)
    if imagenes:
        st.markdown(f"#### 🖼️ {len(imagenes)} imagen(es) cargada(s)")
        if st.button("🧹 Quitar esta carga y empezar de nuevo", key=f"limpiar_carga_{clave_identidad}_{version_carga}"):
            for archivo in imagenes:
                _limpiar_lectura_imagen(nombre, escuela, archivo)
            st.session_state[clave_version_carga] = version_carga + 1
            st.rerun()
        pendientes = [archivo for archivo in imagenes
                      if _clave_imagen_horario(nombre, escuela, archivo) not in st.session_state
                      and f"ocr_error_{_clave_imagen_horario(nombre, escuela, archivo)}" not in st.session_state]
        if pendientes:
            with st.spinner("Leyendo horarios…"):
                leidas, fallos = _leer_imagenes_pendientes(imagenes, nombre, escuela)
            if leidas or fallos:
                st.rerun()
        hay_lectura_fallida = any(
            f"ocr_error_{_clave_imagen_horario(nombre, escuela, archivo)}" in st.session_state
            for archivo in imagenes
        )
        if hay_lectura_fallida:
            st.warning("No se pudo leer una parte. Puedes reintentar o completar la tabla.")
            if st.button("↻ Reintentar lectura", type="primary", key=f"analizar_imagenes_{clave_identidad}_{version_carga}"):
                for archivo in imagenes:
                    st.session_state.pop(
                        f"ocr_error_{_clave_imagen_horario(nombre, escuela, archivo)}", None,
                    )
                with st.spinner("Reintentando lectura…"):
                    leidas, fallos = _leer_imagenes_pendientes(imagenes, nombre, escuela)
                if leidas or fallos:
                    st.rerun()
        else:
            st.success("Lectura lista. Revisa los bloques antes de guardarlos.")
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
        elif tipo == "pdf":
            st.download_button(
                f"Abrir PDF de referencia: {archivo.name}", data=archivo.getvalue(),
                file_name=archivo.name, mime="application/pdf",
                key=f"abrir_pdf_horario_{clave_identidad}_{hashlib.sha256(archivo.getvalue()).hexdigest()[:10]}",
            )
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
        ambiguos=[r for r in restricciones.to_dict('records') if not str(r.get('Grupo','')).strip() and not _referencia_general(r)]
        if ambiguos:
            st.warning('Hay actividades sin grupos confirmados. Se muestran como referencia y no bloquean automáticamente a todos los alumnos. Confirma los grupos con el docente y corrige la referencia antes de considerar definitivo tu horario.')
            st.dataframe(_tabla_vista(pd.DataFrame(ambiguos)),hide_index=True,width='stretch')
        with st.expander('Corregir horarios de referencia guardados'):
            st.caption('Puedes corregir día, horas, actividad y grupos o quitar filas incorrectas, sin subir otra imagen. La corrección es compartida por esta escuela; se conserva la versión anterior. Grupo vacío: por confirmar. Escribe Todos solo si se confirmó que participa toda la escuela.')
            archivos=sorted(restricciones['Archivo'].fillna('').astype(str).unique())
            archivo=st.selectbox('Referencia que corregirás',archivos,key='editar_referencia_'+clave_identidad)
            seleccion=restricciones.loc[restricciones['Archivo'].fillna('').astype(str).eq(archivo)]
            version=str(seleccion.iloc[-1].get('ID_Version',''))
            editkey='referencia_guardada_'+hashlib.sha256((clave_identidad+archivo+version).encode()).hexdigest()[:24]
            columnas=['Dia','Inicio','Fin','Actividad','Grupo','Responsable']
            base=seleccion.reindex(columns=columnas).fillna('').reset_index(drop=True)
            editado=st.data_editor(base,num_rows='dynamic',hide_index=True,width='stretch',key=editkey,
                column_config={'Dia':st.column_config.SelectboxColumn('Día',options=list(DIAS),required=True),'Grupo':st.column_config.TextColumn('Grupos confirmados',help='Ejemplo: 3A, 4B. Vacío significa pendiente, no todos.')})
            confirma=st.checkbox('Revisé la corrección y confirmo actualizar la referencia de esta escuela',key=editkey+'_confirmar')
            if st.button('Guardar corrección de referencia',disabled=not confirma,key=editkey+'_guardar'):
                try:
                    editar_referencia(escuela,archivo,editado,version)
                    st.success('Referencia corregida. Se conserva su historial y se recalculan los choques.');st.rerun()
                except (ValueError,PermissionError,RuntimeError) as exc:st.warning(str(exc))
                except Exception:st.warning('No se confirmó la corrección. Tu edición permanece aquí; actualiza las referencias antes de reintentar.')
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

import html
import base64
import json
import pandas as pd
from io import BytesIO
from pathlib import Path
from fpdf import FPDF
from config.settings import SERVICE_NAME, SCHOOL_YEAR


def header_b64(path="encabezado.png"):
    """Incrusta el encabezado oficial con una ruta estable en producción."""
    try:
        archivo = Path(path)
        if not archivo.is_absolute():
            archivo = Path(__file__).resolve().parents[1] / archivo
        with archivo.open("rb") as f:
            return "data:image/png;base64," + base64.b64encode(f.read()).decode()
    except Exception:
        return ""


def anexo4_html(alumno, rows):
    """Vista previa imprimible del Anexo IV con espacio amplio y firmas apiladas."""
    if rows is None or rows.empty:
        rows = pd.DataFrame([{}])
    head = header_b64()
    nombre = html.escape(str(alumno.get("Nombre_Completo", "Alumno / grupo")))
    out = [
        "<html><head><meta charset='UTF-8'><style>"
        "@page{size:letter portrait;margin:15mm}"
        "body{font-family:Arial,sans-serif;color:#111;font-size:10pt}"
        "img{max-width:100%}.header{text-align:center;margin-bottom:12px}"
        ".hoja{page-break-after:always}.meta{margin:10px 0 14px}"
        ".campo{border:1px solid #222;padding:8px;margin:5px 0 12px;white-space:pre-wrap}"
        ".sugerencias{min-height:150px}.resultados{min-height:45px}"
        ".firmas{width:72%;margin:22px auto 0;text-align:center}"
        ".firma{min-height:58px;border:1px solid #222;padding:12px;margin:8px 0}"
        "@media print{.hoja:last-child{page-break-after:auto}}"
        "</style></head><body>"
    ]
    for _, r in rows.iterrows():
        sugerencias = html.escape(str(r.get("Sugerencias", ""))).replace("\n", "<br>")
        resultados = html.escape(
            str(r.get("Nivel_Cumplimiento_Resultados", ""))
        ).replace("\n", "<br>")
        motivo = html.escape(str(r.get("Motivo", "")))
        area = html.escape(str(r.get("Sugerencias_Area", "Aprendizaje")))
        seguimiento = html.escape(str(r.get("Fecha_Seguimiento", "")))
        fecha = html.escape(str(r.get("Fecha_Elaboracion", "")))
        quien_brinda = html.escape(str(r.get("Quien_Brinda_Sugerencias", "")))
        escuela = html.escape(str(r.get("Escuela", "")))
        grado_grupo = html.escape(str(r.get("Grado_Grupo", "")))
        out.append(
            f"<section class='hoja'><div class='header'><img src='{head}'></div>"
            "<h2 style='text-align:center;text-decoration:underline'>"
            "Anexo IV. Hoja de sugerencias"
            "</h2>"
            f"<div class='meta'><b>Alumno / grupo:</b> {nombre}<br>"
            f"<b>Grado y grupo:</b> {grado_grupo}<br>"
            f"<b>Escuela:</b> {escuela}<br><b>Servicio:</b> {SERVICE_NAME}<br>"
            f"<b>Área:</b> {area}<br><b>Fecha:</b> {fecha}<br>"
            f"<b>Motivo:</b> {motivo}<br><b>Seguimiento:</b> {seguimiento}</div>"
            "<b>Sugerencias</b>"
            f"<div class='campo sugerencias'>{sugerencias or '&nbsp;'}</div>"
            "<b>Nivel de cumplimiento y resultados</b>"
            f"<div class='campo resultados'>{resultados or '&nbsp;'}</div>"
            "<div class='firmas'><b>Firmas</b>"
            "<div class='firma'>______________________________<br>"
            "Nombre y firma de quien recibe</div>"
            f"<div class='firma'>______________________________<br>"
            f"Nombre y firma de quien brinda<br>{quien_brinda}</div>"
            "</div></section>"
        )
    out.append("</body></html>")
    return "".join(out)


def anexo4_pdf(alumno, rows):
    """Genera el Anexo IV en PDF carta vertical con sugerencias amplias y firmas en una columna."""
    if rows is None or rows.empty:
        rows = pd.DataFrame([{}])
    pdf = FPDF(orientation="P", unit="mm", format="letter")
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=15)
    disponible = 180

    for _, registro in rows.iterrows():
        pdf.add_page()
        head = header_b64()
        if head:
            try:
                pdf.image(
                    BytesIO(base64.b64decode(head.split(",", 1)[1])),
                    x=15, y=8, w=180,
                )
            except Exception:
                pass
        pdf.set_y(38)
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(247, 127, 35)
        pdf.cell(
            0, 8, "Anexo IV. Hoja de sugerencias",
            align="C", new_x="LMARGIN", new_y="NEXT",
        )
        pdf.set_text_color(0, 0, 0)
        pdf.ln(3)
        pdf.set_font("Helvetica", "", 9)
        metadatos = (
            f"Alumno / grupo: {alumno.get('Nombre_Completo', 'Alumno / grupo')}\n"
            f"Grado y grupo: {registro.get('Grado_Grupo', '')}\n"
            f"Escuela: {registro.get('Escuela', '')}\n"
            f"Servicio: {SERVICE_NAME}\n"
            f"Área: {registro.get('Sugerencias_Area', 'Aprendizaje')}    "
            f"Fecha: {registro.get('Fecha_Elaboracion', '')}\n"
            f"Motivo: {registro.get('Motivo', '')}\n"
            f"Seguimiento: {registro.get('Fecha_Seguimiento', '')}"
        )
        pdf.multi_cell(0, 5, metadatos)
        pdf.ln(3)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(
            0, 6, "Sugerencias", new_x="LMARGIN", new_y="NEXT",
        )
        pdf.set_font("Helvetica", "", 10)
        sugerencias = str(registro.get("Sugerencias", "") or " ")
        pdf.multi_cell(
            disponible, 5, sugerencias + "\n\n\n\n",
            border=1, new_x="LMARGIN", new_y="NEXT",
        )
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(
            0, 5, "Nivel de cumplimiento y resultados",
            new_x="LMARGIN", new_y="NEXT",
        )
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(
            disponible, 5,
            str(registro.get("Nivel_Cumplimiento_Resultados", "") or " "),
            border=1, new_x="LMARGIN", new_y="NEXT",
        )
        pdf.ln(5)
        ancho_firmas = 132
        x_firmas = 15 + (disponible - ancho_firmas) / 2
        pdf.set_x(x_firmas)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(
            ancho_firmas, 5, "Firmas",
            align="C", new_x="LMARGIN", new_y="NEXT",
        )
        pdf.set_xy(x_firmas, pdf.get_y())
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(
            ancho_firmas, 5,
            "______________________________\nNombre y firma de quien recibe",
            border=1, align="C", new_x="LMARGIN", new_y="NEXT",
        )
        pdf.set_xy(x_firmas, pdf.get_y())
        pdf.multi_cell(
            ancho_firmas, 5,
            "______________________________\nNombre y firma de quien brinda\n"
            + str(registro.get("Quien_Brinda_Sugerencias", "")),
            border=1, align="C", new_x="LMARGIN", new_y="NEXT",
        )

    return bytes(pdf.output())


def anexo5_html(alumno, rows):
    """Una sola hoja por alumno con todas las anotaciones en orden cronológico."""
    head = header_b64()
    rows = rows.copy()
    if not rows.empty and "Fecha" in rows.columns:
        rows["_orden_cronologico"] = pd.to_datetime(
            rows["Fecha"], errors="coerce", dayfirst=True
        )
        rows = (
            rows.sort_values("_orden_cronologico", na_position="last", kind="stable")
            .drop(columns="_orden_cronologico")
        )
    out = ["<html><head><meta charset='UTF-8'><style>@page{size:letter portrait;margin:15mm}body{font-family:Arial,sans-serif;color:#111;margin:0}table{width:100%;border-collapse:collapse}thead{display:table-header-group}tr{page-break-inside:avoid}th,td{border:1px solid #111;padding:8px;vertical-align:top}</style></head><body>"]
    out.append(f"<div style='text-align:center'><img src='{head}' style='max-width:100%'></div><h2 style='text-align:center;text-decoration:underline'>Anexo V. Eventos significativos.</h2><p><b>Nombre del alumno:</b> {html.escape(str(alumno.get('Nombre_Completo','')))}</p><table><thead><tr><th>Fecha</th><th>Evento</th><th>Especialista / docente, firma y fecha</th></tr></thead><tbody>")
    for _, r in rows.iterrows():
        out.append(f"<tr><td>{html.escape(str(r.get('Fecha','')))}</td><td>{html.escape(str(r.get('Evento',''))).replace(chr(10),'<br>')}</td><td style='text-align:center'><br><br>_____________________<br>{html.escape(str(r.get('Especialista','')))}</td></tr>")
    out.append("</tbody></table></body></html>")
    return "".join(out)


def anexo3_html(alumno, rows):
    """Genera una vista imprimible de las observaciones BAP guardadas."""
    head = header_b64()
    nombre = html.escape(str(alumno.get("Nombre_Completo", "")))
    out = [
        "<html><head><meta charset='UTF-8'><style>"
        "body{font-family:Arial,sans-serif;color:#111;margin:28px;}"
        "table{width:100%;border-collapse:collapse;margin-top:16px;}"
        "th,td{border:1px solid #111;padding:8px;vertical-align:top;}"
        "th{background:#eef3f7;text-align:left}.header{text-align:center}"
        "@media print{@page{margin:1cm}}"
        "</style></head><body>"
    ]
    for _, r in rows.iterrows():
        try:
            respuestas = json.loads(str(r.get("BAP_Fisicas", "{}")) or "{}")
        except (TypeError, json.JSONDecodeError):
            respuestas = {}
        out.append(
            f"<section><div class='header'><img src='{head}' style='max-width:100%'></div>"
            "<h2 style='text-align:center;text-decoration:underline'>"
            "Anexo III. BAP — Instrumento de observación de barreras para el aprendizaje y la participación"
            "</h2>"
            f"<p><b>Alumno o grupo:</b> {nombre}<br>"
            f"<b>Fecha:</b> {html.escape(str(r.get('Fecha', '')))}<br>"
            f"<b>Personal:</b> {html.escape(str(r.get('ID_Personal', '')))}</p>"
            "<table><tr><th>Indicador observado</th><th>Frecuencia</th>"
            "<th>Observación específica</th><th>Requiere orientación</th></tr>"
        )
        for respuesta in respuestas.values():
            if not isinstance(respuesta, dict):
                continue
            pregunta = html.escape(str(respuesta.get("pregunta", "")))
            frecuencia = html.escape(str(respuesta.get("frecuencia", "")))
            orientacion = "Sí" if respuesta.get("orientacion") else "No"
            out.append(
                f"<tr><td>{pregunta}</td><td>{frecuencia}</td>"
                f"<td>{html.escape(str(respuesta.get('observacion', ''))).replace(chr(10), '<br>')}</td>"
                f"<td>{orientacion}</td></tr>"
            )
        out.append("</table></section><div style='page-break-after:always'></div>")
    out.append("</body></html>")
    return "".join(out)


def anexo7_html(alumno, registro):
    """Hoja de derivación imprimible con los indicadores capturados."""
    respuestas = json.loads(str(registro.get("Respuestas_JSON", "[]")) or "[]")
    filas = []
    for indice, respuesta in enumerate(respuestas, start=1):
        pregunta = html.escape(str(respuesta.get("pregunta", "")))
        valor = html.escape(str(respuesta.get("valor", "")))
        filas.append(f"<tr><td>{indice}</td><td>{pregunta}</td><td>{valor}</td></tr>")
    tabla = "".join(filas)
    head = header_b64()
    return f"""<html><head><meta charset='UTF-8'><style>
    @page{{size:letter portrait;margin:14mm}} body{{font-family:Arial,sans-serif;color:#111;font-size:10pt}}
    img{{max-width:100%}} h2{{text-align:center}} table{{width:100%;border-collapse:collapse}}
    th,td{{border:1px solid #111;padding:5px;vertical-align:top}} th{{text-align:center}}
    .datos td{{border:0;padding:2px}} .firma{{margin-top:28px;text-align:right}}
    </style></head><body><div style='text-align:center'><img src='{head}'></div>
    <h2>Anexo VII. Hoja de Derivación.</h2>
    <table class='datos'><tr><td><b>Nombre del alumno:</b> {html.escape(str(alumno.get('Nombre_Completo','')))}</td><td><b>Fecha de nacimiento:</b> {html.escape(str(registro.get('Fecha_Nacimiento','')))}</td></tr>
    <tr><td><b>Escuela:</b> {html.escape(str(registro.get('Escuela','')))}</td><td><b>Edad:</b> {html.escape(str(alumno.get('Edad_1_Septiembre','')))} &nbsp; <b>Grado:</b> {html.escape(str(alumno.get('Grado','')))} &nbsp; <b>Grupo:</b> {html.escape(str(alumno.get('Grupo','')))}</td></tr>
    <tr><td><b>Docente:</b> {html.escape(str(registro.get('Docente_Regular','')))}</td><td><b>Fecha de aplicación:</b> {html.escape(str(registro.get('Fecha','')))}</td></tr></table>
    <p><b>Instrucción:</b> Marca la frecuencia con la que el alumno se desempeña en cada indicador.</p>
    <table><tr><th>No.</th><th>Preguntas</th><th>Frecuencia</th></tr>{tabla}</table>
    <p><b>Condición de salud:</b> {html.escape(str(registro.get('Salud','')))}<br><b>Seguimiento médico:</b> {html.escape(str(registro.get('Seguimiento_Medico','')))}<br><b>Aspecto relevante:</b> {html.escape(str(registro.get('Aspecto_Relevante','')))}</p>
    <div class='firma'>_________________________________<br>Docente de grupo regular<br>Nombre y firma</div></body></html>"""


def anexo7_pdf(registro):
    """Genera el Anexo VII oficial en PDF carta vertical para impresión."""
    try:
        respuestas = json.loads(str(registro.get("Respuestas_JSON", "[]")) or "[]")
    except (TypeError, json.JSONDecodeError):
        respuestas = []

    class AnexoVII(FPDF):
        def header(self):
            encabezado = header_b64()
            if encabezado:
                try:
                    contenido = encabezado.split(",", 1)[1]
                    self.image(
                        BytesIO(base64.b64decode(contenido)),
                        x=12, y=8, w=192,
                    )
                except Exception:
                    pass
            self.set_y(38)
            self.set_font("Helvetica", "B", 14)
            self.set_text_color(247, 127, 35)
            self.cell(0, 7, "Anexo VII. Hoja de Derivación.", align="C", new_x="LMARGIN", new_y="NEXT")
            self.set_text_color(0, 0, 0)

        def footer(self):
            self.set_y(-10)
            self.set_font("Helvetica", "", 7)
            self.cell(0, 4, "USAER 02E - Anexo VII. Hoja de Derivación", align="C")

    pdf = AnexoVII(orientation="P", unit="mm", format="letter")
    pdf.set_margins(12, 12, 12)
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.add_page()
    pdf.set_y(50)

    # La hoja se entrega vacía: la completa manualmente el docente regular.
    escuela = ""
    fecha = ""
    docente = ""

    x, y, w, h = 12, pdf.get_y(), 192, 43
    pdf.rect(x, y, w, h)
    pdf.set_font("Helvetica", "", 9)
    lineas = [
        f"Nombre del alumno: _______________________________________    Fecha de nacimiento: ______________",
        "Escuela: _________________________________________________    Edad: ____  Grado: ____  Grupo: ____",
        "Inscrito a la escuela desde: ____________  Atendido por usted desde: ___________________________",
        "Ha repetido algún curso escolar: ________  ¿Cuál? ______________________________________________",
        "Nombre del docente: ______________________________________________________________________",
        "Fecha de aplicación: _________________________  Curso escolar: _______________________________",
    ]
    for linea in lineas:
        pdf.set_x(x + 2)
        pdf.cell(w - 4, 6.5, linea, new_x="LMARGIN", new_y="NEXT")
    pdf.set_y(y + h + 3)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(
    0,
    5,
    "Datos Complementarios:",
    new_x="LMARGIN",
    new_y="NEXT"
)
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(
    0,
    4.5,
    "Marca con una X la frecuencia con la que el alumno se desempeña en cada uno de los siguientes aspectos.",
    new_x="LMARGIN",
    new_y="NEXT",
)
    escala = ["Siempre", "Muchas\nveces", "Algunas\nveces", "Nunca"]
    ancho_numero, ancho_indicador = 8, 92
    ancho_escala = (192 - ancho_numero - ancho_indicador) / 4

    def encabezado_tabla():
        pdf.set_font("Helvetica", "B", 8)
        altura = 9
        y_inicio = pdf.get_y()
        x_inicio = 12
        pdf.set_xy(x_inicio, y_inicio)
        pdf.cell(ancho_numero, altura, "No.", border=1, align="C")
        pdf.cell(ancho_indicador, altura, "Aspectos a observar", border=1, align="C")
        x_escala = x_inicio + ancho_numero + ancho_indicador
        for indice, opcion in enumerate(escala):
            pdf.set_xy(x_escala + indice * ancho_escala, y_inicio)
            pdf.multi_cell(
                ancho_escala, altura / 2, opcion, border=1, align="C",
                max_line_height=altura / 2,
            )
        pdf.set_xy(x_inicio, y_inicio + altura)

    encabezado_tabla()
    pdf.set_font("Helvetica", "", 7.3)
    for indice, respuesta in enumerate(respuestas, start=1):
        pregunta = str(respuesta.get("pregunta", "")).strip()
        valor = ""
        lineas_pregunta = max(1, int(pdf.get_string_width(pregunta) / (ancho_indicador - 3)) + 1)
        altura = max(6.2, lineas_pregunta * 3.5)
        if pdf.get_y() + altura > 263:
            pdf.add_page()
            pdf.set_y(50)
            encabezado_tabla()
            pdf.set_font("Helvetica", "", 7.3)
        y_fila = pdf.get_y()
        x_fila = 12
        pdf.set_xy(x_fila, y_fila)
        pdf.cell(ancho_numero, altura, str(indice), border=1, align="C")
        pdf.set_xy(x_fila + ancho_numero, y_fila)
        pdf.multi_cell(
            ancho_indicador, 3.5, pregunta, border=1, align="L",
            max_line_height=3.5,
        )
        x_escala = x_fila + ancho_numero + ancho_indicador
        for posicion, opcion in enumerate(["Siempre", "Muchas veces", "Algunas veces", "Nunca"]):
            pdf.set_xy(x_escala + posicion * ancho_escala, y_fila)
            pdf.cell(
                ancho_escala, altura, "X" if valor == opcion else "",
                border=1, align="C",
            )
        pdf.set_xy(x_fila, y_fila + altura)

        if pdf.get_y() > 225:
            pdf.add_page()
            pdf.set_y(50)

    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 9)

    pdf.cell(
        0,
        5,
        "Datos complementarios",
        new_x="LMARGIN",
        new_y="NEXT",
    )

    pdf.set_font("Helvetica", "", 8)

    complementos = [
        ("Condición de salud y especificación", str(registro.get("Salud", ""))),
        ("Seguimiento médico familiar", str(registro.get("Seguimiento_Medico", ""))),
        ("Aspecto relevante no contemplado", str(registro.get("Aspecto_Relevante", ""))),
    ]

    for etiqueta, valor in complementos:
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(
            192,
            5,
            f"{etiqueta}: {valor or '________________________________________'}",
            border=1,
            new_x="LMARGIN",
            new_y="NEXT",
        )

    pdf.ln(12)
    pdf.set_font("Helvetica", "", 9)

    pdf.cell(
        0,
        5,
        "____________________________________________",
        align="C",
        new_x="LMARGIN",
        new_y="NEXT",
    )

    pdf.cell(
        0,
        5,
        "Docente de grupo regular - Nombre y firma",
        align="C",
    )

    return bytes(pdf.output())

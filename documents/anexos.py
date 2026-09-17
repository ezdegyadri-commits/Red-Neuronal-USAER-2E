import html
import base64
import json
from pathlib import Path
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
    head = header_b64()
    out = ["<html><head><meta charset='UTF-8'><style>body{font-family:Arial,sans-serif;color:#111}table{width:100%;border-collapse:collapse}th,td{border:1px solid #111;padding:8px;vertical-align:top}.header{text-align:center}.page{margin-bottom:40px;page-break-after:always}</style></head><body>"]
    for _, r in rows.iterrows():
        sugerencias = html.escape(str(r.get("Sugerencias", ""))).replace("\n", "<br>")
        out.append(f"""<div class='page'><div class='header'><img src='{head}' style='max-width:100%'></div><h2 style='text-align:center;text-decoration:underline'>Anexo IV. Hoja de Sugerencias.</h2>
<p><b>Nombre del alumno:</b> {html.escape(str(alumno.get('Nombre_Completo','')))}<br><b>Grado y grupo:</b> {html.escape(str(r.get('Grado_Grupo','')))}<br><b>Escuela:</b> {html.escape(str(r.get('Escuela','')))}<br><b>Servicio de EE:</b> {SERVICE_NAME}</p>
<p><b>Sugerencias del área:</b> {html.escape(str(r.get('Sugerencias_Area','Aprendizaje')))}<br><b>Fecha de elaboración:</b> {html.escape(str(r.get('Fecha_Elaboracion','')))}<br><b>Motivo:</b> {html.escape(str(r.get('Motivo','')))}<br><b>Fecha de seguimiento:</b> {html.escape(str(r.get('Fecha_Seguimiento','')))}</p>
<table><tr><th>Sugerencias</th><th>Indique el nivel de cumplimiento y describa los resultados</th><th>Nombre y firma de quien recibe</th><th>Nombre y firma de quien brinda</th></tr><tr><td style='width:40%'>{sugerencias}</td><td style='width:20%'>{html.escape(str(r.get('Nivel_Cumplimiento_Resultados','')))}</td><td style='text-align:center'><br><br>_____________________<br>Maestro(a) de Grupo</td><td style='text-align:center'><br><br>_____________________<br>{html.escape(str(r.get('Quien_Brinda_Sugerencias','')))}</td></tr></table></div>""")
    out.append("</body></html>")
    return "".join(out)


def anexo5_html(alumno, rows):
    head = header_b64()
    out = ["<html><head><meta charset='UTF-8'><style>body{font-family:Arial,sans-serif;color:#111}table{width:100%;border-collapse:collapse}th,td{border:1px solid #111;padding:8px;vertical-align:top}</style></head><body>"]
    out.append(f"<div style='text-align:center'><img src='{head}' style='max-width:100%'></div><h2 style='text-align:center;text-decoration:underline'>Anexo V. Hoja de Eventos Significativos.</h2><p><b>Nombre del alumno:</b> {html.escape(str(alumno.get('Nombre_Completo','')))}</p><table><tr><th>Fecha</th><th>Evento</th><th>Especialista, firma, fecha.</th></tr>")
    for _, r in rows.iterrows():
        out.append(f"<tr><td>{html.escape(str(r.get('Fecha','')))}</td><td>{html.escape(str(r.get('Evento',''))).replace(chr(10),'<br>')}</td><td style='text-align:center'><br><br>_____________________<br>{html.escape(str(r.get('Especialista','')))}</td></tr>")
    out.append("</table></body></html>")
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
            "Anexo III. Instrumento de observación de barreras para el aprendizaje y la participación"
            "</h2>"
            f"<p><b>Alumno o grupo:</b> {nombre}<br>"
            f"<b>Fecha:</b> {html.escape(str(r.get('Fecha', '')))}<br>"
            f"<b>Personal:</b> {html.escape(str(r.get('ID_Personal', '')))}</p>"
            "<table><tr><th>Indicador observado</th><th>Frecuencia</th>"
            "<th>Requiere orientación</th></tr>"
        )
        for respuesta in respuestas.values():
            if not isinstance(respuesta, dict):
                continue
            pregunta = html.escape(str(respuesta.get("pregunta", "")))
            frecuencia = html.escape(str(respuesta.get("frecuencia", "")))
            orientacion = "Sí" if respuesta.get("orientacion") else "No"
            out.append(
                f"<tr><td>{pregunta}</td><td>{frecuencia}</td>"
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

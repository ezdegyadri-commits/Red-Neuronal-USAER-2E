import html
import base64
from config.settings import SERVICE_NAME, SCHOOL_YEAR


def header_b64(path="encabezado.png"):
    try:
        with open(path, "rb") as f:
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

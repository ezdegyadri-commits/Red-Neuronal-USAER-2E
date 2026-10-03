"""Actas PDF desde los datos conservados en Registro_Visitas."""
from io import BytesIO
from html import escape
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle


def visita_pdf(*, titulo, folio, escuela, lugar, fecha, ciclo, especialidad, motivos, detalles, descripcion, firmantes):
    stream = BytesIO()
    styles = getSampleStyleSheet()
    body = ParagraphStyle('VisitaBody', parent=styles['Normal'], fontSize=10, leading=13, spaceAfter=7)
    center = ParagraphStyle('VisitaFirma', parent=body, fontSize=9, leading=12, alignment=1)
    title = ParagraphStyle('VisitaTitle', parent=styles['Heading1'], fontSize=14, leading=18, alignment=1, spaceAfter=14)
    def p(value, style=body):
        return Paragraph(escape(str(value or '')).replace('\n', '<br/>'), style)
    root = Path(__file__).resolve().parents[1]
    def letterhead(canvas, document):
        width, height = letter
        for filename, y, h in (('encabezado.png', height-95, 85), ('pie_pagina.png', 8, 48)):
            path = root / filename
            if path.exists():
                canvas.drawImage(str(path), 20, y, width=width-40, height=h, preserveAspectRatio=True, anchor='c', mask='auto')
        canvas.setFont('Helvetica', 8)
        canvas.drawRightString(width-36, 57, f'Folio: {folio} | Página {document.page}')
    doc = SimpleDocTemplate(stream, pagesize=letter, leftMargin=38, rightMargin=38, topMargin=110, bottomMargin=74)
    story = [p(titulo, title), p(f'Servicio: {especialidad}'), p(f'Ciclo escolar: {ciclo}     Fecha: {fecha}'),
             p(f'Escuela / sede: {escuela}'), p(f'Lugar: {lugar}     Localidad: Mérida, Yucatán'),
             p('Motivos y actividades', styles['Heading3']), p('\n'.join(f'- {m}' for m in motivos)),
             p(detalles), p('Descripción, temas tratados y acuerdos', styles['Heading3']), p(descripcion)]
    cells = [[Spacer(1, 28), p('________________________________', center), p(nombre, center), p(cargo, center)] for nombre, cargo in firmantes]
    rows = [cells[i:i+2] + ([''] if len(cells[i:i+2]) == 1 else []) for i in range(0, len(cells), 2)]
    if rows:
        table = Table(rows, colWidths=[(letter[0]-76)/2]*2)
        table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('BOTTOMPADDING', (0,0), (-1,-1), 12)]))
        story.extend([Spacer(1, 10), table])
    doc.build(story, onFirstPage=letterhead, onLaterPages=letterhead)
    return stream.getvalue()

"""Informe único del Anexo XVII, con tablas ampliadas según Anexo XVIII."""
from io import BytesIO
from pathlib import Path
from html import escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, KeepTogether
from services.epp_modelo import SECCIONES, AREAS, NEE, BAP, FAMILIA, HISTORIA, GENERALES, conclusion_vigente
from services.epp_entrada import precargar

def _recursos_firmas():
    base = Path(__file__).resolve().parents[1]
    firma_dir = base / "firma.png"
    sello_img = base / "sello.png"
    return (str(firma_dir) if firma_dir.exists() else None,
            str(sello_img) if sello_img.exists() else None)

def _firma_especialista(nombre):
    if not nombre or not str(nombre).strip():
        return None
    try:
        import streamlit as st
        firmas = st.secrets.get("CRONOGRAMAS_FIRMAS", {})
        if isinstance(firmas, str):
            import json
            firmas = json.loads(firmas)
        firma_id = firmas.get(nombre)
        if firma_id:
            from data.google import service_account_drive_service
            data = service_account_drive_service().files().get_media(fileId=firma_id).execute()
            if data:
                return BytesIO(data)
    except Exception:
        pass
    return None

def generar_pdf(doc, alumno, incluir_firmas=True):
    out = BytesIO(); styles = getSampleStyleSheet()
    small = ParagraphStyle('EPPCelda', parent=styles['Normal'], fontSize=8, leading=10)
    center = ParagraphStyle('EPPCeldaCentrada', parent=styles['Normal'], fontSize=7.5, leading=9.5, alignment=1)
    center_bold = ParagraphStyle('EPPCeldaCentradaNegrita', parent=styles['Normal'], fontSize=8, leading=10, alignment=1)
    def p(t, style=small): return Paragraph(escape(str(t or '')).replace('\n', '<br/>') or ' ', style)
    def cell_content(v):
        if hasattr(v, 'drawOn') or isinstance(v, (list, tuple)):
            return v
        return p(v)
    def table(headers, rows, signature=False):
        data = [[p(h) for h in headers]] + [[cell_content(r.get(h, '')) for h in headers] for r in rows or [{}]]
        t = Table(data, colWidths=[540 / len(headers)] * len(headers), repeatRows=1, splitInRow=1,
            rowHeights=[None] + [54] * len(data[1:]) if signature else None)
        t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E7ECEB')),
            ('GRID', (0, 0), (-1, -1), .3, colors.grey), ('VALIGN', (0, 0), (-1, -1), 'TOP')]))
        return t
    values = {a: doc['partes'].get(a, {}).get('contenido', {}) for a in (*AREAS, 'Conclusión')}
    values['Aprendizaje'] = precargar(values['Aprendizaje'], alumno,doc)
    fecha = max((v['fecha'] for v in doc['partes'].values()), default='')[:10]
    epp_oficial_concluida = conclusion_vigente(doc) and all(values[a].get('validada') for a in AREAS)
    story = [p('Informe de Evaluación Psicopedagógica', styles['Title']), p('Servicio de Apoyo de Educación Especial · Anexo XVII'),
        p('Nombre de la escuela: ' + str(alumno.get('Nombre_Escuela', ''))),
        p('Nivel educativo: ' + str(alumno.get('Nivel_Educativo', '')) + ' · Zona escolar: 001'),
        p('Servicio de Apoyo: USAER 02-E · Fecha de elaboración: ' + fecha + ' · Ciclo: ' + doc['ciclo']),
        p('Borrador interdisciplinario; pendiente de validación.' if not epp_oficial_concluida else 'Informe oficial concluido y validado colegiadamente.'),
        p('1. Datos generales', styles['Heading2']), p('Nombre del alumno/a: ' + str(alumno.get('Nombre_Completo', ''))),
        p('CURP: ' + str(alumno.get('CURP', '')) + ' · Grado: ' + str(alumno.get('Grado', '')) + ' · Grupo: ' + str(alumno.get('Grupo', '')))]
    for f in GENERALES: story.append(p(f + ': ' + values['Aprendizaje'].get('generales', {}).get(f, '')))
    story.append(table(['Área', 'Instrumentos aplicados', 'Especialista que aplicó'], [
        {'Área': a, 'Instrumentos aplicados': values[a].get('instrumentos', '') + ('\nFecha: ' + values[a].get('fecha_aplicacion', '') if values[a].get('fecha_aplicacion') else '') +
            '\n' + '\n'.join(e.get('nombre', '') + (' · ' + e['fecha'] if e.get('fecha') else '') for e in values[a].get('evaluaciones', [])),
            'Especialista que aplicó': doc['partes'].get(a, {}).get('autor', '')} for a in AREAS]))
    for section, areas in SECCIONES.items():
        from services.epp_colaborativa import omitido
        if all(omitido(values[area],f) for area,fields in areas.items() for f in fields):continue
        story.extend([Spacer(1, 8), p(section, styles['Heading2'])])
        for area, fields in areas.items():
            for f in fields:
                if omitido(values[area],f):continue
                story.append(p(f, styles['Heading3'])); story.append(p(values[area].get('campos', {}).get(f, '')))
                if f == '6.1. Historia escolar': story.append(table(HISTORIA, values['Aprendizaje'].get('historia', [])))
                if f == '6.2. Contexto familiar': story.append(table(FAMILIA, values['Trabajo Social'].get('familia', [])))
    conclusion = values['Conclusión']
    story.append(p('7. Conclusión, determinación de las NEE e identificación de las BAP', styles['Heading2']))
    if not omitido(conclusion,'7.1. Conclusión'):
        story.extend([p('7.1. Conclusión', styles['Heading3']),p(conclusion.get('campos',{}).get('7.1. Conclusión',''))])
    for f in ['Énfasis de atención acordado', 'Asociación educativa sustentada', 'Acuerdos y apoyos del equipo']:
        if not omitido(conclusion,f) and conclusion.get('campos', {}).get(f): story.append(p(f + ': ' + conclusion['campos'][f]))
    story.extend([p('7.2. Determinación de las necesidades educativas específicas', styles['Heading3']),
        table(['Aspectos', 'Características relevantes', 'NEE'], conclusion.get('nee', [])),
        p('7.3. Identificación de BAP', styles['Heading3']), table(['Contextos', 'Tipo de barrera'], conclusion.get('bap', [])),
        p('Apoyos y acciones acordadas · Guía del Anexo XVIII', styles['Heading2']),
        table(['Aspectos', 'NEE', 'Apoyos', 'Ajustes razonables', 'Responsables', 'Fecha o período'], conclusion.get('nee', [])),
        table(BAP, conclusion.get('bap', [])),
        p('Personas implicadas en la realización de la EPP', styles['Heading2'])])

    filas_esp = []
    for a in AREAS:
        autor = doc['partes'].get(a, {}).get('autor', '')
        es_val = values[a].get('validada', False)
        obs = 'Área revisada y validada' if es_val else 'Pendiente de revisión'
        firma_esp = _firma_especialista(autor) if incluir_firmas else None
        celda_firma = []
        if firma_esp:
            try: celda_firma.append(RLImage(firma_esp, width=65, height=26))
            except Exception: pass
        else:
            celda_firma.append(Spacer(1, 12))
        celda_firma.append(Paragraph("___________________________", center))
        if autor:
            celda_firma.append(Paragraph(escape(autor), center))
        filas_esp.append({
            'Nombre': autor or 'Por asignar',
            'Función': a,
            'Observaciones': obs,
            'Firmas': celda_firma
        })
    story.append(table(['Nombre', 'Función', 'Observaciones', 'Firmas'], filas_esp, signature=True))

    story.append(Spacer(1, 14))
    firma_dir_path, sello_path = _recursos_firmas()
    escuela_nombre = str(alumno.get('Nombre_Escuela', 'Escuela Regular'))
    celda_escuela = [
        Paragraph("<b>Director(a) de la Escuela Regular</b>", center_bold),
        Paragraph(escape(escuela_nombre), center),
        Spacer(1, 26),
        Paragraph("____________________________________________", center),
        Paragraph("Nombre, firma y sello de Dirección Escolar", center)
    ]

    aplicar_firma_dir = incluir_firmas and epp_oficial_concluida

    sub_firma = []
    if aplicar_firma_dir and firma_dir_path:
        sub_firma.append(RLImage(firma_dir_path, width=82, height=36))
    else:
        sub_firma.append(Spacer(1, 26))
    sub_firma.extend([
        Paragraph("____________________________________________", center),
        Paragraph("<b>Psic. Edgar Adrián Yam Briceño MD</b>", center_bold),
        Paragraph("Director de la USAER 02-E", center)
    ])

    sub_sello = []
    if aplicar_firma_dir and sello_path:
        sub_sello.append(RLImage(sello_path, width=46, height=54))
    else:
        sub_sello.append(Spacer(1, 28))

    tabla_dir_apoyo = Table([[sub_firma, sub_sello]], colWidths=[175, 75])
    tabla_dir_apoyo.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))

    celda_apoyo = [
        Paragraph("<b>Director del Servicio de Apoyo</b>", center_bold),
        Paragraph("USAER 02-E · Zona 001 · Educación Especial", center),
        Spacer(1, 4),
        tabla_dir_apoyo
    ]

    tabla_directores = Table([[celda_escuela, celda_apoyo]], colWidths=[270, 270])
    tabla_directores.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E7ECEB')),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(KeepTogether([tabla_directores]))

    def page(c, d):
        width, height = letter
        base = Path(__file__).resolve().parents[1]
        for name, y in [('encabezado.png', height - 56), ('pie_pagina.png', 12)]:
            image = base / name
            if image.exists(): c.drawImage(str(image), 36, y, width=540, height=35, preserveAspectRatio=True, mask='auto')
        c.setFont('Helvetica', 7); c.drawRightString(576, 54, 'Página ' + str(d.page))
    SimpleDocTemplate(out, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=74, bottomMargin=70).build(story, onFirstPage=page, onLaterPages=page)
    return out.getvalue()


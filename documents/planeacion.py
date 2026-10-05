"""Exportación legible: conserva todos los apartados, sin recortar contenido."""
from io import BytesIO
from html import escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from services.planeacion_modelo import FORMATOS


def generar_pdf(doc):
    output=BytesIO(); width,height=landscape(letter); available=width-60
    styles=getSampleStyleSheet()
    small=ParagraphStyle('Celda',parent=styles['Normal'],fontSize=8,leading=10)
    title=ParagraphStyle('TituloPlaneacion',parent=styles['Title'],fontSize=17,leading=20)
    def p(value,style=small):
        return Paragraph(escape(str(value or '')).replace('\n','<br/>') or ' ',style)
    story=[p('USAER 02-E · '+FORMATOS[doc['formato']]['titulo'],title),
           p('Anexo '+doc['formato']+' · '+doc['estado']+' · Revisión '+doc.get('revision','sin guardar')[:12])]
    datos=[]
    for k,v in doc['datos'].items():
        if k=='Alumnos':
            story.append(p('Alumnos seleccionados',styles['Heading2']))
            for alumno in v:
                story.append(p(' · '.join(f'{key}: {value}' for key,value in alumno.items() if value is not None and value!='')))
        elif v is not None and v!='':
            datos.append(p(f'{k.replace("_"," ")}: {v}'))
    if len(datos)%2:datos.append(p(''))
    metadata=Table([datos[i:i+2] for i in range(0,len(datos),2)],colWidths=[available/2]*2)
    metadata.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),0)]))
    story.insert(2,metadata)
    meta=doc['metadatos']
    for key in ('fuente_iepp','necesidades_confirmadas','referente_curricular'):
        if meta.get(key):
            story.append(p(key.replace('_',' ').capitalize()+': '+str(meta[key])))
    for key,headers in FORMATOS[doc['formato']]['tablas'].items():
        story.extend([Spacer(1,10),p(key.replace('_',' ').capitalize(),styles['Heading2'])])
        rows=doc['tablas'][key] or [{}]
        data=[[p(h) for h in headers]]+[[p(row.get(h,'')) for h in headers] for row in rows]
        table=Table(data,colWidths=[available/len(headers)]*len(headers),repeatRows=1,splitInRow=1)
        table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dceeee')),
             ('GRID',(0,0),(-1,-1),.4,colors.grey),('VALIGN',(0,0),(-1,-1),'TOP'),
             ('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4)]))
        story.append(table)
    for k,v in doc['textos'].items():
        story.extend([p(k,styles['Heading2']),p(v)])
    if doc.get('observaciones_director'):
        story.extend([p('Observaciones de Dirección',styles['Heading2']),p(doc['observaciones_director'])])
    firmas=[]
    for firmante in FORMATOS[doc['formato']]['firmantes']:
        nombre=doc['datos']['Nombre del especialista'] if firmante in {'Especialista','Trabajador Social'} else ''
        if firmante.startswith('Vo.'):
            nombre=meta.get('firma_aprobada_por','')
        firmas.append([p(firmante),Spacer(1,30),p('_______________________________'),p(nombre)])
    bloque=Table([firmas],colWidths=[available/len(firmas)]*len(firmas))
    bloque.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP')]))
    story.extend([Spacer(1,14),KeepTogether([bloque])])
    def footer(canvas,_):
        canvas.setFont('Helvetica',8)
        canvas.drawString(30,18,'USAER 02-E · Documento educativo · '+doc['estado'])
        canvas.drawRightString(width-30,18,f'Página {canvas.getPageNumber()}')
    SimpleDocTemplate(output,pagesize=(width,height),leftMargin=30,rightMargin=30,topMargin=26,bottomMargin=32).build(story,onFirstPage=footer,onLaterPages=footer)
    return output.getvalue()

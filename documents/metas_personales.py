"""Las tres columnas del formato proporcionado, sin firmas automáticas."""
from io import BytesIO
from html import escape
from pathlib import Path
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter


def generar_pdf(doc):
    buffer=BytesIO();styles=getSampleStyleSheet();style=styles['BodyText'];style.fontSize=10;style.leading=14
    def p(s):return Paragraph(escape(str(s or '')).replace('\n','<br/>'),style)
    story=[Paragraph('METAS PERSONALES',styles['Title']),p('Nombre del docente: '+doc.get('Docente','')),
           p('Escuela: '+doc.get('Escuela','')),p('Fecha: '+doc.get('Fecha_Sesion','')),Spacer(1,14)]
    filas=doc.get('Filas',[])
    data=[[p('Alumno'),p('Metas'),p('Recursos necesarios')]]+[[p(r.get(k,'')) for k in ('Alumno','Metas','Recursos necesarios')] for r in filas]
    if not filas:data += [[p(''),p(''),p('')] for _ in range(8)]
    t=Table(data,colWidths=[135,215,140],repeatRows=1,minRowHeights=[42]*len(data),splitInRow=1)
    t.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.5,'#444444'),('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,0),'#eeeeee'),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8)]))
    story.append(t)
    SimpleDocTemplate(buffer,pagesize=letter,leftMargin=61,rightMargin=61,topMargin=50,bottomMargin=50,title='Metas personales',author=doc.get('Docente','')).build(story)
    return buffer.getvalue()

"""Cuadro personal o integrado, con procedencia y siglas sin reinterpretación."""
from html import escape
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
from services.juntas_metodologias_catalogo import POR_ID


def generar_pdf(docs,fecha):
    buffer=BytesIO();styles=getSampleStyleSheet();style=styles['BodyText'];style.fontSize=10;style.leading=14
    def p(value):return Paragraph(escape(str(value or '')).replace('\n','<br/>'),style)
    story=[]
    for doc in docs:
        if story:story.append(PageBreak())
        story += [Paragraph('Metodologías y estrategias específicas',styles['Title']),p('Sesión: '+str(fecha)),
            p('Docente: '+doc['Docente']+' · '+doc['Area']),p('A, C y P se conservan como en el original, sin atribuirles significado.'),Spacer(1,12)]
        for code,row in doc['Captura']['Respuestas'].items():
            source=POR_ID[code]
            story += [Paragraph(escape(source[1]),styles['Heading2']),p(source[2]),Spacer(1,6)]
            data=[[p(t) for t in ('Metodologías, programas y estrategias específicas','A','C','P')],
                [p(source[3])]+[p('X' if row[k] else '') for k in ('A','C','P')]]
            t=Table(data,colWidths=[400,30,30,30],repeatRows=1,splitInRow=1)
            t.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.5,'#D9D9D9'),('BACKGROUND',(0,0),(-1,0),'#edf2f7'),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
            story += [t,p('Aplicación prevista: '+row['Aplicación prevista']),p('Evidencia y seguimiento: '+row['Evidencia y seguimiento']),Spacer(1,12)]
    if not story:story=[p('Sin aportaciones confirmadas.')]
    SimpleDocTemplate(buffer,pagesize=letter,leftMargin=61,rightMargin=61,topMargin=42,bottomMargin=42,title='Juntas académicas USAER',author='USAER 02-E').build(story)
    return buffer.getvalue()

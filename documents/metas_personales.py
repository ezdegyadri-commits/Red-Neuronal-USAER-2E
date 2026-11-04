"""Las tres columnas del formato proporcionado, sin firmas automáticas."""
from io import BytesIO
from html import escape
from pathlib import Path
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter


def generar_pdf(doc):
    if 'Periodo' in doc or any(r.get('Instrumento') for r in doc.get('Filas',[])):
        return generar_consolidado([doc])
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


def generar_consolidado(docs):
    """Un PDF con procedencia por aporte; no promedia ni mezcla autores."""
    from services import metas_instrumento as r
    buffer=BytesIO();styles=getSampleStyleSheet();style=styles['BodyText'];style.fontSize=10;style.leading=14
    def p(text):return Paragraph(escape(str(text if text is not None else '')).replace('\n','<br/>'),style)
    def tabla(data,widths,repeat=1):
        t=Table([[p(c) for c in row] for row in data],colWidths=widths,repeatRows=repeat,splitInRow=1)
        t.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.5,'#D9D9D9'),('BACKGROUND',(0,0),(-1,0),'#edf2f7'),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
        return t
    story=[]
    for doc in docs:
        for row in doc.get('Filas',[]):
            if story:story.append(PageBreak())
            story += [Paragraph('Instrumento para valorar la planificación de USAER',styles['Title']),
                p('Docente: '+doc.get('Docente','')+' · Función: '+doc.get('Area','No registrada en captura anterior')),
                p('Escuela: '+doc.get('Escuela','')+' · Sesión: '+doc.get('Fecha_Sesion','')),
                p('Período que abarca la planificación: '+(doc.get('Periodo') or 'Por registrar')),
                p('Alumno: '+row.get('Alumno','')),Spacer(1,10),
                tabla([['Metas','Recursos necesarios'],[row.get('Metas',''),row.get('Recursos necesarios','')]],[275,215]),Spacer(1,12)]
            value=row.get('Instrumento')
            if not value:
                story.append(p('Captura anterior conservada. No se registraron valoraciones de la rúbrica.'));continue
            value=r.validar(value);tot=r.resumen(value)
            story.append(p('Autoevaluación de la planeación por el docente. Pendiente no equivale a cero.'))
            data=[['','Docente: '+doc.get('Docente','')+' · Alumno: '+row.get('Alumno',''),'','','',''],['No.','Indicador','0','1','2','3']]
            for i,text in enumerate(r.INDICADORES,1):
                score=value['Indicadores'][str(i)]
                data.append([i,text+(' (Pendiente)' if score is None else '')]+['X' if score==n else '' for n in range(4)])
            data.append(['','Cantidad por valoración']+[tot['Conteos'][n] for n in range(4)])
            story += [tabla(data,[35,335,30,30,30,30],repeat=2),Spacer(1,8),
                p('Escala: 0 · No lo realiza; 1 · Insuficiente; 2 · Suficiente; 3 · Satisfactorio.'),
                p('Respondidos: '+str(tot['Respondidos'])+'/14. '+('GRAN TOTAL: '+str(tot['Total'])+'/42.' if tot['Total'] is not None else 'Subtotal provisional: '+str(tot['Subtotal'])+'. Faltan '+str(tot['Pendientes'])+' indicadores.')),
                Spacer(1,10),Paragraph('Análisis de la coherencia interna de la planeación',styles['Heading2']),p(r.COHERENCIA)]
            coherence=value['Coherencia']
            story.append(p('Coherencia: Pendiente.' if coherence is None else str(coherence)+' · '+r.ESCALA[coherence]+'. '+r.DESCRIPTORES[coherence]))
            story += [p('La coherencia se valora por separado; no se añade al total de los catorce indicadores.'),Spacer(1,8),p('Observaciones: '+(value['Observaciones'] or 'Sin observaciones registradas.'))]
    if not story:story=[p('No hay aportaciones confirmadas para integrar.')]
    SimpleDocTemplate(buffer,pagesize=letter,leftMargin=61,rightMargin=61,topMargin=42,bottomMargin=42,title='Instrumento integrado de planeación USAER',author='USAER 02-E').build(story)
    return buffer.getvalue()

"""La descarga utiliza las mismas celdas del editor, con el orden del ejemplo."""
from io import BytesIO
from html import escape
from reportlab.lib.pagesizes import landscape,letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate,Paragraph,Table,TableStyle,Spacer
from services.planeacion_papel import hoja


def generar_pdf(doc):
    spec=hoja(doc);output=BytesIO();ancho=landscape(letter)[0]-52
    style=ParagraphStyle('Word',fontName='Times-Roman',fontSize=10,leading=12)
    title=ParagraphStyle('TituloWord',parent=style,fontName='Times-Bold',fontSize=12,leading=15,alignment=1,keepWithNext=True)
    def p(v,sty=style):return Paragraph(escape(str(v or '')).replace('\n','<br/>') or ' ',sty)
    def tabla(rows,widths=None):
        t=Table(rows,colWidths=widths,repeatRows=1,splitInRow=1)
        t.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.6,'black'),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]));return t
    story=[p(spec['titulo'],title),Spacer(1,12)]
    for row in spec['header']:story.append(tabla([[p(v) for v in row]],[ancho/len(row)]*len(row)))
    story.append(Spacer(1,12))
    for section in spec['tables']:
        if section['title']:story.extend([p(section['title'],title),Spacer(1,5)])
        rows=[[p(v) for v in section['headers']]]
        rows.extend([[p((c['referente']+'\n\nAdaptación docente / objetivo de trabajo:\n' if c['referente'] else '')+c['value']+('\n\n'+c['nota'] if c.get('nota') else '')) for c in row] for row in section['rows']])
        widths=[ancho*n/sum(section['widths']) for n in section['widths']] if section['widths'] else [ancho/len(section['headers'])]*len(section['headers'])
        story.extend([tabla(rows,widths),Spacer(1,12)])
    for c in spec['textos']:story.extend([tabla([[p(c['label'])],[p(c['value'])]],[ancho]),Spacer(1,12)])
    story.extend([Spacer(1,24),tabla([[p('____________________________\n'+spec['firma']),p('____________________________\n'+spec['vobo'])]],[ancho/2]*2)])
    # Los fundamentos se conservan, sin copiar otra vez todo el formato.
    from services.planeacion_generacion import fuentes_pertinentes
    fuentes=fuentes_pertinentes(doc)
    if fuentes:
        story.extend([Spacer(1,15),p('Antecedentes documentales vinculados',title)])
        for f in fuentes:story.append(p(f.get('referencia','')+' · '+f.get('tipo','')+' · '+str(f.get('fecha',''))))
    cur=doc['metadatos'].get('referente_curricular','')
    if cur:story.extend([Spacer(1,10),p('Referentes y contextualización',title),p(cur)])
    apoyos=doc['metadatos'].get('configuracion_generacion',{}).get('apoyos','')
    if apoyos:story.extend([Spacer(1,10),p('Apoyos y ajustes DUA acordados por el docente',title),p(apoyos)])
    from services.planeacion_equipo import tablas_salida
    for titulo,headers,rows in tablas_salida(doc):
        if not rows:continue
        if titulo=='Competencias emocionales' and any(t['id']=='competencias' for t in spec['tables']):continue
        if titulo=='Planeación grupal ajustada de zona' and not any(any(str(r.get(k,'')).strip() for k in ('Fecha derivación','Actividades','Situación inicial','Situación final')) for r in rows):continue
        story.extend([Spacer(1,10),p(titulo,title),tabla([[p(h) for h in headers]]+[[p(r.get(h,'')) for h in headers] for r in rows],[ancho/len(headers)]*len(headers))])
    if spec['grupal']:
        from services.planeacion_modelo import FORMATOS
        for nombre,headers in FORMATOS[doc['formato']]['tablas'].items():
            rows=doc['tablas'][nombre]
            if any(any(str(r.get(h,'') or '').strip() for h in headers if h!='Contextos') for r in rows):
                story.extend([Spacer(1,10),p('Detalle conectado · '+nombre,title),tabla([[p(h) for h in headers]]+[[p(r.get(h,'')) for h in headers] for r in rows],[ancho/len(headers)]*len(headers))])
        for campo,value in doc['textos'].items():
            if value:story.extend([Spacer(1,10),p(campo,title),p(value)])
    SimpleDocTemplate(output,pagesize=landscape(letter),leftMargin=26,rightMargin=26,topMargin=26,bottomMargin=26).build(story)
    return output.getvalue()

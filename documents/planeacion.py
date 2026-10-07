"""Exportación legible: conserva todos los apartados, sin recortar contenido."""
from io import BytesIO
from html import escape
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from services.planeacion_modelo import FORMATOS
from services.curriculo import contexto_ia


def generar_pdf(doc):
    from services.planeacion_equipo import aplica
    es_equipo=aplica(doc) and 'equipo' in doc['metadatos']
    output=BytesIO(); width,height=landscape(letter); available=width-60
    styles=getSampleStyleSheet()
    styles['Heading2'].keepWithNext=True
    styles['Heading2'].fontSize=11
    styles['Heading2'].leading=14
    if es_equipo:
        styles['Heading2'].spaceBefore=7
        styles['Heading2'].spaceAfter=4
    small=ParagraphStyle('Celda',parent=styles['Normal'],fontSize=8,leading=10)
    title=ParagraphStyle('TituloPlaneacion',parent=styles['Title'],fontSize=14,leading=17)
    def p(value,style=small):
        return Paragraph(escape(str(value or '')).replace('\n','<br/>') or ' ',style)
    story=[p('USAER 02-E · '+FORMATOS[doc['formato']]['titulo'],title),
           p('Anexo '+doc['formato']+' · '+doc['estado']+' · Revisión '+doc.get('revision','sin guardar')[:12])]
    datos=[]
    for k,v in doc['datos'].items():
        if k=='Alumnos':
            story.append(p('Nombre del alumno/a, grado, grupo y condición',styles['Heading2']))
            rows=[[p(h) for h in ('Nombre del alumno/a','Grado','Grupo','Condición')]]
            rows.extend([[p(a.get(k,'')) for k in ('Nombre del alumno','Grado','Grupo','Condición')] for a in v])
            alumnos_table=Table(rows,colWidths=[available*.46,available*.10,available*.10,available*.34],repeatRows=1,splitInRow=1)
            alumnos_table.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.4,colors.grey),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dceeee')),('VALIGN',(0,0),(-1,-1),'TOP')]))
            story.append(alumnos_table)
        elif k!='ID_Escuela':
            datos.append(p(f'{k.replace("_"," ")}: {"" if v is None else v}'))
    if len(datos)%2:datos.append(p(''))
    metadata=Table([datos[i:i+2] for i in range(0,len(datos),2)],colWidths=[available/2]*2)
    metadata.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),0)]))
    story.insert(2,metadata)
    from services.planeacion_modalidad import guia_grupal, GUIA_XIX, GUIA_XX
    guia=guia_grupal(doc)
    if guia:
        story.extend([p('Anexo XIX. Guía de Planeación Grupal',styles['Heading2']),p('Maestro de grupo: '+guia['maestro_grupo'])])
        for headers,rows in [(GUIA_XIX,guia['filas']),(GUIA_XX,guia['as'])]:
            if not rows:continue
            if headers==GUIA_XX:story.append(p('Anexo XX. Guía de Planeación Grupal AS',styles['Heading2']))
            t=Table([[p(h) for h in headers]]+[[p(r.get(h,'')) for h in headers] for r in rows],colWidths=[available/len(headers)]*len(headers),repeatRows=1,splitInRow=1)
            t.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.3,colors.grey),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dceeee')),('VALIGN',(0,0),(-1,-1),'TOP')]))
            story.append(t)
    meta=doc['metadatos']
    for key in ('fuente_iepp','necesidades_confirmadas','referente_curricular'):
        if meta.get(key):
            story.append(p(key.replace('_',' ').capitalize()+': '+str(meta[key])))
    curricular=meta.get('curriculo',{})
    if curricular:
        story.extend([p('Vinculación curricular',styles['Heading2']),p('Campo formativo: '+curricular.get('campo','')),p('Ejes articuladores: '+', '.join(curricular.get('ejes',[])))])
        for r in curricular.get('registros',[]):
            story.append(p(f"Fase {r['fase']} · Grado {r['grado']} · {r['fuente']} · Página PDF {r['pagina_pdf']}"))
            story.extend([p('Contenido: '+r['contenido']),p('PDA (extracto oficial por grado): '+r['pda'])])
            ajuste=curricular.get('adaptaciones',{}).get(r['id'],{})
            if ajuste:
                story.extend([p('Adaptación docente del contenido: '+ajuste.get('contenido','')),p('PDA adaptado / objetivo de trabajo (redacción docente): '+ajuste.get('pda',''))])
        if curricular.get('contexto_local'):story.append(p('Contextualización escolar y comunitaria: '+curricular['contexto_local']))
    for key,headers in FORMATOS[doc['formato']]['tablas'].items():
        story.extend([Spacer(1,10),p(key.replace('_',' ').capitalize(),styles['Heading2'])])
        rows=doc['tablas'][key] or [{}]
        data=[[p(h) for h in headers]]+[[p(row.get(h,'')) for h in headers] for row in rows]
        anchos=[available/len(headers)]*len(headers)
        if key=='dosificacion':anchos=[available*n for n in (.15,.51,.14,.20)]
        table=Table(data,colWidths=anchos,repeatRows=1,splitInRow=1)
        table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dceeee')),
             ('GRID',(0,0),(-1,-1),.4,colors.grey),('VALIGN',(0,0),(-1,-1),'TOP'),
             ('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4)]))
        story.append(table)
    for k,v in doc['textos'].items():
        story.append(KeepTogether([p(k,styles['Heading2']),p(v)]))
    from services.planeacion_equipo import tablas_salida, contexto_zona
    for titulo,headers,rows in tablas_salida(doc):
        story.extend([Spacer(1,10),p(titulo,styles['Heading2'])])
        data=[[p(h) for h in headers]]+[[p(r.get(h,'')) for h in headers] for r in rows or [{}]]
        if len(headers)==7:
            proporciones=[.16,.12,.09,.09,.24,.15,.15]
        elif len(headers)==3:proporciones=[.16,.59,.25]
        else:proporciones=[.20,.23,.27,.30]
        table=Table(data,colWidths=[available*n for n in proporciones],repeatRows=1,splitInRow=1)
        table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dceeee')),
            ('GRID',(0,0),(-1,-1),.4,colors.grey),('VALIGN',(0,0),(-1,-1),'TOP'),
            ('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5)]))
        story.append(table)
    equipo=meta.get('equipo',{})
    if equipo.get('sugerencia_familia'):
        story.extend([p('Sugerencia prevista para la familia',styles['Heading2']),p(equipo['sugerencia_familia'])])
    zona=contexto_zona(doc)
    if zona:
        story.extend([Spacer(1,10),p('Referentes de zona',styles['Heading2'])])
        for fuente in zona['fuentes']:
            story.append(p(fuente['titulo']+' · '+fuente['edicion']))
    if doc.get('observaciones_director'):
        story.extend([p('Observaciones de Dirección',styles['Heading2']),p(doc['observaciones_director'])])
    firmas=[]
    for firmante in FORMATOS[doc['formato']]['firmantes']:
        nombre=doc['datos']['Nombre del especialista'] if firmante in {'Especialista','Trabajador Social'} else ''
        if firmante.startswith('Vo.'):
            nombre=meta.get('firma_aprobada_por','')
        firmas.append([p(firmante),Spacer(1,18 if es_equipo else 30),p('_______________________________'),p(nombre)])
    bloque=Table([firmas],colWidths=[available/len(firmas)]*len(firmas))
    bloque.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP')]))
    story.extend([Spacer(1,8 if es_equipo else 14),KeepTogether([bloque])])
    if curricular:
        story.append(p('Fuentes oficiales de fundamentación',styles['Heading2']))
        for source in contexto_ia(doc)['fuentes']:
            story.append(p(source['titulo']+' · '+source['organismo']+' · '+source['edicion']+(' · '+source['url'] if source.get('url') else '')))
        story.append(p('Los extractos de SEP se reproducen con reconocimiento de autoría para uso educativo no comercial. Las propuestas pedagógicas son adaptaciones revisables, no texto oficial ni resultados alcanzados.'))
    def footer(canvas,_):
        root=Path(__file__).resolve().parents[1]
        header=root/'encabezado.png';footer_image=root/'pie_pagina.png'
        if header.exists():canvas.drawImage(str(header),(width-620)/2,height-94,width=620,height=74,preserveAspectRatio=True,anchor='c',mask='auto')
        if footer_image.exists():canvas.drawImage(str(footer_image),(width-490)/2,12,width=490,height=72,preserveAspectRatio=True,anchor='c',mask='auto')
        canvas.setFont('Helvetica',8)
        canvas.drawString(30,86,'USAER 02-E · Documento educativo · '+doc['estado'])
        canvas.drawRightString(width-30,86,f'Página {canvas.getPageNumber()}')
    SimpleDocTemplate(output,pagesize=(width,height),leftMargin=30,rightMargin=30,topMargin=110,bottomMargin=100).build(story,onFirstPage=footer,onLaterPages=footer)
    return output.getvalue()

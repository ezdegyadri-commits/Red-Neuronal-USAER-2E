"""La descarga utiliza las mismas celdas del editor, con el orden del ejemplo."""
from io import BytesIO
from html import escape
from reportlab.lib.pagesizes import landscape,letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate,Paragraph,Table,TableStyle,Spacer
from services.planeacion_papel import hoja


def generar_pdf(doc,archivo=False):
    return _generar_pdf(doc,hoja(doc,para_impresion=True,archivo=archivo))


def preparar_descarga(doc):
    # Streamlit ejecuta la descarga diferida fuera del hilo de la pantalla.
    # Autorizar ahora y capturar una instantánea evita leer session_state allí.
    from copy import deepcopy
    import streamlit as st
    copia=deepcopy(doc)
    cache=getattr(st,'session_state',{}).setdefault('_pdf_spec_cache',{}) if hasattr(st,'session_state') else {}
    cache_key=('visibilidad-2026-10-20',doc.get('id',''),doc.get('revision',''))
    spec=cache.get(cache_key)
    if spec is None:
        spec=hoja(copia,para_impresion=True)
        cache[cache_key]=spec
    return lambda:_generar_pdf(copia,spec)


def _generar_pdf(doc,spec):
    output=BytesIO();ancho=landscape(letter)[0]-52
    style=ParagraphStyle('Word',fontName='Times-Roman',fontSize=9.5,leading=11.5)
    title=ParagraphStyle('TituloWord',parent=style,fontName='Times-Bold',fontSize=12,leading=15,alignment=1,keepWithNext=True)
    def p(v,sty=style):return Paragraph(escape(str(v or '')).replace('\n','<br/>') or ' ',sty)
    def tabla(rows,widths=None,padding=5):
        t=Table(rows,colWidths=widths,repeatRows=1,splitInRow=1)
        t.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.6,'black'),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),padding),('BOTTOMPADDING',(0,0),(-1,-1),padding)]));return t

    from pathlib import Path
    img_path = Path(__file__).resolve().parents[1] / 'encabezado.png'

    if doc['datos'].get('Función') == 'Psicología':
        from reportlab.platypus import PageBreak, Image
        story = []
        if img_path.exists():
            story.extend([Image(str(img_path), width=ancho, height=36), Spacer(1, 6)])
        story.extend([p(spec['titulo'], title), Spacer(1, 8)])
        for row in spec['header']:
            if len(row) == 5:
                w = [ancho * 0.36, ancho * 0.16, ancho * 0.16, ancho * 0.16, ancho * 0.16]
            else:
                w = [ancho / len(row)] * len(row)
            story.append(tabla([[p(v['label']+': '+v['value'] if isinstance(v,dict) else v) for v in row]], w, padding=4))
        story.append(Spacer(1, 8))
        legadas = [c['Actividad prevista'] for c in doc.get('metadatos',{}).get('equipo',{}).get('competencias',[]) if c.get('Actividad prevista')]
        for section in spec['tables']:
            if not section['rows']: continue
            if section['title']: story.extend([p(section['title'], title), Spacer(1, 4)])
            rows = [[p(v) for v in section['headers']]]
            for r_idx, row in enumerate(section['rows']):
                row_cells = []
                for c_idx, c in enumerate(row):
                    val = str(c.get('value', '') or '')
                    if section['id'] == 'dosificacion' and c_idx == 1 and r_idx == 0 and legadas and not any(leg in val for leg in legadas):
                        val = (val + '\n' + '\n'.join(legadas)).strip()
                    row_cells.append(p(val))
                rows.append(row_cells)
            widths = [ancho * n / sum(section['widths']) for n in section['widths']] if section['widths'] else [ancho / len(section['headers'])] * len(section['headers'])
            story.extend([tabla(rows, widths, padding=4), Spacer(1, 8)])

        story.append(PageBreak())
        if img_path.exists():
            story.extend([Image(str(img_path), width=ancho, height=36), Spacer(1, 10)])
        obs_val = doc['textos'].get('Observaciones', '')
        obs_p = p(obs_val) if obs_val else p(' ')
        obs_table = Table([[p('Observaciones', ParagraphStyle('ObsTitle', parent=style, fontName='Times-Bold', fontSize=10))], [obs_p]], colWidths=[ancho], rowHeights=[20, 220])
        obs_table.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), .6, 'black'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ]))
        story.extend([obs_table, Spacer(1, 45)])
        sig_table = Table([[
            p('_________________________________________\n' + spec['firma'], ParagraphStyle('Sig1', parent=style, alignment=1)),
            p('_________________________________________\n' + spec['vobo'], ParagraphStyle('Sig2', parent=style, alignment=1))
        ]], colWidths=[ancho/2, ancho/2])
        sig_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ]))
        story.append(sig_table)
        SimpleDocTemplate(output,pagesize=landscape(letter),leftMargin=26,rightMargin=26,topMargin=20,bottomMargin=20).build(story)
        return output.getvalue()

    story=[p(spec['titulo'],title),Spacer(1,12)]
    for row in spec['header']:story.append(tabla([[p(v['label']+': '+v['value'] if isinstance(v,dict) else v) for v in row]],[ancho/len(row)]*len(row)))
    story.append(Spacer(1,12))
    for section in spec['tables']:
        if not section['rows']:continue
        if section['title']:story.extend([p(section['title'],title),Spacer(1,5)])
        rows=[[p(v) for v in section['headers']]]
        rows.extend([[p(c['value']) for c in row] for row in section['rows']])
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
    if not cur:
        from services.planeacion_generacion import texto_curricular
        cur=texto_curricular(doc)
    if cur:story.extend([Spacer(1,10),p('Referentes y contextualización',title),p(cur)])
    if any(r.get('_nee_origen',{}).get('propuesta') for r in doc['tablas'].get('aprendizajes',[])):
        story.extend([Spacer(1,8),p('NEE propuesta para valoración docente. Revisar su pertinencia antes de validarla.')])
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
            if any(t['id']==nombre for t in spec['tables']):continue
            rows=doc['tablas'][nombre]
            if any(any(str(r.get(h,'') or '').strip() for h in headers if h!='Contextos') for r in rows):
                story.extend([Spacer(1,10),p('Detalle conectado · '+nombre,title),tabla([[p(h) for h in headers]]+[[p(r.get(h,'')) for h in headers] for r in rows],[ancho/len(headers)]*len(headers))])
        for campo,value in doc['textos'].items():
            if any(c['label']==campo for c in spec['textos']):continue
            if value:story.extend([Spacer(1,10),p(campo,title),p(value)])
    SimpleDocTemplate(output,pagesize=landscape(letter),leftMargin=26,rightMargin=26,topMargin=26,bottomMargin=26).build(story)
    return output.getvalue()

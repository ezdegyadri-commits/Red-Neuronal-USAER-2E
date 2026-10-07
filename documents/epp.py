"""Informe único del Anexo XVII, con tablas ampliadas según Anexo XVIII."""
from io import BytesIO
from pathlib import Path
from html import escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from services.epp_modelo import SECCIONES, AREAS, NEE, BAP, FAMILIA, HISTORIA, GENERALES, conclusion_vigente
from services.epp_entrada import precargar

def generar_pdf(doc, alumno):
    out=BytesIO(); styles=getSampleStyleSheet()
    small=ParagraphStyle('EPPCelda',parent=styles['Normal'],fontSize=8,leading=10)
    def p(t,style=small):return Paragraph(escape(str(t or '')).replace('\n','<br/>') or ' ',style)
    def table(headers,rows,signature=False):
        data=[[p(h) for h in headers]]+[[p(r.get(h,'')) for h in headers] for r in rows or [{}]]
        t=Table(data,colWidths=[540/len(headers)]*len(headers),repeatRows=1,splitInRow=1,
            rowHeights=[None]+[54]*len(data[1:]) if signature else None)
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#E7ECEB')),
            ('GRID',(0,0),(-1,-1),.3,colors.grey),('VALIGN',(0,0),(-1,-1),'TOP')]))
        return t
    values={a:doc['partes'].get(a,{}).get('contenido',{}) for a in (*AREAS,'Conclusión')}
    values['Aprendizaje']=precargar(values['Aprendizaje'],alumno)
    fecha=max((v['fecha'] for v in doc['partes'].values()),default='')[:10]
    story=[p('Informe de Evaluación Psicopedagógica',styles['Title']),p('Servicio de Apoyo de Educación Especial · Anexo XVII'),
        p('Nombre de la escuela: '+str(alumno.get('Nombre_Escuela',''))),
        p('Nivel educativo: '+str(alumno.get('Nivel_Educativo',''))+' · Zona escolar: 001'),
        p('Servicio de Apoyo: USAER 02-E · Fecha de elaboración: '+fecha+' · Ciclo: '+doc['ciclo']),
        p('Borrador interdisciplinario; pendiente de validación.' if not conclusion_vigente(doc) else 'Conclusión revisada por el equipo.'),
        p('1. Datos generales',styles['Heading2']),p('Nombre del alumno/a: '+str(alumno.get('Nombre_Completo',''))),
        p('CURP: '+str(alumno.get('CURP',''))+' · Grado: '+str(alumno.get('Grado',''))+' · Grupo: '+str(alumno.get('Grupo','')))]
    for f in GENERALES:story.append(p(f+': '+values['Aprendizaje'].get('generales',{}).get(f,'')))
    story.append(table(['Área','Instrumentos aplicados','Especialista que aplicó'],[
        {'Área':a,'Instrumentos aplicados':values[a].get('instrumentos','')+('\nFecha: '+values[a].get('fecha_aplicacion','') if values[a].get('fecha_aplicacion') else '')+
            '\n'+'\n'.join(e.get('nombre','')+(' · '+e['fecha'] if e.get('fecha') else '') for e in values[a].get('evaluaciones',[])),
            'Especialista que aplicó':doc['partes'].get(a,{}).get('autor','')} for a in AREAS]))
    for section,areas in SECCIONES.items():
        story.extend([Spacer(1,8),p(section,styles['Heading2'])])
        for area,fields in areas.items():
            for f in fields:
                story.append(p(f,styles['Heading3']));story.append(p(values[area].get('campos',{}).get(f,'')))
                if f=='6.1. Historia escolar':story.append(table(HISTORIA,values['Aprendizaje'].get('historia',[])))
                if f=='6.2. Contexto familiar':story.append(table(FAMILIA,values['Trabajo Social'].get('familia',[])))
    conclusion=values['Conclusión']
    story.extend([p('7. Conclusión, determinación de las NEE e identificación de las BAP',styles['Heading2']),
        p('7.1. Conclusión',styles['Heading3']),p(conclusion.get('campos',{}).get('7.1. Conclusión',''))])
    for f in ['Énfasis de atención acordado','Asociación educativa sustentada','Acuerdos y apoyos del equipo']:
        if conclusion.get('campos',{}).get(f):story.append(p(f+': '+conclusion['campos'][f]))
    story.extend([p('7.2. Determinación de las necesidades educativas específicas',styles['Heading3']),
        table(['Aspectos','Características relevantes','NEE'],conclusion.get('nee',[])),
        p('7.3. Identificación de BAP',styles['Heading3']),table(['Contextos','Tipo de barrera'],conclusion.get('bap',[])),
        p('Apoyos y acciones acordadas · Guía del Anexo XVIII',styles['Heading2']),
        table(['Aspectos','NEE','Apoyos','Ajustes razonables','Responsables','Fecha o período'],conclusion.get('nee',[])),
        table(BAP,conclusion.get('bap',[])),
        p('Personas implicadas en la realización de la EPP',styles['Heading2']),
        table(['Nombre','Función','Observaciones','Firmas'],[{'Nombre':doc['partes'].get(a,{}).get('autor',''),
            'Función':a,'Observaciones':'Área revisada' if values[a].get('validada') else 'Pendiente de revisión','Firmas':''} for a in AREAS],signature=True),
        Spacer(1,24),table(['Nombre, firma y sello del Director de la Escuela','Nombre, firma y sello del Director del Servicio de Apoyo'],[{}],signature=True)])
    def page(c,d):
        width,height=letter
        base=Path(__file__).resolve().parents[1]
        for name,y in [('encabezado.png',height-56),('pie_pagina.png',12)]:
            image=base/name
            if image.exists():c.drawImage(str(image),36,y,width=540,height=35,preserveAspectRatio=True,mask='auto')
        c.setFont('Helvetica',7);c.drawRightString(576,54,'Página '+str(d.page))
    SimpleDocTemplate(out,pagesize=letter,leftMargin=36,rightMargin=36,topMargin=74,bottomMargin=70).build(story,onFirstPage=page,onLaterPages=page)
    return out.getvalue()

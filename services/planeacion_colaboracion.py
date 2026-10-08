"""Aportes por área dentro del documento existente, sin ampliar permisos generales."""
from copy import deepcopy
from datetime import datetime,timezone
from uuid import uuid4

AREAS=('Aprendizaje','Psicología','Comunicación','Trabajo Social')
COLUMNAS=['ID_Alumno','Necesidad o barrera documentada','Objetivo / qué trabajar','Descriptor de logro',
          'Actividad / cómo trabajar','Apoyos y ajustes','Contexto','Responsable','Temporalidad','Referencia']


def clave_guia(doc):
    if doc['formato']=='XXI' or not compartible(doc):return None
    a=doc['datos']['Alumnos'][0]
    return (doc['datos']['ID_Escuela'],doc['datos']['Curso escolar'],str(a['Grado']),str(a['Grupo']))


def compartible(doc):
    if doc['formato']=='XXI':return True
    if doc['datos']['Función']!='Aprendizaje' or doc['metadatos'].get('modalidad_planeacion')!='grupal':return False
    grupos={(str(a.get('Grado','')),str(a.get('Grupo',''))) for a in doc['datos']['Alumnos']}
    return len(grupos)==1 and all(g and h for g,h in grupos)


def aportar(doc,actor,filas,observaciones):
    if not compartible(doc) or actor.get('director') or actor.get('area') not in AREAS:raise PermissionError('Solo las áreas participantes pueden registrar su aportación.')
    if not isinstance(filas,list) or len(filas)>100:raise ValueError('Revisa las filas de tu aportación.')
    ids={a['ID_Alumno'] for a in doc['datos']['Alumnos']};limpias=[]
    for row in filas:
        if row.get('ID_Alumno') not in ids:raise PermissionError('La aportación incluye otro alumno.')
        limpia={k:str(row.get(k,'')).strip() for k in COLUMNAS}
        from services.planeacion_modelo import FORMATOS
        if limpia['Contexto'] and limpia['Contexto'] not in FORMATOS[doc['formato']]['contextos']:raise ValueError('Elige un contexto del formato correspondiente.')
        if any(len(v)>4000 for v in limpia.values()):raise ValueError('Cada celda admite hasta 4 000 caracteres.')
        if any(limpia[k] for k in COLUMNAS[1:]):limpias.append(limpia)
    if len(str(observaciones))>6000:raise ValueError('Las observaciones admiten hasta 6 000 caracteres.')
    result=deepcopy(doc)
    previo=result['metadatos'].setdefault('aportaciones_equipo',{}).get(actor['area'],{})
    # No apropiarse silenciosamente del trabajo de otro profesional de la misma área.
    if previo and previo['cuenta']!=actor['cuenta']:raise PermissionError('Esta aportación pertenece a otro profesional del área; coordina su revisión con Dirección.')
    result['metadatos']['aportaciones_equipo'][actor['area']]={'cuenta':actor['cuenta'],'autor':actor['nombre'],
        'revision':uuid4().hex,'fecha':datetime.now(timezone.utc).isoformat(),'filas':limpias,'observaciones':str(observaciones).strip()}
    result['metadatos']['firma_aprobada_por']=''
    return result


def integrar(doc):
    """Solo propuesta de integración: no borra celdas redactadas ni valida el documento."""
    result=deepcopy(doc);meta=result['metadatos'];integradas=meta.setdefault('aportaciones_integradas',{})
    bases=meta.setdefault('guia_aportes_integrados',{});avisos=[]
    for area,aporte in meta.get('aportaciones_equipo',{}).items():
        if integradas.get(area)==aporte['revision']:continue
        if doc['formato']=='XXI':
            for row in aporte['filas']:
                ref='Aporte '+area+' · '+aporte['revision']
                if row['Objetivo / qué trabajar']:
                    result['tablas']['necesidades'].append({'NEE':row['Necesidad o barrera documentada'],
                        'Aprendizajes y/u Objetivos':row['Objetivo / qué trabajar'],'Descriptor de Logro':row['Descriptor de logro'],
                        'Apoyos o ajustes':'\n'.join(v for v in (row['Apoyos y ajustes'],row['Actividad / cómo trabajar']) if v),'Responsables':row['Responsable'] or aporte['autor'],
                        'Temporalidad':row['Temporalidad'],'Seguimiento':row['Referencia'],'_aporte':ref})
                elif row['Necesidad o barrera documentada'] and row['Actividad / cómo trabajar']:
                    result['tablas']['barreras'].append({'BAP':row['Necesidad o barrera documentada'],
                        'Acciones para minimizarla o eliminarla':row['Actividad / cómo trabajar'],
                        'Responsable':row['Responsable'] or aporte['autor'],'Temporalidad':row['Temporalidad'],
                        **{k:'X' if row['Contexto']==c else '' for k,c in [('E','Escolar'),('A','Áulico'),('SF','Sociofamiliar')]},'_aporte':ref})
        else:
            from services.planeacion_modalidad import guia_grupal
            guia=guia_grupal(result)
            conflicto=False;anteriores=bases.get(area,{})
            for r in guia['filas']:
                texto='\n'.join(row['Objetivo / qué trabajar']+' · '+row['Actividad / cómo trabajar'] for row in aporte['filas'] if row['ID_Alumno']==r['ID_Alumno'])
                actual=r.get(area,'');previo=anteriores.get(r['ID_Alumno'])
                if actual==texto:continue
                if not actual or (previo is not None and actual==previo):
                    r[area]=texto;anteriores[r['ID_Alumno']]=texto
                elif texto or previo is not None:
                    conflicto=True
            bases[area]=anteriores
            meta['guia_grupal_manual']=guia
            if conflicto:
                avisos.append(area+': se conservaron celdas editadas. Revisa la aportación y concíliala en la guía antes de integrarla de nuevo.')
                continue
        integradas[area]=aporte['revision']
    meta['avisos_integracion']=avisos
    return result

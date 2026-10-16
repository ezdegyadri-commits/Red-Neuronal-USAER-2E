"""Proyecciones aditivas del Anexo XIX; nunca migra ni reescribe el padrón."""
from copy import deepcopy
from datetime import datetime
from zoneinfo import ZoneInfo
from utils.text import normalizar_texto
from utils.escolar import grado_canonico, grupo_canonico


def es_guia(doc):
    return (doc['datos']['Función']=='Aprendizaje'
            and doc['metadatos'].get('modalidad_planeacion')=='grupal'
            and doc['metadatos'].get('vista_formato')!='trimestral')


def etiqueta(doc):
    grupos=sorted({grado_canonico(a.get('Grado'))+' '+grupo_canonico(a.get('Grupo')) for a in doc['datos']['Alumnos']})
    return ' · '.join([doc['datos']['Escuela regular'],', '.join(grupos),
        doc['datos']['Curso escolar'],'T'+str(doc['datos']['Trimestre']),
        doc.get('guardado_en') or doc['datos'].get('Fecha de elaboración',''),
        doc['datos']['Función'],doc['metadatos'].get('modalidad_planeacion','Por confirmar'),
        ', '.join(a['Nombre del alumno'] for a in doc['datos']['Alumnos']),doc['id'][:8]])


def alumno_padron(r):
    from services.planeacion_nee import nee_padron
    return {'ID_Alumno':str(r['ID_Alumno']), 'Nombre del alumno':str(r.get('Nombre_Completo','')),
        'Grado':grado_canonico(r.get('Grado')), 'Grupo':grupo_canonico(r.get('Grupo')),
        'Condición':str(r.get('Condicion_Discapacidad','') or ''),
        'Maestro de apoyo':str(r.get('Maestra de Apoyo','') or ''),
        'ID_Maestro_Regular':str(r.get('ID_Maestro_Regular','') or ''),
        'Situacion_Alumno':str(r.get('Situacion_Alumno','') or ''),
        'NEE registrada':nee_padron(r),
        'Edad de referencia del padrón':str(r.get('Edad_1_Septiembre','') or '')}


def ampliar_matricula(doc,frame):
    """Solo añade altas grupales autorizadas del mismo grupo; conserva toda fila previa."""
    from services.planeacion_modalidad import modalidad
    from services.planeacion_matricula import clave_escuela
    result=deepcopy(doc)
    if not es_guia(doc):return result
    grupos={(grado_canonico(a.get('Grado')),grupo_canonico(a.get('Grupo'))) for a in doc['datos']['Alumnos']}
    if len(grupos)!=1 or not all(next(iter(grupos))):return result
    presentes={a['ID_Alumno'] for a in doc['datos']['Alumnos']}
    contexto={}
    for r in frame.to_dict('records'):
        if (str(r.get('ID_Alumno','')) in presentes or modalidad(r)!='grupal'
            or clave_escuela(r.get('ID_Escuela'))!=clave_escuela(doc['datos']['ID_Escuela'])
            or (grado_canonico(r.get('Grado')),grupo_canonico(r.get('Grupo'))) not in grupos
            or normalizar_texto(r.get('Estatus','')) in {'BAJA','INACTIVO','RETIRADO','ELIMINADO'}):continue
        result['datos']['Alumnos'].append(alumno_padron(r));presentes.add(str(r['ID_Alumno']))
    for r in frame.to_dict('records'):
        if str(r.get('ID_Alumno','')) in presentes and clave_escuela(r.get('ID_Escuela'))==clave_escuela(doc['datos']['ID_Escuela']):
            from services.planeacion_nee import nee_padron
            contexto[str(r['ID_Alumno'])]={'Situacion_Alumno':str(r.get('Situacion_Alumno','') or ''),
                'NEE registrada':nee_padron(r),'ID_Maestro_Regular':str(r.get('ID_Maestro_Regular','') or '')}
    result['metadatos']['contexto_padron_grupo']=contexto
    manual=result['metadatos'].setdefault('guia_grupal_manual',{})
    if not manual.get('maestro_grupo'):
        nombres=list(dict.fromkeys(r['ID_Maestro_Regular'] for r in contexto.values() if r['ID_Maestro_Regular']))
        if nombres:manual['maestro_grupo']=', '.join(nombres)
    if result['datos']['Alumnos']!=doc['datos']['Alumnos']:
        from services.planeacion_modalidad import guia_grupal
        result['metadatos']['guia_grupal_manual']=guia_grupal(result)
    return result


def situacion_inicial(alumno,fuentes):
    """No interpreta BAPSE como necesidad ni deduce NI/RI a partir de discapacidad."""
    from services.planeacion_nee import nee_padron,es_bapse
    status=normalizar_texto(alumno.get('Situacion_Alumno',''))
    if status not in {'NI','RI'}:return ''
    texto=nee_padron(alumno)
    if texto:return status+' · '+texto[:350]
    epp=any(f.get('tipo')=='EPP' and not es_bapse(f) for f in fuentes)
    return status+' · '+('Cuenta con EPP vinculada; revisar los apoyos acordados.' if epp else
        'Nuevo ingreso; revisar la valoración inicial.' if status=='NI' else 'Reingreso; revisar antecedentes y continuidad de apoyos.')


def junio(doc,ahora=None):
    hoy=ahora or datetime.now(ZoneInfo('America/Mexico_City')).date()
    try:fin=int(doc['datos']['Curso escolar'][:4])+1
    except (ValueError,KeyError):return False
    return (hoy.year,hoy.month)>=(fin,6)


def docente_grupo(doc):
    nombres=list(dict.fromkeys(str(a.get('ID_Maestro_Regular','') or '').strip()
        for a in doc['datos']['Alumnos'] if str(a.get('ID_Maestro_Regular','') or '').strip()))
    return ', '.join(nombres)


def sin_aportes(doc):
    """Huella de trabajo del autor, excluyendo SOLO las columnas de especialistas."""
    d=deepcopy(doc)
    for k in ('revision','anterior','guardado_en','_orden'):d.pop(k,None)
    for k in ('aportaciones_equipo','aportaciones_integradas','guia_aportes_integrados','avisos_integracion','firma_aprobada_por'):
        d['metadatos'].pop(k,None)
    for r in d['metadatos'].get('guia_grupal_manual',{}).get('filas',[]):
        for area in ('Psicología','Comunicación','Trabajo Social'):r.pop(area,None)
    return d


def conciliar_autor(doc,base,latest):
    if not es_guia(doc) or sin_aportes(base)!=sin_aportes(latest):
        raise RuntimeError('Otra sesión modificó la planeación. Tu edición se conserva; recupera la versión reciente antes de conciliar.')
    result=deepcopy(doc)
    for k in ('aportaciones_equipo','aportaciones_integradas','guia_aportes_integrados'):
        result['metadatos'][k]=deepcopy(latest['metadatos'].get(k,{}))
    # Las columnas ajenas siempre proceden de la versión reciente, no del editor del autor.
    recientes={r['ID_Alumno']:r for r in latest['metadatos'].get('guia_grupal_manual',{}).get('filas',[])}
    for r in result['metadatos'].get('guia_grupal_manual',{}).get('filas',[]):
        for area in ('Psicología','Comunicación','Trabajo Social'):
            r[area]=recientes.get(r['ID_Alumno'],{}).get(area,'')
    result['revision']=latest['revision']
    return result

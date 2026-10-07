"""Separación de matrícula sin cambiar su modalidad registrada."""
from utils.text import normalizar_texto

def modalidad(alumno):
    value = normalizar_texto(alumno.get('Tipo_Atencion', alumno.get('18.- TIPO DE ATENCIÓN', '')))
    return 'individual' if 'INDIVIDUAL' in value or value in {'I', 'IND'} else 'grupal'

def filtrar(frame, seleccion):
    if seleccion not in {'individual', 'grupal'}:
        raise ValueError('Modalidad no válida.')
    if frame.empty:
        return frame.copy()
    mask = frame.apply(lambda row: modalidad(row.to_dict()) == seleccion, axis=1)
    return frame.loc[mask].copy()

def comprobar(frame, ids, seleccion):
    elegibles = filtrar(frame, seleccion)
    if 'ID_Alumno' not in elegibles or not set(map(str, ids)) <= set(elegibles['ID_Alumno'].astype(str)):
        raise PermissionError('El alumno no pertenece a esta modalidad de tu matrícula.')
    if seleccion == 'individual' and len(set(map(str, ids))) != 1:
        raise ValueError('La planeación individual se crea para un solo alumno.')

def modalidad_documento(doc, frame):
    declared=doc.get('metadatos',{}).get('modalidad_planeacion')
    if declared in {'individual','grupal'}:return declared
    ids={str(a['ID_Alumno']) for a in doc['datos']['Alumnos']}
    rows=frame.loc[frame['ID_Alumno'].astype(str).isin(ids)].to_dict('records') if 'ID_Alumno' in frame else []
    return 'individual' if rows and len(ids)==1 and all(modalidad(r)=='individual' for r in rows) else 'grupal'

GUIA_XIX=['Nombre alumno','Discapacidad o condición','Fecha derivación','Aprendizaje','Psicología','Comunicación','Trabajo Social','Situación inicial','Situación final']
GUIA_XX=['Nombre alumno','Fecha derivación','Aptitud intelectual','Creativa','Socioafectiva','Psicomotriz','Artística','Enriquecimiento escolar','Áulico','Extracurricular','Metodología y responsables']

def guia_grupal(doc):
    """Datos exactos del padrón; no atribuye actividades de otra área ni inventa resultados."""
    if doc.get('metadatos',{}).get('modalidad_planeacion')!='grupal':return {}
    prev=doc['metadatos'].get('guia_grupal_manual',{})
    existentes={r['ID_Alumno']:r for r in prev.get('filas',[])}
    zona={r['ID_Alumno']:r for r in doc['metadatos'].get('grupal_zona',doc['metadatos'].get('equipo',{}).get('grupal',[]))}
    filas=[]
    for a in doc['datos']['Alumnos']:
        row={'ID_Alumno':a['ID_Alumno'],**{h:'' for h in GUIA_XIX}}
        row.update(existentes.get(a['ID_Alumno'],{}))
        row['Nombre alumno']=a['Nombre del alumno'];row['Discapacidad o condición']=a['Condición']
        z=zona.get(a['ID_Alumno'],{})
        for key in ['Fecha derivación','Situación inicial','Situación final']:
            if not row[key]:row[key]=z.get(key,'')
        area=doc['datos']['Función']
        if area in GUIA_XIX and not row[area]:row[area]=z.get('Actividades','')
        filas.append(row)
    return {'maestro_grupo':prev.get('maestro_grupo',''),'filas':filas,'as':prev.get('as',[])}

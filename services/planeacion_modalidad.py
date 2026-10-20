"""Separación de matrícula sin cambiar su modalidad registrada."""
from utils.text import normalizar_texto

def modalidad(alumno):
    value = normalizar_texto(alumno.get('Tipo_Atencion', alumno.get('18.- TIPO DE ATENCIÓN', '')))
    if 'INDIVIDUAL' in value or value in {'I', 'IND'}:return 'individual'
    if 'GRUP' in value or value in {'G','SG','GR','SUB'}:return 'grupal'
    return 'por confirmar'

def filtrar(frame, seleccion, incluir_individuales=False):
    if seleccion not in {'individual', 'grupal'}:
        raise ValueError('Modalidad no válida.')
    if frame.empty:
        return frame.copy()
    admitidas={seleccion}
    if seleccion=='grupal' and incluir_individuales:admitidas.add('individual')
    records = frame.to_dict('records')
    mask = [modalidad(r) in admitidas for r in records]
    return frame.iloc[[i for i, m in enumerate(mask) if m]].copy()

def comprobar(frame, ids, seleccion, incluir_individuales=False):
    elegibles = frame if seleccion=='especialista' else filtrar(frame, seleccion, incluir_individuales)
    if 'ID_Alumno' not in elegibles or not set(map(str, ids)) <= set(elegibles['ID_Alumno'].astype(str)):
        raise PermissionError('El alumno no pertenece a esta modalidad de tu matrícula.')
    if not ids or len(set(map(str, ids))) != len(ids):
        raise ValueError('Selecciona uno o varios alumnos sin duplicados.')

def modalidad_documento(doc, frame):
    declared=doc.get('metadatos',{}).get('modalidad_planeacion')
    if declared in {'individual','grupal','especialista'}:return declared
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
        from services.planeacion_compartida import situacion_inicial,copia_instrumento
        if not row['Situación inicial'] or copia_instrumento(row['Situación inicial']):
            fuentes=[f for f in doc['metadatos'].get('fuentes',[]) if a['ID_Alumno'] in str(f.get('alumno','')).split(',')]
            contexto=doc['metadatos'].get('contexto_padron_grupo',{}).get(a['ID_Alumno'],{})
            resumen=situacion_inicial({**a,**{k:v for k,v in contexto.items() if v}},fuentes)
            row['Situación inicial']=resumen or ('Situación de ingreso por confirmar; revisar la valoración inicial.' if copia_instrumento(row['Situación inicial']) else '')
        # Un aporte forma parte del mismo Anexo, sin requerir que la maestra lo copie.
        for especialidad,aporte in doc['metadatos'].get('aportaciones_equipo',{}).items():
            if especialidad not in ('Psicología','Comunicación','Trabajo Social'):continue
            # Los aportes estructurados anteriores conservan su conciliación
            # humana. Solo las celdas nuevas explícitas son la columna viva.
            if not any('Texto en formato' in r for r in aporte.get('filas',[])):continue
            textos=[]
            for r in aporte.get('filas',[]):
                if r.get('ID_Alumno')==a['ID_Alumno']:
                    texto=r.get('Texto en formato')
                    if texto is None:texto=' · '.join(str(r.get(k,'') or '').strip() for k in ('Objetivo / qué trabajar','Actividad / cómo trabajar') if str(r.get(k,'') or '').strip())
                    if texto:textos.append(texto)
            if textos or any(r.get('ID_Alumno')==a['ID_Alumno'] and 'Texto en formato' in r for r in aporte.get('filas',[])):
                row[especialidad]='\n\n'.join(textos)
        area=doc['datos']['Función']
        if area in GUIA_XIX and not row[area]:row[area]=z.get('Actividades','')
        # Una propuesta local ya revisada conserva su destinatario por ID. La guía
        # y el PDF la leen del mismo origen; nunca se asocia texto por nombre.
        if area in GUIA_XIX and not row[area]:
            actividades=[r.get('Actividades','') for r in doc['tablas'].get('dosificacion',[])
                         if a['ID_Alumno'] in r.get('_alumnos_locales',[]) and r.get('_actividad_local')]
            row[area]='\n\n'.join(v for v in actividades if v)
        filas.append(row)
    from services.planeacion_compartida import docente_grupo
    return {'maestro_grupo':prev.get('maestro_grupo','') or docente_grupo(doc),'filas':filas,'as':prev.get('as',[])}

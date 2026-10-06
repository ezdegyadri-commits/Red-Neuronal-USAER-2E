"""Planeación de especialistas basada en manual y acuerdos de Zona 001.

Complementos aditivos: no reemplazan el formato ni las evidencias del alumno.
"""
from copy import deepcopy
from datetime import date
from uuid import uuid4

AREAS = ('Psicología', 'Comunicación', 'Trabajo Social')
COMPETENCIAS = ('Conciencia emocional', 'Regulación emocional', 'Autonomía emocional',
                'Competencia social', 'Habilidades de vida y bienestar')
FUENTES = [
    {'id':'ZONA-ACUERDOS-2026','titulo':'Acuerdos zona','organismo':'Zona 001','edicion':'Documento compartido octubre 2026'},
    {'id':'ZONA-PSICOLOGIA-2026','titulo':'Acuerdos para el área de Psicología','organismo':'Zona 001','edicion':'Documento compartido octubre 2026'},
    {'id':'ZONA-GRUPAL-2026','titulo':'Planeación grupal del Servicio de Apoyo','organismo':'Zona 001','edicion':'Formato ajustado compartido octubre 2026'},
]


def aplica(doc):
    return doc['datos'].get('Función') in AREAS and doc['formato'] in ('XXIII','XXV')


def preparar(doc):
    result=deepcopy(doc)
    if not aplica(doc):return result
    if 'equipo' not in result['metadatos']:
        result['metadatos']['equipo']={'version':1,'subgrupos':[], 'sesiones':[],
            'competencias':[{'Competencia':c,'Necesidad documentada':'','Descriptor de logro':'','Actividad prevista':''} for c in COMPETENCIAS] if doc['datos']['Función']=='Psicología' else [],
            'grupal':[{'ID_Alumno':a['ID_Alumno'],'Fecha derivación':'','Actividades':'','Situación inicial':'','Situación final':''} for a in doc['datos']['Alumnos']],
            'sugerencia_familia':'','edicion_sesion':{}}
    return result


def limites(doc):
    inicio,fin=doc['datos']['Periodo'].split(' / ')
    return date.fromisoformat(inicio),date.fromisoformat(fin)


def validar(doc):
    if 'grupal_zona' in doc['metadatos']:
        ids={a['ID_Alumno'] for a in doc['datos']['Alumnos']}
        rows=doc['metadatos']['grupal_zona']
        if not isinstance(rows,list) or any(not isinstance(r,dict) for r in rows):
            raise ValueError('La tabla grupal no tiene un formato válido.')
        if any(r.get('ID_Alumno') not in ids for r in rows):
            raise PermissionError('La planeación grupal incluye otro alumno.')
        if {r.get('ID_Alumno') for r in rows}!=ids or len(rows)!=len(ids):
            raise ValueError('La tabla grupal debe conservar una fila por alumno seleccionado.')
    if not aplica(doc) or 'equipo' not in doc['metadatos']:return
    e=doc['metadatos']['equipo'];ids={a['ID_Alumno'] for a in doc['datos']['Alumnos']}
    if e.get('version')!=1:raise ValueError('Versión de organización del equipo no válida.')
    grupos=e.get('subgrupos',[])
    nombres=[str(g.get('nombre','')).strip() for g in grupos]
    if len(nombres)!=len(set(nombres)) or any(not n for n in nombres):
        raise ValueError('Cada subgrupo necesita un nombre único.')
    for grupo in grupos:
        if not grupo.get('alumnos') or not set(grupo['alumnos']).issubset(ids):
            raise PermissionError('El subgrupo contiene alumnos ajenos a esta planeación.')
    for row in e.get('grupal',[]):
        if row.get('ID_Alumno') not in ids:raise PermissionError('La planeación grupal incluye otro alumno.')
    if {r.get('ID_Alumno') for r in e.get('grupal',[])}!=ids or len(e.get('grupal',[]))!=len(ids):
        raise ValueError('La tabla grupal debe conservar una fila por alumno seleccionado.')
    if doc['datos']['Función']=='Psicología' and [r.get('Competencia') for r in e.get('competencias',[])]!=list(COMPETENCIAS):
        raise ValueError('Conserva las cinco competencias emocionales del formato de zona.')
    desde,hasta=limites(doc)
    sesiones=e.get('sesiones',[])
    if len({s.get('id') for s in sesiones})!=len(sesiones):raise ValueError('Hay sesiones duplicadas.')
    for s in sesiones:
        try:fecha=date.fromisoformat(str(s.get('fecha','')))
        except ValueError:raise ValueError('Revisa la fecha de la sesión.') from None
        if not desde<=fecha<=hasta:raise ValueError('La sesión debe quedar dentro del trimestre.')
        if s.get('subgrupo') not in nombres:raise ValueError('Elige un subgrupo registrado.')
        if s.get('contexto') not in contextos(doc):raise ValueError('Contexto no válido para esta función.')
        if not set(s.get('competencias',[])).issubset(COMPETENCIAS):raise ValueError('Competencia no reconocida.')


def contextos(doc):
    from services.planeacion_modelo import FORMATOS
    return FORMATOS[doc['formato']]['contextos']


def guardar_subgrupo(doc,nombre,ids):
    result=preparar(doc);e=result['metadatos']['equipo'];nombre=str(nombre).strip()[:100]
    nuevo={'nombre':nombre,'alumnos':list(dict.fromkeys(ids))}
    e['subgrupos']=[g for g in e['subgrupos'] if g['nombre']!=nombre]+[nuevo]
    validar(result);return result


def guardar_sesion(doc,campos,session_id=''):
    result=preparar(doc);e=result['metadatos']['equipo']
    nueva={k:deepcopy(campos.get(k,[] if k=='competencias' else '')) for k in
           ('fecha','subgrupo','contexto','competencias','objetivo','actividad','apoyos','recursos','seguimiento')}
    if not all(str(nueva[k]).strip() for k in ('objetivo','actividad','recursos','seguimiento')):
        raise ValueError('Completa objetivo, actividad, recursos y cómo observarás el avance.')
    if session_id and session_id not in {s['id'] for s in e['sesiones']}:
        raise ValueError('La sesión que deseas editar no existe.')
    nueva['id']=session_id or uuid4().hex
    if any(s['id']!=nueva['id'] and all(s.get(k)==nueva.get(k) for k in ('fecha','subgrupo','contexto','objetivo','actividad')) for s in e['sesiones']):
        raise ValueError('Esta sesión ya está registrada; abre la existente para editarla.')
    e['sesiones']=[s for s in e['sesiones'] if s['id']!=nueva['id']]+[nueva]
    e['sesiones'].sort(key=lambda s:(s['fecha'],s['id']))
    e['edicion_sesion']={};validar(result)
    return sincronizar(result)


def quitar_sesion(doc,session_id):
    result=preparar(doc);e=result['metadatos']['equipo']
    e['sesiones']=[s for s in e['sesiones'] if s['id']!=session_id]
    e['edicion_sesion']={};return sincronizar(result)


def sincronizar(doc):
    """Actualiza las filas generadas, conservando las redactadas a mano o por IA."""
    result=deepcopy(doc);e=result['metadatos']['equipo']
    filas=[r for r in result['tablas']['dosificacion'] if not r.get('_sesion_equipo')]
    for s in e['sesiones']:
        actividad=s['subgrupo']+' · '+s['objetivo']+'\n'+s['actividad']
        if s['competencias']:actividad+='\nCompetencias: '+', '.join(s['competencias'])
        if s['apoyos']:actividad+='\nApoyos: '+s['apoyos']
        actividad+='\nSeguimiento: '+s['seguimiento']
        if s.get('duracion'):actividad+='\nDuración propuesta: '+str(s['duracion'])+' minutos'
        filas.append({'Contextos':s['contexto'],'Actividades':actividad,
                      'Fecha' if result['formato']=='XXV' else 'Temporalidad':s['fecha'],
                      'Recursos':s['recursos'],'_sesion_equipo':s['id']})
    result['tablas']['dosificacion']=filas
    return result


def revisar(doc):
    if not aplica(doc) or 'equipo' not in doc['metadatos']:return []
    e=doc['metadatos']['equipo'];faltas=[]
    try:validar(doc)
    except (ValueError,PermissionError) as exc:return [str(exc)]
    if not e['subgrupos']:faltas.append('organizar los alumnos en subgrupos de trabajo')
    if not e['sesiones']:faltas.append('calendarizar las sesiones y acciones del trimestre')
    if doc['datos']['Función']=='Psicología':
        if len([s for s in e['sesiones'] if s['contexto']=='Aula de apoyo'])<5:
            faltas.append('calendarizar al menos cinco sesiones de trabajo en subgrupo durante el trimestre')
        cubiertas={c for s in e['sesiones'] for c in s['competencias']}
        for row in e['competencias']:
            c=row.get('Competencia')
            if c not in cubiertas or not all(str(row.get(k,'')).strip() for k in ('Necesidad documentada','Descriptor de logro','Actividad prevista')):
                faltas.append('completar y vincular actividades para '+str(c))
        if not any(s['contexto']=='Aula regular' for s in e['sesiones']):faltas.append('prever al menos una sesión en aula regular')
        if not e.get('sugerencia_familia','').strip():faltas.append('prever una sugerencia a la familia mediante la hoja de sugerencias')
    return faltas


def contexto_zona(doc):
    if doc['formato'] not in ('XXIII','XXV') or doc['datos'].get('Función') not in (*AREAS,'Aprendizaje'):return {}
    psicologia=doc['datos']['Función']=='Psicología'
    fuentes=[FUENTES[0],FUENTES[2]]+([FUENTES[1]] if psicologia else [])
    guia='La planeación grupal ajustada de zona dispone actividades, situación inicial y situación final en filas horizontales. No anticipar la situación final. El plan de intervención se llena anualmente en el formato modificado de zona; esta planeación trimestral no lo sustituye.'
    if psicologia:
        guia+=' Psicología organiza subgrupos, calendariza al menos cinco sesiones grupales en el trimestre, trabaja las cinco competencias emocionales: '+', '.join(COMPETENCIAS)+', prevé una sesión en aula regular y una sugerencia para familias en la hoja correspondiente. No inventar su entrega ni resultados.'
    else:guia+=' No aplicar los mínimos exclusivos de Psicología a Comunicación o Trabajo Social.'
    return {'fuentes':fuentes,'guia':guia}


def tablas_salida(doc):
    e=doc['metadatos'].get('equipo') if aplica(doc) else None
    if not e and doc['metadatos'].get('grupal_zona'):
        e={'subgrupos':[],'competencias':[],'grupal':doc['metadatos']['grupal_zona']}
    if not e:return []
    alumnos={a['ID_Alumno']:a for a in doc['datos']['Alumnos']}
    tablas=[('Organización de subgrupos',['Subgrupo','Alumnos','Grado y grupo'],[
        {'Subgrupo':g['nombre'],'Alumnos':', '.join(alumnos[i]['Nombre del alumno'] for i in g['alumnos'] if i in alumnos),
         'Grado y grupo':', '.join(sorted({str(alumnos[i]['Grado'])+' '+str(alumnos[i]['Grupo']) for i in g['alumnos'] if i in alumnos}))} for g in e['subgrupos']])]
    if not e['subgrupos']:tablas=[]
    if e['competencias']:tablas.append(('Competencias emocionales',['Competencia','Necesidad documentada','Descriptor de logro','Actividad prevista'],e['competencias']))
    headers=['Nombre del alumno','Discapacidad o condición','Fecha derivación','Área','Actividades','Situación inicial','Situación final']
    filas=[]
    for r in e['grupal']:
        if r['ID_Alumno'] not in alumnos:continue
        a=alumnos[r['ID_Alumno']]
        filas.append({**r,'Nombre del alumno':a['Nombre del alumno'],'Discapacidad o condición':a['Condición'],'Área':doc['datos']['Función']})
    tablas.append(('Planeación grupal ajustada de zona',headers,filas))
    return tablas

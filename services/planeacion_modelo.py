"""Plantillas del manual USAER. Sin escrituras ni solicitudes externas."""
from copy import deepcopy
from datetime import date
import re

FORMATOS = {
    'XXI': {
        'titulo': 'Plan de Intervención', 'paginas_manual': [154,155,156,157],
        'tablas': {
            'barreras': ['BAP','Acciones para minimizarla o eliminarla','E','A','SF','Responsable','Temporalidad'],
            'necesidades': ['NEE','Aprendizajes y/u Objetivos','Descriptor de Logro','Tipo de registro','Apoyos o ajustes','E','A','SF','Responsables','Temporalidad','Seguimiento'],
            'curriculo': ['NEE','Aprendizajes priorizados y/u objetivos','Descriptor de logro','Temporalidad','Apoyos','Ajustes razonables','Seguimiento'],
            'evaluacion_final': ['Curso escolar','Resultados de la implementación de las acciones para minimizar o eliminar las barreras','Situación final del alumno en relación con sus NEE','Situación académica'],
            'participantes': ['Nombre','Función','Observaciones','Firmas'],
        },
        'contextos': ['Escolar','Áulico','Sociofamiliar'],
        'firmantes': ['Personas implicadas','Director de la Escuela','Director del Servicio de Apoyo'],
    },
    'XXIII': {
        'titulo': 'Planeación del Servicio de Apoyo de Educación Especial', 'paginas_manual': [166,167],
        'tablas': {'aprendizajes': ['Necesidades educativas específicas','Aprendizaje y/u objetivo','Descriptor de logro'],
                   'dosificacion': ['Contextos','Actividades','Temporalidad','Recursos']},
        'contextos': ['Aula de apoyo','Aula regular','Escuela','Familia'],
        'textos': ['Evaluación','Observaciones'],
        'firmantes': ['Especialista','Vo. Bo. Director del Servicio de Apoyo'],
    },
    'XXV': {
        'titulo': 'Planeación del Área de Trabajo Social', 'paginas_manual': [172,173],
        'tablas': {'barreras': ['Barreras para el Aprendizaje y la Participación','Apoyos y/o ajustes razonables'],
                   'dosificacion': ['Contextos','Actividades','Fecha','Recursos']},
        'contextos': ['Aula regular','Escuela','Familia','Comunidad'],
        'textos': ['Resultados obtenidos en los diferentes contextos'],
        'firmantes': ['Trabajador Social','Vo. Bo. Director del Servicio de Apoyo'],
    },
}


def texto(valor):
    return '' if valor is None or str(valor).strip().lower() in {'nan','none','nat'} else str(valor).strip()


def periodo_trimestral(ciclo_inicio, trimestre):
    if trimestre not in {1,2,3}:
        raise ValueError('Selecciona un trimestre de 1 a 3.')
    anio = int(ciclo_inicio) + (trimestre > 1)
    inicio, fin = {1: ((10,1),(12,31)), 2: ((1,1),(3,31)), 3: ((4,1),(6,30))}[trimestre]
    return date(anio,*inicio).isoformat(), date(anio,*fin).isoformat()


def fase_primaria(grado):
    match = re.match(r'^\s*([1-6])(?:\D|$)', texto(grado))
    return {1:3,2:3,3:4,4:4,5:5,6:5}.get(int(match[1])) if match else None


def crear_plantilla(formato, ids, alumnos_autorizados, *, autor, funcion,
                    ciclo_inicio=2026, trimestre=1, escuelas=(), fecha=None):
    """El adaptador servidor debe entregar solo el padrón autorizado; no el del navegador."""
    if formato not in FORMATOS:
        raise ValueError('Formato no reconocido.')
    ids = list(dict.fromkeys(texto(i) for i in ids))
    if not ids or any(not i for i in ids):
        raise ValueError('Elige al menos un alumno.')
    if formato == 'XXI' and len(ids) != 1:
        raise ValueError('El plan de intervención es individual; crea uno por alumno.')
    por_id = {}
    for row in alumnos_autorizados:
        key = texto(row.get('ID_Alumno'))
        if key in por_id and por_id[key] != row:
            raise ValueError('Hay datos contradictorios para el ID del alumno.')
        por_id[key] = row
    if not set(ids).issubset(por_id):
        raise PermissionError('La selección incluye alumnos fuera de tu autorización.')
    filas = [por_id[i] for i in ids]
    school_ids = {texto(r.get('ID_Escuela')) for r in filas}
    if len(school_ids) != 1 or '' in school_ids:
        raise ValueError('Elige alumnos de una sola escuela identificada.')
    school_id = next(iter(school_ids))
    matches = [r for r in escuelas if texto(r.get('ID_Escuela')) == school_id]
    if len(matches) > 1:
        raise ValueError('La escuela tiene registros duplicados; requiere revisión.')
    escuela = matches[0] if matches else {}
    ccts = {texto(r.get('CCT_Escuela')) for r in filas if texto(r.get('CCT_Escuela'))}
    if texto(escuela.get('CCT')):
        ccts.add(texto(escuela['CCT']))
    if len(ccts) > 1:
        raise ValueError('Hay CCT contradictorios; no se elegirá uno automáticamente.')
    nombres = {texto(r.get('Nombre_Escuela')) for r in filas if texto(r.get('Nombre_Escuela'))}
    school_name = texto(escuela.get('Nombre_Escuela'))
    if not school_name and len(nombres) > 1:
        raise ValueError('Hay nombres de escuela contradictorios; requiere revisión.')
    personas = [{
        'ID_Alumno': texto(r.get('ID_Alumno')), 'Nombre del alumno': texto(r.get('Nombre_Completo')),
        'Edad de referencia del padrón': texto(r.get('Edad_1_Septiembre')),
        'Grado': texto(r.get('Grado')), 'Grupo': texto(r.get('Grupo')),
        'Condición': texto(r.get('Condicion_Discapacidad')),
        'Maestro de apoyo': texto(r.get('Maestra de Apoyo')),
        'ID_Maestro_Regular': texto(r.get('ID_Maestro_Regular')),
        'Fase de inscripción': fase_primaria(r.get('Grado')) if 'PRIMARIA' in texto(r.get('Nivel_Educativo')).upper() else None,
    } for r in filas]
    inicio, fin = periodo_trimestral(ciclo_inicio,trimestre)
    spec = deepcopy(FORMATOS[formato])
    doc = {
        'version_esquema': 1, 'formato': formato, 'estado': 'BORRADOR',
        'datos': {'Servicio de apoyo':'USAER 02E','Zona':'01','ID_Escuela':school_id,
                  'Escuela regular':school_name or next(iter(nombres),''),'CCT':next(iter(ccts),''),
                  'Curso escolar':f'{ciclo_inicio}-{int(ciclo_inicio)+1}',
                  'Fecha de elaboración':(fecha or date.today()).isoformat(),
                  'Nombre del especialista':autor,'Función':funcion,'Trimestre':trimestre,
                  'Periodo':f'{inicio} / {fin}','Alumnos':personas},
        'tablas':{k:[] for k in spec['tablas']},
        'textos':{k:'' for k in spec.get('textos',[])},
        'metadatos':{'fuentes':[],'referencias_curriculares':[],'propuestas_ia':[],
                     'NEE confirmadas desde IEPP':False,'Plan de intervención vinculado':'',
                     'firma_aprobada_por':'','pendientes':[]},
    }
    if formato == 'XXI':
        doc['datos'].update({'Necesidades educativas específicas asociadas a':'','Maestro de grupo':'','Vigencia en cursos escolares':None})
    for contexto in spec['contextos']:
        if 'dosificacion' in doc['tablas']:
            doc['tablas']['dosificacion'].append({c:contexto if c=='Contextos' else '' for c in spec['tablas']['dosificacion']})
    if not next(iter(ccts),''):
        doc['metadatos']['pendientes'].append('CCT no registrado')
    doc['metadatos']['pendientes'].append('Confirmar las NEE y su fuente; una condición del padrón no equivale a NEE')
    return doc


def vincular_evidencias(documento, registros):
    """Los adaptadores resuelven legados/grupos antes; nunca asociar por nombre aquí."""
    doc = deepcopy(documento)
    ids = {r['ID_Alumno'] for r in doc['datos']['Alumnos']}
    fuentes = []
    for r in registros:
        if texto(r.get('Estado')).upper() in {'ANULADO','ELIMINADO','DUPLICADO','RETIRADO'}:
            continue
        alumno, escuela = texto(r.get('ID_Alumno')), texto(r.get('ID_Escuela'))
        if alumno and alumno not in ids:
            continue
        if escuela and escuela != doc['datos']['ID_Escuela']:
            continue
        if not alumno and escuela != doc['datos']['ID_Escuela']:
            continue
        fuentes.append({**deepcopy(r),'alcance':'individual' if alumno else 'contexto escolar','confirmacion_docente':False})
    doc['metadatos']['fuentes'] = fuentes
    return doc


def revisar_redaccion(descriptor):
    """Ayuda local orientativa; no determina aprobación ni logro del alumno."""
    value = texto(descriptor)
    if not value:
        return ['Describe lo que hará el alumno para demostrar el aprendizaje.']
    avisos = []
    if re.search(r'\b(conocer|comprender|mejorar|desarrollar|aprender)\b',value,re.I):
        avisos.append('Expresa el logro con una acción observable en presente: identifica, explica, compara, escribe o resuelve.')
    if not re.search(r'\b(alumn[oa]s?|estudiantes?|niñ[oa]s?|grupo|participantes?)\b',value,re.I):
        avisos.append('Verifica que se identifique el sujeto que aprende; también puede ser su nombre.')
    return avisos

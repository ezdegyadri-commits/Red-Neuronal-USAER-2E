"""Anexos XVII y XVIII del Manual USAER (pp. 141-151). Sin inferencias clínicas."""
from copy import deepcopy
import hashlib
import json
import re

AREAS = ('Aprendizaje', 'Psicología', 'Comunicación', 'Trabajo Social')
SECCIONES = {
    '2. Información inicial y salud': {
        'Trabajo Social': ['2.1. Embarazo', '2.2. Parto', '2.3. Apariencia física', '2.4. Salud']},
    '3. Funcionamiento intelectual': {
        'Psicología': ['3.1. Atención', '3.2. Memoria', '3.3. Percepción', '3.4. Razonamiento',
                      '3.5. Cociente intelectual', '3.6. Etapa de desarrollo', '3.7. Creatividad (AS)']},
    '4. Conducta adaptativa': {
        'Comunicación': ['4.1. Comunicación y lenguaje: intención comunicativa',
            '4.1. Sistema de comunicación alternativo', '4.1. Lenguaje oral: fonológico',
            '4.1. Lenguaje oral: morfosintáctico', '4.1. Lenguaje oral: semántico',
            '4.1. Lenguaje oral: pragmático', '4.1. Comprensión expresiva', '4.1. Comprensión receptiva'],
        'Aprendizaje': ['4.1. Lectura y escritura funcional', '4.1. Matemáticas funcionales',
            '4.1. Conceptos relativos al dinero', '4.1. Orientación temporal', '4.1. Orientación espacial'],
        'Psicología': ['4.1. Autodirección', '4.2. Relaciones interpersonales', '4.2. Cumplimiento de normas',
            '4.2. Responsabilidad', '4.2. Autoestima', '4.2. Autoconcepto',
            '4.2. Identificación y autorregulación de emociones', '4.2. Autodeterminación',
            '4.3. Noción corporal', '4.3. Coordinación motriz fina', '4.3. Coordinación motriz gruesa',
            '4.3. Movilidad, equilibrio y desplazamiento'],
        'Trabajo Social': ['4.3. Autocuidado', '4.3. Actividades en la casa', '4.3. Utilización de la comunidad',
            '4.3. Salud y seguridad', '4.3. Ocio y tiempo libre']},
    '5. Funcionamiento académico': {
        'Aprendizaje': ['5.1. Competencia curricular', '5.2. Estilo de aprendizaje']},
    '6. Contextos': {
        'Aprendizaje': ['6.1. Contexto escolar', '6.1. Historia escolar'],
        'Trabajo Social': ['6.2. Contexto familiar', '6.3. Contexto social']},
}
CONCLUSION = ['7.1. Conclusión', 'Énfasis de atención acordado', 'Asociación educativa sustentada',
              'Acuerdos y apoyos del equipo']
NEE = ['Aspectos', 'Características relevantes', 'NEE', 'Apoyos', 'Ajustes razonables', 'Responsables', 'Fecha o período']
BAP = ['Contextos', 'Tipo de barrera', 'Acciones generales', 'Responsables', 'Fecha o período']
FAMILIA = ['Nombre', 'Parentesco', 'Rol y participación con el alumno', 'Fecha de nacimiento', 'Edad', 'Escolaridad', 'Ocupación y sueldo']
HISTORIA = ['Curso escolar', 'Grado/grupo', 'Nivel educativo', 'Escuela de Educación Especial', 'Escuela de Educación Regular', 'Observaciones']
GENERALES = ['Fecha de nacimiento', 'Edad', 'Domicilio', 'Nombre de la madre', 'Edad de la madre',
    'Escolaridad de la madre', 'Ocupación de la madre', 'Domicilio de la madre', 'Nombre del padre',
    'Edad del padre', 'Escolaridad del padre', 'Ocupación del padre', 'Domicilio del padre',
    'Nombre del maestro/a', 'Fecha inicial de evaluación', 'Fecha final de evaluación', 'Motivo de evaluación']

def campos(area):
    if area == 'Conclusión': return CONCLUSION
    return [f for areas in SECCIONES.values() for f in areas.get(area, [])]

def vacia(area):
    value = {'campos': {f: '' for f in campos(area)}, 'instrumentos': '', 'fecha_aplicacion': '',
             'evaluaciones': [], 'sintesis': '', 'validada': False}
    if area == 'Aprendizaje':
        value.update({'generales': {f: '' for f in GENERALES}, 'historia': []})
    if area == 'Trabajo Social': value['familia'] = []
    if area == 'Conclusión': value.update({'nee': [dict.fromkeys(NEE,'') | {'Aspectos':a} for a in
        ['Funcionamiento intelectual','Habilidades conceptuales de conducta adaptativa','Habilidades sociales de conducta adaptativa','Habilidades prácticas de conducta adaptativa','Funcionamiento académico']],
        'bap': [dict.fromkeys(BAP,'') | {'Contextos':c} for c in ['Áulico','Escolar','Familiar','Social']]})
    return value

def clave(alumno, ciclo):
    if not alumno or not re.fullmatch(r'20\d{2}-20\d{2}', str(ciclo)):
        raise ValueError('Alumno y ciclo escolar son obligatorios.')
    return hashlib.sha256((str(alumno)+'|'+str(ciclo)).encode()).hexdigest()

def reconstruir(rows):
    """Una identidad por alumno/ciclo y revisiones independientes por área."""
    docs = {}; seen=set()
    for row in rows:
        try:
            value = json.loads(row['Contenido'])
            if not isinstance(value, dict): continue
            key = clave(str(row['Alumno']), str(row['Ciclo']))
            parte = str(row['Parte'])
            if parte not in ('META', *AREAS, 'Conclusión'): continue
            version=(key,parte,str(row['Revision']))
            if version in seen:continue
            seen.add(version)
            doc = docs.setdefault(key, {'id': key, 'alumno': str(row['Alumno']), 'ciclo': str(row['Ciclo']), 'partes': {}})
            # Orden del diario append-only, no reloj del servidor: admite fechas iguales
            # sin perder cambios y no revive una revisión antigua reintentada más tarde.
            doc['partes'][parte] = {'contenido': value, 'revision': str(row['Revision']),
                'fecha': str(row['Fecha']), 'autor': str(row['Autor']), 'cuenta': str(row['Cuenta']),
                'estado': str(row['Estado'])}
        except (ValueError, KeyError, TypeError): continue
    return [d for d in docs.values() if 'META' in d['partes']]

def validar_parte(area, value):
    if area not in (*AREAS, 'Conclusión') or not isinstance(value, dict):
        raise ValueError('Apartado no válido.')
    result = deepcopy(value)
    if set(result.get('campos', {})) != set(campos(area)):
        raise ValueError('Los apartados deben conservar la estructura del Anexo XVII.')
    if any(not isinstance(v, str) or len(v) > 12000 for v in result['campos'].values()):
        raise ValueError('Texto del apartado no válido o demasiado extenso.')
    if not isinstance(result.get('validada'),bool):raise ValueError('Revisión no válida.')
    if result['validada'] and area!='Conclusión' and not any(t.strip() for t in result['campos'].values()) and not str(result.get('sintesis','')).strip():
        raise ValueError('Registra hallazgos o justifica que el área no fue evaluada antes de confirmarla.')
    if not isinstance(result.get('evaluaciones'),list) or len(result['evaluaciones'])>20:
        raise ValueError('Evaluaciones no válidas.')
    for ev in result['evaluaciones']:
        if not isinstance(ev,dict) or not all(isinstance(ev.get(k),str) for k in ('id','texto','nombre')):
            raise ValueError('Evaluación no válida.')
        if len(ev['texto'])>12000:raise ValueError('Resume los hallazgos del instrumento a 12000 caracteres.')
    if 'generales' in result:
        if not isinstance(result['generales'],dict) or not set(result['generales'])<=set(GENERALES):
            raise ValueError('Datos generales no válidos.')
        if any(not isinstance(t,str) or len(t)>12000 for t in result['generales'].values()):
            raise ValueError('Dato general demasiado extenso o no válido.')
    if 'generales_editados' in result:
        if not isinstance(result['generales_editados'],list) or any(f not in GENERALES for f in result['generales_editados']):
            raise ValueError('Identificación de datos corregidos no válida.')
    for name,headers in [('nee',NEE),('bap',BAP),('familia',FAMILIA),('historia',HISTORIA)]:
        if name not in result:continue
        if not isinstance(result[name],list) or len(result[name])>100:raise ValueError('Tabla no válida.')
        for row in result[name]:
            if not isinstance(row,dict) or not set(row)<=set(headers):raise ValueError('Columnas no válidas.')
            for key,text in list(row.items()):
                row[key]='' if text is None else str(text)
                if len(row[key])>12000:raise ValueError('Celda demasiado extensa.')
    if len(json.dumps(result, ensure_ascii=False)) > 36000:
        raise ValueError('El área es demasiado extensa; conserva únicamente los hallazgos pertinentes.')
    return result

def pendientes(doc):
    result = []
    for area in AREAS:
        p = doc['partes'].get(area, {}).get('contenido', {})
        if not p.get('validada'): result.append(area+': revisar hallazgos o justificar que no se evaluó el área.')
    p = doc['partes'].get('Conclusión', {}).get('contenido', {})
    if not p.get('campos', {}).get('7.1. Conclusión', '').strip(): result.append('Integrar la conclusión interdisciplinaria.')
    if not any(str(r.get('NEE','')).strip() for r in p.get('nee',[])): result.append('Registrar la determinación de NEE o justificar su ausencia en la tabla.')
    if not any(str(r.get('Tipo de barrera','')).strip() for r in p.get('bap',[])): result.append('Registrar BAP por contexto o documentar su ausencia en la tabla.')
    for row in p.get('nee', []):
        nee = str(row.get('NEE', '')).strip()
        if nee and not re.match(r'^necesita\s+\w+', nee, re.I):
            result.append('NEE: usar Necesita + verbo + qué.'); break
    return result

def conclusion_vigente(doc):
    value=doc['partes'].get('Conclusión',{}).get('contenido',{})
    return bool(value.get('validada') and value.get('revisiones_areas') ==
        {a:doc['partes'].get(a,{}).get('revision','') for a in AREAS})

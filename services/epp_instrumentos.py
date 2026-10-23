"""Instrumentos del manual: respuestas verificables, sin baremos inventados."""
from copy import deepcopy
from collections import Counter
from datetime import date
import hashlib
import json

VERSION='USAER-2020-v1'
SI_NO=('No observado','Sí','No')
FRECUENCIA=('No observado','1 · Poco frecuente','2 · Frecuente','3 · Muy frecuente')
FUENTE='Manual de Operatividad de los Servicios de Apoyo de Educación Especial, segunda edición, 2020'


def items(textos,opciones=SI_NO,prefix=''):
    return [{'id':prefix+str(i+1),'texto':t,'opciones':opciones} for i,t in enumerate(textos)]


DEFINICIONES={
 'XI':{'nombre':'Cuestionario de Identificación de BAP Sociofamiliar (Anexo XI)','area':'Trabajo Social','paginas':'131','destino':'6.2. Contexto familiar',
       'items':items([
        'Los padres de familia reconocen y aceptan las necesidades específicas de su hijo.',
        'En los trabajos de los niños se observa que los padres de familia siguen las recomendaciones dadas por el docente.',
        'La familia coopera para que el alumno realice actividades escolares en otros espacios (trabajo en casa de compañeros, bibliotecas, otros).',
        'La familia asiste y participa en las actividades que promueve la escuela (juntas, talleres, pláticas, recreativas).',
        'El padre de familia dedica tiempo de calidad para apoyar al alumno en las tareas escolares.',
        'En el comportamiento del alumno se observa que hay establecimiento de reglas y/o límites claros en casa.',
        'El alumno se presenta en condiciones aceptables de higiene personal.',
        'En la organización de tareas de la casa al alumno se le asignan responsabilidades.',
        'Existe confianza en el padre de familia para comentar con el maestro conflictos que se estén dando en las relaciones familiares y/o económicas.',
        'Al padre de familia se le informa sobre las necesidades de su hijo cuando se requiere.',
        'Los padres de familia asisten a la escuela para indagar los avances de sus hijos y tomar acuerdos con los profesores en las fechas programadas.',
        'La familia cuenta con recursos económicos para que el alumno sea atendido por otros especialistas/medicamentos.',
        'Los padres de familia satisfacen las necesidades de alimentación de su hijo (desayuno, refrigerio).',
        'El alumno se presenta a la escuela con los materiales requeridos que la maestra solicita para realizar diferentes actividades.',
        'El alumno asiste a actividades recreativas, cultural y/o de juego por la tarde.',
        'El domicilio del alumno se encuentra ubicado donde está la escuela.'])},
 'XIII':{'nombre':'Estilo de Enseñanza del docente regular (Anexo XIII)','area':'Aprendizaje','paginas':'136-137','destino':'6.1. Contexto escolar',
       'items':items([
        'Realiza la planeación didáctica considerando los elementos curriculares que la conforman en tiempo y forma.',
        'Antes de iniciar las actividades emplea alguna dinámica o actividad lúdica para despertar el interés de los alumnos.',
        'Considera los conocimientos previos del alumno mediante distintas técnicas (formula preguntas, lluvia de ideas, hace demostraciones, experimentos u otras).',
        'Emplea el tiempo que se requiere para el desarrollo de la clase considerando la asignatura, horario, tema, actividad o rutina.'])+
        items(['De reproducción de la información: definir, explicar, enumerar.','De clasificación en función de diversas categorías.','De repetición: planas, caligrafía.','De relacionar conceptos e ideas de temas abordados previamente.','De producción y creación personal: resumen, carta, cuento, esquemas.','De estructura donde se delimita claramente qué hay que hacer.'],FRECUENCIA,'5.')+
        items(['Auditivo (audios, audiolibros).','Visual (esquemas, dibujos, ilustraciones).','Kinestésico (experimentos, construcciones, manualidades).'],FRECUENCIA,'6.')+
        [{'id':'7','texto':'Tipo de motivación mediante recompensa','opciones':('No observado','Tangible','Social','Tangible y social','Ninguna')},
         {'id':'8','texto':'Relación del maestro con el alumno','opciones':()}]+
        [{**q,'id':str(i+9)} for i,q in enumerate(items([
        'Al finalizar las actividades, realiza una retroalimentación sobre el tema planteando preguntas/lluvia de ideas.',
        'Realiza alguna estrategia de evaluación al finalizar una clase.',
        'Revisa las tareas o producciones de los alumnos haciéndoles saber sus logros y áreas de oportunidad.',
        'Realiza las actividades con los alumnos dando las indicaciones paso a paso hasta concluirlas.',
        'Emplea material didáctico concreto que apoya el desarrollo de las actividades para el logro de los aprendizajes esperados.',
        'Considera las características de los alumnos, proporcionando el tiempo que requieren para la realización de las actividades.',
        'Durante las actividades el maestro monitorea la participación de los alumnos en las distintas formas de organización.']))]+
        items(['Emplea la plenaria como principal forma de organización.','Emplea el trabajo en pequeños grupos como principal forma de organización.','Emplea el trabajo en binas como principal forma de organización.','Emplea el trabajo individual como principal forma de organización.'],FRECUENCIA,'16.')},
 'XIV':{'nombre':'Estilo de Aprendizaje y Motivación para Aprender (Anexo XIV)','area':'Aprendizaje','paginas':'138','destino':'5.2. Estilo de aprendizaje',
        'items':items(['Muestra interés hacia la tarea que se le presenta.','Mantiene la atención en las actividades que se le proponen.','Busca ayuda en la realización de las tareas.','Inicia, desarrolla y termina la tarea.','Necesita acompañamiento del maestro para concluir la tarea.','Al concluir la tarea se siente satisfecho con lo realizado.'])+
        [{'id':'7','texto':'Tipo de motivación para mantener el interés por aprender','opciones':('No observado','Tangible','Social','Tangible y social','Ninguna')}]+
        items(['Plenaria','Pequeños grupos','Binas','Individual'],FRECUENCIA,'8.')+
        items(['Verbal','Escrita','Kinestésica'],FRECUENCIA,'9.')+
        [{**q,'id':str(i+10)} for i,q in enumerate(items([
        'Sigue el ritmo de trabajo de sus compañeros.','Prefiere seguir instrucciones escritas y no orales.',
        'Aprende mejor cuando tiene acceso a la información a través de imágenes, diagramas, gráficos, mapas.',
        'Se impacienta si tiene que escuchar por períodos prolongados y no se presenta material gráfico.',
        'Después de ver una película o video es capaz de explicar a detalle lo aprendido.',
        'Aprende con mayor rapidez cuando se le explican las cosas.',
        'Tiene facilidad para organizar mentalmente sus ideas y expresarlas.',
        'Aprende a base de repetirse a sí mismo, paso a paso todo un proceso o serie de pasos.',
        'Tiene facilidad para aprender canciones, poemas, rimas, trabalenguas.',
        'Comprende con facilidad cuando tiene la oportunidad de tocar, mover, sentir, dibujar, mostrar.',
        'Prefiere aprender por medio de simulacros, juegos, sociodramas.',
        'Se le dificulta comprender lo que no pone en práctica.',
        'Disfruta trabajar con sus manos en el salón de clase (manualidades).']))]},
 'XVI':{'nombre':'Guía para la Observación de la Autodirección (Anexo XVI)','area':'Psicología','paginas':'140','destino':'4.1. Autodirección',
        'items':items(['Protesta cuando no está de acuerdo.','Hace valer su opinión en actividades conjuntas.','Exige ante los demás sus pertenencias, juegos, etc.',
        'Elige según sus gustos entre diferentes juegos, materiales.','Elige entre dos o tres alternativas que se le presentan.','Manifiesta sus preferencias.','Pide ayuda si lo necesita.',
        'Hace compras sencillas de forma autónoma: golosinas, alimentos, etc.','Ayuda espontáneamente a quien piensa que lo necesita.',
        'Da sus opiniones y acepta las de los demás.','Muestra independencia del adulto para resolver determinados problemas.','Defiende sus derechos y respeta los de los demás en el grupo.',
        'Inicia actividades espontáneamente.','Termina las tareas propuestas por iniciativa propia.',
        'En los trabajos colectivos es capaz de reclamar, manifestar su desacuerdo, protestar, hacer valer su opinión.',
        'Se le puede responsabilizar de actividades adecuadas a su nivel: dar recados, llevar objetos a otro espacio, etc.',
        'Llama a las personas idóneas para buscar ayuda en situación de peligro.','Respeta los horarios habituales: comida, recreo.','Busca alternativas para resolver situaciones conflictivas.'],('No observado','Sí','Con ayuda','No'))}
}


def plantilla(codigo):
    if codigo not in DEFINICIONES:raise ValueError('No hay reglas digitales verificadas para este instrumento.')
    return {'version':VERSION,'fecha':'','respuestas':{q['id']:{'respuesta':'No observado' if q['opciones'] else '', 'observaciones':''} for q in DEFINICIONES[codigo]['items']}}


def validar(codigo,captura):
    expected=plantilla(codigo)
    if not isinstance(captura,dict) or set(captura)!=set(expected) or captura['version']!=VERSION:raise ValueError('Versión de aplicación no válida.')
    if not isinstance(captura['fecha'],str):raise ValueError('La fecha de aplicación debe ser texto ISO.')
    if captura['fecha']:
        try:date.fromisoformat(captura['fecha'])
        except (ValueError,TypeError):raise ValueError('Indica una fecha de aplicación válida.')
    if not isinstance(captura['respuestas'],dict) or set(captura['respuestas'])!=set(expected['respuestas']):raise ValueError('La aplicación no conserva los reactivos del formato.')
    for q in DEFINICIONES[codigo]['items']:
        r=captura['respuestas'][q['id']]
        if not isinstance(r,dict) or set(r)!={'respuesta','observaciones'}:raise ValueError('Respuesta no válida.')
        if not all(isinstance(t,str) and len(t)<=500 for t in r.values()):raise ValueError('Resume cada observación a 500 caracteres.')
        if q['opciones'] and r['respuesta'] not in q['opciones']:raise ValueError('Elige una opción del instrumento.')
    return deepcopy(captura)


def calcular(codigo,captura):
    c=validar(codigo,captura);d=DEFINICIONES[codigo]
    counts=Counter();pendientes=[];hallazgos=[]
    for q in d['items']:
        r=c['respuestas'][q['id']];answer=r['respuesta'].strip()
        if not answer or answer=='No observado':
            pendientes.append(q['id'])
            if r['observaciones'].strip():hallazgos.append(q['id']+'. '+q['texto']+': No observado. Observación: '+r['observaciones'])
            continue
        if q['opciones']:counts[answer]+=1
        hallazgos.append(q['id']+'. '+q['texto']+': '+answer+('. Observación: '+r['observaciones'] if r['observaciones'] else ''))
    return {'conteos':dict(counts),'respondidos':len(d['items'])-len(pendientes),'pendientes':pendientes,
            'total_registros':len(d['items']),'hallazgos':hallazgos,
            'alcance':'Resumen descriptivo de respuestas; el manual no establece puntaje total, baremos ni punto de corte para este anexo.'}


def editar_respuestas(codigo,captura,base,cambios):
    cap=validar(codigo,captura);rows=deepcopy(base)
    for i,values in cambios.get('edited_rows',{}).items():
        if not str(i).isdigit() or not 0<=int(i)<len(rows) or not set(values)<={'Respuesta','Observaciones'}:raise ValueError('Edición fuera de las respuestas del instrumento.')
        rows[int(i)].update(values)
    for row in rows:
        if row['Ítem'] not in cap['respuestas']:raise ValueError('Reactivo ajeno al instrumento.')
        cap['respuestas'][row['Ítem']]={'respuesta':str(row['Respuesta'] or ''),'observaciones':str(row['Observaciones'] or '')}
    return validar(codigo,cap)


def incorporar(doc,area,codigo,captura,revisada=False):
    from services.epp_modelo import vacia,validar_parte
    if not revisada:raise ValueError('Revisa las respuestas antes de incorporarlas a la EPP.')
    d=DEFINICIONES.get(codigo)
    if not d or d['area']!=area:raise PermissionError('El instrumento no corresponde a tu área.')
    c=validar(codigo,captura);result=calcular(codigo,c)
    if not c['fecha'] or not result['hallazgos']:raise ValueError('Indica fecha y al menos una respuesta u observación documentada.')
    value=deepcopy(doc['partes'].get(area,{}).get('contenido',vacia(area)))
    application=hashlib.sha256(json.dumps([doc['id'],area,codigo,c['fecha']]).encode()).hexdigest()
    body=d['nombre']+' · '+c['fecha']+'\n'+FUENTE+', pp. '+d['paginas']+' · '+VERSION+'\n'+result['alcance']+'\n'
    body+='Aplicación '+('parcial' if result['pendientes'] else 'completa')+'. Respondidos: '+str(result['respondidos'])+'/'+str(result['total_registros'])+'.\n'
    body+='\n'.join(result['hallazgos'])
    if len(body)>12000:raise ValueError('La aplicación es demasiado extensa. Resume las observaciones antes de incorporar.')
    ev={'id':hashlib.sha256((application+body).encode()).hexdigest(),'aplicacion_id':application,'nombre':d['nombre'],'fecha':c['fecha'],'texto':body,'entrada':'DIGITAL','codigo':codigo,'version':VERSION,'conteos':result['conteos'],'respuestas':c['respuestas']}
    value['evaluaciones']=[e for e in value.get('evaluaciones',[]) if e.get('aplicacion_id')!=application]+[ev]
    value.setdefault('aplicaciones_en_curso',{})[codigo]=c
    field=d['destino']
    if not value['campos'].get(field,'').strip():value['campos'][field]='Fuente: '+d['nombre']+' ('+c['fecha']+').\n'+body
    value['validada']=False
    return validar_parte(area,value)

"""Contrato de generación del borrador completo; sin datos identificadores."""
import hashlib
import json
from ai.planeacion_prompt import INSTRUCCIONES
from services.planeacion_modelo import FORMATOS
from services.planeacion_equipo import COMPETENCIAS

VERSION='planeacion-completa-2026-10-06-v1'
CAMPOS=('necesidad','objetivo','descriptor','actividad','contexto','apoyos','recursos','evaluacion','fundamento')
LISTAS=('evidencias','fuentes','referentes','destinatarios','competencias')
SCHEMA={'type':'object','required':['observaciones','faltantes','unidades','sugerencia_familia'],
 'properties':{'observaciones':{'type':'string'},'faltantes':{'type':'array','items':{'type':'string'}},
 'sugerencia_familia':{'type':'string'},'unidades':{'type':'array','items':{'type':'object',
 'required':list(CAMPOS)+list(LISTAS),'properties':{**{k:{'type':'string'} for k in CAMPOS},
 **{k:{'type':'array','items':{'type':'string'}} for k in LISTAS}}}}}}


def solicitud_completa(resumen,formato,area,contexto,ajustes,aliases,evidencias):
    if formato not in ('XXIII','XXV'):raise ValueError('Esta generación corresponde a la planeación trimestral; el plan anual conserva su propio formato.')
    if not str(resumen).strip() or len(resumen)>12000:raise ValueError('Revisa el resumen educativo antes de generar.')
    fuentes=[{k:f[k] for k in ('id','titulo','organismo','edicion') if k in f} for f in contexto.get('fuentes',[])]
    datos={'resumen_educativo_revisado':resumen,'funcion':area,'anexo':formato,
       'alumnos_anonimos':list(aliases),'referentes':contexto.get('referentes_por_grado',[]),
       'adaptaciones_docentes':contexto.get('adaptaciones_docentes',{}),
       'campo':contexto.get('campo',contexto.get('campos',{})),'ejes':contexto.get('ejes',{}),
       'guia_local':contexto.get('guia_local',''),'fuentes':fuentes,'evidencias':evidencias,
       'configuracion':{k:ajustes[k] for k in ('duracion','sesiones','dias','enfoque','apoyos') if k in ajustes},
       'contextos_admitidos':FORMATOS[formato]['contextos']}
    reglas='''Prepara el borrador completo de planeación trimestral, no solo ideas sueltas.
Devuelve hasta ocho unidades o secuencias distintas, para dosificar localmente en las
sesiones configuradas. Cada unidad tiene inicio, desarrollo y cierre en pasos cortos,
objetivo observable, descriptor, apoyos, recursos accesibles y evaluación formativa:
instrumento sencillo, qué observar y cuándo. Identifica destinatarios solo con los alias.
Cita al menos una evidencia educativa y una fuente normativa incluidas por unidad.
Si hay PDA elegidos, vincula identificadores suministrados; no inventes otros.
Las evidencias indican qué se registró, no que el alumno logró un objetivo futuro.
No conviertas BAP en diagnósticos. No rellenes resultados, situación final, firmas,
aprobaciones, entregas a familias o acuerdos que no ocurrieron.
Respeta la duración y apoyos configurados. No asignes fechas: se calculan localmente.
Para Psicología, propone las cinco competencias emocionales y al menos una unidad
en aula regular cuando la evidencia permita sostenerlas. No fabriques necesidades
para cubrirlas: indica en faltantes lo que requiere confirmación. Las competencias
son conciencia emocional, regulación emocional, autonomía emocional, competencia
social y habilidades de vida y bienestar. Incluye una sugerencia prevista para familia.
Comunicación trabaja acceso a expresión, comprensión y participación documentadas.
Trabajo Social describe barreras del entorno y acciones en aula, escuela, familia y
comunidad; no responsabiliza a la familia ni sustituye atención clínica o currículo.
Si falta información para una unidad, no la inventes. Puedes devolver unidades vacías
y hasta tres preguntas concretas. No copies ejemplos del manual como hechos del alumno.
La estructura de esta solicitud sustituye la estructura JSON de propuestas rápidas.
Devuelve solo observaciones, faltantes, sugerencia_familia y unidades. Cada unidad
incluye los campos de texto necesidad, objetivo, descriptor, actividad, contexto,
apoyos, recursos, evaluacion, fundamento; y listas evidencias, fuentes, referentes,
destinatarios y competencias. competencias queda vacía fuera de Psicología.
'''
    reglas+='\nPara esta configuración devuelve como máximo '+str(min(8,int(ajustes['sesiones'])))+' unidades.\n'
    return INSTRUCCIONES.split('Devuelve solo JSON')[0]+'\n'+reglas+'\nDATOS DE CONSULTA:\n'+json.dumps(datos,ensure_ascii=False,sort_keys=True)


def huella_completa(*args):
    return hashlib.sha256((VERSION+'\n'+solicitud_completa(*args)).encode()).hexdigest()


def validar_completa(data,formato,area,contexto,aliases,evidencias):
    if not isinstance(data,dict) or not isinstance(data.get('unidades'),list) or len(data['unidades'])>8:
        raise ValueError('La planeación llegó sin una estructura válida.')
    fuentes={f['id'] for f in contexto.get('fuentes',[])}
    referentes={r['id'] for r in contexto.get('referentes_por_grado',[])}
    resultado=[]
    for u in data['unidades']:
        if not isinstance(u,dict) or any(not isinstance(u.get(k),str) or not u[k].strip() or len(u[k])>4000 for k in CAMPOS):
            raise ValueError('Una actividad llegó incompleta.')
        if any(not isinstance(u.get(k),list) or any(not isinstance(v,str) for v in u[k]) for k in LISTAS):raise ValueError('Referencias de actividad inválidas.')
        for campo,permitidos,obligatorio in [('evidencias',set(evidencias),True),('fuentes',fuentes,True),('referentes',referentes,bool(referentes)),('destinatarios',set(aliases),True),('competencias',set(COMPETENCIAS),False)]:
            if not set(u[campo]).issubset(permitidos) or (obligatorio and not u[campo]):raise ValueError('La actividad no tiene un vínculo verificable: '+campo)
        if u['contexto'] not in FORMATOS[formato]['contextos']:raise ValueError('Contexto no permitido para este formato.')
        if isinstance(evidencias,dict):
            documentados={a for ref in u['evidencias'] for a in evidencias.get(ref,[])}
            if not set(u['destinatarios'])<=documentados:raise ValueError('La evidencia de otro alumno no sustenta esta actividad.')
        if area!='Psicología' and u['competencias']:raise ValueError('Se trasladaron competencias exclusivas de Psicología a otra función.')
        resultado.append({**{k:u[k].strip() for k in CAMPOS},**{k:list(dict.fromkeys(u[k])) for k in LISTAS}})
    faltantes=data.get('faltantes',[])
    if not isinstance(faltantes,list):raise ValueError('Preguntas de confirmación no válidas.')
    observaciones=str(data.get('observaciones',''))[:2000]
    if not resultado and not (faltantes or observaciones.strip()):raise ValueError('Respuesta vacía.')
    return {'unidades':resultado,'observaciones':observaciones,'faltantes':[str(f)[:500] for f in faltantes[:3]],'sugerencia_familia':str(data.get('sugerencia_familia',''))[:3000]}


def generar_completa(resumen,formato,area,contexto,ajustes,aliases,evidencias):
    from ai.planeacion import proponer
    prompt=solicitud_completa(resumen,formato,area,contexto,ajustes,aliases,evidencias)
    return proponer(resumen,formato,area,curriculo=contexto,_prompt=prompt,_schema=SCHEMA,
        _max_tokens=6000,_validador=lambda data:validar_completa(data,formato,area,contexto,aliases,evidencias))

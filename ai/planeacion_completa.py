"""Contrato de generación del borrador completo; sin datos identificadores."""
import hashlib
import json
from copy import deepcopy
from ai.planeacion_prompt import INSTRUCCIONES
from services.planeacion_modelo import FORMATOS
from services.planeacion_equipo import COMPETENCIAS

VERSION='planeacion-completa-2026-10-21-v5'
CAMPOS=('necesidad','objetivo','descriptor','actividad','contexto','apoyos','recursos','evaluacion','fundamento')
LISTAS=('evidencias','fuentes','referentes','destinatarios','competencias')


class RespuestaInvalida(ValueError):
    def __init__(self,mensaje,motivo):
        super().__init__(mensaje);self.motivo=motivo
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
       'contextualizacion_docente':contexto.get('contextualizacion_docente',''),
       'actividades_previas_para_no_repetir':contexto.get('actividades_previas',[]),
       'configuracion':{k:ajustes[k] for k in ('duracion','sesiones','dias','enfoque','apoyos') if k in ajustes},
       'contextos_admitidos':FORMATOS[formato]['contextos']}
    reglas='''Prepara el borrador completo de planeación trimestral, no solo ideas sueltas.
Devuelve hasta ocho unidades o secuencias distintas, para dosificar localmente en las
sesiones configuradas. Identifica destinatarios solo con los alias.
Cita al menos una evidencia educativa y una fuente normativa incluidas por unidad.
Vincula cada destinatario con evidencia propia: si una evidencia documenta a un
solo alias, dirige esa actividad únicamente a ese alias. Una actividad para varios
alumnos requiere evidencia proporcionada para cada uno. No extrapoles ni atribuyas
a otro alumno la evidencia individual de alguien más.

CRITERIOS PEDAGÓGICOS FUNDAMENTALES (ZONA DE DESARROLLO PRÓXIMO):
1. NUNCA equipares diagnóstico clínico, condición o grado administrativo con nivel de desempeño.
   Si el alumno está en 4°, 5° o 6° pero presenta habilidades iniciales de lectoescritura
   (presilábico, silábico) o cálculo (conteo 1 a 10), calibra la actividad a su nivel real
   de ejecución con mediación concreta, adaptando la temática a su edad cronológica (temas dignos
   y de su interés; NO infantilices).
2. ESTRUCTURA CONCRETA DE CADA ACTIVIDAD ('actividad'):
   - Inicio (5-10 min): activación visual, modelado o anticipación de la tarea.
   - Desarrollo (20-25 min): mediación docente paso a paso con andamiaje (material manipulable,
     apoyos gráficos, preguntas guía o instrucciones segmentadas).
   - Cierre (10 min): demostración práctica y observable del avance.
   - Variante multinivel: indica brevemente una opción de apoyo (si hay dificultad) y una de reto (si consolida rápido).
3. RECURSOS ACCESIBLES ('recursos'):
   Utiliza exclusivamente materiales cotidianos del aula y de la escuela (tarjetas, pizarrón, cuadernos,
   fichas de conteo, imágenes). Evita recursos costosos, tecnológicos o inaccesibles.
4. DESCRIPTOR DE LOGRO ('descriptor'):
   Redacta con verbos observables en presente (señala, clasifica, asocia, comunica, resuelve con apoyo).
   Evita verbos teóricos o abstractos como 'comprenderá' o 'conocerá'.
5. CONTINUIDAD PEDAGÓGICA Y VARIEDAD:
   No copies ni reformules superficialmente las actividades previas suministradas.
   Cada unidad nueva debe cambiar la tarea observable, la dinámica o el producto,
   manteniendo los apoyos y objetivos que requieran continuidad según la evidencia.
   No basta cambiar nombres, materiales o verbos. No repitas unidades dentro de la respuesta.
   Si no hay datos para justificar una progresión, propón una exploración diferente,
   declárala propuesta y solicita confirmación; nunca inventes logros ni intereses.
   Aprovecha los antecedentes y actividades previas registradas para dar seguimiento a los objetivos
   iniciados; no repitas mecánicamente lo ya superado ni des saltos curriculares descontextualizados.

Si hay PDA elegidos, vincula identificadores suministrados; no inventes otros.
Las evidencias indican qué se registró, no que el alumno logró un objetivo futuro.
No conviertas BAP en diagnósticos. No rellenes resultados, situación final, firmas,
aprobaciones, entregas a familias o acuerdos que no ocurrieron.
Respeta la duración y apoyos configurados. No asignes fechas: se calculan localmente.
Contextualiza en el programa analítico, lengua, intereses, fortalezas, comunidad y
recursos documentados. El contexto escolar no demuestra una necesidad individual.
Respeta el codiseño y las decisiones docentes: tus propuestas son editables, no mandatos.
Para Psicología, propone las cinco competencias emocionales y al menos una unidad
en aula regular cuando la evidencia permita sostenerlas. No fabriques necesidades
para cubrirlas: indica en faltantes lo que requiere confirmación. Las competencias
son conciencia emocional, regulación emocional, autonomía emocional, competencia
social y habilidades de vida y bienestar. Incluye una sugerencia prevista para familia.
Comunicación trabaja acceso a expresión, comprensión y participación documentadas.
Trabajo Social describe barreras del entorno y acciones en aula, escuela, familia y
comunidad; no responsabiliza a la familia ni sustituye atención clínica o currículo.
Si falta información diagnóstica esencial para una unidad, no la inventes. Propón una
actividad de exploración formativa e indica en faltantes hasta tres preguntas de confirmación.
No copies ejemplos del manual como hechos del alumno.
La estructura de esta solicitud sustituye la estructura JSON de propuestas rápidas.
Devuelve solo observaciones, faltantes, sugerencia_familia y unidades. Cada unidad
incluye los campos de texto necesidad, objetivo, descriptor, actividad, contexto,
apoyos, recursos, evaluacion, fundamento; y listas evidencias, fuentes, referentes,
destinatarios y competencias. competencias queda vacía fuera de Psicología.
'''
    limite=min(8,int(ajustes['sesiones']),max(6 if area=='Psicología' else 3,len(aliases)))
    reglas+='\nPara esta configuración devuelve como máximo '+str(limite)+' unidades. '
    reglas+='Sé conciso: actividad hasta 1100 caracteres y los demás textos hasta 300 cada uno. No repitas antecedentes completos ni tablas normativas; usa sus identificadores.\n'
    return INSTRUCCIONES.split('Devuelve solo JSON')[0]+'\n'+reglas+'\nDATOS DE CONSULTA:\n'+json.dumps(datos,ensure_ascii=False,sort_keys=True)


def huella_completa(*args):
    return hashlib.sha256((VERSION+'\n'+solicitud_completa(*args)).encode()).hexdigest()


def validar_completa(data,formato,area,contexto,aliases,evidencias):
    if not isinstance(data,dict) or not isinstance(data.get('unidades'),list) or len(data['unidades'])>8:
        raise RespuestaInvalida('La planeación llegó sin una estructura válida.','EstructuraInvalida')
    fuentes={f['id'] for f in contexto.get('fuentes',[])}
    referentes={r['id'] for r in contexto.get('referentes_por_grado',[])}
    resultado=[]
    for u in data['unidades']:
        if not isinstance(u,dict) or any(not isinstance(u.get(k),str) or not u[k].strip() or len(u[k])>4000 for k in CAMPOS):
            raise RespuestaInvalida('Una actividad llegó incompleta.','CamposIncompletos')
        if any(not isinstance(u.get(k),list) or any(not isinstance(v,str) for v in u[k]) for k in LISTAS):raise RespuestaInvalida('Referencias de actividad inválidas.','ReferenciasInvalidas')
        for campo,permitidos,obligatorio in [('evidencias',set(evidencias),True),('fuentes',fuentes,True),('referentes',referentes,bool(referentes)),('destinatarios',set(aliases),True),('competencias',set(COMPETENCIAS),False)]:
            if not set(u[campo]).issubset(permitidos) or (obligatorio and not u[campo]):raise RespuestaInvalida('La actividad no tiene un vínculo verificable: '+campo,'Vinculo_'+campo)
        if u['contexto'] not in FORMATOS[formato]['contextos']:raise RespuestaInvalida('Contexto no permitido para este formato.','ContextoInvalido')
        if isinstance(evidencias,dict):
            documentados={a for ref in u['evidencias'] for a in evidencias.get(ref,[])}
            if not set(u['destinatarios'])<=documentados:raise RespuestaInvalida('La evidencia de otro alumno no sustenta esta actividad.','EvidenciaAjena')
        if area!='Psicología' and u['competencias']:raise RespuestaInvalida('Se trasladaron competencias exclusivas de Psicología a otra función.','FuncionInvalida')
        from services.planeacion_variedad import repetida
        previas=contexto.get('actividades_previas',[])+[r['actividad'] for r in resultado]
        if repetida(u['actividad'],previas):raise RespuestaInvalida('La IA repitió una actividad. Se conserva tu planeación; solicita una alternativa.','ActividadRepetida')
        resultado.append({**{k:u[k].strip() for k in CAMPOS},**{k:list(dict.fromkeys(u[k])) for k in LISTAS}})
    faltantes=data.get('faltantes',[])
    if not isinstance(faltantes,list):raise ValueError('Preguntas de confirmación no válidas.')
    observaciones=str(data.get('observaciones',''))[:2000]
    if not resultado and not (faltantes or observaciones.strip()):raise ValueError('Respuesta vacía.')
    return {'unidades':resultado,'observaciones':observaciones,'faltantes':[str(f)[:500] for f in faltantes[:3]],'sugerencia_familia':str(data.get('sugerencia_familia',''))[:3000]}


def generar_completa(resumen,formato,area,contexto,ajustes,aliases,evidencias):
    from ai.planeacion import proponer
    prompt=solicitud_completa(resumen,formato,area,contexto,ajustes,aliases,evidencias)
    schema=deepcopy(SCHEMA)
    unidad=schema['properties']['unidades']['items']['properties']
    unidad['contexto']['enum']=list(FORMATOS[formato]['contextos'])
    permitidos={'evidencias':list(evidencias),'fuentes':[f['id'] for f in contexto.get('fuentes',[])],
        'referentes':[r['id'] for r in contexto.get('referentes_por_grado',[])],
        'destinatarios':list(aliases),'competencias':list(COMPETENCIAS) if area=='Psicología' else []}
    for campo,values in permitidos.items():
        if values:unidad[campo]['items']['enum']=values
        else:unidad[campo]['maxItems']=0
    return proponer(resumen,formato,area,curriculo=contexto,_prompt=prompt,_schema=schema,
        _max_tokens=6000,_validador=lambda data:validar_completa(data,formato,area,contexto,aliases,evidencias))


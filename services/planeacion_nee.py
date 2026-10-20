"""NEE breves: prioridad docente, EPP revisada o hipótesis educativa revisable.

Manual USAER, pp. impresas 4, 64 y 168-169. BAPSE es contexto, no NEE.
Este módulo no consulta red, no diagnostica ni escribe en el padrón.
"""
import json
import re
from utils.text import normalizar_texto


def es_bapse(f):
    return normalizar_texto(f.get('tipo','')) in {'III','ANEXO3','BAPSE'} or bool(re.search(r'BAP_(?:Fisicas|Actitudinales|Pedagogicas|Organizativas)|[\"\'](?:pregunta|frecuencia|orientacion)[\"\']\s*:',str(f.get('texto','')),re.I))


def nee_padron(alumno):
    for key,value in alumno.items():
        label=re.sub(r'^\d+[.\- ]*','',normalizar_texto(key).replace('_',' ')).strip()
        if label in {'NEE','NEE REGISTRADA','NEE PROPUESTA','NECESIDADES EDUCATIVAS ESPECIFICAS','NECESIDAD EDUCATIVA ESPECIFICA','NECESIDADES EDUCATIVAS ESPECIALES'}:
            if isinstance(value,list):value='\n'.join(str(v.get('NEE','')) if isinstance(v,dict) else str(v) for v in value)
            text=str(value or '').strip()
            if not es_bapse({'texto':text}) and normalizar_texto(text) not in {'','NAN','NONE','POR DEFINIR','PENDIENTE','NO REGISTRADA','SIN REGISTRO'}:return text
    return ''


def redactar_nee(text):
    lines=[]
    for line in str(text).splitlines():
        line=line.strip(' •-\t')
        if not line:continue
        if re.match(r'^necesita\b',line,re.I):lines.append(line)
        elif re.match(r'^(fortalecer|desarrollar|adquirir|consolidar|mejorar|incrementar|comprender|reconocer|expresar|regular|resolver|comunicar|ampliar)\b',line,re.I):lines.append('Necesita '+line[0].lower()+line[1:])
        else:lines.append('Necesita fortalecer '+line[0].lower()+line[1:])
    return '\n'.join(lines)


def propuesta_logro(nee):
    """Objetivo y descriptor iniciales revisables; no son logros observados."""
    texto=normalizar_texto(nee)
    if any(t in texto for t in ('LECTURA','TEXTOS','LEER')):
        return 'Comprender información de un texto breve.','El alumno identifica información de un texto leído o escuchado y comunica una idea.'
    if 'ESCRIT' in texto:
        return 'Elaborar un mensaje con una intención comunicativa.','El alumno produce y comparte un mensaje mediante escritura o apoyos accesibles.'
    if any(t in texto for t in ('NUMERO','CANTIDAD','CONTEO')):
        return 'Relacionar cantidades con sus representaciones.','El alumno representa una cantidad con objetos, imágenes o números.'
    if any(t in texto for t in ('COMUNICACION','VOCABULARIO')):
        return 'Comunicar una elección o necesidad en una situación cotidiana.','El alumno expresa una elección o petición por un medio accesible.'
    if any(t in texto for t in ('EMOCION','AUTORREGULACION')):
        return 'Reconocer una emoción y elegir una estrategia de regulación.','El alumno identifica una emoción y elige una alternativa de respuesta.'
    return 'Comprender y realizar una consigna en una actividad breve.','El alumno sigue una consigna y realiza la acción solicitada con los apoyos previstos.'


def necesidad(alumno,fuentes,referentes,area):
    registrada=nee_padron(alumno)
    if registrada:return redactar_nee(registrada),{'origen':'padrón docente','propuesta':False,'original':registrada}
    for f in fuentes:
        if f.get('tipo')!='EPP' or f.get('parte')!='Conclusión':continue
        try:data=json.loads(f['texto'])
        except (ValueError,TypeError):continue
        rows=data.get('NEE',[]) if isinstance(data,dict) else []
        nee='\n'.join(str(r.get('NEE','')).strip() for r in rows if isinstance(r,dict) and str(r.get('NEE','')).strip())
        if nee and not es_bapse({'texto':nee}):return redactar_nee(nee),{'origen':'EPP revisada','referencia':f.get('referencia',''),'propuesta':False}
    datos=normalizar_texto(' '.join(f.get('texto','') for f in fuentes if not es_bapse(f))+' '+' '.join(r.get('contenido','') for r in referentes))
    propuestas=[]
    reglas=[(('LECTURA','LEER','LECTO'),'fortalecer la comprensión de textos'),
            (('ESCRIT','LECTO'),'desarrollar la escritura de mensajes significativos'),
            (('NUMER','CONTEO','CANTIDAD'),'desarrollar el concepto de número'),
            (('SUMA','RESTA','OPERACION'),'fortalecer la resolución de problemas de adición y sustracción'),
            (('ATENCION','CONSIGNA'),'fortalecer la atención sostenida y la comprensión de consignas'),
            (('EMOCION','REGULACION','CONVIVENCIA'),'desarrollar la identificación de emociones y estrategias de autorregulación'),
            (('COMUNICACION','EXPRESION','EXPRESAR'),'desarrollar la comunicación funcional')]
    for tokens,text in reglas:
        if any(t in datos for t in tokens):propuestas.append('Necesita '+text+'.')
    if not propuestas:
        text={'Psicología':'desarrollar estrategias de autorregulación',
              'Comunicación':'desarrollar la comunicación funcional'}.get(area,'fortalecer la comprensión de consignas')
        propuestas=['Necesita '+text+'.']
    return '\n'.join(propuestas[:3]),{'origen':'hipótesis educativa para valoración docente' if datos else 'hipótesis inicial sin hallazgos suficientes; valorar antes de mantener',
        'propuesta':True,'manual':'SEGEY-USAER · pp. 64 y 168-169','referencias':[f.get('referencia','') for f in fuentes if not es_bapse(f)]}


def resumir_plan_previo(plan):
    """Resumen pedagógico breve de un plan previo para dar continuidad sin saturar tokens."""
    lineas=[]
    formato=plan.get('formato','XXIII')
    lineas.append(f"Planeación anterior ({formato}):")
    necesidades=str(plan.get('metadatos',{}).get('necesidades_confirmadas','')).strip()
    if necesidades:
        lineas.append('Necesidades previas: '+necesidades[:250])
    tablas=plan.get('tablas',{})
    for k in ('aprendizajes','barreras','necesidades'):
        for fila in tablas.get(k,[])[:3]:
            obj=fila.get('Aprendizaje y/u objetivo') or fila.get('Aprendizajes y/u Objetivos','')
            if obj:lineas.append('Objetivo previo: '+str(obj)[:200])
            apoyos=fila.get('Apoyos o ajustes') or fila.get('Apoyos y/o ajustes razonables','')
            if apoyos:lineas.append('Apoyos previos: '+str(apoyos)[:200])
    for fila in tablas.get('dosificacion',[])[:3]:
        act=fila.get('Actividades','')
        if act:lineas.append('Actividad previa: '+str(act)[:250])
    for s in plan.get('metadatos',{}).get('equipo',{}).get('sesiones',[])[:3]:
        if s.get('actividad'):lineas.append('Actividad previa: '+str(s.get('actividad'))[:250])
    return '\n'.join(lineas) if len(lineas)>1 else f"Planeación anterior ({formato}) registrada sin detalle de actividades."

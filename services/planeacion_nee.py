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
            if normalizar_texto(text) not in {'','NAN','NONE','POR DEFINIR','PENDIENTE','NO REGISTRADA','SIN REGISTRO'}:return text
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


def necesidad(alumno,fuentes,referentes,area):
    registrada=nee_padron(alumno)
    if registrada:return redactar_nee(registrada),{'origen':'padrón docente','propuesta':False,'original':registrada}
    for f in fuentes:
        if f.get('tipo')!='EPP' or f.get('parte')!='Conclusión':continue
        try:data=json.loads(f['texto'])
        except (ValueError,TypeError):continue
        rows=data.get('NEE',[]) if isinstance(data,dict) else []
        nee='\n'.join(str(r.get('NEE','')).strip() for r in rows if isinstance(r,dict) and str(r.get('NEE','')).strip())
        if nee:return redactar_nee(nee),{'origen':'EPP revisada','referencia':f.get('referencia',''),'propuesta':False}
    datos=normalizar_texto(' '.join(f.get('texto','') for f in fuentes if not es_bapse(f))+' '+' '.join(r.get('contenido','') for r in referentes))
    propuestas=[]
    reglas=[(('LECTURA','LEER','LECTO'),'fortalecer la comprensión de textos y la expresión de ideas sobre lo leído'),
            (('ESCRIT','LECTO'),'desarrollar la escritura de mensajes significativos'),
            (('NUMER','CONTEO','CANTIDAD'),'desarrollar el concepto de número y la relación entre cantidades y representaciones'),
            (('SUMA','RESTA','OPERACION'),'fortalecer la resolución de problemas de adición y sustracción'),
            (('ATENCION','CONSIGNA'),'fortalecer la atención y la comprensión de consignas en las actividades escolares'),
            (('EMOCION','REGULACION','CONVIVENCIA'),'desarrollar la identificación de emociones y estrategias de autorregulación'),
            (('COMUNICACION','EXPRESION','EXPRESAR'),'desarrollar la comunicación funcional para expresar elecciones, necesidades e ideas')]
    for tokens,text in reglas:
        if any(t in datos for t in tokens):propuestas.append('Necesita '+text+'.')
    if not propuestas:
        text={'Psicología':'desarrollar estrategias de autorregulación y participación en las actividades escolares',
              'Comunicación':'desarrollar la comunicación funcional para expresar elecciones, necesidades e ideas'}.get(area,'fortalecer la comprensión de consignas y la expresión de respuestas durante las actividades de aprendizaje')
        propuestas=['Necesita '+text+'.']
    return '\n'.join(propuestas[:3]),{'origen':'hipótesis educativa para valoración docente' if datos else 'hipótesis inicial sin hallazgos suficientes; valorar antes de mantener',
        'propuesta':True,'manual':'SEGEY-USAER · pp. 64 y 168-169','referencias':[f.get('referencia','') for f in fuentes if not es_bapse(f)]}

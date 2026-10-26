"""Entradas educativas de EPP: datos registrados y hallazgos, nunca puntuaciones inferidas."""
from copy import deepcopy
from datetime import date, datetime
import hashlib
import json
from services.epp_modelo import GENERALES

def texto(value):
    if value is None: return ''
    result=str(value).strip()
    return '' if result.lower() in {'nan','nat','none','<na>'} else result

def datos_registrados(alumno):
    aliases={
        'Fecha de nacimiento': ('Fecha_Nacimiento','Fecha de nacimiento'),
        'Domicilio': ('Domicilio_Alumno','Domicilio'),
        'Nombre de la madre': ('Nombre_Madre','Nombre de la madre'),
        'Nombre del padre': ('Nombre_Padre','Nombre del padre'),
        'Nombre del maestro/a': ('Docente_Regular','Nombre_Maestro_Regular'),
    }
    result={field:texto(alumno.get(field)) for field in GENERALES if texto(alumno.get(field))}
    for field,keys in aliases.items():
        for key in keys:
            if texto(alumno.get(key)):
                result[field]=texto(alumno[key]);break
    birth=result.get('Fecha de nacimiento','')
    for fmt in ('%Y-%m-%d','%d/%m/%Y'):
        try:
            born=datetime.strptime(birth,fmt).date();today=date.today()
            if born<=today:
                age=today.year-born.year-((today.month,today.day)<(born.month,born.day))
                result['Edad']=f'{age} años (al {today.isoformat()})'
            break
        except ValueError: pass
    if 'Edad' not in result and texto(alumno.get('Edad_1_Septiembre')):
        result['Edad']=texto(alumno['Edad_1_Septiembre'])+' años (referencia del padrón al 1 de septiembre; confirmar ciclo)'
    return result

def datos_entrevista(doc):
    """Solo etiquetas explícitas y registros estructurados; no inferir datos familiares."""
    import re
    import unicodedata
    def norm(s):
        return ''.join(c for c in unicodedata.normalize('NFD',s.casefold()) if unicodedata.category(c)!='Mn').strip()
    fields={norm(f):f for f in GENERALES}
    result={}
    ts=(doc or {}).get('partes',{}).get('Trabajo Social',{}).get('contenido',{})
    for evaluation in ts.get('evaluaciones',[]):
        if 'entrevista' not in norm(str(evaluation.get('nombre',''))):continue
        for line in str(evaluation.get('texto','')).splitlines():
            pair=re.split(r'\s*:\s*',line,maxsplit=1)
            if len(pair)==2 and norm(pair[0]) in fields and texto(pair[1]):
                result[fields[norm(pair[0])]]=texto(pair[1])[:1000]
    for row in ts.get('familia',[]):
        parent={'madre':'madre','padre':'padre'}.get(norm(str(row.get('Parentesco',''))))
        if not parent:continue
        for col,label in [('Nombre','Nombre'),('Edad','Edad'),('Escolaridad','Escolaridad')]:
            if texto(row.get(col)):result[f'{label} de la {parent}' if parent=='madre' else f'{label} del {parent}']=texto(row[col])
    return result

def precargar(value, alumno, doc=None):
    result=deepcopy(value)
    generales=result.setdefault('generales',{})
    edited=set(result.get('generales_editados',[]))
    origins=result.setdefault('origen_generales',{})
    interview=datos_entrevista(doc)
    if interview.get('Fecha de nacimiento') and not interview.get('Edad'):
        derived=datos_registrados({'Fecha de nacimiento':interview['Fecha de nacimiento']})
        if derived.get('Edad'):interview['Edad']=derived['Edad']
    for field,text in {**datos_registrados(alumno),**interview}.items():
        source='Entrevista de Trabajo Social; verificar con la familia.' if field in interview else 'Registro autorizado del alumno; verificar al revisar la EPP.'
        if field not in edited and (not generales.get(field) or field in interview and origins.get(field,'').startswith(('Registro autorizado','Entrevista de Trabajo Social'))):
            generales[field]=text
            origins[field]=source
    return result

def huella_instrumentos(doc, area, value):
    source=({a:doc['partes'].get(a,{}).get('revision','') for a in
             ('Aprendizaje','Psicología','Comunicación','Trabajo Social')}
            if area=='Conclusión' else value.get('evaluaciones',[]))
    return hashlib.sha256(json.dumps(source,ensure_ascii=False,sort_keys=True).encode()).hexdigest()

def entrada_directa(draft):
    name=texto(draft.get('Instrumento o técnica aplicada'))
    when=texto(draft.get('Fecha de aplicación (AAAA-MM-DD)'))
    findings=texto(draft.get('Resultados y observaciones documentadas'))
    if not name or not findings:raise ValueError('Indica el instrumento o técnica y sus resultados observados.')
    try: datetime.strptime(when,'%Y-%m-%d')
    except ValueError:raise ValueError('Indica una fecha válida con formato AAAA-MM-DD.')
    body='\n'.join(k+': '+texto(v) for k,v in draft.items() if texto(v))
    if len(body)>12000:raise ValueError('Resume los hallazgos a un máximo de 12000 caracteres.')
    digest=hashlib.sha256(('DIRECTO|'+body).encode()).hexdigest()
    return {'id':digest,'nombre':name,'fecha':when,'texto':body,'entrada':'DIRECTO'}

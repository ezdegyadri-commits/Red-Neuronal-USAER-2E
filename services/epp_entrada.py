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

def precargar(value, alumno):
    result=deepcopy(value)
    generales=result.setdefault('generales',{})
    edited=set(result.get('generales_editados',[]))
    origins=result.setdefault('origen_generales',{})
    for field,text in datos_registrados(alumno).items():
        if field not in edited and not generales.get(field):
            generales[field]=text
            origins[field]='Registro autorizado del alumno; verificar al revisar la EPP.'
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

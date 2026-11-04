"""Una solicitud contextual; permisos y mezcla por campo, nunca por informe completo."""
from copy import deepcopy
import hashlib
import json
import re
from services.epp_modelo import AREAS, campos, vacia, validar_parte, NEE, BAP
from services.epp_colaborativa import puede, omitido


def contenido(doc, area):
    value=vacia(area)
    value.update(deepcopy(doc.get('partes',{}).get(area,{}).get('contenido',{})))
    return value


def destinos(doc, actor, coordinadora=False, objetivo=None):
    result=[]
    for area in (*AREAS,'Conclusión'):
        value=contenido(doc,area)
        for campo in campos(area):
            autorizado=(area=='Conclusión' and coordinadora and not actor.get('director')) or puede(actor,area,'campos',campo)
            if not autorizado or omitido(value,campo):continue
            if objetivo is not None and (area,campo)!=tuple(objetivo):continue
            if objetivo is None and str(value['campos'].get(campo,'')).strip():continue
            result.append((area,campo))
    if objetivo is not None and not result:raise PermissionError('Este apartado no está habilitado para tu función o está marcado No se requiere.')
    return result


def _limpiar(text, privados):
    text=str(text or '')
    for token in sorted(set(str(x) for x in privados if x),key=len,reverse=True):
        text=re.sub(r'(?<!\w)'+re.escape(token)+r'(?!\w)','[dato retirado]',text,flags=re.I)
    text=re.sub(r'\b[A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]\d\b','[CURP retirada]',text,flags=re.I)
    text=re.sub(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}','[contacto retirado]',text)
    return re.sub(r'(?<!\d)(?:\+?52[\s-]*)?(?:\d[\s()-]*){10}(?!\d)','[contacto retirado]',text)


def preparar(doc, objetivo=None, ideas=''):
    from services import epp as s
    actor=s.autorizar(doc)
    coord=s.es_coordinadora(doc)
    targets=destinos(doc,actor,coord,objetivo)
    alumno=s.alumno_autorizado(doc['alumno'])
    privados=[v for k,v in alumno.items() if any(x in k.lower() for x in ('nombre','curp','domicilio','direccion','telefono','correo','id_')) and v]
    for part in doc['partes'].values():
        privados.append(part.get('autor',''))
        privados.extend(v for k,v in part.get('contenido',{}).get('generales',{}).items() if any(x in k.lower() for x in ('nombre','domicilio')))
        for row in part.get('contenido',{}).get('familia',[]):privados.append(row.get('Nombre',''))
    fuentes=[]
    for area in AREAS:
        v=contenido(doc,area)
        for ev in v.get('evaluaciones',[]):
            if str(ev.get('texto','')).strip():
                fuentes.append({'id':'EV'+str(len(fuentes)+1),'area':area,'instrumento':ev.get('nombre','Evaluación'),
                    'fecha':ev.get('fecha',''),'texto':ev['texto']})
        for campo,texto in v['campos'].items():
            if str(texto).strip() and not omitido(v,campo):
                fuentes.append({'id':'H'+str(len(fuentes)+1),'area':area,'apartado':campo,'texto':texto})
        if str(v.get('sintesis','')).strip():
            fuentes.append({'id':'H'+str(len(fuentes)+1),'area':area,'apartado':'Síntesis','texto':v['sintesis']})
    if ideas.strip():fuentes.append({'id':'IDEAS','area':actor['area'],'texto':ideas.strip()[:3000]})
    if not fuentes:raise ValueError('Incorpora resultados o escribe observaciones en el apartado. No se inventarán hallazgos.')
    datos={'contexto':{k:str(alumno.get(k,'')) for k in ('Edad','Grado','Nivel_Educativo')},'fuentes':fuentes,'destinos':[{'area':a,'campo':c} for a,c in targets]}
    payload=_limpiar(json.dumps(datos,ensure_ascii=False),privados)
    if len(payload)>100000:raise ValueError('Los antecedentes exceden el límite de una solicitud. Resume los resultados de los instrumentos antes de redactar; no se ha enviado información.')
    return {'datos':json.loads(payload),'base':deepcopy(doc),'objetivo':objetivo,'actor':deepcopy(actor),'coordinadora':coord,
        'huella':hashlib.sha256(payload.encode()).hexdigest()}


def validar(resultado, solicitud):
    if not isinstance(resultado,dict) or set(resultado)!={'apartados','nee','bap','faltantes'}:raise ValueError('La propuesta llegó incompleta. El informe permanece intacto.')
    targets={(d['area'],d['campo']) for d in solicitud['datos']['destinos']}
    fuentes={f['id'] for f in solicitud['datos']['fuentes']}
    if not isinstance(resultado['apartados'],list) or len(resultado['apartados'])>len(targets):raise ValueError('Apartados no válidos.')
    seen=set()
    for item in resultado['apartados']:
        if not isinstance(item,dict) or set(item)!={'area','campo','redaccion','fuentes'}:raise ValueError('Apartado incompleto.')
        dest=(item['area'],item['campo'])
        if dest not in targets or dest in seen:raise ValueError('La respuesta incluye apartados ajenos o duplicados.')
        seen.add(dest)
        if not isinstance(item['redaccion'],str) or len(item['redaccion'])>3500:raise ValueError('Redacción no válida.')
        refs=item['fuentes']
        if not isinstance(refs,list) or not refs or any(not isinstance(x,str) or x not in fuentes for x in refs):raise ValueError('La redacción no identifica sus hallazgos de origen.')
    if not isinstance(resultado['faltantes'],list) or len(resultado['faltantes'])>100 or any(not isinstance(x,str) or len(x)>1000 for x in resultado['faltantes']):raise ValueError('Pendientes no válidos.')
    coord=solicitud['coordinadora']
    for name,cols in [('nee',NEE),('bap',BAP)]:
        rows=resultado[name]
        if not isinstance(rows,list) or len(rows)>20 or (rows and not coord):raise ValueError('La conclusión requiere coordinación del equipo.')
        for row in rows:
            if not isinstance(row,dict) or set(row)!=set(cols)|{'fuentes'}:raise ValueError('Tabla no válida.')
            if any(not isinstance(row[c],str) or len(row[c])>1500 for c in cols):raise ValueError('Celda no válida.')
            if not isinstance(row['fuentes'],list) or not row['fuentes'] or any(not isinstance(x,str) or x not in fuentes for x in row['fuentes']):raise ValueError('Tabla sin hallazgos verificables.')
            if name=='nee' and not re.match(r'^(Necesita|Requiere)\s+\w+',row['NEE'],re.I):raise ValueError('La NEE debe expresar una necesidad educativa concreta.')
    return deepcopy(resultado)


def aplicar(actual, solicitud, resultado):
    """Mezcla comparada con la captura al solicitar IA; nunca pisa edición posterior."""
    from services import epp as s
    actor=s.autorizar(actual)
    if actual['id']!=solicitud['base']['id'] or actor['cuenta']!=solicitud['actor']['cuenta']:raise PermissionError('La propuesta corresponde a otro informe o cuenta.')
    r=validar(resultado,solicitud)
    allowed=set(destinos(actual,actor,s.es_coordinadora(actual),solicitud['objetivo']))
    nuevo=deepcopy(actual);modified=set();conflictos=[]
    for item in r['apartados']:
        area,campo=item['area'],item['campo'];v=contenido(nuevo,area);base=contenido(solicitud['base'],area)
        if (area,campo) not in allowed or v['campos'].get(campo,'')!=base['campos'].get(campo,''):
            conflictos.append(area+' · '+campo);continue
        if not item['redaccion'].strip():continue
        v['campos'][campo]=item['redaccion'].strip();v['validada']=False
        v.setdefault('fuentes_redaccion_ia',{})[campo]=item['fuentes']
        nuevo['partes'].setdefault(area,{})['contenido']=v;modified.add(area)
    if solicitud['coordinadora'] and s.es_coordinadora(actual) and any(r[x] for x in ('nee','bap')):
        v=contenido(nuevo,'Conclusión');base=contenido(solicitud['base'],'Conclusión')
        for name,cols,key in [('nee',NEE,'NEE'),('bap',BAP,'Tipo de barrera')]:
            if v[name]!=base[name]:
                if r[name]:conflictos.append('Conclusión · '+name.upper())
                continue
            rows=deepcopy(v[name]);exist={re.sub(r'\s+',' ',str(x.get(key,''))).casefold().strip() for x in rows}
            for row in r[name]:
                ident=re.sub(r'\s+',' ',row[key]).casefold().strip()
                if ident and ident not in exist:
                    rows.append({c:row[c] for c in cols});exist.add(ident)
            if rows!=v[name]:v[name]=rows;v['validada']=False;modified.add('Conclusión')
        if 'Conclusión' in modified:
            v['revisiones_propuesta_ia']={a:actual['partes'].get(a,{}).get('revision','') for a in AREAS}
            nuevo['partes'].setdefault('Conclusión',{})['contenido']=v
    for area in modified:
        v=nuevo['partes'][area]['contenido'];v['pendientes_ia']=r['faltantes']
        nuevo['partes'][area]['contenido']=validar_parte(area,v)
    return nuevo,modified,conflictos

"""Memoria educativa acotada por alumno. No IA, no escrituras ni inferencias clínicas."""
from copy import deepcopy
from datetime import date,datetime
from zoneinfo import ZoneInfo
import hashlib,json,re
from utils.text import normalizar_texto

VERSION='memoria-pedagogica-v1'
PRIORIDAD={'EPP':0,'EPP_ESCANEADA':0,'III':1,'PLAN':1,'SEGUIMIENTO':2,'ACTA':2,'V':2,'IV':3,'DOCUMENTO_REVISADO':3,'DOCENTE':4}
PRIVADOS=re.compile(r'CURP|DOMICILIO|TELEFONO|CONTACTO|FAMILIOGRAMA|COMPOSICION FAMILIAR|NOMBRE (?:DEL|DE LA)|EMBARAZO|PARTO|HISTORIA CLINICA')
TEMAS={'lectura':r'lectur|silab|letras|vocal|consonant|fonolog', 'matematicas':r'conteo|numer|sumar|cantidad|matematic',
       'comunicacion':r'comunica|lenguaje|expresa|instruccion|dialog', 'atencion':r'atencion|distra|concentr',
       'participacion':r'participa|companero|conviven|turnos|familia|escuela'}


def firma(value):return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,default=str).encode()).hexdigest()


def _fragmentos(value):
    if isinstance(value,dict):
        return [x for k,v in value.items() if not PRIVADOS.search(normalizar_texto(k)) for x in _fragmentos(v)]
    if isinstance(value,list):return [x for v in value for x in _fragmentos(v)]
    text=str(value or '').strip()
    if not text:return []
    try:
        parsed=json.loads(text)
        if isinstance(parsed,(dict,list)):return _fragmentos(parsed)
    except (ValueError,TypeError):pass
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+|\n+',text) if s.strip() and not PRIVADOS.search(normalizar_texto(s))]


def _fecha(value):
    try:return date.fromisoformat(str(value)[:10])
    except ValueError:return None


def _categorias(text):
    n=normalizar_texto(text)
    return [label for label,pattern in [('avances',r'AVANZ|AHORA|YA LOGRA|MAYOR PARTICIP'),('fortalezas',r'LOGRA|RECONOCE|PUEDE|FORTALEZA'),
        ('barreras',r'BARRERA|BAP|ENTORNO|AULA|FAMILIA'),('estrategias',r'APOYO|VISUAL|MANIPUL|INSTRUCC|AJUSTE'),
        ('dificultades',r'DIFICULT|NO LOGRA|NO RECONOCE|REQUIERE|NECESITA'),('ineficaces',r'NO FUNCION|NO FUE EFICAZ|SIN MEJORIA|NO FAVOREC')]
        if re.search(pattern,n)] or ['hallazgos']


def _competencias(text):
    n=normalizar_texto(text);result={}
    for skill,pat in [('vocales',r'(?:LAS |TODAS LAS )?VOCALES'),('silabas',r'SILABAS'),('palabras',r'PALABRAS')]:
        if re.search(r'(?:NO|TODAVIA NO|AUN NO) (?:LOGRA |CONSIGUE |PUEDE )?(?:RECONOCER?|COMBINAR|FORMAR?|LEER?|LEE|IDENTIFICA) '+pat,n):result[skill]=False
        elif re.search(r'(?:YA |AHORA )?(?:RECONOCE|FORMA|LEE|IDENTIFICA|COMBINA) '+pat,n):result[skill]=True
    return result


def construir(doc,alumno=None,necesidades=(),hoy=None):
    from services import planeacion as s
    s.autorizar(doc)
    ids={str(a['ID_Alumno']) for a in doc['datos']['Alumnos']}
    if alumno is not None and str(alumno) not in ids:raise PermissionError('El alumno no pertenece a esta planeación autorizada.')
    elegidos={str(alumno)} if alumno is not None else ids
    hoy=hoy or datetime.now(ZoneInfo('America/Mexico_City')).date()
    temas={k for k,p in TEMAS.items() if re.search(p,normalizar_texto(' '.join(necesidades)),re.I)}
    rows=[];vistos=set()
    for f in doc.get('metadatos',{}).get('fuentes',[]):
        ligados=set(str(f.get('alumno','')).split(','))-{''}
        if f.get('tipo') not in PRIORIDAD or not f.get('vinculo_verificado') or not ligados or not ligados<=elegidos:continue
        fecha=_fecha(f.get('fecha',''));dias=(hoy-fecha).days if fecha else None
        temporal='sin_fecha' if dias is None else 'reciente' if 0<=dias<=120 else 'historico' if dias>120 else 'fecha_por_verificar'
        # Nunca atribuir propuestas PLAN a resultados o habilidades adquiridas.
        for fragmento in _fragmentos(f.get('texto',''))[:30]:
            if len(fragmento)<8:continue
            text=s.anonimizar_texto(doc,fragmento)[:700]
            key=(tuple(sorted(ligados)),normalizar_texto(text),f.get('registro',''),f.get('fecha',''))
            if key in vistos:continue
            vistos.add(key)
            ref='M'+firma(key)[:15]
            relacionados=sum(bool(re.search(TEMAS[t],normalizar_texto(text),re.I)) for t in temas)
            rows.append({'id':ref,'alumnos':sorted(ligados),'texto':text,'tipo':f['tipo'],'categorias':_categorias(text),
                'fecha':fecha.isoformat() if fecha else '', 'temporalidad':temporal,'documento':f.get('documento_origen',f.get('registro','')),
                'referencia':f.get('referencia',''),'caracter':'propuesta_anterior' if f['tipo']=='PLAN' else 'registro_documentado',
                '_orden':(temporal!='reciente',-relacionados,-fecha.toordinal() if fecha else 0,PRIORIDAD[f['tipo']])})
    rows.sort(key=lambda r:r['_orden'])
    # Recuperación acotada por alumno y diversidad de fuentes; no transcripción íntegra.
    selected=[];por_alumno={};por_tipo={};caracteres=0
    for r in rows:
        if caracteres+len(r['texto'])>14000 or len(selected)>=32:continue
        if any(por_alumno.get(a,0)>=20 for a in r['alumnos']) or por_tipo.get(r['tipo'],0)>=10:continue
        selected.append({k:v for k,v in r.items() if k!='_orden'});caracteres+=len(r['texto'])
        for a in r['alumnos']:por_alumno[a]=por_alumno.get(a,0)+1
        por_tipo[r['tipo']]=por_tipo.get(r['tipo'],0)+1
    rows=rows[:80]  # Comparación acotada: nunca un recorrido cuadrático de todo el expediente.
    conflicts=[];seen=set()
    for i,a in enumerate(rows):
        if a['caracter']=='propuesta_anterior':continue
        ca=_competencias(a['texto'])
        for b in rows[i+1:]:
            if a['alumnos']!=b['alumnos'] or b['caracter']=='propuesta_anterior':continue
            cb=_competencias(b['texto'])
            for skill in ca.keys()&cb.keys():
                if ca[skill]==cb[skill]:continue
                reciente,anterior=(a,b) if a.get('fecha','')>b.get('fecha','') else (b,a)
                if reciente['temporalidad']=='reciente' and anterior['temporalidad']=='historico':continue
                fr,fa=_fecha(reciente.get('fecha')),_fecha(anterior.get('fecha'))
                if (fr and fa and (fr-fa).days>=7 and 'avances' in reciente['categorias']
                        and _competencias(reciente['texto']).get(skill) is True):continue
                key=(tuple(a['alumnos']),skill)
                if key in seen:continue
                seen.add(key);cid=firma([sorted([a['id'],b['id']]),skill])[:24]
                # Una decisión solo es válida para estas versiones exactas de los fragmentos.
                decision=doc.get('metadatos',{}).get('memoria_decisiones',{}).get(cid,{})
                elegida=decision.get('fuente') if decision.get('fuente') in {a['id'],b['id']} else ''
                conflicts.append({'id':cid,'competencia':skill,'fuentes':[a['id'],b['id']], 'registros':[a,b],
                                  'resuelta':bool(elegida),'actual_confirmada':elegida})
    # Conservar en el contexto los fragmentos en los que se tomó una decisión.
    obligatorios={c['actual_confirmada'] for c in conflicts if c['resuelta']}
    obligadas=[{k:v for k,v in r.items() if k!='_orden'} for r in rows if r['id'] in obligatorios]
    selected=obligadas+[r for r in selected if r['id'] not in obligatorios]
    acotadas=[];caracteres=0
    for r in selected:
        if len(acotadas)>=32 or caracteres+len(r['texto'])>14000:continue
        acotadas.append(r);caracteres+=len(r['texto'])
    selected=acotadas
    faltantes=[]
    if not selected:faltantes.append('Describe el nivel actual y un apoyo que haya funcionado; se tratará como observación docente pendiente, no como EPP confirmada.')
    if selected and not any(r['temporalidad']=='reciente' for r in selected):faltantes.append('Confirmar qué hallazgos históricos siguen describiendo el desempeño actual.')
    if doc.get('metadatos',{}).get('fuentes_pendientes'):faltantes.append('Hay fuentes que no pudieron consultarse; se conserva la última copia disponible.')
    return {'version':VERSION,'alumnos':sorted(elegidos),'hechos':selected,'conflictos':conflicts,'faltantes':faltantes,
            'provisional':bool(faltantes),'huella':firma([selected,conflicts]),'consultado_en':hoy.isoformat()}


def para_ia(doc,memoria,aliases):
    from services import planeacion as s
    s.autorizar(doc)
    reversa={str(v):k for k,v in aliases.items()}
    if not set(memoria['alumnos'])<=set(reversa):raise PermissionError('Contexto de otro alumno.')
    result={'jerarquia':['evidencia individual','referentes oficiales y currículo','instrucciones docentes','conocimiento complementario provisional'],
        'hechos':[{k:v for k,v in r.items() if k not in ('alumnos','documento','referencia')}|{'destinatarios':[reversa[a] for a in r['alumnos']], 'referencia_evidencia':r['referencia'] if re.fullmatch(r'E[0-9]+',r.get('referencia','')) else r['id']} for r in memoria['hechos']],
        'faltantes':memoria['faltantes'],'provisional':memoria['provisional'],
        'decisiones_docentes':[{'competencia':c['competencia'],'actual_confirmada':c['actual_confirmada']} for c in memoria['conflictos'] if c['resuelta']]}
    return result


def resolver(doc,cid,fuente):
    from services import planeacion as s
    s.autorizar(doc,True);memory=construir(doc)
    c=next((c for c in memory['conflictos'] if c['id']==cid),None)
    if not c or fuente not in c['fuentes']:raise ValueError('El conflicto cambió. Revisa los registros actuales.')
    result=deepcopy(doc)
    result['metadatos'].setdefault('memoria_decisiones',{})[cid]={'fuente':fuente,'cuenta':s.identidad()['cuenta'],
        'fecha':datetime.now(ZoneInfo('America/Mexico_City')).isoformat()}
    return result


def alertas_nivel(hechos,actividad):
    """Barreras conservadoras para demandas explícitas incompatibles; no califica al alumno."""
    texto=normalizar_texto(actividad)
    no_lee=any(re.search(r'NO (?:LOGRA |CONSIGUE |PUEDE )?(?:FORMAR?|COMBINAR|RECONOCER?) (?:LAS |TODAS LAS )?(?:SILABAS|LETRAS|VOCALES)',normalizar_texto(h['texto']))
        for h in hechos if h.get('temporalidad')=='reciente' and h.get('caracter')!='propuesta_anterior')
    exigencia=re.search(r'LECTURA AUTONOMA DE (?:TEXTOS|PARRAFOS)|LEER (?:UN |VARIOS )?TEXTO(?:S)? EXTENSO|REDACTAR (?:UN )?ENSAYO|PRODUCIR TEXTOS COMPLEJOS',texto)
    return ['La actividad presupone una lectura o escritura no documentada como adquirida. Reduce la demanda y conserva apoyos.'] if no_lee and exigencia else []

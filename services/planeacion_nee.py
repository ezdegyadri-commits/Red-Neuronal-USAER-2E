"""NEE breves: prioridad docente, EPP revisada o hipótesis educativa revisable.

Manual USAER, pp. impresas 4, 64 y 168-169. BAPSE es contexto, no NEE.
Este módulo no consulta red, no diagnostica ni escribe en el padrón.
"""
import json
import re
from utils.text import normalizar_texto


def es_bapse(f):
    return normalizar_texto(f.get('tipo','')) in {'III','ANEXO3','BAPSE'} or bool(re.search(r'BAP_(?:Fisicas|Actitudinales|Pedagogicas|Organizativas)|[\"\'](?:pregunta|frecuencia|orientacion)[\"\']\s*:',str(f.get('texto','')),re.I))


def es_diagnostico_puro(texto):
    """Detecta si un texto es meramente un diagnóstico clínico o etiqueta médica sin formulación pedagógica."""
    t = normalizar_texto(str(texto or ''))
    if not t:
        return False
    patrones_diagnosticos = [
        r'^(?:DIAGNOSTICO|DX|TRASTORNO|SINDROME|DISCAPACIDAD)\b',
        r'^(?:TDAH|TEA|DI|TIG|F84|F90)\b',
        r'^(?:HIPOACUSIA|CEGUERA|BAJA VISION|PARALISIS CEREBRAL|SINDROME DE DOWN)\b',
        r'^(?:EPILEPSIA|MUTISMO SELECTIVO|ASPERGER)\b'
    ]
    tiene_accion_pedagogica = any(v in t for v in (
        'FORTALECER', 'DESARROLLAR', 'ADQUIRIR', 'CONSOLIDAR', 'MEJORAR',
        'COMPRENDER', 'RECONOCER', 'EXPRESAR', 'REGULAR', 'RESOLVER',
        'COMUNICAR', 'AMPLIAR', 'PARTICIPAR', 'APRENDER', 'APOYO', 'ACCESO'
    ))
    es_patron = any(re.search(p, t) for p in patrones_diagnosticos)
    return es_patron and not tiene_accion_pedagogica


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
    for b in plan.get('metadatos',{}).get('intervenciones_nee',[])[:40]:
        campos=b.get('campos',{})
        for label,key in (('Necesidad previa','NEE'),('Objetivo previo','Aprendizaje y/u objetivo'),('Actividad previa','Actividades')):
            if campos.get(key):lineas.append(label+': '+str(campos[key])[:250])
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


def catalogo_nee_validadas(doc, alumno_id=None):
    """Extrae las NEE estructuradas y validadas de la EPP del alumno para su uso en planeación.

    Garantiza:
    1. Aislamiento estricto por alumno_id (evita confusión entre homónimos).
    2. Filtrado de diagnósticos clínicos puros y BAP.
    3. Normalización pedagógica conforme al manual SEGEY.
    4. Deduplicación conservando orden y trazabilidad.
    """
    alumnos_doc = [str(a.get('ID_Alumno', a) if isinstance(a, dict) else a).strip() for a in doc.get('datos', {}).get('Alumnos', []) if str(a).strip()]
    if alumno_id:
        target_ids = {str(alumno_id.get('ID_Alumno', alumno_id) if isinstance(alumno_id, dict) else alumno_id).strip()}
    else:
        target_ids = set(alumnos_doc)

    fuentes = doc.get('metadatos', {}).get('fuentes', [])
    items = []
    vistos = set()

    for f in fuentes:
        if f.get('tipo') != 'EPP' or f.get('parte') != 'Conclusión':
            continue
        f_alumno = str(f.get('alumno', '')).strip()
        if target_ids and f_alumno not in target_ids:
            continue
        try:
            data = json.loads(f.get('texto', ''))
        except (ValueError, TypeError):
            continue

        rows = data.get('NEE', []) if isinstance(data, dict) else []
        if not isinstance(rows, list):
            continue

        for idx, r in enumerate(rows):
            if not isinstance(r, dict):
                continue
            raw_nee = str(r.get('NEE', '')).strip()
            if not raw_nee or es_bapse({'texto': raw_nee}):
                continue
            if es_diagnostico_puro(raw_nee):
                continue

            texto_nee = redactar_nee(raw_nee)
            norm = normalizar_texto(texto_nee)
            if not norm or norm in vistos:
                continue
            vistos.add(norm)

            items.append({
                'id': f"{f.get('registro', 'EPP')}-NEE-{idx+1}",
                'alumno_id': f_alumno,
                'texto': texto_nee,
                'original': raw_nee,
                'aspectos': str(r.get('Aspectos', '')).strip(),
                'apoyos': str(r.get('Apoyos', '')).strip(),
                'ajustes': str(r.get('Ajustes razonables', '')).strip(),
                'origen': 'EPP validada',
                'referencia': f.get('referencia', 'EPP'),
                'documento_origen': f.get('documento_origen', ''),
                'revision': f.get('revision', ''),
            })

    try:
        from services.planeacion_necesidades import opciones as opciones_necesidades
        doc_opts = opciones_necesidades(doc)
        for r in doc_opts:
            aid = str(r.get('alumno', '')).strip()
            if target_ids and aid not in target_ids:
                continue
            raw_nee = str(r.get('texto', '')).strip()
            if not raw_nee or es_bapse({'texto': raw_nee}) or es_diagnostico_puro(raw_nee):
                continue
            texto_nee = redactar_nee(raw_nee)
            norm = normalizar_texto(texto_nee)
            if not norm or norm in vistos:
                continue
            vistos.add(norm)
            items.append({
                'id': str(r.get('id', '')),
                'alumno_id': aid,
                'texto': texto_nee,
                'original': raw_nee,
                'aspectos': str(r.get('fundamento', '')).strip(),
                'apoyos': '',
                'ajustes': '',
                'origen': 'EPP validada' if r.get('tipo') == 'EPP' else 'EPP escaneada',
                'referencia': str(r.get('referencia', 'EPP')),
                'documento_origen': str(r.get('documento', '')),
                'revision': str(r.get('revision', '')),
            })
    except Exception:
        pass

    # Si no se encontraron en fuentes de EPP, verificar si el padrón docente tiene una NEE registrada
    if not items and doc.get('datos'):
        registrada = nee_padron(doc.get('datos', {}))
        if registrada and not es_diagnostico_puro(registrada):
            texto_nee = redactar_nee(registrada)
            norm = normalizar_texto(texto_nee)
            if norm not in vistos:
                items.append({
                    'id': 'PADRON-NEE-1',
                    'alumno_id': next(iter(target_ids)) if target_ids else '',
                    'texto': texto_nee,
                    'original': registrada,
                    'aspectos': '',
                    'apoyos': '',
                    'ajustes': '',
                    'origen': 'Padrón docente',
                    'referencia': 'Padrón',
                    'documento_origen': '',
                    'revision': '',
                })

    return items


def opciones_nee_validadas(doc, alumno_id=None):
    """Lista de cadenas con las NEE validadas listas para controles de UI (selectbox/multiselect)."""
    return [c['texto'] for c in catalogo_nee_validadas(doc, alumno_id=alumno_id)]

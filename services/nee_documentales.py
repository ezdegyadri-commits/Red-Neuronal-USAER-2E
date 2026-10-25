"""Propuestas locales fundamentadas; ninguna extracción equivale a validación."""
from copy import deepcopy
import re
from uuid import NAMESPACE_URL, uuid5
from utils.text import normalizar_texto

ESTADOS = ('Detectada', 'Validada', 'Descartada')


def clave(texto):
    texto = re.sub(r'^(?:NECESITA|REQUIERE)\s+', '', normalizar_texto(texto))
    return re.sub(r'[^\w]+', ' ', texto).strip()


def identificar(documento, sha, posicion):
    # Posición y documento, no el texto mutable de la necesidad.
    return uuid5(NAMESPACE_URL, f'usaer:nee:{documento}:{sha}:{posicion}').hex


def detectar(texto, documento, sha):
    resultado=[]; vistos=set(); pagina=''; seccion=False
    for i, raw in enumerate(str(texto or '')[:100000].splitlines()):
        linea=re.sub(r'^\s*(?:[•*\-–]|\d+[.)])\s*', '', raw).strip()
        page=re.fullmatch(r'P[áa]gina\s+(\d+)', linea, re.I)
        if page:pagina=page[1];continue
        n=normalizar_texto(linea)
        if n in {'NEE','NECESIDADES EDUCATIVAS ESPECIFICAS','NECESIDADES EDUCATIVAS ESPECIFICAS:'}:
            seccion=True;continue
        if re.match(r'^(DIAGNOSTICO|FORTALEZAS|BAP|BARRERAS|RECOMENDACIONES)\b',n):
            seccion=False;continue
        if re.search(r'\b(EJEMPLO|ILEGIBLE|CURP|DOMICILIO|TELEFONO|CORREO)\b',n):continue
        candidata=re.sub(r'^El (?:alumno|estudiante)\s+', '', linea, flags=re.I)
        explicita=bool(re.match(r'^(Necesita|Requiere)\s+',candidata,re.I))
        if not explicita and not (seccion and re.match(r'^(Fortalecer|Desarrollar|Consolidar|Adquirir|Ampliar|Mejorar)\s+',candidata,re.I)):continue
        if not 4<=len(candidata.split()) or len(candidata)>600 or clave(candidata) in vistos:continue
        vistos.add(clave(candidata))
        resultado.append({'id':identificar(documento,sha,i),'texto':candidata,'fundamento':linea,
            'pagina':pagina,'area':'','estado':'Detectada','origen':'Enunciado explícito' if explicita else 'Sección de NEE',
            'extraida_en':'','validada_en':'','validada_por':''})
        if len(resultado)==40:break
    return resultado


def validar_registros(rows):
    if not isinstance(rows,list) or len(rows)>40:raise ValueError('Revisa hasta 40 propuestas de NEE.')
    result=[];ids=set();validadas=set()
    for row in rows:
        if not isinstance(row,dict):raise ValueError('Propuesta de NEE no válida.')
        r={k:str(row.get(k,'') or '').strip() for k in ('id','texto','fundamento','pagina','area','estado','origen','extraida_en','validada_en','validada_por','alumno','documento','sha256')}
        if not r['texto'] and not r['fundamento']:continue
        if r['estado'] not in ESTADOS:raise ValueError('Elige Detectada, Validada o Descartada para cada NEE.')
        if not 4<=len(r['texto'].split()) or len(r['texto'])>600:raise ValueError('Cada NEE debe ser un enunciado concreto de 4 palabras o más, hasta 600 caracteres.')
        if len(r['fundamento'])>1000 or len(r['area'])>100 or len(r['pagina'])>40:raise ValueError('Resume el fundamento (hasta 1000 caracteres), área y página de origen.')
        if r['estado']=='Validada':
            if len(r['fundamento'])<12 or '[ilegible]' in r['fundamento'].lower():raise ValueError('Una NEE validada requiere un fundamento legible y verificable en la EPP.')
            if clave(r['texto']) in {'apoyo general','mejorar el aprendizaje','apoyo educativo general'}:raise ValueError('Especifica qué necesita aprender o fortalecer el alumno; evita apoyos generales.')
            if clave(r['texto']) in validadas:raise ValueError('Hay NEE validadas repetidas; conserva una y descarta o corrige la otra.')
            validadas.add(clave(r['texto']))
        if r['id'] and r['id'] in ids:raise ValueError('Dos propuestas tienen el mismo identificador. Recupera la revisión guardada.')
        ids.add(r['id']);result.append(r)
    return result


def preparar(rows, documento, sha, alumno, anteriores, cuenta, ahora, base):
    prev={r['id']:r for r in anteriores}
    result=[]
    for i,r in enumerate(validar_registros(rows)):
        r=deepcopy(r)
        if not r['id'] and i<len(anteriores) and all(anteriores[i].get(k)==r[k] for k in ('texto','fundamento','pagina','area','estado')):
            r['id']=anteriores[i]['id']  # Reintento de una fila manual con acuse perdido.
        r['id']=r['id'] or identificar(documento,sha,f'manual:{base}:{i}')
        old=prev.get(r['id'],{})
        # No se acepta identidad, fecha o autoría declarada por el navegador.
        r.update(alumno=alumno,documento=documento,sha256=sha,
            extraida_en=old.get('extraida_en') or ahora,
            origen=old.get('origen') or r['origen'] or 'Propuesta docente')
        mismo=old.get('estado')=='Validada' and all(old.get(k)==r[k] for k in ('texto','fundamento','pagina','area'))
        r['validada_en']=(old.get('validada_en') if mismo else ahora) if r['estado']=='Validada' else ''
        r['validada_por']=(old.get('validada_por') if mismo else cuenta) if r['estado']=='Validada' else ''
        result.append(r)
    return validar_registros(result)

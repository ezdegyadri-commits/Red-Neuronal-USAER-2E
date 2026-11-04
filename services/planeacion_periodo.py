"""Periodos aditivos: ninguna consulta convierte documentos trimestrales."""
from copy import deepcopy
import re


def es_anual(doc):
    return doc.get('metadatos',{}).get('periodicidad')=='anual'


def etiqueta(doc):
    return 'Anual · '+doc['datos']['Curso escolar'] if es_anual(doc) else 'Trimestre '+str(doc['datos']['Trimestre'])


def anual(doc):
    result=deepcopy(doc)
    ciclo=re.fullmatch(r'(\d{4})[-–](\d{4})',str(doc['datos']['Curso escolar']))
    if not ciclo or int(ciclo[2])!=int(ciclo[1])+1:raise ValueError('El ciclo escolar no es válido.')
    if doc.get('revision'):raise ValueError('No se convierte un documento histórico. Abre una planeación anual nueva.')
    result['metadatos']['periodicidad']='anual'
    result['metadatos']['periodos_seguimiento']=[]
    result['datos']['Periodo']=f'{ciclo[1]}-09-01 / {ciclo[2]}-08-31'
    # Trimestre sigue siendo entero por compatibilidad con versiones y anexos;
    # el alcance documental y la identidad anual prevalecen sobre ese campo.
    return result


def agregar_seguimiento(doc,inicio,fin,proposito):
    from datetime import date
    import hashlib
    if not es_anual(doc):raise ValueError('El seguimiento interno corresponde a la planeación anual.')
    desde,hasta=doc['datos']['Periodo'].split(' / ')
    inicio=date.fromisoformat(str(inicio));fin=date.fromisoformat(str(fin))
    if not date.fromisoformat(desde)<=inicio<=fin<=date.fromisoformat(hasta):raise ValueError('El periodo debe quedar dentro del ciclo escolar.')
    proposito=str(proposito).strip()
    if not proposito or len(proposito)>600:raise ValueError('Describe brevemente el propósito del seguimiento.')
    value={'inicio':inicio.isoformat(),'fin':fin.isoformat(),'proposito':proposito}
    value['id']=hashlib.sha256(str(sorted(value.items())).encode()).hexdigest()[:16]
    result=deepcopy(doc);rows=result['metadatos'].setdefault('periodos_seguimiento',[])
    if not any(r['id']==value['id'] for r in rows):rows.append(value)
    return result

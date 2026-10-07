"""EPP colaborativa privada: eventos por área; nunca sobrescribe otras aportaciones."""
from copy import deepcopy
from datetime import datetime
from uuid import uuid4
from zoneinfo import ZoneInfo
import json
import threading
import streamlit as st
from data.google import ensure_headers, retry_google, df_sheet, clear_cache
from services import planeacion as planes
from services.epp_modelo import AREAS, clave, reconstruir, vacia, validar_parte, pendientes
from utils.text import normalizar_texto

HOJA = 'EPP_Versiones'
HEADERS = ['Alumno','Ciclo','Parte','Revision','Anterior','Fecha','Cuenta','Autor','Estado','Contenido']

def actor():
    return planes.identidad()

def puede_crear():
    a = actor()
    return not a['director'] and 'APOYO' in normalizar_texto(a['rol'])

def alumno_autorizado(id_alumno):
    frame = planes.padron_autorizado()
    rows = frame.loc[frame['ID_Alumno'].astype(str).eq(str(id_alumno))] if 'ID_Alumno' in frame else frame
    if len(rows) != 1: raise PermissionError('Alumno fuera de tu matrícula o registro ambiguo.')
    return rows.iloc[0].to_dict()

@st.cache_resource(show_spinner=False)
def control():
    return threading.RLock()

@st.cache_resource(show_spinner=False)
def recientes():
    return {}

@st.cache_resource(ttl=600,show_spinner=False)
def hoja():
    return ensure_headers(HOJA, HEADERS)

def listar(incluir_eliminados=False):
    actor()
    frame = planes.padron_autorizado()
    ids = set(frame['ID_Alumno'].astype(str)) if 'ID_Alumno' in frame else set()
    # No se crea una hoja por visitar la pantalla.
    try: rows = df_sheet(HOJA)
    except Exception as exc:
        # Sólo la ausencia explícita permite un listado vacío. Nunca ocultar cuotas/permisos.
        if type(exc).__name__ == 'WorksheetNotFound': return []
        raise
    records=rows.fillna('').to_dict('records')
    known={str(r.get('Revision','')) for r in records}
    records.extend(deepcopy(r) for rev,r in recientes().items() if rev not in known)
    docs = reconstruir(records)
    return [d for d in docs if d['alumno'] in ids and
        (incluir_eliminados or d['partes']['META']['estado'] != 'ELIMINADO')]

def _actual(id_alumno, ciclo):
    return next((d for d in listar(True) if d['id'] == clave(id_alumno,ciclo)), None)

def autorizar(doc, parte=None):
    a = actor(); alumno_autorizado(doc['alumno'])
    if doc.get('id') != clave(doc['alumno'],doc['ciclo']):raise PermissionError('Identidad del informe no válida.')
    canonical=_actual(doc['alumno'],doc['ciclo'])
    meta = canonical['partes'].get('META', {}) if canonical else {}
    if not meta: raise ValueError('La EPP no tiene una identidad registrada.')
    if parte is not None:
        if meta['estado'] == 'ELIMINADO': raise PermissionError('Recupera primero la EPP retirada.')
        if parte == 'Conclusión':
            if not puede_crear() or a['cuenta'] != meta['cuenta']:
                raise PermissionError('La maestra coordinadora integra la conclusión acordada por el equipo.')
        elif parte != a['area'] or a['director']:
            raise PermissionError('Solo puedes editar los apartados de tu función.')
    return a

def _append(id_alumno, ciclo, parte, value, revision='', estado='BORRADOR'):
    a = actor()
    content = json.dumps(value, ensure_ascii=False, sort_keys=True)
    if len(content) > 36000: raise ValueError('Contenido demasiado extenso para el respaldo.')
    with control():
        ws = hoja()
        clear_cache(HOJA)
        current = _actual(id_alumno,ciclo)
        latest = current['partes'].get(parte) if current else None
        if (latest['revision'] if latest else '') != revision:
            raise RuntimeError('Otra sesión actualizó este apartado. Tu texto se conserva: descarga el respaldo y recupera la versión reciente antes de guardar.')
        if parte=='Conclusión' and value.get('validada'):
            if value.get('revisiones_areas') != {area:current['partes'].get(area,{}).get('revision','') for area in AREAS}:
                raise RuntimeError('El equipo actualizó hallazgos. Recupera las aportaciones actuales antes de validar la conclusión.')
        rev = uuid4().hex
        now = datetime.now(ZoneInfo('America/Mexico_City')).isoformat(timespec='microseconds')
        row = [str(id_alumno),ciclo,parte,rev,revision,now,a['cuenta'],a['nombre'],estado,content]
        retry_google(lambda: ws.append_rows([row],value_input_option='RAW'))
        recientes()[rev]=dict(zip(HEADERS,row))
        if len(recientes())>1000:
            clear_cache(HOJA);recientes().clear()
        # Devuelve únicamente el área confirmada; no modifica snapshots de otras áreas.
        return {'contenido':deepcopy(value),'revision':rev,'fecha':now,'autor':a['nombre'],
                'cuenta':a['cuenta'],'estado':estado}

def crear(id_alumno, ciclo):
    if not puede_crear(): raise PermissionError('Solo las maestras de apoyo pueden iniciar una EPP.')
    alumno_autorizado(id_alumno)
    current = _actual(id_alumno,ciclo)
    if current: raise ValueError('Ya existe una EPP para este alumno y ciclo. Ábrela o recupera la retirada.')
    a = actor()
    meta = {'coordinadora':a['nombre'],'creada_por':a['cuenta'],'fuente':'Manual USAER, Anexos XVII y XVIII, pp. 141-151'}
    doc = {'id':clave(id_alumno,ciclo),'alumno':str(id_alumno),'ciclo':ciclo,'partes':{}}
    doc['partes']['META'] = _append(id_alumno,ciclo,'META',meta)
    return doc

def guardar(doc, parte, value, revision):
    autorizar(doc,parte)
    clean = validar_parte(parte,value)
    # Una propuesta de IA jamás valida un área ni una conclusión.
    if parte == 'Conclusión' and clean.get('validada'):
        clean['revisiones_areas']={area:doc['partes'].get(area,{}).get('revision','') for area in AREAS}
        candidate = deepcopy(doc)
        candidate['partes'][parte] = {'contenido':clean}
        if pendientes(candidate): raise ValueError('El equipo debe revisar sus áreas y completar la conclusión antes de validarla.')
    return _append(doc['alumno'],doc['ciclo'],parte,clean,revision,
                   'REVISADO' if clean.get('validada') else 'BORRADOR')

def retirar(doc, recuperar=False):
    a = autorizar(doc)
    meta = doc['partes']['META']
    if not puede_crear() or meta['cuenta'] != a['cuenta']:
        raise PermissionError('Solo la maestra que creó la EPP puede retirarla o recuperarla.')
    return _append(doc['alumno'],doc['ciclo'],'META',meta['contenido'],meta['revision'],
                   'BORRADOR' if recuperar else 'ELIMINADO')

def contexto(doc):
    autorizar(doc)
    plan = planes.nueva('XXV' if actor()['area']=='Trabajo Social' else 'XXIII',[doc['alumno']])
    plan = planes.preparar_contexto(plan)
    return plan

def resumen(doc, parte, value, plan):
    autorizar(doc)
    parts = []
    if parte == 'Conclusión':
        for area in AREAS:
            p = doc['partes'].get(area,{}).get('contenido',{})
            for f,t in p.get('campos',{}).items():
                if t: parts.append({'referencia':area+' / '+f,'alcance':'hallazgos del área; revisión humana pendiente' if not p.get('validada') else 'área revisada', 'texto':t})
    else:
        for i,e in enumerate(value.get('evaluaciones',[]),1):
            parts.append({'referencia':'EV'+str(i),'alcance':'evaluación revisada por el profesional','texto':e.get('texto','')})
    for f in plan['metadatos'].get('fuentes',[]):
        if f.get('vinculo_verificado') and f.get('alumno') == doc['alumno']:
            parts.append(f)
    return planes.resumen_previo(plan,parts)

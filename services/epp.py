"""EPP colaborativa privada: eventos por área; nunca sobrescribe otras aportaciones."""
from copy import deepcopy
from datetime import datetime
import hashlib
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


def es_coordinadora(doc):
    """La coordinación puede continuar tras un cambio interno confirmado del alumno.

    META conserva a su creadora; cada nueva versión registra a la autora real.
    No concede acceso por apellido ni permite editar las áreas de especialistas.
    """
    a=actor()
    if not puede_crear():return False
    alumno=alumno_autorizado(doc['alumno'])
    meta=doc['partes'].get('META',{})
    if meta.get('cuenta')==a['cuenta']:return True
    from services.alumnos import _canonizar_docente_apoyo as canon
    from services.padron_movimientos import permite_cambio_interno,responsable_interno_confirmado
    if not permite_cambio_interno(alumno) or canon(alumno.get('Maestra de Apoyo',''))!=canon(a['nombre']):return False
    return responsable_interno_confirmado(doc['alumno'],meta.get('contenido',{}).get('coordinadora',''),a['nombre'])

def alumno_autorizado(id_alumno,incluir_bajas=False):
    if incluir_bajas:
        actor()
        from services.padron_movimientos import visibles
        frame=visibles()
    else:frame = planes.padron_autorizado()
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

def listar(incluir_eliminados=False,incluir_bajas=False):
    actor()
    if incluir_bajas:
        from services.padron_movimientos import visibles
        frame=visibles()
    else:frame = planes.padron_autorizado()
    ids = set(frame['ID_Alumno'].astype(str)) if 'ID_Alumno' in frame else set()
    # No se crea una hoja por visitar la pantalla.
    try: rows = df_sheet(HOJA)
    except Exception as exc:
        # Sólo la ausencia explícita permite un listado vacío. Nunca ocultar cuotas/permisos.
        if type(exc).__name__ == 'WorksheetNotFound': return []
        raise
    # Filtrar antes de deserializar el historial completo de toda la USAER.
    # Los permisos se vuelven a comprobar al editar y guardar cada apartado.
    if 'Alumno' in rows:rows=rows.loc[rows['Alumno'].astype(str).isin(ids)]
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
            if not es_coordinadora(canonical):
                raise PermissionError('La maestra coordinadora integra la conclusión acordada por el equipo.')
        elif parte != a['area'] or a['director']:
            from services.epp_colaborativa import comparte
            if not comparte(a,parte):raise PermissionError('Solo puedes editar los apartados de tu función o los campos compartidos contigo.')
    return a

def _append(id_alumno, ciclo, parte, value, revision='', estado='BORRADOR',actual_confirmado=None):
    a = actor()
    content = json.dumps(value, ensure_ascii=False, sort_keys=True)
    if len(content) > 36000: raise ValueError('Contenido demasiado extenso para el respaldo.')
    with control():
        ws = hoja()
        if actual_confirmado is None:clear_cache(HOJA)
        current = actual_confirmado if actual_confirmado is not None else _actual(id_alumno,ciclo)
        latest = current['partes'].get(parte) if current else None
        if latest and ((latest['contenido']==value and latest['estado']==estado) or parte=='META' and not revision):
            return deepcopy(latest)
        if (latest['revision'] if latest else '') != revision:
            raise RuntimeError('Otra sesión actualizó este apartado. Tu texto se conserva: descarga el respaldo y recupera la versión reciente antes de guardar.')
        if parte=='Conclusión' and value.get('validada'):
            if value.get('revisiones_areas') != {area:current['partes'].get(area,{}).get('revision','') for area in AREAS}:
                raise RuntimeError('El equipo actualizó hallazgos. Recupera las aportaciones actuales antes de validar la conclusión.')
        rev = hashlib.sha256(json.dumps([str(id_alumno),ciclo,parte,revision,estado,content],ensure_ascii=False).encode()).hexdigest()
        now = datetime.now(ZoneInfo('America/Mexico_City')).isoformat(timespec='microseconds')
        row = [str(id_alumno),ciclo,parte,rev,revision,now,a['cuenta'],a['nombre'],estado,content]
        # La siguiente invocación reconcilia el envío incierto con el diario.
        # No dormir manteniendo el candado ni duplicar llamadas de escritura.
        from services.planeacion_estabilidad import reservar_escritura
        reservar_escritura()
        ws.append_rows([row],value_input_option='RAW')
        clear_cache(HOJA)
        registros=df_sheet(HOJA).fillna('').to_dict('records')
        if not any(str(r.get('Revision'))==rev and r.get('Contenido')==content for r in registros):
            raise ConnectionError('La revisión enviada aún no tiene confirmación de lectura.')
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
    if current:
        if current['partes']['META']['estado']=='ELIMINADO':raise ValueError('La EPP está retirada; recupera el mismo informe, no crees otra copia.')
        return current
    a = actor()
    meta = {'coordinadora':a['nombre'],'creada_por':a['cuenta'],'fuente':'Manual USAER, Anexos XVII y XVIII, pp. 141-151'}
    doc = {'id':clave(id_alumno,ciclo),'alumno':str(id_alumno),'ciclo':ciclo,'partes':{}}
    doc['partes']['META'] = _append(id_alumno,ciclo,'META',meta)
    return doc


def combinar(base, local, remoto):
    """Fusión de tres vías: solo cambios propios, conflicto visible en el mismo dato."""
    if local==base:return deepcopy(remoto)
    if remoto==base or remoto==local:return deepcopy(local)
    if all(isinstance(v,dict) for v in (base,local,remoto)):
        missing=object();result={}
        for k in base.keys()|local.keys()|remoto.keys():
            b,l,r=base.get(k,missing),local.get(k,missing),remoto.get(k,missing)
            if l==b:v=r
            elif r==b or l==r:v=l
            elif isinstance(l,dict) and isinstance(r,dict) and (isinstance(b,dict) or b is missing):v=combinar({} if b is missing else b,l,r)
            else:raise RuntimeError('Otra sesión cambió el mismo dato de tu área. Se conservan ambas versiones: respalda tu texto y revisa el dato en conflicto.')
            if v is not missing:result[k]=deepcopy(v)
        return result
    raise RuntimeError('Otra sesión cambió la misma tabla. Tu captura permanece pendiente; respáldala y revisa la versión reciente.')


def guardar_cambios(doc, parte, base, value, revision):
    """Reintentos de una misma área no bloquean aportaciones independientes."""
    autorizar(doc,parte)
    with control():
        clear_cache(HOJA)
        actual=_actual(doc['alumno'],doc['ciclo'])
        latest=actual['partes'].get(parte,{})
        remoto=latest.get('contenido',vacia(parte))
        combinado=combinar(base,value,remoto) if latest.get('revision','')!=revision else deepcopy(value)
        if combinado!=remoto:combinado['validada']=False
        return guardar(actual,parte,combinado,latest.get('revision',''),_actual_confirmado=actual)

def guardar(doc, parte, value, revision, _actual_confirmado=None):
    a=autorizar(doc,parte)
    clean = validar_parte(parte,value)
    if parte!=a['area'] and parte!='Conclusión':
        from services.epp_colaborativa import validar_cambios
        current=_actual_confirmado or _actual(doc['alumno'],doc['ciclo'])
        validar_cambios(a,parte,current['partes'].get(parte,{}).get('contenido',vacia(parte)),clean)
    # Una propuesta de IA jamás valida un área ni una conclusión.
    if parte == 'Conclusión' and clean.get('validada'):
        clean['revisiones_areas']={area:doc['partes'].get(area,{}).get('revision','') for area in AREAS}
        candidate = deepcopy(doc)
        candidate['partes'][parte] = {'contenido':clean}
        if pendientes(candidate): raise ValueError('El equipo debe revisar sus áreas y completar la conclusión antes de validarla.')
    return _append(doc['alumno'],doc['ciclo'],parte,clean,revision,
                   'REVISADO' if clean.get('validada') else 'BORRADOR',actual_confirmado=_actual_confirmado)

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
        from services.epp_conclusion import fuentes
        parts=fuentes(doc)
    else:
        if not value.get('evaluaciones'):
            raise ValueError('Incorpora primero los resultados revisados de un instrumento de esta área.')
        for i,e in enumerate(value.get('evaluaciones',[]),1):
            parts.append({'referencia':'EV'+str(i),'alcance':'evaluación revisada por el profesional',
                'texto':'Instrumento: '+e.get('nombre','')+'\nFecha: '+e.get('fecha','por confirmar')+
                    '\nEntrada: '+e.get('entrada','CARGA')+'\n'+e.get('texto','')})
    for f in plan['metadatos'].get('fuentes',[]):
        if parte=='Conclusión':continue  # El cierre se sustenta en los hallazgos actuales del equipo.
        if f.get('vinculo_verificado') and f.get('alumno') == doc['alumno']:
            parts.append(f)
    return planes.resumen_previo(plan,parts)

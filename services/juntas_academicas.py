"""Materiales por sesión y aportaciones versionadas; sin alterar el padrón."""
from copy import deepcopy
from datetime import date,datetime
from zoneinfo import ZoneInfo
import hashlib
import json
from data import repository as repo
from data.google import clear_cache,ensure_headers
from services.planeacion import identidad
from services.planeacion_estabilidad import candado
from services.juntas_metodologias_catalogo import VERSION,POR_ID

PRIMERA_SESION='2026-10-23'
HOJA='Juntas_Academicas_Versiones'
HEADERS=['Documento','Revision','Anterior','Fecha_Sesion','Guardado_En','Cuenta','SHA256','Contenido']


def validar(value):
    if not isinstance(value,dict) or set(value)!={'Version','Respuestas'} or value['Version']!=VERSION or not isinstance(value['Respuestas'],dict):
        raise ValueError('El cuadro no corresponde a esta versión del material.')
    for code,row in value['Respuestas'].items():
        if code not in POR_ID or not isinstance(row,dict) or set(row)!={'A','C','P','Aplicación prevista','Evidencia y seguimiento'}:
            raise ValueError('Conserva las columnas originales del cuadro.')
        if any(type(row[k]) is not bool for k in ('A','C','P')):raise ValueError('Las columnas A, C y P admiten únicamente marcas.')
        if any(not isinstance(row[k],str) or len(row[k])>1500 for k in ('Aplicación prevista','Evidencia y seguimiento')):raise ValueError('Resume cada anotación a 1500 caracteres.')
    return deepcopy(value)


def vacia():return {'Version':VERSION,'Respuestas':{}}


def registro_vacio():return {'A':False,'C':False,'P':False,'Aplicación prevista':'','Evidencia y seguimiento':''}


def _identificador(cuenta,fecha):return hashlib.sha256(json.dumps([cuenta,fecha,'metodologias']).encode()).hexdigest()


def _leer():
    try:return repo.read(HOJA).fillna('').to_dict('records')
    except Exception as exc:
        if type(exc).__name__=='WorksheetNotFound':return []
        raise


def listar(fecha=None,equipo=False):
    actor=identidad()
    if equipo and not actor['director']:raise PermissionError('Solo Dirección puede consultar las aportaciones de todo el equipo.')
    if fecha is not None:fecha=date.fromisoformat(str(fecha)).isoformat()
    actuales={}
    for row in _leer():
        if (not equipo and row.get('Cuenta')!=actor['cuenta']) or (fecha and row.get('Fecha_Sesion')!=fecha):continue
        raw=str(row.get('Contenido',''))
        if hashlib.sha256(raw.encode()).hexdigest()!=row.get('SHA256'):raise RuntimeError('Una aportación requiere revisión de integridad. Se conservó el historial.')
        d=json.loads(raw)
        if any(d.get(k)!=row.get(k) for k in ('Cuenta','Fecha_Sesion')) or _identificador(d['Cuenta'],d['Fecha_Sesion'])!=row.get('Documento'):
            raise RuntimeError('La procedencia de una aportación requiere revisión.')
        validar(d['Captura'])
        actuales[row['Documento']]={**d,'Documento':row['Documento'],'Revision':row['Revision'],'Guardado_En':row['Guardado_En']}
    return sorted(deepcopy(list(actuales.values())),key=lambda d:(d['Fecha_Sesion'],d['Docente'],d['Cuenta']))


def guardar(fecha,capture,revision=''):
    actor=identidad()
    if actor['director']:raise PermissionError('Dirección integra respuestas sin capturar por otro docente.')
    fecha=date.fromisoformat(str(fecha)).isoformat();capture=validar(capture)
    docid=_identificador(actor['cuenta'],fecha)
    payload={'Cuenta':actor['cuenta'],'Docente':actor['nombre'],'Area':actor['area'],'Fecha_Sesion':fecha,'Captura':capture}
    raw=json.dumps(payload,ensure_ascii=False,sort_keys=True)
    if len(raw)>35000:raise ValueError('El cuadro supera el tamaño disponible. Descarga un respaldo y resume las anotaciones.')
    with candado('junta:'+docid):
        clear_cache(HOJA);prev=next(iter(listar(fecha)),{})
        if prev and all(prev.get(k)==v for k,v in payload.items()):return prev
        if prev.get('Revision','')!=revision:raise RuntimeError('Otra pestaña actualizó tu cuadro. Conserva el respaldo antes de conciliar las dos capturas.')
        digest=hashlib.sha256(raw.encode()).hexdigest();rev=hashlib.sha256((docid+revision+digest).encode()).hexdigest()
        row={'Documento':docid,'Revision':rev,'Anterior':revision,'Fecha_Sesion':fecha,'Guardado_En':datetime.now(ZoneInfo('America/Mexico_City')).isoformat(),
            'Cuenta':actor['cuenta'],'SHA256':digest,'Contenido':raw}
        ws,headers=ensure_headers(HOJA,HEADERS,return_columns=True)
        if len(headers)!=len(set(headers)) or not set(HEADERS)<=set(headers):raise RuntimeError('Los encabezados de juntas requieren revisión. No se reemplazaron capturas.')
        ws.append_rows([[row.get(k,'') for k in headers]],value_input_option='RAW');clear_cache(HOJA)
        result=next((d for d in listar(fecha) if d['Revision']==rev),None)
        if not result:raise RuntimeError('No se confirmó la lectura del guardado. Reintenta sin cambiar la captura o descarga el respaldo.')
        return result


def fechas():
    from services import metas_personales
    actor=identidad()
    docs=listar(equipo=actor['director'])
    metas=metas_personales.consolidar() if actor['director'] else metas_personales.propias()
    return sorted({PRIMERA_SESION,*[d['Fecha_Sesion'] for d in docs+metas]},reverse=True)

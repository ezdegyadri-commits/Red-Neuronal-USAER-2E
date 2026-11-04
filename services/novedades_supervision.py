"""Índice privado de supervisión. No consulta alumnos ni llama a IA."""
from datetime import datetime
from urllib.parse import urlparse
from zoneinfo import ZoneInfo
import streamlit as st
from gspread import WorksheetNotFound
from data.google import worksheet,ensure_headers,retry_google
from services.planeacion import identidad
from utils.text import normalizar_texto

HOJA='Novedades_Supervision'
REVISIONES='Novedades_Supervision_Revision'
HEADERS=['ID_Documento','Nombre','Seccion','Tipo','Enlace','Modificado_En','Extracto','Estado_Lectura','Sincronizado_En','Fuente','Estado']
HEADERS_REVISION=['Cuenta','Documento','Modificado_En','Revisado_En']

def autorizar():
    actor=identidad()
    if not actor['director']:raise PermissionError('Las novedades de supervisión son exclusivas de Dirección.')
    return actor

def enlace_seguro(value):
    try:
        parsed=urlparse(str(value))
        return str(value) if parsed.scheme=='https' and parsed.hostname in {'drive.google.com','docs.google.com'} and not parsed.username and not parsed.password else ''
    except ValueError:return ''

@st.cache_data(ttl=300,show_spinner=False)
def _leer(hoja):
    try:ws=worksheet(hoja)
    except WorksheetNotFound:return []
    values=retry_google(ws.get_all_values)
    if not values:return []
    return [dict(zip(values[0],row+['']*max(0,len(values[0])-len(row)))) for row in values[1:]]

def vigentes(rows):
    latest={}
    for row in rows:
        ident=str(row.get('ID_Documento','')).strip()
        if not ident:continue
        previo=latest.get(ident)
        if previo and str(row.get('Sincronizado_En',''))<str(previo.get('Sincronizado_En','')):continue
        latest[ident]=dict(row)
    fuente=latest.pop('__SOURCE__',{})
    docs=[]
    for row in latest.values():
        if row.get('Estado','VIGENTE')=='RETIRADO':continue
        row['Enlace']=enlace_seguro(row.get('Enlace',''))
        row['Extracto']=str(row.get('Extracto',''))[:20000]
        docs.append(row)
    return sorted(docs,key=lambda d:(d.get('Modificado_En',''),d.get('Nombre','')),reverse=True),fuente

def cargar():
    actor=autorizar()  # Siempre antes de acceder incluso a la caché compartida.
    docs,fuente=vigentes(_leer(HOJA))
    vistos={(r.get('Documento'),r.get('Modificado_En')) for r in _leer(REVISIONES) if r.get('Cuenta')==actor['cuenta']}
    for doc in docs:doc['Nuevo']=(doc['ID_Documento'],doc.get('Modificado_En','')) not in vistos
    return docs,fuente

def filtrar(docs,busqueda='',seccion='Todas',solo_nuevos=False,actividades=False):
    texto=normalizar_texto(busqueda)
    return [d for d in docs if (not solo_nuevos or d.get('Nuevo')) and (seccion=='Todas' or d.get('Seccion')==seccion)
        and (not texto or texto in normalizar_texto(' '.join(str(d.get(k,'')) for k in ('Nombre','Seccion','Extracto'))))
        and (not actividades or any(p in normalizar_texto(d.get('Nombre','')+' '+d.get('Seccion','')) for p in ('CALENDARIO','ACTIVIDAD','SUGERENCIA','CTE','JUNTA','PLAN DE ZONA')))]

def marcar_revisado(documento,modificado):
    actor=autorizar();docs,_=cargar()
    actual=next((d for d in docs if d['ID_Documento']==documento),None)
    if not actual or actual.get('Modificado_En','')!=modificado:raise ValueError('El documento cambió. Actualiza la lista antes de marcarlo como revisado.')
    if not actual['Nuevo']:return
    row={'Cuenta':actor['cuenta'],'Documento':documento,'Modificado_En':modificado,
         'Revisado_En':datetime.now(ZoneInfo('America/Mexico_City')).isoformat(timespec='seconds')}
    ws=ensure_headers(REVISIONES,HEADERS_REVISION)
    headers=retry_google(lambda:ws.row_values(1))
    retry_google(lambda:ws.append_rows([[row.get(h,'') for h in headers]],value_input_option='RAW'))
    _leer.clear()

def refrescar():
    autorizar();_leer.clear()

def fecha_local(value):
    try:
        fecha=datetime.fromisoformat(str(value).replace('Z','+00:00'))
        if fecha.tzinfo is None:fecha=fecha.replace(tzinfo=ZoneInfo('UTC'))
        return fecha.astimezone(ZoneInfo('America/Mexico_City')).strftime('%d/%m/%Y %H:%M')
    except (ValueError,TypeError):return 'Sin fecha informada'

"""Control compartido de EPP, por identidad del alumno y versiones aditivas."""
from datetime import date,datetime
from zoneinfo import ZoneInfo
import hashlib
import json
from data import repository as repo
from data.google import ensure_headers,clear_cache
from services import epp
from services.planeacion_estabilidad import candado

HOJA='EPP_Programacion'
HEADERS=['ID_Programacion','Revision','Anterior','Fecha_Registro','Cuenta','ID_Alumno','ID_Escuela','Ciclo','Area','Fecha','Hora','Aspectos','Instrumentos','Lugar','Estado']
AREAS=('Aprendizaje','Psicología','Comunicación','Trabajo Social','Integración interdisciplinaria')
ESTADOS=('Por programar','Programada','Por validar','Validada por Dirección','Realizada','Cancelada')

def _rows():
    try:return repo.read(HOJA).fillna('').to_dict('records')
    except Exception as exc:
        if type(exc).__name__=='WorksheetNotFound':return []
        raise

def listar():
    epp.actor();frame=epp.planes.padron_autorizado()
    alumnos={str(r['ID_Alumno']):str(r['ID_Escuela']) for r in frame.to_dict('records')}
    ultimas={}
    for r in _rows():
        if r.get('ID_Programacion') and alumnos.get(str(r.get('ID_Alumno')))==str(r.get('ID_Escuela')):ultimas[r['ID_Programacion']]=r
    return sorted(ultimas.values(),key=lambda r:(r.get('Fecha') or '9999',r.get('Hora',''),r['ID_Alumno']))

def guardar(id_alumno,ciclo,area,fecha=None,hora='',aspectos='',instrumentos='',lugar='',estado='Por programar',identificador=None,revision=''):
    actor=epp.actor();alumno=epp.alumno_autorizado(id_alumno)
    if area not in AREAS or estado not in ESTADOS:raise ValueError('Selecciona un área y estado del catálogo.')
    if actor['area'] not in AREAS and not actor['director']:raise PermissionError('Función no autorizada.')
    from re import fullmatch
    if not fullmatch(r'20\d{2}-20\d{2}',str(ciclo)) or int(ciclo[-4:])!=int(ciclo[:4])+1:raise ValueError('Revisa el ciclo escolar.')
    fecha=date.fromisoformat(str(fecha)).isoformat() if fecha else ''
    if hora:hora=datetime.strptime(str(hora),'%H:%M').strftime('%H:%M')
    if estado in ('Programada','Por validar','Validada por Dirección','Realizada') and not fecha:raise ValueError('Esta programación requiere una fecha.')
    if estado=='Validada por Dirección' and not actor['director']:raise PermissionError('Dirección valida el cronograma conforme al manual.')
    if any(len(str(v))>3000 for v in (aspectos,instrumentos,lugar)):raise ValueError('Resume los datos de programación.')
    with candado('programacion-epp:'+str(id_alumno)):
        clear_cache(HOJA)
        registros=listar();anterior=next((r for r in registros if r['ID_Programacion']==identificador),None)
        if identificador and not anterior and any(r.get('ID_Programacion')==identificador for r in _rows()):raise PermissionError('Programación fuera de tu asignación.')
        if not anterior and not epp.puede_crear():raise PermissionError('La maestra de apoyo inicia la programación; después el equipo asignado puede editarla.')
        if anterior and (anterior['ID_Alumno']!=str(id_alumno) or anterior['Ciclo']!=ciclo):raise PermissionError('No se puede cambiar el alumno o ciclo de un registro existente.')
        payload={'ID_Alumno':str(id_alumno),'ID_Escuela':str(alumno['ID_Escuela']),'Ciclo':ciclo,'Area':area,
                 'Fecha':fecha,'Hora':hora,'Aspectos':str(aspectos).strip(),'Instrumentos':str(instrumentos).strip(),'Lugar':str(lugar).strip(),'Estado':estado}
        if anterior and all(anterior.get(k,'')==v for k,v in payload.items()):return anterior
        if (anterior or {}).get('Revision','')!=revision:raise RuntimeError('El equipo modificó esta programación. Actualiza antes de guardar; tu captura se conserva.')
        ident=identificador or hashlib.sha256(json.dumps([actor['cuenta'],payload],sort_keys=True).encode()).hexdigest()
        repetido=next((r for r in registros if r['ID_Programacion']==ident),None)
        if repetido and all(repetido.get(k,'')==v for k,v in payload.items()):return repetido
        rev=hashlib.sha256(json.dumps([ident,revision,payload],sort_keys=True).encode()).hexdigest()
        row={**payload,'ID_Programacion':ident,'Revision':rev,'Anterior':revision,'Fecha_Registro':datetime.now(ZoneInfo('America/Mexico_City')).isoformat(),'Cuenta':actor['cuenta']}
        ws=ensure_headers(HOJA,HEADERS)
        headers=ws.row_values(1)
        if len(headers)!=len(set(headers)) or not set(HEADERS)<=set(headers):raise RuntimeError('El control EPP tiene encabezados por verificar; no se sobrescribió.')
        ws.append_rows([[row.get(h,'') for h in headers]],value_input_option='RAW')
        clear_cache(HOJA)
        if not any(r.get('Revision')==rev and r.get('ID_Programacion')==ident for r in _rows()):
            raise RuntimeError('No se confirmó la programación. Tu captura se conserva; reintenta sin cambiar los datos.')
        return row

def eventos_calendario(mes):
    if not epp.st.session_state.get('autenticado'):return []
    return [{'ID_Evento':'EPP-'+r['ID_Programacion'],'Revision':r['Revision'],'Fecha':r['Fecha'],
             'Titulo':'EPP · '+r['Area'],'Detalle':('Hora: '+r['Hora']+'. ' if r['Hora'] else '')+'Consultar el cuadro privado de programación de EPP.',
             'Origen':'Programación EPP'} for r in listar() if r['Fecha'].startswith(mes+'-') and r['Estado']!='Cancelada']

"""Metas por docente, escuela y sesión; historial aditivo y texto literal."""
from copy import deepcopy
from datetime import date,datetime
from zoneinfo import ZoneInfo
import hashlib
import json
from data import repository as repo
from data.google import ensure_headers,clear_cache
from services import planeacion as planes
from services.planeacion_estabilidad import candado
from services import metas_instrumento as instrumento

HOJA='Metas_Personales_Versiones'
HEADERS=['Documento','Revision','Anterior','Guardado_En','Cuenta','ID_Escuela','Fecha_Sesion','SHA256','Contenido']


def identidad():return planes.identidad()


def matricula(escuela):
    from services.planeacion_matricula import clave_escuela
    identidad();frame=planes.padron_autorizado().fillna('')
    filas=[r for r in frame.to_dict('records') if clave_escuela(r.get('ID_Escuela'))==clave_escuela(escuela)]
    if not filas:raise PermissionError('Esta escuela no tiene alumnos disponibles en tu asignación.')
    return filas


def _identificador(cuenta,escuela,fecha):
    return hashlib.sha256(json.dumps([cuenta,escuela,fecha],ensure_ascii=False).encode()).hexdigest()[:32]


def _versiones(cuenta,escuela,fecha):
    try:rows=repo.read(HOJA).fillna('').to_dict('records')
    except Exception as exc:
        if type(exc).__name__=='WorksheetNotFound':return []
        raise
    resultado=[]
    ident=_identificador(cuenta,escuela,fecha)
    for r in rows:
        if r.get('Documento')!=ident or r.get('Cuenta')!=cuenta or r.get('ID_Escuela')!=escuela or r.get('Fecha_Sesion')!=fecha:continue
        raw=str(r.get('Contenido',''))
        if hashlib.sha256(raw.encode()).hexdigest()!=r.get('SHA256'):raise RuntimeError('Una versión de metas requiere revisión. No se reemplazó tu información.')
        d=json.loads(raw)
        if d.get('Cuenta')!=cuenta or d.get('ID_Escuela')!=escuela or d.get('Fecha_Sesion')!=fecha:raise PermissionError('La versión de metas no corresponde a esta cuenta y escuela.')
        resultado.append({**d,'Documento':ident,'Revision':r['Revision'],'Guardado_En':r['Guardado_En']})
    return resultado


def recuperar(escuela,fecha):
    from services.planeacion_matricula import clave_escuela
    escuela=clave_escuela(escuela)
    actor=identidad();matricula(escuela);fecha=date.fromisoformat(str(fecha)).isoformat()
    versiones=_versiones(actor['cuenta'],escuela,fecha)
    return deepcopy(versiones[-1]) if versiones else None


def guardar(escuela,fecha,filas,revision='',periodo=None):
    from services.planeacion_matricula import clave_escuela
    escuela=clave_escuela(escuela)
    actor=identidad();padron={str(r['ID_Alumno']):r for r in matricula(escuela)}
    fecha=date.fromisoformat(str(fecha)).isoformat()
    if actor['director']:raise PermissionError('Dirección consulta y consolida las aportaciones; no captura en nombre de otro docente.')
    if actor['area'] not in {'Aprendizaje','Psicología','Comunicación','Trabajo Social'}:raise PermissionError('Esta función no puede capturar metas.')
    if not isinstance(filas,list) or len(filas)>200:raise ValueError('El formato admite hasta 200 alumnos.')
    if periodo is not None and (not isinstance(periodo,str) or len(periodo)>200):raise ValueError('Resume el período de planificación a 200 caracteres.')
    ident=_identificador(actor['cuenta'],escuela,fecha)
    with candado('metas:'+ident):
        clear_cache(HOJA)
        versiones=_versiones(actor['cuenta'],escuela,fecha);previo=versiones[-1] if versiones else None
        anteriores={r['ID_Alumno']:r for r in (previo or {}).get('Filas',[])}
        nuevas=[];vistos=set()
        for fila in filas:
            aid=str(fila.get('ID_Alumno','')).strip();meta=str(fila.get('Metas','') or '').strip();recursos=str(fila.get('Recursos necesarios','') or '').strip()
            if not aid and not meta and not recursos:continue
            if not aid:raise ValueError('Selecciona un alumno para cada meta capturada.')
            if aid in vistos:raise ValueError('El alumno aparece dos veces. Reúne sus metas en el mismo renglón.')
            vistos.add(aid)
            if len(meta)>1500 or len(recursos)>1000:raise ValueError('Resume cada meta a 1500 caracteres y sus recursos a 1000.')
            rubrica=fila.get('Instrumento',anteriores.get(aid,{}).get('Instrumento'))
            if rubrica is not None:rubrica=instrumento.validar(rubrica)
            if aid not in padron:
                anterior=anteriores.get(aid)
                if not anterior or anterior['Metas']!=meta or anterior['Recursos necesarios']!=recursos or anterior.get('Instrumento')!=rubrica:raise PermissionError('Un alumno ya no está disponible en tu asignación. Su registro anterior se conserva sin cambios.')
                nuevas.append(deepcopy(anterior));continue
            a=padron[aid]
            nueva={'ID_Alumno':aid,'Alumno':str(a.get('Nombre_Completo','')),'Metas':meta,'Recursos necesarios':recursos}
            if rubrica is not None:nueva['Instrumento']=rubrica
            nuevas.append(nueva)
        nombre_escuela=str(next(iter(padron.values())).get('Nombre_Escuela','') or escuela)
        payload={'Cuenta':actor['cuenta'],'Docente':actor['nombre'],'ID_Escuela':escuela,'Escuela':nombre_escuela,'Fecha_Sesion':fecha,'Filas':nuevas}
        if periodo is not None or (previo and 'Periodo' in previo):payload['Periodo']=periodo if periodo is not None else previo['Periodo']
        if periodo is not None or (previo and 'Area' in previo):payload['Area']=actor['area']
        # Una confirmación perdida se reconoce por contenido antes de exigir revisión.
        if previo and all(previo.get(k)==v for k,v in payload.items()):return deepcopy(previo)
        if (previo or {}).get('Revision','')!=revision:raise RuntimeError('Otra pestaña actualizó estas metas. Descarga tu respaldo y recupera la versión guardada antes de conciliar; tu captura sigue aquí.')
        raw=json.dumps(payload,ensure_ascii=False,sort_keys=True)
        if len(raw)>35000:raise ValueError('El formato es muy extenso. Conserva el respaldo y resume las metas antes de guardar.')
        digest=hashlib.sha256(raw.encode()).hexdigest()
        rev=hashlib.sha256((ident+revision+digest).encode()).hexdigest()
        row={'Documento':ident,'Revision':rev,'Anterior':revision,'Guardado_En':datetime.now(ZoneInfo('America/Mexico_City')).isoformat(),
             'Cuenta':actor['cuenta'],'ID_Escuela':escuela,'Fecha_Sesion':fecha,'SHA256':digest,'Contenido':raw}
        ws=ensure_headers(HOJA,HEADERS);headers=ws.row_values(1)
        if len(headers)!=len(set(headers)) or not set(HEADERS)<=set(headers):raise RuntimeError('Los encabezados de metas requieren revisión. No se sobrescribió ninguna captura.')
        ws.append_rows([[row.get(h,'') for h in headers]],value_input_option='RAW')
        clear_cache(HOJA)
        confirmado=next((d for d in reversed(_versiones(actor['cuenta'],escuela,fecha)) if d['Revision']==rev),None)
        if not confirmado:raise RuntimeError('No se confirmó el guardado central. Tu captura sigue aquí; reintenta sin cambiarla o descarga el respaldo.')
        return confirmado


def consolidar(fecha=None):
    """Última versión íntegra por cuenta/escuela/sesión, solo para Dirección.

    Es una proyección de las capturas originales, no una copia editable ni
    una mezcla de autores. Se conserva la procedencia y no se borra historia.
    """
    actor=identidad()
    if not actor['director']:raise PermissionError('Solo Dirección puede integrar las respuestas de todo el equipo.')
    return _actuales(fecha)


def propias():
    actor=identidad()
    return _actuales(cuenta=actor['cuenta'])


def _actuales(fecha=None,cuenta=None):
    from services.planeacion_matricula import clave_escuela
    permitidas={clave_escuela(r['ID_Escuela']) for r in planes.padron_autorizado().fillna('').to_dict('records')}
    if fecha is not None:fecha=date.fromisoformat(str(fecha)).isoformat()
    try:rows=repo.read(HOJA).fillna('').to_dict('records')
    except Exception as exc:
        if type(exc).__name__=='WorksheetNotFound':return []
        raise
    actuales={}
    for r in rows:
        if cuenta is not None and r.get('Cuenta')!=cuenta:continue
        if clave_escuela(r.get('ID_Escuela')) not in permitidas or (fecha and r.get('Fecha_Sesion')!=fecha):continue
        raw=str(r.get('Contenido',''))
        if hashlib.sha256(raw.encode()).hexdigest()!=r.get('SHA256'):raise RuntimeError('Una captura requiere revisión de integridad. No se generó un consolidado incompleto.')
        d=json.loads(raw)
        if any(d.get(k)!=r.get(k) for k in ('Cuenta','ID_Escuela','Fecha_Sesion')) or _identificador(d['Cuenta'],d['ID_Escuela'],d['Fecha_Sesion'])!=r.get('Documento'):
            raise RuntimeError('La procedencia de una captura requiere revisión. No se modificó información.')
        actuales[r['Documento']]={**d,'Documento':r['Documento'],'Revision':r['Revision'],'Guardado_En':r['Guardado_En']}
    return sorted(deepcopy(list(actuales.values())),key=lambda d:(d['Fecha_Sesion'],d.get('Escuela',''),d.get('Docente',''),d['Cuenta']))

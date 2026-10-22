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


def guardar(escuela,fecha,filas,revision=''):
    from services.planeacion_matricula import clave_escuela
    escuela=clave_escuela(escuela)
    actor=identidad();padron={str(r['ID_Alumno']):r for r in matricula(escuela)}
    fecha=date.fromisoformat(str(fecha)).isoformat()
    if not isinstance(filas,list) or len(filas)>50:raise ValueError('El formato admite hasta 50 alumnos.')
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
            if aid not in padron:
                anterior=anteriores.get(aid)
                if not anterior or anterior['Metas']!=meta or anterior['Recursos necesarios']!=recursos:raise PermissionError('Un alumno ya no está disponible en tu asignación. Su registro anterior se conserva sin cambios.')
                nuevas.append(deepcopy(anterior));continue
            a=padron[aid]
            nuevas.append({'ID_Alumno':aid,'Alumno':str(a.get('Nombre_Completo','')),'Metas':meta,'Recursos necesarios':recursos})
        nombre_escuela=str(next(iter(padron.values())).get('Nombre_Escuela','') or escuela)
        payload={'Cuenta':actor['cuenta'],'Docente':actor['nombre'],'ID_Escuela':escuela,'Escuela':nombre_escuela,'Fecha_Sesion':fecha,'Filas':nuevas}
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

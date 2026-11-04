"""Bajas recuperables y traslados internos. Nunca cambia el ID ni borra historia."""
from datetime import datetime,timezone
import json
from uuid import uuid4
import streamlit as st
from config.settings import ESCUELAS_USAER
from data import repository as repo
from data.google import ensure_sheet,worksheet,retry_google,clear_cache
from services.asignaciones import es_direccion,es_especialista,ASIGNACIONES_ESPECIALISTAS,escuelas_asignadas
from services.expedientes import alumnos_visibles
from services.planeacion_estabilidad import candado
from utils.text import normalizar_texto
from utils.escolar import grado_canonico,grupo_canonico

HOJA='Movimientos_Alumnos'
HEADERS=['ID_Movimiento','ID_Alumno','Accion','Estado','Fecha','Cuenta','Motivo','Antes_JSON','Despues_JSON']
UBICACION=('ID_Escuela','Nombre_Escuela','CCT_Escuela','Turno_Escuela','Direccion_Escuela','Localidad_Escuela','Municipio_Escuela','Maestra de Apoyo','ID_Maestro_Regular','Grado','Grupo','Estatus')


def visibles():
    if not st.session_state.get('autenticado'):raise PermissionError('Inicia sesión.')
    nombre=st.session_state.get('nombre','');rol=st.session_state.get('rol','')
    if not str(nombre).strip():raise PermissionError('Falta la identidad del personal.')
    frame=alumnos_visibles(rol,st.session_state.get('escuelas_permitidas',''),nombre,incluir_bajas=True)
    from services.alumnos import filtrar_alumnos_por_escuelas,filtrar_alumnos_por_docente_compartido
    if not es_direccion(rol):frame=filtrar_alumnos_por_escuelas(frame,escuelas_asignadas(nombre,rol))
    if 'APOYO' in normalizar_texto(rol):frame=filtrar_alumnos_por_docente_compartido(frame,nombre)
    return frame


def docentes_destino(escuela):
    return [n for n,escuelas in ASIGNACIONES_ESPECIALISTAS.items()
        if len(escuelas)==1 and escuela in escuelas]


def permite_cambio_interno(actual):
    from services.alumnos import _canonizar_docente_apoyo, DOCENTES_ICHC_AANZIHO
    from services.planeacion_matricula import clave_escuela
    return (clave_escuela(actual.get('ID_Escuela','')) == ESCUELAS_USAER['Ichcaanziho']
            and _canonizar_docente_apoyo(actual.get('Maestra de Apoyo','')) in DOCENTES_ICHC_AANZIHO)


def responsable_interno_confirmado(aid,anterior,nuevo):
    """Prueba una cadena confirmada; no toma una operación PREPARADA como traslado."""
    from services.alumnos import _canonizar_docente_apoyo as canon
    try:rows=repo.read(HOJA).fillna('').to_dict('records')
    except Exception as exc:
        if type(exc).__name__=='WorksheetNotFound':return False
        raise
    responsable=canon(anterior);vistos=set();cambio=False
    for r in rows:
        if str(r.get('ID_Alumno'))!=str(aid) or r.get('Accion')!='Cambiar maestra en la misma escuela' or r.get('Estado')!='CONFIRMADO' or r.get('ID_Movimiento') in vistos:continue
        vistos.add(r.get('ID_Movimiento'))
        antes=json.loads(r['Antes_JSON']);despues=json.loads(r['Despues_JSON'])
        if canon(antes.get('Maestra de Apoyo',''))==responsable:
            responsable=canon(despues.get('Maestra de Apoyo',''));cambio=True
    return cambio and responsable==canon(nuevo)


def preparar(actual,accion,escuela='',docente='',grado='',grupo='',regular=''):
    if accion=='Baja recuperable':return {'Estatus':'Baja'}
    if accion=='Reactivar':return {'Estatus':'Activo'}
    if accion=='Cambiar maestra en la misma escuela':
        from services.alumnos import _canonizar_docente_apoyo, DOCENTES_ICHC_AANZIHO
        destino = _canonizar_docente_apoyo(docente)
        if not permite_cambio_interno(actual) or destino not in DOCENTES_ICHC_AANZIHO:
            raise ValueError('Este cambio interno corresponde únicamente a las dos maestras de apoyo de Ichcaanziho.')
        if destino == _canonizar_docente_apoyo(actual.get('Maestra de Apoyo','')):
            raise ValueError('Elige a la otra maestra que recibirá al alumno.')
        if escuela and escuela != 'Ichcaanziho':raise ValueError('El cambio interno no cambia de escuela.')
        # Solo cambia el responsable; ni grado, modalidad, identidad ni historia.
        return {'Maestra de Apoyo': destino}
    if accion!='Trasladar':raise ValueError('Movimiento no válido.')
    if escuela not in ESCUELAS_USAER:raise ValueError('Elige una escuela de la USAER.')
    if str(actual.get('ID_Escuela'))==str(ESCUELAS_USAER[escuela]):raise ValueError('El destino debe ser otra escuela.')
    if docente not in docentes_destino(escuela):raise ValueError('Elige la maestra de apoyo del destino.')
    grado=grado_canonico(grado);grupo=grupo_canonico(grupo)
    if grado not in [f'{g}°' for g in range(1,7)]:raise ValueError('Confirma el grado de destino.')
    catalogo=repo.escuelas().fillna('')
    filas=catalogo.loc[catalogo['ID_Escuela'].astype(str).eq(str(ESCUELAS_USAER[escuela]))] if 'ID_Escuela' in catalogo else catalogo.iloc[:0]
    if len(filas)!=1:raise ValueError('Dirección debe confirmar la ficha única de la escuela de destino.')
    ficha=filas.iloc[0].to_dict()
    cambios={k:'' for k in UBICACION}
    cambios.update(ID_Escuela=ESCUELAS_USAER[escuela],Nombre_Escuela=escuela,Grado=grado,Grupo=grupo,Estatus='Activo',ID_Maestro_Regular=str(regular).strip())
    cambios['Maestra de Apoyo']=docente
    for target,source in [('CCT_Escuela','CCT'),('Turno_Escuela','Turno'),('Direccion_Escuela','Direccion'),('Localidad_Escuela','Localidad'),('Municipio_Escuela','Municipio')]:
        cambios[target]=str(ficha.get(source,ficha.get(target,'')))
    return cambios


def _anexar(registro):
    retry_google(lambda:worksheet(HOJA).append_rows([[registro.get(h,'') for h in HEADERS]],value_input_option='RAW'))
    clear_cache(HOJA)


def traslado_confirmado(aid,origen,destino):
    """Cadena auditada para consultar documentos individuales anteriores."""
    try:rows=repo.read(HOJA).fillna('').to_dict('records')
    except Exception as exc:
        if type(exc).__name__=='WorksheetNotFound':return False
        raise
    escuela=str(origen);vistos=set()
    for r in sorted(rows,key=lambda r:str(r.get('Fecha',''))):
        if r.get('ID_Alumno')!=str(aid) or r.get('Accion')!='Trasladar' or r.get('Estado')!='CONFIRMADO' or r.get('ID_Movimiento') in vistos:continue
        vistos.add(r.get('ID_Movimiento'))
        antes=json.loads(r['Antes_JSON']);despues=json.loads(r['Despues_JSON'])
        if str(antes.get('ID_Escuela',''))==escuela:escuela=str(despues.get('ID_Escuela',''))
    return escuela==str(destino) and escuela!=str(origen)


def ejecutar(aid,accion,motivo,operacion=None,esperado_origen=None,**destino):
    rol=st.session_state.get('rol','')
    if not es_direccion(rol) and ('APOYO' not in normalizar_texto(rol) or es_especialista(rol)):
        raise PermissionError('Solo apoyo de origen y Dirección gestionan movimientos del padrón.')
    if len(str(motivo).strip())<8:raise ValueError('Indica un motivo breve del movimiento.')
    if len(str(motivo))>500:raise ValueError('El motivo admite hasta 500 caracteres.')
    op=operacion or uuid4().hex
    with candado('padron:'+str(aid)):
        if operacion:
            try:previos=repo.read(HOJA).fillna('').to_dict('records')
            except Exception as exc:
                if type(exc).__name__!='WorksheetNotFound':raise
                previos=[]
            previo=next((r for r in reversed(previos) if r.get('ID_Movimiento')==op and r.get('ID_Alumno')==str(aid) and r.get('Cuenta')==st.session_state.get('usuario')),None)
            if previo:
                if previo.get('Accion')!=accion:raise ValueError('La operación corresponde a otro movimiento.')
                if previo.get('Estado')=='CONFIRMADO':return op
                # Recupera una confirmación perdida, sin volver a mover al alumno
                # ni exigir a origen acceso a la escuela que acaba de recibirlo.
                datos=repo.alumnos().fillna('');filas_actuales=datos.loc[datos['ID_Alumno'].astype(str).eq(str(aid))]
                despues=json.loads(previo['Despues_JSON'])
                if len(filas_actuales)==1 and all(str(filas_actuales.iloc[0].get(k,''))==str(v) for k,v in despues.items()):
                    _anexar({**previo,'Estado':'CONFIRMADO'});return op
        frame=visibles().fillna('');filas=frame.loc[frame['ID_Alumno'].astype(str).eq(str(aid))]
        if len(filas)!=1:raise PermissionError('El alumno no está en tu asignación actual.')
        actual=filas.iloc[0].to_dict()
        raw=repo.read('Alumnos').fillna('')
        curp=str(actual.get('CURP','')).strip().upper()
        if curp and {'CURP','ID_Alumno','Estatus'}.issubset(raw.columns):
            duplicados=raw.loc[raw['CURP'].astype(str).str.strip().str.upper().eq(curp)
                & raw['Estatus'].map(normalizar_texto).isin({'ACTIVO',''})]
            if len(set(duplicados['ID_Alumno'].astype(str)))>1:raise ValueError('Hay varios IDs activos para esta CURP. Dirección debe revisar la identidad antes de moverla; no se modificó ningún registro.')
        if esperado_origen and any(str(actual.get(k,''))!=str(v) for k,v in esperado_origen.items()):raise RuntimeError('La ubicación cambió desde que abriste la ficha. Revisa el padrón actualizado.')
        cambios=preparar(actual,accion,**destino)
        antes={k:str(actual.get(k,'')) for k in cambios}
        hoja=ensure_sheet(HOJA,HEADERS)
        if retry_google(lambda:hoja.row_values(1))!=HEADERS:raise ValueError('El registro de movimientos tiene otro esquema; no se modificó el padrón.')
        registro={'ID_Movimiento':op,'ID_Alumno':str(aid),'Accion':accion,'Estado':'PREPARADO',
            'Fecha':datetime.now(timezone.utc).isoformat(),'Cuenta':st.session_state.get('usuario',''),
            'Motivo':str(motivo).strip(),'Antes_JSON':json.dumps(antes,ensure_ascii=False),
            'Despues_JSON':json.dumps(cambios,ensure_ascii=False)}
        _anexar(registro)
        # El registro PREPARADO permanece si la escritura no se confirma. No se
        # anuncia un traslado completo ni se elimina el origen ante un fallo.
        repo.actualizar_ubicacion_alumno(aid,cambios,antes)
        _anexar({**registro,'Estado':'CONFIRMADO'})
        return op

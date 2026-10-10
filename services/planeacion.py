"""Planeaciones versionadas, aditivas y autorizadas en servidor."""
from copy import deepcopy
from datetime import datetime
import hashlib
import json
import re
import threading
import sys
from uuid import uuid4
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
from data import repository as repo
from data.google import ensure_headers, retry_google
from services.expedientes import alumnos_visibles, baps_de_alumno, sugerencias_de_alumno
from services.cronogramas import perfil_especialista
from services.planeacion_modelo import crear_plantilla, texto, FORMATOS
from utils.text import normalizar_texto
from utils.ids import expediente_id
from data.google import df_sheet
from services.planeacion_estabilidad import candado, intentos, reservar_escritura

HOJA = 'Planeaciones_Versiones'
HEADERS = ['Documento','Revision','Anterior','Fecha','Cuenta','Autor','Escuela_ID','Alumnos_JSON',
           'Formato','Estado','Parte','Total','SHA256','Contenido']
ESTADOS = {'BORRADOR','ENVIADO','CON_OBSERVACIONES','VALIDADO'}
VERSION_CONTEXTO = 2


def _vinculo_individual(r, alumno, padron):
    if texto(r.get('Estado',r.get('Estatus'))).upper() in {'ANULADO','ELIMINADO','RETIRADO','DUPLICADO'}:
        return False
    rid=texto(r.get('ID_Alumno'))
    escuela_id=texto(r.get('ID_Escuela'))
    if escuela_id and escuela_id!=texto(alumno.get('ID_Escuela')):return False
    if rid:return rid==texto(alumno.get('ID_Alumno'))
    nombre=normalizar_texto(r.get('Nombre_Alumno',''))
    escuela=normalizar_texto(r.get('Escuela',''))
    if not nombre or not escuela or nombre!=normalizar_texto(alumno.get('Nombre_Completo','')) or escuela!=normalizar_texto(alumno.get('Nombre_Escuela','')):
        return False
    candidatos={texto(a.get('ID_Alumno')) for a in padron if normalizar_texto(a.get('Nombre_Completo',''))==nombre and normalizar_texto(a.get('Nombre_Escuela',''))==escuela}
    return candidatos=={texto(alumno.get('ID_Alumno'))}


def identidad():
    if not st.session_state.get('autenticado'):
        raise PermissionError('Inicia sesión.')
    cuenta = texto(st.session_state.get('usuario'))
    nombre = texto(st.session_state.get('nombre'))
    rol = texto(st.session_state.get('rol'))
    perfil = perfil_especialista(nombre, rol)
    director = bool(perfil and perfil['area'] == 'Dirección')
    if not cuenta or not nombre or not (director or perfil or 'APOYO' in normalizar_texto(rol)):
        raise PermissionError('Esta cuenta no tiene una función de planeación.')
    return {'cuenta':cuenta,'nombre':nombre,'rol':rol,'director':director,
            'area':perfil['area'] if perfil else 'Aprendizaje','perfil':perfil}


def padron_autorizado():
    actor = identidad()
    # Diego usa su identidad canónica aunque Usuarios haya abreviado la función.
    rol = 'TRABAJO SOCIAL' if actor['area']=='Trabajo Social' else actor['rol']
    frame = alumnos_visibles(rol, st.session_state.get('escuelas_permitidas',''), actor['nombre'])
    if actor['perfil'] and not actor['director'] and not frame.empty:
        permitidas = {normalizar_texto(e) for e in actor['perfil']['escuelas']}
        frame = frame.loc[frame['Nombre_Escuela'].map(normalizar_texto).isin(permitidas)].copy()
    return frame


def nueva(formato, ids, ciclo=2026, trimestre=1, modalidad=None, incluir_individuales=False):
    actor = identidad()
    if modalidad is not None:
        from services.planeacion_modalidad import comprobar
        comprobar(padron_autorizado(), ids, modalidad, incluir_individuales)
    if formato != 'XXI' and formato != ('XXV' if actor['area']=='Trabajo Social' else 'XXIII'):
        raise PermissionError('Utiliza el formato correspondiente a tu función.')
    if formato=='XXI':
        if actor['area']!='Aprendizaje' or actor['director']:raise PermissionError('La maestra de apoyo coordina la creación del PI; los especialistas aportan desde Trabajo colaborativo.')
        existentes=[d for d in compartidos() if d['formato']=='XXI' and d['datos']['Curso escolar']==f'{ciclo}-{int(ciclo)+1}' and {a['ID_Alumno'] for a in d['datos']['Alumnos']}==set(ids)]
        if len(existentes)>1:raise ValueError('Hay varios PI para este alumno y ciclo. Revisa los documentos existentes con Dirección antes de crear otro.')
        if existentes:
            if existentes[0]['cuenta']!=actor['cuenta']:raise PermissionError('Ya existe un PI coordinado por otra maestra; ábrelo en Trabajo colaborativo.')
            return existentes[0]
    doc = crear_plantilla(formato, ids, padron_autorizado().to_dict('records'),
                          autor=actor['nombre'],funcion=actor['area'],ciclo_inicio=ciclo,
                          trimestre=trimestre,escuelas=repo.escuelas().to_dict('records'),
                          fecha=datetime.now(ZoneInfo('America/Mexico_City')).date())
    doc.update({'id':uuid4().hex,'revision':'','cuenta':actor['cuenta'],'observaciones_director':''})
    doc['metadatos'].update({'resumen_educativo':'','fuente_iepp':'','necesidades_confirmadas':'',
                             'referente_curricular':'','revisado_por':''})
    if modalidad is not None:
        doc['metadatos']['modalidad_planeacion'] = modalidad
        doc['metadatos']['individuales_en_sesion_grupal']=bool(incluir_individuales and modalidad=='grupal')
    from services.planeacion_equipo import preparar
    return preparar(doc)


def autorizar(doc, escribir=False):
    actor = identidad()
    if doc.get('formato') not in FORMATOS or doc.get('estado') not in ESTADOS:
        raise ValueError('Documento no válido.')
    ids = [texto(r.get('ID_Alumno')) for r in doc['datos']['Alumnos']]
    if not ids or len(set(ids))!=len(ids):
        raise ValueError('Selección de alumnos no válida.')
    frame = padron_autorizado()
    if not set(ids).issubset(set(frame['ID_Alumno'].astype(str)) if 'ID_Alumno' in frame else set()):
        raise PermissionError('Este documento contiene alumnos fuera de tu asignación actual.')
    actuales = frame.loc[frame['ID_Alumno'].astype(str).isin(ids)]
    if set(actuales['ID_Escuela'].astype(str)) != {doc['datos']['ID_Escuela']}:
        raise PermissionError('La escuela del documento no corresponde al padrón.')
    if doc['formato']=='XXI' and len(ids)!=1:
        raise ValueError('El plan de intervención es individual.')
    if escribir and doc.get('cuenta')!=actor['cuenta'] and not actor['director']:
        raise PermissionError('Solo el autor puede editar este documento.')
    if escribir and doc.get('cuenta')==actor['cuenta'] and doc['formato']!='XXI' and doc['formato']!=('XXV' if actor['area']=='Trabajo Social' else 'XXIII'):
        raise PermissionError('El formato no corresponde a tu función.')
    return actor


@st.cache_resource(show_spinner=False)
def _control():
    return threading.RLock(), {}


@st.cache_resource(show_spinner=False)
def _recientes():
    return {}


def versiones_actuales():
    # No invalida la lectura de Sheets por cada campo editado. Las escrituras
    # confirmadas se incorporan al caché del proceso y el libro se refresca por TTL.
    por_revision={d['revision']:d for d in _versiones()}
    with _control()[0]:
        por_revision.update(dict(_recientes()))
    from data.coordinacion import coordinador
    if coordinador() is not None:
        # El orden físico del ledger es canónico; los relojes de hosts distintos
        # pueden diferir. No elegir una versión antigua por su fecha aparente.
        return sorted(por_revision.values(),key=lambda d:d.get('_orden',-1))
    return sorted(por_revision.values(),key=lambda d:d.get('guardado_en',''))


@st.cache_resource(ttl=600,show_spinner=False)
def _hoja():
    return ensure_headers(HOJA,HEADERS)


def reconstruir(values):
    """Ignora versiones incompletas, conserva duplicados idénticos idempotentes."""
    if not values:
        return []
    grupos = {}
    for index,row in enumerate(values[1:]):
        r = dict(zip(values[0],row))
        grupos.setdefault(r.get('Revision',''),[]).append((index,r))
    resultado=[]
    for revision,filas in grupos.items():
        try:
            first=filas[0][1]; total=int(first['Total']); parts={}
            if not revision or not 1<=total<=12:
                continue
            for _,r in filas:
                if any(r.get(k)!=first.get(k) for k in HEADERS if k not in {'Parte','Contenido'}):
                    raise ValueError('Versión contradictoria')
                part=int(r['Parte'])
                if part in parts and parts[part]!=r['Contenido']:
                    raise ValueError('Parte contradictoria')
                parts[part]=r['Contenido']
            if set(parts)!=set(range(total)):
                continue
            payload=''.join(parts[p] for p in range(total))
            if hashlib.sha256(payload.encode()).hexdigest()!=first['SHA256']:
                continue
            doc=json.loads(payload)
            if doc.get('id')!=first['Documento'] or doc.get('cuenta')!=first['Cuenta'] or doc.get('formato')!=first['Formato'] or doc.get('estado')!=first['Estado']:
                continue
            doc.update({'revision':revision,'anterior':first['Anterior'],'guardado_en':first['Fecha'],'_orden':max(i for i,_ in filas)})
            resultado.append(doc)
        except (ValueError,TypeError,KeyError,json.JSONDecodeError):
            continue
    return sorted(resultado,key=lambda r:r['_orden'])


@st.cache_data(ttl=60,show_spinner=False)
def _versiones():
    return reconstruir(retry_google(_hoja().get_all_values))


def listar(todas_versiones=False):
    actor=identidad(); resultado=[]
    for doc in versiones_actuales():
        if not actor['director'] and doc.get('cuenta')!=actor['cuenta']:
            continue
        try:
            autorizar(doc)
        except PermissionError:
            continue
        resultado.append(deepcopy(doc))
    if todas_versiones:
        return resultado
    ultimas={d['id']:d for d in resultado}
    return list(ultimas.values())


def refrescar():
    identidad(); _versiones.clear()


def refrescar_evidencias():
    """Solo invalida fuentes documentales; no vacía ninguna hoja."""
    from data.google import clear_cache
    refrescar()
    for nombre in ('Alumnos','Anexo3_Deteccion','Anexo4_Sugerencias','Anexo5_Eventos',
                   'Registro_Visitas','Relaciones_Expediente','Linea_Tiempo','EPP_Versiones'):
        clear_cache(nombre)


def _firma_guardado(doc, estado, observaciones):
    copia=deepcopy(doc)
    for k in ('revision','anterior','guardado_en','_orden'):copia.pop(k,None)
    return hashlib.sha256(json.dumps([copia,estado,observaciones],ensure_ascii=False,sort_keys=True).encode()).hexdigest()


def _confirmar(saved):
    from data.coordinacion import coordinador
    sin_orden=coordinador() is not None and '_orden' not in saved
    with _control()[0]:
        _control()[1][saved['id']]=saved['revision']
        if sin_orden:
            # El append confirmado no informa aquí del índice canónico. Recuperar
            # por la caché normal de versiones, sin inventar un índice por reloj.
            _versiones.clear()
        else:_recientes()[saved['revision']]=deepcopy(saved)
        if len(_recientes())>1000:
            _versiones.clear()
            _recientes().clear()


def _resolver_intento(clave, firma, permiso=None):
    pendiente=intentos().get(clave)
    if not pendiente:return None
    # Una respuesta perdida nunca autoriza otro append ciego. Primero leer
    # servidor; una lectura fallida conserva el intento para la próxima vez.
    versiones=reconstruir(retry_google(_hoja().get_all_values))
    confirmado=next((v for v in versiones if v['revision']==pendiente['saved']['revision']),None)
    if confirmado is None:
        ultimo=next((v for v in reversed(versiones) if v['id']==clave[0]),None)
        if (ultimo['revision'] if ultimo else '')!=pendiente['saved']['anterior']:
            raise RuntimeError('El documento cambió mientras se verificaba el guardado. Conserva el respaldo y recupera la versión reciente.')
        reservar_escritura()
        from services.planeacion_distribuida import append_confirmable
        append_confirmable(sys.modules[__name__],pendiente['rows'],permiso,firma)
        confirmado=pendiente['saved']
    _confirmar(confirmado)
    del intentos()[clave]
    if pendiente['firma']!=firma:
        raise RuntimeError('Se confirmó el guardado anterior. Tus cambios nuevos siguen aquí; respáldalos y concílialos con la versión recuperada antes de guardar.')
    return deepcopy(confirmado)


def _conciliar_otros_intentos(documento,clave):
    otros=[k for k in list(intentos()) if k[0]==documento and k!=clave]
    if not otros:return
    versiones=reconstruir(retry_google(_hoja().get_all_values))
    for key in otros:
        revision=intentos()[key]['saved']['revision']
        confirmado=next((v for v in versiones if v['revision']==revision),None)
        if confirmado is None:
            from services.planeacion_estabilidad import GuardadoPendiente
            raise GuardadoPendiente(60)
        _confirmar(confirmado)
        del intentos()[key]


def guardar(doc, estado='BORRADOR', observaciones=None):
    actor=autorizar(doc,True)
    return _guardar_version(doc,actor,estado,observaciones)


def _guardar_version(doc,actor,estado='BORRADOR',observaciones=None,aportacion=False):
    """Persistencia común; las entradas públicas verifican edición completa o aporte acotado."""
    from services.planeacion_equipo import validar, sincronizar, aplica
    validar(doc)
    if aplica(doc) and 'equipo' in doc['metadatos']:
        doc=sincronizar(doc)
    if estado not in ESTADOS:
        raise ValueError('Estado no válido.')
    if estado in {'CON_OBSERVACIONES','VALIDADO'} and not actor['director']:
        raise PermissionError('La revisión corresponde a Dirección.')
    if not aportacion and actor['cuenta']!=doc['cuenta'] and estado not in {'CON_OBSERVACIONES','VALIDADO'}:
        raise PermissionError('Dirección revisa sin reescribir el trabajo del autor.')
    from data.coordinacion import coordinador
    compartido=coordinador()
    if compartido:
        from services.planeacion_distribuida import ejecutar
        return ejecutar(sys.modules[__name__],compartido,doc,actor,estado,observaciones,aportacion)
    return _guardar_version_local(doc,actor,estado,observaciones,aportacion)


def _guardar_version_local(doc,actor,estado='BORRADOR',observaciones=None,aportacion=False,versiones_servidor=None,permiso=None):
    clave=(doc['id'],actor['cuenta'],bool(aportacion))
    firma=_firma_guardado(doc,estado,observaciones)
    with candado(doc['id']):
        _conciliar_otros_intentos(doc['id'],clave)
        confirmado=_resolver_intento(clave,firma,permiso)
        if confirmado is not None:return confirmado
        versiones=[v for v in (versiones_actuales() if versiones_servidor is None else versiones_servidor) if v['id']==doc['id']]
        latest=versiones[-1] if versiones else None
        expected=latest['revision'] if latest else ''
        if expected!=doc.get('revision',''):
            raise RuntimeError('Otra sesión guardó cambios. Tu edición sigue aquí; guarda un respaldo y recupera la versión reciente.')
        if latest:
            claves=('ID_Escuela','Curso escolar','Trimestre','Nombre del especialista','Función','Alumnos')
            if latest['cuenta']!=doc['cuenta'] or latest['formato']!=doc['formato'] or any(latest['datos'].get(k)!=doc['datos'].get(k) for k in claves):
                raise PermissionError('No se puede cambiar la identidad de un documento guardado.')
            if not aportacion and latest['metadatos'].get('aportaciones_equipo',{})!=doc['metadatos'].get('aportaciones_equipo',{}):
                raise PermissionError('Las aportaciones se editan desde Trabajo colaborativo, por el profesional de cada área.')
        elif doc['cuenta']!=actor['cuenta']:
            raise PermissionError('Solo el autor puede crear el documento.')
        if estado in {'ENVIADO','VALIDADO'}:
            faltas=revisar(doc)
            if faltas:
                raise ValueError('Antes de enviar: '+ '; '.join(faltas[:3]))
        saved=deepcopy(doc); saved['estado']=estado
        curricular=saved['metadatos'].get('curriculo')
        if curricular:
            from services.curriculo import vincular
            saved=vincular(saved,curricular.get('campo',''),curricular.get('ejes',[]),[r['id'] for r in curricular.get('registros',[])],curricular.get('contexto_local',''),curricular.get('adaptaciones',{}))
        saved.pop('_orden',None)
        if observaciones is not None:
            saved['observaciones_director']=str(observaciones)
        saved['metadatos']['firma_aprobada_por']=actor['nombre'] if estado=='VALIDADO' else ''
        if actor['director']:
            saved['metadatos']['revisado_por']=actor['nombre']
        if latest and _firma_guardado(saved,estado,None)==_firma_guardado(latest,estado,None):
            return deepcopy(latest)
        revision=uuid4().hex
        fecha=datetime.now(ZoneInfo('America/Mexico_City')).isoformat(timespec='microseconds')
        saved.update({'revision':revision,'anterior':expected,'guardado_en':fecha})
        payload=json.dumps(saved,ensure_ascii=False,sort_keys=True)
        if len(payload)>400000:
            raise ValueError('La planeación es demasiado extensa para este respaldo; conserva un archivo local.')
        partes=[payload[i:i+38000] for i in range(0,len(payload),38000)]
        digest=hashlib.sha256(payload.encode()).hexdigest()
        rows=[[saved['id'],revision,expected,fecha,saved['cuenta'],saved['datos']['Nombre del especialista'],
               saved['datos']['ID_Escuela'],json.dumps([a['ID_Alumno'] for a in saved['datos']['Alumnos']]),
               saved['formato'],estado,str(i),str(len(partes)),digest,p] for i,p in enumerate(partes)]
        reservar_escritura()
        intentos()[clave]={'firma':firma,'saved':deepcopy(saved),'rows':rows}
        # No retry_google para append: los fallos ambiguos se reconcilian por
        # revisión estable en _resolver_intento, sin crear otro UUID.
        from services.planeacion_distribuida import append_confirmable
        append_confirmable(sys.modules[__name__],rows,permiso,firma)
        _confirmar(saved)
        del intentos()[clave]
        return saved


def revisar(doc):
    faltas=[]; meta=doc['metadatos']; tablas=doc['tablas']
    if not doc['datos'].get('CCT'):
        faltas.append('completar el CCT')
    if doc['formato']=='XXI' and not (meta.get('fuente_iepp') and meta.get('NEE confirmadas desde IEPP')):
        faltas.append('confirmar el IEPP del plan individual')
    if doc['formato']=='XXI':
        try:
            if int(doc['datos'].get('Vigencia en cursos escolares') or 0) not in (1,2,3):raise ValueError()
        except (ValueError,TypeError):faltas.append('indicar vigencia del PI de uno a tres cursos escolares')
        required=('barreras','necesidades','curriculo','participantes')
    else:
        required=('barreras',) if doc['formato']=='XXV' else ('aprendizajes',)
    for key in required:
        if not any(any(texto(v) for v in row.values()) for row in tablas[key]):
            faltas.append('completar '+key)
    columnas={'XXIII':{'aprendizajes':['Necesidades educativas específicas','Aprendizaje y/u objetivo','Descriptor de logro']},
              'XXV':{'barreras':['Barreras para el Aprendizaje y la Participación','Apoyos y/o ajustes razonables']},
              'XXI':{'barreras':['BAP','Acciones para minimizarla o eliminarla','Responsable','Temporalidad'],
                     'necesidades':['NEE','Aprendizajes y/u Objetivos','Descriptor de Logro','Apoyos o ajustes','Temporalidad'],
                     'curriculo':['NEE','Aprendizajes priorizados y/u objetivos','Descriptor de logro','Temporalidad'],
                     'participantes':['Nombre','Función']}}
    for key,fields in columnas[doc['formato']].items():
        for row in tablas[key]:
            if any(texto(v) for v in row.values()) and any(not texto(row.get(f)) for f in fields):
                faltas.append('completar las celdas requeridas de '+key);break
    if doc['formato']!='XXI' and not any(texto(r.get('Actividades')) and texto(r.get('Recursos')) and texto(r.get('Temporalidad',r.get('Fecha'))) for r in tablas['dosificacion']):
        faltas.append('describir actividades, tiempos y recursos')
    if doc['formato']=='XXIII' and not texto(doc['textos'].get('Evaluación')):
        faltas.append('describir la evaluación formativa')
    from services.planeacion_equipo import revisar as revisar_equipo
    return faltas+revisar_equipo(doc)


def evidencias(doc):
    autorizar(doc)
    fuentes=[]; fallas=[]; alumnos=padron_autorizado().to_dict('records')
    elegidos={texto(a['ID_Alumno']) for a in doc['datos']['Alumnos']}
    try:padron_completo=repo.alumnos().to_dict('records')
    except Exception:padron_completo=[]
    frames={}
    for nombre,reader in [('III',repo.anexo3),('IV',repo.anexo4),('V',repo.anexo5),('ACTA',repo.visitas)]:
        try:
            frames[nombre]=reader()
        except Exception:
            frames[nombre]=pd.DataFrame();fallas.append(nombre)
    for a in alumnos:
        if texto(a.get('ID_Alumno')) not in elegidos:
            continue
        for nombre,frame in [('III',frames['III']),('IV',frames['IV'])]:
            fields=['BAP_Fisicas','BAP_Actitudinales','BAP_Pedagogicas','BAP_Organizativas'] if nombre=='III' else ['Motivo','Sugerencias','Nivel_Cumplimiento_Resultados']
            for r in frame.to_dict('records'):
                if not _vinculo_individual(r,a,padron_completo):continue
                fuentes.append({'tipo':nombre,'alumno':a['ID_Alumno'],'fecha':texto(r.get('Fecha',r.get('Fecha_Elaboracion'))),
                                'registro':texto(r.get('ID_Anexo3',r.get('ID_Anexo4'))),
                                'texto':'\n'.join(f'{k}: {texto(r.get(k))}' for k in fields if texto(r.get(k))), 'alcance':'individual'})
    # Reutiliza la resolución histórica del expediente: IDs, relaciones y legado
    # exacto no ambiguo. No atribuye eventos de homónimos a otro alumno.
    try:
        referencia=repo.alumnos()
        for a in alumnos:
            if texto(a.get('ID_Alumno')) not in elegidos:continue
            events=repo.eventos_alumno(a['ID_Alumno'],texto(a.get('Nombre_Completo')),
                id_escuela=doc['datos']['ID_Escuela'],escuela=doc['datos']['Escuela regular'],alumnos_referencia=referencia)
            for r in events.to_dict('records'):
                if texto(r.get('ID_Alumno')) and texto(r.get('ID_Alumno'))!=texto(a['ID_Alumno']):continue
                if texto(r.get('ID_Escuela')) not in {'',doc['datos']['ID_Escuela']}:continue
                fuentes.append({'tipo':'V','alumno':a['ID_Alumno'],'fecha':texto(r.get('Fecha')),'registro':texto(r.get('ID_Evento')),'texto':texto(r.get('Evento')),'alcance':'individual; vínculo resuelto por el expediente'})
    except Exception:
        fallas.append('V')
        for r in frames['V'].to_dict('records'):
            if texto(r.get('ID_Alumno')) in elegidos and texto(r.get('ID_Escuela')) in {'',doc['datos']['ID_Escuela']} and texto(r.get('Estado')).upper() not in {'RETIRADO','ELIMINADO','ANULADO','DUPLICADO'}:
                fuentes.append({'tipo':'V','alumno':r['ID_Alumno'],'fecha':texto(r.get('Fecha')),'registro':texto(r.get('ID_Evento')),'texto':texto(r.get('Evento')),'alcance':'individual'})
    for r in frames['ACTA'].to_dict('records'):
        for a in alumnos:
            if texto(a.get('ID_Alumno')) in elegidos and _vinculo_individual(r,a,padron_completo):
                fuentes.append({'tipo':'ACTA','alumno':texto(a['ID_Alumno']),'fecha':texto(r.get('Fecha')),'registro':texto(r.get('ID_Visita')),'texto':texto(r.get('Observaciones')),'alcance':'individual'})
    try:
        ultimas={d['id']:d for d in versiones_actuales()}
        for plan in ultimas.values():
            ids_plan={a['ID_Alumno'] for a in plan['datos']['Alumnos']}
            if plan['id']==doc['id'] or plan['datos']['ID_Escuela']!=doc['datos']['ID_Escuela'] or not ids_plan or not ids_plan.issubset(elegidos):continue
            if plan['estado'] not in {'ENVIADO','VALIDADO'}:continue
            from services.planeacion_continuidad import vigente_pi
            if plan['formato']=='XXI' and not vigente_pi(plan,doc['datos']['Curso escolar']):continue
            autorizar(plan)
            contenido={'tablas':plan['tablas'],'textos':plan['textos'],'necesidades_documentadas':plan['metadatos'].get('necesidades_confirmadas','')}
            fuentes.append({'tipo':'PLAN','alumno':','.join(sorted(ids_plan&elegidos)),'fecha':plan.get('guardado_en','')[:10],'registro':plan['id'],'documento_origen':plan['id'],'formato':plan['formato'],'revision':plan['revision'],'texto':json.dumps(contenido,ensure_ascii=False),'alcance':'plan o planeación anterior enviada; no equivale a resultado alcanzado'})
            for seguimiento in plan['metadatos'].get('seguimiento_formativo',[]):
                fuentes.append({'tipo':'SEGUIMIENTO','alumno':','.join(sorted(ids_plan)),'fecha':seguimiento['fecha'],'registro':plan['id']+'-'+seguimiento['fecha'],
                    'texto':seguimiento['hallazgos']+'\nDecisión docente: '+seguimiento['decision'],'alcance':'resultados registrados por el profesional; verificar sus evidencias'})
    except Exception:fallas.append('PLAN')
    try:
        timeline=df_sheet('Linea_Tiempo')
        exp_ids={expediente_id(i) for i in elegidos}
        for r in timeline.to_dict('records'):
            if texto(r.get('Estado')).upper() in {'ANULADO','ELIMINADO','RETIRADO','DUPLICADO'}:continue
            if texto(r.get('ID_Escuela')) not in {'',doc['datos']['ID_Escuela']}:continue
            alumno=texto(r.get('ID_Alumno'))
            if (alumno and alumno in elegidos) or (not alumno and texto(r.get('ID_Expediente')) in exp_ids):
                if not alumno:alumno=next(i for i in elegidos if expediente_id(i)==texto(r.get('ID_Expediente')))
                if any(f['tipo']=='V' and f['fecha']==texto(r.get('Fecha')) and f['texto']==texto(r.get('Descripcion')) for f in fuentes):continue
                fuentes.append({'tipo':'SEGUIMIENTO','alumno':alumno,'fecha':texto(r.get('Fecha')),'registro':texto(r.get('ID_Evento',r.get('ID_Expediente'))),'texto':texto(r.get('Descripcion')),'alcance':'seguimiento del expediente'})
    except Exception:fallas.append('SEGUIMIENTO')
    try:
        from services.epp_modelo import reconstruir as reconstruir_epp, AREAS as AREAS_EPP, conclusion_vigente
        frame_epp=df_sheet('EPP_Versiones')
        informes=[i for i in reconstruir_epp(frame_epp.fillna('').to_dict('records')) if i['alumno'] in elegidos and i['partes']['META']['estado']!='ELIMINADO' and i['ciclo']<=doc['datos']['Curso escolar']]
        ciclos={aid:max(i['ciclo'] for i in informes if i['alumno']==aid) for aid in {i['alumno'] for i in informes}}
        for informe in informes:
            if informe['ciclo']!=ciclos[informe['alumno']]:continue
            for area in (*AREAS_EPP,'Conclusión'):
                parte=informe['partes'].get(area,{})
                contenido=parte.get('contenido',{})
                if not contenido.get('validada') or (area=='Conclusión' and not conclusion_vigente(informe)):continue
                hallazgos={k:v for k,v in contenido.get('campos',{}).items() if v}
                if area=='Conclusión':hallazgos.update(NEE=contenido.get('nee',[]),BAP=contenido.get('bap',[]))
                if not hallazgos:continue
                fuentes.append({'tipo':'EPP','alumno':informe['alumno'],'fecha':parte.get('fecha','')[:10],
                    'registro':informe['id']+'-'+area,'documento_origen':informe['id'],'parte':area,'revision':parte.get('revision',''),
                    'texto':json.dumps(hallazgos,ensure_ascii=False),
                    'alcance':'hallazgos de EPP revisados por el área; no equivale a diagnóstico médico'})
    except Exception as exc:
        if type(exc).__name__!='WorksheetNotFound':fallas.append('EPP')
    fuentes=unificar_fuentes(fuentes)
    for i,r in enumerate(fuentes):
        r['referencia']='E'+str(i+1)
        r['vinculo_verificado']=True
    return fuentes,list(dict.fromkeys(fallas))


def unificar_fuentes(fuentes):
    unicas={}
    for f in fuentes:
        if not texto(f.get('texto')):continue
        key=(f['tipo'],f.get('registro',''),f.get('fecha',''),f['texto'])
        if key not in unicas:unicas[key]=deepcopy(f)
        else:
            ids=set(unicas[key].get('alumno','').split(','))|set(f.get('alumno','').split(','))
            unicas[key]['alumno']=','.join(sorted(ids-{''}))
    return list(unicas.values())


def preparar_contexto(doc):
    from services.materiales_planeacion import fuentes_materiales
    fuentes,fallas=evidencias(doc)
    resultado=deepcopy(doc)
    # Una desconexión no borra el contexto previamente recuperado.
    elegidos={texto(a['ID_Alumno']) for a in doc['datos']['Alumnos']}
    previas=[f for f in doc['metadatos'].get('fuentes',[]) if f.get('tipo') in fallas and f.get('vinculo_verificado') and set(texto(f.get('alumno')).split(','))<=elegidos]
    fuentes=unificar_fuentes(fuentes+previas+fuentes_materiales(doc))
    for i,f in enumerate(fuentes):f['referencia']='E'+str(i+1)
    def firma(rows):return hashlib.sha256(json.dumps(rows,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    cambio=bool(doc['metadatos'].get('fuentes')) and firma(doc['metadatos']['fuentes'])!=firma(fuentes)
    migrar=doc['metadatos'].get('version_contexto')!=VERSION_CONTEXTO
    resultado['metadatos'].update(fuentes=fuentes,contexto_cargado=True,fuentes_pendientes=fallas,version_contexto=VERSION_CONTEXTO)
    if cambio:
        resultado['metadatos']['resumen_anterior_para_revisar']=doc['metadatos'].get('resumen_educativo','')
        resultado['metadatos'].pop('resumen_ia_completo',None)
    if cambio or migrar or not resultado['metadatos'].get('resumen_educativo'):
        resultado['metadatos']['resumen_educativo']=resumen_previo(resultado,fuentes)
    if migrar:
        resultado['metadatos'].pop('propuestas_ia_guardadas',None)
        resultado['metadatos']['aviso_contexto']='El expediente se revisó por alumno. Las actividades ya redactadas se conservan; confirma su pertinencia antes de enviar.'
    from services.planeacion_generacion import prellenar
    from services.planeacion_continuidad import actualizar_vinculos
    resultado=actualizar_vinculos(prellenar(resultado))
    from services.planeacion_colaboracion import clave_guia
    clave=clave_guia(resultado)
    if clave:
        origen=next((d for d in compartidos() if clave_guia(d)==clave),None)
        if origen and origen['id']!=doc['id']:
            from services.planeacion_modalidad import guia_grupal
            guia=guia_grupal(origen)
            ids={a['ID_Alumno'] for a in doc['datos']['Alumnos']}
            guia['filas']=[r for r in guia['filas'] if r['ID_Alumno'] in ids]
            nombres={a['Nombre del alumno'] for a in doc['datos']['Alumnos']}
            guia['as']=[r for r in guia.get('as',[]) if r.get('Nombre alumno') in nombres]
            resultado['metadatos']['guia_compartida']={'documento':origen['id'],'revision':origen['revision']}
            if resultado['metadatos'].get('guia_grupal_manual')!=guia:
                resultado['metadatos']['guia_local_anterior']=resultado['metadatos'].get('guia_grupal_manual',{})
                resultado['metadatos']['guia_grupal_manual']=guia
    return resultado


def compartidos():
    """Solo PI o guías de apoyo, con todos sus alumnos dentro de la asignación actual."""
    from services.planeacion_colaboracion import compartible,clave_guia
    resultado=[];guias=set()
    for doc in {d['id']:d for d in versiones_actuales()}.values():
        if not compartible(doc):continue
        try:autorizar(doc)
        except PermissionError:continue
        clave=clave_guia(doc)
        if clave and clave in guias:continue
        if clave:guias.add(clave)
        resultado.append(deepcopy(doc))
    return resultado


def guardar_aportacion(doc,filas,observaciones):
    from services.planeacion_colaboracion import aportar
    actor=autorizar(doc)
    # Recuperar servidor: jamás persistir tablas o identidad recibidas del editor compartido.
    actual=next((d for d in compartidos() if d['id']==doc['id']),None)
    if not actual:raise PermissionError('No hay un documento compartido autorizado.')
    if doc.get('revision')!=actual.get('revision'):raise RuntimeError('El equipo actualizó el documento. Tu aportación sigue aquí; actualiza y revisa antes de guardar.')
    updated=aportar(actual,actor,filas,observaciones)
    return _guardar_version(updated,actor,'BORRADOR',aportacion=True)


def resumen_previo(doc,fuentes):
    """Borrador local de minimización; la persona revisa antes de transmitirlo."""
    autorizar(doc)
    partes=[f"{f['referencia']} ({f['alcance']}): {f['texto']}" for f in fuentes if f.get('texto')]
    grados=set()
    for alumno in doc['datos']['Alumnos']:
        grado=re.match(r'^\s*([1-6])(?:\D|$)',str(alumno.get('Grado','')))
        if grado:grados.add(int(grado[1]))
    contexto='Alumnos seleccionados: '+str(len(doc['datos']['Alumnos']))+'. Grados registrados: '+(', '.join(str(g)+'°' for g in sorted(grados)) or 'por confirmar')+'.'
    value=(contexto+'\n\n'+'\n\n'.join(partes))[:12000]
    tokens=[doc['datos'].get('Nombre del especialista',''),doc['datos'].get('Escuela regular',''),doc['datos'].get('CCT',''),doc['datos'].get('ID_Escuela','')]
    for alumno in doc['datos']['Alumnos']:
        tokens.extend([alumno.get('ID_Alumno',''),alumno.get('Nombre del alumno',''),alumno.get('Maestro de apoyo','')])
    # Quita también las partes conocidas de nombres, sin adjudicar hechos por nombre.
    for name in list(tokens):tokens.extend(t for t in str(name).split() if len(t)>3)
    for token in sorted(set(tokens),key=len,reverse=True):
        if token:value=re.sub(r'(?<!\w)'+re.escape(str(token))+r'(?!\w)','[dato retirado]',value,flags=re.I)
    value=re.sub(r'\b[A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]\d\b','[CURP retirada]',value,flags=re.I)
    value=re.sub(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}','[contacto retirado]',value)
    value=re.sub(r'(?<!\d)(?:\+?52[\s-]*)?(?:\d[\s()-]*){10}(?!\d)','[contacto retirado]',value)
    return value

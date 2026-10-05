"""Planeaciones versionadas, aditivas y autorizadas en servidor."""
from copy import deepcopy
from datetime import datetime
import hashlib
import json
import re
import threading
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

HOJA = 'Planeaciones_Versiones'
HEADERS = ['Documento','Revision','Anterior','Fecha','Cuenta','Autor','Escuela_ID','Alumnos_JSON',
           'Formato','Estado','Parte','Total','SHA256','Contenido']
ESTADOS = {'BORRADOR','ENVIADO','CON_OBSERVACIONES','VALIDADO'}


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


def nueva(formato, ids, ciclo=2026, trimestre=1):
    actor = identidad()
    if formato != 'XXI' and formato != ('XXV' if actor['area']=='Trabajo Social' else 'XXIII'):
        raise PermissionError('Utiliza el formato correspondiente a tu función.')
    doc = crear_plantilla(formato, ids, padron_autorizado().to_dict('records'),
                          autor=actor['nombre'],funcion=actor['area'],ciclo_inicio=ciclo,
                          trimestre=trimestre,escuelas=repo.escuelas().to_dict('records'),
                          fecha=datetime.now(ZoneInfo('America/Mexico_City')).date())
    doc.update({'id':uuid4().hex,'revision':'','cuenta':actor['cuenta'],'observaciones_director':''})
    doc['metadatos'].update({'resumen_educativo':'','fuente_iepp':'','necesidades_confirmadas':'',
                             'referente_curricular':'','revisado_por':''})
    return doc


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
    por_revision.update(_recientes())
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


def guardar(doc, estado='BORRADOR', observaciones=None):
    actor=autorizar(doc,True)
    if estado not in ESTADOS:
        raise ValueError('Estado no válido.')
    if estado in {'CON_OBSERVACIONES','VALIDADO'} and not actor['director']:
        raise PermissionError('La revisión corresponde a Dirección.')
    if actor['cuenta']!=doc['cuenta'] and estado not in {'CON_OBSERVACIONES','VALIDADO'}:
        raise PermissionError('Dirección revisa sin reescribir el trabajo del autor.')
    lock,heads=_control()
    with lock:
        versiones=[v for v in versiones_actuales() if v['id']==doc['id']]
        latest=versiones[-1] if versiones else None
        known=heads.get(doc['id'])
        expected=known or (latest['revision'] if latest else '')
        if expected!=doc.get('revision',''):
            raise RuntimeError('Otra sesión guardó cambios. Tu edición sigue aquí; guarda un respaldo y recupera la versión reciente.')
        if latest:
            claves=('ID_Escuela','Curso escolar','Trimestre','Nombre del especialista','Función','Alumnos')
            if latest['cuenta']!=doc['cuenta'] or latest['formato']!=doc['formato'] or any(latest['datos'].get(k)!=doc['datos'].get(k) for k in claves):
                raise PermissionError('No se puede cambiar la identidad de un documento guardado.')
        elif doc['cuenta']!=actor['cuenta']:
            raise PermissionError('Solo el autor puede crear el documento.')
        if estado in {'ENVIADO','VALIDADO'}:
            faltas=revisar(doc)
            if faltas:
                raise ValueError('Antes de enviar: '+ '; '.join(faltas[:3]))
        saved=deepcopy(doc); saved['estado']=estado
        saved.pop('_orden',None)
        if observaciones is not None:
            saved['observaciones_director']=str(observaciones)
        saved['metadatos']['firma_aprobada_por']=actor['nombre'] if estado=='VALIDADO' else ''
        if actor['director']:
            saved['metadatos']['revisado_por']=actor['nombre']
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
        retry_google(lambda:_hoja().append_rows(rows,value_input_option='RAW'))
        heads[doc['id']]=revision
        _recientes()[revision]=deepcopy(saved)
        if len(_recientes())>1000:
            _versiones.clear()
            _recientes().clear()
        return saved


def revisar(doc):
    faltas=[]; meta=doc['metadatos']; tablas=doc['tablas']
    if not doc['datos'].get('CCT'):
        faltas.append('completar el CCT')
    if doc['formato']=='XXI' and not (meta.get('fuente_iepp') and meta.get('NEE confirmadas desde IEPP')):
        faltas.append('confirmar el IEPP del plan individual')
    if doc['formato']=='XXI':
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
    return faltas


def evidencias(doc):
    autorizar(doc)
    fuentes=[]; fallas=[]; alumnos=padron_autorizado().to_dict('records')
    elegidos={a['ID_Alumno'] for a in doc['datos']['Alumnos']}
    frames={}
    for nombre,reader in [('III',repo.anexo3),('IV',repo.anexo4),('V',repo.anexo5),('ACTA',repo.visitas)]:
        try:
            frames[nombre]=reader()
        except Exception:
            frames[nombre]=pd.DataFrame();fallas.append(nombre)
    for a in alumnos:
        if texto(a.get('ID_Alumno')) not in elegidos:
            continue
        for nombre,frame in [('III',baps_de_alumno(frames['III'],a)),('IV',sugerencias_de_alumno(frames['IV'],a))]:
            fields=['BAP_Fisicas','BAP_Actitudinales','BAP_Pedagogicas','BAP_Organizativas'] if nombre=='III' else ['Motivo','Sugerencias','Nivel_Cumplimiento_Resultados']
            for r in frame.to_dict('records'):
                grupal=texto(r.get('ID_Alumno')).startswith('GRUPO-') or texto(r.get('Nombre_Alumno')).startswith('Grupo ')
                fuentes.append({'tipo':nombre,'alumno':a['ID_Alumno'],'fecha':texto(r.get('Fecha',r.get('Fecha_Elaboracion'))),
                                'registro':texto(r.get('ID_Anexo3',r.get('ID_Anexo4'))),
                                'texto':'\n'.join(f'{k}: {texto(r.get(k))}' for k in fields if texto(r.get(k))), 'alcance':'grupo vinculado' if grupal else 'individual'})
    # Reutiliza la resolución histórica del expediente: IDs, relaciones y legado
    # exacto no ambiguo. No atribuye eventos de homónimos a otro alumno.
    try:
        referencia=repo.alumnos()
        for a in alumnos:
            if texto(a.get('ID_Alumno')) not in elegidos:continue
            events=repo.eventos_alumno(a['ID_Alumno'],texto(a.get('Nombre_Completo')),
                id_escuela=doc['datos']['ID_Escuela'],escuela=doc['datos']['Escuela regular'],alumnos_referencia=referencia)
            for r in events.to_dict('records'):
                if texto(r.get('ID_Escuela')) not in {'',doc['datos']['ID_Escuela']}:continue
                fuentes.append({'tipo':'V','alumno':a['ID_Alumno'],'fecha':texto(r.get('Fecha')),'registro':texto(r.get('ID_Evento')),'texto':texto(r.get('Evento')),'alcance':'individual; vínculo resuelto por el expediente'})
    except Exception:
        fallas.append('V')
        for r in frames['V'].to_dict('records'):
            if texto(r.get('ID_Alumno')) in elegidos and texto(r.get('ID_Escuela')) in {'',doc['datos']['ID_Escuela']} and texto(r.get('Estado')).upper() not in {'RETIRADO','ELIMINADO','ANULADO','DUPLICADO'}:
                fuentes.append({'tipo':'V','alumno':r['ID_Alumno'],'fecha':texto(r.get('Fecha')),'registro':texto(r.get('ID_Evento')),'texto':texto(r.get('Evento')),'alcance':'individual'})
    escuela=normalizar_texto(doc['datos']['Escuela regular'])
    for r in frames['ACTA'].to_dict('records'):
        if normalizar_texto(r.get('Escuela',''))==escuela and texto(r.get('Estatus')).upper() not in {'ANULADO','ELIMINADO','RETIRADO'}:
            fuentes.append({'tipo':'ACTA','alumno':'','fecha':texto(r.get('Fecha')),'registro':texto(r.get('ID_Visita')),'texto':texto(r.get('Observaciones')),'alcance':'contexto escolar; no atribuye atención individual'})
    try:
        ultimas={d['id']:d for d in versiones_actuales()}
        for plan in ultimas.values():
            ids_plan={a['ID_Alumno'] for a in plan['datos']['Alumnos']}
            if plan['id']==doc['id'] or plan['datos']['ID_Escuela']!=doc['datos']['ID_Escuela'] or not (ids_plan&elegidos):continue
            if plan['estado'] not in {'ENVIADO','VALIDADO'}:continue
            autorizar(plan)
            contenido={'tablas':plan['tablas'],'textos':plan['textos'],'necesidades_documentadas':plan['metadatos'].get('necesidades_confirmadas','')}
            fuentes.append({'tipo':'PLAN','alumno':','.join(sorted(ids_plan&elegidos)),'fecha':plan.get('guardado_en','')[:10],'registro':plan['id'],'revision':plan['revision'],'texto':json.dumps(contenido,ensure_ascii=False),'alcance':('plan o planeación anterior enviada' if ids_plan.issubset(elegidos) else 'planeación previa del grupo; contexto grupal')+'; no equivale a resultado alcanzado'})
    except Exception:fallas.append('PLAN')
    try:
        timeline=df_sheet('Linea_Tiempo')
        exp_ids={expediente_id(i) for i in elegidos}
        for r in timeline.to_dict('records'):
            if texto(r.get('Estado')).upper() in {'ANULADO','ELIMINADO','RETIRADO','DUPLICADO'}:continue
            if texto(r.get('ID_Escuela')) not in {'',doc['datos']['ID_Escuela']}:continue
            alumno=texto(r.get('ID_Alumno'))
            if (alumno and alumno in elegidos) or (not alumno and texto(r.get('ID_Expediente')) in exp_ids):
                if any(f['tipo']=='V' and f['fecha']==texto(r.get('Fecha')) and f['texto']==texto(r.get('Descripcion')) for f in fuentes):continue
                fuentes.append({'tipo':'SEGUIMIENTO','alumno':alumno,'fecha':texto(r.get('Fecha')),'registro':texto(r.get('ID_Evento',r.get('ID_Expediente'))),'texto':texto(r.get('Descripcion')),'alcance':'seguimiento del expediente'})
    except Exception:fallas.append('SEGUIMIENTO')
    fuentes=unificar_fuentes(fuentes)
    for i,r in enumerate(fuentes):
        r['referencia']='E'+str(i+1)
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
    fuentes,fallas=evidencias(doc)
    resultado=deepcopy(doc)
    # Una desconexión no borra el contexto previamente recuperado.
    previas=[f for f in doc['metadatos'].get('fuentes',[]) if f.get('tipo') in fallas]
    fuentes=unificar_fuentes(fuentes+previas)
    for i,f in enumerate(fuentes):f['referencia']='E'+str(i+1)
    resultado['metadatos'].update(fuentes=fuentes,contexto_cargado=True,fuentes_pendientes=fallas)
    if not resultado['metadatos'].get('resumen_educativo'):
        resultado['metadatos']['resumen_educativo']=resumen_previo(resultado,fuentes)
    return resultado


def resumen_previo(doc,fuentes):
    """Borrador local de minimización; la persona revisa antes de transmitirlo."""
    autorizar(doc)
    partes=[f"{f['referencia']} ({f['alcance']}): {f['texto']}" for f in fuentes if f.get('texto')]
    value='\n\n'.join(partes)[:12000]
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

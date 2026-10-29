"""Índice autorizado de documentos; no escribe, genera archivos ni cambia modalidad."""
from copy import deepcopy
import hashlib
import os
import re
from services import planeacion as s
from services.planeacion_colaboracion import compartible
from utils.text import normalizar_texto


def habilitada():
    return os.environ.get('USAER_NAVEGACION_DOCUMENTOS','0').lower() not in {'0','false','off'}


def enlace_id(documento):
    # La URL no contiene nombres, alumno, escuela, cuenta ni el ID estructurado.
    return hashlib.sha256(('usaer-plan-v1|'+str(documento)).encode()).hexdigest()


def contexto(doc,actor):
    datos=doc['datos']
    return {'documento':doc['id'],'escuela':datos.get('ID_Escuela',''),
            'alumnos':tuple(str(a['ID_Alumno']) for a in datos.get('Alumnos',[])),
            'grupos':tuple(sorted({(str(a.get('Grado','')),str(a.get('Grupo',''))) for a in datos.get('Alumnos',[])})),
            'formato':doc['formato'],'modalidad':doc.get('metadatos',{}).get('modalidad_planeacion',''),
            'ciclo':datos.get('Curso escolar',''),'cuenta':actor['cuenta'],
            'rol':actor.get('rol',''),'area':actor.get('area','')}


def indice(locales=()):
    """Fuentes canónicas, un documento por ID y comprobación actual de permisos."""
    actor=s.identidad();frame=s.padron_autorizado()
    propios=s.listar()
    docs={d['id']:deepcopy(d) for d in s.compartidos()}
    docs.update({d['id']:deepcopy(d) for d in propios if actor['director'] or d['cuenta']==actor['cuenta']})
    for d in locales:
        if d['cuenta']==actor['cuenta'] or d['id'] in docs:
            try:s.autorizar(d,frame=frame)
            except (PermissionError,ValueError):continue
            docs[d['id']]=deepcopy(d)
    salida=[]
    for d in docs.values():
        if d.get('metadatos',{}).get('borrador_eliminado'):continue
        try:s.autorizar(d,frame=frame)
        except (PermissionError,ValueError):continue
        salida.append(d)
    return sorted(salida,key=lambda d:d.get('guardado_en',''),reverse=True)


def resolver(token,locales=()):
    if not isinstance(token,str) or not re.fullmatch('[0-9a-f]{64}',token):
        raise PermissionError('El enlace no corresponde a una planeación disponible en tu cuenta.')
    doc=next((d for d in indice(locales) if enlace_id(d['id'])==token),None)
    if doc is None:raise PermissionError('La planeación no está disponible en tu asignación actual. No se abrió otro documento.')
    s.autorizar(doc)
    return doc


def ruta(doc,actor):
    if doc['cuenta']==actor['cuenta']:return 'propio'
    if actor['director']:return 'lectura'
    if compartible(doc):return 'compartido'
    return 'lectura'


def tipo(doc):
    if doc['formato']=='XXI':return 'Plan de intervención'
    modo=doc.get('metadatos',{}).get('modalidad_planeacion')
    if modo=='grupal':return 'Grupal'
    if modo=='individual':return 'Individual'
    if modo=='especialista':return 'Intervención de especialista'
    return 'Formato guardado'


def filtrar(docs,cuenta,buscar='',escuela='',grupo='',formato='',ciclo='',vista='Todas',pendientes=()):
    from services.planeacion_ambito import etiqueta
    consulta=' '.join(normalizar_texto(buscar).split());pending=set(pendientes)
    resultado=[]
    for d in docs:
        datos=d['datos']
        if escuela and str(datos.get('ID_Escuela',''))!=escuela:continue
        if grupo and etiqueta(d)!=grupo:continue
        if formato and tipo(d)!=formato:continue
        if ciclo and datos.get('Curso escolar','')!=ciclo:continue
        if vista=='Propias' and d['cuenta']!=cuenta:continue
        if vista=='Compartidas' and d['cuenta']==cuenta:continue
        if vista=='Pendientes' and d['id'] not in pending:continue
        if vista=='Borradores' and d.get('estado')!='BORRADOR':continue
        texto=' '.join([tipo(d),datos.get('Escuela regular',''),etiqueta(d),datos.get('Curso escolar',''),
                        *[a.get('Nombre del alumno','') for a in datos.get('Alumnos',[])]])
        if consulta and consulta not in ' '.join(normalizar_texto(texto).split()):continue
        resultado.append(d)
    return sorted(resultado,key=lambda d:(d['id'] in pending,d.get('guardado_en','')),reverse=True)


def solo_lectura(spec):
    """Proyección de interfaz: ninguna celda o acción aparenta poder guardarse."""
    result=deepcopy(spec)
    def recorrer(value):
        if isinstance(value,dict):
            if 'editable' in value:value.update(editable=False,target=None)
            for key in ('add','delete'):
                if key in value:value[key]=False
            for child in value.values():recorrer(child)
        elif isinstance(value,list):
            for child in value:recorrer(child)
    recorrer(result)
    result.update(solo_lectura=True,pendientes=[])
    return result

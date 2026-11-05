"""Solicitudes de expedientes del flujo original, con versiones SQL aditivas."""
import base64
from datetime import datetime, timezone
from io import BytesIO
import hashlib
import json
from typing import Literal
from uuid import uuid4

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text
from data.database import CambioSPA, OficioComision, get_session
from data.sql_repository import _registrar_cambio_spa, guardar_oficio_comision_sql

ESTADOS = ('Recibida', 'En revisión', 'En preparación', 'Respondida', 'Entregada')

class Solicitud(BaseModel):
    model_config = ConfigDict(extra='forbid')
    clave: str = Field(pattern=r'^[a-f0-9]{32}$')
    tipo: Literal['Interna','Externa'] = 'Interna'
    alumnos: list[str] = Field(default_factory=list,max_length=100)
    origen: str = Field(default='',max_length=250)
    expedientes: str = Field(default='',max_length=4000)
    referencia: str = Field(default='',max_length=500)
    solicitud: str = Field(min_length=1,max_length=4000)

class Seguimiento(BaseModel):
    model_config = ConfigDict(extra='forbid')
    revision: str = Field(max_length=64)
    estado: Literal['Recibida','En revisión','En preparación','Respondida','Entregada']
    seguimiento: str = Field(max_length=4000)

class Respuesta(BaseModel):
    model_config = ConfigDict(extra='forbid')
    revision: str = Field(max_length=64)
    destinatario: str = Field(min_length=1,max_length=250)
    texto: str = Field(min_length=1,max_length=4000)
    ciclo: str = Field(pattern=r'^20\d{2}-20\d{2}$')
    nombre_direccion: str = Field(default='',max_length=250)

def gestion(user):
    # No se infiere una delegación administrativa a partir del nombre del personal.
    if not user.director:
        raise HTTPException(403,'La gestión requiere Dirección; las delegaciones deben estar verificadas.')

def ultima(db, ident):
    row=db.query(CambioSPA).filter_by(tipo='tramite',documento_id=ident).order_by(CambioSPA.fecha.desc(),CambioSPA.id.desc()).first()
    if not row:raise HTTPException(404,'Solicitud no disponible.')
    return json.loads(row.contenido)

def autorizar(doc,user,exigir):
    if user.director:return
    if doc['autor_id']!=user.id_usuario or doc['tipo']!='Interna':raise HTTPException(404,'Solicitud no disponible.')
    for aid in doc['alumnos']:exigir(aid,user)

def bloqueo(db,ident):
    if db.bind.dialect.name=='postgresql':
        db.execute(text('SELECT pg_advisory_xact_lock(hashtext(:clave))'),{'clave':'tramite:'+ident})
    else:db.execute(text('BEGIN IMMEDIATE'))

def registrar(db,doc,user):
    anterior=doc.get('revision')
    doc['revision']=uuid4().hex
    doc['actualizado']=datetime.now(timezone.utc).isoformat()
    _registrar_cambio_spa(db,'tramite',doc['id'],doc,user.usuario,anterior)
    db.flush()
    return doc

def consultar(ident,user,exigir):
    with get_session() as db:
        doc=ultima(db,ident);autorizar(doc,user,exigir);return doc

def listar(user,exigir):
    with get_session() as db:
        ids=db.query(CambioSPA.documento_id).filter_by(tipo='tramite').distinct()
        resultado=[]
        for (ident,) in ids:
            doc=ultima(db,ident)
            try:autorizar(doc,user,exigir)
            except HTTPException:continue
            resultado.append(doc)
        return sorted(resultado,key=lambda d:(d['fecha'],d['id']),reverse=True)

def crear(payload,user,exigir):
    if not payload.solicitud.strip():raise HTTPException(422,'Escribe el motivo de la solicitud.')
    datos=payload.model_dump(exclude={'clave'})
    datos['alumnos']=list(dict.fromkeys(datos['alumnos']))
    if datos['tipo']=='Interna':
        if not user.director and user.area!='Aprendizaje':raise HTTPException(403,'Esta función corresponde al apoyo autorizado.')
        if not datos['alumnos']:raise HTTPException(422,'Selecciona alumnos autorizados.')
        datos['origen']='USAER 02-E'
        for aid in datos['alumnos']:exigir(aid,user)
    else:
        gestion(user)
        if datos['alumnos'] or not datos['origen'].strip() or not datos['expedientes'].strip():raise HTTPException(422,'Indica origen y expedientes externos; no asignes alumnos internos.')
    ident='tramite-'+payload.clave
    with get_session() as db:
        bloqueo(db,ident)
        existe=db.query(CambioSPA).filter_by(tipo='tramite',documento_id=ident).first()
        if existe:
            doc=ultima(db,ident);autorizar(doc,user,exigir)
            if any(doc[k]!=v for k,v in datos.items()):raise HTTPException(409,'La clave corresponde a otra solicitud.')
            return doc
        doc={'id':ident,**datos,'autor_id':user.id_usuario,'autor':user.usuario,
             'fecha':datetime.now(timezone.utc).isoformat(),'estado':'Recibida','seguimiento':'','respuesta':None}
        registrar(db,doc,user);db.commit();return doc

def actualizar(ident,payload,user,exigir):
    gestion(user)
    with get_session() as db:
        bloqueo(db,ident);doc=ultima(db,ident);autorizar(doc,user,exigir)
        if doc['revision']!=payload.revision:raise HTTPException(409,'La solicitud cambió. Reábrela.')
        doc.update(estado=payload.estado,seguimiento=payload.seguimiento)
        registrar(db,doc,user);db.commit();return doc

def responder(ident,payload,user,exigir):
    from documents.tramites import _texto
    gestion(user)
    for valor in (payload.destinatario,payload.texto,payload.nombre_direccion):_texto(valor)
    if not payload.destinatario.strip() or not payload.texto.strip():raise HTTPException(422,'Completa destinatario y respuesta.')
    if int(payload.ciclo[5:])!=int(payload.ciclo[:4])+1:raise HTTPException(422,'Ciclo no válido.')
    with get_session() as db:
        # Mismo bloqueo central que el emisor de oficios de comisión: ningún folio compite.
        db.execute(text('LOCK TABLE oficios_comision IN SHARE ROW EXCLUSIVE MODE' if db.bind.dialect.name=='postgresql' else 'BEGIN IMMEDIATE'))
        if db.bind.dialect.name=='postgresql':bloqueo(db,ident)
        doc=ultima(db,ident);autorizar(doc,user,exigir)
        if doc.get('respuesta'):
            previo=doc['respuesta']
            if any(previo[k]!=v for k,v in {'Director_Escuela':payload.destinatario,'Destino':payload.texto,'Ciclo':payload.ciclo,'Nombre_Direccion':payload.nombre_direccion}.items()):raise HTTPException(409,'La respuesta ya emitida se conserva. No se sustituye su folio.')
            return doc
        if doc['revision']!=payload.revision:raise HTTPException(409,'La solicitud cambió. Reábrela.')
        fecha=datetime.now(timezone.utc).date().isoformat()
        # El texto completo vive versionado en la respuesta; la reserva central tiene referencia explícita.
        registro={'Clave_Operacion':'TRAMITE-EXPEDIENTE:'+ident,'Fecha_Emision':fecha,'Fecha_Comision':fecha,
                  'Escuela':doc['origen'][:255],'Maestra_Apoyo':user.nombre,'Director_Escuela':payload.destinatario,
                  'Asunto':'RESPUESTA A SOLICITUD DE EXPEDIENTES','Destino':'Respuesta íntegra en '+ident,
                  'Horario':ident,'Estado':'PREPARADO PARA FIRMA'}
        oficio=guardar_oficio_comision_sql(registro,sesion=db)
        doc['respuesta']={**oficio,'Destino':payload.texto,'Ciclo':payload.ciclo,'Nombre_Direccion':payload.nombre_direccion}
        doc['estado']='En preparación';registrar(db,doc,user);db.commit();return doc

def historial(ident,user,exigir):
    consultar(ident,user,exigir)
    with get_session() as db:
        return [{'revision':r.revision,'fecha':r.fecha.isoformat(),'autor':r.autor,'documento':json.loads(r.contenido)}
                for r in db.query(CambioSPA).filter_by(tipo='tramite',documento_id=ident).order_by(CambioSPA.fecha.desc(),CambioSPA.id.desc()).limit(50)]

def adjuntar(ident,tipo,nombre,contenido,user,exigir):
    from PIL import Image
    gestion(user);consultar(ident,user,exigir)
    if tipo not in ('Oficio recibido','Acuse de recibido'):raise HTTPException(422,'Tipo de comprobante no válido.')
    if not contenido or len(contenido)>5*1024*1024:raise HTTPException(422,'Selecciona una imagen de hasta 5 MB.')
    try:
        with Image.open(BytesIO(contenido)) as image:
            formato=image.format
            if formato not in ('JPEG','PNG','WEBP') or image.width*image.height>25000000:raise ValueError
            image.verify()
    except Exception:raise HTTPException(422,'Imagen JPG, PNG o WEBP no válida.') from None
    digest=hashlib.sha256(contenido).hexdigest();aid=hashlib.sha256((ident+tipo+digest).encode()).hexdigest()
    doc={'revision':aid,'tipo':tipo,'nombre':nombre.replace('\\','/').split('/')[-1][:180],
         'mime':{'JPEG':'image/jpeg','PNG':'image/png','WEBP':'image/webp'}[formato],
         'sha256':digest,'contenido':base64.b64encode(contenido).decode('ascii'),'tramite':ident}
    with get_session() as db:
        bloqueo(db,ident)
        if not db.query(CambioSPA).filter_by(tipo='tramite_adjunto',documento_id=aid).first():
            _registrar_cambio_spa(db,'tramite_adjunto',aid,doc,user.usuario,None)
        db.commit()
    return {'id':aid}

def adjuntos(ident,user,exigir,aid=None):
    consultar(ident,user,exigir)
    with get_session() as db:
        query=db.query(CambioSPA).filter_by(tipo='tramite_adjunto')
        if aid:query=query.filter_by(documento_id=aid)
        else:query=query.filter(CambioSPA.contenido.contains(ident,autoescape=True))
        salida=[]
        for row in query:
            doc=json.loads(row.contenido)
            if doc['tramite']!=ident:continue
            if aid:
                datos=base64.b64decode(doc['contenido'],validate=True)
                if hashlib.sha256(datos).hexdigest()!=doc['sha256']:raise HTTPException(409,'Comprobante requiere revisión de integridad.')
                return doc,datos
            salida.append({'id':row.documento_id,**{k:doc[k] for k in ('tipo','nombre','mime','sha256')}})
        if aid:raise HTTPException(404,'Comprobante no disponible.')
        return salida

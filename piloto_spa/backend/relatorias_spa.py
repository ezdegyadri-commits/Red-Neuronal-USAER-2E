"""Relatoría institucional de Dirección con historial y formato original."""
from datetime import date
import json
from uuid import uuid4

from fastapi import HTTPException
from pydantic import BaseModel, Field
from typing import Literal

from data.database import RegistroVisita, get_session
from data.sql_repository import _registrar_cambio_spa, historial_spa_sql

TIPO = "RELATORIA-SPA"


class CapturaRelatoria(BaseModel):
    fecha: date
    tipo_junta: Literal["Junta de USAER", "Junta de Zona"] = "Junta de USAER"
    modalidad_junta: Literal["Junta Académica", "Sesión de CTE", "Junta de Zona"] = "Junta Académica"
    sesion: str = Field(default="", max_length=120)
    tema: str = Field(default="", max_length=500)
    contenido: str = Field(min_length=1, max_length=50000)
    num_asistentes: int = Field(default=6, ge=1, le=30)
    nombre_director: str = Field(default="", max_length=255)
    revision: str | None = Field(default=None, max_length=64)


def _cargar(row):
    if row is None or row.tipo_acta != TIPO:
        raise HTTPException(404, "Relatoría no disponible.")
    try:
        datos = json.loads(row.evidencia)["relatoria"]
        if not isinstance(datos, dict):
            raise ValueError
        return datos
    except (KeyError, TypeError, ValueError):
        raise HTTPException(409, "La relatoría requiere conciliación.") from None


def listar():
    with get_session() as db:
        return [{"id":r.id,"fecha":r.fecha,"tema":r.motivo}
                for r in db.query(RegistroVisita).filter_by(tipo_acta=TIPO).order_by(
                    RegistroVisita.fecha.desc(), RegistroVisita.id)]


def obtener(ident):
    with get_session() as db:
        return {"id":ident, **_cargar(db.get(RegistroVisita,ident))}


def guardar(payload, user, ident=None):
    datos = payload.model_dump(mode="json", exclude={"revision"})
    if not datos["contenido"].strip():
        raise HTTPException(422, "Captura el contenido de la relatoría.")
    if datos["tipo_junta"] == "Junta de Zona":
        datos["modalidad_junta"] = "Junta de Zona"
        datos["nombre_director"] = ""
    elif datos["modalidad_junta"] == "Junta de Zona":
        raise HTTPException(422, "Confirma la modalidad de la junta USAER.")
    with get_session() as db:
        anterior = ""
        if ident:
            row = db.query(RegistroVisita).filter_by(id=ident).with_for_update().one_or_none()
            anterior = _cargar(row)["revision"]
            if payload.revision != anterior:
                raise HTTPException(409, "La relatoría cambió. Reabre la revisión actual.")
        else:
            if payload.revision:
                raise HTTPException(422, "Una relatoría nueva no tiene revisión previa.")
            ident = "relatoria-" + uuid4().hex
            row = RegistroVisita(id=ident,tipo_acta=TIPO,estatus="GUARDADA",personal=user.usuario)
            db.add(row)
        datos["revision"] = uuid4().hex
        row.fecha, row.motivo = datos["fecha"], datos["tema"]
        row.evidencia = json.dumps({"relatoria":datos},ensure_ascii=False)
        _registrar_cambio_spa(db,"relatoria",ident,datos,user.usuario,anterior or None)
        db.commit()
    return {"id":ident,"revision":datos["revision"]}


def historial(ident):
    obtener(ident)
    return historial_spa_sql("relatoria",ident)


def pdf(ident):
    from documents.relatorias import generar_pdf_oficial

    doc = obtener(ident)
    return generar_pdf_oficial(doc["contenido"],doc["num_asistentes"],fecha=date.fromisoformat(doc["fecha"]),
        sesion=doc["sesion"],tema=doc["tema"],tipo_junta=doc["tipo_junta"],modalidad_junta=doc["modalidad_junta"],
        nombre_director=doc["nombre_director"],incluir_sello=False)

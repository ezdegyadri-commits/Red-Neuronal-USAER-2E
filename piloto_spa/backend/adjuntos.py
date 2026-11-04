"""Archivo PDF del expediente sintético. Los binarios nunca se sirven en línea."""
from datetime import datetime, timezone
import hashlib
from pathlib import PurePosixPath
import re
import uuid

import pymupdf
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import defer

from data.database import Alumno, AdjuntoExpedienteSPA, get_session

LIMITE_BYTES = 5 * 1024 * 1024
_ACCIONES = re.compile(r"/(?:JavaScript|JS|Launch|EmbeddedFile|EmbeddedFiles|RichMedia|OpenAction|AA|XFA)\b")


def _resumen(row):
    return {"id": row.id, "nombre": row.nombre, "bytes": row.bytes, "sha256": row.sha256,
            "autor": row.autor, "fecha": row.fecha.isoformat()}


def listar(alumno):
    with get_session() as db:
        return [_resumen(r) for r in db.scalars(select(AdjuntoExpedienteSPA).options(defer(AdjuntoExpedienteSPA.contenido)).where(
            AdjuntoExpedienteSPA.alumno_id == alumno
        ).order_by(AdjuntoExpedienteSPA.fecha.desc())).all()]


def validar_pdf(nombre, contenido):
    if (not nombre or len(nombre) > 120 or chr(92) in nombre or PurePosixPath(nombre).name != nombre
            or any(ord(c) < 32 for c in nombre) or not nombre.lower().endswith(".pdf")):
        raise HTTPException(422, "El nombre debe corresponder a un archivo PDF.")
    if not contenido.startswith(b"%PDF-") or len(contenido) > LIMITE_BYTES:
        raise HTTPException(422, "Adjunta un PDF de hasta 5 MiB.")
    try:
        with pymupdf.open(stream=contenido, filetype="pdf") as pdf:
            if (pdf.needs_pass or pdf.is_repaired or not 1 <= pdf.page_count <= 40
                    or pdf.xref_length() > 5000 or pdf.embfile_count()
                    or any(_ACCIONES.search(pdf.xref_object(i)) for i in range(1, pdf.xref_length()))):
                raise HTTPException(422, "Usa un PDF simple, sin cifrado, archivos incrustados ni acciones activas.")
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(422, "PDF inválido.") from exc


def guardar(alumno, nombre, autor, contenido):
    validar_pdf(nombre, contenido)
    with get_session() as db:
        if not db.scalar(select(Alumno.id).where(Alumno.id == alumno).with_for_update()):
            raise HTTPException(404, "Expediente no disponible.")
        huella = hashlib.sha256(contenido).hexdigest()
        previo = db.scalar(select(AdjuntoExpedienteSPA).where(
            AdjuntoExpedienteSPA.alumno_id == alumno, AdjuntoExpedienteSPA.sha256 == huella))
        if previo:
            return _resumen(previo)
        total, peso = db.execute(select(func.count(), func.coalesce(func.sum(AdjuntoExpedienteSPA.bytes), 0))
                                 .where(AdjuntoExpedienteSPA.alumno_id == alumno)).one()
        if total >= 20 or peso + len(contenido) > 25 * 1024 * 1024:
            raise HTTPException(409, "Se alcanzó el límite de adjuntos del expediente.")
        row = AdjuntoExpedienteSPA(id=uuid.uuid4().hex, alumno_id=alumno, nombre=nombre,
                                   autor=autor, bytes=len(contenido), sha256=huella,
                                   contenido=contenido, fecha=datetime.now(timezone.utc))
        db.add(row)
        db.commit()
        return _resumen(row)


def descargar(alumno, id_doc):
    with get_session() as db:
        row = db.scalar(select(AdjuntoExpedienteSPA).where(
            AdjuntoExpedienteSPA.id == id_doc, AdjuntoExpedienteSPA.alumno_id == alumno))
        if not row:
            raise HTTPException(404, "Adjunto no disponible.")
        return row.nombre, row.contenido

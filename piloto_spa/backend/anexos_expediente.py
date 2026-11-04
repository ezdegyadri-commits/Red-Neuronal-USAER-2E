"""Operaciones del expediente SPA sobre los anexos canónicos III, IV y V."""
from datetime import date
import uuid

import pandas as pd
from fastapi import HTTPException
from sqlalchemy import select, update

from data.database import Anexo3Deteccion, Anexo4Sugerencia, Anexo5Evento, CambioSPA, get_session
from data.sql_repository import _registrar_cambio_spa

MODELOS = {3: Anexo3Deteccion, 4: Anexo4Sugerencia, 5: Anexo5Evento}
CAMPOS = {
    3: {"fecha": "Fecha", "bap_fisicas": "BAP_Fisicas", "bap_actitudinales": "BAP_Actitudinales",
        "bap_pedagogicas": "BAP_Pedagogicas", "bap_organizativas": "BAP_Organizativas"},
    4: {"fecha_elaboracion": "Fecha_Elaboracion", "ciclo_escolar": "Ciclo_Escolar", "trimestre": "Trimestre",
        "motivo": "Motivo", "sugerencias": "Sugerencias", "fecha_seguimiento": "Fecha_Seguimiento",
        "nivel_cumplimiento_resultados": "Nivel_Cumplimiento_Resultados", "observaciones": "Observaciones"},
    5: {"fecha": "Fecha", "evento": "Evento"},
}
FECHA = {3: "fecha", 4: "fecha_elaboracion", 5: "fecha"}


def _cambios(db, numero, id_doc):
    return select(CambioSPA).where(CambioSPA.tipo == f"anexo{numero}", CambioSPA.documento_id == id_doc)


def _datos(row, numero):
    return {k: getattr(row, k) or "" for k in CAMPOS[numero]}


def _validar(numero, campos, anterior=None):
    if set(campos) - CAMPOS[numero].keys() or any(len(v) > 10000 for v in campos.values()):
        raise HTTPException(422, "Campos del anexo inválidos.")
    datos = {**(anterior or {}), **{k: v.strip() for k, v in campos.items()}}
    for campo in ("fecha", "fecha_elaboracion", "fecha_seguimiento"):
        if datos.get(campo):
            try:
                datos[campo] = date.fromisoformat(datos[campo]).isoformat()
            except ValueError as exc:
                raise HTTPException(422, "Usa fechas válidas AAAA-MM-DD.") from exc
    datos[FECHA[numero]] = datos.get(FECHA[numero]) or date.today().isoformat()
    if numero == 3 and not any(datos.get(k) for k in CAMPOS[3] if k.startswith("bap_")):
        raise HTTPException(422, "Describe al menos una barrera.")
    if numero in (4, 5) and not datos.get({4: "sugerencias", 5: "evento"}[numero]):
        raise HTTPException(422, "Registra el contenido del anexo.")
    return datos


def listar(numero, alumno, user):
    modelo = MODELOS[numero]
    with get_session() as db:
        rows = db.scalars(select(modelo).where(modelo.id_alumno == alumno["id"]).order_by(
            getattr(modelo, FECHA[numero]).desc(), modelo.id
        )).all()
        ids = [r.id for r in rows]
        diarios = db.scalars(select(CambioSPA).where(CambioSPA.tipo == f"anexo{numero}",
                    CambioSPA.documento_id.in_(ids)).order_by(CambioSPA.fecha, CambioSPA.id)).all() if ids else []
        primero, ultimo = {}, {}
        for item in diarios:
            primero.setdefault(item.documento_id, item.autor)
            ultimo[item.documento_id] = item.revision
        return [{"id": r.id, "campos": _datos(r, numero), "autor": primero.get(r.id),
                 "revision": ultimo.get(r.id, ""), "editable": user.director or primero.get(r.id) == user.usuario}
                for r in rows]


def guardar(numero, alumno, user, campos, *, id_doc=None, revision=None):
    modelo = MODELOS[numero]
    with get_session() as db:
        if id_doc:
            row = db.scalar(select(modelo).where(modelo.id == id_doc, modelo.id_alumno == alumno["id"]).with_for_update())
            if row is None:
                raise HTTPException(404, "Anexo no disponible.")
            diario = db.scalars(_cambios(db, numero, id_doc).order_by(CambioSPA.fecha, CambioSPA.id)).all()
            if not user.director and (not diario or diario[0].autor != user.usuario):
                raise HTTPException(403, "Solo la persona autora o Dirección puede editar.")
            anterior = _datos(row, numero)
            vigente = diario[-1].revision if diario else ""
            if revision != vigente:
                raise HTTPException(409, "El anexo cambió. Reabre el registro.")
            datos = _validar(numero, campos, anterior)
            if datos == anterior:
                return {"id": id_doc, "revision": vigente}
            filtros = [getattr(modelo, k) == getattr(row, k) for k in CAMPOS[numero]]
            result = db.execute(update(modelo).where(modelo.id == id_doc, *filtros).values(**datos))
            if result.rowcount != 1:
                raise HTTPException(409, "El anexo cambió. Reabre el registro.")
        else:
            vigente = None
            id_doc = uuid.uuid4().hex
            datos = _validar(numero, campos)
            extra = {
                3: {"id_personal": user.id_usuario, "estado": "ACTIVO", "estatus_ia": "PENDIENTE"},
                4: {"docente_especialista": user.nombre, "area": user.area, "estado": "ACTIVA"},
                5: {"nombre_alumno": alumno["nombre_completo"], "especialista": user.nombre,
                    "grado_grupo": f'{alumno["grado"]} {alumno["grupo"]}'.strip(),
                    "id_escuela": alumno["id_escuela"], "escuela": alumno["escuela"], "estado": "ACTIVO"},
            }
            db.add(modelo(id=id_doc, id_alumno=alumno["id"], **datos, **extra[numero]))
        nueva = uuid.uuid4().hex
        _registrar_cambio_spa(db, f"anexo{numero}", id_doc,
                             {"revision": nueva, "alumno": alumno["id"], "campos": datos}, user.usuario, vigente)
        db.commit()
        return {"id": id_doc, "revision": nueva}


def historial(numero, alumno, id_doc):
    with get_session() as db:
        modelo = MODELOS[numero]
        if not db.scalar(select(modelo.id).where(modelo.id == id_doc, modelo.id_alumno == alumno["id"])):
            raise HTTPException(404, "Anexo no disponible.")
    from data.sql_repository import historial_spa_sql
    return historial_spa_sql(f"anexo{numero}", id_doc)


def exportar(numero, alumno, ids=None):
    from documents.anexos import anexo3_pdf, anexo4_pdf, anexo5_pdf

    modelo = MODELOS[numero]
    with get_session() as db:
        query = select(modelo).where(modelo.id_alumno == alumno["id"])
        if ids is not None:
            query = query.where(modelo.id.in_(ids))
        registros = []
        for row in db.scalars(query.order_by(getattr(modelo, FECHA[numero]), modelo.id)):
            datos = {titulo: getattr(row, k) or "" for k, titulo in CAMPOS[numero].items()}
            if numero == 4:
                datos.update(Area=row.area or "", Quien_Brinda_Sugerencias=row.docente_especialista or "")
            if numero == 5:
                datos.update(Especialista=row.especialista or "", Grado_Grupo=row.grado_grupo or "")
            registros.append(datos)
    if not registros:
        raise HTTPException(404, "No hay registros para exportar.")
    perfil = {"Nombre_Completo": alumno["nombre_completo"], "Nombre_Escuela": alumno["escuela"],
              "Grado": alumno["grado"], "Grupo": alumno["grupo"], "CURP": alumno["curp"]}
    return {3: anexo3_pdf, 4: anexo4_pdf, 5: anexo5_pdf}[numero](perfil, pd.DataFrame(registros))

"""Edición y movimientos del padrón con historial en la misma transacción SQL."""

from hashlib import sha256
import json
import os
import re
from typing import Literal
from uuid import uuid4

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func

from data.database import Alumno, Escuela, Usuario, get_session
from data.sql_repository import (
    _registrar_cambio_spa, alumnos_sql, bloquear_padron_sql, historial_spa_sql, save_alumno_sql, update_alumno_sql,
)
from piloto_spa.backend.auth_service import _perfil
from piloto_spa.backend.padron_excel import autorizar, puede_importar
from services.padron_catalogos import CATALOGOS, canonico, fecha_documental
from utils.escolar import grado_canonico, grupo_canonico
from utils.text import normalizar_texto

CAMPOS = {
    "Nombre_Completo": 255, "CURP": 18, "Edad_1_Septiembre": 3, "Sexo": 16,
    "Situacion_Alumno": 64, "Nivel_Educativo": 64, "Grado": 16, "Grupo": 16,
    "Condicion_Discapacidad": 255, "Tipo_Atencion": 64, "Lengua_Indigena_Mayahablante": 32,
    "Afrodescendiente": 32, "Migrante": 32, "Fecha_Nacimiento": 32, "Fecha_Derivacion": 32,
    "Condiciones_Adicionales": 4000,
}
BAJAS = {"BAJA", "INACTIVO", "RETIRADO"}


class EdicionNominal(BaseModel):
    revision: str = Field(pattern=r"^[0-9a-f]{64}$")
    campos: dict[str, str]


class MovimientoNominal(BaseModel):
    revision: str = Field(pattern=r"^[0-9a-f]{64}$")
    accion: Literal["baja", "reactivacion", "traslado"]
    motivo: str = Field(min_length=8, max_length=500)
    escuela: str = Field(default="", max_length=64)
    cuenta_destino: str = Field(default="", max_length=64)
    grado: str = Field(default="", max_length=16)
    grupo: str = Field(default="", max_length=16)


def _ficha(db, alumno_id, user):
    from piloto_spa.backend.alcance_alumno import filtro

    if not db.query(Alumno.id).filter(Alumno.id == alumno_id, filtro(user)).first():
        raise HTTPException(404, "Alumno no disponible.")
    registros = alumnos_sql(alumno_id, sesion=db).to_dict("records")
    if not registros or (not user.director and registros[0]["ID_Escuela"] not in user.escuelas_permitidas):
        raise HTTPException(404, "Alumno no disponible.")
    return registros[0]


def _revision(ficha, alumno):
    marca = alumno.actualizado_en.isoformat() if alumno.actualizado_en else ""
    return sha256(json.dumps([ficha, marca], sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def consultar(alumno_id, user):
    autorizar(user)
    with get_session() as db:
        ficha = _ficha(db, alumno_id, user)
        return {"revision": _revision(ficha, db.get(Alumno, alumno_id)), "campos": {k: ficha[k] for k in CAMPOS},
                "estatus": ficha["Estatus"], "escuela": ficha["ID_Escuela"],
                "catalogos": {k: CATALOGOS[k] for k in CAMPOS if k in CATALOGOS}}


def historial(alumno_id, user):
    consultar(alumno_id, user)
    return historial_spa_sql("padron_nominal", alumno_id)


def destinos(alumno_id, user):
    autorizar(user)
    with get_session() as db:
        ficha = _ficha(db, alumno_id, user)
        apoyos = [_perfil(cuenta) for cuenta in db.query(Usuario) if cuenta.usuario]
        return [
            {"id": escuela.id, "nombre": escuela.nombre_escuela,
             "responsables": [{"id": perfil.id_usuario, "nombre": perfil.nombre or perfil.usuario}
                              for perfil in apoyos if not perfil.director and puede_importar(perfil)
                              and escuela.id in perfil.escuelas_permitidas]}
            for escuela in db.query(Escuela).filter(Escuela.id != ficha["ID_Escuela"])
            .order_by(Escuela.nombre_escuela)
        ]


def _validar(campos):
    cambios = {}
    for campo, valor in campos.items():
        valor = valor.strip()
        if campo not in CAMPOS or len(valor) > CAMPOS[campo]:
            raise HTTPException(422, f"Campo nominal inválido: {campo}.")
        if campo == "Nombre_Completo" and not valor:
            raise HTTPException(422, "Indica el nombre del alumno.")
        if campo == "CURP":
            valor = valor.upper()
            if not re.fullmatch(r"[A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]\d", valor):
                raise HTTPException(422, "Indica una CURP válida.")
        elif campo in CATALOGOS and valor:
            valor = canonico(campo, valor)
            if valor not in CATALOGOS[campo]:
                raise HTTPException(422, f"El valor de {campo} no está en el catálogo.")
        elif campo.startswith("Fecha_") and valor:
            try:
                valor = fecha_documental(valor).isoformat()
            except ValueError:
                raise HTTPException(422, "Indica una fecha válida.") from None
        elif campo == "Edad_1_Septiembre" and valor and (not valor.isascii() or not valor.isdecimal() or int(valor) > 100):
            raise HTTPException(422, "Indica una edad válida.")
        cambios[campo] = valor
    return cambios


def editar(alumno_id, payload, user):
    return _guardar(alumno_id, user, payload.revision, campos=payload.campos)


def mover(alumno_id, payload, user):
    if os.getenv("USAER_SPA_MODE") == "usaer-private-local" and not user.director:
        raise HTTPException(403, "Los movimientos consolidados corresponden a Dirección.")
    return _guardar(alumno_id, user, payload.revision, movimiento=payload)


def _cambios_movimiento(db, actual, payload):
    estado = normalizar_texto(actual["Estatus"])
    if payload.accion == "reactivacion" and estado in BAJAS:
        return {"Estatus": "Activo"}
    if payload.accion == "baja" and estado == "ACTIVO":
        return {"Estatus": "Baja"}
    if payload.accion != "traslado" or estado != "ACTIVO":
        raise HTTPException(409, "El estado actual del alumno no permite ese movimiento.")
    escuela = db.get(Escuela, payload.escuela)
    cuenta = db.get(Usuario, payload.cuenta_destino)
    grado, grupo = grado_canonico(payload.grado), grupo_canonico(payload.grupo)
    if not escuela or escuela.id == actual["ID_Escuela"] or not cuenta or not cuenta.usuario:
        raise HTTPException(422, "Selecciona otra escuela y una cuenta de apoyo de destino.")
    perfil = _perfil(cuenta)
    if perfil.director or not puede_importar(perfil) or escuela.id not in perfil.escuelas_permitidas:
        raise HTTPException(422, "La cuenta elegida no es personal de apoyo del destino.")
    if grado not in CATALOGOS["Grado"] or grupo not in CATALOGOS["Grupo"]:
        raise HTTPException(422, "Confirma el grado y grupo de destino.")
    return {
        "ID_Escuela": escuela.id, "Nombre_Escuela": escuela.nombre_escuela,
        "CCT_Escuela": escuela.cct or "", "Turno_Escuela": escuela.turno or "",
        "Direccion_Escuela": "", "Localidad_Escuela": "", "Municipio_Escuela": "",
        "Maestra de Apoyo": perfil.nombre or perfil.usuario, "ID_Maestro_Regular": "",
        "Grado": grado, "Grupo": grupo, "Nivel_Educativo": escuela.nivel or actual["Nivel_Educativo"],
    }


def _guardar(alumno_id, user, revision, *, campos=None, movimiento=None):
    autorizar(user)
    with get_session() as db:
        bloquear_padron_sql(db)
        actual = _ficha(db, alumno_id, user)
        alumno = db.get(Alumno, alumno_id)
        anterior = _revision(actual, alumno)
        if revision is not None and revision != anterior:
            raise HTTPException(409, "La ficha cambió. Vuelve a abrirla antes de guardar.")
        cambios = _validar(campos) if movimiento is None else _cambios_movimiento(db, actual, movimiento)
        cambios = {k: v for k, v in cambios.items() if actual.get(k) != v}
        if not cambios:
            return {"id": alumno_id, "revision": anterior}
        curp = cambios.get("CURP", actual["CURP"]).strip().upper()
        if curp and db.query(Alumno.id).filter(
            func.upper(func.trim(Alumno.curp)) == curp, Alumno.id != alumno_id,
        ).first():
            raise HTTPException(409, "La CURP requiere conciliación antes de guardar.")
        motivo = movimiento.motivo.strip() if movimiento else ""
        if movimiento and len(motivo) < 8:
            raise HTTPException(422, "Indica el motivo del movimiento.")
        update_alumno_sql(alumno_id, cambios, [alumno_id], sesion=db)
        db.refresh(alumno)
        nueva = _revision({**actual, **cambios}, alumno)
        _registrar_cambio_spa(db, "padron_nominal", alumno_id, {
            "revision": uuid4().hex, "accion": movimiento.accion if movimiento else "edicion",
            "motivo": motivo, "antes": {k: actual.get(k, "") for k in cambios}, "despues": cambios,
        }, user.usuario, anterior)
        db.commit()
        return {"id": alumno_id, "revision": nueva}


def editar_compatible(alumno_id, campos, user):
    # El PUT histórico tampoco puede eludir el flujo de traslado o baja.
    return _guardar(alumno_id, user, None, campos=campos)


def alta(registro, user):
    if os.getenv("USAER_SPA_MODE") == "usaer-private-local" and not user.director:
        raise HTTPException(403, "Las altas consolidadas corresponden a Dirección.")
    from piloto_spa.backend.alcance_alumno import ICHC

    autorizar(user)
    escuela_id = registro["ID_Escuela"]
    if not user.director and (escuela_id == ICHC or escuela_id not in user.escuelas_permitidas):
        raise HTTPException(403, "Escuela no autorizada para el alta.")
    identidad = _validar({k: registro[k] for k in ("Nombre_Completo", "CURP") if registro[k] or k != "CURP"})
    with get_session() as db:
        bloquear_padron_sql(db)
        escuela = db.get(Escuela, escuela_id)
        if not escuela:
            raise HTTPException(422, "Selecciona una escuela registrada en el catálogo local.")
        registro = {**registro, **identidad, "Nombre_Escuela": escuela.nombre_escuela,
                    "CCT_Escuela": escuela.cct or "", "Turno_Escuela": escuela.turno or ""}
        try:
            alumno_id = save_alumno_sql(registro, sesion=db)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from None
        _registrar_cambio_spa(db, "padron_nominal", alumno_id, {
            "revision": uuid4().hex, "accion": "alta", "motivo": "",
            "antes": {}, "despues": registro,
        }, user.usuario, None)
        db.commit()
        return alumno_id

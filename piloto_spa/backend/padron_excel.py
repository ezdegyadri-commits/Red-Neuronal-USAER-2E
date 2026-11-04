"""Vista previa y conciliación transaccional del padrón de la SPA."""

from hashlib import sha256
import json
from uuid import uuid4
from xml.etree.ElementTree import ParseError
from zipfile import BadZipFile

from fastapi import HTTPException
from openpyxl.utils.exceptions import InvalidFileException
from sqlalchemy import String

from data.database import Alumno, get_session
from data.sql_repository import (
    _registrar_cambio_spa, alumnos_sql, bloquear_padron_sql, save_alumno_sql, update_alumno_sql,
)
from piloto_spa.backend.domain_services import obtener_catalogo_escuelas
from services.padron_importacion import comparar, leer
from utils.text import normalizar_texto

LIMITE = 16 * 1024 * 1024


def puede_importar(user):
    rol = normalizar_texto(user.rol)
    return user.director or (bool(user.escuelas_permitidas) and rol in {
        "MAESTRA DE APOYO", "MAESTRO DE APOYO", "DOCENTE DE APOYO",
    })


def autorizar(user):
    if not puede_importar(user):
        raise HTTPException(403, "Esta cuenta no puede importar el padrón.")


def procesar(data, user, revision=None):
    from piloto_spa.backend.alcance_alumno import ICHC

    if not user.director and (ICHC in user.escuelas_permitidas or "TODAS" in user.escuelas_permitidas):
        raise HTTPException(403, "La importación del padrón compartido corresponde a Dirección.")
    escuelas = [
        {"ID_Escuela": e["id"], "Nombre_Escuela": e["nombre"], "CCT_Escuela": e["cct"]}
        for e in obtener_catalogo_escuelas() if user.director or e["id"] in user.escuelas_permitidas
    ]
    try:
        lectura = leer(data, escuelas)
    except (BadZipFile, InvalidFileException, ParseError, KeyError, TypeError, OSError):
        raise HTTPException(422, "El archivo no es un Excel .xlsx legible.") from None
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None

    with get_session() as db:
        if revision is not None:
            bloquear_padron_sql(db)
        actuales = alumnos_sql(sesion=db).to_dict("records")
        plan = comparar(lectura["registros"], actuales, escuelas)
        errores = [*lectura["errores"], *plan["conflictos"]]
        for numero, fila in enumerate(plan["filas"], 1):
            if fila["tipo"] == "Actualizar" and "Estatus" in fila["cambios"]:
                if normalizar_texto(fila["cambios"]["Estatus"]) == normalizar_texto(fila["anterior"]["Estatus"]):
                    fila["cambios"].pop("Estatus")
                    if not fila["cambios"]:
                        fila["tipo"] = "Sin cambios"
                else:
                    errores.append(f"Registro {numero}: usa Movimientos del padrón para cambiar el estatus.")
            for campo, valor in fila["cambios"].items():
                columna = Alumno.__table__.columns.get(campo.lower())
                if columna is not None and isinstance(columna.type, String):
                    limite = columna.type.length
                    if limite and len(valor) > limite:
                        errores.append(f"Registro {numero}: {campo} excede {limite} caracteres.")
        huella = sha256(json.dumps(
            [user.id_usuario, lectura["sha256"], plan], sort_keys=True, ensure_ascii=False,
        ).encode()).hexdigest()
        if revision is None:
            return {
                "revision": huella, "errores": errores, "hoja": lectura["hoja"],
                "columnas_reconocidas": lectura["columnas_reconocidas"],
                "encabezados_no_reconocidos": lectura["encabezados_no_reconocidos"],
                "filas": [
                    {"accion": f["tipo"], "alumno": f["registro"].get("Nombre_Completo")
                     or f["anterior"].get("Nombre_Completo"),
                     "cambios": {k: {"anterior": f["anterior"].get(k, ""), "nuevo": v}
                                 for k, v in f["cambios"].items()}}
                    for f in plan["filas"]
                ],
            }
        if errores or not plan["filas"]:
            raise HTTPException(422, "Corrige las observaciones antes de confirmar la importación.")
        if revision != huella and any(f["tipo"] != "Sin cambios" for f in plan["filas"]):
            raise HTTPException(409, "El padrón cambió. Revisa de nuevo el archivo antes de confirmar.")
        resultado = {"altas": 0, "actualizados": 0}
        for fila in plan["filas"]:
            if fila["tipo"] == "Sin cambios":
                continue
            previo = fila["anterior"]
            if fila["tipo"] == "Alta":
                alumno_id = save_alumno_sql({
                    **fila["registro"], "Estatus": "Activo", "Maestra de Apoyo": user.nombre,
                }, sesion=db)
                resultado["altas"] += 1
            else:
                alumno_id = previo["ID_Alumno"]
                update_alumno_sql(alumno_id, fila["cambios"], [alumno_id], sesion=db)
                resultado["actualizados"] += 1
            _registrar_cambio_spa(db, "padron_excel", alumno_id, {
                "revision": uuid4().hex, "antes": previo, "cambios": fila["cambios"],
            }, user.usuario, None)
        db.commit()
        return resultado

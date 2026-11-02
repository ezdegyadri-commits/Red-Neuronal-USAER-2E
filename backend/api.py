"""FastAPI backend de USAER 2E (Fase 12).

Servicios de API REST con SQLAlchemy, PostgreSQL y control de bloqueos de concurrencia.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from data.database import (
    Alumno,
    BloqueoConcurrencia,
    Escuela,
    Personal,
    PlaneacionDoc,
    adquirir_bloqueo,
    get_session,
    liberar_bloqueo,
)
from data.sql_repository import (
    alumnos_sql,
    anexo3_sql,
    anexo4_sql,
    anexo5_sql,
    anexo7_sql,
    escuelas_sql,
    personal_sql,
    save_alumno_sql,
    save_anexo3_sql,
    save_anexo4_sql,
    save_anexo5_sql,
    save_anexo7_sql,
    update_alumno_sql,
    visitas_sql,
)

router = APIRouter(prefix="/api/v1", tags=["Fase 12 Core"])


class AlumnoIn(BaseModel):
    ID_Alumno: Optional[str] = None
    Nombre_Completo: str
    CURP: str
    Grado: Optional[str] = ""
    Grupo: Optional[str] = ""
    ID_Escuela: Optional[str] = ""
    Nombre_Escuela: Optional[str] = ""
    Condicion_Discapacidad: Optional[str] = ""
    Estatus: Optional[str] = "ACTIVO"


class BloqueoReq(BaseModel):
    clave: str
    token: str
    segundos: Optional[int] = 30
    namespace: Optional[str] = "usaer2e"


@router.get("/health")
def health_check():
    return {"status": "ok", "backend": "FastAPI + SQLAlchemy + PostgreSQL (Neon)", "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/alumnos")
def listar_alumnos(escuela: Optional[str] = None):
    df = alumnos_sql()
    if escuela and "ID_Escuela" in df.columns:
        df = df[df["ID_Escuela"] == escuela]
    return df.to_dict("records")


@router.post("/alumnos")
def crear_alumno(alumno: AlumnoIn):
    try:
        aid = save_alumno_sql(alumno.model_dump())
        return {"id": aid, "status": "creado"}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/escuelas")
def listar_escuelas():
    return escuelas_sql().to_dict("records")


@router.get("/personal")
def listar_personal():
    return personal_sql().to_dict("records")


# Bloqueos de concurrencia (Fase 12)
@router.post("/concurrencia/adquirir")
def adquirir_bloqueo_endpoint(req: BloqueoReq):
    ok = adquirir_bloqueo(req.clave, req.token, req.segundos, req.namespace)
    if not ok:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Bloqueo no disponible por concurrencia activa.")
    return {"ok": True, "clave": req.clave, "token": req.token}


@router.post("/concurrencia/liberar")
def liberar_bloqueo_endpoint(req: BloqueoReq):
    ok = liberar_bloqueo(req.clave, req.token)
    return {"ok": ok}

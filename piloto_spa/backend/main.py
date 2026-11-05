"""FastAPI Backend Integral para USAER 2E 2.0.

Capa de servicios RESTful de alta velocidad para la versión SPA desacoplada de Streamlit.
Implementa autenticación con tokens seguros, control de acceso basado en roles (RBAC),
persistencia relacional, EPP, expedientes, planeaciones (Formatos XXIII, XXV, XIX, XX),
asistente pedagógico conversacional, anexos oficiales, visitas, oficios e indicadores de la Zona 001.
"""
from __future__ import annotations

import os
import logging
from datetime import date
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
import time
from contextlib import asynccontextmanager
from sqlalchemy import text
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy.engine import make_url

from data.database import get_engine
from data.sql_repository import (
    alumnos_sql, candidatos_grupo_spa_sql, epp_listar_sql, grupo_spa_sql,
    historial_spa_sql, planeacion_por_id_sql, planes_previos_spa_sql,
)
from piloto_spa.backend.grupal import (
    actualizar_guia, alcance_grupo, area_compartida, columnas_editables, editar_grupo, puede_coordinar, sincronizar_matricula,
)
from utils.escolar import grado_canonico, grupo_canonico
from piloto_spa.backend import adjuntos, anexos_expediente, padron_excel, padron_nominal, contextos_epp, tramites_spa
from piloto_spa.backend.evaluacion import anexo_epp, editar_anexo, nee_vigentes
from services.planeacion_modelo import crear_plantilla
from typing import Literal
import uuid

from fastapi import FastAPI, HTTPException, Depends, status, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import pandas as pd

from piloto_spa.backend.auth_service import (
    COOKIE_SESION, TOKEN_TTL_SECONDS, SessionUser, token_solicitud,
    autenticar_usuario, registrar_intento, restablecer_password,
    emitir_token_sesion,
    validar_token_sesion,
    cerrar_sesion,
)
from piloto_spa.backend.domain_services import (
    adaptar_planeacion_para_pdf,
    obtener_catalogo_escuelas,
    obtener_alumnos_autorizados,
    obtener_expediente_completo,
    obtener_epp_documento,
    guardar_epp_documento,
    obtener_planeacion_con_firmas,
    guardar_planeacion_transaccional,
    eliminar_planeacion_documento,
    guardar_anexo7_documento,
    obtener_visitas_documentos,
    obtener_oficios_documentos,
    chat_asistente_pedagogico,
    obtener_estadisticas_zona,
)
from documents.planeacion import generar_pdf as generar_pdf_planeacion

def verificar_base_piloto():
    url = make_url(os.environ.get("DATABASE_URL", "sqlite://"))
    modo = os.environ.get("USAER_SPA_MODE")
    if modo in {"b01-private-local", "b02-private-local", "usaer-private-local"}:
        from piloto_spa.backend.b01_privado import verificar_conexion, verificar_url

        verificar_url(url)
        if os.getenv("USAER_SPA_ROLE") != "runtime":
            raise RuntimeError("La SPA privada requiere el rol operativo.")
        with get_engine(initialize_schema=False).connect() as connection:
            verificar_conexion(connection)
        return
    if modo == "uppcoder":
        from deploy.uppcoder import verificar_instalacion, verificar_url

        verificar_url()
        with get_engine(initialize_schema=False).connect() as connection:
            verificar_instalacion(connection)
        return
    if modo == "local-synthetic" and url.drivername == "sqlite" and url.database not in (None, "", ":memory:"):
        return
    perfil = os.environ.get("USAER_SPA_ROLE", "owner")
    prefijo = "spa_runtime_" if perfil == "runtime" else "spa_fixture_"
    contenedor = modo == "postgres-container-synthetic"
    host_valido = (url.host == "db" and url.port == 5432 and url.database == "usaer_spa_test_oracle"
                   if contenedor else url.host == "127.0.0.1" and url.port and url.port != 5432)
    if (
        modo not in {"postgres-synthetic", "postgres-container-synthetic"}
        or url.drivername not in {"postgresql", "postgresql+psycopg2"}
        or not host_valido
        or not re.fullmatch(r"usaer_spa_test_[a-z0-9_]+", url.database or "")
        or perfil not in {"owner", "runtime"}
        or url.username != (url.database or "").replace("usaer_spa_test_", prefijo, 1)
        or not url.password or url.query
    ):
        raise RuntimeError("El piloto requiere una base sintética SQLite o PostgreSQL local identificada.")
    engine = get_engine(initialize_schema=False)
    with engine.connect() as connection:
        marca = connection.execute(text("""
            SELECT shobj_description(oid, 'pg_database') FROM pg_database
            WHERE datname = current_database()
        """)).scalar_one()
        privilegiado = connection.execute(text("""
            SELECT rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls
            FROM pg_roles WHERE rolname = current_user
        """)).scalar_one()
        if marca != "USAER SPA synthetic only" or privilegiado:
            raise RuntimeError("PostgreSQL no está marcado para pruebas o la cuenta tiene privilegios elevados.")
        if perfil == "runtime":
            puede_ddl = connection.execute(text("""
                SELECT has_schema_privilege(current_user, 'public', 'CREATE')
                    OR has_database_privilege(current_user, current_database(), 'CREATE')
                    OR pg_has_role(current_user, datdba, 'MEMBER')
                FROM pg_database WHERE datname = current_database()
            """)).scalar_one()
            if puede_ddl:
                raise RuntimeError("La cuenta operativa debe estar separada del rol de migración.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    verificar_base_piloto()
    if not all((SPA_STATIC_DIR / nombre).is_file() for nombre in ("index.html", "app.js", "app.css")):
        raise RuntimeError("Compila el frontend con npm ci y npm run build en piloto_spa/frontend.")
    with get_engine().connect() as connection:
        connection.execute(text("SELECT 1"))
    yield


app = FastAPI(
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    title="USAER 2E 2.0 — API de Servicios Pedagógicos",
    version="2.0.0",
    description="Backend desacoplado de alto rendimiento para el sistema educativo USAER 02-E",
)

hosts_piloto = ["localhost", "127.0.0.1", "testserver"]
if os.environ.get("USAER_SPA_LAN_IP"):
    hosts_piloto.append(os.environ["USAER_SPA_LAN_IP"])
if os.environ.get("USAER_SPA_TLS_HOST") and os.environ.get("USAER_SPA_TLS_CERT"):
    hosts_piloto.append(os.environ["USAER_SPA_TLS_HOST"])
if os.environ.get("USAER_SPA_MODE") == "postgres-container-synthetic":
    hosts_piloto = [os.environ.get("USAER_PUBLIC_HOST", ""), "localhost"]
es_uppcoder = os.environ.get("USAER_SPA_MODE") == "uppcoder"
if es_uppcoder:
    from deploy.uppcoder import host_publico

    hosts_piloto = [host_publico(), "localhost", "127.0.0.1"]
app.add_middleware(TrustedHostMiddleware, allowed_hosts=hosts_piloto)
accesos_piloto = logging.getLogger("uvicorn.error")

@app.middleware("http")
async def cabeceras_piloto(request: Request, call_next):
    if os.environ.get("USAER_SPA_MODE") in {"b01-private-local", "b02-private-local", "usaer-private-local"}:
        if not request.client or request.client.host not in {"127.0.0.1", "::1"}:
            return Response(status_code=403)
        if request.url.path.startswith("/api/ai/") or request.url.path.endswith("/actividad-curricular-externa"):
            return Response(status_code=403)
    response = await call_next(request)
    ruta = getattr(request.scope.get("route"), "path", None)
    accesos_piloto.info("acceso origen=%s metodo=%s ruta=%s estado=%d",
                        request.client.host if request.client else "desconocido",
                        request.method, ruta or ("estatico" if request.url.path.startswith("/assets/") else "sin_ruta"),
                        response.status_code)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    if request.url.scheme == "https" or es_uppcoder:
        response.headers["Strict-Transport-Security"] = "max-age=86400"
    if request.url.path == "/":
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        )
    return response


# -------------------------------------------------------------
# MODELOS PYDANTIC PARA CONTRATOS DE ENTRADA Y SALIDA
# -------------------------------------------------------------

class LoginPayload(BaseModel):
    usuario: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=255)

class LoginResponse(BaseModel):
    token: Optional[str] = None
    user: SessionUser

class AlumnoPayload(BaseModel):
    id: Optional[str] = None
    nombre_completo: str
    curp: str = ""
    edad_1_septiembre: str = ""
    sexo: str = "Hombre"
    situacion_alumno: str = "INSCRITO"
    nivel_educativo: str = "Primaria"
    grado: str = "1"
    grupo: str = "A"
    id_escuela: str = "ESC-001"
    nombre_escuela: str = "Damián Carmona"
    maestra_apoyo: str = ""
    condicion_discapacidad: str = "TDAH"
    estatus: str = "ACTIVO"
    tipo_atencion: str = "Atención Focalizada"

class PlaneacionPayload(BaseModel):
    id: Optional[str] = None
    formato: str = "XXIII"
    estado: str = "BORRADOR"
    revision: Optional[str] = None
    datos: Dict[str, Any] = Field(default_factory=dict)
    metadatos: Dict[str, Any] = Field(default_factory=dict)
    tablas: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)
    textos: Dict[str, str] = Field(default_factory=dict)
    observaciones_director: str = ""

class NuevaPlaneacion(BaseModel):
    modalidad: Literal["individual", "grupal"]
    formato: Literal["XXI", "XXIII", "XXV"] = "XXIII"
    alumnos: list[str] = Field(min_length=1, max_length=100)
    ciclo_inicio: int = Field(default=2026, ge=2000, le=2100)
    trimestre: int = Field(default=1, ge=1, le=3)


class PropuestaPlaneacion(BaseModel):
    nee_id: str = Field(default="", max_length=64)
    enfoque: str = Field(default="", max_length=1500)
    pda_id: str = Field(default="", max_length=100)
    campo: str = Field(default="Lenguajes", max_length=80)
    alumno_id: str = Field(default="", max_length=64)
    variante: int = Field(default=0, ge=0, le=2)
    metodo: str = Field(default="", max_length=500)
    materiales: str = Field(default="", max_length=500)


class ActividadCurricularExterna(BaseModel):
    pda_id: str = Field(min_length=1, max_length=100)
    campo: str = Field(default="Lenguajes", max_length=80)
    autorizo: bool = Field(default=False, strict=True)


class FundamentoNEE(BaseModel):
    texto: str = Field(min_length=1, max_length=1200)
    fundamento: str = Field(min_length=1, max_length=2500)
    desde: date
    hasta: date


class SeccionEPP(BaseModel):
    revision: str
    valor: dict
    nee: list[FundamentoNEE] = Field(default_factory=list, max_length=20)


class EPPPayload(BaseModel):
    id: str
    alumno: str
    revision: Optional[str] = None
    ciclo: str = "2026-2027"
    partes: Dict[str, Any] = Field(default_factory=dict)

class AIChatPayload(BaseModel):
    mensaje: str
    alumno_id: Optional[str] = None
    planeacion_id: Optional[str] = None

class AISugerenciaPayload(BaseModel):
    area: str = "Aprendizaje"
    necesidad_o_barrera: str
    grado: str = "2"
    condicion: str = "General"

class Anexo3Payload(BaseModel):
    id: Optional[str] = None
    id_alumno: str
    fecha: str = ""
    bap_fisicas: str = ""
    bap_actitudinales: str = ""
    bap_pedagogicas: str = ""
    bap_organizativas: str = ""

class Anexo4Payload(BaseModel):
    id: Optional[str] = None
    id_alumno: str
    fecha_elaboracion: str = ""
    ciclo_escolar: str = "2026-2027"
    trimestre: str = "1"
    docente_especialista: str = ""
    area: str = "Aprendizaje"
    sugerencias: str = ""
    motivo: str = ""
    fecha_seguimiento: str = ""
    nivel_cumplimiento_resultados: str = ""

class Anexo5Payload(BaseModel):
    id: Optional[str] = None
    id_alumno: str
    fecha: str = ""
    nombre_alumno: str = ""
    grado_grupo: str = ""
    especialista: str = ""
    evento: str = ""
    id_escuela: str = ""
    escuela: str = ""

class VisitaPayload(BaseModel):
    id: Optional[str] = None
    fecha: str = ""
    escuela: str = ""
    personal: str = ""
    motivo: str = ""
    observaciones: str = ""
    tipo_acta: str = "Acompañamiento"
    lugar: str = "Mérida, Yucatán"

    acuerdos: str = Field(default="", max_length=12000)
    seguimiento: str = Field(default="", max_length=12000)
    responsable: str = Field(default="", max_length=255)
    alumno_id: str | None = Field(default=None, max_length=64)


class EdicionActa(VisitaPayload):
    revision: str = Field(max_length=64)


class OficioPayload(BaseModel):
    id: Optional[str] = None
    folio: str = ""
    clave_operacion: str = ""
    fecha_emision: str = ""
    fecha_comision: str = ""
    escuela: str = ""
    id_escuela: str = ""
    maestra_apoyo: str = ""
    director_escuela: str = ""
    asunto: str = ""
    destino: str = ""
    horario: str = ""


class EdicionOficio(OficioPayload):
    revision: str = Field(max_length=64)

# -------------------------------------------------------------
# 1. AUTENTICACIÓN Y SESIÓN (SEGURA Y CON TOKENS)
# -------------------------------------------------------------

@app.get("/api/health")
def healthcheck():
    """Monitoreo de estado y keep-alive de disponibilidad."""
    with get_engine().connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok", "version": "2.0.0", "release": "usaer-docente-spark-20261105", "timestamp": time.time()}


@app.post("/api/auth/login", response_model=LoginResponse, response_model_exclude_none=True)
def login_endpoint(payload: LoginPayload, request: Request, response: Response):
    """Autentica credenciales y emite un token de sesión criptográfico."""
    inicio = time.perf_counter()
    registrar_intento(request, payload.usuario)
    limite = time.perf_counter()
    credenciales = autenticar_usuario(payload.usuario, payload.password)
    verificado = time.perf_counter()
    if not credenciales:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos."
        )
    user, version = credenciales
    token = emitir_token_sesion(user, version)
    emitido = time.perf_counter()
    response.headers["Server-Timing"] = (
        f"limite;dur={(limite - inicio) * 1000:.1f}, "
        f"credencial;dur={(verificado - limite) * 1000:.1f}, "
        f"sesion;dur={(emitido - verificado) * 1000:.1f}"
    )
    response.headers["Cache-Control"] = "no-store"
    if request.headers.get("X-USAER-Client") == "browser":
        cerrar_sesion(token_solicitud(request))
        response.set_cookie(COOKIE_SESION, token, max_age=TOKEN_TTL_SECONDS, httponly=True,
                            samesite="strict", secure=es_uppcoder or request.url.scheme == "https")
        return LoginResponse(user=user)
    return LoginResponse(token=token, user=user)


@app.get("/api/me", response_model=SessionUser)
def obtener_perfil_actual(user: SessionUser = Depends(validar_token_sesion)):
    """Retorna los datos y alcance de autorización del usuario autenticado."""
    return user


class CambioPassword(BaseModel):
    actual: str = Field(min_length=1, max_length=255)
    nueva: str = Field(min_length=16, max_length=255)


@app.put("/api/auth/cuentas/{usuario_id}/password")
def cambiar_password(usuario_id: str, payload: CambioPassword, request: Request, response: Response,
                     user: SessionUser = Depends(validar_token_sesion)):
    registrar_intento(request, user.usuario)
    restablecer_password(user, usuario_id, payload.actual, payload.nueva)
    if user.id_usuario == usuario_id:
        response.delete_cookie(COOKIE_SESION)
    return {"revocado": True}


class AltaCuenta(BaseModel):
    usuario: str = Field(pattern=r"^[a-z0-9][a-z0-9_.-]{2,63}$")
    nombre: str = Field(min_length=1, max_length=120)
    rol: Literal["MAESTRA DE APOYO", "MAESTRO DE APOYO", "PSICOLOGIA", "COMUNICACION", "TRABAJO SOCIAL"]
    escuelas: list[str] = Field(min_length=1, max_length=30)
    password: str = Field(max_length=255)
    actual: str = Field(max_length=255)


class BajaCuenta(BaseModel):
    actual: str = Field(max_length=255)


def comprobar_direccion_para_cuentas(request, user, password):
    exigir_direccion(user)
    registrar_intento(request, user.usuario)
    credencial = autenticar_usuario(user.usuario, password)
    if not credencial:
        raise HTTPException(401, "La contraseña actual no coincide.")
    return credencial[1]


@app.get("/api/auth/cuentas")
def listar_cuentas(user: SessionUser = Depends(validar_token_sesion)):
    from data.database import Usuario, get_session
    exigir_direccion(user)
    with get_session() as db:
        return [{"id": row.id, "usuario": row.usuario, "nombre": row.nombre,
                 "rol": row.rol, "escuelas": row.escuelas_permitidas, "habilitada": bool(row.password)}
                for row in db.query(Usuario).order_by(Usuario.usuario)]


@app.post("/api/auth/cuentas", status_code=201)
def alta_cuenta(payload: AltaCuenta, request: Request, user: SessionUser = Depends(validar_token_sesion)):
    from data.database import Escuela, Usuario, get_session
    from data.sql_repository import _registrar_cambio_spa
    from piloto_spa.backend.auth_service import _huella, _perfil, hash_password, password_admisible
    from sqlalchemy import func, select
    from sqlalchemy.exc import IntegrityError

    credencial = comprobar_direccion_para_cuentas(request, user, payload.actual)
    if not password_admisible(payload.password) or not payload.nombre.strip():
        raise HTTPException(422, "Indica el nombre y una contraseña robusta.")
    with get_session() as db:
        actor = db.scalar(select(Usuario).where(Usuario.id == user.id_usuario).with_for_update())
        if not actor or not _perfil(actor).director or _huella(actor.password or "") != credencial:
            raise HTTPException(403, "La autorización de Dirección cambió.")
        escuelas = set(db.scalars(select(Escuela.id).where(Escuela.id.in_(payload.escuelas))))
        if escuelas != set(payload.escuelas):
            raise HTTPException(422, "Selecciona escuelas del servicio actual.")
        if db.scalar(select(Usuario.id).where(func.lower(func.trim(Usuario.usuario)) == payload.usuario)):
            raise HTTPException(409, "Ese usuario ya está registrado.")
        id_cuenta = uuid.uuid4().hex
        db.add(Usuario(id=id_cuenta, usuario=payload.usuario, nombre=payload.nombre.strip(),
                       rol=payload.rol, escuelas_permitidas=",".join(sorted(escuelas)),
                       password=hash_password(payload.password)))
        _registrar_cambio_spa(db, "cuenta", id_cuenta,
                             {"revision": uuid.uuid4().hex, "accion": "alta"}, user.usuario, None)
        try:
            db.commit()
        except IntegrityError as exc:
            raise HTTPException(409, "Ese usuario ya está registrado.") from exc
        return {"id": id_cuenta}


@app.post("/api/auth/cuentas/{id_cuenta}/baja")
def baja_cuenta(id_cuenta: str, payload: BajaCuenta, request: Request,
                user: SessionUser = Depends(validar_token_sesion)):
    from data.database import SesionSPA, Usuario, get_session
    from data.sql_repository import _registrar_cambio_spa
    from piloto_spa.backend.auth_service import _huella, _perfil
    from sqlalchemy import delete, select

    credencial = comprobar_direccion_para_cuentas(request, user, payload.actual)
    with get_session() as db:
        actor = db.scalar(select(Usuario).where(Usuario.id == user.id_usuario).with_for_update())
        if not actor or not _perfil(actor).director or _huella(actor.password or "") != credencial:
            raise HTTPException(403, "La autorización de Dirección cambió.")
        cuenta = db.scalar(select(Usuario).where(Usuario.id == id_cuenta).with_for_update())
        if not cuenta:
            raise HTTPException(404, "Cuenta no disponible.")
        if _perfil(cuenta).director:
            raise HTTPException(403, "La baja de Dirección corresponde al operador del servicio.")
        if cuenta.password:
            cuenta.password = ""
            db.execute(delete(SesionSPA).where(SesionSPA.usuario_id == id_cuenta))
            _registrar_cambio_spa(db, "cuenta", id_cuenta,
                                 {"revision": uuid.uuid4().hex, "accion": "baja"}, user.usuario, None)
            db.commit()
        return {"habilitada": False}


@app.post("/api/auth/logout")
def logout_endpoint(request: Request, response: Response):
    """Invalida la sesión actual de forma inmediata en el servidor."""
    cerrar_sesion(token_solicitud(request))
    response.delete_cookie(COOKIE_SESION)
    return {"status": "success", "mensaje": "Sesión cerrada correctamente."}

# -------------------------------------------------------------
# 2. ESCUELAS Y PADRÓN DE ALUMNOS (RBAC)
# -------------------------------------------------------------

def exigir_alumno(alumno_id: str, user: SessionUser):
    if not user.director and not _alumnos_en_alcance(user, alumno_id=alumno_id):
        raise HTTPException(status_code=404, detail="Alumno no disponible.")
    alumnos = obtener_alumnos_autorizados(user.rol, user.escuelas_permitidas, alumno_id=alumno_id)
    for alumno in alumnos:
        if alumno["id"] == alumno_id:
            return alumno
    raise HTTPException(status_code=404, detail="Alumno no disponible.")


def exigir_direccion(user: SessionUser):
    if not user.director:
        raise HTTPException(status_code=403, detail="Operación reservada a Dirección.")


def _alumnos_en_planeacion(doc):
    datos = doc.get("datos") or {}
    meta = doc.get("metadatos") or {}
    guia = meta.get("guia_grupal_manual") or {}
    ids = {a.get("ID_Alumno") for a in datos.get("Alumnos", []) if isinstance(a, dict)}
    for tabla in ("filas", "as"):
        ids.update(a.get("ID_Alumno") for a in guia.get(tabla, []) if isinstance(a, dict))
    ids.update(a.get("alumno") for a in meta.get("vinculos_documentales", []) if isinstance(a, dict))
    ids.update(meta.get("alumnos_retirados_del_grupo") or {})
    return {aid for aid in ids if isinstance(aid, str) and aid}


def _alumnos_en_alcance(user, *, sesion=None, alumno_id=None):
    from data.database import Alumno, get_session
    from contextlib import nullcontext
    from piloto_spa.backend.alcance_alumno import filtro

    with (nullcontext(sesion) if sesion is not None else get_session()) as db:
        consulta = db.query(Alumno.id).filter(filtro(user))
        if alumno_id is not None:
            consulta = consulta.filter(Alumno.id == alumno_id)
        return {aid for (aid,) in consulta}


def exigir_planeacion(doc_id: str, user: SessionUser, *, crear=False):
    doc = planeacion_por_id_sql(doc_id)
    if doc is None and crear:
        return None
    if doc and not user.director and doc.get("metadatos", {}).get("origen_privado_sin_cuenta_verificada"):
        raise HTTPException(404, "Planeación no disponible.")
    grupo = grupo_spa_sql(documento=doc_id) if doc and doc.get("metadatos", {}).get("grupo_compartido") else None
    if grupo:
        if not alcance_grupo(user, grupo[0]):
            raise HTTPException(404, "Planeación no disponible.")
    elif doc is None or (not user.director and doc.get("cuenta") != user.usuario):
        raise HTTPException(status_code=404, detail="Planeación no disponible.")
    if not user.director and (ids := _alumnos_en_planeacion(doc)) and not ids <= _alumnos_en_alcance(user):
        raise HTTPException(status_code=404, detail="Planeación no disponible.")
    return doc


@app.get("/api/escuelas")
def listar_escuelas(user: SessionUser = Depends(validar_token_sesion)):
    """Retorna las 8 primarias oficiales de la Zona 001."""
    return obtener_catalogo_escuelas()


@app.get("/api/alumnos")
def listar_alumnos(
    escuela: Optional[str] = None,
    user: SessionUser = Depends(validar_token_sesion)
):
    """Padrón de alumnos autorizado según el rol del usuario."""
    alumnos = obtener_alumnos_autorizados(
        usuario_rol=user.rol,
        escuelas_permitidas=user.escuelas_permitidas,
        nombre_docente=user.nombre
    )
    if not user.director:
        ids = _alumnos_en_alcance(user)
        alumnos = [a for a in alumnos if a["id"] in ids]
    if escuela:
        escuela_norm = escuela.strip().lower()
        alumnos = [a for a in alumnos if escuela_norm in str(a.get("escuela", "")).lower() or escuela_norm in str(a.get("id_escuela", "")).lower()]
    return alumnos


@app.post("/api/alumnos")
def crear_alumno(payload: AlumnoPayload, user: SessionUser = Depends(validar_token_sesion)):
    """Registra un nuevo alumno en la base de datos."""
    padron_excel.autorizar(user)
    if not user.director and payload.id_escuela not in user.escuelas_permitidas:
        raise HTTPException(status_code=403, detail="No tiene permisos para agregar alumnos en esta escuela.")
    doc_dict = {
        "Nombre_Completo": payload.nombre_completo,
        "CURP": payload.curp,
        "Edad_1_Septiembre": payload.edad_1_septiembre,
        "Sexo": payload.sexo,
        "Situacion_Alumno": payload.situacion_alumno,
        "Nivel_Educativo": payload.nivel_educativo,
        "Grado": payload.grado,
        "Grupo": payload.grupo,
        "ID_Escuela": payload.id_escuela,
        "Nombre_Escuela": payload.nombre_escuela,
        "Maestra de Apoyo": payload.maestra_apoyo or user.nombre,
        "Condicion_Discapacidad": payload.condicion_discapacidad,
        "Estatus": "Activo",
        "Tipo_Atencion": payload.tipo_atencion,
    }
    nuevo_id = padron_nominal.alta(doc_dict, user)
    return {"status": "success", "id": nuevo_id, "mensaje": "Alumno registrado exitosamente."}


@app.put("/api/alumnos/{alumno_id}")
def editar_alumno(alumno_id: str, payload: Dict[str, Any], user: SessionUser = Depends(validar_token_sesion)):
    if any(not isinstance(valor, str) for valor in payload.values()):
        raise HTTPException(422, "Los campos nominales deben ser texto.")
    return {"status": "success", **padron_nominal.editar_compatible(alumno_id, payload, user)}


@app.get("/api/alumnos/{alumno_id}/ficha")
def consultar_ficha(alumno_id: str, user: SessionUser = Depends(validar_token_sesion)):
    return padron_nominal.consultar(alumno_id, user)


@app.put("/api/alumnos/{alumno_id}/ficha")
def editar_ficha(alumno_id: str, payload: padron_nominal.EdicionNominal,
                 user: SessionUser = Depends(validar_token_sesion)):
    return padron_nominal.editar(alumno_id, payload, user)


@app.get("/api/alumnos/{alumno_id}/movimientos")
def historial_padron(alumno_id: str, user: SessionUser = Depends(validar_token_sesion)):
    return padron_nominal.historial(alumno_id, user)


@app.get("/api/alumnos/{alumno_id}/destinos")
def destinos_padron(alumno_id: str, user: SessionUser = Depends(validar_token_sesion)):
    return padron_nominal.destinos(alumno_id, user)


@app.post("/api/alumnos/{alumno_id}/movimientos")
def mover_alumno(alumno_id: str, payload: padron_nominal.MovimientoNominal,
                user: SessionUser = Depends(validar_token_sesion)):
    return padron_nominal.mover(alumno_id, payload, user)




def _padron_oficial_autorizado(user):
    from data.sql_repository import alumnos_sql, escuelas_sql
    from services.padron_oficial import vista_padron_oficial

    alumnos = alumnos_sql()
    alumnos = alumnos[alumnos["ID_Alumno"].isin(_alumnos_en_alcance(user))]
    escuelas = escuelas_sql()
    if not user.director:
        escuelas = escuelas[escuelas["ID_Escuela"].isin(set(alumnos["ID_Escuela"].astype(str)))]
    activo = alumnos["Estatus"].fillna("").astype(str).str.strip().str.upper().eq("ACTIVO")
    curps = alumnos["CURP"].fillna("").astype(str).str.strip().str.upper()
    validos = activo & curps.str.fullmatch(r"[A-Z0-9]{18}", na=False)
    duplicados = int(curps[validos].duplicated(keep=False).sum())
    incluidos = len(vista_padron_oficial(alumnos, escuelas)) if not duplicados else 0
    return alumnos, escuelas, {"detectados": len(alumnos), "incluidos": incluidos,
        "pendientes": len(alumnos) - incluidos, "curp_duplicadas": duplicados,
        "inactivos": int((~activo).sum()), "curp_no_exportables": int((activo & ~validos).sum())}


@app.get("/api/reportes/padron-oficial/resumen")
def resumen_padron_oficial(user: SessionUser = Depends(validar_token_sesion)):
    return _padron_oficial_autorizado(user)[2]



@app.get("/api/reportes/padron-oficial.xlsx")
def exportar_padron_oficial(user: SessionUser = Depends(validar_token_sesion)):
    from documents.reportes import generar_padron_usaer

    alumnos, escuelas, resumen = _padron_oficial_autorizado(user)
    if resumen["curp_duplicadas"]:
        raise HTTPException(409, "Concilia las CURP duplicadas antes de generar el formato oficial.")
    archivo = generar_padron_usaer(alumnos, escuelas)
    return Response(archivo, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="Padron-oficial-USAER.xlsx"',
                 "X-USAER-Registros": str(resumen["incluidos"]), "X-USAER-Pendientes": str(resumen["pendientes"])})

@app.get("/api/alumnos/exportar")
def exportar_alumnos_csv(user: SessionUser = Depends(validar_token_sesion)):
    """Exporta el padrón autorizado en formato CSV para respaldos."""
    alumnos = listar_alumnos(user=user)
    df = pd.DataFrame(alumnos)
    csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="Padron_Alumnos_USAER_2E.csv"'}
    )


@app.post("/api/alumnos/importar-excel")
async def importar_excel(request: Request, user: SessionUser = Depends(validar_token_sesion)):
    from starlette.concurrency import run_in_threadpool
    padron_excel.autorizar(user)
    revision = request.headers.get("X-USAER-Revision")
    if revision is not None and not re.fullmatch(r"[0-9a-f]{64}", revision):
        raise HTTPException(422, "Revisión inválida.")
    archivo = bytearray()
    async for fragmento in request.stream():
        if len(archivo) + len(fragmento) > padron_excel.LIMITE:
            raise HTTPException(413, "Usa un Excel .xlsx de hasta 16 MB.")
        archivo.extend(fragmento)
    return await run_in_threadpool(padron_excel.procesar, bytes(archivo), user, revision)


@app.get("/api/alumnos/importar-excel/permisos")
def permisos_importacion_padron(user: SessionUser = Depends(validar_token_sesion)):
    return {"permitido": padron_excel.puede_importar(user)}


@app.get("/api/alumnos/exportar.xlsx")
def exportar_padron_xlsx(user: SessionUser = Depends(validar_token_sesion)):
    from documents.reportes import generar_padron_usaer

    alumnos = alumnos_sql()
    escuelas = obtener_catalogo_escuelas()
    if not user.director:
        alumnos = alumnos[alumnos["ID_Alumno"].isin(_alumnos_en_alcance(user))]
        escuelas = [e for e in escuelas if e["id"] in user.escuelas_permitidas]
    catalogo = pd.DataFrame([{"ID_Escuela": e["id"], "Nombre_Escuela": e["nombre"],
                              "CCT_Escuela": e["cct"], "Turno_Escuela": e["turno"]} for e in escuelas])
    archivo = generar_padron_usaer(alumnos, catalogo)
    return Response(archivo, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": 'attachment; filename="Padron_USAER_2E.xlsx"',
                             "Cache-Control": "no-store"})

# -------------------------------------------------------------
# 3. EXPEDIENTES Y SEGUIMIENTO EDUCATIVO
# -------------------------------------------------------------

@app.get("/api/expedientes/{alumno_id}/originales-b01")
def originales_b01(alumno_id: str, original: Optional[str] = None,
                   user: SessionUser = Depends(validar_token_sesion)):
    from data.database import get_session

    if os.getenv("USAER_SPA_MODE") not in {"b01-private-local", "usaer-private-local"}:
        raise HTTPException(status_code=404)
    exigir_direccion(user)
    exigir_alumno(alumno_id, user)
    with get_session() as db:
        if original:
            dato = db.execute(text("""SELECT contenido FROM spa_b01_originales
                WHERE id=:original AND :alumno=ANY(alumnos)"""),
                {"original": original, "alumno": alumno_id}).scalar_one_or_none()
            if dato is None:
                raise HTTPException(status_code=404)
            from fastapi.responses import JSONResponse

            return JSONResponse(dato, headers={"Content-Disposition": 'attachment; filename="original-b01.json"'})
        if not db.scalar(text("SELECT to_regclass('public.spa_b01_originales') IS NOT NULL")):
            return []
        return [dict(fila) for fila in db.execute(text("""SELECT id,tipo,ciclo,versiones
            FROM spa_b01_originales WHERE :alumno=ANY(alumnos) ORDER BY tipo,ciclo,id"""),
            {"alumno": alumno_id}).mappings()]


@app.get("/api/expedientes/{alumno_id}")
def ver_expediente(alumno_id: str, user: SessionUser = Depends(validar_token_sesion)):
    """Expediente integral (BAP, sugerencias, eventos cronológicos, derivación, EPP)."""
    from services.epp_modelo import AREAS, conclusion_vigente

    alumno = exigir_alumno(alumno_id, user)
    expediente = obtener_expediente_completo(alumno_id, alumno=alumno)
    expediente["originales_b01_disponibles"] = user.director and os.getenv("USAER_SPA_MODE") in {"b01-private-local", "usaer-private-local"}
    informes = _listar_informes_autorizados(alumno, user)
    planes = planes_previos_spa_sql(alumno_id, "", user.usuario, direccion=user.director)
    expediente["seguimiento"] = [
        {"tipo": tipo, "id": fila["id"], "fecha": fila["fecha"], "detalle": fila.get(campo) or tipo}
        for clave, tipo, campo in (
            ("anexo3_bap", "BAP", "pedagogicas"), ("anexo4_sugerencias", "Sugerencia", "sugerencias"),
            ("anexo5_eventos", "Evento significativo", "evento"),
        )
        for fila in expediente[clave]
    ]
    comparativo = []
    for epp in epp_listar_sql([alumno_id]):
        anexo = anexo_epp(epp)
        partes = anexo["partes"]
        conclusion_confirmada = conclusion_vigente(anexo)
        comparativo.append({
            "ciclo": epp["ciclo"], "fecha": epp["fecha"],
            "areas_validadas": [area for area in AREAS if partes[area]["contenido"].get("validada")],
            "evaluaciones": sum(len(partes[area]["contenido"].get("evaluaciones", [])) for area in AREAS),
            "conclusion_confirmada": conclusion_confirmada,
            "nee_confirmadas": [r["texto"] for r in partes["Conclusión"].get("nee_confirmadas", [])]
            if conclusion_confirmada else [],
        })
        expediente["seguimiento"].append({
            "tipo": "EPP", "id": epp["id"], "fecha": epp["fecha"], "detalle": epp["ciclo"],
        })
        expediente["seguimiento"].extend(
            {"tipo": "NEE vigente", "id": nee["id"], "fecha": nee["desde"], "detalle": nee["texto"]}
            for nee in nee_vigentes(epp)
        )
    expediente["seguimiento"].extend(
        {"tipo": "Informe", "id": informe["id"], "fecha": informe["actualizado_en"],
         "detalle": informe["titulo"]} for informe in informes
    )
    expediente["seguimiento"].extend(
        {"tipo": "Plan individual", "id": plan["id"], "fecha": str(plan["datos"].get("Fecha") or ""),
         "detalle": plan["metadatos"].get("titulo") or f"Anexo {plan['formato']}"} for plan in planes
    )
    actas = _actas_vinculadas(alumno_id, user)
    expediente["seguimiento"].extend(
        {"tipo": "Acta", "id": acta["id"], "fecha": acta["fecha"],
         "detalle": acta["acuerdos"] or acta["tipo_acta"]} for acta in actas
    )
    expediente["seguimiento"].sort(key=lambda fila: (fila["fecha"], fila["tipo"], fila["id"]), reverse=True)
    expediente["comparativo_epp"] = sorted(comparativo, key=lambda fila: fila["ciclo"], reverse=True)
    expediente["total_documentos"] += len(informes) + len(planes) + len(actas)
    from data.database import ExpedienteHistoricoSPA, RelacionHistoricaSPA, get_session
    with get_session() as db:
        fichas = db.query(ExpedienteHistoricoSPA).filter_by(alumno_id=alumno_id).order_by(
            ExpedienteHistoricoSPA.apertura, ExpedienteHistoricoSPA.id,
        )
        expediente["expedientes_historicos"] = [
            {"id": fila.id, "escuela_id": fila.escuela_id, "estado": fila.estado,
             "apertura": fila.apertura, "actualizado": fila.actualizado}
            for fila in fichas if user.director or fila.escuela_id == alumno["id_escuela"]
        ]
        if user.director:
            ids = [f["id"] for f in expediente["expedientes_historicos"]]
            expediente["relaciones_historicas"] = [
                {"id": r.id, "expediente_id": r.expediente_id,
                 "tipo": r.tipo_documento, "documento_id": r.documento_id,
                 "documento_origen_id": r.documento_origen_id}
                for r in db.query(RelacionHistoricaSPA).filter(RelacionHistoricaSPA.expediente_id.in_(ids))
                .order_by(RelacionHistoricaSPA.id)
            ]
    return expediente

# -------------------------------------------------------------
# 4. EVALUACIÓN PSICOPEDAGÓGICA (EPP) MULTI-ÁREA
# -------------------------------------------------------------

AREAS_EPP = {"Aprendizaje": "APRENDIZAJE", "Psicología": "PSICOLOGIA",
             "Comunicación": "COMUNICACION", "Trabajo Social": "TRABAJO_SOCIAL"}


def areas_epp_editables(user: SessionUser):
    if user.director:
        return list(AREAS_EPP.values())
    return [AREAS_EPP[user.area]] if user.area in AREAS_EPP else []


def ciclo_epp(ciclo: str):
    if not re.fullmatch(r"20\d{2}-20\d{2}", ciclo) or int(ciclo[5:]) != int(ciclo[:4]) + 1:
        raise HTTPException(422, "Indica un ciclo válido (AAAA-AAAA).")
    return ciclo


@app.get("/api/epp/{alumno_id}/contextos/{tipo}")
def consultar_contexto_epp(alumno_id: str, tipo: str, ciclo: str = "2026-2027",
                           user: SessionUser = Depends(validar_token_sesion)):
    exigir_alumno(alumno_id, user)
    return contextos_epp.consultar(obtener_epp_documento(alumno_id, ciclo_epp(ciclo)), tipo, user)


@app.put("/api/epp/{alumno_id}/contextos/{tipo}")
def guardar_contexto_epp(alumno_id: str, tipo: str, payload: contextos_epp.CapturaContexto,
                         ciclo: str = "2026-2027", user: SessionUser = Depends(validar_token_sesion)):
    exigir_alumno(alumno_id, user)
    epp = obtener_epp_documento(alumno_id, ciclo_epp(ciclo))
    actualizado = contextos_epp.guardar(epp, tipo, payload, user)
    guardar_epp_documento(actualizado, autor_cuenta=user.usuario)
    return contextos_epp.consultar(actualizado, tipo, user)


@app.get("/api/epp/{alumno_id}/anexo")
def consultar_anexo_epp(alumno_id: str, ciclo: str = "2026-2027", user: SessionUser = Depends(validar_token_sesion)):
    from services.epp_modelo import AREAS, FAMILIA, HISTORIA, conclusion_vigente
    exigir_alumno(alumno_id, user)
    epp = obtener_epp_documento(alumno_id, ciclo_epp(ciclo))
    anexo = anexo_epp(epp)
    return {**anexo, "editables": [*AREAS, "Conclusión"] if user.director else [user.area],
            "conclusion_vigente": conclusion_vigente(anexo), "nee_vigentes": nee_vigentes(epp),
            "columnas": {"familia": list(FAMILIA), "historia": list(HISTORIA)},
            "ciclos": sorted({d["ciclo"] for d in epp_listar_sql([alumno_id])}, reverse=True)}


@app.put("/api/epp/{alumno_id}/anexo/{area}")
def guardar_anexo_epp(alumno_id: str, area: str, payload: SeccionEPP, ciclo: str = "2026-2027",
                      user: SessionUser = Depends(validar_token_sesion)):
    exigir_alumno(alumno_id, user)
    epp = obtener_epp_documento(alumno_id, ciclo_epp(ciclo))
    actualizado = editar_anexo(epp, area, payload.valor, payload.revision, user, payload.nee)
    return guardar_epp_documento(actualizado, autor_cuenta=user.usuario)


class AplicacionEPP(BaseModel):
    revision: str = Field(max_length=64)
    captura: dict
    incorporar: bool = False
    revisada: bool = False


class EvaluacionExternaEPP(BaseModel):
    revision: str = Field(max_length=64)
    adjunto_id: str = Field(min_length=1, max_length=64)
    nombre: str = Field(min_length=1, max_length=255)
    fecha: date
    resultados: str = Field(min_length=1, max_length=11000)
    revisada: bool
    vigente_hasta: date | None = None


@app.put("/api/epp/{alumno_id}/externa/{area}")
def guardar_evaluacion_externa(alumno_id: str, area: str, payload: EvaluacionExternaEPP,
                                ciclo: str = "2026-2027", user: SessionUser = Depends(validar_token_sesion)):
    from services.epp_entrada import entrada_directa
    from services.epp_modelo import AREAS

    exigir_alumno(alumno_id, user)
    if area not in AREAS or (not user.director and area != user.area):
        raise HTTPException(403, "La evaluación corresponde a otra función.")
    if payload.vigente_hasta and payload.vigente_hasta < payload.fecha:
        raise HTTPException(422, "La vigencia no puede preceder a la evaluación.")
    if not payload.revisada:
        raise HTTPException(422, "Coteja el resumen con el original antes de incorporarlo.")
    adjunto = next((a for a in adjuntos.listar(alumno_id) if a["id"] == payload.adjunto_id), None)
    if not adjunto:
        raise HTTPException(404, "El PDF no pertenece al expediente.")
    epp = obtener_epp_documento(alumno_id, ciclo_epp(ciclo))
    if epp["revision"] != payload.revision:
        raise HTTPException(409, "La EPP cambió. Reabre el ciclo antes de guardar.")
    try:
        evaluacion = entrada_directa({
            "Instrumento o técnica aplicada": payload.nombre,
            "Fecha de aplicación (AAAA-MM-DD)": payload.fecha.isoformat(),
            "Resultados y observaciones documentadas": payload.resultados,
        })
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    evaluacion.update(entrada="EXTERNA_REVISADA", adjunto_id=adjunto["id"],
                      archivo_sha256=adjunto["sha256"], resultados=payload.resultados.strip(),
                      vigente_hasta=payload.vigente_hasta.isoformat() if payload.vigente_hasta else "")
    contenido = anexo_epp(epp)["partes"][area]["contenido"]
    contenido["evaluaciones"] = [e for e in contenido["evaluaciones"]
                                if e.get("archivo_sha256") != adjunto["sha256"]] + [evaluacion]
    contenido["validada"] = False
    actualizado = editar_anexo(epp, area, contenido, payload.revision, user, [], actualizar_externa=True)
    return guardar_epp_documento(actualizado, autor_cuenta=user.usuario)


@app.get("/api/epp/{alumno_id}/instrumentos")
def catalogo_instrumentos_epp(alumno_id: str, user: SessionUser = Depends(validar_token_sesion)):
    from services.epp_instrumentos import DEFINICIONES, FUENTE, plantilla

    exigir_alumno(alumno_id, user)
    return {codigo: {**definicion, "fuente": FUENTE, "plantilla": plantilla(codigo)}
            for codigo, definicion in DEFINICIONES.items()
            if user.director or definicion["area"] == user.area}


@app.get("/api/epp/{alumno_id}/instrumentos/{codigo}/respaldo")
def respaldar_instrumento_epp(alumno_id: str, codigo: str, ciclo: str = "2026-2027",
                              user: SessionUser = Depends(validar_token_sesion)):
    from services.epp_instrumentos import DEFINICIONES, validar
    from fastapi.responses import JSONResponse
    exigir_alumno(alumno_id, user)
    definicion = DEFINICIONES.get(codigo)
    if not definicion or (not user.director and user.area != definicion["area"]):
        raise HTTPException(404, "Instrumento no disponible para tu función.")
    epp = obtener_epp_documento(alumno_id, ciclo_epp(ciclo))
    captura = anexo_epp(epp)["partes"][definicion["area"]]["contenido"].get("aplicaciones_en_curso", {}).get(codigo)
    if captura is None:
        raise HTTPException(404, "No hay una aplicación guardada.")
    return JSONResponse({"tipo":"USAER-aplicacion-v1", "documento":epp["id"],
                         "area":definicion["area"], "instrumento":codigo,
                         "vigente_hasta":anexo_epp(epp)["partes"][definicion["area"]]["contenido"].get("vigencias_instrumentos", {}).get(codigo, ""),
                         "captura":{k:v for k,v in validar(codigo, captura).items() if k != "vigente_hasta"}},
                        headers={"Content-Disposition": f'attachment; filename="aplicacion-{codigo}.json"',
                                 "Cache-Control":"no-store"})


@app.put("/api/epp/{alumno_id}/instrumentos/{codigo}")
def guardar_instrumento_epp(alumno_id: str, codigo: str, payload: AplicacionEPP, ciclo: str = "2026-2027",
                            user: SessionUser = Depends(validar_token_sesion)):
    from copy import deepcopy
    from services.epp_instrumentos import DEFINICIONES, calcular, incorporar, validar

    exigir_alumno(alumno_id, user)
    definicion = DEFINICIONES.get(codigo)
    if not definicion or (not user.director and definicion["area"] != user.area):
        raise HTTPException(404, "Instrumento no disponible para tu función.")
    epp = obtener_epp_documento(alumno_id, ciclo_epp(ciclo))
    if epp["revision"] != payload.revision:
        raise HTTPException(409, "La EPP cambió. Reabre el ciclo antes de guardar.")
    anexo = anexo_epp(epp)
    area = definicion["area"]
    try:
        captura = validar(codigo, payload.captura)
        if payload.incorporar:
            contenido = incorporar(anexo, area, codigo, captura, revisada=payload.revisada)
        else:
            contenido = deepcopy(anexo["partes"][area]["contenido"])
            contenido.setdefault("aplicaciones_en_curso", {})[codigo] = {k:v for k,v in captura.items() if k != "vigente_hasta"}
            contenido.setdefault("vigencias_instrumentos", {})[codigo] = captura.get("vigente_hasta", "")
            contenido["validada"] = False
        resultado = calcular(codigo, captura)
    except (ValueError, TypeError) as exc:
        raise HTTPException(422, str(exc)) from None
    actualizado = editar_anexo(epp, area, contenido, payload.revision, user, [])
    return {**guardar_epp_documento(actualizado, autor_cuenta=user.usuario), "resultado": resultado}


@app.get("/api/epp/{alumno_id}/historial")
def historial_epp(alumno_id: str, ciclo: str = "2026-2027", offset: int = 0,
                  user: SessionUser = Depends(validar_token_sesion)):
    from data.database import CambioSPA, get_session

    exigir_alumno(alumno_id, user)
    if not 0 <= offset <= 100000:
        raise HTTPException(422, "Página de historial inválida.")
    epp = obtener_epp_documento(alumno_id, ciclo_epp(ciclo))
    with get_session() as db:
        rows = db.query(CambioSPA).filter_by(tipo="epp", documento_id=epp["id"]).order_by(
            CambioSPA.fecha.desc(), CambioSPA.id.desc()).offset(offset).limit(30)
        return [{"revision":r.revision,"autor":r.autor,"fecha":r.fecha.isoformat()} for r in rows]


@app.get("/api/epp/{alumno_id}/historial/{revision}")
def consultar_version_epp(alumno_id: str, revision: str, ciclo: str = "2026-2027",
                         user: SessionUser = Depends(validar_token_sesion)):
    from data.database import CambioSPA, get_session
    from services.epp_modelo import conclusion_vigente
    import json

    exigir_alumno(alumno_id, user)
    epp = obtener_epp_documento(alumno_id, ciclo_epp(ciclo))
    with get_session() as db:
        row = db.query(CambioSPA).filter_by(tipo="epp",documento_id=epp["id"],revision=revision).first()
        if row is None:
            raise HTTPException(404, "Versión EPP no disponible.")
        documento = json.loads(row.contenido)
        if (documento.get("id") != epp["id"] or documento.get("alumno") != alumno_id
                or documento.get("ciclo") != ciclo):
            raise HTTPException(409, "La versión histórica requiere conciliación.")
        confirmado = conclusion_vigente(anexo_epp(documento))
        return {"revision":row.revision,"autor":row.autor,"fecha":row.fecha.isoformat(),
                "conclusion_confirmada":confirmado,"documento":documento}



@app.get("/api/epp/{alumno_id}/historial/{revision}/pdf")
def pdf_version_epp(alumno_id: str, revision: str, ciclo: str = "2026-2027",
                    user: SessionUser = Depends(validar_token_sesion)):
    from documents.epp import generar_pdf

    version = consultar_version_epp(alumno_id, revision, ciclo, user)
    documento = version["documento"]
    if not documento.get("partes", {}).get("META", {}).get("anexo_xvii"):
        raise HTTPException(409, "La versión histórica requiere cotejo con su formato original.")
    alumno = exigir_alumno(alumno_id, user)
    row = {"Nombre_Completo":alumno["nombre_completo"],"Nombre_Escuela":alumno["escuela"],
           "CURP":alumno["curp"],"Grado":alumno["grado"],"Grupo":alumno["grupo"]}
    pdf = generar_pdf(anexo_epp(documento), row, incluir_firmas=False, incluir_trazabilidad=True)
    return Response(pdf, media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="EPP-version-historica.pdf"'})



@app.get("/api/epp/{alumno_id}/pdf")
def descargar_epp(alumno_id: str, ciclo: str = "2026-2027", user: SessionUser = Depends(validar_token_sesion)):
    from documents.epp import generar_pdf
    alumno = exigir_alumno(alumno_id, user)
    row = {"Nombre_Completo": alumno["nombre_completo"], "Nombre_Escuela": alumno["escuela"],
           "CURP": alumno["curp"], "Grado": alumno["grado"], "Grupo": alumno["grupo"]}
    epp = anexo_epp(obtener_epp_documento(alumno_id, ciclo_epp(ciclo)))
    return Response(generar_pdf(epp, row, incluir_firmas=False, incluir_trazabilidad=True), media_type="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="EPP-Anexo-XVII.pdf"'})


@app.get("/api/epp/{alumno_id}")
def consultar_epp(alumno_id: str, user: SessionUser = Depends(validar_token_sesion)):
    """Recupera el informe EPP con sus cuatro áreas integradas."""
    exigir_alumno(alumno_id, user)
    return {**obtener_epp_documento(alumno_id), "areas_editables": areas_epp_editables(user)}


@app.post("/api/epp")
def guardar_epp(payload: EPPPayload, user: SessionUser = Depends(validar_token_sesion)):
    """Guarda o actualiza el informe EPP con hash de revisión atómico."""
    exigir_alumno(payload.alumno, user)
    actual = obtener_epp_documento(payload.alumno, payload.ciclo)
    if payload.revision != actual["revision"]:
        raise HTTPException(status_code=409, detail="La EPP cambió. Vuelve a abrirla antes de guardar.")
    partes = dict(actual["partes"])
    editables = areas_epp_editables(user)
    for area, contenido in payload.partes.items():
        if area in editables and isinstance(contenido, dict):
            if contenido != partes.get(area):
                canon = next((nombre for nombre, clave in AREAS_EPP.items() if clave == area), None)
                estructurada = partes.get("META", {}).get("anexo_xvii", {}).get(canon)
                if estructurada:
                    estructurada["contenido"]["validada"] = False
                    estructurada["revision"] = uuid.uuid4().hex
            partes[area] = contenido
        elif area == "META" and not isinstance(contenido, dict):
            raise HTTPException(status_code=422, detail="Metadatos de EPP inválidos.")
        elif area != "META" and contenido != partes.get(area):
            raise HTTPException(status_code=403, detail="Esta sección pertenece a otra área profesional.")
    return guardar_epp_documento(payload.model_dump() | {"partes": partes}, autor_cuenta=user.usuario)

# -------------------------------------------------------------
# 5. PLANEACIÓN PEDAGÓGICA (FORMATOS XXIII, XXV, XIX, XX)
# -------------------------------------------------------------

@app.get("/api/planeaciones")
def listar_planeaciones(user: SessionUser = Depends(validar_token_sesion)):
    """Lista resumida de planeaciones con límite duro para el usuario activo."""
    from data.sql_repository import planeaciones_resumen_sql
    planes = planeaciones_resumen_sql(cuenta=user.usuario, es_director=user.director,
                                     escuelas_spa=user.escuelas_permitidas, compartir_grupos=area_compartida(user),
                                     limite=None if os.getenv("USAER_SPA_MODE") == "usaer-private-local" else 50)
    if user.director:
        return planes
    alumnos = _alumnos_en_alcance(user)
    return [doc for doc in planes if not doc.get("metadatos", {}).get("origen_privado_sin_cuenta_verificada")
            and _alumnos_en_planeacion(doc) <= alumnos]


def _continuidad_trimestral(doc, alumno_id, user):
    """Solo trae decisiones del mismo docente, alumno, escuela, función y ciclo."""
    from services.curriculo import grados, opciones
    datos, meta = doc["datos"], doc["metadatos"]
    epp = obtener_epp_documento(alumno_id, datos["Curso escolar"])
    necesidades = nee_vigentes(epp)
    if len(necesidades) == 1:
        meta["spa_nee_id"] = necesidades[0]["id"]
    def anterior(p):
        d = p["datos"]
        return (p.get("formato") == doc["formato"] and d.get("Curso escolar") == datos["Curso escolar"]
                and d.get("ID_Escuela") == datos["ID_Escuela"] and d.get("Función") == datos["Función"]
                and str(d.get("Trimestre")) in {str(t) for t in range(1, datos["Trimestre"])})
    if datos["Trimestre"] == 1:
        return
    previos = planes_previos_spa_sql(alumno_id, doc["id"], user.usuario, filtro=anterior)
    if not previos:
        return
    previo = max(previos, key=lambda p: int(p["datos"]["Trimestre"]))
    m = previo.get("metadatos", {})
    if m.get("spa_nee_id") in {n["id"] for n in necesidades}:
        meta["spa_nee_id"] = m["spa_nee_id"]
    campo = m.get("spa_campo_pda", "Lenguajes")
    if isinstance(campo, str) and m.get("spa_pda_id") in {r["id"] for r in opciones(doc, campo, grados(doc))}:
        meta.update(spa_pda_id=m["spa_pda_id"], spa_campo_pda=campo)
    for k in ("metodo_docente", "materiales_docentes"):
        if isinstance(m.get(k), str):
            meta[k] = m[k][:500]
    apoyos, avances = [], []
    if isinstance(m.get("apoyos_docentes"), str) and m["apoyos_docentes"].strip():
        apoyos.append(m["apoyos_docentes"][:500])
    for k in ("Evaluación", "Observaciones", "Resultados obtenidos en los diferentes contextos"):
        t = previo.get("textos", {}).get(k)
        if isinstance(t, str) and t.strip():
            avances.append(k + " registrada: " + t[:500])
    for tabla in ("necesidades", "curriculo", "barreras", "dosificacion", "evaluacion_final"):
        for fila in previo.get("tablas", {}).get(tabla, [])[:10]:
            for k in ("Apoyos", "Ajustes razonables", "Apoyos o ajustes", "Apoyos y/o ajustes razonables"):
                if fila.get(k): apoyos.append(str(fila[k])[:500])
            for k in ("Seguimiento", "Situación final del alumno en relación con sus NEE", "Resultados de la implementación de las acciones para minimizar o eliminar las barreras"):
                if fila.get(k): avances.append(str(fila[k])[:500])
    meta["continuidad_trimestral"] = {"id": previo["id"], "revision": previo["revision"],
        "trimestre": previo["datos"]["Trimestre"], "apoyos": list(dict.fromkeys(apoyos))[:6],
        "seguimiento": list(dict.fromkeys(avances))[:6]}


@app.post("/api/planeaciones/nueva")
def nueva_planeacion(payload: NuevaPlaneacion, user: SessionUser = Depends(validar_token_sesion)):
    alcance = _alumnos_en_alcance(user) if not user.director else None
    registros = [r for r in alumnos_sql().to_dict("records")
                 if r["ID_Alumno"] in payload.alumnos
                 and (alcance is None or r["ID_Alumno"] in alcance)]
    if {r["ID_Alumno"] for r in registros} != set(payload.alumnos):
        raise HTTPException(status_code=404, detail="Algún alumno no está disponible.")
    if len(set(payload.alumnos)) != len(payload.alumnos):
        raise HTTPException(status_code=422, detail="Elimina los alumnos duplicados.")
    if payload.modalidad == "individual" and len(payload.alumnos) != 1:
        raise HTTPException(status_code=422, detail="Selecciona un alumno para la planeación individual.")
    clave = None
    if payload.modalidad == "grupal":
        grupos = {(r["ID_Escuela"], grado_canonico(r["Grado"]), grupo_canonico(r["Grupo"])) for r in registros}
        if payload.formato == "XXI" or len(grupos) != 1 or not all(next(iter(grupos))):
            raise HTTPException(422, "Selecciona un grupo identificado y un formato grupal.")
        escuela, grado, grupo = next(iter(grupos))
        if not alcance_grupo(user, escuela):
            raise HTTPException(404, "Planeación no disponible.")
        clave = (escuela, grado, grupo, f"{payload.ciclo_inicio}-{payload.ciclo_inicio + 1}")
        existente = grupo_spa_sql(clave=clave)
        if existente:
            exigir_planeacion(existente[4], user)
            return {"id": existente[4], "existente": True}
        if not puede_coordinar(user):
            raise HTTPException(403, "Aprendizaje o Dirección debe abrir primero la guía anual.")
        candidatos = candidatos_grupo_spa_sql(clave)
        if len(candidatos) > 1:
            raise HTTPException(409, "Hay guías previas duplicadas. Requieren conciliación por Dirección.")
        if candidatos:
            anterior = exigir_planeacion(candidatos[0], user)
            anterior["metadatos"]["grupo_compartido"] = True
            anterior["metadatos"]["periodicidad"] = "anual"
            anterior["metadatos"]["alcance_grupal"] = {"grado": grado, "grupo": grupo}
            actualizar_guia(anterior)
            return guardar_planeacion_transaccional(anterior, autor_cuenta=user.usuario,
                                                   existente=True, grupo_spa=clave)
    try:
        doc = crear_plantilla(payload.formato, payload.alumnos, registros, autor=user.nombre,
                              funcion=user.area, ciclo_inicio=payload.ciclo_inicio, trimestre=payload.trimestre)
    except (ValueError, PermissionError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    doc["id"] = f"plan-{uuid.uuid4().hex}"
    doc["metadatos"].update(modalidad_planeacion=payload.modalidad, plantilla_spa=True,
                           titulo=f"Planeación {payload.modalidad} · {doc['datos']['Curso escolar']}")
    ciclo = doc["datos"]["Curso escolar"]
    fuentes = {}
    for epp in epp_listar_sql(payload.alumnos):
        if epp["ciclo"] == ciclo:
            fuentes.setdefault(epp["alumno"], {"alumno": epp["alumno"], "documento": epp["id"],
                                                "revision": epp["revision"], "tipo": "EPP"})
    doc["metadatos"]["vinculos_documentales"] = list(fuentes.values())
    if payload.modalidad == "individual":
        _continuidad_trimestral(doc, payload.alumnos[0], user)
    if payload.modalidad == "grupal":
        doc["datos"]["Vigencia"] = doc["datos"]["Curso escolar"]
        doc["datos"].pop("Trimestre", None)
        doc["datos"].pop("Periodo", None)
        doc["metadatos"].update(grupo_compartido=True, periodicidad="anual",
                                 alcance_grupal={"grado": clave[1], "grupo": clave[2]})
        for alumno in doc["datos"]["Alumnos"]:
            alumno.update(Grado=clave[1], Grupo=clave[2])
        actualizar_guia(doc)
    try:
        return guardar_planeacion_transaccional(doc, autor_cuenta=user.usuario, existente=False,
                                               alumnos_spa=payload.alumnos, grupo_spa=clave)
    except HTTPException as exc:
        concurrente = grupo_spa_sql(clave=clave) if clave and exc.status_code == 409 else None
        if concurrente:
            exigir_planeacion(concurrente[4], user)
            return {"id": concurrente[4], "existente": True}
        raise


@app.post("/api/planeaciones/{doc_id}/matricula")
def actualizar_matricula_grupal(doc_id: str, payload: dict, user: SessionUser = Depends(validar_token_sesion)):
    doc = exigir_planeacion(doc_id, user)
    if not doc["metadatos"].get("grupo_compartido") or not puede_coordinar(user):
        raise HTTPException(403, "La actualización de matrícula corresponde a Aprendizaje o Dirección.")
    if payload.get("revision") != doc["revision"]:
        raise HTTPException(409, "La guía cambió. Reabre el documento.")
    alcance = _alumnos_en_alcance(user) if not user.director else None
    ids = sincronizar_matricula(doc, [r for r in alumnos_sql().to_dict("records")
                                    if alcance is None or r["ID_Alumno"] in alcance])
    return guardar_planeacion_transaccional(doc, autor_cuenta=user.usuario, existente=True, alumnos_spa=ids)


@app.get("/api/planeaciones/{doc_id}/historial")
def historial_planeacion(doc_id: str, user: SessionUser = Depends(validar_token_sesion)):
    historial = historial_spa_sql("planeacion", doc_id, cuenta=exigir_planeacion(doc_id, user)["cuenta"])
    if user.director:
        return historial
    alumnos = _alumnos_en_alcance(user)
    return [fila for fila in historial if _alumnos_en_planeacion(fila["documento"]) <= alumnos]


def exigir_plantilla(doc_id: str, user: SessionUser):
    doc = exigir_planeacion(doc_id, user)
    if not doc.get("metadatos", {}).get("plantilla_spa"):
        raise HTTPException(status_code=422, detail="Abre una planeación vinculada al padrón.")
    return doc


@app.get("/api/planeaciones/{doc_id}/referentes")
def referentes_planeacion(doc_id: str, campo: str = "Lenguajes",
                           user: SessionUser = Depends(validar_token_sesion)):
    from services.curriculo import grados, opciones
    doc = exigir_plantilla(doc_id, user)
    return opciones(doc, campo, grados(doc))


@app.post("/api/planeaciones/{doc_id}/propuesta")
def propuesta_planeacion(doc_id: str, payload: PropuestaPlaneacion,
                         user: SessionUser = Depends(validar_token_sesion)):
    from services.curriculo import grados, opciones, vincular
    from services.epp_modelo import conclusion_vigente
    from services.planeacion_calidad import revisar
    from services.planeacion_local import preparar_documento_autorizado, vincular_cadena_nee

    doc = exigir_plantilla(doc_id, user)
    if payload.alumno_id and payload.alumno_id not in _alumnos_en_planeacion(doc):
        raise HTTPException(404, "Alumno no disponible en esta planeación.")
    doc["metadatos"]["fuentes"] = []
    necesidad = None
    oficial = None
    if payload.nee_id:
        if doc["metadatos"]["modalidad_planeacion"] != "individual":
            raise HTTPException(422, "Selecciona la NEE en una planeación individual.")
        aid = doc["datos"]["Alumnos"][0]["ID_Alumno"]
        epp = obtener_epp_documento(aid, doc["datos"]["Curso escolar"])
        conclusion = anexo_epp(epp)["partes"]["Conclusión"]["contenido"]
        necesidad = next((r for r in nee_vigentes(epp) if r["id"] == payload.nee_id), None)
        if not necesidad:
            raise HTTPException(422, "La NEE no está confirmada y vigente para este alumno y ciclo.")
        if not payload.pda_id:
            raise HTTPException(422, "Selecciona un PDA del catálogo oficial.")
        doc["metadatos"]["fuentes"].append({
            "tipo": "NEE", "alumno": aid, "referencia": f"NEE {necesidad['id']} · EPP {epp['id']}",
            "texto": f"{necesidad['texto']} · {necesidad['fundamento']}", "vinculo_verificado": True,
        })
    for alumno in doc["datos"]["Alumnos"]:
        aid = alumno["ID_Alumno"]
        if payload.alumno_id and aid != payload.alumno_id:
            continue
        autorizado = exigir_alumno(aid, user)
        expediente = obtener_expediente_completo(aid, alumno=autorizado)
        fuentes = [
            (tipo, str(row["id"]), " · ".join(str(row.get(k) or "") for k in claves))
            for clave, tipo, claves in (
                ("anexo3_bap", "BAP", ("fisicas", "actitudinales", "pedagogicas", "organizativas")),
                ("anexo4_sugerencias", "Sugerencia", ("sugerencias",)),
                ("anexo5_eventos", "Evento", ("evento",)),
            )
            for row in expediente[clave][:5]
        ]
        epp = obtener_epp_documento(aid, doc["datos"]["Curso escolar"])
        if epp.get("revision") == "rev-epp-inicial":
            epp = None
        if epp:
            fuentes.extend(contextos_epp.fuentes(epp))
            fuentes.extend(("NEE", f"{n['id']} · EPP {epp['id']}", n["texto"] + " · " + n["fundamento"])
                           for n in nee_vigentes(epp) if not necesidad or n["id"] != necesidad["id"])
            anexo = anexo_epp(epp)
            if conclusion_vigente(anexo):
                for fila in anexo["partes"]["Conclusión"]["contenido"].get("bap", [])[:8]:
                    texto_bap = " · ".join(str(fila.get(k) or "").strip() for k in
                        ("Contextos", "Tipo de barrera", "Acciones generales", "Apoyos", "Ajustes razonables"))
                    if texto_bap.strip(" ·"):
                        fuentes.append(("BAP", f"EPP {epp['id']} · rev. {epp['revision']}", texto_bap))
            for area, apartado in anexo["partes"].items():
                if user.director or area == user.area:
                    contenido = apartado["contenido"]
                    textos = [contenido.get("sintesis", ""), *contenido.get("campos", {}).values()]
                    textos += [r.get("texto", "") for r in contenido.get("evaluaciones", [])]
                    fuentes.append(("EPP Anexo XVII", epp["id"], " · ".join(t for t in textos if t)))
            for area, campos in epp.get("partes", {}).items():
                if area in areas_epp_editables(user) and isinstance(campos, dict):
                    textos = " · ".join(v for v in campos.values() if isinstance(v, str) and v.strip())
                    fuentes.append(("EPP", epp["id"], textos))
        for previo in planes_previos_spa_sql(aid, doc_id, user.usuario, direccion=user.director):
            try:
                exigir_planeacion(previo["id"], user)
            except HTTPException as exc:
                if exc.status_code in (403,404): continue
                raise
            tipo = "Plan de intervención" if previo["formato"] == "XXI" else "Planeación previa"
            partes = [v for v in previo.get("textos", {}).values() if isinstance(v, str)]
            for tabla in ("aprendizajes", "necesidades", "dosificacion"):
                for fila in previo.get("tablas", {}).get(tabla, [])[:5]:
                    partes.extend(str(fila[k]) for k in ("Descriptor de logro", "Descriptor de Logro", "Actividades", "Seguimiento", "Apoyos", "Apoyos o ajustes", "Ajustes razonables") if fila.get(k))
            fuentes.append((tipo, f"{previo['id']} · rev. {previo['revision']}", " · ".join(partes)))
        for informe in _listar_informes_autorizados(autorizado, user, limite=3):
            resumen = " · ".join(informe[k] for k in CAMPOS_INFORME)
            if resumen.strip(" ·"):
                fuentes.append(("Informe educativo", f"{informe['id']} · rev. {informe['revision']}", resumen))
        for acta in _actas_vinculadas(aid, user, limite=3):
            resumen = " · ".join(v for v in (acta["acuerdos"], acta["seguimiento"]) if v)
            if resumen:
                fuentes.append(("Acta", acta["id"], resumen))
        doc["metadatos"]["fuentes"].extend(
            {"tipo": tipo, "alumno": aid, "referencia": f"{tipo} {origen}",
             "texto": texto[:1500], "vinculo_verificado": True}
            for tipo, origen, texto in fuentes if texto.strip(" ·")
        )
    contexto = doc.get("metadatos", {}).get("contexto_aulico") or doc.get("metadatos", {}).get("contexto_grupal_vinculado", {}).get("contexto")
    origen_contexto = doc.get("metadatos", {}).get("contexto_grupal_vinculado") or {"id": doc_id, "revision": doc["revision"]}
    for fila in origen_contexto.get("perfil", []):
        texto_perfil = " · ".join(str(fila.get(c, "")) for c in
            ("Situación inicial", "Aprendizaje", "Psicología", "Comunicación", "Trabajo Social", "Situación final") if fila.get(c))
        if texto_perfil:
            doc["metadatos"]["fuentes"].append({"tipo": "Perfil grupal · Anexo XIX",
                "alumno": fila["ID_Alumno"], "referencia": f"Guía {origen_contexto['id']} · revisión {origen_contexto['revision']}",
                "texto": texto_perfil, "vinculo_verificado": True})
    if contexto:
        from piloto_spa.backend.contexto_aulico import resumen
        texto = resumen(contexto)
        if texto:
            doc["metadatos"]["fuentes"].append({
                "tipo": "Contexto áulico · Anexo III", "alumno": "",
                "referencia": f"Guía {origen_contexto['id']} · revisión {origen_contexto['revision']}",
                "texto": texto, "vinculo_verificado": True})
    if payload.pda_id:
        oficial = next((r for r in opciones(doc, payload.campo, grados(doc)) if r["id"] == payload.pda_id), None)
        if not oficial:
            raise HTTPException(status_code=422, detail="El PDA no pertenece al catálogo del grado y campo.")
        doc = vincular(doc, payload.campo, [], [payload.pda_id])
    try:
        propuesta = preparar_documento_autorizado(doc, payload.enfoque, alumno_id=payload.alumno_id,
            variante=payload.variante, metodo=payload.metodo or str(doc["metadatos"].get("metodo_docente", ""))[:500],
            materiales_docentes=payload.materiales or str(doc["metadatos"].get("materiales_docentes", ""))[:500])
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if necesidad:
        for actividad in propuesta["propuestas"]:
            actividad.update(vincular_cadena_nee(actividad, necesidad, oficial["pda"], conclusion))
    return {**propuesta, "revision": doc["revision"], "indicadores": revisar(doc), "motor": "reglas_locales"}


@app.post("/api/planeaciones/{doc_id}/actividad-curricular-externa")
def actividad_curricular_externa(doc_id: str, payload: ActividadCurricularExterna,
                                user: SessionUser = Depends(validar_token_sesion)):
    from ai.actividades_curriculares import sugerir_con_gemini
    from services.curriculo import grados, opciones

    doc = exigir_plantilla(doc_id, user)
    if os.getenv("USAER_IA_CURRICULAR_HABILITADA") != "1" or not payload.autorizo:
        raise HTTPException(403, "La actividad externa requiere habilitación y autorización explícita.")
    referente = next((fila for fila in opciones(doc, payload.campo, grados(doc))
                      if fila["id"] == payload.pda_id), None)
    if referente is None:
        raise HTTPException(422, "Selecciona un PDA oficial del grado y campo de la planeación.")
    try:
        actividad = sugerir_con_gemini(referente["id"], autorizado=True)
    except PermissionError:
        raise HTTPException(403, "La integración curricular externa está deshabilitada.") from None
    except Exception:
        raise HTTPException(503, "No se pudo obtener la actividad curricular externa.") from None
    return {"actividad": actividad.model_dump(), "referente": referente, "revision": doc["revision"],
            "requiere_revision_docente": True}




def _perfil_grupal_vinculado(destino, referencia, user):
    if (not isinstance(referencia, dict) or set(referencia) != {"id", "revision"}
            or any(not isinstance(referencia[k], str) or not 1 <= len(referencia[k]) <= 64 for k in referencia)):
        raise HTTPException(422, "Selecciona una guía grupal y su revisión.")
    fuente = exigir_planeacion(referencia["id"], user)
    if (fuente["metadatos"].get("modalidad_planeacion") != "grupal"
            or destino["datos"]["Curso escolar"] != fuente["datos"]["Curso escolar"]
            or destino["datos"]["ID_Escuela"] != fuente["datos"]["ID_Escuela"]
            or not _alumnos_en_planeacion(destino)
            or not _alumnos_en_planeacion(destino) <= _alumnos_en_planeacion(fuente)):
        raise HTTPException(404, "La guía no corresponde al alumnado y ciclo del documento.")
    if fuente["revision"] != referencia["revision"]:
        raise HTTPException(409, "La guía cambió. Selecciona su revisión actual.")
    ids = _alumnos_en_planeacion(destino)
    return {"id": fuente["id"], "revision": fuente["revision"],
            "contexto": fuente["metadatos"].get("contexto_aulico", {}),
            "perfil": [r for r in fuente["metadatos"].get("guia_grupal_manual", {}).get("filas", [])
                       if r.get("ID_Alumno") in ids]}


@app.get("/api/planeaciones/{doc_id}/contextos-grupales")
def listar_contextos_grupales(doc_id: str, user: SessionUser = Depends(validar_token_sesion)):
    from data.sql_repository import planeaciones_resumen_sql

    destino = exigir_planeacion(doc_id, user)
    resultado = []
    candidatos = planeaciones_resumen_sql(user.usuario, es_director=user.director,
        escuelas_spa=user.escuelas_permitidas, compartir_grupos=area_compartida(user), limite=None)
    for fila in candidatos:
        if fila["id"] == doc_id or fila.get("metadatos", {}).get("modalidad_planeacion") != "grupal":
            continue
        ref = {"id": fila["id"], "revision": fila["revision"]}
        try:
            _perfil_grupal_vinculado(destino, ref, user)
        except HTTPException:
            continue
        resultado.append({**ref, "titulo": fila["metadatos"].get("titulo") or "Guía grupal anual"})
    return resultado



@app.get("/api/planeaciones/{doc_id}/contexto-aulico/pdf")
def exportar_contexto_aulico(doc_id: str, user: SessionUser = Depends(validar_token_sesion)):
    import json
    import pandas as pd
    from documents.anexos import anexo3_pdf

    doc = exigir_planeacion(doc_id, user)
    meta = doc.get("metadatos", {})
    captura = meta.get("contexto_aulico")
    if meta.get("modalidad_planeacion") != "grupal" or not captura or not captura.get("respuestas"):
        raise HTTPException(404, "La guía no tiene reactivos observados.")
    alcance = meta.get("alcance_grupal", {})
    objetivo = "-".join(("GRUPO", doc["datos"]["ID_Escuela"], alcance.get("grado", ""), alcance.get("grupo", "")))
    fila = {"ID_Alumno": objetivo, "Fecha": captura["fecha"], "ID_Personal": captura["autor"],
            "BAP_Fisicas": json.dumps(captura["respuestas"], ensure_ascii=False)}
    pdf = anexo3_pdf({}, pd.DataFrame([fila]), contexto=captura.get("observaciones", ""))
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="Contexto-aulico-Anexo-III.pdf"'})



@app.get("/api/planeaciones/{doc_id}")
def obtener_planeacion(doc_id: str, user: SessionUser = Depends(validar_token_sesion)):
    """Documento de planeación completo con cálculo oficial de firmas."""
    exigir_planeacion(doc_id, user, crear=doc_id.startswith("plan-nuevo-"))
    doc = obtener_planeacion_con_firmas(doc_id, usuario_cuenta=user.usuario)
    if doc.get("metadatos", {}).get("plantilla_spa"):
        from services.planeacion_modelo import FORMATOS
        doc["editor"] = dict(FORMATOS[doc["formato"]])
        if doc["metadatos"]["modalidad_planeacion"] == "individual":
            aid = doc["datos"]["Alumnos"][0]["ID_Alumno"]
            doc["editor"]["nee_confirmadas"] = nee_vigentes(
                obtener_epp_documento(aid, doc["datos"]["Curso escolar"])
            )
        if doc["metadatos"]["modalidad_planeacion"] == "grupal":
            from services.planeacion_modalidad import GUIA_XIX, GUIA_XX
            from piloto_spa.backend.contexto_aulico import ITEMS, FRECUENCIAS
            doc["editor"] = {**doc["editor"], "columnas_grupales": GUIA_XIX,
                             "items_contexto": ITEMS, "frecuencias_contexto": FRECUENCIAS}
            if doc["metadatos"].get("grupo_compartido"):
                doc["editor"].update(columnas_editables=columnas_editables(user),
                                     coordina=puede_coordinar(user), columnas_as=GUIA_XX)
    return doc


class CambioCeldaGrupal(BaseModel):
    tabla: Literal["filas", "as"]
    alumno: str = Field(min_length=1, max_length=64)
    campo: str = Field(min_length=1, max_length=120)
    revision: str = Field(max_length=64)
    texto: str = Field(max_length=12000)


@app.patch("/api/planeaciones/{doc_id}/celda")
def guardar_celda_grupal(doc_id: str, cambio: CambioCeldaGrupal, user: SessionUser = Depends(validar_token_sesion)):
    import json
    from data.database import PlaneacionDoc, get_session
    from data.sql_repository import ConflictoRevision, guardar_planeacion_sql
    from services.planeacion_modalidad import GUIA_XX

    grupo = grupo_spa_sql(documento=doc_id)
    if not grupo or not alcance_grupo(user, grupo[0]):
        raise HTTPException(404, "Planeación no disponible.")
    campos = columnas_editables(user) if cambio.tabla == "filas" else GUIA_XX[1:] if puede_coordinar(user) else []
    if cambio.campo not in campos:
        raise HTTPException(403, "Esa columna pertenece a otra función.")
    with get_session() as sesion:
        row = sesion.query(PlaneacionDoc).filter_by(id=doc_id).with_for_update().one_or_none()
        if row is None:
            raise HTTPException(404, "Planeación no disponible.")
        doc = json.loads(row.payload_json)
        if not user.director and not (_alumnos_en_planeacion(doc) | {cambio.alumno}) <= _alumnos_en_alcance(user, sesion=sesion):
            raise HTTPException(404, "Planeación no disponible.")
        meta = doc["metadatos"]
        fila = next((r for r in meta["guia_grupal_manual"][cambio.tabla] if r.get("ID_Alumno") == cambio.alumno), None)
        if fila is None:
            raise HTTPException(404, "El alumno ya no está en esta sección.")
        revision = meta.get("revisiones_celda", {}).get(cambio.tabla, {}).get(cambio.alumno, {}).get(cambio.campo, "")
        actual = fila.get(cambio.campo, "")
        if cambio.texto == actual:
            return {"texto": actual, "revision": revision}
        if cambio.revision != revision:
            raise HTTPException(409, {"mensaje": "Esta celda cambió. Revisa ambos textos.",
                                      "texto": actual, "revision": revision})
        fila[cambio.campo] = cambio.texto
        esperada = doc["revision"]
        doc["revision"] = "rev-" + uuid.uuid4().hex
        doc["guardado_en"] = time.strftime("%Y-%m-%d %H:%M:%S")
        try:
            guardar_planeacion_sql(doc, revision_esperada=esperada, existente_esperado=True,
                                   actor_spa=user.usuario, sesion=sesion)
        except ConflictoRevision as exc:
            raise HTTPException(409, "La guía cambió. Vuelve a consultar la celda.") from exc
        return {"texto": cambio.texto, "revision": doc["revision"]}


@app.post("/api/planeaciones")
def guardar_planeacion(payload: PlaneacionPayload, user: SessionUser = Depends(validar_token_sesion)):
    """Guarda planeación con control de versiones y verificación de concurrencia."""
    doc_dict = payload.model_dump()
    existente = exigir_planeacion(payload.id, user, crear=True) if payload.id else None
    if not existente and doc_dict["metadatos"].get("modalidad_planeacion") == "grupal":
        raise HTTPException(422, "Abre la guía anual desde Nueva planeación.")
    if existente:
        doc_dict["cuenta"] = existente["cuenta"]
    doc_dict["metadatos"].pop("plantilla_spa", None)
    doc_dict["metadatos"].pop("grupo_compartido", None)
    if existente and existente.get("metadatos", {}).get("grupo_compartido"):
        doc_dict = editar_grupo(existente, doc_dict, user)
    if existente and existente.get("metadatos", {}).get("plantilla_spa"):
        doc_dict["datos"] = existente["datos"]
        doc_dict["formato"] = existente["formato"]
        doc_dict["metadatos"]["plantilla_spa"] = True
        doc_dict["metadatos"]["modalidad_planeacion"] = existente["metadatos"]["modalidad_planeacion"]
        doc_dict["metadatos"]["vinculos_documentales"] = existente["metadatos"].get("vinculos_documentales", [])
        from services.curriculo import grados, opciones, vincular
        meta = doc_dict["metadatos"]
        meta.pop("curriculo", None)
        elegido = meta.get("spa_pda_id")
        if elegido:
            campo = meta.get("spa_campo_pda", "Lenguajes")
            if elegido not in {r["id"] for r in opciones(doc_dict, campo, grados(doc_dict))}:
                raise HTTPException(status_code=422, detail="PDA fuera del catálogo autorizado.")
            doc_dict = vincular(doc_dict, campo, [], [elegido])
    if doc_dict["metadatos"].get("modalidad_planeacion") != "grupal":
        doc_dict["metadatos"].pop("contexto_aulico", None)
        referencia = doc_dict["metadatos"].get("contexto_grupal_ref")
        if referencia:
            previa = existente.get("metadatos", {}) if existente else {}
            if referencia == previa.get("contexto_grupal_ref") and previa.get("contexto_grupal_vinculado"):
                exigir_planeacion(referencia["id"], user)
                doc_dict["metadatos"]["contexto_grupal_vinculado"] = previa["contexto_grupal_vinculado"]
            else:
                doc_dict["metadatos"]["contexto_grupal_vinculado"] = _perfil_grupal_vinculado(doc_dict, referencia, user)
        else:
            doc_dict["metadatos"].pop("contexto_grupal_vinculado", None)
    if not user.director and not _alumnos_en_planeacion(doc_dict) <= _alumnos_en_alcance(user):
        raise HTTPException(404, "Planeación no disponible.")
    return guardar_planeacion_transaccional(doc_dict, autor_cuenta=user.usuario, existente=existente is not None)


@app.delete("/api/planeaciones/{doc_id}")
def eliminar_planeacion_endpoint(doc_id: str, user: SessionUser = Depends(validar_token_sesion)):
    """Elimina una planeación tras confirmación explícita del docente."""
    doc = exigir_planeacion(doc_id, user)
    if doc.get("metadatos", {}).get("grupo_compartido"):
        raise HTTPException(409, "La guía anual conserva su historial y no se elimina desde Mis documentos.")
    ok = eliminar_planeacion_documento(doc_id, usuario_cuenta=user.usuario, es_director=user.director)
    if not ok:
        raise HTTPException(status_code=404, detail="No se encontró la planeación o no tiene permisos para eliminarla.")
    return {"status": "success", "mensaje": "Planeación eliminada correctamente."}


@app.get("/api/planeaciones/{doc_id}/pdf")
def descargar_planeacion_pdf(doc_id: str, user: SessionUser = Depends(validar_token_sesion)):
    """Genera la exportación oficial en PDF con los sellos y firmas de la Zona 001."""
    exigir_planeacion(doc_id, user)
    doc = obtener_planeacion_con_firmas(doc_id, usuario_cuenta=user.usuario)
    doc = adaptar_planeacion_para_pdf(doc)
    try:
        pdf_bytes = generar_pdf_planeacion(doc, actor_impresion={"cuenta": user.usuario, "area": user.area,
                                                                "director": user.director})
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generando el PDF de planeación."
        ) from exc
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="Planeacion_{doc_id}.pdf"'}
    )

# -------------------------------------------------------------
# 6. ANEXOS III, IV, V Y VII (BAP, SUGERENCIAS, EVENTOS, DERIVACIÓN)
# -------------------------------------------------------------

@app.get("/api/expedientes/{alumno_id}/adjuntos")
def listar_adjuntos(alumno_id: str, user: SessionUser = Depends(validar_token_sesion)):
    exigir_alumno(alumno_id, user)
    return adjuntos.listar(alumno_id)


@app.post("/api/expedientes/{alumno_id}/adjuntos")
async def guardar_adjunto(alumno_id: str, nombre: str, request: Request,
                          user: SessionUser = Depends(validar_token_sesion)):
    from starlette.concurrency import run_in_threadpool
    await run_in_threadpool(exigir_alumno, alumno_id, user)
    if request.headers.get("content-type", "").split(";")[0] != "application/pdf":
        raise HTTPException(415, "Se admite únicamente application/pdf.")
    cuerpo = bytearray()
    async for fragmento in request.stream():
        if len(cuerpo) + len(fragmento) > adjuntos.LIMITE_BYTES:
            raise HTTPException(413, "El PDF excede 5 MiB.")
        cuerpo.extend(fragmento)
    return await run_in_threadpool(adjuntos.guardar, alumno_id, nombre, user.usuario, bytes(cuerpo))


@app.get("/api/expedientes/{alumno_id}/adjuntos/{adjunto_id}")
def descargar_adjunto(alumno_id: str, adjunto_id: str, user: SessionUser = Depends(validar_token_sesion)):
    from urllib.parse import quote
    exigir_alumno(alumno_id, user)
    nombre, contenido = adjuntos.descargar(alumno_id, adjunto_id)
    return Response(contenido, media_type="application/octet-stream",
                    headers={"Content-Disposition": "attachment; filename*=UTF-8''" + quote(nombre),
                             "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})


class CambiosAnexo(BaseModel):
    campos: dict[str, str]
    revision: str | None = None


@app.get("/api/expedientes/{alumno_id}/anexos/{numero:int}")
def listar_anexos(alumno_id: str, numero: Literal[3, 4, 5], user: SessionUser = Depends(validar_token_sesion)):
    return anexos_expediente.listar(numero, exigir_alumno(alumno_id, user), user)


@app.post("/api/expedientes/{alumno_id}/anexos/{numero:int}")
def crear_anexo(alumno_id: str, numero: Literal[3, 4, 5], payload: CambiosAnexo,
                user: SessionUser = Depends(validar_token_sesion)):
    return anexos_expediente.guardar(numero, exigir_alumno(alumno_id, user), user, payload.campos)


@app.put("/api/expedientes/{alumno_id}/anexos/{numero:int}/{anexo_id}")
def modificar_anexo(alumno_id: str, numero: Literal[3, 4, 5], anexo_id: str, payload: CambiosAnexo,
                    user: SessionUser = Depends(validar_token_sesion)):
    return anexos_expediente.guardar(numero, exigir_alumno(alumno_id, user), user, payload.campos,
                                    id_doc=anexo_id, revision=payload.revision)


@app.get("/api/expedientes/{alumno_id}/anexos/{numero:int}/{anexo_id}/historial")
def historial_anexo(alumno_id: str, numero: Literal[3, 4, 5], anexo_id: str,
                    user: SessionUser = Depends(validar_token_sesion)):
    return anexos_expediente.historial(numero, exigir_alumno(alumno_id, user), anexo_id)


@app.get("/api/expedientes/{alumno_id}/anexos/{numero:int}/pdf")
def exportar_anexo(alumno_id: str, numero: Literal[3, 4, 5], registro: str | None = None,
                   user: SessionUser = Depends(validar_token_sesion)):
    pdf = anexos_expediente.exportar(numero, exigir_alumno(alumno_id, user), [registro] if registro else None)
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="Anexo-{numero}.pdf"'})


@app.post("/api/anexo3")
def crear_anexo3(payload: Anexo3Payload, user: SessionUser = Depends(validar_token_sesion)):
    alumno = exigir_alumno(payload.id_alumno, user)
    campos = payload.model_dump(include=set(anexos_expediente.CAMPOS[3]))
    return {"status": "success", **anexos_expediente.guardar(3, alumno, user, campos)}


@app.post("/api/anexo4")
def crear_anexo4(payload: Anexo4Payload, user: SessionUser = Depends(validar_token_sesion)):
    alumno = exigir_alumno(payload.id_alumno, user)
    campos = payload.model_dump(include=set(anexos_expediente.CAMPOS[4]))
    return {"status": "success", **anexos_expediente.guardar(4, alumno, user, campos)}


@app.post("/api/anexo5")
def crear_anexo5(payload: Anexo5Payload, user: SessionUser = Depends(validar_token_sesion)):
    alumno = exigir_alumno(payload.id_alumno, user)
    campos = payload.model_dump(include=set(anexos_expediente.CAMPOS[5]))
    return {"status": "success", **anexos_expediente.guardar(5, alumno, user, campos)}


# -------------------------------------------------------------
# 7. ACTAS DE VISITA Y OFICIOS DE COMISIÓN
# -------------------------------------------------------------


from piloto_spa.backend import relatorias_spa


@app.get("/api/relatorias")
def listar_relatorias(user: SessionUser = Depends(validar_token_sesion)):
    exigir_direccion(user)
    return relatorias_spa.listar()


@app.post("/api/relatorias")
def crear_relatoria(payload: relatorias_spa.CapturaRelatoria, user: SessionUser = Depends(validar_token_sesion)):
    exigir_direccion(user)
    return relatorias_spa.guardar(payload, user)


@app.get("/api/relatorias/{ident}")
def consultar_relatoria(ident: str, user: SessionUser = Depends(validar_token_sesion)):
    exigir_direccion(user)
    return relatorias_spa.obtener(ident)


@app.put("/api/relatorias/{ident}")
def editar_relatoria(ident: str, payload: relatorias_spa.CapturaRelatoria, user: SessionUser = Depends(validar_token_sesion)):
    exigir_direccion(user)
    return relatorias_spa.guardar(payload, user, ident)


@app.get("/api/relatorias/{ident}/historial")
def historial_relatoria(ident: str, user: SessionUser = Depends(validar_token_sesion)):
    exigir_direccion(user)
    return relatorias_spa.historial(ident)


@app.get("/api/relatorias/{ident}/pdf")
def pdf_relatoria(ident: str, user: SessionUser = Depends(validar_token_sesion)):
    exigir_direccion(user)
    return Response(relatorias_spa.pdf(ident), media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="Relatoria-USAER.pdf"'})



@app.get("/api/visitas")
def listar_visitas(escuela: Optional[str] = None, user: SessionUser = Depends(validar_token_sesion)):
    """Consulta actas de visitas de acompañamiento técnico."""
    if user.director:
        return [r for r in obtener_visitas_documentos(escuela) if r.get("Tipo_Acta") != "RELATORIA-SPA"]
    from data.database import RegistroVisita, get_session
    import json
    permitidos = _alumnos_en_alcance(user)
    with get_session() as db:
        candidatos = db.query(RegistroVisita).filter(
            RegistroVisita.evidencia.contains(json.dumps(user.id_usuario, ensure_ascii=False), autoescape=True)
        ).order_by(RegistroVisita.fecha.desc(), RegistroVisita.id)
        resultado = []
        for row in candidatos:
            datos = datos_acta(row)
            try:
                _acta_autorizada(row, user)
            except HTTPException:
                continue
            if datos["alumno_id"] in permitidos and (not escuela or escuela == row.escuela):
                resultado.append({"ID_Visita": row.id, "Fecha": row.fecha, "Escuela": row.escuela,
                                  "Personal": row.personal, "Motivo": row.motivo, "Observaciones": row.observaciones})
        return resultado


def datos_acta(row):
    import json
    try:
        extras = json.loads(row.evidencia or "{}")
        if not isinstance(extras, dict):
            extras = {}
    except ValueError:
        extras = {}
    return {campo: getattr(row, campo) or "" for campo in (
        "fecha", "escuela", "personal", "motivo", "observaciones", "tipo_acta", "lugar"
    )} | {campo: extras.get(campo, "") for campo in ("acuerdos", "seguimiento", "responsable", "alumno_id")}



def _acta_autorizada(row, user):
    if row.tipo_acta == "RELATORIA-SPA":
        raise HTTPException(404, "Utiliza el módulo de relatorías.")
    if user.director:
        return
    import json
    try:
        extras = json.loads(row.evidencia or "{}")
    except (TypeError, ValueError):
        extras = {}
    if not isinstance(extras, dict) or extras.get("autor_id") != user.id_usuario or not extras.get("alumno_id"):
        raise HTTPException(404, "Acta no disponible.")
    exigir_alumno(extras["alumno_id"], user)



def _actas_vinculadas(alumno_id, user, *, limite=None):
    from data.database import RegistroVisita, get_session

    # La evidencia histórica admite texto libre. Filtrar candidatos antes de interpretar JSON.
    with get_session() as db:
        candidatos = (db.query(RegistroVisita)
                      .filter(RegistroVisita.evidencia.contains(alumno_id, autoescape=True))
                      .order_by(RegistroVisita.fecha.desc(), RegistroVisita.id))
        actas = []
        for row in candidatos:
            try:
                _acta_autorizada(row, user)
            except HTTPException:
                continue
            datos = datos_acta(row)
            if datos["alumno_id"] == alumno_id:
                actas.append({"id": row.id, **datos})
                if limite and len(actas) == limite:
                    break
        return actas


def revision_acta(db, acta_id):
    from data.database import CambioSPA
    cambio = db.query(CambioSPA).filter_by(tipo="acta", documento_id=acta_id).order_by(
        CambioSPA.fecha.desc(), CambioSPA.id.desc()).first()
    return cambio.revision if cambio else ""


def persistir_acta(payload, user, acta_id=None):
    import json
    from data.database import RegistroVisita, get_session
    from data.sql_repository import _registrar_cambio_spa
    from datetime import date

    if not user.director and not payload.alumno_id:
        raise HTTPException(422, "Vincula el acta a un alumno autorizado.")
    if payload.alumno_id:
        exigir_alumno(payload.alumno_id, user)
    try:
        fecha = date.fromisoformat(payload.fecha).isoformat() if payload.fecha else date.today().isoformat()
    except ValueError as exc:
        raise HTTPException(422, "Indica una fecha válida.") from exc
    campos = {k: getattr(payload, k).strip() for k in
              ("escuela", "personal", "motivo", "observaciones", "tipo_acta", "lugar")}
    if campos["tipo_acta"] == "RELATORIA-SPA":
        raise HTTPException(422, "Utiliza el módulo institucional de relatorías.")
    limites = {"escuela": 255, "personal": 255, "motivo": 12000, "observaciones": 12000,
               "tipo_acta": 64, "lugar": 255}
    if any(len(valor) > limites[k] for k, valor in campos.items()):
        raise HTTPException(422, "Un campo del acta supera su longitud máxima.")
    campos.update(fecha=fecha, personal=campos["personal"] or user.nombre)
    with get_session() as db:
        if acta_id:
            row = db.query(RegistroVisita).filter_by(id=acta_id).with_for_update().one_or_none()
            if row is None:
                raise HTTPException(404, "Acta no disponible.")
            _acta_autorizada(row, user)
            if not user.director and payload.alumno_id != datos_acta(row)["alumno_id"]:
                raise HTTPException(403, "El acta conserva su expediente de origen.")
            anterior = revision_acta(db, acta_id)
            if payload.revision != anterior:
                raise HTTPException(409, "El acta cambió. Consulta la revisión vigente.")
            evidencia = row.evidencia or ""
            try:
                extras = json.loads(evidencia) if evidencia else {}
            except ValueError:
                extras = None
            if not isinstance(extras, dict):
                extras = {"evidencia_original": evidencia}
        else:
            acta_id = "acta-" + uuid.uuid4().hex
            row = RegistroVisita(id=acta_id, estatus="GUARDADA")
            db.add(row)
            anterior, extras = "", {"autor_id": user.id_usuario}
        if "alumno_id" in payload.model_fields_set:
            extras["alumno_id"] = payload.alumno_id or ""
        if extras.get("alumno_id"):
            alumno = exigir_alumno(extras["alumno_id"], user)
            campos["escuela"] = alumno["escuela"] or alumno["id_escuela"]
        extras.update({k: getattr(payload, k).strip() for k in ("acuerdos", "seguimiento", "responsable")})
        for k, valor in campos.items():
            setattr(row, k, valor)
        row.evidencia = json.dumps(extras, ensure_ascii=False)
        revision = uuid.uuid4().hex
        _registrar_cambio_spa(db, "acta", acta_id, {"revision": revision, **datos_acta(row)}, user.usuario, anterior or None)
        db.commit()
    return {"id": acta_id, "revision": revision}


@app.post("/api/visitas")
def crear_visita(payload: VisitaPayload, user: SessionUser = Depends(validar_token_sesion)):
    return {"status": "success", **persistir_acta(payload, user)}


@app.get("/api/visitas/{acta_id}")
def consultar_acta(acta_id: str, user: SessionUser = Depends(validar_token_sesion)):
    from data.database import RegistroVisita, get_session
    with get_session() as db:
        row = db.get(RegistroVisita, acta_id)
        if row is None:
            raise HTTPException(404, "Acta no disponible.")
        _acta_autorizada(row, user)
        return {"id": acta_id, "revision": revision_acta(db, acta_id), **datos_acta(row)}


@app.put("/api/visitas/{acta_id}")
def editar_acta(acta_id: str, payload: EdicionActa, user: SessionUser = Depends(validar_token_sesion)):
    return persistir_acta(payload, user, acta_id)


@app.get("/api/visitas/{acta_id}/historial")
def historial_acta(acta_id: str, user: SessionUser = Depends(validar_token_sesion)):
    consultar_acta(acta_id, user)
    return historial_spa_sql("acta", acta_id)


@app.get("/api/visitas/{acta_id}/pdf")
def exportar_acta(acta_id: str, user: SessionUser = Depends(validar_token_sesion)):
    from documents.visitas import visita_pdf
    acta = consultar_acta(acta_id, user)
    descripcion = "\n".join(
        f"{etiqueta}: {acta[k]}" for etiqueta, k in (
            ("Observaciones", "observaciones"), ("Acuerdos", "acuerdos"),
            ("Seguimiento", "seguimiento"), ("Responsable", "responsable")
        ) if acta[k]
    )
    pdf = visita_pdf(titulo=acta["tipo_acta"] or "Acta de visita", folio=acta_id, escuela=acta["escuela"],
                     lugar=acta["lugar"], fecha=acta["fecha"], ciclo="", especialidad="USAER 2E",
                     motivos=[acta["motivo"]] if acta["motivo"] else [], detalles="", descripcion=descripcion,
                     firmantes=[(acta["personal"], "Personal registrado")])
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="Acta-USAER.pdf"'})


@app.get("/api/tramites")
def listar_tramites(user: SessionUser = Depends(validar_token_sesion)):
    return tramites_spa.listar(user, exigir_alumno)


@app.post("/api/tramites")
def crear_tramite(payload: tramites_spa.Solicitud, user: SessionUser = Depends(validar_token_sesion)):
    return tramites_spa.crear(payload, user, exigir_alumno)


@app.get("/api/tramites/{ident}")
def consultar_tramite(ident: str, user: SessionUser = Depends(validar_token_sesion)):
    return tramites_spa.consultar(ident, user, exigir_alumno)


@app.put("/api/tramites/{ident}")
def actualizar_tramite(ident: str, payload: tramites_spa.Seguimiento, user: SessionUser = Depends(validar_token_sesion)):
    return tramites_spa.actualizar(ident, payload, user, exigir_alumno)


@app.post("/api/tramites/{ident}/respuesta")
def responder_tramite(ident: str, payload: tramites_spa.Respuesta, user: SessionUser = Depends(validar_token_sesion)):
    try:
        return tramites_spa.responder(ident, payload, user, exigir_alumno)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None


@app.get("/api/tramites/{ident}/historial")
def historial_tramite(ident: str, user: SessionUser = Depends(validar_token_sesion)):
    return tramites_spa.historial(ident, user, exigir_alumno)


@app.get("/api/tramites/{ident}/pdf")
def pdf_tramite(ident: str, user: SessionUser = Depends(validar_token_sesion)):
    from documents.tramites import generar_respuesta
    doc = tramites_spa.consultar(ident, user, exigir_alumno)
    if not doc.get("respuesta"):
        raise HTTPException(409, "Dirección debe preparar la respuesta y reservar su folio antes de exportar.")
    return Response(generar_respuesta(doc["respuesta"]), media_type="application/pdf",
                    headers={"Cache-Control":"no-store"})


@app.get("/api/tramites/{ident}/adjuntos")
def adjuntos_tramite(ident: str, user: SessionUser = Depends(validar_token_sesion)):
    return tramites_spa.adjuntos(ident, user, exigir_alumno)


@app.post("/api/tramites/{ident}/adjuntos")
async def adjuntar_tramite(ident: str, request: Request, tipo: str, nombre: str,
                          user: SessionUser = Depends(validar_token_sesion)):
    tramites_spa.gestion(user)
    tramites_spa.consultar(ident,user,exigir_alumno)
    contenido = bytearray()
    async for bloque in request.stream():
        contenido.extend(bloque)
        if len(contenido)>5*1024*1024:
            raise HTTPException(413, "Comprobante mayor de 5 MB.")
    return tramites_spa.adjuntar(ident,tipo,nombre,bytes(contenido),user,exigir_alumno)


@app.get("/api/tramites/{ident}/adjuntos/{aid}")
def descargar_adjunto_tramite(ident: str, aid: str, user: SessionUser = Depends(validar_token_sesion)):
    doc,contenido=tramites_spa.adjuntos(ident,user,exigir_alumno,aid)
    return Response(contenido,media_type=doc["mime"],headers={"Cache-Control":"no-store",
                     "Content-Disposition":"attachment", "X-Content-Type-Options":"nosniff"})


@app.get("/api/oficios")
def listar_oficios(escuela: Optional[str] = None, user: SessionUser = Depends(validar_token_sesion)):
    """Consulta oficios de comisión oficiales de la zona."""
    exigir_direccion(user)
    return [r for r in obtener_oficios_documentos(escuela)
            if not str(r.get("Clave_Operacion", "")).startswith("TRAMITE-EXPEDIENTE:")]


@app.post("/api/oficios")
def crear_oficio(payload: OficioPayload, user: SessionUser = Depends(validar_token_sesion)):
    from data.database import OficioComision, get_session
    from data.sql_repository import _registrar_cambio_spa, guardar_oficio_comision_sql

    exigir_direccion(user)
    datos = _campos_oficio(payload)
    with get_session() as db:
        db.execute(text("LOCK TABLE oficios_comision IN SHARE ROW EXCLUSIVE MODE"
                        if db.bind.dialect.name == "postgresql" else "BEGIN IMMEDIATE"))
        if payload.clave_operacion:
            existente = db.query(OficioComision).filter_by(clave_operacion=payload.clave_operacion).first()
            if existente:
                actual = _oficio_serializado(db, existente)
                if any(actual[k] != valor for k, valor in datos.items()):
                    raise HTTPException(409, "La clave corresponde a otro contenido.")
                return actual
        registro = {_OFICIO_SQL[k]: valor for k, valor in datos.items()}
        registro.update(Clave_Operacion=payload.clave_operacion, Estado="ACTIVO")
        creado = guardar_oficio_comision_sql(registro, sesion=db)
        row = db.get(OficioComision, creado["ID_Oficio"])
        resultado = {"id": row.id, "folio": row.folio, "revision": uuid.uuid4().hex, **datos}
        _registrar_cambio_spa(db, "oficio", row.id, resultado, user.usuario, None)
        db.commit()
        return resultado


_OFICIO_SQL = {
    "fecha_emision": "Fecha_Emision", "fecha_comision": "Fecha_Comision", "escuela": "Escuela",
    "id_escuela": "ID_Escuela", "maestra_apoyo": "Maestra_Apoyo", "director_escuela": "Director_Escuela",
    "asunto": "Asunto", "destino": "Destino", "horario": "Horario",
}


def _campos_oficio(payload):
    if payload.clave_operacion.startswith("TRAMITE-EXPEDIENTE:"):
        raise HTTPException(422, "Utiliza el módulo de trámites.")
    campos = {k: getattr(payload, k).strip() for k in _OFICIO_SQL}
    campos["fecha_emision"] = campos["fecha_emision"] or date.today().isoformat()
    for k in ("fecha_emision", "fecha_comision"):
        try:
            campos[k] = date.fromisoformat(campos[k]).isoformat()
        except ValueError:
            raise HTTPException(422, "Indica ambas fechas del oficio.") from None
    if any(not campos[k] for k in ("escuela", "maestra_apoyo", "asunto", "destino")):
        raise HTTPException(422, "Completa escuela, personal, asunto y destino.")
    for k, valor in campos.items():
        if len(valor) > (64 if k in {"horario", "id_escuela"} else 255) or any(ord(c) < 32 for c in valor):
            raise HTTPException(422, "Un campo del oficio contiene caracteres o longitud no admitidos.")
    if len(payload.clave_operacion) > 64:
        raise HTTPException(422, "Clave de operación demasiado extensa.")
    return campos


def _oficio_serializado(db, row):
    if (row.clave_operacion or "").startswith("TRAMITE-EXPEDIENTE:"):
        raise HTTPException(404, "Utiliza el módulo de trámites.")
    from data.database import CambioSPA
    revision = (db.query(CambioSPA.revision).filter_by(tipo="oficio", documento_id=row.id)
                .order_by(CambioSPA.fecha.desc(), CambioSPA.id.desc()).first())
    return {"id": row.id, "folio": row.folio or "", "revision": revision[0] if revision else "",
            **{k: getattr(row, k) or "" for k in _OFICIO_SQL}}


@app.get("/api/oficios/{oficio_id}")
def consultar_oficio(oficio_id: str, user: SessionUser = Depends(validar_token_sesion)):
    from data.database import OficioComision, get_session

    exigir_direccion(user)
    with get_session() as db:
        row = db.get(OficioComision, oficio_id)
        if not row:
            raise HTTPException(404, "Oficio no disponible.")
        return _oficio_serializado(db, row)


@app.put("/api/oficios/{oficio_id}")
def editar_oficio(oficio_id: str, payload: EdicionOficio, user: SessionUser = Depends(validar_token_sesion)):
    from data.database import OficioComision, get_session
    from data.sql_repository import _registrar_cambio_spa

    exigir_direccion(user)
    datos = _campos_oficio(payload)
    with get_session() as db:
        if db.bind.dialect.name == "sqlite":
            db.execute(text("BEGIN IMMEDIATE"))
        row = db.get(OficioComision, oficio_id, with_for_update=True)
        if not row:
            raise HTTPException(404, "Oficio no disponible.")
        anterior = _oficio_serializado(db, row)
        if anterior["revision"] != payload.revision:
            raise HTTPException(409, "El oficio cambió. Consulta la revisión actual.")
        for k, valor in datos.items():
            setattr(row, k, valor)
        resultado = {**anterior, **datos, "revision": uuid.uuid4().hex}
        _registrar_cambio_spa(db, "oficio", oficio_id, resultado, user.usuario, anterior["revision"] or None)
        db.commit()
        return resultado


@app.get("/api/oficios/{oficio_id}/historial")
def historial_oficio(oficio_id: str, user: SessionUser = Depends(validar_token_sesion)):
    consultar_oficio(oficio_id, user)
    return historial_spa_sql("oficio", oficio_id)


@app.get("/api/oficios/{oficio_id}/pdf")
def exportar_oficio(oficio_id: str, user: SessionUser = Depends(validar_token_sesion)):
    from documents.oficios import generar_oficio_comision
    from fpdf.errors import FPDFUnicodeEncodingException

    oficio = consultar_oficio(oficio_id, user)
    registro = {_OFICIO_SQL[k]: oficio[k] for k in _OFICIO_SQL}
    try:
        archivo = generar_oficio_comision({**registro, "Folio": oficio["folio"]}, incluir_firmas=False,
            para_revision=os.getenv("USAER_SPA_MODE") == "usaer-private-local")
    except (ValueError, FPDFUnicodeEncodingException):
        raise HTTPException(422, "Revisa los campos y caracteres del oficio antes de exportar.") from None
    return Response(archivo, media_type="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="Oficio-Comision.pdf"'})

# -------------------------------------------------------------
# 8. ASISTENTE PEDAGÓGICO CONVERSACIONAL E IA
# -------------------------------------------------------------

@app.post("/api/ai/chat")
def chat_asistente(payload: AIChatPayload, user: SessionUser = Depends(validar_token_sesion)):
    """Asistente conversacional con recuperación contextual del alumno y reglas Zona 001."""
    if payload.alumno_id:
        exigir_alumno(payload.alumno_id, user)
    if payload.planeacion_id:
        exigir_planeacion(payload.planeacion_id, user)
    return chat_asistente_pedagogico(
        mensaje_docente=payload.mensaje,
        alumno_id=payload.alumno_id,
        planeacion_id=payload.planeacion_id
    )


@app.post("/api/ai/sugerencias")
def sugerencias_asistente(payload: AISugerenciaPayload, user: SessionUser = Depends(validar_token_sesion)):
    """Generación directa de ajustes razonables y descriptores observables."""
    from ai.sugerencia_local import fallback as ai_fallback
    return {**ai_fallback(), "origen": "ejemplo_local"}


# -------------------------------------------------------------
# INFORMES EDUCATIVOS: CRUD, AUTORÍA, HISTORIAL Y PDF
# -------------------------------------------------------------

CAMPOS_INFORME = ("antecedentes", "avances", "dificultades", "intervenciones", "recomendaciones")


class InformeEducativoPayload(BaseModel):
    alumno_id: str = Field(min_length=1, max_length=64)
    ciclo: str = Field(pattern=r"^\d{4}-\d{4}$")
    tipo: Literal["seguimiento", "evaluacion", "intervencion", "otro"] = "seguimiento"
    titulo: str = Field(min_length=1, max_length=255, pattern=r"\S")
    antecedentes: str = Field(default="", max_length=20000)
    avances: str = Field(default="", max_length=20000)
    dificultades: str = Field(default="", max_length=20000)
    intervenciones: str = Field(default="", max_length=20000)
    recomendaciones: str = Field(default="", max_length=20000)
    revision: Optional[str] = Field(default=None, max_length=64)


def _informe_autorizado(db, informe_id, user, *, bloqueo=False):
    from data.database import InformeEducativoSPA
    row = db.get(InformeEducativoSPA, informe_id, with_for_update=bloqueo)
    if row is None:
        raise HTTPException(404, "Informe no disponible.")
    alumno = exigir_alumno(row.id_alumno, user)
    if not user.director and (row.id_autor != user.id_usuario or row.id_escuela != alumno["id_escuela"]):
        raise HTTPException(404, "Informe no disponible.")
    return row


def _serializar_informe(row):
    import json
    contenido = json.loads(row.contenido_json or "{}")
    return {"id": row.id, "alumno_id": row.id_alumno, "ciclo": row.ciclo,
            "tipo": row.tipo, "titulo": row.titulo, "autor": row.autor,
            "revision": row.revision, "actualizado_en": row.actualizado_en.isoformat() if row.actualizado_en else "",
            **contenido}


def _listar_informes_autorizados(alumno, user, *, limite=None):
    from data.database import InformeEducativoSPA, get_session
    with get_session() as db:
        query = db.query(InformeEducativoSPA).filter_by(id_alumno=alumno["id"])
        if not user.director:
            query = query.filter_by(id_autor=user.id_usuario, id_escuela=alumno["id_escuela"])
        return [_serializar_informe(r) for r in query.order_by(InformeEducativoSPA.actualizado_en.desc()).limit(limite)]


@app.get("/api/informes")
def listar_informes(alumno_id: str, user: SessionUser = Depends(validar_token_sesion)):
    return _listar_informes_autorizados(exigir_alumno(alumno_id, user), user)


@app.post("/api/informes", status_code=201)
def crear_informe(payload: InformeEducativoPayload, user: SessionUser = Depends(validar_token_sesion)):
    import json
    from data.database import InformeEducativoSPA, get_session
    from data.sql_repository import _registrar_cambio_spa
    alumno = exigir_alumno(payload.alumno_id, user)
    campos = payload.model_dump(include=set(CAMPOS_INFORME))
    doc_id, rev = uuid.uuid4().hex, uuid.uuid4().hex
    with get_session() as db:
        row = InformeEducativoSPA(id=doc_id, id_alumno=payload.alumno_id,
              id_escuela=alumno["id_escuela"], ciclo=payload.ciclo, tipo=payload.tipo,
              titulo=payload.titulo.strip(), contenido_json=json.dumps(campos, ensure_ascii=False),
              autor=user.usuario, id_autor=user.id_usuario, revision=rev)
        db.add(row)
        _registrar_cambio_spa(db, "informe", doc_id, _serializar_informe(row), user.usuario, None)
        db.commit()
    return {"id": doc_id, "revision": rev}


@app.get("/api/informes/{informe_id}")
def obtener_informe(informe_id: str, user: SessionUser = Depends(validar_token_sesion)):
    from data.database import get_session
    with get_session() as db:
        return _serializar_informe(_informe_autorizado(db, informe_id, user))


@app.put("/api/informes/{informe_id}")
def editar_informe(informe_id: str, payload: InformeEducativoPayload,
                   user: SessionUser = Depends(validar_token_sesion)):
    import json
    from data.database import get_session
    from data.sql_repository import _registrar_cambio_spa
    with get_session() as db:
        row = _informe_autorizado(db, informe_id, user, bloqueo=True)
        if row.id_alumno != payload.alumno_id or row.ciclo != payload.ciclo:
            raise HTTPException(422, "No se puede reasignar el informe a otro alumno o ciclo.")
        if payload.revision != row.revision:
            raise HTTPException(409, "Informe modificado en otra sesión; consulta la revisión actual.")
        anterior = row.revision
        row.titulo = payload.titulo.strip()
        row.tipo = payload.tipo
        row.contenido_json = json.dumps(payload.model_dump(include=set(CAMPOS_INFORME)), ensure_ascii=False)
        row.revision = uuid.uuid4().hex
        _registrar_cambio_spa(db, "informe", informe_id, _serializar_informe(row), user.usuario, anterior)
        db.commit()
        return {"id": informe_id, "revision": row.revision}


@app.get("/api/informes/{informe_id}/historial")
def historial_informe(informe_id: str, user: SessionUser = Depends(validar_token_sesion)):
    obtener_informe(informe_id, user)
    return historial_spa_sql("informe", informe_id)


@app.get("/api/informes/{informe_id}/pdf")
def exportar_informe(informe_id: str, user: SessionUser = Depends(validar_token_sesion)):
    from io import BytesIO
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from xml.sax.saxutils import escape
    from reportlab.lib.pagesizes import A4
    inf = obtener_informe(informe_id, user)
    alumno = exigir_alumno(inf["alumno_id"], user)
    styles = getSampleStyleSheet()
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, title="Informe educativo USAER 2E")
    flow = [Paragraph("USAER 2E — Informe educativo", styles["Heading1"]),
            Paragraph(escape(inf["titulo"]), styles["Heading2"]),
            Paragraph("Alumno: " + escape(alumno["nombre_completo"]), styles["Normal"]),
            Paragraph("Ciclo: " + escape(inf["ciclo"]), styles["Normal"]), Spacer(1, 14)]
    for key, label in (("antecedentes", "Antecedentes"), ("avances", "Avances"),
                       ("dificultades", "Dificultades"), ("intervenciones", "Intervenciones"),
                       ("recomendaciones", "Recomendaciones")):
        flow.append(Paragraph(label, styles["Heading3"]))
        for paragraph in (inf.get(key) or "Sin registro").split("\n"):
            flow.append(Paragraph(escape(paragraph) or " ", styles["Normal"]))
        flow.append(Spacer(1, 10))
    doc.build(flow)
    return Response(buffer.getvalue(), media_type="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="Informe-USAER-2E.pdf"'})


# -------------------------------------------------------------
# 9. ESTADÍSTICAS INSTITUCIONALES ZONA 001
# -------------------------------------------------------------

@app.get("/api/estadisticas/zona")
def estadisticas_zona(user: SessionUser = Depends(validar_token_sesion)):
    """Métricas globales de la zona escolar para el panel directivo."""
    exigir_direccion(user)
    return obtener_estadisticas_zona()


def _padron_en_alcance_estadistico(user, escuela):
    if escuela and not user.director and escuela not in user.escuelas_permitidas:
        raise HTTPException(404, "Escuela no disponible.")
    alumnos = alumnos_sql().drop_duplicates("ID_Alumno")
    if not user.director:
        alumnos = alumnos[alumnos["ID_Alumno"].isin(_alumnos_en_alcance(user))]
    if escuela:
        alumnos = alumnos[alumnos["ID_Escuela"].eq(escuela)]
    return alumnos


@app.get("/api/estadisticas/epp-ciclos")
def comparar_epp_ciclos(ciclos: str, escuela: str = "", user: SessionUser = Depends(validar_token_sesion)):
    """Compara cobertura documental de la cohorte activa actual por ciclo."""
    from data.sql_repository import cobertura_epp_sql
    from utils.text import normalizar_texto

    solicitados = ciclos.split(",")
    if not 2 <= len(solicitados) <= 5 or len(set(solicitados)) != len(solicitados):
        raise HTTPException(422, "Indica de dos a cinco ciclos distintos separados por comas.")
    for ciclo in solicitados:
        ciclo_epp(ciclo)
    alumnos = _padron_en_alcance_estadistico(user, escuela)
    ids = alumnos.loc[alumnos["Estatus"].map(normalizar_texto).eq("ACTIVO"), "ID_Alumno"].tolist()
    epp = cobertura_epp_sql(ids, solicitados)
    return {"cohorte": "padron_activo_actual", "alumnos_activos": len(ids), "ciclos": [
        {"ciclo": ciclo, "alumnos_con_epp": epp.get(ciclo, 0),
         "porcentaje": round(100 * epp.get(ciclo, 0) / len(ids), 1) if ids else None}
        for ciclo in solicitados
    ]}


@app.get("/api/estadisticas/padron")
def estadisticas_padron(escuela: str = "", incluir_bajas: bool = False,
                       ciclo: str = "2026-2027", user: SessionUser = Depends(validar_token_sesion)):
    from utils.text import normalizar_texto

    ciclo_epp(ciclo)
    alumnos = _padron_en_alcance_estadistico(user, escuela)
    activos = alumnos["Estatus"].map(normalizar_texto).eq("ACTIVO")
    ids_activos = alumnos.loc[activos, "ID_Alumno"].tolist()
    if not incluir_bajas:
        alumnos = alumnos[~alumnos["Estatus"].map(normalizar_texto).isin(
            {"BAJA", "INACTIVO", "RETIRADO", "ELIMINADO"})]
    epp = {doc["alumno"] for doc in epp_listar_sql(ids_activos) if doc["ciclo"] == ciclo}
    sexo = alumnos["Sexo"].map(normalizar_texto)
    hombres = int(sexo.isin({"H", "HOMBRE", "MASCULINO"}).sum())
    mujeres = int(sexo.isin({"M", "MUJER", "FEMENINO", "F"}).sum())
    edades = pd.to_numeric(alumnos["Edad_1_Septiembre"], errors="coerce").dropna()
    edades = edades[edades.between(0, 100)]
    opciones = [e for e in obtener_catalogo_escuelas() if user.director or e["id"] in user.escuelas_permitidas]
    nombres = {e["id"]: e["nombre"] for e in opciones}
    por_escuela = (alumnos["ID_Escuela"].map(nombres).fillna(alumnos["Nombre_Escuela"])
                   .replace("", "Sin escuela").value_counts().to_dict())
    return {
        "total_alumnos": len(alumnos), "alumnos_activos": len(ids_activos),
        "total_escuelas": len(por_escuela), "escuelas": opciones, "ciclo_activo": ciclo,
        "cumplimiento_epp": f"{100 * len(epp) / len(ids_activos):.1f}%" if ids_activos else "—",
        "distribucion_condicion": alumnos["Condicion_Discapacidad"].replace("", "Sin dato").value_counts().to_dict(),
        "distribucion_escuela": por_escuela,
        "sexo": {"hombres": hombres, "mujeres": mujeres, "sin_dato": len(alumnos) - hombres - mujeres},
        "edad": {"media": round(float(edades.mean()), 1), "minima": float(edades.min()), "maxima": float(edades.max())}
        if not edades.empty else None,
    }

# -------------------------------------------------------------
# 10. SERVIR FRONTEND SPA ESTÁTICO DIRECTO
# -------------------------------------------------------------

SPA_STATIC_DIR = Path(__file__).resolve().parents[1] / "frontend" / "dist"
INDEX_HTML = SPA_STATIC_DIR / "index.html"
app.mount("/assets", StaticFiles(directory=SPA_STATIC_DIR, check_dir=False), name="assets")

@app.get("/", response_class=HTMLResponse)
def index_spa():
    """Punto de entrada de la SPA React 18."""
    if INDEX_HTML.exists():
        return HTMLResponse(content=INDEX_HTML.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>USAER 2E 2.0</h1><p>Compilando frontend...</p>")

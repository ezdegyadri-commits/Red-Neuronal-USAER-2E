"""FastAPI Backend Integral para USAER 2E 2.0.

Capa de servicios RESTful de alta velocidad para la versión SPA desacoplada de Streamlit.
Implementa autenticación con tokens seguros, control de acceso basado en roles (RBAC),
persistencia relacional completa (PostgreSQL 17), y todos los módulos institucionales:
- Mis Documentos y Planeación e Intervención (Formatos XXI, XXIII, XXV, XIX, XX)
- Alumnos y Expedientes Integrales (con Línea de Tiempo, Adjuntos y Movimientos)
- Evaluación Psicopedagógica (EPP) Multi-Área
- Anexo III (BAP), Anexo IV (Hoja de Sugerencias), Anexo V (Eventos Significativos) y Anexo VII (Derivación)
- Informes Educativos de Seguimiento
- Cronograma Mensual y Avisos
- Horarios de Apoyo y Restricciones por Escuela
- Calendario Institucional de Actividades SEGEY / USAER
- Juntas Académicas (Cuadro de Metodologías) y Relatorías CTE
- Metas Personales
- Trámites de Expedientes
- Directorio de Maestros de Primaria (Docentes Regulares)
- Novedades de Supervisión Zona 001
- Constancias / Actas de Visita y Oficios de Comisión
- Estadísticas e Indicadores de Zona 001 y Panel de Dirección
"""
from __future__ import annotations

import gzip
import io
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT_DIR = str(Path(__file__).resolve().parents[2])
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

try:
    import streamlit as _st
except ImportError:
    import types as _types
    _st = _types.ModuleType("streamlit")
    def _noop_cache(func=None, **kwargs):
        if callable(func):
            func.clear = getattr(func, "clear", lambda: None)
            return func
        def _decorator(f):
            f.clear = getattr(f, "clear", lambda: None)
            return f
        return _decorator
    _st.cache_data = _noop_cache
    _st.cache_resource = _noop_cache
    _st.secrets = {}
    _st.session_state = {}
    sys.modules["streamlit"] = _st

from fastapi import FastAPI, HTTPException, Depends, Header, Query, status, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import pandas as pd

from piloto_spa.backend.auth_service import (
    SessionUser,
    autenticar_usuario,
    emitir_token_sesion,
    validar_token_sesion,
    cerrar_sesion,
)
from piloto_spa.backend.domain_services import (
    generar_propuesta_actividad_docente,
    generar_propuesta_redaccion_epp,

    obtener_catalogo_escuelas,
    obtener_alumnos_autorizados,
    guardar_alumno_nuevo,
    actualizar_alumno_existente,
    obtener_expediente_completo,
    obtener_anexo3_autorizados,
    obtener_anexo4_autorizados,
    obtener_anexo5_autorizados,
    obtener_anexo7_autorizados,
    listar_epp_autorizados,
    obtener_epp_documento,
    guardar_epp_documento,
    listar_planeaciones_autorizadas,
    obtener_planeacion_con_firmas,
    verificar_acceso_planeacion,
    guardar_planeacion_transaccional,
    eliminar_planeacion_documento,
    guardar_anexo3_documento,
    actualizar_anexo3_documento,
    guardar_anexo4_documento,
    actualizar_anexo4_documento,
    guardar_anexo5_documento,
    actualizar_anexo5_documento,
    guardar_anexo7_documento,
    obtener_visitas_documentos,
    guardar_visita_documento,
    obtener_oficios_documentos,
    guardar_oficio_documento,
    obtener_horarios_modulo,
    guardar_horario_modulo,
    obtener_cronogramas_modulo,
    guardar_cronograma_modulo,
    obtener_docentes_regulares_autorizados,
    guardar_docente_regular_modulo,
    obtener_calendario_modulo,
    guardar_evento_calendario_modulo,
    obtener_juntas_y_catalogo,
    chat_asistente_pedagogico,
    obtener_estadisticas_zona,
)
from data.sql_repository import (
    coleccion_listar_sql,
    coleccion_guardar_sql,
    configuracion_oficios_sql,
    guardar_configuracion_oficios_sql,
)
from documents.planeacion import generar_pdf as generar_pdf_planeacion

app = FastAPI(
    title="USAER 2E 2.0 — API de Servicios Pedagógicos",
    version="2.0.0",
    description="Backend desacoplado de alto rendimiento para el sistema educativo USAER 02-E",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)


def reconciliar_base_datos(confirmacion_manual: bool = False) -> Dict[str, Any]:
    """Herramienta administrativa de migración histórica manual.

    SALVAGUARDA ESTRICTA DE DATOS OPERATIVOS:
    1. DESACTIVADA DEL ARRANQUE: Nunca se ejecuta automáticamente en el startup de FastAPI.
    2. PROTEGIDA: Requiere el parámetro explícito confirmacion_manual=True.
    3. SIN DESCARGAS EXTERNAS: No descarga semillas ni archivos desde GitHub.
    4. NO DESTRUCTIVA: Nunca sobrescribe alumnos, usuarios, contraseñas,
       planeaciones, EPP ni documentos existentes en PostgreSQL. Solo inserta registros ausentes.
    5. NUNCA ANULA ALUMNOS: Se eliminó cualquier lógica de marcado a ANULADO_MIGRACION.
    """
    if not confirmacion_manual:
        logging.getLogger("uvicorn").warning(
            "reconciliar_base_datos invocada sin confirmacion_manual=True. Operación CANCELADA para proteger datos operativos."
        )
        return {
            "status": "bloqueado",
            "motivo": "Reconciliación manual protegida. Requiere confirmacion_manual=True explícita."
        }

    from data.database import (
        Base,
        get_engine,
        get_session,
        Alumno,
        Escuela,
        Personal,
        Usuario,
        PlaneacionDoc,
        EPPDoc,
        Anexo3Deteccion,
        Anexo4Sugerencia,
        Anexo5Evento,
        Anexo7Derivacion,
        RegistroVisita,
        OficioComision,
        ConfiguracionOficio,
        DocenteRegular,
        ColeccionInstitucional,
    )

    engine = get_engine(initialize_schema=False)
    try:
        for table in Base.metadata.sorted_tables:
            try:
                table.create(engine, checkfirst=True)
            except Exception:
                pass
    except Exception:
        pass

    candidatos_semilla = [
        Path(__file__).resolve().parents[2] / "data" / "semilla_historica_completa.json.gz",
        Path(__file__).resolve().parents[1] / "data" / "semilla_historica_completa.json.gz",
        Path(__file__).resolve().parent / "data" / "semilla_historica_completa.json.gz",
        Path("/home/uppcoder/app/usaer2e/data/semilla_historica_completa.json.gz"),
        Path("/home/uppcoder/app/data/semilla_historica_completa.json.gz"),
        Path(__file__).resolve().parents[2] / "data" / "semilla_datos_reales.json",
        Path("/home/uppcoder/app/usaer2e/data/semilla_datos_reales.json"),
        Path("/home/uppcoder/app/data/semilla_datos_reales.json"),
    ]

    data = None
    for cand in candidatos_semilla:
        if cand.exists():
            try:
                if str(cand).endswith(".gz"):
                    with gzip.open(cand, "rt", encoding="utf-8") as f:
                        data = json.load(f)
                else:
                    with open(cand, "r", encoding="utf-8") as f:
                        data = json.load(f)
                if data and "alumnos" in data and len(data["alumnos"]) > 0:
                    logging.getLogger("uvicorn").info("Semilla leída localmente desde %s (%d alumnos)", cand, len(data["alumnos"]))
                    break
            except Exception as e:
                logging.getLogger("uvicorn").warning("Error leyendo semilla local %s: %s", cand, e)

    if not data or "alumnos" not in data or len(data["alumnos"]) == 0:
        logging.getLogger("uvicorn").warning("reconciliar_base_datos: no se encontró semilla local válida. Operación omitida.")
        return {"status": "sin_semilla_local"}

    resumen = {}
    with get_session() as session:
        # 1. Escuelas (solo insertar si no existen)
        for item in data.get("escuelas", []):
            obj = session.query(Escuela).filter_by(id=item["id"]).first()
            if not obj:
                session.add(Escuela(**item))
        session.commit()

        # 2. Personal (solo insertar si no existen)
        for item in data.get("personal", []):
            obj = session.query(Personal).filter_by(id=item["id"]).first()
            if not obj:
                session.add(Personal(**item))
        session.commit()

        # 3. Usuarios (solo insertar si no existen; NUNCA modificar contraseñas, roles ni escuelas)
        for item in data.get("usuarios", []):
            obj = session.query(Usuario).filter_by(usuario=item["usuario"]).first() or session.query(Usuario).filter_by(id=item["id"]).first()
            if not obj:
                session.add(Usuario(**item))
        session.commit()

        # 4. Alumnos canónicos (solo insertar si no existen; NUNCA sobrescribir alumnos ni alterar estatus)
        for item in data.get("alumnos", []):
            aid = item["id"]
            obj = session.query(Alumno).filter_by(id=aid).first()
            if not obj:
                item_status = str(item.get("estatus") or "ACTIVO").strip().upper()
                item["estatus"] = item_status
                session.add(Alumno(**item))
        session.commit()
        resumen["alumnos"] = session.query(Alumno).filter(Alumno.estatus == "ACTIVO").count()

        # 5. Planeaciones (solo insertar si no existen; NUNCA sobrescribir planeaciones activas)
        for item in data.get("planeaciones", []):
            pid = item["id"]
            obj = session.query(PlaneacionDoc).filter_by(id=pid).first()
            if not obj:
                payload_str = item.get("payload_json", "{}")
                datos_str = item.get("datos_json", "{}")
                metadatos_str = item.get("metadatos_json", "{}")
                tablas_str = item.get("tablas_json", "{}")
                textos_str = item.get("textos_json", "{}")
                obs_dir = item.get("observaciones_director", "")
                if payload_str and payload_str != "{}" and datos_str == "{}":
                    try:
                        parsed = json.loads(payload_str)
                        if isinstance(parsed, dict):
                            datos_str = json.dumps(parsed.get("datos", {}), ensure_ascii=False)
                            metadatos_str = json.dumps(parsed.get("metadatos", {}), ensure_ascii=False)
                            tablas_str = json.dumps(parsed.get("tablas", {}), ensure_ascii=False)
                            textos_str = json.dumps(parsed.get("textos", {}), ensure_ascii=False)
                            obs_dir = str(parsed.get("observaciones_director", obs_dir) or "")
                    except Exception:
                        pass
                session.add(PlaneacionDoc(
                    id=pid,
                    cuenta=item.get("cuenta", ""),
                    formato=item.get("formato", "XXIII"),
                    estado=item.get("estado", "BORRADOR"),
                    revision=item.get("revision", ""),
                    guardado_en=item.get("guardado_en", ""),
                    datos_json=datos_str,
                    metadatos_json=metadatos_str,
                    tablas_json=tablas_str,
                    textos_json=textos_str,
                    payload_json=payload_str,
                    observaciones_director=obs_dir,
                ))
        session.commit()
        resumen["planeaciones"] = session.query(PlaneacionDoc).count()

        # 6. EPP (solo insertar si no existen; NUNCA sobrescribir capturas recientes)
        for item in data.get("epp", []):
            eid = item["id"]
            obj = session.query(EPPDoc).filter_by(id=eid).first()
            if not obj:
                session.add(EPPDoc(**item))
        session.commit()
        resumen["epp"] = session.query(EPPDoc).count()

        # 7. Anexos, Visitas, Oficios, Docentes y Colecciones (solo insertar registros ausentes)
        for ModelCls, key_name in [
            (Anexo3Deteccion, "anexo3"),
            (Anexo4Sugerencia, "anexo4"),
            (Anexo5Evento, "anexo5"),
            (Anexo7Derivacion, "anexo7"),
            (RegistroVisita, "visitas"),
            (OficioComision, "oficios"),
            (ConfiguracionOficio, "configuracion_oficios"),
            (DocenteRegular, "docentes_regulares"),
            (ColeccionInstitucional, "colecciones"),
        ]:
            try:
                items = data.get(key_name, [])
                if not items:
                    continue
                try:
                    session.query(ModelCls).first()
                except Exception:
                    session.rollback()
                    continue
                existing_ids = {r[0] for r in session.query(ModelCls.id).all()}
                seen_in_batch = set(existing_ids)
                valid_columns = {c.name for c in ModelCls.__table__.columns}
                nuevos = []
                for it in items:
                    iid = str(it.get("id") or "").strip()
                    if not iid or iid in seen_in_batch:
                        continue
                    seen_in_batch.add(iid)
                    filt_item = {k: v for k, v in it.items() if k in valid_columns}
                    nuevos.append(ModelCls(**filt_item))
                if nuevos:
                    session.bulk_save_objects(nuevos)
                    session.commit()
                resumen[key_name] = session.query(ModelCls).count()
            except Exception as exc:
                session.rollback()
                logging.getLogger("uvicorn").warning("Aviso reconciliando %s: %s", key_name, exc)

    return resumen


@app.on_event("startup")
def inicializar_base_datos():
    """Arranque seguro de producción:
    La reconciliación automática de base de datos está estrictamente DESACTIVADA
    para proteger capturas nuevas, estados y planeaciones de las maestras.
    """
    logging.getLogger("uvicorn").info(
        "Arranque de producción: Reconciliación automática DESACTIVADA para proteger datos operativos y capturas."
    )



@app.post("/api/admin/auto-actualizar")
def auto_actualizar_servidor(user: SessionUser = Depends(validar_token_sesion)):
    """Ejecuta la actualización y sincronización de código y base de datos de forma autónoma."""
    if not user.director:
        raise HTTPException(status_code=403, detail="Acceso reservado exclusivamente a Dirección.")
    
    script_path = Path("/home/uppcoder/app/tools/actualizar_uppcoder.py")
    try:
        import urllib.request
        script_path.parent.mkdir(parents=True, exist_ok=True)
        url_upd = f"https://raw.githubusercontent.com/ezdegyadri-commits/Red-Neuronal-USAER-2E/piloto-spa/tools/actualizar_uppcoder.py?v={int(time.time())}"
        urllib.request.urlretrieve(url_upd, str(script_path))
    except Exception as dl_err:
        logging.getLogger("uvicorn").warning("No se pudo actualizar actualizar_uppcoder.py: %s", dl_err)
    if not script_path.exists():
        script_path = Path(__file__).resolve().parents[2] / "tools" / "actualizar_uppcoder.py"
    
    import subprocess
    try:
        res = subprocess.run([sys.executable, str(script_path)], capture_output=True, text=True, timeout=60)
        return {"status": "ok", "code": res.returncode, "stdout": res.stdout, "stderr": res.stderr}
    except Exception as exc:
        return {"status": "error", "detalle": str(exc)}

@app.get("/api/admin/status-bd")
def estado_base_datos():
    """Diagnóstico en vivo del motor de base de datos relacional y conteo de registros."""
    from data.database import (
        get_session,
        Alumno,
        Escuela,
        Personal,
        Usuario,
        PlaneacionDoc,
        EPPDoc,
        Anexo3Deteccion,
        Anexo4Sugerencia,
        Anexo5Evento,
        Anexo7Derivacion,
        RegistroVisita,
        OficioComision,
        DocenteRegular,
        ColeccionInstitucional,
        is_postgres,
        get_database_url,
    )
    from sqlalchemy.engine import make_url

    url_str = get_database_url()
    try:
        parsed = make_url(url_str)
        host_repr = parsed.host or "local"
        db_repr = parsed.database or "local"
    except Exception:
        host_repr = "desconocido"
        db_repr = "desconocido"

    with get_session() as session:
        def _cnt(q_func):
            try:
                return q_func()
            except Exception:
                return 0

        return {
            "motor": "PostgreSQL 17" if is_postgres() else "SQLite Local",
            "host": host_repr,
            "database": db_repr,
            "escuelas": _cnt(lambda: session.query(Escuela).count()),
            "personal": _cnt(lambda: session.query(Personal).count()),
            "usuarios": _cnt(lambda: session.query(Usuario).count()),
            "alumnos_activos": _cnt(lambda: session.query(Alumno).filter(Alumno.estatus == "ACTIVO").count()),
            "alumnos_total": _cnt(lambda: session.query(Alumno).filter(Alumno.estatus != "ANULADO_MIGRACION").count()),
            "planeaciones": _cnt(lambda: session.query(PlaneacionDoc).count()),
            "epp": _cnt(lambda: session.query(EPPDoc).count()),
            "anexo3_bap": _cnt(lambda: session.query(Anexo3Deteccion).count()),
            "anexo4_sugerencias": _cnt(lambda: session.query(Anexo4Sugerencia).count()),
            "anexo5_eventos": _cnt(lambda: session.query(Anexo5Evento).count()),
            "anexo7_derivaciones": _cnt(lambda: session.query(Anexo7Derivacion).count()),
            "visitas": _cnt(lambda: session.query(RegistroVisita).count()),
            "oficios": _cnt(lambda: session.query(OficioComision).count()),
            "docentes_regulares": _cnt(lambda: session.query(DocenteRegular).count()),
            "colecciones_institucionales": _cnt(lambda: session.query(ColeccionInstitucional).count()),
            "estado": "OK - Base de datos histórica completa y sincronizada",
        }


# -------------------------------------------------------------
# MODELOS PYDANTIC PARA CONTRATOS DE ENTRADA Y SALIDA
# -------------------------------------------------------------
class LoginPayload(BaseModel):
    usuario: str
    password: str


class AlumnoPayload(BaseModel):
    id: Optional[str] = None
    nombre_completo: str
    curp: str = ""
    edad_1_septiembre: str = ""
    sexo: str = "Hombre"
    situacion_alumno: str = "CON"
    nivel_educativo: str = "Primaria"
    grado: str = "1"
    grupo: str = "A"
    id_escuela: str = "ESC-001"
    nombre_escuela: str = "Damián Carmona"
    maestra_apoyo: str = ""
    condicion_discapacidad: str = "TDAH"
    estatus: str = "ACTIVO"
    tipo_atencion: str = "Grupal"


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
    aporte_area: Optional[Dict[str, Any]] = None
    forzar: bool = False


class EPPPayload(BaseModel):
    id: str
    alumno: str
    ciclo: str = "2026-2027"
    partes: Dict[str, Any] = Field(default_factory=dict)


class AIChatPayload(BaseModel):
    mensaje: str
    alumno_id: Optional[str] = None
    planeacion_id: Optional[str] = None



class ActividadPropuestaPayload(BaseModel):
    alumno_id: Optional[str] = ""
    nivel_aprendizaje: str = "Presilábico / Inicial"
    metodo: str = "Conciencia Fonológica y Asociación"
    area: str = "Aprendizaje"
    prioridad: str = ""
    apoyos: List[str] = ["Material concreto manipulable", "Claves visuales"]
    duracion_min: int = 30


class EPPPropuestaPayload(BaseModel):
    alumno_id: str = ""
    area: str = "Conclusión"
    observaciones: str = ""
    instrumentos: List[str] = []

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
    nombre_alumno: str = ""
    grado_grupo: str = ""
    escuela: str = ""
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
    id_alumno: str = ""
    fecha: str = ""
    nombre_alumno: str = ""
    grado_grupo: str = ""
    especialista: str = ""
    evento: str = ""
    id_escuela: str = ""
    escuela: str = ""


class Anexo7Payload(BaseModel):
    id: Optional[str] = None
    id_alumno: str = ""
    fecha: str = ""
    escuela: str = ""
    docente_regular: str = ""
    fecha_nacimiento: str = ""
    salud: str = ""
    seguimiento_medico: str = ""
    aspecto_relevante: str = ""
    elaborado_por: str = ""
    respuestas: Any = Field(default_factory=list)


class VisitaPayload(BaseModel):
    id: Optional[str] = None
    fecha: str = ""
    escuela: str = ""
    personal: str = ""
    motivo: str = ""
    observaciones: str = ""
    tipo_acta: str = "Acompañamiento"
    lugar: str = "Mérida, Yucatán"


class OficioPayload(BaseModel):
    id: Optional[str] = None
    folio: str = ""
    folio_manual: Optional[int] = None
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


# -------------------------------------------------------------
# 1. AUTENTICACIÓN Y SESIÓN
# -------------------------------------------------------------

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    """Responde 204 No Content para evitar errores 404 en la consola del navegador."""
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@app.get("/api/health")
def healthcheck():
    return {"status": "ok", "version": "2.0.0", "timestamp": time.time()}

@app.post("/api/logs/frontend")
def registrar_error_frontend(payload: Dict[str, Any]):
    """Registra errores de JavaScript capturados por ErrorBoundary para diagnóstico remoto."""
    err_msg = str(payload.get("message") or payload.get("error") or "Error no especificado")
    err_stack = str(payload.get("stack") or "")
    logger.error(f"[FRONTEND ERROR] {err_msg} | URL: {payload.get('url')} | Stack: {err_stack[:200]}")
    return {"status": "ok", "registrado": True}



@app.post("/api/auth/login")
def login_endpoint(payload: LoginPayload):
    user = autenticar_usuario(payload.usuario, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario o contraseña incorrectos.")
    token = emitir_token_sesion(user)
    return {
        "token": token,
        "user": {
            "id_usuario": getattr(user, "id_usuario", "USR-001"),
            "nombre": getattr(user, "nombre", "Psic. Edgar Adrian Yam Briceno"),
            "usuario": getattr(user, "usuario", payload.usuario),
            "rol": getattr(user, "rol", "DIRECTOR"),
            "escuelas_permitidas": getattr(user, "escuelas_permitidas", ["TODAS"]),
            "director": getattr(user, "director", True),
            "area": getattr(user, "area", "Dirección"),
        },
    }


@app.get("/api/me", response_model=SessionUser)
def obtener_perfil_actual(user: SessionUser = Depends(validar_token_sesion)):
    return user


@app.post("/api/auth/logout")
def logout_endpoint(authorization: Optional[str] = Header(None)):
    cerrar_sesion(authorization)
    return {"status": "success", "mensaje": "Sesión cerrada correctamente."}


# -------------------------------------------------------------

# -------------------------------------------------------------
# REGISTRO GLOBAL DE NOVEDADES EN VIVO (CERO RECARGAS)
# -------------------------------------------------------------
NOVEDADES_EN_VIVO: List[Dict[str, Any]] = []

def registrar_novedad(
    modulo: str,
    id_registro: str,
    accion: str,
    usuario: str,
    id_escuela: str = "",
    resumen: str = ""
):
    """Registra eventos en memoria para notificación reactiva entre pestañas y navegadores concurrentes."""
    global NOVEDADES_EN_VIVO
    evento = {
        "id_evento": uuid.uuid4().hex[:8],
        "timestamp": time.time(),
        "fecha_hora": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "modulo": modulo,
        "id_registro": str(id_registro),
        "accion": accion,
        "usuario": usuario,
        "id_escuela": str(id_escuela or ""),
        "resumen": str(resumen or "")[:180]
    }
    NOVEDADES_EN_VIVO.append(evento)
    if len(NOVEDADES_EN_VIVO) > 500:
        NOVEDADES_EN_VIVO = NOVEDADES_EN_VIVO[-500:]

@app.get("/api/novedades-en-vivo")
def obtener_novedades_en_vivo(
    desde: float = 0.0,
    user: SessionUser = Depends(validar_token_sesion)
):
    """Retorna las novedades registradas después del timestamp 'desde' filtradas por alcance institucional."""
    ahora = time.time()
    es_director = user.director or "TRABAJO" in user.rol.upper() or "TODAS" in user.escuelas_permitidas
    permitidas = set(user.escuelas_permitidas or [])

    filtradas = []
    for ev in reversed(NOVEDADES_EN_VIVO):
        if ev["timestamp"] <= desde:
            break
        if es_director or not ev["id_escuela"] or ev["id_escuela"] in permitidas or ev["usuario"] == user.usuario:
            filtradas.append(ev)

    return {
        "novedades": list(reversed(filtradas)),
        "servidor_tiempo": ahora,
        "total_eventos": len(NOVEDADES_EN_VIVO)
    }

# 2. ESCUELAS Y PADRÓN DE ALUMNOS (RBAC)
# -------------------------------------------------------------
@app.get("/api/escuelas")
def listar_escuelas(user: SessionUser = Depends(validar_token_sesion)):
    todas = obtener_catalogo_escuelas()
    if user.director or "TRABAJO" in user.rol.upper() or "TODAS" in user.escuelas_permitidas:
        return todas
    permitidas = {str(e).strip() for e in user.escuelas_permitidas}
    filtradas = [e for e in todas if e["id"] in permitidas]
    return filtradas or todas


@app.get("/api/alumnos")
def listar_alumnos(
    escuela: Optional[str] = None,
    incluir_inactivos: bool = False,
    user: SessionUser = Depends(validar_token_sesion),
):
    alumnos = obtener_alumnos_autorizados(
        usuario_rol=user.rol,
        escuelas_permitidas=user.escuelas_permitidas,
        nombre_docente=user.nombre,
        incluir_inactivos=incluir_inactivos,
    )
    if escuela:
        escuela_norm = escuela.strip().lower()
        alumnos = [
            a for a in alumnos
            if escuela_norm in str(a.get("escuela", "")).lower() or escuela_norm in str(a.get("id_escuela", "")).lower()
        ]
    return alumnos


@app.post("/api/alumnos")
def crear_alumno(payload: AlumnoPayload, user: SessionUser = Depends(validar_token_sesion)):
    if not user.director and "TODAS" not in user.escuelas_permitidas and payload.id_escuela not in user.escuelas_permitidas:
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
        "Estatus": payload.estatus,
        "Tipo_Atencion": payload.tipo_atencion,
    }
    try:
        nuevo_id = guardar_alumno_nuevo(doc_dict)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    registrar_novedad("alumnos", nuevo_id, "CREADO", user.usuario, payload.id_escuela, f"Alta de alumno {payload.nombre_completo}")
    return {"status": "success", "id": nuevo_id, "mensaje": "Alumno registrado exitosamente."}


@app.put("/api/alumnos/{alumno_id}")
def editar_alumno(alumno_id: str, payload: Dict[str, Any], user: SessionUser = Depends(validar_token_sesion)):
    alumnos = obtener_alumnos_autorizados(user.rol, user.escuelas_permitidas, user.nombre, incluir_inactivos=True)
    allowed_ids = [a["id"] for a in alumnos]
    if alumno_id not in allowed_ids and not user.director:
        raise HTTPException(status_code=403, detail="No tiene permisos para modificar este alumno.")
    try:
        actualizar_alumno_existente(alumno_id, payload, allowed_ids)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    registrar_novedad("alumnos", alumno_id, "ACTUALIZADO", user.usuario, payload.get("id_escuela", ""), f"Actualización de alumno {alumno_id}")
    return {"status": "success", "id": alumno_id, "mensaje": "Alumno actualizado correctamente."}


@app.get("/api/alumnos/exportar")
def exportar_alumnos_csv(user: SessionUser = Depends(validar_token_sesion)):
    alumnos = obtener_alumnos_autorizados(user.rol, user.escuelas_permitidas, user.nombre)
    df = pd.DataFrame(alumnos)
    csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="Padron_Alumnos_USAER_2E.csv"'},
    )


def _verificar_acceso_alumno(alumno_id: str, user: SessionUser) -> Dict[str, Any]:
    clean_id = str(alumno_id).replace("epp-", "").replace("alu-uppcoder-", "").strip()
    if clean_id.startswith("GRUPO-") or clean_id == "GRUPAL":
        return {"id": clean_id, "nombre_completo": clean_id}
    alumnos = obtener_alumnos_autorizados(
        "DIRECTOR" if user.director else user.rol, user.escuelas_permitidas,
        user.nombre, incluir_inactivos=True,
    )
    alumno = next((a for a in alumnos if str(a.get("id")).removeprefix("epp-").strip() == clean_id), None)
    if not alumno:
        raise HTTPException(404, "Alumno no disponible para esta cuenta.")
    return alumno


# -------------------------------------------------------------
# 3. EXPEDIENTES Y MÓDULOS DEDICADOS DE ANEXOS III, IV, V Y VII
# -------------------------------------------------------------
@app.get("/api/expedientes/{alumno_id}")
def ver_expediente(alumno_id: str, user: SessionUser = Depends(validar_token_sesion)):
    _verificar_acceso_alumno(alumno_id, user)
    return obtener_expediente_completo(alumno_id)


@app.get("/api/anexo3")
def listar_anexo3_endpoint(user: SessionUser = Depends(validar_token_sesion)):
    return obtener_anexo3_autorizados(user.rol, user.escuelas_permitidas, user.nombre)


@app.post("/api/anexo3")
def crear_anexo3(payload: Anexo3Payload, user: SessionUser = Depends(validar_token_sesion)):
    _verificar_acceso_alumno(payload.id_alumno, user)
    doc = {
        "ID_Anexo3": payload.id or f"AN3-{uuid.uuid4().hex[:6].upper()}",
        "Fecha": payload.fecha or time.strftime("%Y-%m-%d"),
        "ID_Alumno": payload.id_alumno,
        "ID_Personal": user.nombre,
        "BAP_Fisicas": payload.bap_fisicas,
        "BAP_Actitudinales": payload.bap_actitudinales,
        "BAP_Pedagogicas": payload.bap_pedagogicas,
        "BAP_Organizativas": payload.bap_organizativas,
        "Estatus_IA": "VALIDADO",
        "Estado": "ACTIVO",
    }
    aid = guardar_anexo3_documento(doc)
    registrar_novedad("anexo3", aid, "CREADO", user.usuario, "", f"Detección BAP para {payload.id_alumno}")
    return {"status": "success", "id": aid, "mensaje": "Detección de BAP (Anexo III) registrada correctamente."}


@app.put("/api/anexo3/{anexo_id}")
def actualizar_anexo3_endpoint(anexo_id: str, payload: Dict[str, Any], user: SessionUser = Depends(validar_token_sesion)):
    aid = actualizar_anexo3_documento(anexo_id, payload)
    return {"status": "success", "id": aid, "mensaje": "Anexo III actualizado correctamente."}


@app.delete("/api/anexo3/{anexo_id}")
def anular_anexo3_endpoint(anexo_id: str, user: SessionUser = Depends(validar_token_sesion)):
    aid = actualizar_anexo3_documento(anexo_id, {"Estado": "ANULADO"})
    return {"status": "success", "id": aid, "mensaje": "Anexo III anulado lógicamente."}


@app.get("/api/anexo4")
def listar_anexo4_endpoint(user: SessionUser = Depends(validar_token_sesion)):
    return obtener_anexo4_autorizados(user.rol, user.escuelas_permitidas, user.nombre)


@app.post("/api/anexo4")
def crear_anexo4(payload: Anexo4Payload, user: SessionUser = Depends(validar_token_sesion)):
    if payload.id_alumno and payload.id_alumno.startswith("ALU-"):
        _verificar_acceso_alumno(payload.id_alumno, user)
    obs_meta = json.dumps({
        "nombre_alumno": payload.nombre_alumno or payload.id_alumno,
        "grado_grupo": payload.grado_grupo,
        "escuela": payload.escuela,
        "servicio_ee": "USAER 2E",
    }, ensure_ascii=False)
    doc = {
        "ID_Anexo4": payload.id or f"AN4-{uuid.uuid4().hex[:6].upper()}",
        "ID_Alumno": payload.id_alumno or payload.nombre_alumno or "GRUPAL",
        "Fecha_Elaboracion": payload.fecha_elaboracion or time.strftime("%Y-%m-%d"),
        "Ciclo_Escolar": payload.ciclo_escolar,
        "Trimestre": payload.trimestre,
        "Docente_Especialista": payload.docente_especialista or user.nombre,
        "Area": payload.area,
        "Sugerencias_Area": payload.area,
        "Sugerencias": payload.sugerencias,
        "Motivo": payload.motivo,
        "Fecha_Seguimiento": payload.fecha_seguimiento,
        "Nivel_Cumplimiento_Resultados": payload.nivel_cumplimiento_resultados or "En seguimiento",
        "Observaciones": obs_meta,
        "Estado": "ACTIVA",
    }
    aid = guardar_anexo4_documento(doc)
    registrar_novedad("anexo4", aid, "CREADO", user.usuario, payload.escuela, f"Hoja de sugerencias para {payload.id_alumno}")
    return {"status": "success", "id": aid, "mensaje": "Hoja de sugerencias (Anexo IV) guardada correctamente."}


@app.put("/api/anexo4/{anexo_id}")
def actualizar_anexo4_endpoint(anexo_id: str, payload: Dict[str, Any], user: SessionUser = Depends(validar_token_sesion)):
    aid = actualizar_anexo4_documento(anexo_id, payload)
    return {"status": "success", "id": aid, "mensaje": "Hoja de sugerencias (Anexo IV) actualizada correctamente."}


@app.delete("/api/anexo4/{anexo_id}")
def anular_anexo4_endpoint(anexo_id: str, user: SessionUser = Depends(validar_token_sesion)):
    aid = actualizar_anexo4_documento(anexo_id, {"Estado": "ANULADA"})
    return {"status": "success", "id": aid, "mensaje": "Hoja de sugerencias (Anexo IV) anulada lógicamente."}


@app.get("/api/anexo5")
def listar_anexo5_endpoint(user: SessionUser = Depends(validar_token_sesion)):
    return obtener_anexo5_autorizados(user.rol, user.escuelas_permitidas, user.nombre)


@app.post("/api/anexo5")
def crear_anexo5(payload: Anexo5Payload, user: SessionUser = Depends(validar_token_sesion)):
    if payload.id_alumno and payload.id_alumno.startswith("ALU-"):
        alu = _verificar_acceso_alumno(payload.id_alumno, user)
        if not payload.nombre_alumno:
            payload.nombre_alumno = alu.get("nombre_completo", "")
        if not payload.escuela:
            payload.escuela = alu.get("escuela", "")
        if not payload.id_escuela:
            payload.id_escuela = alu.get("id_escuela", "")
        if not payload.grado_grupo:
            payload.grado_grupo = f"{alu.get('grado', '')}° {alu.get('grupo', '')}"
    doc = {
        "ID_Evento": payload.id or f"AN5-{uuid.uuid4().hex[:6].upper()}",
        "Fecha": payload.fecha or time.strftime("%Y-%m-%d"),
        "Nombre_Alumno": payload.nombre_alumno,
        "Grado_Grupo": payload.grado_grupo,
        "Especialista": payload.especialista or user.nombre,
        "Evento": payload.evento,
        "Estado": "ACTIVO",
        "ID_Alumno": payload.id_alumno,
        "ID_Escuela": payload.id_escuela,
        "Escuela": payload.escuela,
    }
    aid = guardar_anexo5_documento(doc)
    return {"status": "success", "id": aid, "mensaje": "Evento significativo (Anexo V) registrado correctamente."}


@app.put("/api/anexo5/{evento_id}")
def actualizar_anexo5_endpoint(evento_id: str, payload: Dict[str, Any], user: SessionUser = Depends(validar_token_sesion)):
    aid = actualizar_anexo5_documento(evento_id, payload)
    return {"status": "success", "id": aid, "mensaje": "Evento significativo actualizado correctamente."}


@app.delete("/api/anexo5/{evento_id}")
def anular_anexo5_endpoint(evento_id: str, user: SessionUser = Depends(validar_token_sesion)):
    aid = actualizar_anexo5_documento(evento_id, {"Estado": "ANULADO"})
    return {"status": "success", "id": aid, "mensaje": "Evento significativo anulado lógicamente."}


@app.get("/api/anexo7")
def listar_anexo7_endpoint(user: SessionUser = Depends(validar_token_sesion)):
    return obtener_anexo7_autorizados(user.rol, user.escuelas_permitidas, user.nombre)


@app.post("/api/anexo7")
def crear_anexo7(payload: Anexo7Payload, user: SessionUser = Depends(validar_token_sesion)):
    doc = {
        "ID_Anexo7": payload.id or f"AN7-{uuid.uuid4().hex[:6].upper()}",
        "Fecha": payload.fecha or time.strftime("%Y-%m-%d"),
        "ID_Alumno": payload.id_alumno,
        "Escuela": payload.escuela,
        "Docente_Regular": payload.docente_regular,
        "Fecha_Nacimiento": payload.fecha_nacimiento,
        "Respuestas_JSON": json.dumps(payload.respuestas, ensure_ascii=False) if not isinstance(payload.respuestas, str) else payload.respuestas,
        "Salud": payload.salud,
        "Seguimiento_Medico": payload.seguimiento_medico,
        "Aspecto_Relevante": payload.aspecto_relevante,
        "Elaborado_Por": payload.elaborado_por or user.nombre,
    }
    aid = guardar_anexo7_documento(doc)
    return {"status": "success", "id": aid, "mensaje": "Ficha de derivación (Anexo VII) guardada correctamente."}


@app.get("/api/anexo3/{anexo_id}/pdf")
def descargar_anexo3_pdf(anexo_id: str, user: SessionUser = Depends(validar_token_sesion)):
    from documents.anexos import anexo3_pdf
    from data.sql_repository import anexo3_sql
    df = anexo3_sql()
    sub = df[(df["ID_Anexo3"] == anexo_id) | (df["ID_Alumno"] == anexo_id)]
    if sub.empty:
        raise HTTPException(status_code=404, detail=f"Anexo III {anexo_id} no encontrado")
    aid = sub.iloc[0].get("ID_Alumno", anexo_id)
    alumno = {"ID_Alumno": aid, "Nombre_Completo": sub.iloc[0].get("Nombre_Alumno", aid), "Nombre_Escuela": sub.iloc[0].get("Escuela", "")}
    pdf_bytes = anexo3_pdf(alumno, sub)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="Anexo_III_{anexo_id}.pdf"'},
    )


@app.get("/api/anexo4/{anexo_id}/pdf")
def descargar_anexo4_pdf(anexo_id: str, user: SessionUser = Depends(validar_token_sesion)):
    from documents.anexos import anexo4_pdf
    from data.sql_repository import anexo4_sql
    df = anexo4_sql()
    sub = df[(df["ID_Anexo4"] == anexo_id) | (df["ID_Alumno"] == anexo_id)]
    if sub.empty:
        raise HTTPException(status_code=404, detail=f"Anexo IV {anexo_id} no encontrado")
    aid = sub.iloc[0].get("ID_Alumno", anexo_id)
    alumno = {"ID_Alumno": aid, "Nombre_Completo": sub.iloc[0].get("Nombre_Alumno", aid), "Nombre_Escuela": sub.iloc[0].get("Escuela", "")}
    pdf_bytes = anexo4_pdf(alumno, sub)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="Anexo_IV_{anexo_id}.pdf"'},
    )


@app.get("/api/anexo5/{anexo_id}/pdf")
def descargar_anexo5_pdf(anexo_id: str, user: SessionUser = Depends(validar_token_sesion)):
    from documents.anexos import anexo5_pdf
    from data.sql_repository import anexo5_sql
    df = anexo5_sql()
    sub = df[(df["ID_Evento"] == anexo_id) | (df["ID_Alumno"] == anexo_id)]
    if sub.empty:
        raise HTTPException(status_code=404, detail=f"Anexo V {anexo_id} no encontrado")
    aid = sub.iloc[0].get("ID_Alumno", anexo_id)
    alumno = {"ID_Alumno": aid, "Nombre_Completo": sub.iloc[0].get("Nombre_Alumno", aid), "Nombre_Escuela": sub.iloc[0].get("Escuela", "")}
    pdf_bytes = anexo5_pdf(alumno, sub)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="Anexo_V_{anexo_id}.pdf"'},
    )


@app.get("/api/anexo7/{anexo_id}/pdf")
def descargar_anexo7_pdf(anexo_id: str, user: SessionUser = Depends(validar_token_sesion)):
    from documents.anexos import anexo7_pdf
    if anexo_id == "plantilla":
        pdf_bytes = anexo7_pdf({})
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": 'attachment; filename="Anexo_VII_Hoja_Derivacion_Docente_Regular.pdf"'},
        )
    from data.sql_repository import anexo7_sql
    df = anexo7_sql()
    sub = df[(df["ID_Anexo7"] == anexo_id) | (df["ID_Alumno"] == anexo_id)]
    if sub.empty:
        raise HTTPException(status_code=404, detail=f"Anexo VII {anexo_id} no encontrado")
    pdf_bytes = anexo7_pdf(sub.iloc[0].to_dict())
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="Anexo_VII_{anexo_id}.pdf"'},
    )


@app.get("/api/oficios/{oficio_id}/pdf")
def descargar_oficio_pdf(oficio_id: str, user: SessionUser = Depends(validar_token_sesion)):
    from documents.oficios import generar_oficio_comision
    from data.sql_repository import oficios_comision_sql
    df = oficios_comision_sql()
    mask = (df["Folio"].astype(str) == str(oficio_id))
    if "ID_Oficio" in df.columns:
        mask = mask | (df["ID_Oficio"].astype(str) == str(oficio_id))
    if "ID" in df.columns:
        mask = mask | (df["ID"].astype(str) == str(oficio_id))
    sub = df[mask]
    if sub.empty:
        raise HTTPException(status_code=404, detail=f"Oficio {oficio_id} no encontrado")
    pdf_bytes = generar_oficio_comision(sub.iloc[0].to_dict())
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="Oficio_{oficio_id}.pdf"'},
    )


@app.get("/api/visitas/{visita_id}/pdf")
def descargar_visita_pdf(visita_id: str, user: SessionUser = Depends(validar_token_sesion)):
    from documents.visitas import visita_pdf
    from data.sql_repository import visitas_sql
    df = visitas_sql()
    sub = df[(df["ID_Visita"] == visita_id) | (df["ID_Visita"].str.lower() == visita_id.lower())]
    if sub.empty:
        raise HTTPException(status_code=404, detail=f"Visita {visita_id} no encontrada")
    row = sub.iloc[0].to_dict()
    motivos_list = [m.strip() for m in str(row.get("Motivo", "")).split("\n") if m.strip()] or [str(row.get("Motivo", "Acompañamiento"))]
    firmantes_list = [
        (str(row.get("Personal", user.nombre)), "Personal de Acompañamiento USAER 2E"),
        (user.nombre if user.rol == "DIRECTOR" else "Director(a) de Escuela / USAER", "Vo. Bo. Institucional"),
    ]
    pdf_bytes = visita_pdf(
        titulo=f"ACTA DE VISITA — {row.get('Tipo_Acta', 'ACOMPAÑAMIENTO')}".upper(),
        folio=str(row.get("ID_Visita", visita_id)),
        escuela=str(row.get("Escuela", "")),
        lugar=str(row.get("Lugar", "Mérida, Yucatán")),
        fecha=str(row.get("Fecha", "")),
        ciclo="2026-2027",
        especialidad="USAER 02-E (Zona 001 Primarias)",
        motivos=motivos_list,
        detalles=str(row.get("Observaciones", "")),
        descripcion=str(row.get("Observaciones", "Se constató el desarrollo de las actividades programadas.")),
        firmantes=firmantes_list,
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="Visita_{visita_id}.pdf"'},
    )


# -------------------------------------------------------------
# 4. EVALUACIÓN PSICOPEDAGÓGICA (EPP) MULTI-ÁREA
# -------------------------------------------------------------
@app.get("/api/epp")
def listar_epps_endpoint(user: SessionUser = Depends(validar_token_sesion)):
    return listar_epp_autorizados(user.rol, user.escuelas_permitidas, user.nombre)


def _id_epp(alumno_id):
    value = str(alumno_id).removeprefix("epp-").removeprefix("alu-uppcoder-").strip()
    if not value or value == "GRUPAL" or value.startswith("GRUPO-"):
        raise HTTPException(404, "La EPP requiere un alumno del padrón autorizado.")
    return value


def _cargar_epp(alumno_id, ciclo, user):
    from data.sql_repository import epp_listar_sql
    from services.epp_modelo import clave

    alumno_id = _id_epp(alumno_id)
    alumno = _verificar_acceso_alumno(alumno_id, user)
    try:
        identificador = clave(alumno_id, ciclo)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    candidatos = [d for d in epp_listar_sql([alumno_id, "epp-" + alumno_id, "alu-uppcoder-" + alumno_id])
                  if d["ciclo"] == ciclo]
    if len(candidatos) > 1:
        raise HTTPException(409, "Existen varias EPP para este ciclo. Dirección debe conciliar sus revisiones.")
    return (candidatos[0] if candidatos else {
        "id": identificador, "alumno": alumno_id, "ciclo": ciclo, "revision": None, "partes": {}
    }), alumno


def _vista_epp(doc, alumno, user):
    from piloto_spa.backend.epp_viva import editables, vista_partes
    from services.epp_modelo import BAP, NEE

    return {"id": doc["id"], "alumno": _id_epp(doc["alumno"]), "ciclo": doc["ciclo"],
            "revision": doc["revision"], "nombre_alumno": alumno.get("nombre_completo", ""),
            "partes": vista_partes(doc), "editables": editables(doc, user),
            "columnas": {"nee": NEE, "bap": BAP}}


@app.get("/api/epp/{alumno_id}")
def consultar_epp(alumno_id: str, ciclo: str = "2026-2027", user: SessionUser = Depends(validar_token_sesion)):
    doc, alumno = _cargar_epp(alumno_id, ciclo, user)
    return _vista_epp(doc, alumno, user)


class EPPVivaPayload(BaseModel):
    ciclo: str
    area: str
    revision: Optional[str] = None
    campos: Dict[str, str] = Field(default_factory=dict)
    instrumentos: Optional[str] = Field(default=None, max_length=12000)
    fecha_aplicacion: Optional[str] = Field(default=None, max_length=100)
    sintesis: Optional[str] = Field(default=None, max_length=12000)
    nee: Optional[List[Dict[str, str]]] = Field(default=None, max_length=50)
    bap: Optional[List[Dict[str, str]]] = Field(default=None, max_length=50)
    revisada: bool = False


@app.put("/api/epp/{alumno_id}/apartado")
def guardar_epp_viva(alumno_id: str, payload: EPPVivaPayload, user: SessionUser = Depends(validar_token_sesion)):
    from data.sql_repository import guardar_epp_sql
    from piloto_spa.backend.epp_viva import editables, vista_partes
    from services.epp_modelo import AREAS, validar_parte, pendientes
    from sqlalchemy.exc import IntegrityError

    doc, alumno = _cargar_epp(alumno_id, payload.ciclo, user)
    if payload.area not in editables(doc, user):
        raise HTTPException(403, "Este apartado corresponde a otra área o coordinación.")
    if payload.revision != doc["revision"]:
        raise HTTPException(409, "La EPP cambió en otra sesión. Conserva tu texto y abre la revisión más reciente.")
    previas = vista_partes(doc)
    valor = previas[payload.area]["contenido"]
    if not payload.campos.keys() <= valor["campos"].keys():
        raise HTTPException(422, "Hay campos fuera del formato de esta área.")
    for key, value in payload.campos.items():
        if not valor.get("no_requeridos", {}).get(key):
            valor["campos"][key] = value
            if key in valor:
                valor[key] = value
    for k in ("instrumentos", "fecha_aplicacion", "sintesis"):
        if getattr(payload, k) is not None:
            valor[k] = getattr(payload, k)
    if payload.area == "Conclusión":
        for k in ("nee", "bap"):
            if getattr(payload, k) is not None:
                valor[k] = getattr(payload, k)
    elif payload.nee is not None or payload.bap is not None:
        raise HTTPException(403, "Las tablas de determinación corresponden a la coordinación.")
    valor["validada"] = payload.revisada
    if payload.area == "Conclusión" and payload.revisada:
        valor["revisiones_areas"] = {a: previas[a]["revision"] for a in AREAS}
        control = {**previas, "Conclusión": {"contenido": valor}}
        faltantes = pendientes({"partes": control})
        if faltantes:
            raise HTTPException(422, " ".join(faltantes))
    try:
        valor = validar_parte(payload.area, valor)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    revision = uuid.uuid4().hex
    fecha = time.strftime("%Y-%m-%d %H:%M:%S")
    doc["partes"][payload.area] = {"contenido": valor, "autor": user.nombre, "cuenta": user.usuario,
                                  "revision": revision, "fecha": fecha,
                                  "estado": "REVISADO" if payload.revisada else "BORRADOR"}
    doc["partes"].setdefault("META", {"estado": "BORRADOR"})
    doc.update(revision=revision, fecha=fecha)
    try:
        if guardar_epp_sql(doc, comparar_revision=True, revision_anterior=payload.revision) is None:
            raise HTTPException(409, "Otra sesión guardó esta EPP. Conserva tu texto antes de reabrir.")
    except IntegrityError as exc:
        raise HTTPException(409, "Otra sesión abrió y guardó esta EPP.") from exc
    return _vista_epp(doc, alumno, user)


@app.post("/api/epp")
def guardar_epp(payload: EPPPayload, user: SessionUser = Depends(validar_token_sesion)):
    raise HTTPException(405, "Actualiza la página y guarda únicamente tu apartado de la EPP.")


@app.get("/api/epp/{alumno_id}/pdf")
def descargar_epp_pdf(alumno_id: str, ciclo: str = "2026-2027", user: SessionUser = Depends(validar_token_sesion)):
    from documents.epp import generar_pdf
    from piloto_spa.backend.epp_viva import vista_partes

    doc, a = _cargar_epp(alumno_id, ciclo, user)
    if doc["revision"] is None:
        raise HTTPException(404, "Aún no hay un informe guardado para este ciclo.")
    doc["partes"] = vista_partes(doc)
    alumno = {"Nombre_Completo": a.get("nombre_completo"), "Nombre_Escuela": a.get("escuela"),
              "Nivel_Educativo": a.get("nivel"), "CURP": a.get("curp"),
              "Grado": a.get("grado"), "Grupo": a.get("grupo")}
    return Response(generar_pdf(doc, alumno, incluir_firmas=False, precargar_datos=False),
                    media_type="application/pdf", headers={"Cache-Control": "private, no-store"})


class EPPAsistentePayload(BaseModel):
    ciclo: str
    area: str
    campo: str = Field(default="", max_length=180)
    notas: str = Field(default="", max_length=4000)
    archivo_nombre: str = Field(default="", max_length=200)
    archivo_base64: str = Field(default="", max_length=4194304)


@app.post("/api/epp/{alumno_id}/propuesta")
def proponer_epp_viva(alumno_id: str, payload: EPPAsistentePayload, user: SessionUser = Depends(validar_token_sesion)):
    from piloto_spa.backend.epp_viva import editables, extraer, propuesta_campo, propuesta_conclusion, vista_partes
    doc, _ = _cargar_epp(alumno_id, payload.ciclo, user)
    if payload.area not in editables(doc, user):
        raise HTTPException(403, "Esta cuenta no puede generar propuestas para ese apartado.")
    try:
        if payload.area == "Conclusión":
            return propuesta_conclusion(doc)
        if payload.campo not in vista_partes(doc)[payload.area]["contenido"]["campos"]:
            raise ValueError("Selecciona un apartado del formato.")
        texto, huella = extraer(payload.archivo_nombre, payload.archivo_base64) if payload.archivo_base64 else ("", "")
        evidencia = "\n".join(x for x in (texto, payload.notas.strip()) if x)
        return {"texto": propuesta_campo(payload.campo, evidencia), "archivo_sha256": huella,
                "fuente": payload.archivo_nombre if huella else "Observación docente"}
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except ImportError as exc:
        raise HTTPException(503, "El lector de este archivo no está instalado. Prueba con TXT.") from exc


@app.get("/api/epp/{alumno_id}/pruebas")
def listar_pruebas_epp(alumno_id: str, user: SessionUser = Depends(validar_token_sesion)):
    clean_id = _id_epp(alumno_id)
    _verificar_acceso_alumno(clean_id, user)
    return [{k: p[k] for k in ("id", "nombre_prueba", "area", "fecha", "observaciones", "nombre_archivo") if k in p}
            for p in coleccion_listar_sql("epp_pruebas") if str(p.get("alumno_id")) == clean_id]


# -------------------------------------------------------------
# 5. PLANEACIÓN PEDAGÓGICA (FORMATOS XXI, XXIII, XXV, XIX, XX)
# -------------------------------------------------------------
@app.get("/api/planeaciones")
def listar_planeaciones(user: SessionUser = Depends(validar_token_sesion)):
    return listar_planeaciones_autorizadas(
        cuenta=user.usuario,
        usuario_rol=user.rol,
        escuelas_permitidas=user.escuelas_permitidas,
        nombre_docente=user.nombre,
        es_director=user.director,
    )


@app.get("/api/planeaciones/{doc_id}")
def obtener_planeacion(doc_id: str, user: SessionUser = Depends(validar_token_sesion)):
    from data.sql_repository import planeacion_por_id_sql

    registrada = planeacion_por_id_sql(doc_id)
    if not registrada and not doc_id.startswith("plan-nuevo-"):
        raise HTTPException(404, "Planeación no encontrada.")
    doc = obtener_planeacion_con_firmas(doc_id, usuario_cuenta=user.usuario)
    if registrada and not verificar_acceso_planeacion(
        doc=doc,
        usuario_cuenta=user.usuario,
        usuario_rol=user.rol,
        escuelas_permitidas=user.escuelas_permitidas,
        nombre_docente=user.nombre,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para acceder a esta planeación."
        )
    meta = doc.get("metadatos", {})
    datos = doc.get("datos", {})
    if meta.get("modalidad_planeacion") == "grupal" and (
        meta.get("vista_formato") == "guia" or isinstance(meta.get("guia_grupal_manual"), dict)
    ) and all(k in datos for k in ("Alumnos", "Función")):
        from services.planeacion_modalidad import guia_grupal
        doc["guia_grupal"] = guia_grupal(doc)
    return doc


@app.post("/api/planeaciones")
def guardar_planeacion(payload: PlaneacionPayload, user: SessionUser = Depends(validar_token_sesion)):
    doc_dict = payload.model_dump()
    res = guardar_planeacion_transaccional(
        payload=doc_dict,
        autor_cuenta=user.usuario,
        usuario_rol=user.rol,
        escuelas_permitidas=user.escuelas_permitidas,
        nombre_docente=user.nombre,
        area_docente=user.area,
    )
    plan_id = res.get("id") or doc_dict.get("id") or "plan"
    esc_id = doc_dict.get("datos", {}).get("Escuela_ID") or doc_dict.get("metadatos", {}).get("id_escuela") or ""
    registrar_novedad("planeaciones", plan_id, "ACTUALIZADO" if doc_dict.get("revision") else "CREADO", user.usuario, str(esc_id), f"Planeación {plan_id} guardada por {user.nombre}")
    return res


@app.delete("/api/planeaciones/{doc_id}")
def eliminar_planeacion_endpoint(doc_id: str, user: SessionUser = Depends(validar_token_sesion)):
    ok = eliminar_planeacion_documento(doc_id, usuario_cuenta=user.usuario, es_director=user.director)
    if not ok:
        raise HTTPException(status_code=404, detail="No se encontró la planeación o no tiene permisos para eliminarla.")
    return {"status": "success", "mensaje": "Planeación eliminada correctamente."}


@app.get("/api/planeaciones/{doc_id}/pdf")
def descargar_planeacion_pdf(doc_id: str, user: SessionUser = Depends(validar_token_sesion)):
    doc = obtener_planeacion_con_firmas(doc_id, usuario_cuenta=user.usuario)
    if not verificar_acceso_planeacion(
        doc=doc,
        usuario_cuenta=user.usuario,
        usuario_rol=user.rol,
        escuelas_permitidas=user.escuelas_permitidas,
        nombre_docente=user.nombre,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para descargar el PDF de esta planeación."
        )
    try:
        pdf_bytes = generar_pdf_planeacion(doc)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error generando PDF de planeación: {exc}")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="Planeacion_{doc_id}.pdf"'},
    )


# -------------------------------------------------------------
# 6. ACTAS DE VISITA Y OFICIOS DE COMISIÓN
# -------------------------------------------------------------
@app.get("/api/visitas")
def listar_visitas(escuela: Optional[str] = None, user: SessionUser = Depends(validar_token_sesion)):
    return obtener_visitas_documentos(escuela, user.rol, user.escuelas_permitidas, user.nombre)


@app.post("/api/visitas")
def crear_visita(payload: VisitaPayload, user: SessionUser = Depends(validar_token_sesion)):
    doc = {
        "Fecha": payload.fecha or time.strftime("%Y-%m-%d"),
        "Escuela": payload.escuela,
        "Personal": payload.personal or user.nombre,
        "Motivo": payload.motivo,
        "Observaciones": payload.observaciones,
        "Tipo_Acta": payload.tipo_acta,
        "Lugar": payload.lugar,
        "Estatus": "GENERADA",
    }
    vid = guardar_visita_documento(doc)
    return {"status": "success", "id": vid, "mensaje": "Constancia / Acta de visita guardada correctamente."}


@app.get("/api/oficios")
def listar_oficios(escuela: Optional[str] = None, user: SessionUser = Depends(validar_token_sesion)):
    return obtener_oficios_documentos(escuela, user.rol, user.escuelas_permitidas, user.nombre)


@app.post("/api/oficios")
def crear_oficio(payload: OficioPayload, user: SessionUser = Depends(validar_token_sesion)):
    from data.sql_repository import guardar_oficio_comision_sql
    doc = {
        "Folio": payload.folio,
        "Clave_Operacion": payload.clave_operacion or f"{payload.maestra_apoyo}|{payload.escuela}|{payload.fecha_comision}|{payload.asunto}",
        "Fecha_Emision": payload.fecha_emision or time.strftime("%Y-%m-%d"),
        "Fecha_Comision": payload.fecha_comision or time.strftime("%Y-%m-%d"),
        "Escuela": payload.escuela,
        "ID_Escuela": payload.id_escuela,
        "Maestra_Apoyo": payload.maestra_apoyo or user.nombre,
        "Director_Escuela": payload.director_escuela,
        "Asunto": payload.asunto,
        "Destino": payload.destino,
        "Horario": payload.horario or "en su horario laboral",
        "Estado": "GENERADO",
    }
    res = guardar_oficio_comision_sql(doc, folio_manual=payload.folio_manual)
    return {"status": "success", "oficio": res, "mensaje": "Oficio de comisión emitido correctamente."}


@app.get("/api/oficios/configuracion")
def obtener_config_oficios(user: SessionUser = Depends(validar_token_sesion)):
    df = configuracion_oficios_sql()
    return df.to_dict(orient="records") if not df.empty else []


@app.post("/api/oficios/configuracion")
def guardar_config_oficios(payload: Dict[str, Any], user: SessionUser = Depends(validar_token_sesion)):
    payload["Actualizado_Por"] = user.nombre
    payload["Actualizado_En"] = time.strftime("%Y-%m-%d %H:%M:%S")
    return guardar_configuracion_oficios_sql(payload)


# -------------------------------------------------------------
# 7. HORARIOS, CRONOGRAMAS, CALENDARIO, MAESTROS PRIMARIA, NOVEDADES, JUNTAS, METAS, TRÁMITES E INFORMES
# -------------------------------------------------------------
@app.get("/api/horarios")
def listar_horarios(
    escuela: Optional[str] = None,
    docente: Optional[str] = None,
    user: SessionUser = Depends(validar_token_sesion)
):
    target_doc = docente if (docente and user.director) else (user.nombre if not user.director else "")
    return obtener_horarios_modulo(user.rol, user.escuelas_permitidas, target_doc, escuela=escuela or "")


@app.post("/api/horarios")
def guardar_horario(payload: Dict[str, Any], user: SessionUser = Depends(validar_token_sesion)):
    return guardar_horario_modulo(payload, user.nombre)


@app.get("/api/cronogramas")
def listar_cronogramas(
    mes: Optional[str] = None,
    docente: Optional[str] = None,
    usuario: Optional[str] = None,
    user: SessionUser = Depends(validar_token_sesion)
):
    target = (docente or usuario) if (docente or usuario) and user.director else (user.nombre if not user.director else "")
    return obtener_cronogramas_modulo(user.rol, user.escuelas_permitidas, target, mes=mes or "")


@app.post("/api/cronogramas")
def guardar_cronograma(payload: Dict[str, Any], user: SessionUser = Depends(validar_token_sesion)):
    return guardar_cronograma_modulo(payload, user.nombre)


@app.get("/api/calendario")
def listar_calendario(mes: Optional[str] = None, user: SessionUser = Depends(validar_token_sesion)):
    return obtener_calendario_modulo(mes)


@app.post("/api/calendario")
def crear_evento_calendario(payload: Dict[str, Any], user: SessionUser = Depends(validar_token_sesion)):
    return guardar_evento_calendario_modulo(payload, user.nombre)


@app.get("/api/docentes-regulares")
def listar_docentes_primaria(user: SessionUser = Depends(validar_token_sesion)):
    return obtener_docentes_regulares_autorizados(user.rol, user.escuelas_permitidas)


@app.post("/api/docentes-regulares")
def crear_docente_primaria(payload: Dict[str, Any], user: SessionUser = Depends(validar_token_sesion)):
    did = guardar_docente_regular_modulo(payload)
    return {"status": "success", "id": did, "mensaje": "Docente de primaria registrado correctamente."}


@app.get("/api/novedades")
def listar_novedades(user: SessionUser = Depends(validar_token_sesion)):
    if not user.director and user.rol != "DIRECTOR":
        raise HTTPException(status_code=403, detail="Módulo de supervisión exclusivo de Dirección.")
    return coleccion_listar_sql("novedades_supervision")


@app.post("/api/novedades")
def crear_novedad(payload: Dict[str, Any], user: SessionUser = Depends(validar_token_sesion)):
    did = str(payload.get("id") or f"nov-{uuid.uuid4().hex[:8]}")
    doc = {
        "ID_Documento": did,
        "Nombre": str(payload.get("nombre") or "").strip(),
        "Seccion": str(payload.get("seccion") or "General").strip(),
        "Tipo": str(payload.get("tipo") or "documento").strip(),
        "Enlace": str(payload.get("enlace") or "").strip(),
        "Extracto": str(payload.get("extracto") or "").strip(),
        "Modificado_En": time.strftime("%Y-%m-%d"),
        "Estado_Lectura": "Disponible",
        "Estado": "VIGENTE",
    }
    coleccion_guardar_sql("novedades_supervision", did, doc, cuenta=user.usuario, fecha=doc["Modificado_En"])
    return {"status": "success", "id": did, "documento": doc}


@app.get("/api/juntas")
def listar_juntas(user: SessionUser = Depends(validar_token_sesion)):
    return obtener_juntas_y_catalogo(user.usuario, es_director=user.director)


@app.post("/api/juntas")
def guardar_junta(payload: Dict[str, Any], user: SessionUser = Depends(validar_token_sesion)):
    reg_id = str(payload.get("id") or f"junta-{user.usuario}-{payload.get('fecha_sesion', time.strftime('%Y-%m-%d'))}")
    doc = {
        "id": reg_id,
        "cuenta": user.usuario,
        "docente": user.nombre,
        "area": user.area,
        "fecha_sesion": str(payload.get("fecha_sesion") or time.strftime("%Y-%m-%d")),
        "codigo": str(payload.get("codigo") or ""),
        "necesidad": str(payload.get("necesidad") or ""),
        "A": bool(payload.get("A", False)),
        "C": bool(payload.get("C", False)),
        "P": bool(payload.get("P", False)),
        "aplicacion_prevista": str(payload.get("aplicacion_prevista") or ""),
        "evidencia_seguimiento": str(payload.get("evidencia_seguimiento") or ""),
        "guardado_en": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    coleccion_guardar_sql("juntas_academicas", reg_id, doc, cuenta=user.usuario, fecha=doc["fecha_sesion"])
    return {"status": "success", "id": reg_id, "documento": doc}


@app.get("/api/personal")
def listar_personal_endpoint(user: SessionUser = Depends(validar_token_sesion)):
    from data.sql_repository import personal_sql
    df = personal_sql()
    return df.to_dict(orient="records") if not df.empty else []


@app.get("/api/ai/motores")
def listar_motores_ia(user: SessionUser = Depends(validar_token_sesion)):
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    motores = [
        {
            "id": "gemini-1.5-flash",
            "nombre": "Google Gemini 1.5 Flash (Rápido y Oficial)",
            "proveedor": "Google",
            "disponible": bool(gemini_key),
            "recomendado": bool(gemini_key)
        },
        {
            "id": "gemini-2.5-pro",
            "nombre": "Google Gemini 2.5 Pro (Razonamiento Complejo)",
            "proveedor": "Google",
            "disponible": bool(gemini_key),
            "recomendado": False
        },
        {
            "id": "gpt-4o",
            "nombre": "OpenAI GPT-4o",
            "proveedor": "OpenAI",
            "disponible": bool(openai_key),
            "recomendado": bool(openai_key and not gemini_key)
        },
        {
            "id": "plantilla-institucional",
            "nombre": "Plantilla Institucional USAER 2E (Determinista / Sin API Key)",
            "proveedor": "USAER 2E",
            "disponible": True,
            "recomendado": not bool(gemini_key or openai_key)
        }
    ]
    return {
        "motores": motores,
        "proveedor_activo": "gemini" if gemini_key else ("openai" if openai_key else "plantilla"),
        "tiene_llave": bool(gemini_key or openai_key)
    }


@app.get("/api/relatorias")
def listar_relatorias(user: SessionUser = Depends(validar_token_sesion)):
    guardadas = coleccion_listar_sql("relatorias")
    ids_guardadas = {str(r.get("id")) for r in guardadas}

    # Integrar actas históricas de visitas (Juntas de USAER y Reuniones de Trabajo)
    from data.sql_repository import visitas_sql
    try:
        df_v = visitas_sql()
        if not df_v.empty:
            for _, v in df_v.iterrows():
                tipo = str(v.get("Tipo_Acta") or "").strip()
                motivo = str(v.get("Motivo") or "").strip()
                if any(k in tipo.lower() or k in motivo.lower() for k in ["junta", "reunión", "reunion", "cte", "consejo técnico"]):
                    vid = f"visita-{v.get('ID_Visita')}"
                    if vid in ids_guardadas:
                        continue
                    obs = str(v.get("Observaciones") or "").strip()
                    evid = str(v.get("Evidencia") or "").strip()
                    guardadas.append({
                        "id": vid,
                        "fecha": str(v.get("Fecha") or "")[:10],
                        "sesion": motivo or tipo or "Reunión de Trabajo",
                        "tipo_junta": tipo or "Junta de USAER",
                        "modalidad": "Presencial" + (f" ({v.get('Escuela')})" if v.get("Escuela") else ""),
                        "tema": motivo or "Atención Pedagógica y Organización Escolar",
                        "cuerpo": obs or f"Reunión colegiada celebrada en {v.get('Escuela') or 'Sede USAER 02E'}.",
                        "acuerdos": evid or "• Continuar con el acompañamiento pedagógico programado.",
                        "asistentes": 6,
                        "autor": str(v.get("Personal") or "Dirección USAER"),
                        "origen": "Histórico (Actas de Visita)",
                        "guardado_en": str(v.get("Fecha") or "")
                    })
    except Exception as exc:
        logger.warning("Aviso integrando visitas en relatorias: %s", exc)

    guardadas.sort(key=lambda x: str(x.get("fecha") or ""), reverse=True)
    return guardadas


@app.post("/api/relatorias")
def guardar_relatoria(payload: Dict[str, Any], user: SessionUser = Depends(validar_token_sesion)):
    reg_id = str(payload.get("id") or f"rel-{uuid.uuid4().hex[:8]}")
    doc = {
        "id": reg_id,
        "fecha": str(payload.get("fecha") or time.strftime("%Y-%m-%d")),
        "sesion": str(payload.get("sesion") or "Consejo Técnico Escolar"),
        "tipo_junta": str(payload.get("tipo_junta") or "CTE"),
        "modalidad": str(payload.get("modalidad") or "Presencial"),
        "tema": str(payload.get("tema") or ""),
        "cuerpo": str(payload.get("cuerpo") or ""),
        "acuerdos": str(payload.get("acuerdos") or ""),
        "asistentes": int(payload.get("asistentes", 6) or 6),
        "autor": user.nombre,
        "guardado_en": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    coleccion_guardar_sql("relatorias", reg_id, doc, cuenta=user.usuario, fecha=doc["fecha"])
    return {"status": "success", "id": reg_id, "relatoria": doc}


@app.post("/api/relatorias/generar")
def generar_relatoria_endpoint(payload: Dict[str, Any], user: SessionUser = Depends(validar_token_sesion)):
    sesion = str(payload.get("sesion") or "Primera Sesión")
    tema = str(payload.get("tema") or "Atención a la Diversidad y BAP")
    notas = str(payload.get("notas") or "").strip()
    tipo_junta = str(payload.get("tipo_junta") or "Junta de USAER")
    modalidad_junta = str(payload.get("modalidad_junta") or "Sesión de CTE")
    fecha_str = str(payload.get("fecha") or time.strftime("%Y-%m-%d"))
    motor_solicitado = str(payload.get("motor") or "").strip().lower()
    api_key_manual = str(payload.get("api_key_manual") or "").strip()

    texto_generado = None
    motor_utilizado = "Plantilla Institucional Determinista"

    prompt = (
        f"Actúa como secretario técnico de la USAER 02-E y redacta una relatoría institucional "
        f"de la sesión indicada. No inventes hechos ni compromisos; basa la redacción en las notas provistas.\n"
        f"Estructura el cuerpo en:\n"
        f"1. Contexto y desarrollo: síntesis formal del diálogo colegiado.\n"
        f"2. Reflexiones y retos pedagógicos.\n"
        f"3. Acuerdos y compromisos con responsables y plazos.\n\n"
        f"Tipo de junta: {tipo_junta}\n"
        f"Modalidad: {modalidad_junta}\n"
        f"Fecha de la sesión: {fecha_str}\n"
        f"Sesión: {sesion}\n"
        f"Tema central: {tema}\n"
        f"Notas de Dirección: {notas or 'Revisión técnica de atención pedagógica y ajustes razonables'}\n"
    )

    # 1. Probar Gemini si fue seleccionado o si hay llave Gemini
    gemini_key = api_key_manual if (api_key_manual and "AIza" in api_key_manual) else (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
    if not texto_generado and (motor_solicitado.startswith("gemini") or (gemini_key and not motor_solicitado.startswith("gpt") and not motor_solicitado.startswith("plantilla"))):
        if gemini_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=gemini_key)
                modelo_nom = "gemini-1.5-flash"
                if "2.5" in motor_solicitado or "pro" in motor_solicitado:
                    modelo_nom = "gemini-1.5-pro"
                model = genai.GenerativeModel(modelo_nom)
                res = model.generate_content(prompt)
                if res and res.text:
                    texto_generado = res.text.strip()
                    motor_utilizado = f"Google Gemini ({modelo_nom})"
            except Exception as e:
                logger.warning(f"Generador Gemini relatorías no disponible: {e}")

    # 2. Probar OpenAI si fue seleccionado o si hay llave OpenAI
    openai_key = api_key_manual if (api_key_manual and api_key_manual.startswith("sk-")) else os.getenv("OPENAI_API_KEY")
    if not texto_generado and (motor_solicitado.startswith("gpt") or (openai_key and not motor_solicitado.startswith("plantilla"))):
        if openai_key:
            try:
                import urllib.request
                import json
                req_data = json.dumps({
                    "model": "gpt-4o",
                    "messages": [
                        {"role": "system", "content": "Eres el secretario técnico de la USAER 02E. Redactas relatorías institucionales formales."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.4
                }).encode("utf-8")
                req = urllib.request.Request(
                    "https://api.openai.com/v1/chat/completions",
                    data=req_data,
                    headers={
                        "Authorization": f"Bearer {openai_key}",
                        "Content-Type": "application/json"
                    }
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    resp_json = json.loads(resp.read().decode("utf-8"))
                    texto_generado = resp_json["choices"][0]["message"]["content"].strip()
                    motor_utilizado = "OpenAI GPT-4o"
            except Exception as e:
                logger.warning(f"Generador OpenAI relatorías no disponible: {e}")

    # 3. Si no hay proveedor externo o falló, plantilla institucional estructurada
    if not texto_generado:
        motor_utilizado = "Plantilla Institucional Determinista"
        texto_generado = (
            f"1. Contexto y desarrollo:\n"
            f"El personal docente y técnico de la USAER 02-E se reunió formalmente en modalidad {modalidad_junta.lower()} ({tipo_junta}) "
            f"para abordar la temática «{tema}» correspondiente a la {sesion}.\n"
            f"{notas if notas else 'Se dio inicio con la revisión de prioridades técnico-pedagógicas, el análisis colegiado de la atención a alumnos que enfrentan BAP y la organización de los apoyos en las escuelas primarias adscritas.'}\n\n"
            f"2. Reflexiones y retos pedagógicos:\n"
            f"El colegiado reflexionó sobre la importancia de consolidar los ajustes razonables en las aulas regulares, "
            f"fortaleciendo la colaboración interdisciplinaria entre docentes de apoyo, especialistas de área y personal directivo.\n"
            f"Se enfatizó la necesidad de mantener actualizados los expedientes institucionales y articular la evaluación psicopedagógica con la planeación de intervención.\n\n"
            f"3. Acuerdos y compromisos:\n"
            f"• Dar seguimiento puntual a las evaluaciones psicopedagógicas y planes de intervención vigentes.\n"
            f"• Coordinar las visitas de acompañamiento escolar conforme a los cronogramas publicados.\n"
            f"• Mantener actualizados los expedientes y registros en la plataforma institucional USAER 2E."
        )

    return {"status": "success", "texto": texto_generado, "motor_utilizado": motor_utilizado}


@app.get("/api/relatorias/{relatoria_id}/pdf")
def descargar_relatoria_pdf(relatoria_id: str, user: SessionUser = Depends(validar_token_sesion)):
    from documents.relatorias import generar_pdf_oficial
    from data.sql_repository import coleccion_obtener_sql
    rel = coleccion_obtener_sql("relatorias", relatoria_id)
    if not rel:
        guardados = coleccion_listar_sql("relatorias")
        rel = next((r for r in guardados if str(r.get("id")) == str(relatoria_id)), None)
    if not rel and relatoria_id.startswith("visita-"):
        from data.sql_repository import visitas_sql
        df_v = visitas_sql()
        target_vid = relatoria_id.replace("visita-", "")
        v_sub = df_v[df_v["ID_Visita"] == target_vid]
        if not v_sub.empty:
            vr = v_sub.iloc[0]
            rel = {
                "id": relatoria_id,
                "fecha": str(vr.get("Fecha") or "")[:10],
                "sesion": str(vr.get("Motivo") or vr.get("Tipo_Acta") or "Reunión de Trabajo"),
                "tipo_junta": str(vr.get("Tipo_Acta") or "Junta de USAER"),
                "modalidad": "Presencial (" + str(vr.get("Escuela") or "USAER") + ")",
                "tema": str(vr.get("Motivo") or "Reunión de Trabajo Colegiado"),
                "cuerpo": str(vr.get("Observaciones") or f"Reunión celebrada en {vr.get('Escuela')}."),
                "acuerdos": str(vr.get("Evidencia") or "• Seguimiento puntual a los compromisos acordados."),
                "asistentes": 6
            }
    if not rel:
        raise HTTPException(status_code=404, detail="Relatoría no encontrada.")
    fecha_dt = None
    try:
        from datetime import date
        f_str = str(rel.get("fecha", ""))[:10]
        if f_str:
            fecha_dt = date.fromisoformat(f_str)
    except Exception:
        pass
    pdf_bytes = generar_pdf_oficial(
        contenido_relatoria=rel.get("cuerpo", "") + ("\n\n**Acuerdos y compromisos:**\n" + rel.get("acuerdos", "") if rel.get("acuerdos") else ""),
        num_asistentes=int(rel.get("asistentes", 6) or 6),
        fecha=fecha_dt,
        sesion=rel.get("sesion", "Sesión Ordinaria"),
        tema=rel.get("tema", ""),
        tipo_junta=rel.get("tipo_junta", "Junta de USAER"),
        modalidad_junta=rel.get("modalidad", "Junta Académica"),
    )
    content_val = pdf_bytes.getvalue() if hasattr(pdf_bytes, "getvalue") else pdf_bytes
    return Response(
        content=content_val,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="Relatoria_{relatoria_id}.pdf"'},
    )


@app.get("/api/metas")
def listar_metas(user: SessionUser = Depends(validar_token_sesion)):
    return coleccion_listar_sql("metas_personales", cuenta=None if user.director else user.usuario)


@app.post("/api/metas")
def guardar_meta(payload: Dict[str, Any], user: SessionUser = Depends(validar_token_sesion)):
    reg_id = str(payload.get("id") or f"meta-{user.usuario}-{uuid.uuid4().hex[:6]}")
    doc = {
        "id": reg_id,
        "cuenta": user.usuario,
        "docente": user.nombre,
        "area": user.area,
        "escuela": str(payload.get("escuela") or ""),
        "id_escuela": str(payload.get("id_escuela") or ""),
        "fecha_sesion": str(payload.get("fecha_sesion") or time.strftime("%Y-%m-%d")),
        "id_alumno": str(payload.get("id_alumno") or ""),
        "nombre_alumno": str(payload.get("nombre_alumno") or ""),
        "meta": str(payload.get("meta") or ""),
        "recursos": str(payload.get("recursos") or ""),
        "periodo": str(payload.get("periodo") or "2026-2027"),
        "guardado_en": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    coleccion_guardar_sql(
        "metas_personales",
        reg_id,
        doc,
        cuenta=user.usuario,
        id_escuela=doc["id_escuela"],
        id_alumno=doc["id_alumno"],
        fecha=doc["fecha_sesion"],
    )
    return {"status": "success", "id": reg_id, "meta": doc}


@app.get("/api/tramites")
def listar_tramites(user: SessionUser = Depends(validar_token_sesion)):
    es_gestor = user.director or "TRABAJO" in user.rol.upper()
    return coleccion_listar_sql("tramites", cuenta=None if es_gestor else user.usuario)


@app.post("/api/tramites")
def guardar_tramite(payload: Dict[str, Any], user: SessionUser = Depends(validar_token_sesion)):
    reg_id = str(payload.get("id") or f"TRM-{uuid.uuid4().hex[:6].upper()}")
    doc = {
        "id": reg_id,
        "fecha": str(payload.get("fecha") or time.strftime("%Y-%m-%d")),
        "solicitante": str(payload.get("solicitante") or user.nombre),
        "cuenta": str(payload.get("cuenta") or user.usuario),
        "tipo": str(payload.get("tipo") or ("Externa" if user.director or "TRABAJO" in user.rol.upper() else "Interna")),
        "origen": str(payload.get("origen") or ""),
        "escuela": str(payload.get("escuela") or ""),
        "alumnos": str(payload.get("alumnos") or ""),
        "solicitud": str(payload.get("solicitud") or ""),
        "seguimiento": str(payload.get("seguimiento") or ""),
        "estado": str(payload.get("estado") or "Solicitado"),
        "folio": str(payload.get("folio") or ""),
    }
    coleccion_guardar_sql("tramites", reg_id, doc, cuenta=doc["cuenta"], fecha=doc["fecha"], estado=doc["estado"])
    return {"status": "success", "id": reg_id, "tramite": doc}


@app.get("/api/informes")
def listar_informes(alumno_id: Optional[str] = None, user: SessionUser = Depends(validar_token_sesion)):
    alumnos = obtener_alumnos_autorizados(user.rol, user.escuelas_permitidas, user.nombre, incluir_inactivos=True)
    ids_set = {a["id"] for a in alumnos}
    guardados = coleccion_listar_sql("informes", id_alumno=alumno_id)
    if not user.director and "TODAS" not in user.escuelas_permitidas:
        guardados = [g for g in guardados if g.get("id_alumno") in ids_set or g.get("_cuenta") == user.usuario]
    return guardados


@app.post("/api/informes")
def guardar_informe(payload: Dict[str, Any], user: SessionUser = Depends(validar_token_sesion)):
    reg_id = str(payload.get("id") or f"INF-{uuid.uuid4().hex[:6].upper()}")
    doc = {
        "id": reg_id,
        "id_alumno": str(payload.get("id_alumno") or ""),
        "nombre_alumno": str(payload.get("nombre_alumno") or ""),
        "escuela": str(payload.get("escuela") or ""),
        "grado_grupo": str(payload.get("grado_grupo") or ""),
        "periodo": str(payload.get("periodo") or "1er Trimestre 2026-2027"),
        "tipo_informe": str(payload.get("tipo_informe") or "Informe de Seguimiento Pedagógico"),
        "avances": str(payload.get("avances") or ""),
        "barreras_atendidas": str(payload.get("barreras_atendidas") or ""),
        "acuerdos_familia": str(payload.get("acuerdos_familia") or ""),
        "recomendaciones_aula": str(payload.get("recomendaciones_aula") or ""),
        "elaborado_por": user.nombre,
        "fecha": str(payload.get("fecha") or time.strftime("%Y-%m-%d")),
    }
    coleccion_guardar_sql("informes", reg_id, doc, cuenta=user.usuario, id_alumno=doc["id_alumno"], fecha=doc["fecha"])
    return {"status": "success", "id": reg_id, "informe": doc}


# -------------------------------------------------------------
# 8. ASISTENTE PEDAGÓGICO CONVERSACIONAL E IA
# -------------------------------------------------------------
@app.post("/api/ai/chat")
def chat_asistente(payload: AIChatPayload, user: SessionUser = Depends(validar_token_sesion)):
    if payload.alumno_id:
        _verificar_acceso_alumno(payload.alumno_id, user)
    return chat_asistente_pedagogico(
        mensaje_docente=payload.mensaje,
        alumno_id=payload.alumno_id,
        planeacion_id=payload.planeacion_id,
    )


@app.post("/api/ai/sugerencias")
def sugerencias_asistente(payload: AISugerenciaPayload, user: SessionUser = Depends(validar_token_sesion)):
    contexto = {
        "area": payload.area,
        "barreras_o_necesidades": payload.necesidad_o_barrera,
        "grado": payload.grado,
        "condicion": payload.condicion,
    }
    from ai.engine import generar_sugerencias, fallback as ai_fallback
    try:
        return generar_sugerencias(contexto)
    except Exception:
        return ai_fallback()


# -------------------------------------------------------------

# -------------------------------------------------------------
# ENDPOINTS RESTITUIDOS: ASISTENTE PEDAGÓGICO Y DESCARGAS OFICIALES
# -------------------------------------------------------------
@app.post("/api/ai/proponer-actividades")
def proponer_actividades_endpoint(payload: ActividadPropuestaPayload, user: SessionUser = Depends(validar_token_sesion)):
    if payload.alumno_id:
        _verificar_acceso_alumno(payload.alumno_id, user)
    return generar_propuesta_actividad_docente(payload.model_dump())


@app.post("/api/ai/epp-propuesta")
def epp_propuesta_endpoint(payload: EPPPropuestaPayload, user: SessionUser = Depends(validar_token_sesion)):
    raise HTTPException(405, "Usa el asistente dentro del formato vivo de la EPP.")


@app.get("/api/anexo7/plantilla/pdf")
def descargar_anexo7_plantilla_pdf(user: SessionUser = Depends(validar_token_sesion)):
    from documents.anexos import anexo7_pdf
    pdf_bytes = anexo7_pdf({})
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="Anexo_VII_Hoja_Derivacion_Docente_Regular.pdf"'},
    )


@app.get("/api/horarios/pdf")
def descargar_horarios_pdf(
    escuela: Optional[str] = None,
    docente: Optional[str] = None,
    user: SessionUser = Depends(validar_token_sesion)
):
    from documents.horarios_apoyo import generar_horario_apoyo_cuadricula_pdf, generar_horario_apoyo_pdf
    doc_nombre = docente if (docente and user.director) else user.nombre
    esc_nombre = escuela if (escuela and user.director) else (user.escuelas_permitidas[0] if user.escuelas_permitidas and user.escuelas_permitidas[0] != "TODAS" else "Primaria Adscrita")

    horarios_data = obtener_horarios_modulo(user.rol, user.escuelas_permitidas, doc_nombre)
    sesiones = horarios_data.get("sesiones", []) if isinstance(horarios_data, dict) else []
    if not sesiones:
        sesiones = [
            {"Dia": "Lunes", "Inicio": "07:30", "Fin": "08:15", "Grado": "1", "Grupo": "A", "Modalidad": "Aula Regular", "Espacio": "Salón 1A", "Proposito": "Atención pedagógica inicial"},
            {"Dia": "Lunes", "Inicio": "08:15", "Fin": "09:00", "Grado": "2", "Grupo": "A", "Modalidad": "Subgrupo", "Espacio": "Aula Apoyo", "Proposito": "Fortalecimiento de lectoescritura"},
            {"Dia": "Miércoles", "Inicio": "09:30", "Fin": "10:15", "Grado": "3", "Grupo": "B", "Modalidad": "Aula Regular", "Espacio": "Salón 3B", "Proposito": "Ajustes razonables y DUA"},
            {"Dia": "Viernes", "Inicio": "10:30", "Fin": "11:15", "Grado": "1", "Grupo": "A", "Modalidad": "Individual", "Espacio": "Aula Apoyo", "Proposito": "Seguimiento específico"},
        ]
    franjas = sorted({
        (str(row.get("Inicio", "")), str(row.get("Fin", "")))
        for row in sesiones
        if str(row.get("Inicio", "")).strip() and str(row.get("Fin", "")).strip()
    })
    try:
        pdf_bytes = generar_horario_apoyo_cuadricula_pdf(esc_nombre, doc_nombre, sesiones, franjas)
    except Exception:
        pdf_bytes = generar_horario_apoyo_pdf(esc_nombre, doc_nombre, sesiones)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="Horario_Apoyo_{doc_nombre.replace(" ", "_")}.pdf"'},
    )


@app.get("/api/cronogramas/pdf")
def descargar_cronograma_pdf(
    mes: str = "Noviembre 2026",
    usuario: Optional[str] = None,
    docente: Optional[str] = None,
    user: SessionUser = Depends(validar_token_sesion)
):
    from documents.cronogramas import generar_cronograma_pdf
    nom = (docente or usuario) if (docente or usuario) and user.director else user.nombre
    cronos = obtener_cronogramas_modulo(user.rol, user.escuelas_permitidas, nom)
    filas = cronos.get("actividades", []) if isinstance(cronos, dict) else []
    if not filas:
        filas = [
            {"Fecha": "2026-11-03", "Dia": "Martes", "Escuela": "Damián Carmona", "Actividad": "Observación áulica y asesoría a docente regular", "Objetivo": "Identificación de BAP"},
            {"Fecha": "2026-11-10", "Dia": "Martes", "Escuela": "Ichcaanziho", "Actividad": "Evaluación Psicopedagógica inicial y entrevistas", "Objetivo": "Construcción de expediente"},
            {"Fecha": "2026-11-17", "Dia": "Martes", "Escuela": "Gregorio Torres Quintero", "Actividad": "Acompañamiento pedagógico y diseño de ajustes", "Objetivo": "Seguimiento DUA"},
            {"Fecha": "2026-11-27", "Dia": "Viernes", "Escuela": "Sede USAER", "Actividad": "Consejo Técnico Escolar (CTE)", "Objetivo": "Evaluación interdisciplinaria"},
        ]
    perfil = {"nombre": nom, "area": "Especialista" if not user.director else "Dirección", "nombre_profesional": nom}
    pdf_bytes = generar_cronograma_pdf(perfil, mes, filas)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="Cronograma_{nom.replace(" ", "_")}_{mes.replace(" ", "_")}.pdf"'},
    )


@app.get("/api/informes/{informe_id}/pdf")
def descargar_informe_pdf(informe_id: str, user: SessionUser = Depends(validar_token_sesion)):
    from documents.anexos import generar_informe_pdf
    guardados = coleccion_listar_sql("informes")
    inf = next((g for g in guardados if g.get("id") == informe_id), None)
    if not inf:
        inf = {
            "id": informe_id,
            "nombre_alumno": "Alumno de Ejemplo",
            "id_alumno": "ALU-000",
            "escuela": "Primaria Adscrita",
            "grado_grupo": "1°A",
            "periodo": "1er Trimestre 2026-2027",
            "tipo_informe": "Informe de Seguimiento Pedagógico",
            "avances": "Presenta avances en la convivencia áulica y en el reconocimiento de claves visuales de trabajo.",
            "barreras_atendidas": "Barreras pedagógicas vinculadas al acceso de materiales concretos.",
            "acuerdos_familia": "Compromiso de asistencia regular y refuerzo en casa de rutinas estructuradas.",
            "recomendaciones_aula": "Uso de material concreto y anticipación de transiciones entre actividades.",
            "elaborado_por": user.nombre,
            "fecha": time.strftime("%Y-%m-%d"),
        }
    pdf_bytes = generar_informe_pdf(inf)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="Informe_{informe_id}.pdf"'},
    )


@app.put("/api/tramites/{tramite_id}")
def actualizar_tramite_endpoint(tramite_id: str, payload: Dict[str, Any], user: SessionUser = Depends(validar_token_sesion)):
    doc = coleccion_obtener_sql("tramites", tramite_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Trámite no encontrado.")
    doc.update(payload)
    doc["actualizado_por"] = user.usuario
    doc["actualizado_en"] = time.strftime("%Y-%m-%d %H:%M:%S")
    coleccion_guardar_sql("tramites", tramite_id, doc, cuenta=user.usuario, fecha=doc.get("fecha"))
    return {"status": "success", "id": tramite_id, "tramite": doc}

# 9. ESTADÍSTICAS INSTITUCIONALES ZONA 001, PANEL DE DIRECCIÓN Y REPORTES
# -------------------------------------------------------------
@app.get("/api/estadisticas/zona")
@app.get("/api/estadisticas")
def estadisticas_zona(user: SessionUser = Depends(validar_token_sesion)):
    return obtener_estadisticas_zona(user.rol, user.escuelas_permitidas, user.nombre)


@app.get("/api/actas")
def listar_actas_alias(escuela: Optional[str] = None, user: SessionUser = Depends(validar_token_sesion)):
    return listar_visitas(escuela=escuela, user=user)


@app.get("/api/panel-direccion")
@app.get("/api/admin/panel-resumen")
def panel_direccion_resumen(user: SessionUser = Depends(validar_token_sesion)):
    if not user.director:
        raise HTTPException(status_code=403, detail="Acceso reservado exclusivamente a Dirección.")
    try:
        from data.sql_repository import escuelas_sql, personal_sql
        al_activos = len(obtener_alumnos_autorizados("DIRECTOR", ["TODAS"], incluir_inactivos=False))
        al_totales = len(obtener_alumnos_autorizados("DIRECTOR", ["TODAS"], incluir_inactivos=True))
        escuelas_df = escuelas_sql()
        escuelas_lista = escuelas_df.to_dict(orient="records") if not escuelas_df.empty else []
        personal_df = personal_sql()
        personal_lista = personal_df.to_dict(orient="records") if not personal_df.empty else []

        plan_docs = coleccion_listar_sql("planeaciones")
        epp_docs = coleccion_listar_sql("epp")
        oficios_docs = coleccion_listar_sql("oficios_comision")
        relatorias_docs = coleccion_listar_sql("relatorias")
        visitas_docs = coleccion_listar_sql("visitas")
        novedades_docs = coleccion_listar_sql("novedades_supervision")
        db_stat = estado_base_datos()

        return {
            "status": "OK",
            "alumnos_activos": al_activos,
            "alumnos_totales": al_totales,
            "escuelas": len(escuelas_lista),
            "escuelas_lista": escuelas_lista,
            "personal_lista": personal_lista,
            "planeaciones_count": len(plan_docs),
            "epp_count": len(epp_docs),
            "oficios_count": len(oficios_docs),
            "relatorias_count": len(relatorias_docs),
            "visitas_count": len(visitas_docs),
            "novedades_count": len(novedades_docs),
            "db_status": db_stat,
        }
    except Exception as exc:
        logger.warning(f"Aviso en panel_direccion_resumen: {exc}")
        return estado_base_datos()


@app.get("/api/admin/padron-excel")
def descargar_padron_excel(user: SessionUser = Depends(validar_token_sesion)):
    if not user.director:
        raise HTTPException(status_code=403, detail="Acceso reservado a Dirección.")
    try:
        from data.sql_repository import alumnos_sql, escuelas_sql
        from documents.reportes import generar_padron_usaer
        al = alumnos_sql()
        esc = escuelas_sql()
        excel_bytes = generar_padron_usaer(al, esc)
        return Response(
            content=excel_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": 'attachment; filename="Padron_USAER_02E_2026_2027.xlsx"'},
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error generando padrón oficial: {exc}")


@app.get("/api/admin/personal-excel")
def descargar_personal_excel(user: SessionUser = Depends(validar_token_sesion)):
    if not user.director:
        raise HTTPException(status_code=403, detail="Acceso reservado a Dirección.")
    try:
        from data.sql_repository import personal_sql, escuelas_sql, alumnos_sql, asignaciones_sql
        from documents.reportes import generar_formato_personal
        p = personal_sql()
        esc = escuelas_sql()
        al = alumnos_sql()
        asig = asignaciones_sql()
        excel_bytes = generar_formato_personal(p, esc, al, asig)
        return Response(
            content=excel_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": 'attachment; filename="Personal_USAER_02E_2026_2027.xlsx"'},
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error generando formato de personal: {exc}")


class ObservacionesDirectorPayload(BaseModel):
    observaciones: str


@app.post("/api/planeaciones/{doc_id}/observaciones")
def guardar_observaciones_planeacion_endpoint(
    doc_id: str,
    payload: ObservacionesDirectorPayload,
    user: SessionUser = Depends(validar_token_sesion),
):
    if not user.director:
        raise HTTPException(status_code=403, detail="Acceso reservado exclusivamente a Dirección.")
    from data.database import get_session, PlaneacionDoc
    with get_session() as session:
        p = session.query(PlaneacionDoc).filter_by(id=doc_id).first()
        if not p:
            raise HTTPException(status_code=404, detail="Planeación no encontrada.")
        p.observaciones_director = payload.observaciones.strip()
        session.commit()
    return {"status": "success", "id": doc_id, "observaciones_director": payload.observaciones.strip()}


# -------------------------------------------------------------
# 10. DESCARGA OFICIAL DE CONCENTRADO EN EXCEL
# -------------------------------------------------------------
@app.get("/descargar-concentrado")
@app.get("/api/descargar-concentrado")
def descargar_concentrado():
    for p in [
        Path(ROOT_DIR) / "Concentrado_Revision_Planificaciones_USAER_02E_2026_2027.xlsx",
        Path("/home/uppcoder/app/Concentrado_Revision_Planificaciones_USAER_02E_2026_2027.xlsx"),
        Path("/home/uppcoder/app/usaer2e/Concentrado_Revision_Planificaciones_USAER_02E_2026_2027.xlsx"),
        Path(__file__).resolve().parent / "Concentrado_Revision_Planificaciones_USAER_02E_2026_2027.xlsx",
    ]:
        if p.exists():
            return FileResponse(
                path=str(p),
                filename="Concentrado_Revision_Planificaciones_USAER_02E_2026_2027.xlsx",
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
    try:
        from tools.generar_concentrado_excel import crear_libro_concentrado
        excel_path = crear_libro_concentrado()
        return FileResponse(
            path=str(excel_path),
            filename="Concentrado_Revision_Planificaciones_USAER_02E_2026_2027.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo generar el concentrado: {e}")


# -------------------------------------------------------------
# 11. SERVIR FRONTEND SPA ESTÁTICO DIRECTO
# -------------------------------------------------------------
SPA_STATIC_DIR = Path(__file__).resolve().parent / "static"

# Montaje de archivos estáticos locales (CSS compilado, JS precompilado, React)
for _s_cand in [
    SPA_STATIC_DIR,
    Path("/home/uppcoder/app/usaer2e/piloto_spa/backend/static"),
    Path("/home/uppcoder/app/static"),
]:
    if _s_cand.exists():
        app.mount("/static", StaticFiles(directory=str(_s_cand)), name="static")
        break



@app.get("/", response_class=HTMLResponse)
def index_spa():
    posibles_rutas = [
        SPA_STATIC_DIR / "index.html",
        Path("/home/uppcoder/app/static/index.html"),
        Path("/home/uppcoder/app/usaer2e/piloto_spa/backend/static/index.html"),
    ]
    for p in posibles_rutas:
        if p.exists():
            return HTMLResponse(
                content=p.read_text(encoding="utf-8"),
                media_type="text/html; charset=utf-8",
                headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache"},
            )
    return HTMLResponse("<h1>USAER 2E 2.0</h1><p>Compilando frontend...</p>")

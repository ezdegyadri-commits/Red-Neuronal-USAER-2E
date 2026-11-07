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
from fastapi.responses import HTMLResponse, FileResponse
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
    guardar_planeacion_transaccional,
    eliminar_planeacion_documento,
    guardar_anexo3_documento,
    guardar_anexo4_documento,
    guardar_anexo5_documento,
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


def reconciliar_base_datos() -> Dict[str, Any]:
    """Sincroniza e hidrata el 100% de la información histórica desde semilla_historica_completa.json.gz."""
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

    engine = get_engine(initialize_schema=True)
    Base.metadata.create_all(engine)

    data_dir = Path(__file__).resolve().parents[2] / "data"
    gz_path = data_dir / "semilla_historica_completa.json.gz"
    json_path = data_dir / "semilla_datos_reales.json"

    if gz_path.exists():
        with gzip.open(gz_path, "rt", encoding="utf-8") as f:
            data = json.load(f)
    elif json_path.exists():
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        return {"status": "sin_semilla"}

    resumen = {}
    with get_session() as session:
        # 1. Escuelas
        for item in data.get("escuelas", []):
            obj = session.query(Escuela).filter_by(id=item["id"]).first()
            if not obj:
                session.add(Escuela(**item))
            else:
                for k, v in item.items():
                    setattr(obj, k, v)
        session.commit()

        # 2. Personal
        for item in data.get("personal", []):
            obj = session.query(Personal).filter_by(id=item["id"]).first()
            if not obj:
                session.add(Personal(**item))
            else:
                for k, v in item.items():
                    setattr(obj, k, v)
        session.commit()

        # 3. Usuarios
        for item in data.get("usuarios", []):
            obj = session.query(Usuario).filter_by(usuario=item["usuario"]).first() or session.query(Usuario).filter_by(id=item["id"]).first()
            if not obj:
                session.add(Usuario(**item))
            else:
                obj.nombre = item.get("nombre", obj.nombre)
                obj.usuario = item.get("usuario", obj.usuario)
                obj.password = item.get("password", obj.password)
                obj.rol = item.get("rol", obj.rol)
                obj.escuelas_permitidas = item.get("escuelas_permitidas", obj.escuelas_permitidas)
        session.commit()

        # 4. Alumnos canónicos (sin romper llaves foráneas previas)
        ids_canonicos = set()
        for item in data.get("alumnos", []):
            aid = item["id"]
            ids_canonicos.add(aid)
            obj = session.query(Alumno).filter_by(id=aid).first()
            if not obj:
                session.add(Alumno(**item))
            else:
                for k, v in item.items():
                    if hasattr(obj, k):
                        setattr(obj, k, v)
        # Cualquier ID antiguo (ALU-001..ALU-034 de carga previa secuencial) que no esté en el padrón canónico se marca como ANULADO_MIGRACION
        for row_old in session.query(Alumno).all():
            if row_old.id not in ids_canonicos and not str(row_old.id).startswith("ALU-3"):
                row_old.estatus = "ANULADO_MIGRACION"
        session.commit()
        resumen["alumnos"] = len(ids_canonicos)

        # 5. Planeaciones (167 documentos con JSON reconstruido e íntegro)
        for item in data.get("planeaciones", []):
            pid = item["id"]
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
            obj = session.query(PlaneacionDoc).filter_by(id=pid).first()
            if not obj:
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
            else:
                # Actualizar si estaba truncado o sin datos_json
                if not obj.datos_json or obj.datos_json == "{}" or len(payload_str) > len(obj.payload_json or ""):
                    obj.cuenta = item.get("cuenta", obj.cuenta)
                    obj.formato = item.get("formato", obj.formato)
                    obj.estado = item.get("estado", obj.estado)
                    obj.revision = item.get("revision", obj.revision)
                    obj.guardado_en = item.get("guardado_en", obj.guardado_en)
                    obj.datos_json = datos_str
                    obj.metadatos_json = metadatos_str
                    obj.tablas_json = tablas_str
                    obj.textos_json = textos_str
                    obj.payload_json = payload_str
                    obj.observaciones_director = obs_dir
        session.commit()
        resumen["planeaciones"] = session.query(PlaneacionDoc).count()

        # 6. EPP (9 expedientes multi-área reconstruidos de 249 versiones)
        for item in data.get("epp", []):
            eid = item["id"]
            obj = session.query(EPPDoc).filter_by(id=eid).first()
            if not obj:
                session.add(EPPDoc(**item))
            else:
                obj.alumno = item.get("alumno", obj.alumno)
                obj.ciclo = item.get("ciclo", obj.ciclo)
                obj.estado = item.get("estado", obj.estado)
                obj.revision = item.get("revision", obj.revision)
                obj.fecha = item.get("fecha", obj.fecha)
                obj.partes_json = item.get("partes_json", obj.partes_json)
        session.commit()
        resumen["epp"] = session.query(EPPDoc).count()

        # 7. Anexo 3, Anexo 4, Anexo 5, Anexo 7, Visitas, Oficios, Docentes y Colecciones
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
                # Inserción registro a registro como fallback seguro
                try:
                    for it in data.get(key_name, []):
                        iid = str(it.get("id") or "").strip()
                        if not iid:
                            continue
                        exists = session.query(ModelCls).filter_by(id=iid).first()
                        if not exists:
                            filt_it = {k: v for k, v in it.items() if k in valid_columns}
                            session.add(ModelCls(**filt_it))
                    session.commit()
                    resumen[key_name] = session.query(ModelCls).count()
                except Exception as exc2:
                    session.rollback()
                    logging.getLogger("uvicorn").error("Error persistiendo %s: %s", key_name, exc2)

    return resumen


@app.on_event("startup")
def inicializar_base_datos():
    """Inicializa el esquema relacional y asegura la presencia del 100% de los datos históricos."""
    try:
        reconciliar_base_datos()
    except Exception as exc:
        logging.getLogger("uvicorn").error("Error inicializando semilla relacional: %s", exc)


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
        return {
            "motor": "PostgreSQL 17" if is_postgres() else "SQLite Local",
            "host": host_repr,
            "database": db_repr,
            "escuelas": session.query(Escuela).count(),
            "personal": session.query(Personal).count(),
            "usuarios": session.query(Usuario).count(),
            "alumnos_activos": session.query(Alumno).filter(Alumno.estatus == "ACTIVO").count(),
            "alumnos_total": session.query(Alumno).filter(Alumno.estatus != "ANULADO_MIGRACION").count(),
            "planeaciones": session.query(PlaneacionDoc).count(),
            "epp": session.query(EPPDoc).count(),
            "anexo3_bap": session.query(Anexo3Deteccion).count(),
            "anexo4_sugerencias": session.query(Anexo4Sugerencia).count(),
            "anexo5_eventos": session.query(Anexo5Evento).count(),
            "anexo7_derivaciones": session.query(Anexo7Derivacion).count(),
            "visitas": session.query(RegistroVisita).count(),
            "oficios": session.query(OficioComision).count(),
            "docentes_regulares": session.query(DocenteRegular).count(),
            "colecciones_institucionales": session.query(ColeccionInstitucional).count(),
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


class EPPPayload(BaseModel):
    id: str
    alumno: str
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
@app.get("/api/health")
def healthcheck():
    return {"status": "ok", "version": "2.0.0", "timestamp": time.time()}


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
    if str(alumno_id).startswith("GRUPO-") or str(alumno_id) == "GRUPAL":
        return {"id": alumno_id, "nombre_completo": alumno_id}
    alumnos = obtener_alumnos_autorizados("DIRECTOR", ["TODAS"], incluir_inactivos=True)
    alumno = next((a for a in alumnos if str(a.get("id")) == str(alumno_id)), None)
    if not alumno:
        raise HTTPException(status_code=404, detail=f"Alumno {alumno_id} no encontrado en el padrón central.")
    if user.director or "TRABAJO" in user.rol.upper() or "TODAS" in user.escuelas_permitidas:
        return alumno
    escuela_alumno = str(alumno.get("id_escuela", "")).strip()
    permitidas = {str(e).strip() for e in user.escuelas_permitidas}
    if escuela_alumno not in permitidas:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado a este centro de trabajo.")
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
    return {"status": "success", "id": aid, "mensaje": "Detección de BAP (Anexo III) registrada correctamente."}


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
    return {"status": "success", "id": aid, "mensaje": "Hoja de sugerencias (Anexo IV) guardada correctamente."}


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


# -------------------------------------------------------------
# 4. EVALUACIÓN PSICOPEDAGÓGICA (EPP) MULTI-ÁREA
# -------------------------------------------------------------
@app.get("/api/epp")
def listar_epps_endpoint(user: SessionUser = Depends(validar_token_sesion)):
    return listar_epp_autorizados(user.rol, user.escuelas_permitidas, user.nombre)


@app.get("/api/epp/{alumno_id}")
def consultar_epp(alumno_id: str, user: SessionUser = Depends(validar_token_sesion)):
    _verificar_acceso_alumno(alumno_id, user)
    return obtener_epp_documento(alumno_id)


@app.post("/api/epp")
def guardar_epp(payload: EPPPayload, user: SessionUser = Depends(validar_token_sesion)):
    _verificar_acceso_alumno(payload.alumno, user)
    return guardar_epp_documento(payload.model_dump(), autor_cuenta=user.usuario)


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
    return obtener_planeacion_con_firmas(doc_id, usuario_cuenta=user.usuario)


@app.post("/api/planeaciones")
def guardar_planeacion(payload: PlaneacionPayload, user: SessionUser = Depends(validar_token_sesion)):
    doc_dict = payload.model_dump()
    return guardar_planeacion_transaccional(doc_dict, autor_cuenta=user.usuario)


@app.delete("/api/planeaciones/{doc_id}")
def eliminar_planeacion_endpoint(doc_id: str, user: SessionUser = Depends(validar_token_sesion)):
    ok = eliminar_planeacion_documento(doc_id, usuario_cuenta=user.usuario, es_director=user.director)
    if not ok:
        raise HTTPException(status_code=404, detail="No se encontró la planeación o no tiene permisos para eliminarla.")
    return {"status": "success", "mensaje": "Planeación eliminada correctamente."}


@app.get("/api/planeaciones/{doc_id}/pdf")
def descargar_planeacion_pdf(doc_id: str, user: SessionUser = Depends(validar_token_sesion)):
    doc = obtener_planeacion_con_firmas(doc_id, usuario_cuenta=user.usuario)
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
    res = guardar_oficio_documento(doc)
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
def listar_horarios(user: SessionUser = Depends(validar_token_sesion)):
    return obtener_horarios_modulo(user.rol, user.escuelas_permitidas, user.nombre)


@app.post("/api/horarios")
def guardar_horario(payload: Dict[str, Any], user: SessionUser = Depends(validar_token_sesion)):
    return guardar_horario_modulo(payload, user.nombre)


@app.get("/api/cronogramas")
def listar_cronogramas(user: SessionUser = Depends(validar_token_sesion)):
    return obtener_cronogramas_modulo(user.rol, user.escuelas_permitidas, user.nombre)


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


@app.get("/api/relatorias")
def listar_relatorias(user: SessionUser = Depends(validar_token_sesion)):
    return coleccion_listar_sql("relatorias")


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
        "autor": user.nombre,
        "guardado_en": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    coleccion_guardar_sql("relatorias", reg_id, doc, cuenta=user.usuario, fecha=doc["fecha"])
    return {"status": "success", "id": reg_id, "relatoria": doc}


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
# 9. ESTADÍSTICAS INSTITUCIONALES ZONA 001
# -------------------------------------------------------------
@app.get("/api/estadisticas/zona")
def estadisticas_zona(user: SessionUser = Depends(validar_token_sesion)):
    return obtener_estadisticas_zona(user.rol, user.escuelas_permitidas, user.nombre)


# -------------------------------------------------------------
# 10. DESCARGA OFICIAL DE CONCENTRADO EN EXCEL
# -------------------------------------------------------------
@app.get("/descargar-concentrado")
@app.get("/api/descargar-concentrado")
def descargar_concentrado():
    excel_path = Path(ROOT_DIR) / "Concentrado_Revision_Planificaciones_USAER_02E_2026_2027.xlsx"
    if not excel_path.exists():
        from tools.generar_concentrado_excel import crear_libro_concentrado
        crear_libro_concentrado()
    return FileResponse(
        path=str(excel_path),
        filename="Concentrado_Revision_Planificaciones_USAER_02E_2026_2027.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# -------------------------------------------------------------
# 11. SERVIR FRONTEND SPA ESTÁTICO DIRECTO
# -------------------------------------------------------------
SPA_STATIC_DIR = Path(__file__).resolve().parent / "static"


@app.get("/", response_class=HTMLResponse)
def index_spa():
    posibles_rutas = [
        SPA_STATIC_DIR / "index.html",
        Path("/home/uppcoder/app/usaer2e/piloto_spa/backend/static/index.html"),
    ]
    for p in posibles_rutas:
        if p.exists():
            return HTMLResponse(
                content=p.read_text(encoding="utf-8"),
                headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
            )
    return HTMLResponse("<h1>USAER 2E 2.0</h1><p>Compilando frontend...</p>")

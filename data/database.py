"""Capa de persistencia relacional PostgreSQL / Neon con SQLAlchemy y control de concurrencia.

Preserva el modelo canónico de USAER 2E y permite ejecución ultrarrápida sin latencias de Google Sheets.
"""
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import threading
from typing import Any, Dict, List, Optional
import uuid

import pandas as pd
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Index,
    ForeignKey,
    Integer,
    LargeBinary,
    UniqueConstraint,
    MetaData,
    String,
    Text,
    create_engine,
    inspect,
    text,
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session as SQLSession
from sqlalchemy.engine import make_url

logger = logging.getLogger(__name__)

Base = declarative_base()


class Alumno(Base):
    __tablename__ = "alumnos"

    id = Column(String(64), primary_key=True)
    nombre_completo = Column(String(255), nullable=False, index=True)
    curp = Column(String(32), index=True, default="")
    edad_1_septiembre = Column(String(16), default="")
    sexo = Column(String(16), default="")
    situacion_alumno = Column(String(64), default="")
    nivel_educativo = Column(String(64), default="")
    grado = Column(String(16), default="")
    grupo = Column(String(16), default="")
    id_escuela = Column(String(64), index=True, default="")
    maestra_apoyo = Column(String(255), default="")
    id_maestro_regular = Column(String(64), default="")
    condicion_discapacidad = Column(String(255), default="")
    estatus = Column(String(32), index=True, default="ACTIVO")
    tipo_atencion = Column(String(64), default="")
    lengua_indigena_mayahablante = Column(String(32), default="")
    afrodescendiente = Column(String(32), default="")
    migrante = Column(String(32), default="")
    nombre_escuela = Column(String(255), default="")
    turno_escuela = Column(String(32), default="")
    cct_escuela = Column(String(32), default="")
    direccion_escuela = Column(String(255), default="")
    localidad_escuela = Column(String(255), default="")
    municipio_escuela = Column(String(255), default="")
    condiciones_adicionales = Column(Text, default="")
    fecha_nacimiento = Column(String(32), default="")
    fecha_derivacion = Column(String(32), default="")
    creado_en = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    actualizado_en = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class ApoyoAlumnoSPA(Base):
    __tablename__ = "spa_apoyo_alumno"

    id = Column(String(64), primary_key=True)
    alumno_id = Column(String(64), ForeignKey("alumnos.id"), nullable=False, index=True)
    escuela_id = Column(String(64), nullable=False)
    usuario_id = Column(String(64), ForeignKey("usuarios.id"), nullable=False, index=True)
    desde = Column(String(10), nullable=False, default="")
    hasta = Column(String(10), nullable=False, default="")
    responsable = Column(String(16), nullable=False)


class ExpedienteHistoricoSPA(Base):
    __tablename__ = "spa_expedientes_historicos"

    id = Column(String(64), primary_key=True)
    alumno_id = Column(String(64), ForeignKey("alumnos.id"), nullable=False, index=True)
    escuela_id = Column(String(64), nullable=False)
    estado = Column(String(64), nullable=False)
    apertura = Column(String(32), nullable=False)
    actualizado = Column(String(32), nullable=False)


class RelacionHistoricaSPA(Base):
    __tablename__ = "spa_relaciones_historicas"

    id = Column(String(64), primary_key=True)
    expediente_id = Column(String(64), ForeignKey("spa_expedientes_historicos.id"), nullable=False, index=True)
    tipo_documento = Column(String(64), nullable=False)
    documento_id = Column(String(128), nullable=False)
    documento_origen_id = Column(String(128), nullable=False)


class Escuela(Base):
    __tablename__ = "escuelas"

    id = Column(String(64), primary_key=True)
    cct = Column(String(32), default="", index=True)
    nombre_escuela = Column(String(255), nullable=False)
    nivel = Column(String(64), default="")
    turno = Column(String(32), default="")


class Personal(Base):
    __tablename__ = "personal"

    id = Column(String(64), primary_key=True)
    nombre_completo = Column(String(255), nullable=False)
    rol = Column(String(64), default="", index=True)
    email = Column(String(128), default="", index=True)
    telefono = Column(String(32), default="")


class Asignacion(Base):
    __tablename__ = "asignaciones"

    id = Column(String(64), primary_key=True)
    id_personal = Column(String(64), index=True)
    id_escuela = Column(String(64), index=True)


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(String(64), primary_key=True)
    nombre = Column(String(255), default="")
    usuario = Column(String(128), unique=True, index=True, nullable=False)
    password = Column(String(255), default="")
    rol = Column(String(64), default="")
    escuelas_permitidas = Column(Text, default="")


class AdjuntoExpedienteSPA(Base):
    __tablename__ = "spa_adjunto_expediente"
    __table_args__ = (UniqueConstraint("alumno_id", "sha256"),)

    id = Column(String(32), primary_key=True)
    alumno_id = Column(String(64), ForeignKey("alumnos.id"), nullable=False, index=True)
    nombre = Column(String(120), nullable=False)
    bytes = Column(Integer, nullable=False)
    sha256 = Column(String(64), nullable=False)
    autor = Column(String(128), nullable=False)
    fecha = Column(DateTime(timezone=True), nullable=False)
    contenido = Column(LargeBinary, nullable=False)


class IntentoAccesoSPA(Base):
    __tablename__ = "spa_intentos_acceso"

    clave = Column(String(64), primary_key=True)
    ventana = Column(Integer, primary_key=True, index=True)
    total = Column(Integer, nullable=False)


class SesionSPA(Base):
    __tablename__ = "spa_sesiones"

    token_hash = Column(String(64), primary_key=True)
    usuario_id = Column(String(64), ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True)
    expira = Column(Integer, nullable=False, index=True)
    credencial_version = Column(String(64), nullable=False)


class CambioSPA(Base):
    __tablename__ = "spa_cambios"
    __table_args__ = (Index("ix_spa_cambios_documento", "tipo", "documento_id", "fecha"),)

    id = Column(String(32), primary_key=True)
    tipo = Column(String(32), nullable=False)
    documento_id = Column(String(128), nullable=False)
    autor = Column(String(128), nullable=False)
    revision_anterior = Column(String(64))
    revision = Column(String(64), nullable=False)
    fecha = Column(DateTime(timezone=True), nullable=False)
    contenido = Column(Text, nullable=False)


class Anexo3Deteccion(Base):
    __tablename__ = "anexo3_deteccion"

    id = Column(String(64), primary_key=True)
    fecha = Column(String(32), default="")
    id_alumno = Column(String(64), index=True)
    id_personal = Column(String(64), default="")
    bap_fisicas = Column(Text, default="")
    bap_actitudinales = Column(Text, default="")
    bap_pedagogicas = Column(Text, default="")
    bap_organizativas = Column(Text, default="")
    estatus_ia = Column(String(32), default="")
    estado = Column(String(32), default="BORRADOR")


class Anexo4Sugerencia(Base):
    __tablename__ = "anexo4_sugerencias"

    id = Column(String(64), primary_key=True)
    id_alumno = Column(String(64), index=True)
    fecha_elaboracion = Column(String(32), default="")
    ciclo_escolar = Column(String(32), default="")
    trimestre = Column(String(32), default="")
    docente_especialista = Column(String(255), default="")
    area = Column(String(64), default="")
    sugerencias_area = Column(Text, default="")
    motivo = Column(Text, default="")
    sugerencias = Column(Text, default="")
    fecha_seguimiento = Column(Text, default="")
    nivel_cumplimiento_resultados = Column(Text, default="")
    observaciones = Column(Text, default="")
    estado = Column(String(32), default="ACTIVA")


class Anexo5Evento(Base):
    __tablename__ = "anexo5_eventos"

    id = Column(String(64), primary_key=True)
    fecha = Column(String(32), default="")
    nombre_alumno = Column(String(255), default="")
    grado_grupo = Column(Text, default="")
    especialista = Column(Text, default="")
    evento = Column(Text, default="")
    estado = Column(String(32), default="ACTIVO")
    id_alumno = Column(String(64), index=True, default="")
    id_escuela = Column(String(64), default="")
    escuela = Column(String(255), default="")


class Anexo7Derivacion(Base):
    __tablename__ = "anexo7_derivacion"

    id = Column(String(64), primary_key=True)
    fecha = Column(String(32), default="")
    id_alumno = Column(String(64), index=True)
    escuela = Column(String(255), default="")
    docente_regular = Column(String(255), default="")
    fecha_nacimiento = Column(String(32), default="")
    respuestas_json = Column(Text, default="{}")
    salud = Column(Text, default="")
    seguimiento_medico = Column(Text, default="")
    aspecto_relevante = Column(Text, default="")
    elaborado_por = Column(String(255), default="")


class RegistroVisita(Base):
    __tablename__ = "registro_visitas"

    id = Column(String(64), primary_key=True)
    fecha = Column(String(32), default="")
    escuela = Column(String(255), default="")
    personal = Column(String(255), default="")
    motivo = Column(Text, default="")
    observaciones = Column(Text, default="")
    evidencia = Column(Text, default="")
    estatus = Column(String(32), default="GUARDADA")
    tipo_acta = Column(String(64), default="")
    lugar = Column(String(255), default="")


class InformeEducativoSPA(Base):
    """Informe escolar versionado; vinculado al alumno y su escuela."""
    __tablename__ = "informes_educativos_spa"

    id = Column(String(64), primary_key=True)
    id_alumno = Column(String(64), ForeignKey("alumnos.id"), nullable=False, index=True)
    id_escuela = Column(String(64), nullable=False, index=True)
    ciclo = Column(String(16), nullable=False)
    tipo = Column(String(64), nullable=False, default="seguimiento")
    titulo = Column(String(255), nullable=False)
    contenido_json = Column(Text, nullable=False, default="{}")
    autor = Column(String(128), nullable=False)
    id_autor = Column(String(64), nullable=False)
    revision = Column(String(64), nullable=False)
    creado_en = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    actualizado_en = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                            onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class OficioComision(Base):
    __tablename__ = "oficios_comision"

    id = Column(String(64), primary_key=True)
    folio = Column(String(64), default="", index=True)
    clave_operacion = Column(Text, default="")
    fecha_emision = Column(String(32), default="")
    fecha_comision = Column(String(32), default="")
    escuela = Column(String(255), default="")
    id_escuela = Column(String(64), default="")
    maestra_apoyo = Column(String(255), default="")
    director_escuela = Column(String(255), default="")
    asunto = Column(Text, default="")
    destino = Column(String(255), default="")
    horario = Column(String(64), default="")
    estado = Column(String(32), default="ACTIVO")


class ConfiguracionOficio(Base):
    __tablename__ = "configuracion_oficios"

    id = Column(String(64), primary_key=True)
    fecha_comision = Column(String(32), default="")
    asunto = Column(Text, default="")
    destino = Column(String(255), default="")
    horario = Column(String(64), default="")
    actualizado_por = Column(String(255), default="")
    actualizado_en = Column(String(32), default="")


class DocenteRegular(Base):
    __tablename__ = "docentes_regulares"

    id = Column(String(64), primary_key=True)
    fecha_registro = Column(String(32), default="")
    ciclo_escolar = Column(String(32), default="")
    id_escuela = Column(String(64), index=True, default="")
    nombre_escuela = Column(String(255), default="")
    turno = Column(String(32), default="")
    grado = Column(String(16), default="")
    grupo = Column(String(16), default="")
    nombre_docente = Column(String(255), default="")
    telefono = Column(String(32), default="")
    email = Column(String(128), default="")
    observaciones = Column(Text, default="")


class PlaneacionDoc(Base):
    __tablename__ = "planeaciones"

    id = Column(String(64), primary_key=True)
    cuenta = Column(String(128), index=True)
    formato = Column(String(32), default="XXIII")
    estado = Column(String(32), default="BORRADOR", index=True)
    revision = Column(String(64), default="")
    guardado_en = Column(String(32), default="")
    datos_json = Column(Text, default="{}")
    metadatos_json = Column(Text, default="{}")
    tablas_json = Column(Text, default="{}")
    textos_json = Column(Text, default="{}")
    payload_json = Column(Text, default="{}")
    observaciones_director = Column(Text, default="")
    actualizado_en = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), index=True)


class PlaneacionGrupoSPA(Base):
    __tablename__ = "spa_planeacion_grupos"

    escuela = Column(String(64), primary_key=True)
    grado = Column(String(24), primary_key=True)
    grupo = Column(String(24), primary_key=True)
    ciclo = Column(String(24), primary_key=True)
    planeacion_id = Column(String(64), ForeignKey("planeaciones.id", ondelete="RESTRICT"),
                           nullable=False, unique=True)


class PlaneacionAlumnoSPA(Base):
    __tablename__ = "spa_planeacion_alumnos"

    planeacion_id = Column(String(64), ForeignKey("planeaciones.id", ondelete="CASCADE"), primary_key=True)
    alumno_id = Column(String(64), ForeignKey("alumnos.id"), primary_key=True, index=True)


class EPPDoc(Base):
    __tablename__ = "epp_documentos"

    id = Column(String(64), primary_key=True)
    alumno = Column(String(64), index=True)
    ciclo = Column(String(32), index=True)
    estado = Column(String(32), default="BORRADOR", index=True)
    revision = Column(String(64), default="")
    fecha = Column(String(32), default="")
    partes_json = Column(Text, default="{}")
    actualizado_en = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), index=True)


class BloqueoConcurrencia(Base):
    __tablename__ = "bloqueos_concurrencia"

    clave = Column(String(128), primary_key=True)
    token = Column(String(128), nullable=False)
    adquirido_en = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expira_en = Column(DateTime, nullable=False)
    namespace = Column(String(64), default="usaer2e")


_ENGINE = None
_SESSION_FACTORY = None
_LOCK_DB = threading.Lock()
_SCHEMA_READY = False

class SafeSession(SQLSession):
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            if exc_type is not None:self.rollback()
        finally:
            self.close()
        return False


def get_database_url() -> str:
    url = (
        os.getenv("DATABASE_URL")
        or os.getenv("NEON_DATABASE_URL")
        or os.getenv("POSTGRES_URL")
        or os.getenv("SUPABASE_DB_URL")
        or ""
    )
    if not url:
        try:
            import streamlit as st
            url = st.secrets.get("DATABASE_URL") or st.secrets.get("NEON_DATABASE_URL") or ""
        except Exception:
            pass
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if not url:
        # Fallback local SQLite seguro si no hay PostgreSQL configurado
        local_db = Path(__file__).resolve().parents[1] / "data" / "usaer_local.db"
        url = f"sqlite:///{local_db}"
    return url


def is_postgres() -> bool:
    url = get_database_url()
    return make_url(url).drivername.split("+",1)[0] == "postgresql"


def get_engine(*, initialize_schema=True):
    global _ENGINE, _SESSION_FACTORY, _SCHEMA_READY
    with _LOCK_DB:
        if _ENGINE is None:
            db_url = get_database_url()
            if is_postgres():
                url = make_url(db_url)
                if os.getenv("USAER_SPA_MODE") != "uppcoder" or url.drivername != "postgresql+psycopg":
                    url = url.set(drivername="postgresql+psycopg2")
                db_url = url.render_as_string(hide_password=False)
            from sqlalchemy.pool import NullPool
            if db_url.startswith("sqlite"):
                _ENGINE = create_engine(db_url, connect_args={"check_same_thread": False}, echo=False, hide_parameters=True)
            elif os.getenv("USAER_SPA_MODE") in {"postgres-synthetic", "postgres-container-synthetic", "uppcoder"} and os.getenv("USAER_SPA_ROLE") == "runtime":
                args = {"connect_timeout": 5}
                if os.getenv("USAER_SPA_MODE") == "uppcoder":
                    args["options"] = "-c search_path=public"
                _ENGINE = create_engine(db_url, connect_args=args,
                                        pool_size=12, max_overflow=4, pool_timeout=10,
                                        pool_pre_ping=True, echo=False, hide_parameters=True)
            else:
                _ENGINE = create_engine(db_url, connect_args={"connect_timeout": 5}, poolclass=NullPool, pool_pre_ping=True, echo=False, hide_parameters=True)
            _SESSION_FACTORY = sessionmaker(bind=_ENGINE, class_=SafeSession, autoflush=False, expire_on_commit=False)
        if initialize_schema and not _SCHEMA_READY:
            if os.getenv("USAER_SPA_MODE") in {"postgres-synthetic", "postgres-container-synthetic", "uppcoder"} and os.getenv("USAER_SPA_ROLE") == "runtime":
                faltantes = set(Base.metadata.tables) - set(inspect(_ENGINE).get_table_names())
                if faltantes:
                    raise RuntimeError("El esquema del piloto requiere una migración previa.")
            else:
                Base.metadata.create_all(_ENGINE)
            _SCHEMA_READY=True
        return _ENGINE


def get_session(*, initialize_schema=True):
    get_engine(initialize_schema=initialize_schema)
    return _SESSION_FACTORY()


# Control de bloqueos de concurrencia de Fase 12
def adquirir_bloqueo(clave: str, token: str, segundos: int = 30, namespace: str = "usaer2e") -> bool:
    """Bloqueo transaccional de concurrencia optimizado para Neon/PostgreSQL."""
    get_engine()
    ahora = datetime.now(timezone.utc)
    from datetime import timedelta
    expira = ahora + timedelta(seconds=segundos)
    with get_session() as session:
        try:
            bloqueo = session.query(BloqueoConcurrencia).filter_by(clave=clave).first()
            if bloqueo is None:
                session.add(BloqueoConcurrencia(clave=clave, token=token, adquirido_en=ahora, expira_en=expira, namespace=namespace))
                session.commit()
                return True
            # Si expiró o pertenece al mismo token
            if bloqueo.token == token or (bloqueo.expira_en and bloqueo.expira_en < ahora):
                bloqueo.token = token
                bloqueo.adquirido_en = ahora
                bloqueo.expira_en = expira
                session.commit()
                return True
            return False
        except Exception as exc:
            logger.warning("Error al adquirir bloqueo: %s", exc)
            session.rollback()
            return False


def liberar_bloqueo(clave: str, token: str) -> bool:
    """Libera el bloqueo de concurrencia si coincide el token del poseedor."""
    get_engine()
    with get_session() as session:
        try:
            bloqueo = session.query(BloqueoConcurrencia).filter_by(clave=clave, token=token).first()
            if bloqueo:
                session.delete(bloqueo)
                session.commit()
                return True
            return False
        except Exception as exc:
            logger.warning("Error al liberar bloqueo: %s", exc)
            session.rollback()
            return False

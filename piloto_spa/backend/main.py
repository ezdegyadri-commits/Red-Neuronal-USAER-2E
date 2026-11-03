"""FastAPI Backend Integral para USAER 2E 2.0.

Capa de servicios RESTful de alta velocidad para la versión SPA desacoplada de Streamlit.
Implementa autenticación con tokens seguros, control de acceso basado en roles (RBAC),
persistencia relacional, EPP, expedientes, planeaciones (Formatos XXIII, XXV, XIX, XX),
asistente pedagógico conversacional, anexos oficiales, visitas, oficios e indicadores de la Zona 001.
"""
from __future__ import annotations

import io
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
import time

# Configurar path raíz para módulos canónicos
ROOT_DIR = str(Path(__file__).resolve().parents[2])
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from fastapi import FastAPI, HTTPException, Depends, Header, Query, status, Response, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
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
    obtener_epp_documento,
    guardar_epp_documento,
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
    chat_asistente_pedagogico,
    obtener_estadisticas_zona,
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

# -------------------------------------------------------------
# MODELOS PYDANTIC PARA CONTRATOS DE ENTRADA Y SALIDA
# -------------------------------------------------------------

class LoginPayload(BaseModel):
    usuario: str
    password: str

class LoginResponse(BaseModel):
    token: str
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
# 1. AUTENTICACIÓN Y SESIÓN (SEGURA Y CON TOKENS)
# -------------------------------------------------------------

@app.get("/api/health")
def healthcheck():
    """Monitoreo de estado y keep-alive de disponibilidad."""
    return {"status": "ok", "version": "2.0.0", "timestamp": time.time()}


@app.post("/api/auth/login", response_model=LoginResponse)
def login_endpoint(payload: LoginPayload):
    """Autentica credenciales y emite un token de sesión criptográfico."""
    user = autenticar_usuario(payload.usuario, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos."
        )
    token = emitir_token_sesion(user)
    return LoginResponse(token=token, user=user)


@app.get("/api/me", response_model=SessionUser)
def obtener_perfil_actual(user: SessionUser = Depends(validar_token_sesion)):
    """Retorna los datos y alcance de autorización del usuario autenticado."""
    return user


@app.post("/api/auth/logout")
def logout_endpoint(authorization: Optional[str] = Header(None)):
    """Invalida la sesión actual de forma inmediata en el servidor."""
    cerrar_sesion(authorization)
    return {"status": "success", "mensaje": "Sesión cerrada correctamente."}

# -------------------------------------------------------------
# 2. ESCUELAS Y PADRÓN DE ALUMNOS (RBAC)
# -------------------------------------------------------------

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
    if escuela:
        escuela_norm = escuela.strip().lower()
        alumnos = [a for a in alumnos if escuela_norm in str(a.get("escuela", "")).lower() or escuela_norm in str(a.get("id_escuela", "")).lower()]
    return alumnos


@app.post("/api/alumnos")
def crear_alumno(payload: AlumnoPayload, user: SessionUser = Depends(validar_token_sesion)):
    """Registra un nuevo alumno en la base de datos."""
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
    """Edita un alumno existente validando permisos de escuela."""
    alumnos = obtener_alumnos_autorizados(user.rol, user.escuelas_permitidas)
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
    """Exporta el padrón autorizado en formato CSV para respaldos."""
    alumnos = obtener_alumnos_autorizados(user.rol, user.escuelas_permitidas)
    df = pd.DataFrame(alumnos)
    csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="Padron_Alumnos_USAER_2E.csv"'}
    )

# -------------------------------------------------------------
# 3. EXPEDIENTES Y SEGUIMIENTO EDUCATIVO
# -------------------------------------------------------------

@app.get("/api/expedientes/{alumno_id}")
def ver_expediente(alumno_id: str, user: SessionUser = Depends(validar_token_sesion)):
    """Expediente integral (BAP, sugerencias, eventos cronológicos, derivación, EPP)."""
    return obtener_expediente_completo(alumno_id)

# -------------------------------------------------------------
# 4. EVALUACIÓN PSICOPEDAGÓGICA (EPP) MULTI-ÁREA
# -------------------------------------------------------------

@app.get("/api/epp/{alumno_id}")
def consultar_epp(alumno_id: str, user: SessionUser = Depends(validar_token_sesion)):
    """Recupera el informe EPP con sus cuatro áreas integradas."""
    return obtener_epp_documento(alumno_id)


@app.post("/api/epp")
def guardar_epp(payload: EPPPayload, user: SessionUser = Depends(validar_token_sesion)):
    """Guarda o actualiza el informe EPP con hash de revisión atómico."""
    return guardar_epp_documento(payload.model_dump(), autor_cuenta=user.usuario)

# -------------------------------------------------------------
# 5. PLANEACIÓN PEDAGÓGICA (FORMATOS XXIII, XXV, XIX, XX)
# -------------------------------------------------------------

@app.get("/api/planeaciones")
def listar_planeaciones(user: SessionUser = Depends(validar_token_sesion)):
    """Lista resumida de planeaciones con límite duro para el usuario activo."""
    from data.sql_repository import planeaciones_resumen_sql
    return planeaciones_resumen_sql(cuenta=user.usuario, es_director=user.director)


@app.get("/api/planeaciones/{doc_id}")
def obtener_planeacion(doc_id: str, user: SessionUser = Depends(validar_token_sesion)):
    """Documento de planeación completo con cálculo oficial de firmas."""
    return obtener_planeacion_con_firmas(doc_id, usuario_cuenta=user.usuario)


@app.post("/api/planeaciones")
def guardar_planeacion(payload: PlaneacionPayload, user: SessionUser = Depends(validar_token_sesion)):
    """Guarda planeación con control de versiones y verificación de concurrencia."""
    doc_dict = payload.model_dump()
    return guardar_planeacion_transaccional(doc_dict, autor_cuenta=user.usuario)


@app.delete("/api/planeaciones/{doc_id}")
def eliminar_planeacion_endpoint(doc_id: str, user: SessionUser = Depends(validar_token_sesion)):
    """Elimina una planeación tras confirmación explícita del docente."""
    ok = eliminar_planeacion_documento(doc_id, usuario_cuenta=user.usuario, es_director=user.director)
    if not ok:
        raise HTTPException(status_code=404, detail="No se encontró la planeación o no tiene permisos para eliminarla.")
    return {"status": "success", "mensaje": "Planeación eliminada correctamente."}


@app.get("/api/planeaciones/{doc_id}/pdf")
def descargar_planeacion_pdf(doc_id: str, user: SessionUser = Depends(validar_token_sesion)):
    """Genera la exportación oficial en PDF con los sellos y firmas de la Zona 001."""
    doc = obtener_planeacion_con_firmas(doc_id, usuario_cuenta=user.usuario)
    try:
        pdf_bytes = generar_pdf_planeacion(doc)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generando PDF de planeación: {exc}"
        )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="Planeacion_{doc_id}.pdf"'}
    )

# -------------------------------------------------------------
# 6. ANEXOS III, IV, V Y VII (BAP, SUGERENCIAS, EVENTOS, DERIVACIÓN)
# -------------------------------------------------------------

@app.post("/api/anexo3")
def crear_anexo3(payload: Anexo3Payload, user: SessionUser = Depends(validar_token_sesion)):
    """Guarda registro de detección de BAP (Anexo III)."""
    doc = {
        "Fecha": payload.fecha or time.strftime("%Y-%m-%d"),
        "ID_Alumno": payload.id_alumno,
        "ID_Personal": user.id_usuario,
        "BAP_Fisicas": payload.bap_fisicas,
        "BAP_Actitudinales": payload.bap_actitudinales,
        "BAP_Pedagogicas": payload.bap_pedagogicas,
        "BAP_Organizativas": payload.bap_organizativas,
        "Estatus_IA": "VALIDADO",
        "Estado": "ACTIVO"
    }
    aid = guardar_anexo3_documento(doc)
    return {"status": "success", "id": aid, "mensaje": "BAP registrada correctamente."}


@app.post("/api/anexo4")
def crear_anexo4(payload: Anexo4Payload, user: SessionUser = Depends(validar_token_sesion)):
    """Guarda sugerencias técnico pedagógicas a docente regular (Anexo IV)."""
    doc = {
        "ID_Alumno": payload.id_alumno,
        "Fecha_Elaboracion": payload.fecha_elaboracion or time.strftime("%Y-%m-%d"),
        "Ciclo_Escolar": payload.ciclo_escolar,
        "Trimestre": payload.trimestre,
        "Docente_Especialista": payload.docente_especialista or user.nombre,
        "Area": payload.area,
        "Sugerencias": payload.sugerencias,
        "Motivo": payload.motivo,
        "Fecha_Seguimiento": payload.fecha_seguimiento,
        "Nivel_Cumplimiento_Resultados": payload.nivel_cumplimiento_resultados,
        "Estado": "ACTIVA"
    }
    aid = guardar_anexo4_documento(doc)
    return {"status": "success", "id": aid, "mensaje": "Sugerencias guardadas correctamente."}


@app.post("/api/anexo5")
def crear_anexo5(payload: Anexo5Payload, user: SessionUser = Depends(validar_token_sesion)):
    """Guarda hoja de evento significativo (Anexo V)."""
    doc = {
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
    return {"status": "success", "id": aid, "mensaje": "Evento significativo registrado correctamente."}

# -------------------------------------------------------------
# 7. ACTAS DE VISITA Y OFICIOS DE COMISIÓN
# -------------------------------------------------------------

@app.get("/api/visitas")
def listar_visitas(escuela: Optional[str] = None, user: SessionUser = Depends(validar_token_sesion)):
    """Consulta actas de visitas de acompañamiento técnico."""
    return obtener_visitas_documentos(escuela)


@app.post("/api/visitas")
def crear_visita(payload: VisitaPayload, user: SessionUser = Depends(validar_token_sesion)):
    """Registra acta de visita técnica."""
    doc = {
        "Fecha": payload.fecha or time.strftime("%Y-%m-%d"),
        "Escuela": payload.escuela,
        "Personal": payload.personal or user.nombre,
        "Motivo": payload.motivo,
        "Observaciones": payload.observaciones,
        "Tipo_Acta": payload.tipo_acta,
        "Lugar": payload.lugar,
        "Estatus": "GUARDADA"
    }
    vid = guardar_visita_documento(doc)
    return {"status": "success", "id": vid, "mensaje": "Acta de visita guardada correctamente."}


@app.get("/api/oficios")
def listar_oficios(escuela: Optional[str] = None, user: SessionUser = Depends(validar_token_sesion)):
    """Consulta oficios de comisión oficiales de la zona."""
    return obtener_oficios_documentos(escuela)


@app.post("/api/oficios")
def crear_oficio(payload: OficioPayload, user: SessionUser = Depends(validar_token_sesion)):
    """Emite un oficio de comisión oficial."""
    doc = {
        "Folio": payload.folio or f"OF-2026-{int(time.time())%1000:03d}",
        "Clave_Operacion": payload.clave_operacion,
        "Fecha_Emision": payload.fecha_emision or time.strftime("%Y-%m-%d"),
        "Fecha_Comision": payload.fecha_comision,
        "Escuela": payload.escuela,
        "ID_Escuela": payload.id_escuela,
        "Maestra_Apoyo": payload.maestra_apoyo,
        "Director_Escuela": payload.director_escuela,
        "Asunto": payload.asunto,
        "Destino": payload.destino,
        "Horario": payload.horario,
        "Estado": "ACTIVO"
    }
    oid = guardar_oficio_documento(doc)
    return {"status": "success", "id": oid, "mensaje": "Oficio de comisión emitido correctamente."}

# -------------------------------------------------------------
# 8. ASISTENTE PEDAGÓGICO CONVERSACIONAL E IA
# -------------------------------------------------------------

@app.post("/api/ai/chat")
def chat_asistente(payload: AIChatPayload, user: SessionUser = Depends(validar_token_sesion)):
    """Asistente conversacional con recuperación contextual del alumno y reglas Zona 001."""
    return chat_asistente_pedagogico(
        mensaje_docente=payload.mensaje,
        alumno_id=payload.alumno_id,
        planeacion_id=payload.planeacion_id
    )


@app.post("/api/ai/sugerencias")
def sugerencias_asistente(payload: AISugerenciaPayload, user: SessionUser = Depends(validar_token_sesion)):
    """Generación directa de ajustes razonables y descriptores observables."""
    contexto = {
        "area": payload.area,
        "barreras_o_necesidades": payload.necesidad_o_barrera,
        "grado": payload.grado,
        "condicion": payload.condicion
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
    """Métricas globales de la zona escolar para el panel directivo."""
    return obtener_estadisticas_zona()

# -------------------------------------------------------------
# 10. SERVIR FRONTEND SPA ESTÁTICO DIRECTO
# -------------------------------------------------------------

SPA_STATIC_DIR = Path(__file__).resolve().parent / "static"
INDEX_HTML = SPA_STATIC_DIR / "index.html"

@app.get("/", response_class=HTMLResponse)
def index_spa():
    """Punto de entrada de la SPA React 18."""
    if INDEX_HTML.exists():
        return HTMLResponse(content=INDEX_HTML.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>USAER 2E 2.0</h1><p>Compilando frontend...</p>")

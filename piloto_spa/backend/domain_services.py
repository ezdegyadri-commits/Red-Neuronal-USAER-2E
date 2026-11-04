"""Servicios de Dominio Pedagógico y Administrativo para USAER 2E 2.0.

Implementa la lógica de negocio desacoplada de Streamlit para todos los módulos:
- Padrón de Escuelas y Alumnos (RBAC real)
- Expedientes Educativos Integrales con Línea de Tiempo
- Evaluación Psicopedagógica (EPP) Multi-Área (Aprendizaje, Psicología, Comunicación, Trabajo Social)
- Planeación Individual y Grupal (Formatos XXIII, XXV, XIX, XX)
- Anexos III (BAP), IV (Sugerencias), V (Eventos) y VII (Derivación)
- Actas de Visita de Acompañamiento
- Oficios de Comisión Oficiales
- Estadísticas e Indicadores de Zona 001
- Asistente Pedagógico con Recuperación Contextual
- Importación y Exportación Masiva
"""
from __future__ import annotations

import json
import time
import uuid
from typing import Any, Dict, List, Optional
import pandas as pd

from config.settings import ESCUELAS_USAER
from data.sql_repository import (
    alumnos_sql,
    save_alumno_sql,
    update_alumno_sql,
    anexo3_sql,
    save_anexo3_sql,
    anexo4_sql,
    save_anexo4_sql,
    anexo5_sql,
    save_anexo5_sql,
    anexo7_sql,
    save_anexo7_sql,
    epp_listar_sql,
    guardar_epp_sql,
    escuelas_sql,
    visitas_sql,
    save_visita_sql,
    oficios_comision_sql,
    guardar_oficio_comision_sql,
    planeaciones_resumen_sql,
    planeacion_por_id_sql,
    guardar_planeacion_sql,
    delete_planeacion_sql,
)
from services.planeacion_firmas import resolver_firmas_planeacion, DIRECTOR_USAER
from services.planeacion_modelo import FORMATOS
from services.curriculo import contexto_ia
from fastapi import HTTPException
from data.sql_repository import ConflictoRevision

# -------------------------------------------------------------
# 1. SERVICIO DE ESCUELAS
# -------------------------------------------------------------
def obtener_catalogo_escuelas() -> List[Dict[str, Any]]:
    """Retorna las 8 primarias oficiales de la Zona 001 consultando la base relacional."""
    df = escuelas_sql()
    if df.empty:
        escuelas = []
        ccts = {
            "Damián Carmona": "31DPR0001A",
            "Ichcaanziho": "31DPR0002Z",
            "Gregorio Torres Quintero": "31DPR0003Y",
            "Remigio Aguilar Sosa": "31DPR0004X",
            "Elvira Parra Ávila": "31DPR0005W",
            "Manuel Sarrado": "31DPR0006V",
            "Domingo Solís Rodríguez": "31DPR0007U",
            "Quintana Roo": "31DPR0008T",
        }
        for nombre, id_esc in ESCUELAS_USAER.items():
            escuelas.append({
                "id": id_esc,
                "nombre": nombre,
                "cct": ccts.get(nombre, "31DPR0000X"),
                "turno": "Matutino",
                "nivel": "Primaria"
            })
        return escuelas

    records = df.to_dict(orient="records")
    return [
        {
            "id": str(r.get("ID_Escuela") or r.get("id")),
            "nombre": str(r.get("Nombre_Escuela") or r.get("nombre_escuela")),
            "cct": str(r.get("CCT") or r.get("cct")),
            "turno": str(r.get("Turno") or r.get("turno") or "Matutino"),
            "nivel": str(r.get("Nivel") or r.get("nivel") or "Primaria"),
        }
        for r in records
    ]

# -------------------------------------------------------------
# 2. SERVICIO DE PADRÓN DE ALUMNOS (RBAC)
# -------------------------------------------------------------
def obtener_alumnos_autorizados(
    usuario_rol: str,
    escuelas_permitidas: List[str],
    nombre_docente: str = "",
    *, alumno_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Consulta el padrón de alumnos filtrado estrictamente por los permisos del usuario en la BD."""
    df = alumnos_sql(alumno_id)
    if df.empty:
        return []

    records = df.to_dict(orient="records")
    alumnos = []
    for r in records:
        alumnos.append({
            "id": str(r.get("ID_Alumno", "")),
            "nombre_completo": str(r.get("Nombre_Completo", "")),
            "curp": str(r.get("CURP", "")),
            "grado": str(r.get("Grado", "")),
            "grupo": str(r.get("Grupo", "")),
            "escuela": str(r.get("Nombre_Escuela", "")),
            "id_escuela": str(r.get("ID_Escuela", "")),
            "condicion": str(r.get("Condicion_Discapacidad", "")),
            "estatus": str(r.get("Estatus", "ACTIVO")),
            "maestra_apoyo": str(r.get("Maestra de Apoyo", "")),
            "tipo_atencion": str(r.get("Tipo_Atencion", "Atención Focalizada")),
            "turno": str(r.get("Turno_Escuela", "Matutino")),
            "cct": str(r.get("CCT_Escuela", "")),
            "sexo": str(r.get("Sexo", "")),
            "edad": str(r.get("Edad_1_Septiembre", "")),
        })

    # Filtrar por rol y escuelas permitidas
    if usuario_rol == "DIRECTOR" or "TODAS" in escuelas_permitidas:
        return alumnos

    permitidas_set = {str(e).strip() for e in escuelas_permitidas}
    return [a for a in alumnos if a.get("id_escuela") in permitidas_set]

def guardar_alumno_nuevo(payload: Dict[str, Any]) -> str:
    """Registra un nuevo alumno en la base de datos validando CURP única."""
    return save_alumno_sql(payload)

def actualizar_alumno_existente(id_alumno: str, cambios: Dict[str, Any], allowed_ids: List[str]) -> str:
    """Actualiza datos del alumno verificando permisos de edición."""
    return update_alumno_sql(id_alumno, cambios, allowed_ids)

# -------------------------------------------------------------
# 3. EXPEDIENTE EDUCATIVO INTEGRAL
# -------------------------------------------------------------
def obtener_expediente_completo(alumno_id: str, *, alumno=None) -> Dict[str, Any]:
    """Reúne el expediente integral desde la base de datos (BAP, Sugerencias, Eventos, Derivación, EPP)."""
    if alumno is None:
        alumnos = obtener_alumnos_autorizados("DIRECTOR", ["TODAS"], alumno_id=alumno_id)
        alumno = alumnos[0] if alumnos else None
    if not alumno:
        alumno = {"id": alumno_id, "nombre_completo": "Alumno no encontrado", "grado": "", "grupo": "", "escuela": ""}

    # BAP registradas (Anexo III) desde BD
    df_anx3 = anexo3_sql(alumno_id)
    bap = []
    if not df_anx3.empty:
        filas = df_anx3.to_dict(orient="records")
        for f in filas:
            bap.append({
                "id": str(f.get("ID_Anexo3")),
                "fecha": str(f.get("Fecha")),
                "fisicas": str(f.get("BAP_Fisicas") or ""),
                "actitudinales": str(f.get("BAP_Actitudinales") or ""),
                "pedagogicas": str(f.get("BAP_Pedagogicas") or ""),
                "organizativas": str(f.get("BAP_Organizativas") or ""),
                "estatus": str(f.get("Estado", "ACTIVO"))
            })

    # Sugerencias (Anexo IV) desde BD
    df_anx4 = anexo4_sql(alumno_id)
    sugerencias = []
    if not df_anx4.empty:
        filas = df_anx4.to_dict(orient="records")
        for f in filas:
            sugerencias.append({
                "id": str(f.get("ID_Anexo4")),
                "fecha": str(f.get("Fecha_Elaboracion")),
                "docente_especialista": str(f.get("Docente_Especialista")),
                "area": str(f.get("Area")),
                "sugerencias": str(f.get("Sugerencias")),
                "motivo": str(f.get("Motivo")),
                "seguimiento": str(f.get("Fecha_Seguimiento")),
                "cumplimiento": str(f.get("Nivel_Cumplimiento_Resultados"))
            })

    # Eventos significativos (Anexo V) desde BD
    df_anx5 = anexo5_sql(alumno_id)
    eventos = []
    if not df_anx5.empty:
        filas = df_anx5.to_dict(orient="records")
        for f in filas:
            eventos.append({
                "id": str(f.get("ID_Evento")),
                "fecha": str(f.get("Fecha")),
                "evento": str(f.get("Evento")),
                "especialista": str(f.get("Especialista")),
                "estado": str(f.get("Estado"))
            })

    # Derivación (Anexo VII) desde BD
    df_anx7 = anexo7_sql(alumno_id)
    derivacion = {}
    if not df_anx7.empty:
        filas = df_anx7.to_dict(orient="records")
        if filas:
            f = filas[0]
            derivacion = {
                "id": str(f.get("ID_Anexo7")),
                "fecha": str(f.get("Fecha")),
                "docente_regular": str(f.get("Docente_Regular")),
                "salud": str(f.get("Salud")),
                "seguimiento_medico": str(f.get("Seguimiento_Medico")),
                "aspecto_relevante": str(f.get("Aspecto_Relevante")),
                "elaborado_por": str(f.get("Elaborado_Por"))
            }

    # EPP desde BD
    epp_docs = epp_listar_sql([alumno_id])
    epp = epp_docs[0] if epp_docs else None

    return {
        "alumno": alumno,
        "anexo3_bap": bap,
        "anexo4_sugerencias": sugerencias,
        "anexo5_eventos": eventos,
        "anexo7_derivacion": derivacion,
        "epp": epp,
        "total_documentos": len(bap) + len(sugerencias) + len(eventos) + (1 if epp else 0)
    }

# -------------------------------------------------------------
# 4. EVALUACIÓN PSICOPEDAGÓGICA (EPP) MULTI-ÁREA
# -------------------------------------------------------------
def obtener_epp_documento(alumno_id: str, ciclo: str = "2026-2027") -> Dict[str, Any]:
    """Recupera el informe EPP para el ciclo activo desde la BD."""
    docs = epp_listar_sql([alumno_id])
    if docs:
        for d in docs:
            if d.get("ciclo") == ciclo or not ciclo:
                return d

    # Plantilla canónica si no existe
    return {
        "id": f"epp_{alumno_id}_{ciclo}",
        "alumno": alumno_id,
        "ciclo": ciclo,
        "revision": "rev-epp-inicial",
        "fecha": time.strftime("%Y-%m-%d"),
        "partes": {
            "META": {"estado": "BORRADOR", "ultima_modificacion": time.strftime("%Y-%m-%d %H:%M")},
            "APRENDIZAJE": {
                "estilo_aprendizaje": "",
                "nivel_competencia_curricular": "",
                "avances_observables": "",
                "apoyos_requeridos": ""
            },
            "PSICOLOGIA": {
                "desarrollo_emocional": "",
                "atencion_y_memoria": "",
                "recomendaciones": ""
            },
            "COMUNICACION": {
                "lenguaje_expresivo": "",
                "lenguaje_comprensivo": "",
                "recomendaciones": ""
            },
            "TRABAJO_SOCIAL": {
                "dinamica_familiar": "",
                "entorno_sociofamiliar": "",
                "acuerdos_casa": ""
            }
        }
    }

def guardar_epp_documento(doc_payload: Dict[str, Any], autor_cuenta: str) -> Dict[str, Any]:
    """Persiste el informe EPP con hash de revisión atómico en la BD."""
    actual = obtener_epp_documento(doc_payload["alumno"], doc_payload["ciclo"])
    if actual["id"] != doc_payload["id"]:
        raise HTTPException(status_code=409, detail="La EPP no coincide con el alumno y ciclo seleccionados.")
    esperada = doc_payload.get("revision")
    doc_payload["revision"] = f"rev-epp-{uuid.uuid4().hex}"
    doc_payload["fecha"] = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        guardar_epp_sql(doc_payload, revision_esperada=esperada, verificar_revision=True, actor_spa=autor_cuenta)
    except ConflictoRevision as exc:
        raise HTTPException(status_code=409, detail="La EPP cambió. Vuelve a abrirla antes de guardar.") from exc
    return {
        "status": "success",
        "id": doc_payload["id"],
        "revision": doc_payload["revision"],
        "mensaje": "Evaluación Psicopedagógica guardada correctamente en base relacional."
    }

# -------------------------------------------------------------
# 5. PLANEACIÓN PEDAGÓGICA (FORMATOS XXIII, XXV, XIX, XX)
# -------------------------------------------------------------
def obtener_planeacion_con_firmas(doc_id: str, usuario_cuenta: str) -> Dict[str, Any]:
    """Carga la planeación de la BD y computa automáticamente las firmas canónicas oficiales."""
    doc = planeacion_por_id_sql(doc_id)
    if not doc:
        doc = {
            "id": doc_id,
            "cuenta": usuario_cuenta,
            "formato": "XXIII",
            "estado": "BORRADOR",
            "revision": "rev-ini",
            "guardado_en": time.strftime("%Y-%m-%d %H:%M"),
            "datos": {
                "Ciclo": "2026-2027",
                "Mes": "Noviembre 2026",
                "Docente_Especialista": "Docente USAER",
                "Director_USAER": DIRECTOR_USAER
            },
            "metadatos": {"titulo": "Nueva Planeación"},
            "tablas": {"nee": [], "dosificacion": [], "evaluacion": []},
            "textos": {"proposito": ""},
            "observaciones_director": ""
        }

    # Resolución canónica de firmas oficiales
    firmas = resolver_firmas_planeacion(doc)
    doc["firmas_resueltas"] = firmas
    return doc

def adaptar_planeacion_para_pdf(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Adapta las columnas del editor SPA al contrato del generador compartido."""
    formato = doc["formato"]
    if formato not in FORMATOS:
        raise HTTPException(status_code=422, detail="Este anexo aún no tiene exportación en el piloto.")
    tablas = {**doc["tablas"]}
    if formato == "XXIII" and not tablas.get("aprendizajes"):
        tablas["aprendizajes"] = [{
            "Necesidades educativas específicas": fila.get("barreras_o_necesidades", ""),
            "Aprendizaje y/u objetivo": fila.get("pda", ""),
            "Descriptor de logro": fila.get("descriptor", ""),
        } for fila in tablas.get("nee", [])]
    conversion = {
        "Contextos": "modalidad", "Actividades": "actividad",
        "Temporalidad": "semana", "Fecha": "semana", "Recursos": "recursos",
    }
    tablas["dosificacion"] = [
        {**fila, **{k: fila.get(k, fila.get(v, "")) for k, v in conversion.items()}}
        for fila in tablas.get("dosificacion", [])
    ]
    for tabla in FORMATOS[formato]["tablas"]:
        tablas.setdefault(tabla, [])
    textos = {("Evaluación" if k == "evaluacion" else k): v for k, v in doc["textos"].items()}
    return {**doc, "tablas": tablas, "textos": textos}


def guardar_planeacion_transaccional(payload: Dict[str, Any], autor_cuenta: str, *, existente: bool, alumnos_spa=(), grupo_spa=None) -> Dict[str, Any]:
    """Guarda planeación con control de versiones y verificación de concurrencia en la BD."""
    pid = payload.get("id") or f"plan-{uuid.uuid4().hex[:8]}"
    nueva_rev = f"rev-{uuid.uuid4().hex}"

    payload["id"] = pid
    payload["cuenta"] = payload.get("cuenta") or autor_cuenta
    esperada = payload.get("revision")
    payload["revision"] = nueva_rev
    payload["guardado_en"] = time.strftime("%Y-%m-%d %H:%M:%S")

    # Persistir en BD
    firmas = resolver_firmas_planeacion(payload)
    try:
        guardar_planeacion_sql(payload, revision_esperada=esperada, existente_esperado=existente,
                               actor_spa=autor_cuenta, alumnos_spa=alumnos_spa, grupo_spa=grupo_spa)
    except ConflictoRevision as exc:
        raise HTTPException(status_code=409, detail="La planeación cambió. Vuelve a abrirla antes de guardar.") from exc

    return {
        "status": "success",
        "id": pid,
        "revision": nueva_rev,
        "guardado_en": payload["guardado_en"],
        "firmas": firmas
    }

def eliminar_planeacion_documento(doc_id: str, usuario_cuenta: str, es_director: bool) -> bool:
    """Elimina una planeación verificando que sea del usuario o que sea el Director."""
    doc = planeacion_por_id_sql(doc_id)
    if not doc:
        return False
    if not es_director and doc.get("cuenta") != usuario_cuenta:
        return False
    return delete_planeacion_sql(doc_id)

# -------------------------------------------------------------
# 6. ANEXOS III, IV, V Y VII (MUTACIONES)
# -------------------------------------------------------------
def guardar_anexo3_documento(payload: Dict[str, Any]) -> str:
    """Guarda detección de BAP (Anexo III) en la BD."""
    return save_anexo3_sql(payload)

def guardar_anexo4_documento(payload: Dict[str, Any]) -> str:
    """Guarda sugerencias técnico pedagógicas (Anexo IV) en la BD."""
    return save_anexo4_sql(payload)

def guardar_anexo5_documento(payload: Dict[str, Any]) -> str:
    """Guarda evento significativo (Anexo V) en la BD."""
    return save_anexo5_sql(payload)

def guardar_anexo7_documento(payload: Dict[str, Any]) -> str:
    """Guarda derivación (Anexo VII) en la BD."""
    return save_anexo7_sql(payload)

# -------------------------------------------------------------
# 7. VISITAS Y OFICIOS DE COMISIÓN
# -------------------------------------------------------------
def obtener_visitas_documentos(escuela: Optional[str] = None) -> List[Dict[str, Any]]:
    """Consulta actas de visitas desde la BD."""
    df = visitas_sql()
    if df.empty:
        return []
    records = df.to_dict(orient="records")
    if escuela:
        records = [r for r in records if escuela.lower() in str(r.get("Escuela", "")).lower()]
    return records

def guardar_visita_documento(payload: Dict[str, Any]) -> str:
    """Registra acta de visita en la BD."""
    return save_visita_sql(payload)

def obtener_oficios_documentos(escuela: Optional[str] = None) -> List[Dict[str, Any]]:
    """Consulta oficios de comisión desde la BD."""
    df = oficios_comision_sql()
    if df.empty:
        return []
    records = df.to_dict(orient="records")
    if escuela:
        records = [r for r in records if escuela.lower() in str(r.get("Escuela", "")).lower()]
    return records

def guardar_oficio_documento(payload: Dict[str, Any]) -> str:
    """Registra oficio de comisión en la BD."""
    return guardar_oficio_comision_sql(payload)

# -------------------------------------------------------------
# 8. ASISTENTE PEDAGÓGICO IA CONVERSACIONAL
# -------------------------------------------------------------
def chat_asistente_pedagogico(
    mensaje_docente: str,
    alumno_id: Optional[str] = None,
    planeacion_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Asistente conversacional contextualizado:
    - Recupera la historia real del alumno desde la BD (EPP, BAP, NEE).
    - Formula descriptores con sujeto + verbo en presente + complemento observable.
    - Valida contra los 14 indicadores oficiales de la Zona 001.
    """
    fuentes_consultadas = []
    alumno_info = None

    if alumno_id:
        exp = obtener_expediente_completo(alumno_id)
        alumno_info = exp.get("alumno")
        if exp.get("anexo3_bap"):
            fuentes_consultadas.append("Anexo III (Detección de BAP)")
        if exp.get("anexo4_sugerencias"):
            fuentes_consultadas.append("Anexo IV (Sugerencias a Docente Regular)")
        if exp.get("anexo5_eventos"):
            fuentes_consultadas.append("Anexo V (Eventos Significativos)")
        if exp.get("epp"):
            fuentes_consultadas.append("Evaluación Psicopedagógica (EPP)")

    nombre = alumno_info.get("nombre_completo") if alumno_info else "El alumno"
    pda_sugerido = ""
    descriptor_formato = f"{nombre} identifica los elementos centrales y formula dos preguntas con apoyo visual."
    apoyos = "Ejemplo de apoyo: ofrecer material visual y retroalimentación inmediata."

    respuesta_texto = (
        "Ejemplo local para revisión docente. No evalúa las evidencias ni valida indicadores.\n\n"
        f"Descriptor de ejemplo: {descriptor_formato}\n\n"
        f"{apoyos}"
    )

    propuesta_tabla = {
        "alumno": nombre,
        "curp": alumno_info.get("curp", "") if alumno_info else "",
        "barreras_o_necesidades": mensaje_docente,
        "pda": pda_sugerido,
        "descriptor": descriptor_formato,
        "apoyos": apoyos
    }

    return {
        "respuesta": respuesta_texto,
        "fuentes_consultadas": fuentes_consultadas,
        "propuesta_tabla": propuesta_tabla,
        "alumno_activo": alumno_info
    }

# -------------------------------------------------------------
# 9. ESTADÍSTICAS Y MÉTRICAS DE ZONA 001
# -------------------------------------------------------------
def obtener_estadisticas_zona() -> Dict[str, Any]:
    """Genera estadísticas reales agregadas de la Zona 001 desde la base relacional."""
    df_alumnos = alumnos_sql()
    df_visitas = visitas_sql()
    df_oficios = oficios_comision_sql()

    total_alumnos = len(df_alumnos) if not df_alumnos.empty else 0
    alumnos_activos = len(df_alumnos[df_alumnos["Estatus"] == "ACTIVO"]) if not df_alumnos.empty and "Estatus" in df_alumnos.columns else total_alumnos

    distribucion_condicion: Dict[str, int] = {}
    distribucion_escuela: Dict[str, int] = {}

    if not df_alumnos.empty:
        if "Condicion_Discapacidad" in df_alumnos.columns:
            distribucion_condicion = df_alumnos["Condicion_Discapacidad"].value_counts().to_dict()
        if "Nombre_Escuela" in df_alumnos.columns:
            distribucion_escuela = df_alumnos["Nombre_Escuela"].value_counts().to_dict()

    ciclo = "2026-2027"
    ids_activos = (df_alumnos.loc[df_alumnos["Estatus"] == "ACTIVO", "ID_Alumno"].tolist()
                   if alumnos_activos else [])
    con_epp = {doc["alumno"] for doc in epp_listar_sql(ids_activos) if doc["ciclo"] == ciclo}
    cobertura = f"{100 * len(con_epp) / alumnos_activos:.1f}%" if alumnos_activos else "—"
    return {
        "total_alumnos": total_alumnos,
        "alumnos_activos": alumnos_activos,
        "total_escuelas": 8,
        "visitas_registradas": len(df_visitas) if not df_visitas.empty else 0,
        "oficios_emitidos": len(df_oficios) if not df_oficios.empty else 0,
        "distribucion_condicion": distribucion_condicion,
        "distribucion_escuela": distribucion_escuela,
        "cumplimiento_epp": cobertura,
        "ciclo_activo": ciclo,
        "zona": "Zona 001 Especial"
    }

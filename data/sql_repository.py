"""Repositorio SQL ultrarrápido para Streamlit conectado a PostgreSQL / Neon.

Sustituye la latencia de Google Sheets con operaciones SQL indexadas y transacciones atómicas.
"""
from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, List, Optional
import uuid

import pandas as pd
from sqlalchemy import text, inspect

from data.database import (
    Alumno,
    Anexo3Deteccion,
    Anexo4Sugerencia,
    Anexo5Evento,
    Anexo7Derivacion,
    Asignacion,
    ColeccionInstitucional,
    ConfiguracionOficio,
    DocenteRegular,
    Escuela,
    EPPDoc,
    OficioComision,
    Personal,
    PlaneacionDoc,
    RegistroVisita,
    Usuario,
    get_engine,
    get_session,
    is_postgres,
)

logger = logging.getLogger(__name__)


def _df_from_query(model_class, order_by=None) -> pd.DataFrame:
    with get_session() as session:
        query = session.query(model_class)
        if order_by is not None:
            query = query.order_by(order_by)
        records = [r.__dict__ for r in query.all()]
        for r in records:
            r.pop("_sa_instance_state", None)
        return pd.DataFrame(records)


def alumnos_sql() -> pd.DataFrame:
    with get_session() as session:
        alumnos = session.query(Alumno).all()
        if not alumnos:
            return pd.DataFrame(columns=[
                "ID_Alumno", "Nombre_Completo", "CURP", "Edad_1_Septiembre", "Sexo",
                "Situacion_Alumno", "Nivel_Educativo", "Grado", "Grupo", "ID_Escuela",
                "Maestra de Apoyo", "ID_Maestro_Regular", "Condicion_Discapacidad",
                "Estatus", "Tipo_Atencion", "Lengua_Indigena_Mayahablante",
                "Afrodescendiente", "Migrante", "Nombre_Escuela", "Turno_Escuela",
                "CCT_Escuela", "Direccion_Escuela", "Localidad_Escuela",
                "Municipio_Escuela", "Condiciones_Adicionales", "Fecha_Nacimiento", "Fecha_Derivacion"
            ])
        filas = []
        for a in alumnos:
            filas.append({
                "ID_Alumno": str(a.id or ""),
                "Nombre_Completo": str(a.nombre_completo or ""),
                "CURP": str(a.curp or ""),
                "Edad_1_Septiembre": str(a.edad_1_septiembre or ""),
                "Sexo": str(a.sexo or ""),
                "Situacion_Alumno": str(a.situacion_alumno or ""),
                "Nivel_Educativo": str(a.nivel_educativo or ""),
                "Grado": str(a.grado or ""),
                "Grupo": str(a.grupo or ""),
                "ID_Escuela": str(a.id_escuela or ""),
                "Maestra de Apoyo": str(a.maestra_apoyo or ""),
                "ID_Maestro_Regular": str(a.id_maestro_regular or ""),
                "Condicion_Discapacidad": str(a.condicion_discapacidad or ""),
                "Estatus": str(a.estatus or "ACTIVO"),
                "Tipo_Atencion": str(a.tipo_atencion or ""),
                "Lengua_Indigena_Mayahablante": str(a.lengua_indigena_mayahablante or ""),
                "Afrodescendiente": str(a.afrodescendiente or ""),
                "Migrante": str(a.migrante or ""),
                "Nombre_Escuela": str(a.nombre_escuela or ""),
                "Turno_Escuela": str(a.turno_escuela or ""),
                "CCT_Escuela": str(a.cct_escuela or ""),
                "Direccion_Escuela": str(a.direccion_escuela or ""),
                "Localidad_Escuela": str(a.localidad_escuela or ""),
                "Municipio_Escuela": str(a.municipio_escuela or ""),
                "Condiciones_Adicionales": str(a.condiciones_adicionales or ""),
                "Fecha_Nacimiento": str(a.fecha_nacimiento or ""),
                "Fecha_Derivacion": str(a.fecha_derivacion or ""),
            })
        return pd.DataFrame(filas)


def save_alumno_sql(record: Dict[str, Any]) -> str:
    with get_session() as session:
        curp = str(record.get("CURP", "")).strip().upper()
        if curp:
            existente = session.query(Alumno).filter_by(curp=curp).first()
            if existente:
                raise ValueError("No se creó el alumno: esa CURP ya existe en la base central.")
        
        # Generar ID correlativo
        alumnos_con_id = session.query(Alumno.id).all()
        numeros = []
        for (aid,) in alumnos_con_id:
            if aid and aid.startswith("ALU-"):
                try:
                    numeros.append(int(aid.split("-")[-1]))
                except ValueError:
                    pass
        siguiente_num = max(numeros) + 1 if numeros else 1
        nuevo_id = record.get("ID_Alumno") or f"ALU-{siguiente_num:03d}"

        alumno = Alumno(
            id=nuevo_id,
            nombre_completo=str(record.get("Nombre_Completo", "")).strip(),
            curp=curp,
            edad_1_septiembre=str(record.get("Edad_1_Septiembre", "")),
            sexo=str(record.get("Sexo", "")),
            situacion_alumno=str(record.get("Situacion_Alumno", "")),
            nivel_educativo=str(record.get("Nivel_Educativo", "")),
            grado=str(record.get("Grado", "")),
            grupo=str(record.get("Grupo", "")),
            id_escuela=str(record.get("ID_Escuela", "")),
            maestra_apoyo=str(record.get("Maestra de Apoyo", "")),
            id_maestro_regular=str(record.get("ID_Maestro_Regular", "")),
            condicion_discapacidad=str(record.get("Condicion_Discapacidad", "")),
            estatus=str(record.get("Estatus", "ACTIVO")),
            tipo_atencion=str(record.get("Tipo_Atencion", "")),
            lengua_indigena_mayahablante=str(record.get("Lengua_Indigena_Mayahablante", "")),
            afrodescendiente=str(record.get("Afrodescendiente", "")),
            migrante=str(record.get("Migrante", "")),
            nombre_escuela=str(record.get("Nombre_Escuela", "")),
            turno_escuela=str(record.get("Turno_Escuela", "")),
            cct_escuela=str(record.get("CCT_Escuela", "")),
            direccion_escuela=str(record.get("Direccion_Escuela", "")),
            localidad_escuela=str(record.get("Localidad_Escuela", "")),
            municipio_escuela=str(record.get("Municipio_Escuela", "")),
            condiciones_adicionales=str(record.get("Condiciones_Adicionales", "")),
            fecha_nacimiento=str(record.get("Fecha_Nacimiento", "")),
            fecha_derivacion=str(record.get("Fecha_Derivacion", "")),
        )
        session.add(alumno)
        session.commit()
        return nuevo_id


def update_alumno_sql(id_alumno: str, cambios: Dict[str, Any], allowed_ids: List[str]) -> str:
    campos_editables = {
        "Nombre_Completo": "nombre_completo",
        "CURP": "curp",
        "Edad_1_Septiembre": "edad_1_septiembre",
        "Sexo": "sexo",
        "Situacion_Alumno": "situacion_alumno",
        "Nivel_Educativo": "nivel_educativo",
        "Grado": "grado",
        "Grupo": "grupo",
        "Condicion_Discapacidad": "condicion_discapacidad",
        "Estatus": "estatus",
        "Tipo_Atencion": "tipo_atencion",
        "Lengua_Indigena_Mayahablante": "lengua_indigena_mayahablante",
        "Afrodescendiente": "afrodescendiente",
        "Migrante": "migrante",
        "Condiciones_Adicionales": "condiciones_adicionales",
        "Fecha_Derivacion": "fecha_derivacion",
        "Fecha_Nacimiento": "fecha_nacimiento",
        "ID_Escuela": "id_escuela",
        "Nombre_Escuela": "nombre_escuela",
        "CCT_Escuela": "cct_escuela",
        "Turno_Escuela": "turno_escuela",
        "Direccion_Escuela": "direccion_escuela",
        "Localidad_Escuela": "localidad_escuela",
        "Municipio_Escuela": "municipio_escuela",
        "Maestra de Apoyo": "maestra_apoyo",
        "ID_Maestro_Regular": "id_maestro_regular",
    }
    id_alumno = str(id_alumno).strip()
    if not id_alumno or (allowed_ids and id_alumno not in {str(v).strip() for v in allowed_ids}):
        raise PermissionError("El alumno no está dentro del ámbito autorizado para edición.")

    with get_session() as session:
        alumno = session.query(Alumno).filter_by(id=id_alumno).first()
        if not alumno:
            raise ValueError(f"No se encontró el alumno {id_alumno} en la base SQL.")

        curp_nuevo = str(cambios.get("CURP", "")).strip().upper()
        if curp_nuevo and curp_nuevo != alumno.curp:
            otro = session.query(Alumno).filter(Alumno.curp == curp_nuevo, Alumno.id != id_alumno).first()
            if otro:
                raise ValueError("Ese CURP ya está registrado para otro alumno; no se aplicó ningún cambio.")

        for campo, valor in dict(cambios).items():
            if campo in campos_editables:
                col_attr = campos_editables[campo]
                setattr(alumno, col_attr, str(valor) if valor is not None else "")

        session.commit()
        return id_alumno


def save_alumnos_sql(rows: List[Dict[str, Any]]) -> List[str]:
    ids_creados = []
    for r in rows:
        aid = save_alumno_sql(r)
        ids_creados.append(aid)
    return ids_creados


def escuelas_sql() -> pd.DataFrame:
    with get_session() as session:
        escuelas = session.query(Escuela).all()
        if not escuelas:
            # Consultar nunca crea escuelas de ejemplo ni modifica el catálogo.
            return pd.DataFrame(columns=["ID_Escuela", "CCT", "Nombre_Escuela", "Nivel", "Turno"])
        return pd.DataFrame([
            {"ID_Escuela": e.id, "CCT": e.cct, "Nombre_Escuela": e.nombre_escuela, "Nivel": e.nivel, "Turno": e.turno}
            for e in escuelas
        ])


def personal_sql() -> pd.DataFrame:
    with get_session() as session:
        personal = session.query(Personal).all()
        if not personal:
            return pd.DataFrame(columns=["ID_Personal", "Nombre_Completo", "Rol", "Email", "Telefono"])
        return pd.DataFrame([
            {"ID_Personal": p.id, "Nombre_Completo": p.nombre_completo, "Rol": p.rol, "Email": p.email, "Telefono": p.telefono}
            for p in personal
        ])


def asignaciones_sql() -> pd.DataFrame:
    with get_session() as session:
        asignaciones = session.query(Asignacion).all()
        if not asignaciones:
            return pd.DataFrame(columns=["ID_Asignacion", "ID_Personal", "ID_Escuela"])
        return pd.DataFrame([
            {"ID_Asignacion": a.id, "ID_Personal": a.id_personal, "ID_Escuela": a.id_escuela}
            for a in asignaciones
        ])


def usuarios_sql() -> pd.DataFrame:
    # El login es solo lectura: una tabla aún no migrada no crea un esquema
    # vacío ni oculta las cuentas vigentes de la base central.
    engine=get_engine(initialize_schema=False)
    if not inspect(engine).has_table(Usuario.__tablename__):
        return pd.DataFrame(columns=["ID_Usuario", "Nombre", "Usuario", "Password", "Rol", "Escuelas_Permitidas"])
    with get_session(initialize_schema=False) as session:
        usuarios = session.query(Usuario).all()
        if not usuarios:
            return pd.DataFrame(columns=["ID_Usuario", "Nombre", "Usuario", "Password", "Rol", "Escuelas_Permitidas"])
        return pd.DataFrame([
            {"ID_Usuario": u.id, "Nombre": u.nombre, "Usuario": u.usuario, "Password": u.password, "Rol": u.rol, "Escuelas_Permitidas": u.escuelas_permitidas}
            for u in usuarios
        ])


def anexo3_sql() -> pd.DataFrame:
    with get_session() as session:
        registros = session.query(Anexo3Deteccion).all()
        if not registros:
            return pd.DataFrame(columns=["ID_Anexo3", "Fecha", "ID_Alumno", "ID_Personal", "BAP_Fisicas", "BAP_Actitudinales", "BAP_Pedagogicas", "BAP_Organizativas", "Estatus_IA", "Estado"])
        return pd.DataFrame([
            {
                "ID_Anexo3": r.id, "Fecha": r.fecha, "ID_Alumno": r.id_alumno, "ID_Personal": r.id_personal,
                "BAP_Fisicas": r.bap_fisicas, "BAP_Actitudinales": r.bap_actitudinales,
                "BAP_Pedagogicas": r.bap_pedagogicas, "BAP_Organizativas": r.bap_organizativas,
                "Estatus_IA": r.estatus_ia, "Estado": r.estado
            }
            for r in registros
        ])


def save_anexo3_sql(record: Dict[str, Any]) -> str:
    with get_session() as session:
        aid = str(record.get("ID_Anexo3") or uuid.uuid4().hex[:12])
        r = Anexo3Deteccion(
            id=aid,
            fecha=str(record.get("Fecha", "")),
            id_alumno=str(record.get("ID_Alumno", "")),
            id_personal=str(record.get("ID_Personal", "")),
            bap_fisicas=str(record.get("BAP_Fisicas", "")),
            bap_actitudinales=str(record.get("BAP_Actitudinales", "")),
            bap_pedagogicas=str(record.get("BAP_Pedagogicas", "")),
            bap_organizativas=str(record.get("BAP_Organizativas", "")),
            estatus_ia=str(record.get("Estatus_IA", "")),
            estado=str(record.get("Estado", "BORRADOR")),
        )
        session.add(r)
        session.commit()
        return aid


def update_anexo3_sql(id_anexo3: str, cambios: Dict[str, Any]) -> str:
    with get_session() as session:
        r = session.query(Anexo3Deteccion).filter_by(id=str(id_anexo3).strip()).first()
        if not r:
            raise ValueError(f"No se encontró el Anexo III {id_anexo3}")
        for k, v in dict(cambios).items():
            if k == "BAP_Fisicas": r.bap_fisicas = str(v)
            elif k == "BAP_Actitudinales": r.bap_actitudinales = str(v)
            elif k == "BAP_Pedagogicas": r.bap_pedagogicas = str(v)
            elif k == "BAP_Organizativas": r.bap_organizativas = str(v)
            elif k == "Estatus_IA": r.estatus_ia = str(v)
            elif k == "Estado": r.estado = str(v)
            elif k == "Fecha": r.fecha = str(v)
        session.commit()
        return str(id_anexo3)


def delete_anexo3_sql(id_anexo3: str) -> str:
    return update_anexo3_sql(id_anexo3, {"Estado": "ANULADO"})


def anexo4_sql() -> pd.DataFrame:
    from config.settings import ANEXO4_FIELDS
    with get_session() as session:
        registros = session.query(Anexo4Sugerencia).all()
        if not registros:
            return pd.DataFrame(columns=ANEXO4_FIELDS)
        return pd.DataFrame([
            {
                "ID_Anexo4": r.id, "ID_Alumno": r.id_alumno, "Fecha_Elaboracion": r.fecha_elaboracion,
                "Ciclo_Escolar": r.ciclo_escolar, "Trimestre": r.trimestre,
                "Docente_Especialista": r.docente_especialista, "Area": r.area,
                "Sugerencias_Area": r.sugerencias_area, "Motivo": r.motivo,
                "Sugerencias": r.sugerencias, "Fecha_Seguimiento": r.fecha_seguimiento,
                "Nivel_Cumplimiento_Resultados": r.nivel_cumplimiento_resultados,
                "Observaciones": r.observaciones, "Estado": r.estado
            }
            for r in registros
        ])


def save_anexo4_sql(record: Dict[str, Any]) -> str:
    with get_session() as session:
        aid = str(record.get("ID_Anexo4") or uuid.uuid4().hex[:12])
        r = Anexo4Sugerencia(
            id=aid,
            id_alumno=str(record.get("ID_Alumno", "")),
            fecha_elaboracion=str(record.get("Fecha_Elaboracion", "")),
            ciclo_escolar=str(record.get("Ciclo_Escolar", "")),
            trimestre=str(record.get("Trimestre", "")),
            docente_especialista=str(record.get("Docente_Especialista", "")),
            area=str(record.get("Area", "")),
            sugerencias_area=str(record.get("Sugerencias_Area", "")),
            motivo=str(record.get("Motivo", "")),
            sugerencias=str(record.get("Sugerencias", "")),
            fecha_seguimiento=str(record.get("Fecha_Seguimiento", "")),
            nivel_cumplimiento_resultados=str(record.get("Nivel_Cumplimiento_Resultados", "")),
            observaciones=str(record.get("Observaciones", "")),
            estado=str(record.get("Estado", "ACTIVA")),
        )
        session.add(r)
        session.commit()
        return aid


def update_anexo4_sql(id_anexo4: str, cambios: Dict[str, Any]) -> str:
    with get_session() as session:
        r = session.query(Anexo4Sugerencia).filter_by(id=str(id_anexo4).strip()).first()
        if not r:
            raise ValueError(f"No se encontró el Anexo IV {id_anexo4}")
        for k, v in dict(cambios).items():
            if k == "Sugerencias": r.sugerencias = str(v)
            elif k == "Sugerencias_Area": r.sugerencias_area = str(v)
            elif k == "Motivo": r.motivo = str(v)
            elif k == "Fecha_Seguimiento": r.fecha_seguimiento = str(v)
            elif k == "Nivel_Cumplimiento_Resultados": r.nivel_cumplimiento_resultados = str(v)
            elif k == "Observaciones": r.observaciones = str(v)
            elif k == "Estado": r.estado = str(v)
        session.commit()
        return str(id_anexo4)


def delete_anexo4_sql(id_anexo4: str) -> str:
    return update_anexo4_sql(id_anexo4, {"Estado": "ANULADO"})


def anexo5_sql() -> pd.DataFrame:
    with get_session() as session:
        registros = session.query(Anexo5Evento).all()
        if not registros:
            return pd.DataFrame(columns=["ID_Evento", "Fecha", "Nombre_Alumno", "Grado_Grupo", "Especialista", "Evento", "Estado", "ID_Alumno", "ID_Escuela", "Escuela"])
        return pd.DataFrame([
            {
                "ID_Evento": r.id, "Fecha": r.fecha, "Nombre_Alumno": r.nombre_alumno,
                "Grado_Grupo": r.grado_grupo, "Especialista": r.especialista,
                "Evento": r.evento, "Estado": r.estado, "ID_Alumno": r.id_alumno,
                "ID_Escuela": r.id_escuela, "Escuela": r.escuela
            }
            for r in registros
        ])


def save_anexo5_sql(record: Dict[str, Any]) -> str:
    with get_session() as session:
        aid = str(record.get("ID_Evento") or uuid.uuid4().hex[:12])
        r = Anexo5Evento(
            id=aid,
            fecha=str(record.get("Fecha", "")),
            nombre_alumno=str(record.get("Nombre_Alumno", "")),
            grado_grupo=str(record.get("Grado_Grupo", "")),
            especialista=str(record.get("Especialista", "")),
            evento=str(record.get("Evento", "")),
            estado=str(record.get("Estado", "ACTIVO")),
            id_alumno=str(record.get("ID_Alumno", "")),
            id_escuela=str(record.get("ID_Escuela", "")),
            escuela=str(record.get("Escuela", "")),
        )
        session.add(r)
        session.commit()
        return aid


def update_anexo5_sql(id_evento: str, cambios: Dict[str, Any]) -> str:
    with get_session() as session:
        r = session.query(Anexo5Evento).filter_by(id=str(id_evento).strip()).first()
        if not r:
            raise ValueError(f"No se encontró el evento {id_evento}")
        for k, v in dict(cambios).items():
            if k == "Fecha": r.fecha = str(v)
            elif k == "Evento": r.evento = str(v)
            elif k == "Estado": r.estado = str(v)
            elif k == "Especialista": r.especialista = str(v)
            elif k == "Grado_Grupo": r.grado_grupo = str(v)
        session.commit()
        return str(id_evento)


def anexo7_sql() -> pd.DataFrame:
    with get_session() as session:
        registros = session.query(Anexo7Derivacion).all()
        if not registros:
            return pd.DataFrame(columns=["ID_Anexo7", "Fecha", "ID_Alumno", "Escuela", "Docente_Regular", "Fecha_Nacimiento", "Respuestas_JSON", "Salud", "Seguimiento_Medico", "Aspecto_Relevante", "Elaborado_Por"])
        return pd.DataFrame([
            {
                "ID_Anexo7": r.id, "Fecha": r.fecha, "ID_Alumno": r.id_alumno, "Escuela": r.escuela,
                "Docente_Regular": r.docente_regular, "Fecha_Nacimiento": r.fecha_nacimiento,
                "Respuestas_JSON": r.respuestas_json, "Salud": r.salud,
                "Seguimiento_Medico": r.seguimiento_medico, "Aspecto_Relevante": r.aspecto_relevante,
                "Elaborado_Por": r.elaborado_por
            }
            for r in registros
        ])


def save_anexo7_sql(record: Dict[str, Any]) -> str:
    with get_session() as session:
        aid = str(record.get("ID_Anexo7") or uuid.uuid4().hex[:12])
        r = Anexo7Derivacion(
            id=aid,
            fecha=str(record.get("Fecha", "")),
            id_alumno=str(record.get("ID_Alumno", "")),
            escuela=str(record.get("Escuela", "")),
            docente_regular=str(record.get("Docente_Regular", "")),
            fecha_nacimiento=str(record.get("Fecha_Nacimiento", "")),
            respuestas_json=str(record.get("Respuestas_JSON", "{}")),
            salud=str(record.get("Salud", "")),
            seguimiento_medico=str(record.get("Seguimiento_Medico", "")),
            aspecto_relevante=str(record.get("Aspecto_Relevante", "")),
            elaborado_por=str(record.get("Elaborado_Por", "")),
        )
        session.add(r)
        session.commit()
        return aid


def visitas_sql() -> pd.DataFrame:
    with get_session() as session:
        registros = session.query(RegistroVisita).all()
        if not registros:
            return pd.DataFrame(columns=["ID_Visita", "Fecha", "Escuela", "Personal", "Motivo", "Observaciones", "Evidencia", "Estatus", "Tipo_Acta", "Lugar"])
        return pd.DataFrame([
            {
                "ID_Visita": r.id, "Fecha": r.fecha, "Escuela": r.escuela, "Personal": r.personal,
                "Motivo": r.motivo, "Observaciones": r.observaciones, "Evidencia": r.evidencia,
                "Estatus": r.estatus, "Tipo_Acta": r.tipo_acta, "Lugar": r.lugar
            }
            for r in registros
        ])


def save_visita_sql(record: Dict[str, Any]) -> str:
    with get_session() as session:
        aid = str(record.get("ID_Visita") or uuid.uuid4().hex[:12])
        r = RegistroVisita(
            id=aid,
            fecha=str(record.get("Fecha", "")),
            escuela=str(record.get("Escuela", "")),
            personal=str(record.get("Personal", "")),
            motivo=str(record.get("Motivo", "")),
            observaciones=str(record.get("Observaciones", "")),
            evidencia=str(record.get("Evidencia", "")),
            estatus=str(record.get("Estatus", "GUARDADA")),
            tipo_acta=str(record.get("Tipo_Acta", "")),
            lugar=str(record.get("Lugar", "")),
        )
        session.add(r)
        session.commit()
        return aid


def oficios_comision_sql() -> pd.DataFrame:
    with get_session() as session:
        registros = session.query(OficioComision).all()
        if not registros:
            return pd.DataFrame(columns=["ID_Oficio", "Folio", "Clave_Operacion", "Fecha_Emision", "Fecha_Comision", "Escuela", "ID_Escuela", "Maestra_Apoyo", "Director_Escuela", "Asunto", "Destino", "Horario", "Estado"])
        return pd.DataFrame([
            {
                "ID_Oficio": r.id, "Folio": r.folio, "Clave_Operacion": r.clave_operacion,
                "Fecha_Emision": r.fecha_emision, "Fecha_Comision": r.fecha_comision,
                "Escuela": r.escuela, "ID_Escuela": r.id_escuela,
                "Maestra_Apoyo": r.maestra_apoyo, "Director_Escuela": r.director_escuela,
                "Asunto": r.asunto, "Destino": r.destino, "Horario": r.horario, "Estado": r.estado
            }
            for r in registros
        ])


def guardar_oficio_comision_sql(record: Dict[str, Any], folio_manual: Optional[int] = None) -> Dict[str, Any]:
    with get_session() as session:
        clave = str(record.get("Clave_Operacion", "")).strip()
        if clave:
            existente = session.query(OficioComision).filter_by(clave_operacion=clave).first()
            if existente:
                return {
                    "ID_Oficio": existente.id,
                    "Folio": existente.folio,
                    **record
                }

        oficios = session.query(OficioComision.folio).all()
        folios = []
        for (f,) in oficios:
            try:
                folios.append(int(str(f).strip()))
            except (ValueError, TypeError):
                pass

        if folio_manual is not None:
            folio = int(folio_manual)
            if any(f == folio for f in folios):
                raise ValueError(f"El folio {folio:03d} ya está registrado.")
        else:
            folio = max([21, *folios]) + 1

        aid = f"OFI-{folio:03d}"
        r = OficioComision(
            id=aid,
            folio=str(folio),
            clave_operacion=clave,
            fecha_emision=str(record.get("Fecha_Emision", "")),
            fecha_comision=str(record.get("Fecha_Comision", "")),
            escuela=str(record.get("Escuela", "")),
            id_escuela=str(record.get("ID_Escuela", "")),
            maestra_apoyo=str(record.get("Maestra_Apoyo", "")),
            director_escuela=str(record.get("Director_Escuela", "")),
            asunto=str(record.get("Asunto", "")),
            destino=str(record.get("Destino", "")),
            horario=str(record.get("Horario", "")),
            estado=str(record.get("Estado", "GENERADO")),
        )
        session.add(r)
        session.commit()
        return {
            "ID_Oficio": aid,
            "Folio": folio,
            **record,
            "Estado": "GENERADO",
        }


def configuracion_oficios_sql() -> pd.DataFrame:
    with get_session() as session:
        registros = session.query(ConfiguracionOficio).all()
        if not registros:
            return pd.DataFrame(columns=["ID_Configuracion", "Fecha_Comision", "Asunto", "Destino", "Horario", "Actualizado_Por", "Actualizado_En"])
        return pd.DataFrame([
            {
                "ID_Configuracion": r.id, "Fecha_Comision": r.fecha_comision, "Asunto": r.asunto,
                "Destino": r.destino, "Horario": r.horario, "Actualizado_Por": r.actualizado_por,
                "Actualizado_En": r.actualizado_en
            }
            for r in registros
        ])


def guardar_configuracion_oficios_sql(record: Dict[str, Any]) -> Dict[str, Any]:
    with get_session() as session:
        aid = str(record.get("ID_Configuracion") or f"CFG-OFI-{uuid.uuid4().hex[:6]}")
        r = ConfiguracionOficio(
            id=aid,
            fecha_comision=str(record.get("Fecha_Comision", "")),
            asunto=str(record.get("Asunto", "")),
            destino=str(record.get("Destino", "")),
            horario=str(record.get("Horario", "")),
            actualizado_por=str(record.get("Actualizado_Por", "")),
            actualizado_en=str(record.get("Actualizado_En", "")),
        )
        session.add(r)
        session.commit()
        res = dict(record)
        res["ID_Configuracion"] = aid
        return res


def docentes_regulares_sql() -> pd.DataFrame:
    with get_session() as session:
        registros = session.query(DocenteRegular).all()
        if not registros:
            return pd.DataFrame(columns=["ID_Registro", "Fecha_Registro", "Ciclo_Escolar", "ID_Escuela", "Nombre_Escuela", "Turno", "Grado", "Grupo", "Nombre_Docente", "Telefono", "Email", "Observaciones"])
        return pd.DataFrame([
            {
                "ID_Registro": r.id, "Fecha_Registro": r.fecha_registro, "Ciclo_Escolar": r.ciclo_escolar,
                "ID_Escuela": r.id_escuela, "Nombre_Escuela": r.nombre_escuela, "Turno": r.turno,
                "Grado": r.grado, "Grupo": r.grupo, "Nombre_Docente": r.nombre_docente,
                "Telefono": r.telefono, "Email": r.email, "Observaciones": r.observaciones
            }
            for r in registros
        ])


def guardar_docente_regular_sql(record: Dict[str, Any]) -> str:
    with get_session() as session:
        aid = str(record.get("ID_Registro") or uuid.uuid4().hex[:12])
        r = DocenteRegular(
            id=aid,
            fecha_registro=str(record.get("Fecha_Registro", "")),
            ciclo_escolar=str(record.get("Ciclo_Escolar", "")),
            id_escuela=str(record.get("ID_Escuela", "")),
            nombre_escuela=str(record.get("Nombre_Escuela", "")),
            turno=str(record.get("Turno", "")),
            grado=str(record.get("Grado", "")),
            grupo=str(record.get("Grupo", "")),
            nombre_docente=str(record.get("Nombre_Docente", "")),
            telefono=str(record.get("Telefono", "")),
            email=str(record.get("Email", "")),
            observaciones=str(record.get("Observaciones", "")),
        )
        session.add(r)
        session.commit()
        return aid


def sync_from_sheets_if_empty(table_name: str, df: pd.DataFrame) -> None:
    """Sincroniza datos iniciales de Google Sheets hacia SQL solo si la tabla SQL está vacía."""
    if df is None or df.empty:
        return
    try:
        if table_name == "Alumnos":
            with get_session() as session:
                if session.query(Alumno).count() == 0:
                    for r in df.to_dict("records"):
                        try:
                            save_alumno_sql(r)
                        except Exception:
                            pass
        elif table_name == "Escuelas":
            with get_session() as session:
                if session.query(Escuela).count() == 0:
                    for r in df.to_dict("records"):
                        session.add(Escuela(
                            id=str(r.get("ID_Escuela", "")),
                            cct=str(r.get("CCT", "")),
                            nombre_escuela=str(r.get("Nombre_Escuela", "")),
                            nivel=str(r.get("Nivel", "")),
                            turno=str(r.get("Turno", "")),
                        ))
                    session.commit()
        elif table_name == "Personal":
            with get_session() as session:
                if session.query(Personal).count() == 0:
                    for r in df.to_dict("records"):
                        session.add(Personal(
                            id=str(r.get("ID_Personal", "")),
                            nombre_completo=str(r.get("Nombre_Completo", "")),
                            rol=str(r.get("Rol", "")),
                            email=str(r.get("Email", "")),
                            telefono=str(r.get("Telefono", "")),
                        ))
                    session.commit()
        elif table_name == "Asignaciones":
            with get_session() as session:
                if session.query(Asignacion).count() == 0:
                    for r in df.to_dict("records"):
                        session.add(Asignacion(
                            id=str(r.get("ID_Asignacion", "")),
                            id_personal=str(r.get("ID_Personal", "")),
                            id_escuela=str(r.get("ID_Escuela", "")),
                        ))
                    session.commit()
        elif table_name == "Usuarios":
            with get_session() as session:
                if session.query(Usuario).count() == 0:
                    for r in df.to_dict("records"):
                        session.add(Usuario(
                            id=str(r.get("ID_Usuario", "")),
                            nombre=str(r.get("Nombre", "")),
                            usuario=str(r.get("Usuario", "")),
                            password=str(r.get("Password", "")),
                            rol=str(r.get("Rol", "")),
                            escuelas_permitidas=str(r.get("Escuelas_Permitidas", "")),
                        ))
                    session.commit()
    except Exception as exc:
        logger.warning("Error en sincronización inicial de %s: %s", table_name, exc)


def planeaciones_resumen_sql(cuenta: str, es_director: bool = False) -> List[Dict[str, Any]]:
    """Carga EXCLUSIVAMENTE la vista resumida de los documentos del usuario activo (o todos para Director).
    
    Optimización crítica: No descarga el historial completo de la BD ni los payloads pesados de tablas/textos;
    filtra por cuenta en el motor relacional y retorna únicamente las columnas necesarias para el listado.
    """
    with get_session() as session:
        query = session.query(
            PlaneacionDoc.id,
            PlaneacionDoc.cuenta,
            PlaneacionDoc.formato,
            PlaneacionDoc.estado,
            PlaneacionDoc.revision,
            PlaneacionDoc.guardado_en,
            PlaneacionDoc.datos_json,
            PlaneacionDoc.metadatos_json,
            PlaneacionDoc.payload_json,
            PlaneacionDoc.observaciones_director,
        )
        if not es_director and cuenta:
            query = query.filter(PlaneacionDoc.cuenta == str(cuenta).strip())
        
        query = query.order_by(PlaneacionDoc.actualizado_en.desc()).limit(500)
        rows = query.all()
        
        res = []
        for r in rows:
            datos = json.loads(r.datos_json) if r.datos_json else {}
            metadatos = json.loads(r.metadatos_json) if r.metadatos_json else {}
            if (not datos or not metadatos) and getattr(r, "payload_json", None) and r.payload_json != "{}":
                try:
                    full_p = json.loads(r.payload_json)
                    if isinstance(full_p, dict):
                        if not datos:
                            datos = full_p.get("datos", {}) or {}
                        if not metadatos:
                            metadatos = full_p.get("metadatos", {}) or {}
                except Exception:
                    pass
            res.append({
                "id": str(r.id),
                "cuenta": str(r.cuenta or ""),
                "formato": str(r.formato or "XXIII"),
                "estado": str(r.estado or "BORRADOR"),
                "revision": str(r.revision or ""),
                "guardado_en": str(r.guardado_en or ""),
                "datos": datos,
                "metadatos": metadatos,
                "tablas": {},
                "textos": {},
                "observaciones_director": str(r.observaciones_director or ""),
            })
        return res


def planeacion_por_id_sql(id_planeacion: str) -> Optional[Dict[str, Any]]:
    """Obtiene el documento completo de una planeación por su ID."""
    with get_session() as session:
        r = session.query(PlaneacionDoc).filter_by(id=str(id_planeacion).strip()).first()
        if not r:
            return None
        if hasattr(r, "payload_json") and r.payload_json and r.payload_json != "{}":
            try:
                return json.loads(r.payload_json)
            except Exception:
                pass
        datos = json.loads(r.datos_json) if r.datos_json else {}
        metadatos = json.loads(r.metadatos_json) if r.metadatos_json else {}
        tablas = json.loads(r.tablas_json) if r.tablas_json else {}
        textos = json.loads(r.textos_json) if r.textos_json else {}
        return {
            "id": str(r.id),
            "cuenta": str(r.cuenta or ""),
            "formato": str(r.formato or "XXIII"),
            "estado": str(r.estado or "BORRADOR"),
            "revision": str(r.revision or ""),
            "guardado_en": str(r.guardado_en or ""),
            "datos": datos,
            "metadatos": metadatos,
            "tablas": tablas,
            "textos": textos,
            "observaciones_director": str(r.observaciones_director or ""),
        }


def guardar_planeacion_sql(doc: Dict[str, Any]) -> str:
    """Persiste o actualiza una planeación en PostgreSQL con transacción atómica."""
    with get_session() as session:
        pid = str(doc.get("id") or uuid.uuid4().hex[:12])
        existente = session.query(PlaneacionDoc).filter_by(id=pid).first()
        payload_str = json.dumps(doc, ensure_ascii=False)
        datos_str = json.dumps(doc.get("datos", {}), ensure_ascii=False)
        metadatos_str = json.dumps(doc.get("metadatos", {}), ensure_ascii=False)
        tablas_str = json.dumps(doc.get("tablas", {}), ensure_ascii=False)
        textos_str = json.dumps(doc.get("textos", {}), ensure_ascii=False)
        
        if existente:
            existente.cuenta = str(doc.get("cuenta", ""))
            existente.formato = str(doc.get("formato", "XXIII"))
            existente.estado = str(doc.get("estado", "BORRADOR"))
            existente.revision = str(doc.get("revision", ""))
            existente.guardado_en = str(doc.get("guardado_en", ""))
            existente.datos_json = datos_str
            existente.metadatos_json = metadatos_str
            existente.tablas_json = tablas_str
            existente.textos_json = textos_str
            existente.payload_json = payload_str
            existente.observaciones_director = str(doc.get("observaciones_director", ""))
        else:
            p = PlaneacionDoc(
                id=pid,
                cuenta=str(doc.get("cuenta", "")),
                formato=str(doc.get("formato", "XXIII")),
                estado=str(doc.get("estado", "BORRADOR")),
                revision=str(doc.get("revision", "")),
                guardado_en=str(doc.get("guardado_en", "")),
                datos_json=datos_str,
                metadatos_json=metadatos_str,
                tablas_json=tablas_str,
                textos_json=textos_str,
                payload_json=payload_str,
                observaciones_director=str(doc.get("observaciones_director", "")),
            )
            session.add(p)
        session.commit()
        return pid


def delete_planeacion_sql(id_planeacion: str) -> bool:
    with get_session() as session:
        r = session.query(PlaneacionDoc).filter_by(id=str(id_planeacion).strip()).first()
        if r:
            session.delete(r)
            session.commit()
            return True
        return False


def epp_listar_sql(ids_alumnos: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Consulta indexada ultrarrápida de informes EPP filtrados por los alumnos autorizados."""
    with get_session() as session:
        query = session.query(EPPDoc)
        if ids_alumnos is not None:
            query = query.filter(EPPDoc.alumno.in_([str(a).strip() for a in ids_alumnos]))
        records = query.order_by(EPPDoc.actualizado_en.desc()).all()
        docs = []
        for r in records:
            partes = json.loads(r.partes_json) if r.partes_json else {}
            docs.append({
                "id": str(r.id),
                "alumno": str(r.alumno),
                "ciclo": str(r.ciclo),
                "revision": str(r.revision),
                "fecha": str(r.fecha),
                "partes": partes,
            })
        return docs


def guardar_epp_sql(doc: Dict[str, Any]) -> str:
    """Persiste un informe EPP en PostgreSQL."""
    with get_session() as session:
        eid = str(doc.get("id") or f"{doc.get('alumno')}:{doc.get('ciclo')}")
        existente = session.query(EPPDoc).filter_by(id=eid).first()
        partes_str = json.dumps(doc.get("partes", {}), ensure_ascii=False)
        estado = str(doc.get("partes", {}).get("META", {}).get("estado", "BORRADOR"))
        if existente:
            existente.alumno = str(doc.get("alumno", ""))
            existente.ciclo = str(doc.get("ciclo", ""))
            existente.estado = estado
            existente.revision = str(doc.get("revision", ""))
            existente.fecha = str(doc.get("fecha", ""))
            existente.partes_json = partes_str
        else:
            e = EPPDoc(
                id=eid,
                alumno=str(doc.get("alumno", "")),
                ciclo=str(doc.get("ciclo", "")),
                estado=estado,
                revision=str(doc.get("revision", "")),
                fecha=str(doc.get("fecha", "")),
                partes_json=partes_str,
            )
            session.add(e)
        session.commit()
        return eid


def coleccion_listar_sql(
    modulo: str,
    id_escuela: Optional[str] = None,
    id_alumno: Optional[str] = None,
    cuenta: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Lista registros de una colección institucional con filtrado indexado y tolerancia a fallos."""
    try:
        with get_session() as session:
            query = session.query(ColeccionInstitucional).filter(ColeccionInstitucional.modulo == str(modulo).strip())
            if id_escuela:
                query = query.filter(ColeccionInstitucional.id_escuela == str(id_escuela).strip())
            if id_alumno:
                query = query.filter(ColeccionInstitucional.id_alumno == str(id_alumno).strip())
            if cuenta:
                query = query.filter(ColeccionInstitucional.cuenta == str(cuenta).strip())
            rows = query.order_by(ColeccionInstitucional.fecha.desc(), ColeccionInstitucional.actualizado_en.desc()).all()
            out = []
            for r in rows:
                if r.estado == "ANULADO":
                    continue
                try:
                    payload = json.loads(r.payload_json) if r.payload_json else {}
                except Exception:
                    payload = {}
                if isinstance(payload, dict):
                    item = dict(payload)
                else:
                    item = {"valor": payload}
                item.setdefault("id", str(r.registro_id or r.id))
                item.setdefault("_modulo", str(r.modulo))
                item.setdefault("_cuenta", str(r.cuenta or ""))
                item.setdefault("_id_escuela", str(r.id_escuela or ""))
                item.setdefault("_id_alumno", str(r.id_alumno or ""))
                item.setdefault("_fecha", str(r.fecha or ""))
                item.setdefault("_estado", str(r.estado or "ACTIVO"))
                out.append(item)
            return out
    except Exception as exc:
        logger.warning("Aviso en coleccion_listar_sql (%s): %s", modulo, exc)
        return []


def coleccion_guardar_sql(
    modulo: str,
    registro_id: str,
    payload: Dict[str, Any],
    cuenta: str = "",
    id_escuela: str = "",
    id_alumno: str = "",
    fecha: str = "",
    estado: str = "ACTIVO",
) -> str:
    """Guarda o actualiza un registro dentro de una colección institucional."""
    mod_clean = str(modulo).strip()
    reg_clean = str(registro_id or uuid.uuid4().hex[:12]).strip()
    pk = f"{mod_clean}:{reg_clean}"
    payload_str = json.dumps(payload, ensure_ascii=False)
    try:
        with get_session() as session:
            existente = session.query(ColeccionInstitucional).filter_by(id=pk).first()
            if existente:
                existente.registro_id = reg_clean
                existente.cuenta = str(cuenta or existente.cuenta or "")
                existente.id_escuela = str(id_escuela or existente.id_escuela or "")
                existente.id_alumno = str(id_alumno or existente.id_alumno or "")
                existente.fecha = str(fecha or existente.fecha or "")
                existente.estado = str(estado or "ACTIVO")
                existente.payload_json = payload_str
            else:
                session.add(ColeccionInstitucional(
                    id=pk,
                    modulo=mod_clean,
                    registro_id=reg_clean,
                    cuenta=str(cuenta or ""),
                    id_escuela=str(id_escuela or ""),
                    id_alumno=str(id_alumno or ""),
                    fecha=str(fecha or ""),
                    estado=str(estado or "ACTIVO"),
                    payload_json=payload_str,
                ))
            session.commit()
    except Exception as exc:
        logger.warning("Aviso en coleccion_guardar_sql (%s): %s", pk, exc)
    return reg_clean


"""Servicio de gestión y registro de maestros regulares de escuelas primarias."""
import json
import os
from datetime import datetime
from uuid import uuid4
import pandas as pd
from zoneinfo import ZoneInfo
from config.settings import ESCUELAS_USAER, SCHOOL_YEAR

ZONA = ZoneInfo("America/Merida")

# Las 7 escuelas primarias atendidas por la USAER 02E
ESCUELAS_PRIMARIAS = [
    "Damián Carmona",
    "Ichcaanziho",
    "Gregorio Torres Quintero",
    "Remigio Aguilar Sosa",
    "Elvira Parra Ávila",
    "Manuel Sarrado",
    "Domingo Solís Rodríguez",
]

GRADOS = ["1°", "2°", "3°", "4°", "5°", "6°"]
GRUPOS = ["A", "B", "C", "D", "E"]
TURNOS = ["Matutino", "Vespertino", "Jornada Completa / Tiempo Completo"]

HEADERS_DOCENTES_REGULARES = [
    "ID_Registro",
    "Fecha_Registro",
    "Ciclo_Escolar",
    "ID_Escuela",
    "Nombre_Escuela",
    "Turno",
    "Grado",
    "Grupo",
    "Nombre_Docente",
    "Telefono",
    "Email",
    "Observaciones",
]

_LOCAL_BACKUP_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "docentes_regulares_backup.json")


def _guardar_local(registro):
    """Respaldo de contingencia local para no perder nunca un registro."""
    registros = _leer_local()
    # Si ya existe misma escuela, turno, grado y grupo, actualizamos
    actualizado = False
    for i, r in enumerate(registros):
        if (
            r.get("Nombre_Escuela") == registro.get("Nombre_Escuela")
            and r.get("Turno") == registro.get("Turno")
            and r.get("Grado") == registro.get("Grado")
            and r.get("Grupo") == registro.get("Grupo")
        ):
            registros[i] = {**r, **registro}
            actualizado = True
            break
    if not actualizado:
        registros.append(registro)
    try:
        os.makedirs(os.path.dirname(_LOCAL_BACKUP_PATH), exist_ok=True)
        with open(_LOCAL_BACKUP_PATH, "w", encoding="utf-8") as f:
            json.dump(registros, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _leer_local():
    """Lee registros del respaldo local si existe."""
    if os.path.exists(_LOCAL_BACKUP_PATH):
        try:
            with open(_LOCAL_BACKUP_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def registrar_docente_regular(
    escuela,
    grado,
    grupo,
    nombre_docente,
    turno="Matutino",
    telefono="",
    email="",
    observaciones="",
    ciclo_escolar=None,
):
    """Registra o actualiza a un maestro de grupo en Google Sheets y respaldo."""
    escuela = str(escuela or "").strip()
    grado = str(grado or "").strip()
    grupo = str(grupo or "").strip().upper()
    nombre_docente = str(nombre_docente or "").strip()
    turno = str(turno or "Matutino").strip()

    if not escuela:
        raise ValueError("Debes seleccionar una escuela primaria.")
    if not grado:
        raise ValueError("Debes especificar el grado escolar (ej. 1°, 2°).")
    if not grupo:
        raise ValueError("Debes especificar el grupo escolar (ej. A, B).")
    if not nombre_docente:
        raise ValueError("Debes ingresar el nombre completo del docente de grupo.")

    id_escuela = ESCUELAS_USAER.get(escuela, "")
    ahora = datetime.now(ZONA).isoformat(timespec="seconds")
    ciclo = ciclo_escolar or SCHOOL_YEAR

    registro = {
        "ID_Registro": f"DOC-{uuid4().hex[:8].upper()}",
        "Fecha_Registro": ahora,
        "Ciclo_Escolar": ciclo,
        "ID_Escuela": id_escuela,
        "Nombre_Escuela": escuela,
        "Turno": turno,
        "Grado": grado,
        "Grupo": grupo,
        "Nombre_Docente": nombre_docente,
        "Telefono": str(telefono or "").strip(),
        "Email": str(email or "").strip(),
        "Observaciones": str(observaciones or "").strip(),
    }

    # Guardar en contingencia local
    _guardar_local(registro)

    # Intentar persistir en Google Sheets central
    try:
        from data.google import ensure_headers, append_dict, df_sheet, clear_cache
        ensure_headers("Docentes_Regulares", HEADERS_DOCENTES_REGULARES)
        append_dict("Docentes_Regulares", registro)
    except Exception:
        # Si no hay credenciales o está offline, el respaldo local asegura persistencia
        pass

    return registro


def registrar_lote_docentes(escuela, turno, lista_docentes, ciclo_escolar=None):
    """Registra múltiples docentes para una misma escuela y turno."""
    guardados = []
    for d in lista_docentes:
        nom = d.get("Nombre_Docente", "").strip()
        grd = d.get("Grado", "").strip()
        grp = d.get("Grupo", "").strip()
        if nom and grd and grp:
            reg = registrar_docente_regular(
                escuela=escuela,
                grado=grd,
                grupo=grp,
                nombre_docente=nom,
                turno=turno,
                telefono=d.get("Telefono", ""),
                email=d.get("Email", ""),
                observaciones=d.get("Observaciones", ""),
                ciclo_escolar=ciclo_escolar,
            )
            guardados.append(reg)
    return guardados


def listar_docentes_regulares(escuela=None):
    """Obtiene el listado consolidado de docentes regulares registrados."""
    registros = []
    # 1. Intentar leer de Google Sheets
    try:
        from data.google import df_sheet
        df = df_sheet("Docentes_Regulares")
        if not df.empty:
            registros = df.to_dict("records")
    except Exception:
        pass

    # 2. Combinar con registros locales de contingencia
    locales = _leer_local()
    mapa = {}
    # Google Sheets primero
    for r in registros:
        k = (r.get("Nombre_Escuela", ""), r.get("Turno", ""), r.get("Grado", ""), r.get("Grupo", ""))
        if any(k):
            mapa[k] = r
    # Locales sobreescriben si son más recientes
    for r in locales:
        k = (r.get("Nombre_Escuela", ""), r.get("Turno", ""), r.get("Grado", ""), r.get("Grupo", ""))
        if any(k):
            mapa[k] = r

    todos = list(mapa.values())
    if escuela:
        escuela_norm = escuela.strip().lower()
        todos = [r for r in todos if r.get("Nombre_Escuela", "").strip().lower() == escuela_norm]

    # Ordenar por Escuela, Turno, Grado, Grupo
    todos.sort(key=lambda x: (
        x.get("Nombre_Escuela", ""),
        x.get("Turno", ""),
        x.get("Grado", ""),
        x.get("Grupo", ""),
    ))
    return todos


def resumen_cobertura_escuelas():
    """Calcula cuántos grupos tienen maestro registrado por escuela."""
    docentes = listar_docentes_regulares()
    resumen = []
    for esc in ESCUELAS_PRIMARIAS:
        regs = [d for d in docentes if d.get("Nombre_Escuela") == esc]
        grupos_cubiertos = len(regs)
        resumen.append({
            "Escuela": esc,
            "CCT": ESCUELAS_USAER.get(esc, ""),
            "Docentes_Registrados": grupos_cubiertos,
            "Detalle": regs,
        })
    return resumen

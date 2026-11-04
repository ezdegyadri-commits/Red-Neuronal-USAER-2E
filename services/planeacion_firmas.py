"""Resolución canónica de firmas para planeaciones USAER 02-E.

Asigna automáticamente el nombre oficial del docente o especialista que elaboró
la planeación según la escuela, función y rol asignado, así como la firma de
Dirección (Psic. Personal ficticio 11).
"""
from __future__ import annotations

import re
from typing import Any, Mapping

from config.settings import ESCUELAS_USAER
from utils.text import normalizar_texto

DIRECTOR_USAER = "Psic. Personal ficticio 11"
CARGO_DIRECTOR_USAER = "Vo. Bo. Director del Servicio de Apoyo"

# Directorio oficial de Maestras y Maestros de Apoyo por escuela (Ciclo 2026-2027)
DOCENTES_APOYO_POR_ESCUELA: dict[str, str] = {
    "Damián Carmona": "Mtra. Personal ficticio 03",
    "Ichcaanziho": "Mtra. Personal ficticio 19",
    "Gregorio Torres Quintero": "Mtra. Personal ficticio 07",
    "Remigio Aguilar Sosa": "Mtra. Personal ficticio 05",
    "Elvira Parra Ávila": "Mtro. Personal ficticio 13",
    "Manuel Sarrado": "Mtra. Personal ficticio 16",
    "Domingo Solís Rodríguez": "Mtra. Personal ficticio 26",
    "Quintana Roo": "Mtro. Personal ficticio 25",
}

DOCENTES_APOYO_ALTERNOS: dict[str, list[str]] = {
    "Ichcaanziho": ["Mtra. Personal ficticio 15"],
}

# Especialistas por Función y Zona Escolar
ESPECIALISTAS_POR_AREA: dict[str, dict[str, str]] = {
    "PSICOLOGIA": {
        "Damián Carmona": "Psic. Personal ficticio 17",
        "Ichcaanziho": "Psic. Personal ficticio 17",
        "Elvira Parra Ávila": "Psic. Personal ficticio 17",
        "Quintana Roo": "Psic. Personal ficticio 17",
        "Gregorio Torres Quintero": "Psic. Personal ficticio 01",
        "Remigio Aguilar Sosa": "Psic. Personal ficticio 01",
        "Manuel Sarrado": "Psic. Personal ficticio 01",
        "Domingo Solís Rodríguez": "Psic. Personal ficticio 01",
    },
    "COMUNICACION": {
        "Damián Carmona": "Lic. Personal ficticio 10",
        "Ichcaanziho": "Lic. Personal ficticio 10",
        "Elvira Parra Ávila": "Lic. Personal ficticio 10",
        "Quintana Roo": "Lic. Personal ficticio 10",
        "Gregorio Torres Quintero": "Lic. Personal ficticio 18",
        "Remigio Aguilar Sosa": "Lic. Personal ficticio 18",
        "Manuel Sarrado": "Lic. Personal ficticio 18",
        "Domingo Solís Rodríguez": "Lic. Personal ficticio 18",
    },
    "TRABAJO_SOCIAL": {
        "__todas__": "LTS. Personal ficticio 06",
    },
}

CARGOS_POR_AREA: dict[str, str] = {
    "PSICOLOGIA": "Área de Psicología",
    "COMUNICACION": "Área de Comunicación",
    "TRABAJO_SOCIAL": "Trabajo Social",
    "APOYO_MASCULINO": "Maestro de Apoyo",
    "APOYO_FEMENINO": "Maestra de Apoyo",
}

# Mapeo inverso de nombres normalizados a nombres formales oficiales
NOMBRES_FORMALES: dict[str, str] = {
    "PERSONAL FICTICIO 03": "Mtra. Personal ficticio 03",
    "PERSONAL FICTICIO 19": "Mtra. Personal ficticio 19",
    "PERSONAL FICTICIO 15": "Mtra. Personal ficticio 15",
    "PERSONAL FICTICIO 07": "Mtra. Personal ficticio 07",
    "PERSONAL FICTICIO 05": "Mtra. Personal ficticio 05",
    "PERSONAL FICTICIO 13": "Mtro. Personal ficticio 13",
    "PERSONAL FICTICIO 16": "Mtra. Personal ficticio 16",
    "PERSONAL FICTICIO 26": "Mtra. Personal ficticio 26",
    "PERSONAL FICTICIO 25": "Mtro. Personal ficticio 25",
    "PERSONAL FICTICIO 17": "Psic. Personal ficticio 17",
    "PERSONAL FICTICIO 01": "Psic. Personal ficticio 01",
    "PERSONAL FICTICIO 10": "Lic. Personal ficticio 10",
    "PERSONAL FICTICIO 18": "Lic. Personal ficticio 18",
    "PERSONAL FICTICIO 06": "LTS. Personal ficticio 06",
    "PERSONAL FICTICIO 09": "Psic. Personal ficticio 11",
}


def _normalizar_identidad(texto_entrada: str | None) -> str:
    if not texto_entrada:
        return ""
    n = normalizar_texto(texto_entrada)
    # Retirar títulos previos si los tiene
    n = re.sub(r"\b(MTRA|MTRO|LIC|PSIC|LTS|DR|DRA|MD|DOCENTE|ESPECIALISTA)\b", "", n)
    return " ".join(n.replace(".", " ").split())


def canonizar_escuela(escuela_o_id: str | None) -> str:
    """Convierte un código ESC-00X o nombre parcial a la escuela canónica."""
    if not escuela_o_id:
        return ""
    entrada = str(escuela_o_id).strip()
    # Coincidencia directa por código
    for nombre, codigo in ESCUELAS_USAER.items():
        if entrada.upper() == codigo.upper() or entrada.upper() == nombre.upper():
            return nombre
    # Búsqueda por texto normalizado
    norm = normalizar_texto(entrada)
    for nombre in ESCUELAS_USAER:
        if normalizar_texto(nombre) in norm or norm in normalizar_texto(nombre):
            return nombre
    return entrada


def clasificar_area(doc: Mapping[str, Any]) -> str:
    """Clasifica la función del documento: TRABAJO_SOCIAL, PSICOLOGIA, COMUNICACION o APOYO."""
    meta = doc.get("metadatos", {}) if isinstance(doc.get("metadatos"), dict) else {}
    meta_area = normalizar_texto(str(meta.get("area", "") or ""))
    if any(k in meta_area for k in ("TRABAJO", "SOCIAL", "TS")):
        return "TRABAJO_SOCIAL"
    if any(k in meta_area for k in ("PSIC", "PSICOLOG")):
        return "PSICOLOGIA"
    if any(k in meta_area for k in ("COM", "COMUNICAC")):
        return "COMUNICACION"

    datos = doc.get("datos", {}) if isinstance(doc.get("datos"), dict) else {}
    funcion = normalizar_texto(str(datos.get("Función", "") or datos.get("Funcion", "") or ""))
    autor = normalizar_texto(str(datos.get("Nombre del especialista", "") or meta.get("autor", "") or doc.get("cuenta", "") or ""))

    if any(k in funcion for k in ("TRABAJO", "SOCIAL", "TS")) or "PERALTA" in autor:
        return "TRABAJO_SOCIAL"
    if any(k in funcion for k in ("PSIC", "PSICOLOG")) or any(k in autor for k in ("CUPUL", "CHABLE")):
        return "PSICOLOGIA"
    if any(k in funcion for k in ("COM", "COMUNICAC")) or any(k in autor for k in ("PUERTO GONE", "PEREZ LIZAMA")):
        return "COMUNICACION"

    formato = str(doc.get("formato", "")).strip().upper()
    if formato == "XXV":
        return "TRABAJO_SOCIAL"
    return "APOYO"


def resolver_firmante_docente(doc: Mapping[str, Any]) -> tuple[str, str]:
    """
    Resuelve (nombre_completo, cargo) del docente o especialista que elaboró
    la planeación, verificando la escuela asignada, función y rol.
    """
    area = clasificar_area(doc)
    datos = doc.get("datos", {}) if isinstance(doc.get("datos"), dict) else {}
    meta = doc.get("metadatos", {}) if isinstance(doc.get("metadatos"), dict) else {}
    escuela = canonizar_escuela(
        datos.get("ID_Escuela")
        or datos.get("Escuela regular")
        or datos.get("Escuela")
        or datos.get("escuela")
    )

    autor_raw = str(
        datos.get("Nombre del especialista", "")
        or meta.get("autor", "")
        or doc.get("cuenta", "")
        or ""
    ).strip()
    autor_norm = _normalizar_identidad(autor_raw)

    # 1. Caso Trabajo Social:
    if area == "TRABAJO_SOCIAL":
        return ESPECIALISTAS_POR_AREA["TRABAJO_SOCIAL"]["__todas__"], CARGOS_POR_AREA["TRABAJO_SOCIAL"]

    # 2. Caso Psicología:
    if area == "PSICOLOGIA":
        cargo = CARGOS_POR_AREA["PSICOLOGIA"]
        # Si el autor coincide directamente con una psicóloga
        for clave_norm, nombre_formal in NOMBRES_FORMALES.items():
            if "PSIC" in nombre_formal and clave_norm in autor_norm:
                return nombre_formal, cargo
        # Búsqueda por escuela
        if escuela in ESPECIALISTAS_POR_AREA["PSICOLOGIA"]:
            return ESPECIALISTAS_POR_AREA["PSICOLOGIA"][escuela], cargo
        # Default
        return "Psic. Personal ficticio 17", cargo

    # 3. Caso Comunicación:
    if area == "COMUNICACION":
        cargo = CARGOS_POR_AREA["COMUNICACION"]
        for clave_norm, nombre_formal in NOMBRES_FORMALES.items():
            if "Lic." in nombre_formal and clave_norm in autor_norm:
                return nombre_formal, cargo
        if escuela in ESPECIALISTAS_POR_AREA["COMUNICACION"]:
            return ESPECIALISTAS_POR_AREA["COMUNICACION"][escuela], cargo
        return "Lic. Personal ficticio 10", cargo

    # 4. Caso Aprendizaje / Docente de Apoyo:
    # Si el autor guardado es un nombre docente reconocido (y no el director ni un correo):
    if autor_norm and normalizar_texto(DIRECTOR_USAER) != autor_norm and "@" not in autor_raw:
        for clave_norm, nombre_formal in NOMBRES_FORMALES.items():
            if ("Mtra." in nombre_formal or "Mtro." in nombre_formal) and (clave_norm in autor_norm or autor_norm in clave_norm):
                cargo = CARGOS_POR_AREA["APOYO_MASCULINO"] if "Mtro." in nombre_formal else CARGOS_POR_AREA["APOYO_FEMENINO"]
                return nombre_formal, cargo

    # Revisar si los alumnos del padrón traen 'Maestro de apoyo'
    alumnos = datos.get("Alumnos", [])
    if isinstance(alumnos, list):
        for al in alumnos:
            if isinstance(al, dict) and al.get("Maestro de apoyo"):
                m_norm = _normalizar_identidad(al["Maestro de apoyo"])
                for clave_norm, nombre_formal in NOMBRES_FORMALES.items():
                    if clave_norm in m_norm or m_norm in clave_norm:
                        cargo = CARGOS_POR_AREA["APOYO_MASCULINO"] if "Mtro." in nombre_formal else CARGOS_POR_AREA["APOYO_FEMENINO"]
                        return nombre_formal, cargo

    # Revisar alternos en la escuela (ej. Cecilia Solís en Ichcaanziho)
    if escuela in DOCENTES_APOYO_ALTERNOS:
        for alterno in DOCENTES_APOYO_ALTERNOS[escuela]:
            if _normalizar_identidad(alterno) in autor_norm:
                return alterno, CARGOS_POR_AREA["APOYO_FEMENINO"]

    # Por escuela oficial
    if escuela in DOCENTES_APOYO_POR_ESCUELA:
        nombre = DOCENTES_APOYO_POR_ESCUELA[escuela]
        cargo = CARGOS_POR_AREA["APOYO_MASCULINO"] if "Mtro." in nombre else CARGOS_POR_AREA["APOYO_FEMENINO"]
        return nombre, cargo

    # Fallback si el autor es un nombre válido de persona
    if autor_raw and "@" not in autor_raw and normalizar_texto(DIRECTOR_USAER) != autor_norm:
        return autor_raw, CARGOS_POR_AREA["APOYO_FEMENINO"]

    return "Nombre y firma del Especialista", "Servicio de Apoyo"


def resolver_firmas_planeacion(doc: Mapping[str, Any]) -> dict[str, str]:
    """
    Devuelve las firmas completas para la planeación (editor vivo y PDF):
    - 'especialista_nombre': Nombre oficial del especialista o maestro.
    - 'especialista_cargo': Cargo o función oficial.
    - 'director_nombre': Nombre oficial del director.
    - 'director_cargo': Leyenda de Vo. Bo. Director.
    - 'firma': Texto formateado con salto de línea para el especialista.
    - 'vobo': Texto formateado con salto de línea para Dirección.
    """
    nombre_esp, cargo_esp = resolver_firmante_docente(doc)
    nombre_dir = DIRECTOR_USAER
    cargo_dir = CARGO_DIRECTOR_USAER

    firma_esp = f"{nombre_esp}\n{cargo_esp}" if cargo_esp else nombre_esp
    vobo_dir = f"{nombre_dir}\n{cargo_dir}"

    return {
        "especialista_nombre": nombre_esp,
        "especialista_cargo": cargo_esp,
        "director_nombre": nombre_dir,
        "director_cargo": cargo_dir,
        "firma": firma_esp,
        "vobo": vobo_dir,
    }

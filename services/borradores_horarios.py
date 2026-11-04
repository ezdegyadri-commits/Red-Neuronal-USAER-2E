"""Borradores privados, persistentes y versionados; no modifican horarios publicados."""
import json
from datetime import datetime
from uuid import uuid4

import streamlit as st

from data.google import retry_google
from services.asignaciones import escuelas_asignadas
from services.horarios import _leer, _ws, ZONA
from utils.text import normalizar_texto

HOJA = "Borradores_Horarios"
HEADERS = ["ID_Version", "Guardado_En", "Maestra", "Escuela", "Datos_JSON"]


def _autorizar(nombre, escuela):
    cuenta = str(st.session_state.get("nombre", ""))
    rol = str(st.session_state.get("rol", ""))
    if (not cuenta or normalizar_texto(cuenta) != normalizar_texto(nombre)
            or "APOYO" not in normalizar_texto(rol)
            or normalizar_texto(escuela) not in {
                normalizar_texto(e) for e in escuelas_asignadas(cuenta, rol)
            }):
        raise PermissionError("El borrador pertenece a otra cuenta o escuela.")


def cargar_borrador(nombre, escuela):
    _autorizar(nombre, escuela)
    _, _, rows = _leer(HOJA, HEADERS)
    for row in reversed(rows):
        if (normalizar_texto(row.get("Maestra", "")) == normalizar_texto(nombre)
                and normalizar_texto(row.get("Escuela", "")) == normalizar_texto(escuela)):
            datos = json.loads(row.get("Datos_JSON", ""))
            if not isinstance(datos, dict):
                raise ValueError("El borrador guardado no es válido; se conserva sin sobrescribirlo.")
            return datos
    return {}


def guardar_borrador(nombre, escuela, datos):
    _autorizar(nombre, escuela)
    texto = json.dumps(datos, ensure_ascii=False, sort_keys=True)
    if len(texto) > 45000:
        raise ValueError("El borrador excede el tamaño permitido; no se modificó la versión anterior.")
    ws = _ws(HOJA, HEADERS)
    retry_google(lambda: ws.append_rows([
        [uuid4().hex, datetime.now(ZONA).isoformat(timespec="seconds"), nombre, escuela, texto]
    ], value_input_option="RAW"))
    return texto

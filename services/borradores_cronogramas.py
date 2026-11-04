"""Respaldo privado y aditivo del cronograma en edición; nunca publica avisos."""
import json
from datetime import datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

import streamlit as st
from data.google import ensure_headers, retry_google
from services.cronogramas import perfil_especialista, lugares_cronograma, _registros_cache, _iso_fecha
from utils.text import normalizar_texto

HOJA = "Borradores_Cronogramas"
HEADERS = ["ID_Version", "Guardado_En", "Especialista", "Mes", "Dias_JSON"]


def _autorizar(nombre, mes):
    p = perfil_especialista(st.session_state.get("nombre", ""), st.session_state.get("rol", ""))
    if not p or p["nombre"] != nombre:
        raise PermissionError("El borrador pertenece a otra cuenta.")
    datetime.strptime(mes, "%Y-%m")
    return p


@st.cache_resource(ttl=600, show_spinner=False)
def _hoja():
    return ensure_headers(HOJA, HEADERS)


@st.cache_data(ttl=60, show_spinner=False)
def _registros():
    values = retry_google(_hoja().get_all_values)
    return [dict(zip(values[0], row)) for row in values[1:]] if values else []


def cargar_borrador(nombre, mes, agenda_publicada=None):
    _autorizar(nombre, mes)
    for row in reversed(_registros()):
        if row.get("Especialista") == nombre and row.get("Mes") == mes:
            datos = json.loads(row["Dias_JSON"])
            if not isinstance(datos, dict):
                raise ValueError("El respaldo no tiene un formato válido.")
            if agenda_publicada is not None and datos != agenda_publicada:
                # Un respaldo anterior no puede reemplazar una publicación posterior.
                _, publicaciones = _registros_cache()
                propias = [r for r in publicaciones if r.get("Especialista") == nombre and _iso_fecha(r.get("Fecha")).startswith(mes)]
                if propias:
                    marca = propias[-1].get("Marca temporal", "")
                    for formato in ("%d/%m/%Y %H:%M:%S.%f", "%d/%m/%Y %H:%M:%S"):
                        try:
                            publicada = datetime.strptime(marca, formato).replace(tzinfo=ZoneInfo("America/Mexico_City"))
                            if datetime.fromisoformat(row["Guardado_En"]) <= publicada:
                                return None
                            break
                        except (ValueError, KeyError):
                            continue
            return datos
    return None  # Un mes borrado explícitamente ({}) es distinto de no tener respaldo.


def guardar_borrador(nombre, mes, dias):
    p = _autorizar(nombre, mes)
    permitidas = {normalizar_texto(e) for e in [*p["escuelas"], *lugares_cronograma(p)]}
    for fecha, datos in dias.items():
        if not fecha.startswith(mes + "-"):
            raise ValueError("El borrador contiene otro mes.")
        datetime.strptime(fecha, "%Y-%m-%d")
        if datos.get("escuela") and normalizar_texto(datos["escuela"]) not in permitidas:
            raise PermissionError("Esta escuela no está asignada a tu cuenta.")
    texto = json.dumps(dias, ensure_ascii=False, sort_keys=True)
    if len(texto) > 45000:
        raise ValueError("Resume las actividades para respaldar el mes.")
    ws = _hoja()
    # Sin leer encabezados en cada campo: la hoja se prepara una sola vez.
    retry_google(lambda: ws.append_rows([[uuid4().hex, datetime.now(ZoneInfo("America/Mexico_City")).isoformat(timespec="seconds"), nombre, mes, texto]], value_input_option="RAW"))
    _registros.clear()
    return texto

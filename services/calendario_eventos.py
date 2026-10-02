"""Avisos informativos comunes, separados de las restricciones de horario."""
from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

import streamlit as st
from gspread import WorksheetNotFound

from data.google import worksheet, ensure_headers, retry_google
from services.cronogramas import perfil_especialista

HOJA = "Eventos_Calendario"
HEADERS = ["ID_Evento", "Revision", "Guardado_En", "Autor", "Fecha", "Titulo", "Detalle", "Origen"]
FUENTE = Path(__file__).resolve().parents[1] / "config" / "calendario_actividades_2026_2027.json"


def calendario_base():
    return json.loads(FUENTE.read_text(encoding="utf-8"))


@st.cache_data(ttl=30, show_spinner=False)
def _eventos_guardados():
    # Consultar no crea hojas ni registros. Solo Dirección puede escribir.
    try:
        ws = worksheet(HOJA)
    except WorksheetNotFound:
        return []
    values = retry_google(ws.get_all_values)
    if not values:
        return []
    headers = values[0]
    return [dict(zip(headers, row + [""] * (len(headers) - len(row)))) for row in values[1:]]


def eventos_vigentes(registros):
    latest = {e["ID_Evento"]: dict(e) for e in calendario_base()["eventos"]}
    for row in registros:
        if not row.get("ID_Evento"):
            continue
        try:
            date.fromisoformat(row.get("Fecha", ""))
        except (TypeError, ValueError):
            continue
        latest[row["ID_Evento"]] = dict(row)
    return sorted(latest.values(), key=lambda e: (e["Fecha"], e["Titulo"], e["ID_Evento"]))


def cargar_eventos(mes):
    date.fromisoformat(mes + "-01")
    return [e for e in eventos_vigentes(_eventos_guardados()) if e["Fecha"].startswith(mes + "-")]


def guardar_evento(fecha, titulo, detalle="", id_evento=None, revision_esperada=None):
    perfil = perfil_especialista(st.session_state.get("nombre", ""), st.session_state.get("rol", ""))
    if not perfil or perfil["area"] != "Dirección":
        raise PermissionError("Solo Dirección puede publicar eventos para el equipo.")
    fecha = date.fromisoformat(str(fecha)).isoformat()
    titulo, detalle = str(titulo).strip(), str(detalle).strip()
    if not titulo:
        raise ValueError("Escribe el nombre de la actividad.")
    if len(titulo) > 300 or len(detalle) > 3000:
        raise ValueError("Resume el nombre y los detalles de la actividad.")
    _eventos_guardados.clear()
    existentes = eventos_vigentes(_eventos_guardados())
    anterior = next((e for e in existentes if e["ID_Evento"] == id_evento), None)
    if revision_esperada is not None and (not anterior or anterior.get("Revision") != revision_esperada):
        raise ValueError("Este evento cambió en otra sesión. Recarga antes de editarlo.")
    # Reenviar el mismo formulario no duplica el evento ni su versión.
    if anterior and (anterior["Fecha"], anterior["Titulo"], anterior.get("Detalle", "")) == (fecha, titulo, detalle):
        return anterior["ID_Evento"]
    row = {"ID_Evento": id_evento or uuid4().hex, "Revision": uuid4().hex,
           "Guardado_En": datetime.now(ZoneInfo("America/Mexico_City")).isoformat(timespec="seconds"),
           "Autor": perfil["nombre"], "Fecha": fecha, "Titulo": titulo, "Detalle": detalle, "Origen": "Dirección"}
    ws = ensure_headers(HOJA, HEADERS)
    headers = retry_google(lambda: ws.row_values(1))
    retry_google(lambda: ws.append_rows([[row.get(h, "") for h in headers]], value_input_option="RAW"))
    _eventos_guardados.clear()
    return row["ID_Evento"]

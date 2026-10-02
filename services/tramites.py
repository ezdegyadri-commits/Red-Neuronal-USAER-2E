"""Solicitudes y comprobantes privados, con historial aditivo y permisos por autor."""
import base64
import hashlib
import json
from datetime import datetime
from io import BytesIO
from uuid import uuid4
from zoneinfo import ZoneInfo

import streamlit as st
from PIL import Image
from gspread import WorksheetNotFound

from data import repository as repo
from data.google import worksheet, ensure_headers, retry_google
from services.asignaciones import escuelas_asignadas
from services.cronogramas import perfil_especialista
from services.expedientes import alumnos_visibles
from utils.text import normalizar_texto
from documents.tramites import _texto

HOJA = "Tramites_Expedientes"
HEADERS = ["ID_Tramite", "Revision", "Fecha", "Solicitante", "Tipo", "Origen", "Escuela", "ID_Alumnos", "Alumnos", "Solicitud", "Estado", "Seguimiento", "ID_Oficio", "Folio", "Actualizado_Por"]
ARCHIVOS = "Tramites_Adjuntos"
AH = ["ID_Adjunto", "ID_Tramite", "Tipo", "Nombre", "Mime", "SHA256", "Total", "Indice", "Contenido", "Fecha", "Autor"]
ESTADOS = ["Recibida", "En revisión", "En preparación", "Respondida", "Entregada"]


def gestor():
    p = perfil_especialista(st.session_state.get("nombre", ""), st.session_state.get("rol", ""))
    return bool(p and (p["area"] == "Dirección" or p["nombre"] == "Diego Peralta Torres"))


def puede_solicitar():
    nombre, rol = st.session_state.get("nombre", ""), st.session_state.get("rol", "")
    return "APOYO" in normalizar_texto(rol) and bool(escuelas_asignadas(nombre, rol))


def _ahora():
    return datetime.now(ZoneInfo("America/Mexico_City")).isoformat(timespec="seconds")


def _leer(hoja):
    try:
        ws = worksheet(hoja)
    except WorksheetNotFound:
        return []
    values = retry_google(ws.get_all_values)
    if not values:
        return []
    return [dict(zip(values[0], list(row) + [""] * max(0, len(values[0]) - len(row)))) for row in values[1:]]


def _anexar(hoja, headers, rows):
    ws = ensure_headers(hoja, headers)
    cols = retry_google(lambda: ws.row_values(1))
    retry_google(lambda: ws.append_rows([[r.get(h, "") for h in cols] for r in rows], value_input_option="RAW"))


def _vigentes():
    latest = {}
    for r in _leer(HOJA):
        if r.get("ID_Tramite"):
            latest[r["ID_Tramite"]] = r
    return latest


def _visible(r):
    return gestor() or (puede_solicitar() and r.get("Tipo") == "Interna" and
                       normalizar_texto(r.get("Solicitante", "")) == normalizar_texto(st.session_state.get("nombre", "")))


def solicitudes():
    if not (gestor() or puede_solicitar()):
        raise PermissionError("Este módulo es para Trabajo Social, Dirección y maestras de apoyo.")
    return sorted([r for r in _vigentes().values() if _visible(r)], key=lambda r: r.get("Fecha", ""), reverse=True)


def consultar(identificador):
    r = _vigentes().get(identificador)
    if not r or not _visible(r):
        raise PermissionError("No tienes acceso a esta solicitud.")
    return r


def alumnos_solicitables():
    if not puede_solicitar():
        raise PermissionError("Solo las maestras de apoyo pueden solicitar sus expedientes.")
    nombre, rol = st.session_state.get("nombre", ""), st.session_state.get("rol", "")
    escuelas = escuelas_asignadas(nombre, rol)
    return alumnos_visibles(rol, ",".join(escuelas), nombre)


def crear_solicitud(tipo, solicitud, identificador, ids=None, origen="", alumnos="", referencia=""):
    solicitud = str(solicitud).strip()
    if not solicitud or len(solicitud) > 4000:
        raise ValueError("Escribe una solicitud breve (máximo 4000 caracteres).")
    if tipo == "Interna":
        df = alumnos_solicitables().fillna("")
        ids = list(dict.fromkeys(str(i) for i in ids or []))
        permitidos = set(df["ID_Alumno"].astype(str)) if "ID_Alumno" in df else set()
        if not ids or not set(ids).issubset(permitidos):
            raise PermissionError("Selecciona únicamente alumnos asignados a tu cuenta.")
        rows = df.loc[df["ID_Alumno"].astype(str).isin(ids)].to_dict("records")
        alumnos = "; ".join(str(r.get("Nombre_Completo", r.get("Nombre", ""))) for r in rows)
        escuela = "; ".join(dict.fromkeys(str(r.get("Nombre_Escuela", "")) for r in rows))
        origen = "USAER 02-E"
    elif tipo == "Externa" and gestor():
        if not str(origen).strip() or not str(alumnos).strip():
            raise ValueError("Indica la USAER/CAM solicitante y los expedientes requeridos.")
        if len(str(origen)) > 250 or len(str(alumnos)) > 4000 or len(str(referencia)) > 500:
            raise ValueError("Resume los datos de la solicitud externa.")
        escuela, ids = str(origen).strip(), []
    else:
        raise PermissionError("No puedes registrar este tipo de solicitud.")
    anterior = _vigentes().get(identificador)
    if anterior:
        if not _visible(anterior):
            raise PermissionError("Solicitud no autorizada.")
        return anterior
    row = {"ID_Tramite": identificador, "Revision": uuid4().hex, "Fecha": _ahora(),
           "Solicitante": st.session_state.get("nombre", ""), "Tipo": tipo, "Origen": str(origen).strip(),
           "Escuela": escuela, "ID_Alumnos": json.dumps(ids), "Alumnos": str(alumnos).strip(),
           "Solicitud": solicitud + ("\nReferencia: " + referencia.strip() if referencia.strip() else ""),
           "Estado": "Recibida", "Actualizado_Por": st.session_state.get("nombre", "")}
    _anexar(HOJA, HEADERS, [row])
    return row


def actualizar(identificador, revision, estado, seguimiento, oficio=None):
    if not gestor():
        raise PermissionError("Solo Trabajo Social y Dirección pueden dar seguimiento.")
    r = consultar(identificador)
    if r["Revision"] != revision:
        raise ValueError("La solicitud cambió. Recárgala antes de guardar.")
    if estado not in ESTADOS:
        raise ValueError("Selecciona un estado válido.")
    if len(str(seguimiento)) > 4000:
        raise ValueError("Resume el seguimiento (máximo 4000 caracteres).")
    r = {**r, "Revision": uuid4().hex, "Estado": estado, "Seguimiento": str(seguimiento).strip(),
         "Actualizado_Por": st.session_state.get("nombre", "")}
    if oficio:
        r.update(ID_Oficio=oficio["ID_Oficio"], Folio=str(oficio["Folio"]))
    _anexar(HOJA, HEADERS, [r])
    return r


def emitir_respuesta(identificador, destinatario, texto):
    if not gestor():
        raise PermissionError("Solo Trabajo Social y Dirección pueden preparar respuestas.")
    r = consultar(identificador)
    if not str(destinatario).strip() or not str(texto).strip():
        raise ValueError("Indica el destinatario y la respuesta.")
    if len(texto) > 4000 or len(destinatario) > 250:
        raise ValueError("Resume el destinatario o la respuesta.")
    _texto(destinatario)
    _texto(texto)
    clave = "TRAMITE-EXPEDIENTE:" + identificador
    # El mismo trámite recupera el oficio ya emitido; no vuelve a consumir folio.
    existentes = repo.oficios_comision().fillna("")
    coincidencias = existentes.loc[existentes["Clave_Operacion"].astype(str).eq(clave)] if "Clave_Operacion" in existentes else existentes.iloc[0:0]
    if not coincidencias.empty:
        oficio = coincidencias.iloc[-1].to_dict()
    else:
        oficio = repo.guardar_oficio_comision({"Clave_Operacion": clave, "Fecha_Emision": _ahora()[:10],
            "Fecha_Comision": _ahora()[:10], "Escuela": r["Escuela"], "Maestra_Apoyo": st.session_state.get("nombre", ""),
            "Director_Escuela": str(destinatario).strip(), "Asunto": "RESPUESTA A SOLICITUD DE EXPEDIENTES",
            "Destino": str(texto).strip(), "Horario": r["ID_Tramite"], "Estado": "PREPARADO PARA FIRMA"})
    if not r.get("ID_Oficio"):
        actualizar(identificador, r["Revision"], "En preparación", r.get("Seguimiento", ""), oficio)
    return oficio


def oficio_guardado(identificador):
    r = consultar(identificador)
    rows = repo.oficios_comision().fillna("")
    clave = "TRAMITE-EXPEDIENTE:" + identificador
    encontrados = rows.loc[rows["Clave_Operacion"].astype(str).eq(clave)] if "Clave_Operacion" in rows else rows.iloc[0:0]
    if encontrados.empty:
        raise ValueError("Aún no hay un oficio de respuesta registrado.")
    return encontrados.iloc[-1].to_dict()


def _archivos_completos(identificador):
    grupos = {}
    for row in _leer(ARCHIVOS):
        if row.get("ID_Tramite") == identificador:
            grupos.setdefault(row.get("ID_Adjunto"), {})[row.get("Indice")] = row
    return {key: rows for key, rows in grupos.items() if rows and len(rows) == int(next(iter(rows.values())).get("Total", 0))}


def guardar_imagen(identificador, tipo, nombre, contenido):
    consultar(identificador)
    if not gestor():
        raise PermissionError("Solo Trabajo Social y Dirección pueden anexar oficios recibidos y acuses.")
    if tipo not in {"Oficio recibido", "Acuse de recibido"}:
        raise ValueError("Tipo de documento no válido.")
    if not contenido or len(contenido) > 5 * 1024 * 1024:
        raise ValueError("Elige una imagen de hasta 5 MB.")
    with Image.open(BytesIO(contenido)) as image:
        formato = image.format
        if formato not in {"JPEG", "PNG", "WEBP"}:
            raise ValueError("Usa una imagen JPG, PNG o WEBP.")
        image.verify()
    digest = hashlib.sha256(contenido).hexdigest()
    key = hashlib.sha256((identificador + tipo + digest).encode()).hexdigest()
    if key in _archivos_completos(identificador):
        return key
    encoded = base64.b64encode(contenido).decode("ascii")
    trozos = [encoded[i:i + 30000] for i in range(0, len(encoded), 30000)]
    # Privado en la base institucional. No crea enlaces públicos ni depende de OAuth Drive.
    mime = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}[formato]
    _anexar(ARCHIVOS, AH, [{"ID_Adjunto": key, "ID_Tramite": identificador, "Tipo": tipo,
        "Nombre": str(nombre).replace("\\", "/").split("/")[-1], "Mime": mime, "SHA256": digest,
        "Total": str(len(trozos)), "Indice": str(i), "Contenido": chunk,
        "Fecha": _ahora(), "Autor": st.session_state.get("nombre", "")} for i, chunk in enumerate(trozos)])
    return key


def adjuntos(identificador):
    consultar(identificador)
    salida = []
    for key, rows in _archivos_completos(identificador).items():
        primero = next(iter(rows.values()))
        salida.append({k: primero.get(k, "") for k in ("ID_Adjunto", "Tipo", "Nombre", "Mime", "Fecha")})
    return salida


def descargar_imagen(identificador, adjunto):
    consultar(identificador)  # Guardar/consultar un ID ajeno nunca permite leer el archivo.
    rows = _archivos_completos(identificador).get(adjunto)
    if not rows:
        raise ValueError("El documento no está disponible.")
    first = next(iter(rows.values()))
    data = base64.b64decode("".join(rows[str(i)]["Contenido"] for i in range(int(first["Total"]))), validate=True)
    if hashlib.sha256(data).hexdigest() != first["SHA256"]:
        raise ValueError("El documento está incompleto. Vuelve a cargarlo.")
    return data

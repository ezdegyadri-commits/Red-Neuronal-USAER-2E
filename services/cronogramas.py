"""Lectura y escritura aditiva del historial de cronogramas USAER."""

from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from config.settings import CRONOGRAMAS_SPREADSHEET_ID, ESCUELAS_USAER
from data.google import drive_oauth_google_client, retry_google, service_account_client
from services.asignaciones import ASIGNACIONES_ESPECIALISTAS, es_direccion, es_especialista, escuelas_asignadas
from utils.text import normalizar_texto


ENCABEZADOS_CRONOGRAMA = [
    "Marca temporal", "Especialista", "Área", "Modalidad", "Escuela",
    "Fecha", "Actividad", "Estado", "ID_Publicacion",
]

AREAS_ESPECIALISTAS = {
    "MARIA JOSE CUPUL REALPOZO": "Psicología",
    "ABRIL DE MARIA CHABLE RIOS": "Psicología",
    "ELMY LUCELLY PUERTO GONE": "Comunicación",
    "MARILYN PEREZ LIZAMA": "Comunicación",
    "DIEGO PERALTA TORRES": "Trabajo Social",
}

NOMBRES_ESPECIALISTAS = {
    "MARIA JOSE CUPUL REALPOZO": "María José Cupul Realpozo",
    "ABRIL DE MARIA CHABLE RIOS": "Abril de María Chable Ríos",
    "ELMY LUCELLY PUERTO GONE": "Elmy Lucelly Puerto Gone",
    "MARILYN PEREZ LIZAMA": "Marilyn Pérez Lizama",
    "DIEGO PERALTA TORRES": "Diego Peralta Torres",
}

DIAS_INHABILES = {}

# Calendario Escolar 2026-2027, Educación Básica, SEGEY Yucatán.
# Se guardan solo días hábiles dentro de los recesos; fines de semana ya se
# excluyen por separado en fechas_habiles().
def _registrar_rango_inhabil(inicio: str, fin: str, motivo: str) -> None:
    fecha = date.fromisoformat(inicio)
    limite = date.fromisoformat(fin)
    while fecha <= limite:
        if fecha.weekday() < 5:
            DIAS_INHABILES[fecha.isoformat()] = motivo
        fecha = date.fromordinal(fecha.toordinal() + 1)


def _registrar_dia_inhabil(fecha: str, motivo: str) -> None:
    DIAS_INHABILES[fecha] = motivo


_registrar_rango_inhabil("2026-08-03", "2026-08-21", "Receso escolar de verano")
_registrar_rango_inhabil("2026-08-24", "2026-08-28", "Consejo Técnico Escolar, fase intensiva")
_registrar_dia_inhabil("2026-09-16", "Suspensión de labores docentes")
_registrar_dia_inhabil("2026-09-25", "Consejo Técnico Escolar")
_registrar_dia_inhabil("2026-10-30", "Consejo Técnico Escolar")
_registrar_dia_inhabil("2026-11-02", "Suspensión de labores docentes")
_registrar_dia_inhabil("2026-11-16", "Suspensión de labores docentes")
_registrar_dia_inhabil("2026-11-27", "Consejo Técnico Escolar")
_registrar_rango_inhabil("2026-12-21", "2026-12-31", "Receso escolar de invierno")
_registrar_rango_inhabil("2027-01-01", "2027-01-05", "Receso escolar de invierno")
_registrar_dia_inhabil("2027-01-06", "Suspensión de labores docentes")
_registrar_dia_inhabil("2027-01-29", "Consejo Técnico Escolar")
_registrar_dia_inhabil("2027-02-01", "Suspensión de labores docentes")
_registrar_dia_inhabil("2027-02-26", "Consejo Técnico Escolar")
_registrar_dia_inhabil("2027-03-15", "Suspensión de labores docentes")
_registrar_rango_inhabil("2027-03-22", "2027-04-02", "Receso escolar de primavera")
_registrar_dia_inhabil("2027-04-30", "Consejo Técnico Escolar")
_registrar_dia_inhabil("2027-05-05", "Suspensión de labores docentes")
_registrar_dia_inhabil("2027-05-28", "Consejo Técnico Escolar")
_registrar_dia_inhabil("2027-06-25", "Consejo Técnico Escolar")
_registrar_rango_inhabil("2027-07-10", "2027-07-31", "Receso escolar de verano")


def perfil_especialista(nombre: str, rol: str) -> dict | None:
    """Resuelve perfiles autorizados del equipo especialista y de Dirección."""
    # En la hoja Usuarios algunos nombres llevan el prefijo de la función
    # (p. ej. "Com." o "Psic."). Retíralo para buscar el nombre canónico,
    # conservando la lista cerrada de especialistas autorizados.
    tokens = normalizar_texto(nombre).replace(".", " ").split()
    prefijos = {"COM", "COMUNICACION", "PSIC", "PSICOLOGA", "PSICOLOGO", "TS", "DIRECTOR", "LIC", "LTS", "MTRO", "MTRA"}
    if tokens[:2] == ["T", "S"]:
        tokens = tokens[2:]
    while tokens and tokens[0] in prefijos:
        tokens = tokens[1:]
    llave = " ".join(tokens).strip()

    # Diego está autorizado por Dirección, aunque Usuarios use una etiqueta
    # de rol distinta. La identidad completa evita habilitar otras cuentas.
    if llave == "DIEGO PERALTA TORRES":
        return {
            "nombre": "Diego Peralta Torres",
            "area": "Trabajo Social",
            "escuelas": list(ESCUELAS_USAER.keys()),
        }

    # Dirección genera su propio cronograma y consulta el mismo calendario
    # consolidado del equipo. La lista cerrada evita habilitar cuentas ajenas.
    if es_direccion(rol):
        nombres_direccion = {
            "EDGAR ADRIAN YAM BRICENO",
            "EDGAR ADRIAN YAM BRICENO MD",
        }
        if llave not in nombres_direccion:
            return None
        return {
            "nombre": "Psic. Edgar Adrián Yam Briceño MD",
            "area": "Dirección",
            "escuelas": list(ESCUELAS_USAER.keys()),
        }

    if not es_especialista(rol):
        return None
    for nombre_directorio, escuelas in ASIGNACIONES_ESPECIALISTAS.items():
        if llave == normalizar_texto(nombre_directorio).replace(".", "").strip():
            area = AREAS_ESPECIALISTAS.get(normalizar_texto(nombre_directorio))
            if not area:
                return None
            return {
                "nombre": NOMBRES_ESPECIALISTAS[normalizar_texto(nombre_directorio)],
                "area": area,
                "escuelas": list(escuelas),
            }
    return None


def lugares_cronograma(perfil):
    """Destinos adicionales sin ampliar las escuelas del especialista."""
    if perfil["area"] == "Dirección":
        return ["Sede", "Junta de Zona", "Junta de USAER", "Reunión Académica", "Junta General (Sede)"]
    return ["Junta General (Sede)"]


def fechas_habiles(mes: str) -> list[date]:
    """Fechas de lunes a viernes que no estén marcadas como inhábiles oficiales."""
    try:
        anio, numero_mes = (int(valor) for valor in mes.split("-", 1))
        inicio = date(anio, numero_mes, 1)
    except (TypeError, ValueError):
        raise ValueError("Selecciona un mes válido en formato AAAA-MM.")
    if numero_mes == 12:
        fin = date(anio + 1, 1, 1)
    else:
        fin = date(anio, numero_mes + 1, 1)
    dias = []
    actual = inicio
    while actual < fin:
        if actual.weekday() < 5 and actual.isoformat() not in DIAS_INHABILES:
            dias.append(actual)
        actual = date.fromordinal(actual.toordinal() + 1)
    return dias


@st.cache_resource(ttl=600, show_spinner=False)
def _worksheet():
    errores = []
    # Preferir la cuenta de servicio para evitar depender del token OAuth de
    # Drive, que puede vencer o revocarse. Esta credencial abre directamente
    # libros compartidos y no requiere acceder al atributo interno del libro maestro.
    try:
        libro = service_account_client().open_by_key(CRONOGRAMAS_SPREADSHEET_ID)
        return retry_google(lambda: libro.worksheet("Registros"))
    except Exception as exc:
        if "429" in str(exc) or "quota exceeded" in str(exc).lower():
            raise  # Una cuota agotada no es un fallo de autenticación.
        errores.append(("cuenta de servicio", exc))
    try:
        libro = drive_oauth_google_client().open_by_key(CRONOGRAMAS_SPREADSHEET_ID)
        return retry_google(lambda: libro.worksheet("Registros"))
    except Exception as exc:
        errores.append(("Drive OAuth", exc))
        detalle = "; ".join(
            f"{metodo}: {_resumen_error(error)}" for metodo, error in errores
        )
        raise RuntimeError(
            "No se pudo autenticar contra el libro de cronogramas. "
            f"Diagnóstico: {detalle}. La pestaña 'Registros' existe. "
            "Si aparece permiso insuficiente o archivo no visible, en Streamlit Cloud abre Manage app > Settings > "
            "Secrets, copia el campo client_email dentro de credenciales_json y comparte "
            "con esa cuenta el libro de cronogramas como Editor. Si Drive OAuth reporta "
            "invalid_grant, vuelve a autorizar/actualizar token_json y reinicia la app. "
            f"Libro: https://docs.google.com/spreadsheets/d/{CRONOGRAMAS_SPREADSHEET_ID}/edit"
        ) from exc


def _resumen_error(exc: Exception) -> str:
    """Clasifica el error de Google sin mostrar tokens ni datos de credenciales."""
    response = getattr(exc, "response", None)
    status = getattr(response, "status_code", None) or getattr(exc, "code", None)
    texto = str(exc).lower()
    if "invalid_grant" in texto or "expired or revoked" in texto:
        return "token OAuth inválido o vencido (invalid_grant)"
    if status == 403 or "permission denied" in texto or "insufficient permission" in texto:
        return "permiso insuficiente (HTTP 403)"
    if status == 404 or "spreadsheet not found" in texto or "file not found" in texto:
        return "archivo no visible para esta credencial (HTTP 404)"
    if "worksheetnotfound" in texto or "worksheet not found" in texto:
        return "no se encontró la pestaña solicitada"
    if status:
        return f"error de Google HTTP {status}"
    return type(exc).__name__


def _leer_registros():
    ws = _worksheet()
    values = retry_google(lambda: ws.get_all_values())
    if not values:
        return ws, [], []
    headers = [str(value).strip() for value in values[0]]
    registros = []
    for numero_fila, raw in enumerate(values[1:], start=2):
        padded = (list(raw) + [""] * max(0, len(headers) - len(raw)))[:len(headers)]
        fila = dict(zip(headers, padded))
        fila["_fila"] = numero_fila
        if any(str(value).strip() for key, value in fila.items() if key != "_fila"):
            registros.append(fila)
    return ws, headers, registros


@st.cache_data(ttl=60, show_spinner=False)
def _registros_cache():
    """Una lectura compartida para agenda, historial y paneles de todo el equipo."""
    _, headers, registros = _leer_registros()
    return headers, registros


def _iso_fecha(valor: object) -> str:
    texto = str(valor or "").strip().lstrip("'")
    if not texto:
        return ""
    for formato in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(texto[:10], formato).date().isoformat()
        except ValueError:
            continue
    return texto[:10]


@st.cache_data(ttl=20, show_spinner=False)
def cargar_agenda(nombre: str, mes: str) -> dict[str, dict[str, str]]:
    headers, registros = _registros_cache()
    if not {"Especialista", "Fecha", "Escuela", "Actividad"}.issubset(headers):
        raise RuntimeError("La pestaña Registros no tiene las columnas esperadas.")
    agenda = {}
    for row in _versiones_vigentes(registros, mes):
        fecha_iso = _iso_fecha(row.get("Fecha"))
        if (
            row.get("Especialista", "").strip() == nombre
            and fecha_iso.startswith(mes)
            and str(row.get("Estado", "ACTIVO") or "ACTIVO").strip().upper() != "SUSTITUIDO"
        ):
            # Ante filas históricas repetidas para una fecha, prevalece la última.
            agenda[fecha_iso] = {
                "escuela": str(row.get("Escuela", "")).strip(),
                "actividad": str(row.get("Actividad", "")).strip(),
            }
    return agenda


@st.cache_data(ttl=20, show_spinner=False)
def meses_con_cronograma(nombre: str) -> list[str]:
    """Meses propios conservados, sin limitar la recuperación a los últimos doce."""
    _, registros = _registros_cache()
    meses = set()
    for row in registros:
        if str(row.get("Especialista", "")).strip() != nombre:
            continue
        try:
            fecha = date.fromisoformat(_iso_fecha(row.get("Fecha")))
        except ValueError:
            continue
        meses.add(fecha.strftime("%Y-%m"))
    return sorted(meses, reverse=True)


def _versiones_vigentes(registros, mes):
    """Una publicación completa por autor/mes, incluso si falló marcar el historial."""
    seleccionadas = [r for r in registros if _iso_fecha(r.get("Fecha")).startswith(mes)]
    ultima = {}
    for row in seleccionadas:
        publicacion = str(row.get("ID_Publicacion", "")).strip()
        if publicacion:
            ultima[normalizar_texto(row.get("Especialista", ""))] = publicacion
    return [r for r in seleccionadas
            if str(r.get("Estado", "ACTIVO") or "ACTIVO").upper() not in {"SUSTITUIDO", "VACIO"}
            and (normalizar_texto(r.get("Especialista", "")) not in ultima
                 or str(r.get("ID_Publicacion", "")).strip() == ultima[normalizar_texto(r.get("Especialista", ""))])]


@st.cache_data(ttl=20, show_spinner=False)
def cargar_agenda_global(mes: str) -> list[dict[str, str]]:
    headers, registros = _registros_cache()
    if not {"Especialista", "Fecha", "Escuela"}.issubset(headers):
        raise RuntimeError("La pestaña Registros no tiene las columnas esperadas.")
    efectivos = {}
    for row in _versiones_vigentes(registros, mes):
        fecha_iso = _iso_fecha(row.get("Fecha"))
        if (
            fecha_iso.startswith(mes)
            and str(row.get("Estado", "ACTIVO") or "ACTIVO").strip().upper() != "SUSTITUIDO"
        ):
            key = (row.get("Especialista", "").strip(), fecha_iso)
            efectivos[key] = {
                "Fecha": fecha_iso,
                "Especialista": row.get("Especialista", "").strip(),
                "Área": row.get("Área", "").strip(),
                "Escuela": row.get("Escuela", "").strip(),
                "Actividad": row.get("Actividad", "").strip(),
                "ID_Publicacion": str(row.get("ID_Publicacion", "")).strip(),
            }
    return sorted(efectivos.values(), key=lambda row: (row["Fecha"], row["Especialista"]))


@st.cache_data(ttl=30, show_spinner=False)
def cargar_publicacion(publicacion_id: str) -> list[dict[str, str]]:
    """Lee las actividades de una versión publicada del cronograma sin alterar historial."""
    headers, registros = _registros_cache()
    if "ID_Publicacion" not in headers:
        return []
    return [
        {
            "Fecha": _iso_fecha(row.get("Fecha", "")),
            "Escuela": row.get("Escuela", "").strip(),
            "Actividad": row.get("Actividad", "").strip(),
            "Especialista": row.get("Especialista", "").strip(),
        }
        for row in registros
        if str(row.get("ID_Publicacion", "")).strip() == str(publicacion_id).strip()
        and str(row.get("Estado", "ACTIVO") or "ACTIVO").strip().upper() != "SUSTITUIDO"
    ]


def guardar_agenda(nombre: str, area: str, mes: str, escuelas: list[str], agenda: list[dict]) -> dict:
    """Anexa la nueva versión y marca la anterior como sustituida, sin borrar filas."""
    mes_date = datetime.strptime(mes, "%Y-%m")
    perfil = perfil_especialista(nombre, area)
    if not perfil:
        raise PermissionError("La cuenta no está autorizada para elaborar cronogramas.")
    permitidas = {normalizar_texto(e) for e in [*perfil["escuelas"], *lugares_cronograma(perfil)]}
    dias_habiles = {f.isoformat() for f in fechas_habiles(mes)}
    filas_nuevas = []
    publicacion_id = uuid4().hex
    dias_vistos = set()
    for item in agenda:
        fecha_iso = _iso_fecha(item.get("fecha"))
        escuela = str(item.get("escuela", "")).strip()
        actividad = str(item.get("actividad", "")).strip()
        if not escuela and not actividad:
            continue
        if not fecha_iso.startswith(mes_date.strftime("%Y-%m")):
            raise ValueError("Hay una actividad cuya fecha no corresponde al mes seleccionado.")
        if fecha_iso not in dias_habiles:
            raise ValueError("No se pueden programar actividades en fines de semana, CTE o días inhábiles.")
        if normalizar_texto(escuela) not in permitidas:
            raise ValueError("La escuela seleccionada no pertenece al ámbito autorizado.")
        if not actividad:
            raise ValueError(f"Escribe la actividad del {fecha_iso} o deja vacía toda esa fila.")
        if fecha_iso in dias_vistos:
            raise ValueError("Solo puede guardarse una actividad por día en el cronograma.")
        dias_vistos.add(fecha_iso)
        filas_nuevas.append({
            "Marca temporal": datetime.now(ZoneInfo("America/Mexico_City")).strftime("%d/%m/%Y %H:%M:%S.%f"),
            "Especialista": nombre,
            "Área": area,
            "Modalidad": "Sede Base",
            "Escuela": escuela,
            "Fecha": fecha_iso,
            "Actividad": actividad,
            "Estado": "ACTIVO",
            "ID_Publicacion": publicacion_id,
        })
    ws, headers, existentes = _leer_registros()
    cantidad_actividades = len(filas_nuevas)
    if not filas_nuevas:
        if not any(row.get("Especialista", "").strip() == nombre
                   and _iso_fecha(row.get("Fecha")).startswith(mes) for row in existentes):
            raise ValueError("Agrega al menos una actividad antes de guardar.")
        # Un mes vaciado también es una versión: no reaparecen actividades viejas.
        filas_nuevas.append({
            "Marca temporal": datetime.now(ZoneInfo("America/Mexico_City")).strftime("%d/%m/%Y %H:%M:%S.%f"),
            "Especialista": nombre, "Área": area, "Fecha": f"{mes}-01",
            "Estado": "VACIO", "ID_Publicacion": publicacion_id,
        })
    requeridos = ["Especialista", "Área", "Escuela", "Fecha", "Actividad"]
    if not set(requeridos).issubset(headers):
        raise RuntimeError("La pestaña Registros no tiene las columnas esperadas.")
    if "Estado" not in headers:
        posicion = max(len(headers), 7) + 1
        if ws.col_count < posicion:
            retry_google(lambda: ws.add_cols(posicion - ws.col_count))
        retry_google(lambda: ws.update_cell(1, posicion, "Estado"))
        headers = headers + [""] * max(0, posicion - len(headers) - 1) + ["Estado"]

    if "ID_Publicacion" not in headers:
        posicion = max(len(headers), 8) + 1
        if ws.col_count < posicion:
            retry_google(lambda: ws.add_cols(posicion - ws.col_count))
        retry_google(lambda: ws.update_cell(1, posicion, "ID_Publicacion"))
        headers = headers + [""] * max(0, posicion - len(headers) - 1) + ["ID_Publicacion"]

    col_estado = headers.index("Estado") + 1
    # Primero se escribe la versión nueva. Si falla, el historial anterior sigue activo.
    retry_google(lambda: ws.append_rows(
        [[row.get(header, "") for header in headers] for row in filas_nuevas],
        value_input_option="RAW",
    ))

    columnas = []
    for row in existentes:
        fecha_iso = _iso_fecha(row.get("Fecha"))
        estado = str(row.get("Estado", "ACTIVO") or "ACTIVO").strip().upper()
        if row.get("Especialista", "").strip() == nombre and fecha_iso.startswith(mes) and estado != "SUSTITUIDO":
            columnas.append({
                "range": f"{_columna_a1(col_estado)}{row['_fila']}",
                "values": [["SUSTITUIDO"]],
            })
    aviso = ""
    if columnas:
        try:
            retry_google(lambda: ws.batch_update(columnas, value_input_option="RAW"))
        except Exception:
            aviso = "La agenda nueva se guardó; no se pudo marcar la versión anterior como sustituida. El historial se conserva y la vista usa la versión más reciente."
    _registros_cache.clear()
    cargar_publicacion.clear()
    cargar_agenda.clear()
    meses_con_cronograma.clear()
    cargar_agenda_global.clear()
    _agenda_visitas_cache.clear()
    return {"filas": cantidad_actividades, "aviso": aviso, "publicacion_id": publicacion_id}


@st.cache_data(ttl=30, show_spinner=False)
def _agenda_visitas_cache(mes):
    return cargar_agenda_global(mes)


def cargar_visitas_escuela(escuela, mes):
    """Solo expone visitas publicadas de una escuela autorizada de la cuenta."""
    nombre, rol = st.session_state.get("nombre", ""), st.session_state.get("rol", "")
    permitidas = escuelas_asignadas(nombre, rol)
    if normalizar_texto(escuela) not in {normalizar_texto(e) for e in permitidas}:
        raise PermissionError("La escuela no está asignada a esta cuenta.")
    return [r for r in _agenda_visitas_cache(mes)
            if normalizar_texto(r.get("Escuela", "")) == normalizar_texto(escuela)]


def resumir_visitas_escuela(registros, escuela):
    """Resumen sin otras escuelas, IDs internos ni cronogramas completos."""
    dias = ("Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo")
    resumen = []
    for row in registros:
        perfil = perfil_especialista(row.get("Especialista", ""), row.get("Área", ""))
        if not perfil or perfil["area"] == "Dirección":
            continue
        asignadas = {normalizar_texto(e) for e in perfil["escuelas"]}
        if normalizar_texto(escuela) not in asignadas or normalizar_texto(row.get("Escuela", "")) != normalizar_texto(escuela):
            continue
        fecha = date.fromisoformat(row["Fecha"])
        resumen.append({"Fecha": fecha.strftime("%d/%m/%Y"), "Día": dias[fecha.weekday()],
                        "Especialista": perfil["nombre"], "Área": perfil["area"],
                        "Actividad": row.get("Actividad", "")})
    return resumen


def _columna_a1(numero: int) -> str:
    letras = ""
    while numero:
        numero, resto = divmod(numero - 1, 26)
        letras = chr(65 + resto) + letras
    return letras

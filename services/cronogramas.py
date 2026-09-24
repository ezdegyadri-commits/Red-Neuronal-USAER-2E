"""Lectura y escritura aditiva del historial de cronogramas USAER."""

from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

import pandas as pd

from config.settings import CRONOGRAMAS_SPREADSHEET_ID, ESCUELAS_USAER
from data.google import connections, drive_oauth_google_client, retry_google
from services.asignaciones import ASIGNACIONES_ESPECIALISTAS, es_direccion, es_especialista
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

DIAS_INHABILES = {
    "2026-09-16": "Suspensión de labores docentes",
    "2026-09-25": "Consejo Técnico Escolar",
    "2026-10-30": "Consejo Técnico Escolar",
    "2026-11-02": "Suspensión de labores docentes",
    "2026-11-16": "Suspensión de labores docentes",
    "2026-11-27": "Consejo Técnico Escolar",
    "2026-12-25": "Suspensión de labores docentes",
}


def perfil_especialista(nombre: str, rol: str) -> dict | None:
    """Resuelve perfiles autorizados del equipo especialista y de Dirección."""
    # En la hoja Usuarios algunos nombres llevan el prefijo de la función
    # (p. ej. "Com." o "Psic."). Retíralo para buscar el nombre canónico,
    # conservando la lista cerrada de especialistas autorizados.
    tokens = normalizar_texto(nombre).replace(".", " ").split()
    prefijos = {"COM", "COMUNICACION", "PSIC", "PSICOLOGA", "PSICOLOGO", "TS", "DIRECTOR"}
    while tokens and tokens[0] in prefijos:
        tokens = tokens[1:]
    llave = " ".join(tokens).strip()

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


def _worksheet():
    errores = []
    # El libro fue creado y usado por Apps Script desde Drive. Primero se prueba
    # la identidad OAuth que ya utiliza la plataforma para Drive y después la
    # cuenta de servicio que lee la base central.
    try:
        libro = drive_oauth_google_client().open_by_key(CRONOGRAMAS_SPREADSHEET_ID)
        return retry_google(lambda: libro.worksheet("Registros"))
    except Exception as exc:
        errores.append(exc)
    try:
        libro_maestro, _ = connections()
        libro = libro_maestro.client.open_by_key(CRONOGRAMAS_SPREADSHEET_ID)
        return retry_google(lambda: libro.worksheet("Registros"))
    except Exception as exc:
        errores.append(exc)
        raise RuntimeError(
            "No se pudo abrir la pestaña Registros del libro Cronogramas con las "
            "credenciales de Drive ni con la cuenta de servicio. Verifica los permisos "
            "del archivo en Google Sheets."
        ) from errores[-1]


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


def cargar_agenda(nombre: str, mes: str) -> dict[str, dict[str, str]]:
    _, headers, registros = _leer_registros()
    if not {"Especialista", "Fecha", "Escuela", "Actividad"}.issubset(headers):
        raise RuntimeError("La pestaña Registros no tiene las columnas esperadas.")
    agenda = {}
    for row in registros:
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


def cargar_agenda_global(mes: str) -> list[dict[str, str]]:
    _, headers, registros = _leer_registros()
    if not {"Especialista", "Fecha", "Escuela"}.issubset(headers):
        raise RuntimeError("La pestaña Registros no tiene las columnas esperadas.")
    efectivos = {}
    for row in registros:
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
            }
    return sorted(efectivos.values(), key=lambda row: (row["Fecha"], row["Especialista"]))


def cargar_publicacion(publicacion_id: str) -> list[dict[str, str]]:
    """Lee las actividades de una versión publicada del cronograma sin alterar historial."""
    _, headers, registros = _leer_registros()
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
    permitidas = set(escuelas) | {"Junta General (Sede)"}
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
        if escuela not in permitidas:
            raise ValueError("La escuela seleccionada no pertenece al ámbito autorizado.")
        if not actividad:
            raise ValueError(f"Escribe la actividad del {fecha_iso} o deja vacía toda esa fila.")
        if fecha_iso in dias_vistos:
            raise ValueError("Solo puede guardarse una actividad por día en el cronograma.")
        dias_vistos.add(fecha_iso)
        filas_nuevas.append({
            "Marca temporal": datetime.now(ZoneInfo("America/Mexico_City")).strftime("%d/%m/%Y %H:%M:%S"),
            "Especialista": nombre,
            "Área": area,
            "Modalidad": "Sede Base",
            "Escuela": escuela,
            "Fecha": fecha_iso,
            "Actividad": actividad,
            "Estado": "ACTIVO",
            "ID_Publicacion": publicacion_id,
        })
    if not filas_nuevas:
        raise ValueError("Agrega al menos una actividad antes de guardar.")

    ws, headers, existentes = _leer_registros()
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
        value_input_option="USER_ENTERED",
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
    return {"filas": len(filas_nuevas), "aviso": aviso, "publicacion_id": publicacion_id}


def _columna_a1(numero: int) -> str:
    letras = ""
    while numero:
        numero, resto = divmod(numero - 1, 26)
        letras = chr(65 + resto) + letras
    return letras


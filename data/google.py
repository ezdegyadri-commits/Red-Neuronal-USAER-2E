import json, random, time
import threading
from requests.exceptions import Timeout
import gspread
import streamlit as st
import pandas as pd
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from config.settings import (
    HOJA_RESPUESTAS_PERSONAL,
    URL_SPREADSHEET_MAESTRO,
    URL_SPREADSHEET_RESPUESTAS_PERSONAL,
)

# Por petición: conexión y lectura acotadas. No reintentar escrituras ambiguas.
SHEETS_TIMEOUT = (5, 12)
_cuota_lock = threading.RLock()
_cuota_hasta = 0.0


class GoogleTemporal(RuntimeError):
    """Error operativo sin datos privados y sin descartar el borrador."""
    def __init__(self,mensaje,espera=20,cuota=False):
        self.espera=espera;self.cuota=cuota
        super().__init__(mensaje)


def _cliente_acotado(client):
    client.set_timeout(SHEETS_TIMEOUT)
    return client

def _secret_dict(name):
    value = st.secrets[name]
    if isinstance(value, str):
        try: return json.loads(value)
        except json.JSONDecodeError: return json.loads(value.replace('\\"','"').strip())
    return dict(value)

@st.cache_resource(show_spinner=False)
def connections():
    """Conexión esencial para Google Sheets.

    No solicita ni refresca Drive: un token de Drive vencido no puede impedir
    el inicio de sesión ni la lectura de la base central.
    """
    gc = _cliente_acotado(gspread.service_account_from_dict(_secret_dict('credenciales_json')))
    sheet = gc.open_by_url(URL_SPREADSHEET_MAESTRO)
    return sheet, None


@st.cache_resource(show_spinner=False)
def service_account_client():
    """Devuelve el cliente autenticado de Sheets para abrir libros distintos al central."""
    return _cliente_acotado(gspread.service_account_from_dict(_secret_dict('credenciales_json')))


@st.cache_resource(show_spinner=False)
def personal_responses_connection():
    """Abre en solo lectura la hoja vinculada al formulario de personal."""
    gc = _cliente_acotado(gspread.service_account_from_dict(_secret_dict('credenciales_json')))
    return gc.open_by_url(URL_SPREADSHEET_RESPUESTAS_PERSONAL)


@st.cache_resource(show_spinner=False)
def drive_oauth_google_client():
    """gspread client for Drive-owned workbooks using the existing Drive OAuth token."""
    token = _secret_dict('token_json')
    creds = Credentials.from_authorized_user_info(token, ['https://www.googleapis.com/auth/drive'])
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return _cliente_acotado(gspread.authorize(creds))


def _records_from_values(valores):
    if not valores:
        return []

    encabezados = []
    usados = {}
    for i, encabezado in enumerate(valores[0]):
        base = str(encabezado).strip() or f"Columna_{i + 1}"
        usados[base] = usados.get(base, 0) + 1
        encabezados.append(base if usados[base] == 1 else f"{base}_{usados[base]}")

    registros = []
    for fila in valores[1:]:
        fila = (list(fila) + [""] * len(encabezados))[:len(encabezados)]
        if any(str(valor).strip() for valor in fila):
            registros.append(dict(zip(encabezados, fila)))
    return registros


@st.cache_resource(show_spinner=False)
def drive_service():
    """Conexión opcional de Drive, usada solo por funciones que realmente la requieren."""
    token = _secret_dict('token_json')
    creds = Credentials.from_authorized_user_info(token, ['https://www.googleapis.com/auth/drive'])
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build('drive', 'v3', credentials=creds)


@st.cache_resource(show_spinner=False)
def service_account_drive_service():
    """Drive de solo lectura para recursos privados compartidos con la cuenta de servicio."""
    from google.oauth2.service_account import Credentials as ServiceAccountCredentials

    info = _secret_dict('credenciales_json')
    creds = ServiceAccountCredentials.from_service_account_info(
        info, scopes=['https://www.googleapis.com/auth/drive.readonly']
    )
    return build('drive', 'v3', credentials=creds)

def retry_google(operation, attempts=3):
    """Evita esperas de cuota dentro del hilo de edición de cada docente.

    Una cuota agotada abre una pausa compartida de 60 s. Los siguientes
    intentos fallan rápido sin generar una tormenta de consultas. El llamador
    conserva su borrador y confirma siempre mediante lectura antes del éxito.
    """
    global _cuota_hasta
    last = None
    for attempt in range(attempts):
        with _cuota_lock:
            espera_cuota = _cuota_hasta - time.monotonic()
        if espera_cuota > 0:
            raise GoogleTemporal('La conexión de Google Sheets está ocupada. Reintenta en '+str(int(espera_cuota)+1)+' segundos; no cierres una captura pendiente.',espera=int(espera_cuota)+1,cuota=True)
        try:
            return operation()
        except Exception as exc:
            last = exc
            message = str(exc).lower()
            response = getattr(exc, "response", None)
            status = getattr(response, "status_code", None)
            is_quota = (
                status == 429
                or "429" in message
                or "quota exceeded" in message
                or "resource_exhausted" in message
                or "read requests" in message
            )
            is_temporary_server_error = status in {500, 502, 503, 504}
            if is_quota:
                with _cuota_lock:_cuota_hasta=max(_cuota_hasta,time.monotonic()+60)
                raise GoogleTemporal('Google Sheets alcanzó su límite temporal de consultas. Se pausaron los reintentos durante un minuto para recuperar la conexión. Conserva tu captura y vuelve a intentar.',espera=60,cuota=True) from None
            if isinstance(exc, Timeout):
                raise GoogleTemporal('Google Sheets no respondió dentro del tiempo de espera. No se confirmó la operación; conserva la captura y reintenta sin volver a crearla.') from None
            if not (is_quota or is_temporary_server_error) or attempt == attempts - 1:
                raise
            # No insistir cada segundo contra una cuota que se repone por minuto.
            espera = min(30, 8 * (2 ** attempt)) if is_quota else min(4, 0.75 * (2 ** attempt))
            time.sleep(espera + random.uniform(0, 0.25))
    raise last


@st.cache_data(ttl=300, show_spinner=False)
def read_sheet(name):
    """
    Lee una hoja de Google Sheets de forma tolerante.

    Evita get_all_records(), ya que falla cuando existen
    encabezados duplicados o vacíos.

    NO elimina información.
    NO modifica la hoja.
    """

    def operation():

        ws = worksheet(name)

        valores = ws.get_all_values()

        return _records_from_values(valores)

    return retry_google(operation)


@st.cache_data(ttl=300, show_spinner=False)
def read_personal_responses():
    """Lee respuestas recientes del formulario sin escribir en Google Sheets."""
    def operation():
        book = personal_responses_connection()
        ws = _worksheet_cached(HOJA_RESPUESTAS_PERSONAL, id(book), book)
        return _records_from_values(ws.get_all_values())

    return retry_google(operation)

def df_sheet(name):
    return pd.DataFrame(
        read_sheet(name)
    )

def clear_cache(name=None):
    """
    Limpia el caché de lectura de Google Sheets.
    El parámetro name se conserva por compatibilidad
    con el repositorio.
    """
    if name is None:
        read_sheet.clear()
    else:
        read_sheet.clear(name)

@st.cache_resource(ttl=300,show_spinner=False)
def _worksheet_cached(name,book_id,_book):
    # Solo metadata; jamás se cachean aquí valores ni permisos de un usuario.
    return retry_google(lambda:_book.worksheet(name))


def worksheet(name):
    book=connections()[0]
    return _worksheet_cached(name,id(book),book)

def ensure_sheet(name,headers):
    sheet,_=connections()
    try: return worksheet(name)
    except gspread.WorksheetNotFound:
        ws=sheet.add_worksheet(title=name,rows=2000,cols=max(10,len(headers))); ws.append_row(headers,value_input_option='USER_ENTERED'); clear_cache(name); return ws

def ensure_headers(name, headers, *, return_columns=False):
    """Agrega columnas faltantes sin modificar registros existentes."""
    ws = ensure_sheet(name, headers)
    actuales = retry_google(lambda: ws.row_values(1))
    faltantes = [header for header in headers if header not in actuales]
    if not faltantes:
        return (ws,list(actuales)) if return_columns else ws
    retry_google(lambda: ws.add_cols(len(faltantes)))
    for posicion, header in enumerate(faltantes, start=len(actuales) + 1):
        retry_google(lambda: ws.update_cell(1, posicion, header))
    clear_cache(name)
    return (ws,list(actuales)+faltantes) if return_columns else ws

def append_dict(sheet_name,data):
    ws=worksheet(sheet_name); headers=retry_google(lambda: ws.row_values(1)); retry_google(lambda: ws.append_row([data.get(h,'') for h in headers],value_input_option='USER_ENTERED')); clear_cache(sheet_name)

def google_append_rows_raw(sheet_name, rows):
    if not rows:
        return
    ws = worksheet(sheet_name)
    headers = retry_google(lambda: ws.row_values(1))
    retry_google(lambda: ws.append_rows([[row.get(h, '') for h in headers] for row in rows], value_input_option='USER_ENTERED'))
    clear_cache(sheet_name)


def google_append_raw(sheet_name, data):
    ws = worksheet(sheet_name)
    headers = retry_google(lambda: ws.row_values(1))
    retry_google(lambda: ws.append_row([data.get(h, '') for h in headers], value_input_option='USER_ENTERED'))
    clear_cache(sheet_name)


def next_numeric_id(sheet_name,id_column,prefix):
    df=df_sheet(sheet_name); nums=[]
    if not df.empty and id_column in df.columns:
        for v in df[id_column].astype(str):
            try: nums.append(int(v.split('-')[-1]))
            except Exception: pass
    return f'{prefix}-{(max(nums)+1 if nums else 1):03d}'

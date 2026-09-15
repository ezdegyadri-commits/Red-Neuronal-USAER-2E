import json, random, time
import gspread
import streamlit as st
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from config.settings import URL_SPREADSHEET_MAESTRO

def _secret_dict(name):
    value = st.secrets[name]
    if isinstance(value, str):
        try: return json.loads(value)
        except json.JSONDecodeError: return json.loads(value.replace('\\"','"').strip())
    return dict(value)

@st.cache_resource(show_spinner=False)
def connections():
    gc = gspread.service_account_from_dict(_secret_dict('credenciales_json'))
    sheet = gc.open_by_url(URL_SPREADSHEET_MAESTRO)
    token = _secret_dict('token_json')
    creds = Credentials.from_authorized_user_info(token, ['https://www.googleapis.com/auth/drive'])
    if creds.expired and creds.refresh_token: creds.refresh(Request())
    return sheet, build('drive','v3',credentials=creds)

def retry_google(operation, attempts=6):
    """Reintenta solo límites transitorios de Google con espera progresiva."""
    last = None
    for attempt in range(attempts):
        try:
            return operation()
        except Exception as exc:
            last = exc
            message = str(exc).lower()
            is_quota = (
                "429" in message
                or "quota exceeded" in message
                or "resource_exhausted" in message
                or "read requests" in message
            )
            if not is_quota or attempt == attempts - 1:
                raise
            time.sleep(min(30, 2 ** attempt) + random.uniform(0, 0.75))
    raise last


@st.cache_data(ttl=120, show_spinner=False)
def read_sheet(name):
    """
    Lee una hoja de Google Sheets de forma tolerante.

    Evita get_all_records(), ya que falla cuando existen
    encabezados duplicados o vacíos.

    NO elimina información.
    NO modifica la hoja.
    """

    def operation():

        ws = sheet.worksheet(name)

        valores = ws.get_all_values()

        if not valores:
            return []

        encabezados_originales = valores[0]
        filas = valores[1:]

        encabezados = []
        usados = {}

        for i, encabezado in enumerate(encabezados_originales):

            encabezado = str(encabezado).strip()

            # Si una columna no tiene encabezado,
            # generar uno interno.
            if not encabezado:
                encabezado = f"Columna_{i + 1}"

            base = encabezado

            # Si el encabezado se repite,
            # conservar ambas columnas haciéndolas únicas.
            if base in usados:

                usados[base] += 1

                encabezado = (
                    f"{base}_{usados[base]}"
                )

            else:

                usados[base] = 1

            encabezados.append(encabezado)

        registros = []

        for fila in filas:

            # Completar filas cortas
            if len(fila) < len(encabezados):

                fila = fila + [""] * (
                    len(encabezados)
                    - len(fila)
                )

            # Ignorar valores que excedan
            # la cantidad de encabezados
            fila = fila[:len(encabezados)]

            # Ignorar solamente filas completamente vacías
            if not any(
                str(valor).strip()
                for valor in fila
            ):
                continue

            registros.append(
                dict(
                    zip(
                        encabezados,
                        fila
                    )
                )
            )

        return registros

    return retry_google(operation)

def df_sheet(name):
    return pd.DataFrame(
        read_sheet(name)
    )

def clear_sheet_cache():
    """
    Limpia el caché de lectura de Google Sheets.

    Debe llamarse después de modificar datos.
    """

    read_sheet.clear()

def worksheet(name): return retry_google(lambda: connections()[0].worksheet(name))

def ensure_sheet(name,headers):
    sheet,_=connections()
    try: return sheet.worksheet(name)
    except gspread.WorksheetNotFound:
        ws=sheet.add_worksheet(title=name,rows=2000,cols=max(10,len(headers))); ws.append_row(headers,value_input_option='USER_ENTERED'); clear_cache(name); return ws

def ensure_headers(name, headers):
    """Agrega columnas faltantes sin modificar registros existentes."""
    ws = ensure_sheet(name, headers)
    actuales = retry_google(lambda: ws.row_values(1))
    faltantes = [header for header in headers if header not in actuales]
    if not faltantes:
        return ws
    retry_google(lambda: ws.add_cols(len(faltantes)))
    for posicion, header in enumerate(faltantes, start=len(actuales) + 1):
        retry_google(lambda: ws.update_cell(1, posicion, header))
    clear_cache(name)
    return ws

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

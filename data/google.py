import json, time
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

@st.cache_data(ttl=120, show_spinner=False)
def read_sheet(name):
    sheet,_ = connections(); last=None
    for attempt in range(4):
        try: return sheet.worksheet(name).get_all_records()
        except Exception as exc:
            last=exc; msg=str(exc)
            if '429' not in msg and 'Quota exceeded' not in msg: raise
            if attempt < 3: time.sleep(1.5*(2**attempt))
    raise last

def df_sheet(name):
    import pandas as pd
    return pd.DataFrame(read_sheet(name))

def clear_cache(name=None):
    if name: read_sheet.clear(name)
    else: read_sheet.clear()

def worksheet(name): return connections()[0].worksheet(name)

def ensure_sheet(name,headers):
    sheet,_=connections()
    try: return sheet.worksheet(name)
    except gspread.WorksheetNotFound:
        ws=sheet.add_worksheet(title=name,rows=2000,cols=max(10,len(headers))); ws.append_row(headers,value_input_option='USER_ENTERED'); clear_cache(name); return ws

def ensure_headers(name, headers):
    """Agrega columnas faltantes sin modificar registros existentes."""
    ws = ensure_sheet(name, headers)
    actuales = ws.row_values(1)
    faltantes = [header for header in headers if header not in actuales]
    if not faltantes:
        return ws
    ws.add_cols(len(faltantes))
    for posicion, header in enumerate(faltantes, start=len(actuales) + 1):
        ws.update_cell(1, posicion, header)
    clear_cache(name)
    return ws

def append_dict(sheet_name,data):
    ws=worksheet(sheet_name); headers=ws.row_values(1); ws.append_row([data.get(h,'') for h in headers],value_input_option='USER_ENTERED'); clear_cache(sheet_name)

def google_append_rows_raw(sheet_name, rows):
    if not rows:
        return
    ws = worksheet(sheet_name)
    headers = ws.row_values(1)
    ws.append_rows([[row.get(h, '') for h in headers] for row in rows], value_input_option='USER_ENTERED')
    clear_cache(sheet_name)


def google_append_raw(sheet_name, data):
    ws = worksheet(sheet_name)
    headers = ws.row_values(1)
    ws.append_row([data.get(h, '') for h in headers], value_input_option='USER_ENTERED')
    clear_cache(sheet_name)


def next_numeric_id(sheet_name,id_column,prefix):
    df=df_sheet(sheet_name); nums=[]
    if not df.empty and id_column in df.columns:
        for v in df[id_column].astype(str):
            try: nums.append(int(v.split('-')[-1]))
            except Exception: pass
    return f'{prefix}-{(max(nums)+1 if nums else 1):03d}'

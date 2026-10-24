"""Índice privado de síntesis revisadas, ligado a la copia íntegra del expediente.

No modifica el esquema de archivos ni ejecuta OCR al navegar. Las revisiones
son append-only y se deduplican por documento, hash del original y contenido.
"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import streamlit as st
from data import repository as repo
from data.google import ensure_headers, retry_google, clear_cache
from services import archivo_expediente as archivo
from services.planeacion_estabilidad import candado

HOJA = 'Sintesis_Documentos'
HEADERS = ['ID_Documento', 'SHA256', 'Revision', 'Sintesis_JSON', 'Cuenta', 'Fecha']


def _rows():
    try: return repo.read(HOJA).fillna('').to_dict('records')
    except Exception as exc:
        if type(exc).__name__ == 'WorksheetNotFound': return []
        raise


def validar(value):
    if not isinstance(value, dict): raise ValueError('Síntesis no válida.')
    resumen = value.get('resumen', '')
    needs = value.get('necesidades', [])
    if not isinstance(resumen, str) or not resumen.strip() or len(resumen) > 1200:
        raise ValueError('Revisa la síntesis breve: entre 1 y 1200 caracteres.')
    if not isinstance(needs, list) or len(needs) > 20 or any(not isinstance(n, str) or not 4 <= len(n.split()) or len(n) > 600 for n in needs):
        raise ValueError('Revisa las necesidades seleccionadas, hasta 20 enunciados breves.')
    return {'resumen': resumen.strip(), 'necesidades': list(dict.fromkeys(n.strip() for n in needs)), 'revisada': True}


def guardar(did, value):
    # Revalida acceso actual; ni un ID ni un resumen recibido del navegador autorizan.
    row = next((r for r in archivo.listar() if r['ID_Documento'] == did), None)
    if not row: raise PermissionError('Documento fuera de tu asignación actual.')
    value = validar(value)
    ids = json.loads(row['ID_Alumnos_JSON'])
    if value['necesidades'] and (row['Tipo'] != 'EPP' or row['Ambito'] != 'individual' or len(ids) != 1):
        raise ValueError('Las NEE se vinculan solo a una EPP identificada de un único alumno.')
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True)
    with candado('sintesis:' + did):
        anteriores=[r for r in _rows() if r.get('ID_Documento')==did and r.get('SHA256')==row['SHA256']]
        ultima=anteriores[-1] if anteriores else {}
        if ultima.get('Sintesis_JSON')==payload:return ultima['Revision']
        # Incluye la revisión anterior: volver a una síntesis antigua también es
        # un cambio real. Un reintento tras acuse perdido sigue siendo no-op.
        rev = hashlib.sha256((did + row['SHA256'] + payload + ultima.get('Revision','')).encode()).hexdigest()
        ws, headers = ensure_headers(HOJA, HEADERS, return_columns=True)
        registro = {'ID_Documento': did, 'SHA256': row['SHA256'], 'Revision': rev,
                    'Sintesis_JSON': payload, 'Cuenta': st.session_state.get('usuario', ''),
                    'Fecha': datetime.now(timezone.utc).isoformat()}
        retry_google(lambda: ws.append_rows([[registro.get(h, '') for h in headers]], value_input_option='RAW'))
        clear_cache(HOJA)
        if not any(r.get('Revision') == rev for r in _rows()):
            raise RuntimeError('Falta confirmar la síntesis; el original permanece archivado. Reintenta sin volver a escanear.')
    return rev


def listar():
    registros = _rows()
    if not registros:return {}
    autorizados = {r['ID_Documento']: r for r in archivo.listar()}
    result = {}
    for r in registros:
        doc = autorizados.get(r.get('ID_Documento'))
        if not doc or r.get('SHA256') != doc['SHA256']: continue
        try:
            parsed=json.loads(r['Sintesis_JSON'])
            if not isinstance(parsed,dict):continue
            if parsed.get('revisada') is not True:continue
            value = validar(parsed)
        except (ValueError, TypeError, KeyError): continue
        result[r['ID_Documento']] = {**deepcopy(r), **value, 'documento': doc}
    return result


def fuentes_epp(ids, ciclo):
    fuentes = []
    for r in listar().values():
        d = r['documento']; destinatarios = json.loads(d['ID_Alumnos_JSON'])
        if d['Tipo'] != 'EPP' or d['Ambito'] != 'individual' or len(destinatarios) != 1 or destinatarios[0] not in ids or d['Ciclo'] > ciclo:
            continue
        if not r['necesidades']: continue
        fuentes.append({'tipo': 'EPP_ESCANEADA', 'alumno': destinatarios[0], 'registro': d['ID_Documento'],
                        'documento_origen': d['ID_Documento'], 'revision': r['Revision'], 'fecha': d['Fecha'][:10],
                        'texto': json.dumps({'NEE': [{'NEE': n} for n in r['necesidades']], 'Síntesis': r['resumen']}, ensure_ascii=False),
                        'alcance': 'NEE explícitas de EPP escaneada, seleccionadas y revisadas contra el original; fecha de archivo, no de evaluación; no diagnóstico automático'})
    return fuentes

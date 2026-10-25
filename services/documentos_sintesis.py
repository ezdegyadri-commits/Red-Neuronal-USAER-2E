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
    if not isinstance(needs, list) or len(needs) > (40 if 'nee_registros' in value else 20) or any(not isinstance(n, str) or not 4 <= len(n.split()) or len(n) > 600 for n in needs):
        raise ValueError('Revisa las necesidades seleccionadas, hasta 20 enunciados breves.')
    result={'resumen': resumen.strip(), 'necesidades': list(dict.fromkeys(n.strip() for n in needs)), 'revisada': True}
    if 'nee_registros' in value:
        from services.nee_documentales import validar_registros
        result['nee_registros']=validar_registros(value['nee_registros'])
        result['necesidades']=[r['texto'] for r in result['nee_registros'] if r['estado']=='Validada']
    return result


def guardar(did, value, revision_esperada=None):
    # Revalida acceso actual; ni un ID ni un resumen recibido del navegador autorizan.
    row = next((r for r in archivo.listar() if r['ID_Documento'] == did), None)
    if not row: raise PermissionError('Documento fuera de tu asignación actual.')
    value = validar(value)
    ids = json.loads(row['ID_Alumnos_JSON'])
    if (value['necesidades'] or value.get('nee_registros')) and (row['Tipo'] != 'EPP' or row['Ambito'] != 'individual' or len(ids) != 1):
        raise ValueError('Las NEE se vinculan solo a una EPP identificada de un único alumno.')
    with candado('sintesis:' + did):
        clear_cache(HOJA)
        anteriores=[r for r in _rows() if r.get('ID_Documento')==did and r.get('SHA256')==row['SHA256']]
        ultima=anteriores[-1] if anteriores else {}
        previo=json.loads(ultima.get('Sintesis_JSON','{}'))
        if 'nee_registros' in value:
            if revision_esperada is None:raise ValueError('Recupera la revisión del documento antes de validar las NEE.')
            from services.nee_documentales import preparar
            now=datetime.now(timezone.utc).isoformat()
            value['nee_registros']=preparar(value['nee_registros'],did,row['SHA256'],ids[0],
                previo.get('nee_registros',[]),st.session_state.get('usuario',''),now,revision_esperada)
            value['necesidades']=[r['texto'] for r in value['nee_registros'] if r['estado']=='Validada']
        elif previo.get('nee_registros'):
            raise RuntimeError('Esta EPP tiene un catálogo revisado. Recupera su síntesis para conservar y editar las NEE con sus fundamentos.')
        payload = json.dumps(value, ensure_ascii=False, sort_keys=True)
        if len(payload)>45000:raise ValueError('La revisión supera el tamaño seguro. Sintetiza los fundamentos sin eliminar las referencias al original.')
        if ultima.get('Sintesis_JSON')==payload:return ultima['Revision']
        if revision_esperada is not None and ultima.get('Revision','')!=revision_esperada:
            raise RuntimeError('Otra profesional guardó una revisión más reciente. Tu captura sigue en pantalla; respáldala y recupera la revisión actual antes de integrar los cambios.')
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


EDUCATIVOS = {'EPP', 'Competencia curricular', 'Estudio psicológico',
    'Evaluación de comunicación y lenguaje', 'Estudio social', 'Entrevista',
    'Estilo de aprendizaje y motivación', 'Informe pedagógico inicial',
    'Informe pedagógico final', 'Informe psicológico inicial', 'Informe psicológico final',
    'Informe de comunicación inicial', 'Informe de comunicación final', 'Derivación',
    'Sugerencias', 'Eventos significativos', 'Evaluación diagnóstica', 'BAP áulico',
    'BAP familiar', 'Agote de recursos', 'Otro documento educativo',
    'Informe médico', 'Reporte de atención médica', 'Canalización'}


def fuentes_documentales(ids, ciclo):
    """Solo síntesis revisadas, sin OCR ni documentos de identificación/contacto.

    Una fuente colectiva exige que todos sus destinatarios estén en la consulta.
    No se convierte un resultado externo en diagnóstico ni en EPP validada.
    """
    fuentes = []
    for r in listar().values():
        d = r['documento']; destinatarios = json.loads(d['ID_Alumnos_JSON'])
        if d['Tipo'] not in EDUCATIVOS or not destinatarios or not set(destinatarios).issubset(set(ids)) or d['Ciclo'] > ciclo:
            continue
        epp = d['Tipo'] == 'EPP' and d['Ambito'] == 'individual' and len(destinatarios) == 1
        fuentes.append({'tipo': 'EPP_ESCANEADA' if epp else 'DOCUMENTO_REVISADO',
                        'alumno': ','.join(sorted(destinatarios)), 'registro': d['ID_Documento'],
                        'documento_origen': d['ID_Documento'], 'revision': r['Revision'], 'fecha': d['Fecha'][:10],
                        'texto': json.dumps({'Documento': d['Tipo'], 'Síntesis': r['resumen'],
                            **({'NEE': ([{'NEE': n['texto'],'ID_NEE':n['id'],'Fundamento':n['fundamento'],
                                'Página':n['pagina'],'Área':n['area'],'Estado':n['estado'],
                                'Validada_En':n['validada_en'],'Validada_Por':n['validada_por']}
                                for n in r['nee_registros'] if n['estado']=='Validada'] if 'nee_registros' in r
                                else [{'NEE': n} for n in r['necesidades']])} if epp else {})}, ensure_ascii=False),
                        'alcance': 'Síntesis revisada contra el original; '+('individual' if len(destinatarios)==1 else 'colectiva, no atribuible a un solo alumno')+
                            '; fecha de archivo, no de evaluación; no diagnóstico automático'})
    return fuentes


def fuentes_epp(ids, ciclo):
    return [f for f in fuentes_documentales(ids, ciclo) if f['tipo']=='EPP_ESCANEADA']

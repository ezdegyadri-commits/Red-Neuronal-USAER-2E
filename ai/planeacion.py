"""IA bajo demanda: recibe únicamente el resumen revisado, nunca el padrón."""
import json
import logging
import os
import re
import streamlit as st
from ai.planeacion_prompt import solicitud, validar_respuesta

MODEL = os.environ.get('PLANEACION_GEMINI_MODEL', 'gemini-2.5-flash')
logger = logging.getLogger(__name__)


def _fallo(exc):
    codigo = getattr(exc, 'code', None)
    codigo = codigo if isinstance(codigo, int) else None
    # No registrar el resumen, la respuesta, credenciales ni el mensaje del proveedor.
    logger.warning('planeacion_ia_error codigo=%s tipo=%s', codigo, type(exc).__name__)
    st.session_state['planeacion_ia_diagnostico'] = {
        'codigo': codigo, 'tipo': type(exc).__name__, 'motor': MODEL}
    if codigo == 429:
        return 'Se alcanzó el límite de IA. Conservamos tu borrador; vuelve a intentar más tarde.'
    if codigo in (401, 403):
        return 'La conexión de IA requiere revisión de Dirección. Tu borrador se conserva.'
    if codigo == 404:
        return 'El motor de IA configurado no está disponible. Dirección debe revisar la configuración.'
    if codigo in (500, 502, 503):
        return 'El servicio de IA está ocupado. Tu borrador se conserva.'
    if codigo == 504 or isinstance(exc, TimeoutError) or 'Timeout' in type(exc).__name__:
        return 'La IA tardó demasiado en responder. Tu borrador se conserva.'
    return 'No se completó la propuesta. Dirección puede revisar el diagnóstico; tu borrador se conserva.'


def proponer(resumen, formato, area, revisar=False, curriculo=None):
    prompt = solicitud(resumen, formato, area, revisar, curriculo)
    try:
        key = st.secrets.get('GEMINI_API_KEY', '')
        if not key:
            raise RuntimeError('La IA no está configurada; puedes continuar editando.')
        from google import genai
        from google.genai import types
        cli = genai.Client(api_key=key, http_options=types.HttpOptions(
            timeout=45000, retry_options=types.HttpRetryOptions(attempts=1)))
        config = {'temperature': 0.2, 'response_mime_type': 'application/json',
                  'max_output_tokens': 4000}
        if MODEL.startswith('gemini-2.5-flash'):
            config['thinking_config'] = {'thinking_budget': 0}
        response = cli.models.generate_content(model=MODEL, contents=prompt, config=config)
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(_fallo(exc)) from None
    try:
        raw = re.sub(r'^```(?:json)?\s*|\s*```$', '', (response.text or '').strip())
        result = validar_respuesta(json.loads(raw), curriculo)
    except (ValueError, TypeError, AttributeError):
        raise RuntimeError('La propuesta llegó incompleta o sin un fundamento verificable. Tu borrador se conserva.') from None
    st.session_state.pop('planeacion_ia_diagnostico', None)
    return result


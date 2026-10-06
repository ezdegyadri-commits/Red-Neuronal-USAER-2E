"""IA bajo demanda: recibe únicamente el resumen revisado, nunca el padrón."""
import json
import logging
import os
import re
import time
import random
import streamlit as st
from ai.planeacion_prompt import solicitud, validar_respuesta

DEFAULT_MODEL = 'gemini-3.5-flash-lite'
MODEL = os.environ.get('PLANEACION_GEMINI_MODEL', DEFAULT_MODEL)
# Migración explícita de la configuración heredada: un único motor vigente,
# sin cadena de intentos ni cambio de proveedor o contratación de servicios.
MODELOS_HEREDADOS = {'gemini-2.5-flash','gemini-2.5-flash-preview-09-2025',
                    'gemini-3.1-flash-lite-preview'}
logger = logging.getLogger(__name__)


def configuracion_modelo():
    """La configuración del portal tiene prioridad; no cambia facturación ni claves."""
    try:
        pedido = str(st.secrets.get('PLANEACION_GEMINI_MODEL', MODEL)).strip() or DEFAULT_MODEL
    except FileNotFoundError:
        pedido = MODEL.strip() or DEFAULT_MODEL
    pedido = pedido.removeprefix('models/')
    elegido = DEFAULT_MODEL if pedido in MODELOS_HEREDADOS else pedido
    return {'solicitado':pedido,'efectivo':elegido,'migrado':pedido!=elegido}


def modelo_configurado():
    return configuracion_modelo()['efectivo']


def _fallo(exc, modelo=None):
    codigo = getattr(exc, 'code', None)
    codigo = codigo if isinstance(codigo, int) else None
    # No registrar el resumen, la respuesta, credenciales ni el mensaje del proveedor.
    logger.warning('planeacion_ia_error codigo=%s tipo=%s', codigo, type(exc).__name__)
    st.session_state['planeacion_ia_diagnostico'] = {
        'codigo': codigo, 'tipo': type(exc).__name__, 'motor': modelo or modelo_configurado()}
    if codigo in (408, 429, 500, 502, 503, 504):
        st.session_state['planeacion_ia_reintentar_desde'] = time.monotonic() + 30
    if codigo == 402:
        return 'La cuenta de IA no tiene saldo disponible. Dirección debe revisar la facturación; tu borrador se conserva.'
    if codigo == 429:
        return 'Se alcanzó el límite de IA. Conservamos tu borrador; vuelve a intentar más tarde.'
    if codigo in (401, 403):
        return 'La conexión de IA requiere revisión de Dirección. Tu borrador se conserva.'
    if codigo == 404:
        return 'Google no encontró el modelo '+str(modelo or modelo_configurado())+' para esta conexión. No es un error del borrador; Dirección debe comprobar el acceso al modelo con la clave del proyecto.'
    if codigo in (500, 502, 503):
        return 'El servicio de IA está ocupado. Tu borrador se conserva.'
    if codigo == 504 or isinstance(exc, TimeoutError) or 'Timeout' in type(exc).__name__:
        return 'La IA tardó demasiado en responder. Tu borrador se conserva.'
    return 'No se completó la propuesta. Dirección puede revisar el diagnóstico; tu borrador se conserva.'


def proponer(resumen, formato, area, revisar=False, curriculo=None, *, _prompt=None, _schema=None, _validador=None, _max_tokens=4000):
    prompt = _prompt or solicitud(resumen, formato, area, revisar, curriculo)
    modelo = modelo_configurado()
    if time.monotonic() < st.session_state.get('planeacion_ia_reintentar_desde', 0):
        raise RuntimeError('Espera unos 30 segundos antes de volver a solicitar IA. Puedes seguir editando tu borrador.')
    try:
        key = st.secrets.get('GEMINI_API_KEY', '')
        if not key:
            st.session_state['planeacion_ia_diagnostico'] = {
                'codigo': None, 'tipo': 'ClaveNoConfigurada', 'motor': modelo}
            raise RuntimeError('La IA no está configurada; puedes continuar editando.')
        from google import genai
        from google.genai import types
        cli = genai.Client(api_key=key, http_options=types.HttpOptions(
            timeout=45000, retry_options=types.HttpRetryOptions(attempts=1)))
        config = {'temperature': 0.2, 'response_mime_type': 'application/json',
                  'max_output_tokens': min(int(_max_tokens),6000)}
        textos = ('necesidad', 'objetivo', 'descriptor', 'actividad', 'contexto',
                  'temporalidad', 'recursos', 'evaluacion', 'fundamento')
        config['response_schema'] = {
            'type': 'object', 'required': ['observaciones', 'faltantes', 'propuestas'],
            'properties': {
                'observaciones': {'type': 'string'},
                'faltantes': {'type': 'array', 'items': {'type': 'string'}},
                'propuestas': {'type': 'array', 'items': {
                    'type': 'object', 'required': list(textos) + ['fuentes', 'referentes'],
                    'properties': {**{t: {'type': 'string'} for t in textos},
                        'fuentes': {'type': 'array', 'items': {'type': 'string'}},
                        'referentes': {'type': 'array', 'items': {'type': 'string'}}}}}}}
        if _schema is not None:config['response_schema']=_schema
        if modelo.startswith('gemini-2.5-flash'):
            config['thinking_config'] = {'thinking_budget': 0}
        # Un solo reintento breve. Nunca cambia de proveedor ni repite errores de
        # permisos, configuración o saldo. El SDK no añade reintentos ocultos.
        for intento in range(2):
            try:
                response = cli.models.generate_content(model=modelo, contents=prompt, config=config)
                break
            except Exception as exc:
                codigo = getattr(exc, 'code', None)
                temporal = codigo in (408, 429, 500, 502, 503, 504) or isinstance(exc, TimeoutError) or 'Timeout' in type(exc).__name__
                if intento or not temporal:
                    raise RuntimeError(_fallo(exc, modelo)) from None
                time.sleep(1 + random.random() * 0.5)
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(_fallo(exc, modelo)) from None
    try:
        raw = re.sub(r'^```(?:json)?\s*|\s*```$', '', (response.text or '').strip())
        result = _validador(json.loads(raw)) if _validador else validar_respuesta(json.loads(raw), curriculo)
    except (ValueError, TypeError, AttributeError):
        st.session_state['planeacion_ia_diagnostico'] = {
            'codigo': None, 'tipo': 'RespuestaNoVerificable', 'motor': modelo}
        logger.warning('planeacion_ia_error codigo=None tipo=RespuestaNoVerificable')
        raise RuntimeError('La propuesta llegó incompleta o sin un fundamento verificable. Tu borrador se conserva.') from None
    st.session_state.pop('planeacion_ia_diagnostico', None)
    st.session_state.pop('planeacion_ia_reintentar_desde', None)
    return result

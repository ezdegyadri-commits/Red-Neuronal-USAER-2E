"""IA bajo demanda: recibe únicamente el resumen revisado, nunca el padrón."""
import json
import logging
import os
import re
import time
import random
from contextvars import ContextVar
from contextlib import contextmanager
import streamlit as st
from ai.planeacion_prompt import solicitud, validar_respuesta, INSTRUCCIONES

DEFAULT_MODEL = 'gemini-3.5-flash-lite'
MODEL = os.environ.get('PLANEACION_GEMINI_MODEL', DEFAULT_MODEL)
# Migración explícita de la configuración heredada: un único motor vigente,
# sin cadena de intentos ni cambio de proveedor o contratación de servicios.
MODELOS_HEREDADOS = {'gemini-2.5-flash','gemini-2.5-flash-preview-09-2025',
                    'gemini-3.1-flash-lite-preview'}
logger = logging.getLogger(__name__)
_progreso = ContextVar('planeacion_ia_progreso', default=None)


@contextmanager
def progreso_generacion(callback):
    token=_progreso.set(callback)
    try:yield
    finally:_progreso.reset(token)


def notificar_progreso(etapa):
    callback=_progreso.get()
    if callback:callback(etapa)


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


def _proponer_openai(prompt, schema=None, max_tokens=4000):
    api_key = (
        st.session_state.get('relatoria_openai_key')
        or st.session_state.get('planeacion_openai_key')
        or st.session_state.get('OPENAI_API_KEY')
    )
    if not api_key:
        try:
            api_key = st.secrets.get('OPENAI_API_KEY', '')
        except Exception:
            api_key = ''
    if not api_key:
        return None
    from openai import OpenAI
    client = OpenAI(api_key=api_key, timeout=60.0, max_retries=2)
    base_system = INSTRUCCIONES.split('Devuelve solo JSON')[0].strip()
    instruccion_formato = (
        f"{base_system}\n\n"
        "INSTRUCCIÓN OBLIGATORIA DE FORMATO:\n"
        "Devuelve EXCLUSIVAMENTE un objeto JSON válido que cumpla estrictamente con la estructura solicitada, sin bloques markdown ni texto adicional fuera del JSON."
    )
    messages = [
        {"role": "system", "content": instruccion_formato},
        {"role": "user", "content": prompt},
    ]
    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        response_format={"type": "json_object"},
        temperature=0.2,
        max_tokens=min(int(max_tokens), 4000),
    )
    return (completion.choices[0].message.content or "").strip()


def proponer(resumen, formato, area, revisar=False, curriculo=None, *, _prompt=None, _schema=None, _validador=None, _max_tokens=4000):
    prompt = _prompt or solicitud(resumen, formato, area, revisar, curriculo)
    modelo_config = modelo_configurado()
    preferido = st.session_state.get('planeacion_modelo_preferido')
    modelo = preferido or modelo_config

    motor_solicitado = st.session_state.get('planeacion_motor') or st.session_state.get('epp_motor')
    if motor_solicitado == 'ChatGPT (OpenAI)':
        try:
            notificar_progreso('solicitando')
            raw_openai = _proponer_openai(prompt, _schema, _max_tokens)
            if raw_openai:
                notificar_progreso('validando')
                raw = re.sub(r'^```(?:json)?\s*|\s*```$', '', raw_openai.strip())
                return _validador(json.loads(raw)) if _validador else validar_respuesta(json.loads(raw), curriculo)
        except Exception as exc:
            logger.warning('openai_planeacion_error: %s', exc)

    if time.monotonic() < st.session_state.get('planeacion_ia_reintentar_desde', 0):
        raise RuntimeError('Espera unos 30 segundos antes de volver a solicitar IA. Puedes seguir editando tu borrador.')
    try:
        key = st.secrets.get('GEMINI_API_KEY', '')
        if not key:
            raw_openai = _proponer_openai(prompt, _schema, _max_tokens)
            if raw_openai:
                notificar_progreso('validando')
                raw = re.sub(r'^```(?:json)?\s*|\s*```$', '', raw_openai.strip())
                return _validador(json.loads(raw)) if _validador else validar_respuesta(json.loads(raw), curriculo)
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
        if str(modelo).startswith('gemini-2.5-flash'):
            config['thinking_config'] = {'thinking_budget': 0}

        candidatos = [modelo]
        for alt in ['gemini-2.5-pro', 'gemini-3.8-flash', 'gemini-3.5-flash-lite']:
            if alt not in candidatos:
                candidatos.append(alt)

        response = None
        ultimo_exc = None
        ultimo_mod = modelo

        for mod_actual in candidatos:
            for intento in range(2):
                try:
                    notificar_progreso('solicitando' if not intento else 'reintento')
                    response = cli.models.generate_content(model=mod_actual, contents=prompt, config=config)
                    ultimo_mod = mod_actual
                    break
                except Exception as exc:
                    ultimo_exc = exc
                    ultimo_mod = mod_actual
                    codigo = getattr(exc, 'code', None)
                    temporal = codigo in (408, 429, 500, 502, 503, 504) or isinstance(exc, TimeoutError) or 'Timeout' in type(exc).__name__
                    if not temporal:
                        break
                    if intento == 0:
                        time.sleep(1 + random.random() * 0.5)
            if response is not None:
                break
            codigo_err = getattr(ultimo_exc, 'code', None)
            if codigo_err in (400, 401, 402, 403, 404, 429):
                break

        if response is None:
            raw_openai = _proponer_openai(prompt, _schema, _max_tokens)
            if raw_openai:
                notificar_progreso('validando')
                raw = re.sub(r'^```(?:json)?\s*|\s*```$', '', raw_openai.strip())
                return _validador(json.loads(raw)) if _validador else validar_respuesta(json.loads(raw), curriculo)
            if ultimo_exc is not None:
                raise RuntimeError(_fallo(ultimo_exc, ultimo_mod)) from None
            raise RuntimeError('No fue posible completar la propuesta de IA.')
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(_fallo(exc, modelo)) from None
    try:
        notificar_progreso('validando')
        raw = re.sub(r'^```(?:json)?\s*|\s*```$', '', (response.text or '').strip())
        result = _validador(json.loads(raw)) if _validador else validar_respuesta(json.loads(raw), curriculo)
    except (ValueError, TypeError, AttributeError) as exc:
        motivos={
            'JSONInvalido':'la respuesta no llegó en el formato estructurado solicitado',
            'SalidaCortada':'la respuesta se cortó al alcanzar el límite de salida',
            'CamposIncompletos':'faltaron campos obligatorios en una actividad',
            'EstructuraInvalida':'la estructura de actividades no es válida',
            'ReferenciasInvalidas':'las referencias no llegaron en el formato requerido',
            'Vinculo_evidencias':'una actividad no citó evidencias válidas de las proporcionadas',
            'Vinculo_fuentes':'una actividad no citó las fuentes normativas proporcionadas',
            'Vinculo_referentes':'una actividad citó un PDA no seleccionado o no vinculó el elegido',
            'Vinculo_destinatarios':'una actividad no identificó correctamente a sus destinatarios',
            'Vinculo_competencias':'se incluyó una competencia no reconocida',
            'EvidenciaAjena':'una evidencia individual no correspondía a los alumnos destinatarios. No se integró ninguna propuesta. Revisa que cada alumno tenga evidencia propia; puedes proponer una actividad por alumno o continuar sin IA con «Preparar actividades con mis datos · sin IA» y después «Incorporar actividades locales a mi formato»',
            'ContextoInvalido':'una actividad usó un contexto distinto al admitido por el formato',
            'FuncionInvalida':'se mezclaron indicaciones de otra función profesional',
            'ActividadRepetida':'la propuesta repitió una actividad ya registrada; necesitamos una tarea diferente',
            'ContenidoNoVerificable':'la respuesta no superó la revisión de contenido y referencias'}
        motivo=getattr(exc,'motivo','JSONInvalido' if isinstance(exc,json.JSONDecodeError) else 'ContenidoNoVerificable')
        candidatos=getattr(response,'candidates',None) or []
        final=getattr(candidatos[0],'finish_reason',None) if candidatos else None
        final=str(getattr(final,'name',final) or '').split('.')[-1]
        if final=='MAX_TOKENS':motivo='SalidaCortada'
        if motivo not in motivos:motivo='ContenidoNoVerificable'
        st.session_state['planeacion_ia_diagnostico'] = {
            'codigo': None, 'tipo': 'RespuestaNoVerificable', 'motor': modelo,'motivo':motivo}
        logger.warning('planeacion_ia_error codigo=None tipo=RespuestaNoVerificable motivo=%s',motivo)
        raise RuntimeError('La IA no completó una propuesta válida: '+motivos[motivo]+'. Tu borrador se conserva.') from None
    st.session_state.pop('planeacion_ia_diagnostico', None)
    st.session_state.pop('planeacion_ia_reintentar_desde', None)
    return result


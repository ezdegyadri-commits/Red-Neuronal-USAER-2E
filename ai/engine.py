import json, re
import streamlit as st
from google import genai
from config.settings import GEMINI_MODEL

@st.cache_resource(show_spinner=False)
def client():
    key = st.secrets.get('GEMINI_API_KEY', '')
    return genai.Client(api_key=key) if key else None

def fallback():
    return {'area':'Aprendizaje','motivo':'Resultados del Anexo 3: barreras identificadas','sugerencias':'Revisar los resultados del Anexo 3 y establecer estrategias de acceso, participación y aprendizaje acordes con las barreras identificadas. Definir responsables, evidencias observables y un plazo de seguimiento.','seguimiento':'30 días'}

def generar_sugerencias(contexto):
    cli = client()
    if cli is None: return fallback()
    prompt = ('Actúa como especialista de educación especial de USAE. Analiza el contexto estructurado. '
              'No inventes diagnósticos ni información. Propón estrategias concretas, observables, viables y vinculadas a las barreras. '
              'Devuelve SOLO JSON válido con las claves area, motivo, sugerencias, seguimiento.\nCONTEXTO:\n' + json.dumps(contexto, ensure_ascii=False, indent=2))
    try:
        resp = cli.models.generate_content(model=GEMINI_MODEL, contents=prompt, config={'temperature':0.35})
        text = re.sub(r'^```(?:json)?\s*|\s*```$', '', (getattr(resp,'text','') or '').strip(), flags=re.I)
        data = json.loads(text)
        return {'area':str(data.get('area') or 'Aprendizaje'),'motivo':str(data.get('motivo') or fallback()['motivo']),'sugerencias':str(data.get('sugerencias') or fallback()['sugerencias']),'seguimiento':str(data.get('seguimiento') or '30 días')}
    except Exception as e:
        msg = str(e)
        if '429' in msg or 'quota' in msg.lower() or 'rate limit' in msg.lower():
            raise RuntimeError('Gemini alcanzó la cuota disponible. La evaluación ya quedó guardada; puedes volver a ejecutar la IA más tarde.') from e
        raise RuntimeError(f'No fue posible generar la propuesta de IA: {e}') from e

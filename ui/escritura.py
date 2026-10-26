"""Corrector privado: diccionario en navegador, sin enviar textos a APIs."""
from pathlib import Path
from weakref import WeakKeyDictionary
import threading
import streamlit as st
from streamlit.components.v2.get_bidi_component_manager import get_bidi_component_manager

_COMPONENTES=WeakKeyDictionary()
_LOCK=threading.RLock()
_KEY='corrector_global'


@st.cache_resource(show_spinner=False)
def _palabras():
    try:
        from spellchecker import SpellChecker
        dictionary = SpellChecker(language='es', distance=1).word_frequency.dictionary
        words = sorted(dictionary, key=lambda word: (-dictionary[word], word))
    except (ImportError, ModuleNotFoundError):
        words = []
    return ['usaer', 'segey', 'bap', 'cte', 'psicoeducativo', 'psicoeducativa', 'lectoescritura', *words]


def _componente():
    import streamlit.components.v2 as v2
    registro=get_bidi_component_manager()
    with _LOCK:
        if registro not in _COMPONENTES:
            js = Path(__file__).with_name('escritura.js').read_text(encoding='utf-8')
            _COMPONENTES[registro]=v2.component('revision_espanol', js=js)
        return _COMPONENTES[registro]


def _evento():
    event=st.session_state.get(_KEY,{}).get('evento') or {}
    if event.get('tipo') in ('diccionario_listo','pedir_diccionario'):
        st.session_state['_corrector_confirmado']=event['tipo']=='diccionario_listo'


def activar_revision():
    # El diccionario es público; se transmite una vez por navegador, no por clic.
    data={} if st.session_state.get('_corrector_confirmado') else {'words':_palabras()}
    _componente()(data=data,key=_KEY,default={'evento':None},on_evento_change=_evento)

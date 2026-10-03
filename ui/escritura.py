"""Corrector privado: diccionario en navegador, sin enviar textos a APIs."""
from pathlib import Path
import streamlit as st


@st.cache_resource(show_spinner=False)
def _palabras():
    from spellchecker import SpellChecker
    dictionary = SpellChecker(language='es', distance=1).word_frequency.dictionary
    words = sorted(dictionary, key=lambda word: (-dictionary[word], word))
    return ['usaer', 'segey', 'bap', 'cte', 'psicoeducativo', 'psicoeducativa', 'lectoescritura', *words]


def _componente():
    import streamlit.components.v2 as v2
    js = Path(__file__).with_name('escritura.js').read_text(encoding='utf-8')
    return v2.component('revision_espanol', js=js)


def activar_revision():
    _componente()(data={'words': _palabras()}, key='corrector_global')

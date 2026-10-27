"""Feedback inmediato local para los botones de todos los módulos."""
from pathlib import Path
from weakref import WeakKeyDictionary
import threading
import streamlit.components.v2 as components
from streamlit.components.v2.get_bidi_component_manager import get_bidi_component_manager

_componentes=WeakKeyDictionary()
_lock=threading.RLock()


def activar():
    registro=get_bidi_component_manager()
    with _lock:
        if registro not in _componentes:
            _componentes[registro]=components.component('usaer_interaccion_rapida_v1',
                js=Path(__file__).with_suffix('.js').read_text(encoding='utf-8'))
    _componentes[registro](key='usaer_interaccion_rapida',data={})

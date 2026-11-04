"""I/O acotado fuera del hilo de Streamlit; sin acceso al estado de la sesión."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
from pathlib import Path
from threading import BoundedSemaphore
import importlib
import logging
import sys
import time

_ROOT_DIR = str(Path(__file__).resolve().parents[1])
if _ROOT_DIR not in sys.path:
    sys.path.append(_ROOT_DIR)

_PAQUETES_RAIZ = ('config', 'data', 'services', 'ui', 'documents', 'ai', 'utils')


def _asegurar_paquetes():
    if _ROOT_DIR not in sys.path:
        sys.path.append(_ROOT_DIR)
    for nombre in _PAQUETES_RAIZ:
        if nombre not in sys.modules:
            importlib.import_module(nombre)
import logging
import time

_identidad = ContextVar('usaer_actor_trabajo', default=None)
_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix='usaer-documento')
_capacidad = BoundedSemaphore(12)


def contexto():
    return _identidad.get()


@contextmanager
def como(actor, escuelas):
    token = _identidad.set({'actor': deepcopy(actor), 'escuelas': str(escuelas)})
    try:
        yield
    finally:
        _identidad.reset(token)


def enviar(actor, escuelas, operacion, *args):
    # No cola ilimitada ni espera de admisión en el evento del navegador.
    if not _capacidad.acquire(blocking=False):
        from services.planeacion_estabilidad import GuardadoPendiente
        raise GuardadoPendiente(5)
    try:
        copia = deepcopy(args)
        identidad = deepcopy(actor)
    except BaseException:
        _capacidad.release()
        raise
    encolado=time.monotonic()
    def ejecutar():
        inicio = time.monotonic()
        resultado='error'
        try:
            _asegurar_paquetes()
            with como(identidad, escuelas):
                valor=operacion(*copia)
                resultado='ok'
                return valor
        finally:
            # Sin argumentos, identificadores, nombres ni mensajes del proveedor.
            logging.getLogger(__name__).info('documento_io cola_ms=%.0f duracion_ms=%.0f resultado=%s',
                (inicio-encolado)*1000,(time.monotonic()-inicio)*1000,resultado)
    try:
        future = _pool.submit(ejecutar)
    except BaseException:
        _capacidad.release()
        raise
    future.add_done_callback(lambda _: _capacidad.release())
    return future

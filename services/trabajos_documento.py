"""I/O acotado fuera del hilo de Streamlit; sin acceso al estado de la sesión."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
from threading import BoundedSemaphore
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
    def ejecutar():
        inicio = time.monotonic()
        try:
            with como(identidad, escuelas):
                return operacion(*copia)
        finally:
            logging.getLogger(__name__).info('documento_io duracion_ms=%.0f', (time.monotonic()-inicio)*1000)
    try:
        future = _pool.submit(ejecutar)
    except BaseException:
        _capacidad.release()
        raise
    future.add_done_callback(lambda _: _capacidad.release())
    return future

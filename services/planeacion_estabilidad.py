"""Coordinación acotada por proceso, sin otra base ni cambios de formato.

El límite reserva margen para otros módulos. No es un bloqueo distribuido:
la operación de producción sigue requiriendo una única instancia escritora.
"""
from collections import deque
import threading
import time
import streamlit as st


class GuardadoPendiente(RuntimeError):
    def __init__(self, espera=15):
        self.espera = max(1, int(espera) + 1)
        super().__init__('El guardado está pendiente para cuidar la conexión. Tu edición se conserva; se reintentará automáticamente.')


class Presupuesto:
    def __init__(self, limite=45, ventana=60, reloj=time.monotonic):
        self.limite, self.ventana, self.reloj = limite, ventana, reloj
        self.lock = threading.RLock()
        self.eventos = deque()

    def reservar(self):
        with self.lock:
            ahora = self.reloj()
            while self.eventos and ahora - self.eventos[0] >= self.ventana:
                self.eventos.popleft()
            if len(self.eventos) >= self.limite:
                raise GuardadoPendiente(self.ventana - (ahora - self.eventos[0]))
            self.eventos.append(ahora)


@st.cache_resource(show_spinner=False)
def presupuesto():
    return Presupuesto()


@st.cache_resource(show_spinner=False)
def coordinacion():
    return threading.RLock(), {}, {}


def candado(documento):
    lock, locks, _ = coordinacion()
    with lock:
        return locks.setdefault(documento, threading.RLock())


def intentos():
    return coordinacion()[2]


def reservar_escritura():
    presupuesto().reservar()


@st.cache_resource(show_spinner=False)
def lecturas_materiales():
    """Dos lecturas pesadas por proceso; no bloquea el editor esperando OCR."""
    return threading.BoundedSemaphore(2)

"""Paquete de servicios y lógica de negocio de USAER 2E."""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.append(_ROOT)


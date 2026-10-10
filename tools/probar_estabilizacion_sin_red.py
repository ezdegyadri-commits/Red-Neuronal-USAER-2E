"""Regresión offline: corta sockets antes de importar pruebas, sin credenciales."""
import os
import socket
import ipaddress
import sys
import unittest
import logging
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
def prohibido(*args,**kwargs):
    raise AssertionError('Las pruebas de estabilización no permiten conexiones de red')
original_connect=socket.socket.connect
original_connect_ex=socket.socket.connect_ex
def solo_loopback(original):
    def conectar(sock,address):
        if isinstance(address,tuple) and ipaddress.ip_address(address[0]).is_loopback:
            return original(sock,address)
        return prohibido()
    return conectar
# Windows necesita loopback para el socketpair interno de asyncio/AppTest.
# Todas las conexiones externas y todos los clientes HTTP permanecen bloqueados.
socket.socket.connect=solo_loopback(original_connect)
socket.socket.connect_ex=solo_loopback(original_connect_ex)
socket.create_connection=prohibido
import requests
requests.sessions.Session.request=prohibido
os.environ['STREAMLIT_BROWSER_GATHER_USAGE_STATS']='false'
os.environ['GEMINI_API_KEY']=''
logging.disable(logging.WARNING)

modulos=[
 'tests.test_planeacion_estabilidad','tests.test_planeacion_panel',
 'tests.test_planeacion_simple',
 'tests.test_planeacion_modelo','tests.test_planeacion_contexto',
 'tests.test_planeacion_continuidad','tests.test_planeacion_equipo',
 'tests.test_planeacion_completa','tests.test_planeacion_formato',
 'tests.test_planeacion_motor','tests.test_planeacion_propuestas',
 'tests.test_planeacion_ui','tests.test_planeacion_equipo_ui',
 'tests.test_planeacion_completa_ui','tests.test_curriculo_planeacion',
 'tests.test_materiales_planeacion','tests.test_google_retry',
 'tests.test_epp','tests.test_epp_entrada','tests.test_epp_ui',
 'tests.test_shared_support_scope',
 'tests.test_passkey_session',
 'tests.test_horarios_apoyo','tests.test_horarios_edicion',
 'tests.test_horarios_cruces_breves','tests.test_cronogramas',
 'tests.test_cronograma_respaldo','tests.test_diego_cronograma',
 'tests.test_calendario_eventos','tests.test_tramites',
 'tests.test_specialist_views','tests.test_alta_permissions',
 'tests.test_sugerencias_access','tests.test_visitas_historial',
 'tests.test_novedades_supervision',
]
suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(m) for m in modulos)
result=unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(0 if result.wasSuccessful() else 1)

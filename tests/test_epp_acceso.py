from types import SimpleNamespace
import unittest
from unittest.mock import patch,Mock
from ui import epp_acceso as acceso

class AccesoTests(unittest.TestCase):
    def test_arranque_actual_no_recarga_ni_reinicia_nada(self):
        pagina=Mock(return_value='informe');module=SimpleNamespace(VERSION_INTERFAZ_EPP=acceso.VERSION,epp_page=pagina)
        with patch.object(acceso.importlib,'import_module',return_value=module),patch.object(acceso.importlib,'reload') as reload:
            self.assertEqual(acceso.epp_page(),'informe');reload.assert_not_called()

    def test_version_antigua_recarga_dependencias_una_sola_vez(self):
        state={'texto_pendiente':'Captura ficticia','autenticado':True}
        modules={n:SimpleNamespace(nombre=n) for n in acceso._MODULOS}
        modules['ui.epp'].epp_page=lambda:state
        def reload(module):
            if module.nombre=='ui.epp':module.VERSION_INTERFAZ_EPP=acceso.VERSION
            return module
        with patch.object(acceso.importlib,'import_module',side_effect=modules.get),patch.object(acceso.importlib,'reload',side_effect=reload) as r:
            self.assertIs(acceso.epp_page(),state);self.assertIs(acceso.epp_page(),state)
            self.assertEqual([c.args[0].nombre for c in r.call_args_list],list(acceso._MODULOS))
            self.assertEqual(state,{'texto_pendiente':'Captura ficticia','autenticado':True})

    def test_version_no_disponible_informa_y_no_ejecuta_interfaz_antigua(self):
        page=Mock();module=SimpleNamespace(epp_page=page)
        with patch.object(acceso.importlib,'import_module',return_value=module),patch.object(acceso.importlib,'reload',return_value=module):
            with self.assertRaises(RuntimeError):acceso.epp_page()
            page.assert_not_called()

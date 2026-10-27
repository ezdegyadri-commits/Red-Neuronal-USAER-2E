from types import SimpleNamespace
import unittest
from unittest.mock import patch
from ui import epp_actualizacion as arranque


class ActualizacionTests(unittest.TestCase):
    def test_entrada_vigente_no_recarga(self):
        module = SimpleNamespace(VERSION='vigente')
        with patch.object(arranque.importlib,'import_module',return_value=module), patch.object(arranque.importlib,'reload') as reload:
            self.assertIs(arranque.preparar_entrada('vigente'),module)
            reload.assert_not_called()

    def test_entrada_antigua_actualiza_una_vez_sin_tocar_estado(self):
        state={'texto_pendiente':'Captura ficticia','autenticado':True}
        module=SimpleNamespace(VERSION='anterior',estado=state)
        def actualizar(value):
            value.VERSION='vigente'
            return value
        with patch.object(arranque.importlib,'import_module',return_value=module), patch.object(arranque.importlib,'reload',side_effect=actualizar) as reload:
            self.assertIs(arranque.preparar_entrada('vigente').estado,state)
            self.assertIs(arranque.preparar_entrada('vigente').estado,state)
            reload.assert_called_once_with(module)
            self.assertEqual(state,{'texto_pendiente':'Captura ficticia','autenticado':True})

    def test_fuentes_incompletas_no_aceptan_version_antigua(self):
        module=SimpleNamespace(VERSION='anterior')
        with patch.object(arranque.importlib,'import_module',return_value=module), patch.object(arranque.importlib,'reload',return_value=module):
            with self.assertRaises(RuntimeError):arranque.preparar_entrada('vigente')


if __name__=='__main__':unittest.main()

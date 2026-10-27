"""Pruebas de durabilidad y resiliencia del modelo de IA para Relatorías del Director."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from ui import relatorias


class RelatoriasModeloTests(unittest.TestCase):
    def test_modelo_obsoleto_migra_automaticamente_a_gemini_3_8_flash(self):
        with patch.object(relatorias.st, "secrets", {"GEMINI_MODEL": "gemini-2.5-flash"}):
            modelo = relatorias._resolver_modelo_gemini_relatoria()
            self.assertEqual(modelo, "gemini-3.8-flash")

    def test_modelo_con_prefijo_models_se_limpia(self):
        with patch.object(relatorias.st, "secrets", {"RELATORIAS_GEMINI_MODEL": "models/gemini-3.8-flash"}):
            modelo = relatorias._resolver_modelo_gemini_relatoria()
            self.assertEqual(modelo, "gemini-3.8-flash")

    def test_modelo_vacio_usa_default_durable(self):
        with patch.object(relatorias.st, "secrets", {}):
            modelo = relatorias._resolver_modelo_gemini_relatoria()
            self.assertEqual(modelo, "gemini-3.8-flash")

    def test_procesar_gemini_reintenta_ante_404_not_found(self):
        cliente = Mock()
        archivo_mock = SimpleNamespace(name="files/test_audio")
        cliente.files.upload.return_value = archivo_mock

        # Primer intento lanza 404 NOT_FOUND (modelo descontinuado)
        # Segundo intento con modelo durable responde con texto
        class Error404(Exception):
            pass

        def side_effect(model, contents):
            if model == "modelo-antiguo":
                raise Error404("404 NOT_FOUND: model not available")
            return SimpleNamespace(text="Relatoría generada exitosamente")

        cliente.models.generate_content.side_effect = side_effect

        with patch.object(relatorias, "gemini_client", return_value=cliente), \
             patch.object(relatorias, "_resolver_modelo_gemini_relatoria", return_value="modelo-antiguo"):
            texto = relatorias._procesar_gemini("ruta/falsa/audio.mp3", "prompt de prueba")
            self.assertEqual(texto, "Relatoría generada exitosamente")
            # Verifica que se llamó a upload y delete del archivo temporal
            cliente.files.upload.assert_called_once()
            cliente.files.delete.assert_called_once_with(name="files/test_audio")


if __name__ == "__main__":
    unittest.main()

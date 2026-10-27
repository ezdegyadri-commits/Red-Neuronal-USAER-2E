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


    def test_procesar_gemini_reintenta_ante_503_unavailable_alta_demanda(self):
        cliente = Mock()
        archivo_mock = SimpleNamespace(name="files/test_audio")
        cliente.files.upload.return_value = archivo_mock

        llamadas = []

        def side_effect(model, contents):
            llamadas.append(model)
            if model == "gemini-3.8-flash":
                raise RuntimeError("503 UNAVAILABLE. This model is currently experiencing high demand. Spikes in demand are usually temporary.")
            return SimpleNamespace(text="Relatoría generada tras conmutar por 503")

        cliente.models.generate_content.side_effect = side_effect

        with patch.object(relatorias, "gemini_client", return_value=cliente), \
             patch.object(relatorias, "_resolver_modelo_gemini_relatoria", return_value="gemini-3.8-flash"), \
             patch("time.sleep", return_value=None):
            texto = relatorias._procesar_gemini("ruta/falsa/audio.mp3", "prompt")
            self.assertEqual(texto, "Relatoría generada tras conmutar por 503")
            self.assertIn("gemini-3.8-flash", llamadas)
            self.assertIn("gemini-2.5-pro", llamadas)

    def test_procesar_gemini_con_modelo_preferido_pro(self):
        cliente = Mock()
        archivo_mock = SimpleNamespace(name="files/test_audio")
        cliente.files.upload.return_value = archivo_mock

        modelos_invocados = []

        def side_effect(model, contents):
            modelos_invocados.append(model)
            return SimpleNamespace(text="Relatoría con Pro")

        cliente.models.generate_content.side_effect = side_effect

        with patch.object(relatorias, "gemini_client", return_value=cliente):
            texto = relatorias._procesar_gemini(
                "ruta/falsa/audio.mp3", "prompt", modelo_preferido="gemini-2.5-pro"
            )
            self.assertEqual(texto, "Relatoría con Pro")
            self.assertEqual(modelos_invocados[0], "gemini-2.5-pro")


if __name__ == "__main__":
    unittest.main()


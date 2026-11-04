import secrets
import unittest
from unittest.mock import Mock, patch

from pydantic import ValidationError

from ai.actividades_curriculares import sugerir_actividad_publica, sugerir_con_gemini


class AdaptadorCurricularTest(unittest.TestCase):
    @patch("ai.documento_json.generar")
    @patch("ai.actividades_curriculares.catalogo")
    def test_gemini_exige_doble_activacion_y_solo_envia_curriculo(self, catalogo, generar):
        catalogo.return_value = {"registros": [{
            "id": "sep-1", "grado": 3, "campo": "Lenguajes", "contenido": "Lectura",
            "pda": "Reconoce personajes", "alumno": "DATO QUE NO DEBE SALIR",
        }]}
        generar.return_value = dict(actividad="Leer", apoyos="Imágenes", recursos="Relato", evaluacion="Registro")
        with patch.dict("os.environ", {"USAER_IA_CURRICULAR_HABILITADA": "0"}):
            with self.assertRaises(PermissionError):
                sugerir_con_gemini("sep-1", autorizado=True)
        with patch.dict("os.environ", {"USAER_IA_CURRICULAR_HABILITADA": "1",
                                       "USAER_IA_GEMINI_MODELO": "gemini-fixture",
                                       "USAER_IA_GEMINI_API_KEY": secrets.token_urlsafe(24)}):
            with self.assertRaises(PermissionError):
                sugerir_con_gemini("sep-1")
            generar.assert_not_called()
            self.assertEqual(sugerir_con_gemini("sep-1", autorizado=True).actividad, "Leer")
            self.assertIn("Reconoce personajes", generar.call_args.args[0])
            self.assertNotIn("DATO QUE NO DEBE SALIR", generar.call_args.args[0])

    @patch("ai.actividades_curriculares.catalogo")
    def test_permiso_catalogo_y_contrato_de_respuesta(self, catalogo):
        catalogo.return_value = {"registros": [{
            "id": "pda-publico", "grado": 2, "campo": "Lenguajes",
            "contenido": "Lectura", "pda": "Identifica personajes", "fuente": "SEP",
        }]}
        proveedor = Mock(return_value={"actividad": "Leer un relato", "apoyos": "Imágenes",
                                       "recursos": "Relato breve", "evaluacion": "Registro de respuestas"})
        with self.assertRaises(PermissionError):
            sugerir_actividad_publica("pda-publico", proveedor)
        with self.assertRaises(ValueError):
            sugerir_actividad_publica("id-inventado", proveedor, autorizado=True)
        proveedor.assert_not_called()
        actividad = sugerir_actividad_publica("pda-publico", proveedor, autorizado=True)
        proveedor.assert_called_once_with({"grado": 2, "campo": "Lenguajes",
                                          "contenido": "Lectura", "pda": "Identifica personajes"})
        self.assertEqual(actividad.apoyos, "Imágenes")
        proveedor.return_value = {"actividad": ""}
        with self.assertRaises(ValidationError):
            sugerir_actividad_publica("pda-publico", proveedor, autorizado=True)

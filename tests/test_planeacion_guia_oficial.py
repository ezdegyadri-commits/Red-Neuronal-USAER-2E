"""Pruebas de alineación con la Guía de Educación Especial y Rúbrica Zona 001."""
from unittest import TestCase
from unittest.mock import patch, MagicMock
from copy import deepcopy
from services.planeacion_modelo import crear_plantilla, FORMATOS
from services import planeacion_calidad as calidad
from services import planeacion_rapida as rapido
from ai.planeacion_prompt import INSTRUCCIONES
from ai.planeacion_completa import solicitud_completa


from tests.test_planeacion_cero_friccion import individual


class GuiaOficialZona001Tests(TestCase):
    def setUp(self):
        self.doc = individual('Aprendizaje')

    def test_descriptor_sigue_formula_canonica_sujeto_verbo_complemento(self):
        """Indicador 4 de Zona 001: Sujeto + verbo en presente + complemento observable."""
        desc = calidad.descriptor('Dianely', 'identifica', 'cantidades del 1 al 10 con fichas de colores')
        self.assertEqual(desc, 'Dianely identifica cantidades del 1 al 10 con fichas de colores.')

        # Rechazo de verbos no observables o abstractos
        with self.assertRaises(ValueError):
            calidad.descriptor('Dianely', 'comprende', 'los números del 1 al 10')
        with self.assertRaises(ValueError):
            calidad.descriptor('Dianely', 'concientiza', 'sobre la lectura')

    def test_contextos_oficiales_por_defecto_cubren_los_4_contextos_usaer(self):
        """Indicadores 6, 12 y 13: Aula de apoyo, Aula regular, Escuela y Familia."""
        from services import planeacion as s
        with patch.object(s, 'autorizar', return_value={'cuenta': 'docente@usaer.edu', 'area': 'Aprendizaje', 'rol': 'Especialista'}):
            estado = rapido.estado(self.doc)
            contextos = estado['defaults']['contextos']
            self.assertIn('Aula de apoyo', contextos)
            self.assertIn('Aula regular', contextos)
            self.assertIn('Escuela', contextos)
            self.assertIn('Familia', contextos)
            self.assertEqual(len(contextos), 4)

    def test_resumen_zona_001_evalua_14_indicadores_y_coherencia(self):
        """Comprueba el reporte sintético de los 14 indicadores y nivel de desempeño."""
        resumen = calidad.resumen_zona_001(self.doc)
        self.assertEqual(resumen['total'], 14)
        self.assertIn('cumplidos', resumen)
        self.assertIn('contextos', resumen)
        self.assertIn('nivel_sugerido', resumen)
        self.assertIn('etiqueta_nivel', resumen)

    def test_prompt_maestro_incluye_blindaje_zona_001_y_marco_dua(self):
        """Verifica que el System Prompt instruya expresamente la fórmula canónica y los 4 contextos."""
        self.assertIn('Zona 001', INSTRUCCIONES)
        self.assertIn('Nivel 3 (Satisfactorio)', INSTRUCCIONES)
        self.assertIn('Sujeto + verbo en presente (acción observable) + complemento', INSTRUCCIONES)
        self.assertIn('AULA DE APOYO', INSTRUCCIONES)
        self.assertIn('AULA REGULAR', INSTRUCCIONES)
        self.assertIn('ESCUELA', INSTRUCCIONES)
        self.assertIn('FAMILIA', INSTRUCCIONES)
        self.assertIn('DUA', INSTRUCCIONES)

    def test_ui_asistente_expone_boton_1_clic_y_ajustes_conduccion(self):
        """Metáfora del Automóvil: El maestro conduce en 1 clic con ajustes opcionales."""
        from streamlit.testing.v1 import AppTest
        from tests.test_planeacion_documento_directo import HELP_APP
        app = AppTest.from_string(HELP_APP, default_timeout=30).run()
        self.assertFalse(app.exception)
        
        # Verificar botón principal de 1 clic
        btn_1clic = next((b for b in app.button if '1 clic' in b.label), None)
        self.assertIsNotNone(btn_1clic)
        self.assertEqual(btn_1clic.label, '⚡ Generar planeación inteligente (1 clic)')
        
        # Verificar expander de ajustes opcionales de conducción
        exp_conduccion = next((e for e in app.expander if 'conducción' in e.label.lower()), None)
        self.assertIsNotNone(exp_conduccion)

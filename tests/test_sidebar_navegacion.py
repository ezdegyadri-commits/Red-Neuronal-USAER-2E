import unittest
from unittest.mock import patch
import streamlit as st

class TestSidebarNavegacion(unittest.TestCase):
    def setUp(self):
        # Limpiar session_state para cada prueba
        for key in list(st.session_state.keys()):
            del st.session_state[key]

    def test_sidebar_titles_and_icons(self):
        """Verifica que los títulos simplificados y los iconos estén definidos correctamente."""
        from ui.sidebar import TITULOS_SIMPLIFICADOS, ICONOS_MENU, obtener_bloques_menu
        self.assertEqual(TITULOS_SIMPLIFICADOS["Anexo III BAP"], "Anexo III (BAP)")
        self.assertEqual(TITULOS_SIMPLIFICADOS["Anexo IV Hoja de sugerencias"], "Anexo IV (Sugerencias)")
        self.assertEqual(TITULOS_SIMPLIFICADOS["Anexo V Eventos significativos"], "Anexo V (Eventos)")
        self.assertEqual(TITULOS_SIMPLIFICADOS["Estadística"], "Estadística")
        self.assertEqual(TITULOS_SIMPLIFICADOS["Calendario de actividades"], "Calendario")
        self.assertEqual(TITULOS_SIMPLIFICADOS["Trámites"], "Trámites")
        
        self.assertIn("Inicio", ICONOS_MENU)
        self.assertIn("Expedientes", ICONOS_MENU)
        self.assertIn("Anexo III BAP", ICONOS_MENU)
        self.assertIn("Estadística", ICONOS_MENU)

        bloques = obtener_bloques_menu(["Inicio", "Expedientes", "Anexo III BAP", "Estadística"])
        bloques_dict = dict(bloques)
        self.assertEqual(bloques_dict["GENERAL"], ["Inicio", "Expedientes"])
        self.assertEqual(bloques_dict["ANEXOS"], ["Anexo III BAP"])
        self.assertEqual(bloques_dict["ADMINISTRACIÓN"], ["Estadística"])

    def test_theme_css_contains_mobile_touch_rules(self):
        """Verifica que el CSS de ui/theme.py incluya las reglas móviles, áreas táctiles y estilos del sidebar."""
        from ui.theme import CSS
        self.assertIn("-webkit-tap-highlight-color: transparent", CSS)
        self.assertIn("touch-action: manipulation", CSS)
        self.assertIn("transform: scale(0.96)", CSS)
        self.assertIn(".nav-category-header", CSS)
        self.assertIn("border-left: 4px solid #F59E0B", CSS)
        self.assertIn(".hub-hero", CSS)
        self.assertIn(".hub-tile", CSS)
        self.assertIn(".module-breadcrumb", CSS)

    def test_central_hub_modules(self):
        """Verifica que el Hub Central defina correctamente los módulos de las 3 categorías."""
        from ui.hub import MODULOS_INFO
        self.assertIn("Expedientes", MODULOS_INFO)
        self.assertEqual(MODULOS_INFO["Expedientes"]["categoria"], "GENERAL")

        self.assertIn("Anexo III BAP", MODULOS_INFO)
        self.assertEqual(MODULOS_INFO["Anexo III BAP"]["categoria"], "ANEXOS")
        self.assertIn("Anexo IV Hoja de sugerencias", MODULOS_INFO)
        self.assertIn("Anexo V Eventos significativos", MODULOS_INFO)

        self.assertIn("Estadística", MODULOS_INFO)
        self.assertEqual(MODULOS_INFO["Estadística"]["categoria"], "ADMINISTRACIÓN")
        self.assertIn("Documentos", MODULOS_INFO)
        self.assertIn("Calendario de actividades", MODULOS_INFO)
        self.assertIn("Planeación e intervención", MODULOS_INFO)

if __name__ == '__main__':
    unittest.main()

from pathlib import Path
import unittest
from streamlit.testing.v1 import AppTest
class NovedadesUITests(unittest.TestCase):
    def test_consulta_filtro_y_revision(self):
        app=AppTest.from_file(str(Path(__file__).with_name('fixture_novedades_supervision.py'))).run(timeout=30)
        self.assertFalse(app.exception)
        next(b for b in app.button if b.label=='Marcar esta versión como revisada').click().run()
        self.assertFalse(app.exception)
        next(c for c in app.checkbox if c.label=='Mostrar solo lo que falta revisar').check().run()
        self.assertTrue(any('No hay documentos' in m.value for m in app.info))
    def test_apoyo_no_ve_novedades(self):
        app=AppTest.from_file(str(Path(__file__).with_name('fixture_novedades_supervision.py'))).run(timeout=30)
        app.radio[0].set_value('Apoyo').run()
        self.assertTrue(app.warning);self.assertFalse(app.subheader);self.assertFalse(app.text_input)

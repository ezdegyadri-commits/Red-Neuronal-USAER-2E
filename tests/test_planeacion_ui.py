import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest


class PlaneacionUITests(unittest.TestCase):
    def test_creacion_guardado_pdf_y_revision(self):
        at=AppTest.from_file(str(Path(__file__).with_name('fixture_planeacion_panel.py'))).run(timeout=30)
        self.assertFalse(at.exception)
        next(s for s in at.selectbox if s.label=='Alumno en atención individual').set_value('A1').run()
        next(b for b in at.button if b.label=='Crear y guardar borrador').click().run()
        next(r for r in at.radio if r.label=='Cómo quieres trabajar').set_value('Edición guiada').run()
        self.assertFalse(at.exception)
        self.assertTrue({'1. Conocer y elegir','2. Preparar actividades','3. Revisar y compartir'}.issubset({t.label for t in at.tabs}))
        next(t for t in at.text_area if t.label=='Necesidades y apoyos documentados (incluye la referencia de origen)').set_value('Necesidad educativa documentada').run()
        next(b for b in at.button if b.label=='Guardar borrador').click().run()
        self.assertEqual(at.session_state.fixture_versions[-1]['metadatos']['necesidades_confirmadas'],'Necesidad educativa documentada')
        next(b for b in at.button if b.label=='Preparar PDF').click().run()
        self.assertFalse(at.exception)
        at.selectbox[0].set_value('Dirección').run()
        self.assertFalse(at.exception)
        self.assertTrue(any(b.label=='Devolver con observaciones' for b in at.button))
    def test_social_tiene_anexo_xxv(self):
        at=AppTest.from_file(str(Path(__file__).with_name('fixture_planeacion_panel.py'))).run(timeout=30)
        at.selectbox[0].set_value('Trabajo Social').run()
        next(s for s in at.selectbox if s.label=='Alumno en atención individual').set_value('A1').run()
        next(b for b in at.button if b.label=='Crear y guardar borrador').click().run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state.fixture_versions[-1]['formato'],'XXV')

if __name__=='__main__':unittest.main()

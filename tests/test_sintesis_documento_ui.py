from pathlib import Path
from unittest import TestCase
from streamlit.testing.v1 import AppTest


class SintesisUITests(TestCase):
    def test_preview_breve_requiere_revision_y_nee_seleccionada(self):
        app=AppTest.from_file(str(Path(__file__).parent/'fixtures/sintesis_documento_app.py'),default_timeout=30).run()
        self.assertFalse(app.exception)
        next(b for b in app.button if b.label=='Preparar vista previa sintetizada').click().run()
        self.assertFalse(app.exception)
        resumen=next(t for t in app.text_area if t.label.startswith('Síntesis del documento'))
        self.assertLessEqual(len(resumen.value),800)
        self.assertFalse(any('transcri' in t.label.lower() for t in app.text_area))
        self.assertEqual(app.multiselect[0].value,[])
        guardar=next(b for b in app.button if b.label.startswith('Guardar síntesis'))
        self.assertTrue(guardar.disabled)
        app.multiselect[0].set_value([app.multiselect[0].options[0]]).run()
        app.checkbox[0].check().run()
        next(b for b in app.button if b.label.startswith('Guardar síntesis')).click().run()
        self.assertFalse(app.exception)
        saved=app.session_state.qa_guardados
        self.assertEqual(len(saved),1)
        self.assertEqual(len(saved[0][1]['necesidades']),1)
        self.assertLessEqual(len(saved[0][1]['resumen']),1200)
        # Simula volver a entrar sin el OCR en memoria: se recupera del índice.
        del app.session_state['qa_QA-DOC_lectura']
        app.run()
        self.assertFalse(app.exception)
        self.assertTrue(any(saved[0][1]['resumen']==m.value for m in app.markdown))
        self.assertFalse(app.text_area)

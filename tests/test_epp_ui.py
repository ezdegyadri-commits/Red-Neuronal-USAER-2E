from pathlib import Path
from copy import deepcopy
import unittest
from streamlit.testing.v1 import AppTest

class EPPUITests(unittest.TestCase):
    def open(self):return AppTest.from_file(str(Path(__file__).with_name('fixture_epp_panel.py')),default_timeout=30).run()
    def test_edicion_se_guarda_y_recupera_en_sesion_nueva(self):
        app=self.open();self.assertFalse(app.exception)
        next(t for t in app.text_area if t.label=='5.1. Competencia curricular').set_value('Lectura documentada: reconoce letras.').run()
        self.assertFalse(app.exception)
        rows=deepcopy(app.session_state['qa_epp_rows'])
        self.assertGreater(len(rows),1)
        new=AppTest.from_file(str(Path(__file__).with_name('fixture_epp_panel.py')),default_timeout=30)
        new.session_state['qa_epp_rows']=rows;new.run()
        self.assertEqual(next(t for t in new.text_area if t.label=='5.1. Competencia curricular').value,'Lectura documentada: reconoce letras.')
    def test_especialistas_no_crean_y_editan_solo_su_area(self):
        for area,field in [('Psicología','3.1. Atención'),('Comunicación','4.1. Comprensión receptiva'),('Trabajo Social','6.3. Contexto social')]:
            app=self.open();app.selectbox[0].set_value(area).run();self.assertFalse(app.exception)
            self.assertFalse(any(b.label=='Crear EPP y guardar' for b in app.button))
            self.assertTrue(any(t.label==field for t in app.text_area))
            self.assertFalse(any(t.label=='5.1. Competencia curricular' for t in app.text_area))
            next(t for t in app.text_area if t.label==field).set_value('Hallazgo ficticio propio del área.').run()
            self.assertFalse(app.exception)
    def test_director_consulta_sin_edicion_de_areas(self):
        app=self.open();app.selectbox[0].set_value('Dirección').run()
        self.assertFalse(app.exception);self.assertEqual(len(app.text_area),0)
    def test_ia_solo_despues_de_revisar_y_permanece_borrador(self):
        app=self.open()
        next(b for b in app.button if b.label=='Reunir expediente y evaluaciones').click().run()
        generate=next(b for b in app.button if b.label=='Generar mis apartados')
        self.assertTrue(generate.disabled)
        next(c for c in app.checkbox if c.label.startswith('Revisé el resumen:')).check().run()
        next(c for c in app.checkbox if c.label.startswith('Sustituir los textos')).check().run()
        next(b for b in app.button if b.label=='Generar mis apartados').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['qa_ai_calls'],1)
        self.assertEqual(app.session_state['qa_epp_rows'][-1][8],'BORRADOR')

if __name__=='__main__':unittest.main()

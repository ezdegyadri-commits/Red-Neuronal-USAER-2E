from pathlib import Path
from copy import deepcopy
import unittest
from streamlit.testing.v1 import AppTest

class EPPUITests(unittest.TestCase):
    def open(self):return AppTest.from_file(str(Path(__file__).with_name('fixture_epp_panel.py')),default_timeout=30).run()
    def instrument(self,app):
        for label,text in [('Instrumento o técnica aplicada','Observación ficticia'),
            ('Fecha de aplicación (AAAA-MM-DD)','2026-10-07'),
            ('Resultados y observaciones documentadas','Reconoce letras con apoyo documentado.')]:
            next(t for t in app.text_area if t.label==label).set_value(text).run()
        next(c for c in app.checkbox if c.label.startswith('Revisé los resultados')).check().run()
        next(b for b in app.button if b.label=='Incorporar instrumento aplicado').click().run()
        self.assertFalse(app.exception)
        return app
    def test_precarga_y_vacio_manual_no_se_repone(self):
        app=self.open()
        age=next(t for t in app.text_area if t.label=='Edad')
        self.assertIn('referencia del padrón',age.value)
        age.set_value('').run()
        rows=deepcopy(app.session_state['qa_epp_rows'])
        new=AppTest.from_file(str(Path(__file__).with_name('fixture_epp_panel.py')),default_timeout=30)
        new.session_state['qa_epp_rows']=rows;new.run()
        self.assertEqual(next(t for t in new.text_area if t.label=='Edad').value,'')
    def test_sin_instrumentos_no_generacion_y_carga_conservada(self):
        app=self.open()
        self.assertTrue(next(b for b in app.button if b.label=='Reunir expediente y evaluaciones').disabled)
        self.assertTrue(any(u.label=='Evaluación de mi área' for u in app.get('file_uploader')))
        self.assertEqual(app.session_state['qa_ai_calls'],0)
    def test_aplicacion_incompleta_se_recupera_al_entrar(self):
        app=self.open()
        next(t for t in app.text_area if t.label=='Instrumento o técnica aplicada').set_value('Observación en curso').run()
        new=AppTest.from_file(str(Path(__file__).with_name('fixture_epp_panel.py')),default_timeout=30)
        new.session_state['qa_epp_rows']=deepcopy(app.session_state['qa_epp_rows']);new.run()
        self.assertEqual(next(t for t in new.text_area if t.label=='Instrumento o técnica aplicada').value,'Observación en curso')
        self.assertTrue(next(b for b in new.button if b.label=='Reunir expediente y evaluaciones').disabled)
    def test_entrada_directa_recuperable_y_resumen_obsoleto(self):
        app=self.instrument(self.open())
        next(b for b in app.button if b.label=='Reunir expediente y evaluaciones').click().run()
        next(c for c in app.checkbox if c.label.startswith('Revisé el resumen:')).check().run()
        next(c for c in app.checkbox if c.label.startswith('Sustituir los textos')).check().run()
        next(b for b in app.button if b.label.startswith('Retirar esta evaluación')).click().run()
        self.assertTrue(next(b for b in app.button if b.label=='Generar mis apartados').disabled)
        self.assertEqual(app.session_state['qa_ai_calls'],0)
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
    def test_especialistas_filtran_escuela_y_solo_epp_iniciadas(self):
        for area in ('Psicología','Comunicación','Trabajo Social'):
            app=AppTest.from_file(str(Path(__file__).with_name('fixture_epp_panel.py')),default_timeout=30)
            app.session_state['qa_multiescuela']=True;app.run()
            app.selectbox[0].set_value(area).run()
            school=next(s for s in app.selectbox if s.label=='Escuela asignada')
            self.assertEqual(len(school.options),3)
            school.set_value('E2').run()
            pupils=next(s for s in app.selectbox if s.label=='Alumno con EPP iniciada')
            self.assertEqual(len(pupils.options),1);self.assertIn('Alumno escuela dos',pupils.options[0])
            self.assertFalse(any('Sin EPP' in label for label in pupils.options))
            field={'Psicología':'3.1. Atención','Comunicación':'4.1. Comprensión receptiva','Trabajo Social':'6.3. Contexto social'}[area]
            next(t for t in app.text_area if t.label==field).set_value('Aportación de escuela dos.').run()
            self.assertEqual(app.session_state['qa_epp_rows'][-1][0],'FICTICIO-A2')
            next(s for s in app.selectbox if s.label=='Escuela asignada').set_value('E3').run()
            self.assertFalse(app.exception)
            self.assertFalse(any(s.label=='Alumno con EPP iniciada' for s in app.selectbox))
            self.assertTrue(any('Todavía no hay EPP' in i.value for i in app.info))
            next(s for s in app.selectbox if s.label=='Escuela asignada').set_value('E1').run()
            self.assertIn('Alumno de prueba',next(s for s in app.selectbox if s.label=='Alumno con EPP iniciada').options[0])
            self.assertEqual(next(t for t in app.text_area if t.label==field).value,'')
            next(s for s in app.selectbox if s.label=='Escuela asignada').set_value('E2').run()
            self.assertEqual(next(t for t in app.text_area if t.label==field).value,'Aportación de escuela dos.')
            self.assertEqual(sum(row[2]=='META' for row in app.session_state['qa_epp_rows']),2)
    def test_ia_solo_despues_de_revisar_y_permanece_borrador(self):
        app=self.instrument(self.open())
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

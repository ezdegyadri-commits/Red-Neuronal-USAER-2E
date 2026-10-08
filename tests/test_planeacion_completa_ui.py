from pathlib import Path
import unittest
from streamlit.testing.v1 import AppTest

class GeneracionCompletaUITests(unittest.TestCase):
    def abrir(self):return AppTest.from_file(str(Path(__file__).with_name('fixture_planeacion_completa.py')),default_timeout=30).run()
    def test_cuatro_perfiles_generan_editan_recuperan_y_no_repiten_ia(self):
        for area in ['Aprendizaje','Psicología','Comunicación','Trabajo Social']:
            app=self.abrir();app.radio[0].set_value(area).run()
            next(m for m in app.multiselect if m.label=='Alumnos de atención grupal de la misma escuela').set_value(['A1']).run()
            next(b for b in app.button if b.label=='Crear y guardar borrador').click().run()
            self.assertFalse(app.exception,area)
            self.assertTrue(any(b.label=='Generar mi planeación trimestral con IA' for b in app.button))
            next(c for c in app.checkbox if c.label.startswith('Revisé el resumen y los ajustes')).check().run()
            next(b for b in app.button if b.label=='Generar mi planeación trimestral con IA').click().run()
            self.assertFalse(app.exception,area)
            self.assertEqual(app.session_state.llamadas_ficticias,1)
            doc=app.session_state.versiones_ficticias[-1]
            self.assertIn('generacion_completa',doc['metadatos'])
            self.assertTrue(any('Vista previa de tu planeación' in s.value for s in app.subheader))
            next(b for b in app.button if b.label=='Abrir documento').click().run()
            self.assertFalse(app.exception,area)
            self.assertEqual(app.session_state.llamadas_ficticias,1)
            self.assertTrue(any(b.label=='Recuperar la generación guardada' for b in app.button))
            if area!='Trabajo Social':
                next(t for t in app.text_area if t.label=='Evaluación').set_value('Seguimiento revisado por docente.').run()
                next(b for b in app.button if b.label=='Guardar borrador').click().run()
                self.assertEqual(app.session_state.versiones_ficticias[-1]['textos']['Evaluación'],'Seguimiento revisado por docente.')
                self.assertEqual(app.session_state.llamadas_ficticias,1)
    def test_configuracion_se_recupera_sin_otra_llamada(self):
        app=self.abrir()
        next(m for m in app.multiselect if m.label=='Alumnos de atención grupal de la misma escuela').set_value(['A1']).run()
        next(b for b in app.button if b.label=='Crear y guardar borrador').click().run()
        next(n for n in app.number_input if n.label=='Duración de cada sesión (minutos)').set_value(60).run()
        next(b for b in app.button if b.label=='Guardar borrador').click().run()
        next(b for b in app.button if b.label=='Abrir documento').click().run()
        self.assertEqual(next(n for n in app.number_input if n.label=='Duración de cada sesión (minutos)').value,60)
        self.assertEqual(app.session_state.llamadas_ficticias,0)
    def test_actualizacion_requiere_revision_y_no_replica_ia(self):
        app=self.abrir()
        next(m for m in app.multiselect if m.label=='Alumnos de atención grupal de la misma escuela').set_value(['A1']).run()
        next(b for b in app.button if b.label=='Crear y guardar borrador').click().run()
        next(c for c in app.checkbox if c.label.startswith('Revisé el resumen y los ajustes')).check().run()
        next(b for b in app.button if b.label=='Generar mi planeación trimestral con IA').click().run()
        antes=app.session_state.versiones_ficticias[-1]['tablas']
        next(c for c in app.checkbox if c.label.startswith('Revisé el resumen y los ajustes')).check().run()
        next(b for b in app.button if b.label=='Recuperar la generación guardada').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state.versiones_ficticias[-1]['tablas'],antes)
        self.assertEqual(app.session_state.llamadas_ficticias,1)
        next(b for b in app.button if b.label=='Aplicar actualización conservando mis ediciones').click().run()
        self.assertFalse(app.exception);self.assertEqual(app.session_state.llamadas_ficticias,1)
    def test_aporte_especialista_se_autoguarda_en_documento_de_apoyo(self):
        app=self.abrir()
        next(m for m in app.multiselect if m.label=='Alumnos de atención grupal de la misma escuela').set_value(['A1']).run()
        next(b for b in app.button if b.label=='Crear y guardar borrador').click().run()
        app.radio[0].set_value('Psicología').run()
        self.assertFalse(app.exception)
        next(t for t in app.text_area if t.label=='Observaciones de mi área').set_value('Hallazgo educativo documentado del área.').run()
        self.assertFalse(app.exception)
        doc=app.session_state.versiones_ficticias[-1]
        self.assertEqual(doc['cuenta'],'demo-Aprendizaje')
        self.assertEqual(doc['metadatos']['aportaciones_equipo']['Psicología']['observaciones'],'Hallazgo educativo documentado del área.')
        self.assertFalse(doc['metadatos']['firma_aprobada_por'])

if __name__=='__main__':unittest.main()

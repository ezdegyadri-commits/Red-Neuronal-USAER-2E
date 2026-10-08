from pathlib import Path
import unittest
from streamlit.testing.v1 import AppTest

class EquipoUITests(unittest.TestCase):
    def test_tres_perfiles_subgrupo_sesion_recuperacion_y_director(self):
        for area in ['Psicología','Comunicación','Trabajo Social']:
            app=AppTest.from_file(str(Path(__file__).with_name('fixture_planeacion_equipo.py')),default_timeout=30).run()
            next(s for s in app.selectbox if s.label=='Perfil de demostración').set_value(area).run()
            next(m for m in app.multiselect if m.label=='Alumnos de atención grupal de la misma escuela').set_value(['A1']).run()
            next(b for b in app.button if b.label=='Crear y guardar borrador').click().run()
            self.assertFalse(app.exception,area)
            next(t for t in app.text_input if t.label=='Nombre del subgrupo').set_value('Subgrupo 1').run()
            next(m for m in app.multiselect if m.label=='Alumnos de este subgrupo').set_value(['A1']).run()
            next(b for b in app.button if b.label=='Guardar subgrupo').click().run()
            self.assertFalse(app.exception,area)
            for label in ['Qué queremos lograr','Cómo lo trabajaremos','Materiales y recursos','Cómo reconoceremos el avance']:
                next(t for t in app.text_area if t.label==label).set_value('Contenido educativo de demostración.').run()
            next(b for b in app.button if b.label=='Guardar sesión en la planeación').click().run()
            self.assertFalse(app.exception,area)
            ultimo=app.session_state.versiones_demo[-1]
            self.assertEqual(len(ultimo['metadatos']['equipo']['sesiones']),1)
            self.assertEqual(ultimo['formato'],'XXV' if area=='Trabajo Social' else 'XXIII')
            next(b for b in app.button if b.label=='Abrir documento').click().run()
            self.assertFalse(app.exception,area)
            next(s for s in app.selectbox if s.label=='Perfil de demostración').set_value('Dirección').run()
            self.assertFalse(app.exception,area)
            self.assertTrue(any(b.label=='Validar revisión' for b in app.button))

if __name__=='__main__':unittest.main()

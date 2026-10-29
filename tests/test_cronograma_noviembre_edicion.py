import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest
from services.cronogramas import perfil_especialista
from config.settings import ESCUELAS_USAER


class NoviembreTests(unittest.TestCase):
    def abrir(self,nombre,rol):
        app=AppTest.from_file(str(Path(__file__).parent/'fixtures/cronograma_noviembre_app.py'),default_timeout=30)
        app.session_state['qa_nombre']=nombre;app.session_state['qa_rol']=rol
        return app.run()

    def test_diego_y_maria_jose_editan_noviembre_con_bandera_antigua(self):
        for nombre,rol in (('Diego Peralta Torres','Trabajo Social'),('María José Cupul Realpozo','Psicología')):
            with self.subTest(nombre=nombre):
                app=self.abrir(nombre,rol);self.assertFalse(app.exception)
                fields=[w for w in app.selectbox if w.label=='Escuela o junta']
                self.assertTrue(fields);self.assertTrue(all(not w.disabled for w in fields))
                permitidas=perfil_especialista(nombre,rol)['escuelas']
                self.assertTrue(set(permitidas)<=set(fields[0].options))
                self.assertFalse((set(ESCUELAS_USAER)-set(permitidas))&set(fields[0].options))
                self.assertFalse(any(b.label=='Editar cronograma' for b in app.button))
                field=next(w for w in fields if '2026-11-03_escuela' in w.key)
                field.select(permitidas[-1]).run()
                activity=next(w for w in app.text_area if '2026-11-03_actividad' in w.key)
                activity.input('Acompañamiento educativo ajustado').run()
                self.assertFalse(app.exception)
                next(b for b in app.button if b.label=='Guardar cambios y generar PDF').click().run()
                self.assertFalse(app.exception)
                saved=app.session_state['qa_guardado'];self.assertEqual(saved['mes'],'2026-11')
                dia=next(d for d in saved['agenda'] if d['fecha']=='2026-11-03')
                self.assertEqual(dia['escuela'],permitidas[-1]);self.assertEqual(dia['actividad'],'Acompañamiento educativo ajustado')
                self.assertTrue(all(not w.disabled for w in app.selectbox if w.label=='Escuela o junta'))

    def test_diego_dispone_ocho_escuelas_sin_cambiar_su_rol(self):
        app=self.abrir('TS. Diego Peralta Torres','TS')
        self.assertFalse(app.exception)
        field=next(w for w in app.selectbox if w.label=='Escuela o junta')
        self.assertTrue(set(ESCUELAS_USAER)<=set(field.options))

    def test_cuenta_ajena_no_obtiene_editor_ni_escuelas(self):
        app=self.abrir('Persona ajena ficticia','Trabajo Social')
        self.assertFalse(app.exception);self.assertTrue(app.error)
        self.assertFalse(any(w.label=='Escuela o junta' for w in app.selectbox))


if __name__=='__main__':unittest.main()

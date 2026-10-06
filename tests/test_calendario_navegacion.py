from datetime import date
from pathlib import Path
import unittest
from streamlit.testing.v1 import AppTest

class NavegacionCalendarioTests(unittest.TestCase):
    def abrir(self):
        return AppTest.from_file(str(Path(__file__).parent/'fixtures'/'calendario_navegacion_app.py'),default_timeout=30).run()
    def test_navegar_mes_siguiente_anterior_y_anio(self):
        app=self.abrir();self.assertFalse(app.exception)
        selector=next(s for s in app.selectbox if s.label=='Mes de actividades')
        selector.set_value('2026-12').run()
        next(b for b in app.button if b.label=='Mes siguiente ▶').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(next(s for s in app.selectbox if s.label=='Mes de actividades').value,'2027-01')
        next(b for b in app.button if b.label=='◀ Mes anterior').click().run()
        self.assertEqual(next(s for s in app.selectbox if s.label=='Mes de actividades').value,'2026-12')
    def test_publicacion_futura_visible_para_todos_y_edicion_sin_duplicar(self):
        app=self.abrir()
        next(s for s in app.selectbox if s.label=='Mes de actividades').set_value('2026-11').run()
        next(t for t in app.text_input if t.label=='Actividad').set_value('Encuentro común ficticio')
        next(d for d in app.date_input if d.label=='Fecha de la actividad').set_value(date(2026,11,5))
        next(b for b in app.button if b.label=='Publicar actividad para todos').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.session_state.eventos_ficticios),1)
        for perfil in ['Psicología','Comunicación','Trabajo Social','Apoyo']:
            app.radio[0].set_value(perfil).run()
            next(s for s in app.selectbox if s.label=='Mes para consultar').set_value('2026-11').run()
            self.assertFalse(app.exception,perfil)
            self.assertTrue(any(m.value=='Encuentro común ficticio' for m in app.markdown),perfil)
            self.assertFalse(any(b.label=='Publicar actividad para todos' for b in app.button))
        app.radio[0].set_value('Dirección').run()
        next(s for s in app.selectbox if s.label=='Mes de actividades').set_value('2026-11').run()
        seleccionar=next(s for s in app.selectbox if s.label=='Añadir o actualizar')
        nuevo=next(e for e in seleccionar.options if 'Encuentro común ficticio' in e)
        index=seleccionar.options.index(nuevo)
        seleccionar.select_index(index).run()
        next(t for t in app.text_input if t.label=='Actividad').set_value('Encuentro corregido')
        next(b for b in app.button if b.label=='Publicar actividad para todos').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.session_state.eventos_ficticios),2)
        self.assertEqual(len({e['ID_Evento'] for e in app.session_state.eventos_ficticios}),1)
    def test_mes_sin_actividades_muestra_mensaje_y_no_escribe(self):
        app=self.abrir();app.radio[0].set_value('Apoyo').run()
        next(s for s in app.selectbox if s.label=='Mes para consultar').set_value('2028-01').run()
        self.assertFalse(app.exception)
        self.assertTrue(any('No hay actividades publicadas' in c.value for c in app.caption))
        self.assertEqual(app.session_state.eventos_ficticios,[])

if __name__=='__main__':unittest.main()

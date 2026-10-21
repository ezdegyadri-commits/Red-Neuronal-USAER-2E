import json
from datetime import date
from pathlib import Path
from unittest import TestCase
from streamlit.testing.v1 import AppTest

class ContinuidadUITests(TestCase):
    def fixture(self,nombre):
        return AppTest.from_file(str(Path(__file__).parent/'fixtures'/nombre),default_timeout=30).run()

    def emitir(self,app,event):
        componente=app.get('bidi_component')[0]
        estados=app._tree.get_widget_states()
        estados.widgets.add(id=componente.proto.id,json_value=json.dumps({'evento':event}))
        app._run(estados)
        self.assertFalse(app.exception)

    def test_sesion_recupera_despues_de_recarga_y_cierre_revoca(self):
        app=self.fixture('continuidad_sesion_app.py')
        app.button[0].click().run();self.assertFalse(app.exception)
        token=app.session_state['_sesion_token']
        self.assertEqual(len(app.session_state.diario_ficticio),1)
        for key in ('autenticado','usuario','nombre','rol','escuelas_permitidas','_sesion_token'):
            del app.session_state[key]
        self.emitir(app,{'accion':'recuperar','token':token,'nonce':'recarga-1'})
        self.assertEqual(app.session_state.usuario,'ficticia')
        self.assertTrue(app.session_state.autenticado)
        self.assertEqual(len(app.session_state.diario_ficticio),1)
        next(b for b in app.button if b.label=='Cerrar acceso de prueba').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state.diario_ficticio[-1]['Estado'],'CERRADA')

    def test_control_iniciado_por_apoyo_continuado_por_comunicacion(self):
        app=self.fixture('epp_control_app.py')
        app.checkbox[0].check().run()
        self.assertFalse(app.exception)
        next(w for w in app.date_input if w.label=='Fecha programada').set_value(date(2026,11,3))
        next(w for w in app.selectbox if w.label=='Estado').set_value('Programada')
        next(w for w in app.text_area if w.label=='Aspectos a evaluar').set_value('Participación con apoyos')
        next(b for b in app.button if b.label=='Guardar programación').click().run()
        self.assertFalse(app.exception);self.assertEqual(len(app.session_state.control_ficticio),1)
        app.radio[0].set_value('Comunicación').run()
        self.assertFalse(app.exception)
        self.assertNotIn('Nueva programación',next(w for w in app.selectbox if w.label=='Programación a continuar').options)
        next(w for w in app.text_area if w.label=='Instrumentos previstos').set_value('Observación de comunicación funcional')
        next(b for b in app.button if b.label=='Guardar programación').click().run()
        self.assertFalse(app.exception);self.assertEqual(len(app.session_state.control_ficticio),2)
        self.assertEqual(app.session_state.control_ficticio[-1]['Aspectos'],'Participación con apoyos')

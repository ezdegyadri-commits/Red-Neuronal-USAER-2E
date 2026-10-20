from unittest import TestCase
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from tests.test_planeacion_panel import ACTOR
from ui.planeacion_accesos import opciones


APP='''
import streamlit as st
from unittest.mock import patch
from services import planeacion as s
from ui import planeacion as u,planeacion_viva as ui
from tests.test_planeacion_panel import ACTOR
actor={**ACTOR,'area':st.session_state.get('area_prueba','Comunicación')}
def entrada(*args):st.text('ENTRADA PROPIA')
def equipo(*args):st.text('ENTRADA COMPARTIDA')
with patch.object(s,'identidad',return_value=actor),patch.object(u,'_prefix',return_value='p'),patch.object(ui,'_entrada',side_effect=entrada),patch('ui.planeacion_colaboracion.panel',side_effect=equipo):
    ui.pagina()
'''


class AccesosTests(TestCase):
    def test_selector_reune_duplicados_y_muestra_apoyo_y_comunicacion(self):
        from copy import deepcopy
        from pathlib import Path
        import streamlit as st
        from ui import planeacion_papel as ui
        from services import planeacion as s
        from tests.test_planeacion_grupo_unico import duplicados
        nombres=('identidad','autorizar','compartidos','padron_autorizado','listar','refrescar','guardar_aportacion')
        originales={n:getattr(s,n) for n in nombres}
        def editor(**kw):st.session_state['qa_union']=kw['hoja'];return None
        try:
            with patch.object(ui,'editor',side_effect=editor):
                app=AppTest.from_file(str(Path(__file__).with_name('fixture_acceso_equipo.py')),default_timeout=30).run()
                a,b=duplicados()
                a['datos']['Alumnos'][0]['Grado']='3°';b['datos']['Alumnos'][0]['Grado']='3°'
                app.session_state['f_docs']=[deepcopy(a),deepcopy(b)];app.run()
                self.assertFalse(app.exception)
                selector=next(w for w in app.selectbox if w.label.startswith('Documento compartido'))
                self.assertEqual(len(selector.options),1)
                self.assertNotIn('origen',selector.options[0]);self.assertNotIn('copia',selector.options[0])
                next(w for w in app.button if w.label=='Abrir Anexo XIX compartido').click().run()
                self.assertFalse(app.exception)
                texto=str(app.session_state['qa_union']['tables'])
                self.assertIn('Texto de apoyo',texto);self.assertIn('Actividad de comunicación',texto)
        finally:
            for n,v in originales.items():setattr(s,n,v)

    def test_rol_muestra_dos_accesos_claros_no_otras_areas(self):
        for area in ('Aprendizaje','Psicología','Comunicación','Trabajo Social'):
            labels=[t for id,t,detalle,icon in opciones({**ACTOR,'area':area})]
            self.assertEqual(len(labels),2)
            self.assertEqual(labels[1],'Planeación grupal compartida')
            self.assertIn('apoyo' if area=='Aprendizaje' else area,labels[0])

    def test_inicio_abre_directamente_sin_bloqueo_de_menu(self):
        app=AppTest.from_string(APP,default_timeout=30).run()
        self.assertFalse(app.exception)
        self.assertTrue(any(t.value=='ENTRADA PROPIA' for t in app.text))
        self.assertFalse(any(t.value=='ENTRADA COMPARTIDA' for t in app.text))

    def test_menu_accesos_aislado(self):
        MENU_APP='''
import streamlit as st
from ui.planeacion_accesos import menu
from tests.test_planeacion_panel import ACTOR
actor={**ACTOR,'area':'Comunicación'}
menu('p',actor)
'''
        app=AppTest.from_string(MENU_APP,default_timeout=30).run()
        self.assertFalse(app.exception)
        self.assertEqual([b.label for b in app.button],['Mi planeación de Comunicación','Planeación grupal compartida'])

    def test_css_respetar_movimiento_reducido(self):
        from pathlib import Path
        source=(Path(__file__).parents[1]/'ui'/'planeacion_accesos.py').read_text(encoding='utf-8')
        self.assertIn('prefers-reduced-motion',source)
        self.assertIn('focus-visible',source)

"""Continuidad sin IA con documentos y repositorios ficticios."""
from copy import deepcopy
from pathlib import Path
import unittest
import hashlib
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from services import planeacion_respaldo as r
from tests.test_planeacion_completa import documento
from tests import test_planeacion_simple as simple_tests


class AutollenadoTests(unittest.TestCase):
    def setUp(self):
        self.auth = patch.object(r, 'autorizar')
        self.auth.start(); self.addCleanup(self.auth.stop)

    def test_cuatro_areas_sin_reemplazar_formatos_ni_redaccion(self):
        for area in ('Aprendizaje','Psicología','Comunicación','Trabajo Social'):
            for grupal in (False, True):
                with self.subTest(area=area,grupal=grupal):
                    doc=documento(area,grupal);doc['revision']='r1'
                    doc['metadatos']['necesidades_confirmadas']='Decisión profesional conservada'
                    doc['textos'][next(iter(doc['textos']))]='Redacción manual conservada'
                    previo=deepcopy(doc);nuevo=r.autollenar(doc)
                    for campo in ('datos','tablas','textos','id','cuenta','revision','formato'):
                        self.assertEqual(nuevo[campo],previo[campo])
                    self.assertEqual(nuevo['metadatos']['necesidades_confirmadas'],'Decisión profesional conservada')
                    self.assertEqual(doc,previo)

    def test_fuentes_ajenas_y_no_verificadas_excluidas(self):
        doc=documento()
        doc['metadatos']['fuentes'].extend([
            {**doc['metadatos']['fuentes'][0],'alumno':'A999','texto':'Contenido de otro alumno'},
            {**doc['metadatos']['fuentes'][0],'vinculo_verificado':False,'texto':'Sin vínculo comprobado'}])
        nuevo=r.autollenar(doc)
        self.assertIn('E1',nuevo['metadatos']['necesidades_confirmadas'])
        self.assertNotIn('Contenido de otro',nuevo['metadatos']['necesidades_confirmadas'])
        self.assertNotIn('Sin vínculo',nuevo['metadatos']['necesidades_confirmadas'])

    def test_repetir_no_duplica_ni_genera(self):
        doc=r.autollenar(documento())
        self.assertEqual(r.autollenar(doc),doc)
        self.assertNotIn('generacion_completa',doc['metadatos'])
        self.assertFalse(doc['tablas']['aprendizajes'])

    def test_sin_fuentes_conserva_formato_vacio_editable(self):
        doc=documento();doc['metadatos']['fuentes']=[]
        doc['metadatos']['fuentes_pendientes']=['EPP']
        nuevo=r.autollenar(doc)
        self.assertEqual(nuevo['tablas'],doc['tablas'])
        self.assertEqual(nuevo['metadatos']['necesidades_confirmadas'],'')
        self.assertEqual(nuevo['metadatos']['fuentes_pendientes'],['EPP'])

    def test_autorizacion_antes_del_autollenado(self):
        with patch.object(r,'autorizar',side_effect=PermissionError),patch.object(r,'prellenar') as llenar:
            with self.assertRaises(PermissionError):r.autollenar(documento())
            llenar.assert_not_called()


class ContinuidadUITests(unittest.TestCase):
    setUp=simple_tests.RecorridoTests.setUp
    tearDown=simple_tests.RecorridoTests.tearDown
    paso=simple_tests.RecorridoTests.paso

    def abrir(self,area='Aprendizaje',individual=False,sin_fuentes=False):
        app=AppTest.from_file(str(Path(__file__).with_name('fixture_planeacion_respaldo.py')),default_timeout=30)
        app.session_state['individual_ficticio']=individual
        app.session_state['sin_fuentes_ficticio']=sin_fuentes
        app.run();app.radio[0].set_value(area).run()
        next(m for m in app.multiselect if m.label=='Alumno o alumnos para planear').set_value(['A1']).run()
        next(b for b in app.button if b.label=='Crear mi borrador').click().run()
        self.assertFalse(app.exception,area)
        return app

    def test_cuatro_perfiles_fallo_ia_continuan_editan_guardan_y_recuperan(self):
        for area in ('Aprendizaje','Psicología','Comunicación','Trabajo Social'):
            with self.subTest(area=area):
                app=self.abrir(area)
                doc=deepcopy(app.session_state.versiones_ficticias[-1])
                next(c for c in app.checkbox if c.label.startswith('Revisé el resumen')).check().run()
                app.session_state['fallo_ia_ficticio']=True
                next(b for b in app.button if b.label=='Preparar mi planeación').click().run()
                self.assertFalse(app.exception)
                self.assertEqual(app.session_state.llamadas_ficticias,1)
                next(b for b in app.button if b.label=='Continuar sin IA · abrir mi formato').click().run()
                self.assertFalse(app.exception)
                self.assertEqual(app.session_state.llamadas_ficticias,1)
                self.assertTrue(any(b.label=='Guardar borrador' for b in app.button))
                self.assertTrue(any(b.label=='Ver PDF' for b in app.button))
                next(b for b in app.button if b.label=='Autollenar información disponible · sin IA').click().run()
                self.assertFalse(app.exception)
                campo='Resultados obtenidos en los diferentes contextos' if area=='Trabajo Social' else 'Observaciones'
                next(t for t in app.text_area if t.label==campo).set_value('Edición profesional sin motor de IA.').run()
                next(b for b in app.button if b.label=='Guardar borrador').click().run()
                saved=app.session_state.versiones_ficticias[-1]
                self.assertEqual(saved['id'],doc['id']);self.assertEqual(saved['formato'],doc['formato'])
                self.assertEqual(saved['textos'][campo],'Edición profesional sin motor de IA.')
                self.assertFalse(saved['metadatos'].get('generacion_completa'))
                self.paso(app,0);next(b for b in app.button if b.label=='Continuar').click().run()
                self.assertFalse(app.exception)
                self.assertEqual(app.session_state.versiones_ficticias[-1]['textos'][campo],'Edición profesional sin motor de IA.')
                self.assertEqual(app.session_state.llamadas_ficticias,1)
                self.paso(app,2)
                next(b for b in app.button if b.label=='Volver a preparar con IA').click().run()
                self.assertFalse(app.exception)
                self.assertTrue(any(b.label=='Preparar mi planeación' for b in app.button))

    def test_continuar_no_crea_version_y_respeta_validacion_de_envio(self):
        app=self.abrir();count=len(app.session_state.versiones_ficticias)
        next(b for b in app.button if b.label=='Continuar sin IA · abrir mi formato').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.session_state.versiones_ficticias),count)
        self.assertTrue(next(b for b in app.button if b.label=='Enviar a Dirección').disabled)
        next(b for b in app.button if b.label=='Ver PDF').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state.llamadas_ficticias,0)

    def test_acceso_individual_sin_evidencia_ni_ia(self):
        app=self.abrir(individual=True,sin_fuentes=True)
        self.assertTrue(next(b for b in app.button if b.label=='Preparar mi planeación').disabled)
        next(b for b in app.button if b.label=='Continuar sin IA · abrir mi formato').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state.versiones_ficticias[-1]['metadatos']['modalidad_planeacion'],'individual')
        self.assertTrue(any(b.label=='Guardar borrador' for b in app.button))
        self.assertEqual(app.session_state.llamadas_ficticias,0)

    def test_fallo_guardado_conserva_edicion_y_respaldo(self):
        app=self.abrir()
        next(b for b in app.button if b.label=='Continuar sin IA · abrir mi formato').click().run()
        app.session_state['fallo_guardado_ficticio']=True
        next(t for t in app.text_area if t.label=='Observaciones').set_value('Texto que debe conservarse ante fallo.').run()
        next(b for b in app.button if b.label=='Guardar borrador').click().run()
        self.assertFalse(app.exception)
        prefix='planeacion_'+hashlib.sha256(b'demo-Aprendizaje').hexdigest()[:12]+'_grupal'
        self.assertEqual(app.session_state[prefix+'_doc']['textos']['Observaciones'],'Texto que debe conservarse ante fallo.')
        self.assertTrue(app.session_state[prefix+'_pending'])
        self.assertTrue(app.get('download_button'))
        self.assertEqual(app.session_state.llamadas_ficticias,0)

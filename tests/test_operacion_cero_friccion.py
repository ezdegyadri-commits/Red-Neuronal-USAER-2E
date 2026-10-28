"""Red y cuentas ficticias: no abre Sheets ni usa expedientes reales."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from threading import Event
from unittest.mock import patch
import unittest

from services import planeacion as s
from tests import test_planeacion_panel as fixtures
documento=fixtures.documento


class AcusesTests(unittest.TestCase):
    def setUp(self):
        fixtures.PanelTests.setUp(self)
        self.origin=patch.object(s,'identidad',return_value={**fixtures.ACTOR,'origen_editor':'pestana-ficticia-a'})
        self.origin.start()

    def tearDown(self):
        self.origin.stop()
        s.intentos().clear()
        fixtures.PanelTests.tearDown(self)

    def test_respuesta_perdida_y_escritura_posterior_se_concilian(self):
        doc = documento()
        append = self.sheet.append_rows
        def perdido(rows, value_input_option):
            append(rows, value_input_option)
            raise TimeoutError('Respuesta ficticia perdida')
        with patch.object(self.sheet, 'append_rows', side_effect=perdido):
            with self.assertRaises(TimeoutError):
                s.guardar(doc)
        doc['textos']['Evaluación'] = 'Texto escrito después de la espera'
        saved = s.guardar(doc)
        self.assertEqual(saved['textos']['Evaluación'], doc['textos']['Evaluación'])
        self.assertEqual(len(self.sheet.options), 2)
        self.assertEqual(s.guardar(saved)['revision'], saved['revision'])
        self.assertEqual(len(self.sheet.options), 2)

    def test_otro_aporte_no_queda_bloqueado_por_intento_sin_append(self):
        doc = documento()
        with patch.object(self.sheet, 'append_rows', side_effect=TimeoutError):
            with self.assertRaises(TimeoutError):
                s.guardar(doc)
        original = next(iter(s.intentos().values()))['saved']['revision']
        # Una aportación de otra clave debe conciliar el envío incierto anterior.
        s._conciliar_otros_intentos(doc['id'], (doc['id'], 'especialista-ficticio', True))
        self.assertFalse(s.intentos())
        self.assertEqual(s.reconstruir(self.sheet.rows)[0]['revision'], original)
        self.assertEqual(len(self.sheet.options), 1)

    def test_conflicto_real_de_misma_celda_sigue_protegido(self):
        first = s.guardar(documento())
        a, b = deepcopy(first), deepcopy(first)
        a['textos']['Evaluación'] = 'Versión A'
        b['textos']['Evaluación'] = 'Versión B'
        s.guardar(a)
        with self.assertRaises(RuntimeError):
            s.guardar(b)
        self.assertEqual(len(self.sheet.options), 2)
        self.assertEqual(b['textos']['Evaluación'], 'Versión B')

    def test_otra_pestana_del_mismo_usuario_no_se_confunde_con_continuacion(self):
        doc=s.guardar(documento())
        first,other=deepcopy(doc),deepcopy(doc)
        first['textos']['Evaluación']='Captura en pestaña A'
        other['textos']['Evaluación']='Captura en pestaña B'
        append=self.sheet.append_rows
        def perdido(rows,value_input_option):
            append(rows,value_input_option);raise TimeoutError('Acuse ficticio perdido')
        with patch.object(self.sheet,'append_rows',side_effect=perdido):
            with self.assertRaises(TimeoutError):s.guardar(first)
        with patch.object(s,'identidad',return_value={**fixtures.ACTOR,'origen_editor':'pestana-ficticia-b'}):
            with self.assertRaises(RuntimeError):s.guardar(other)
        self.assertEqual(len(self.sheet.options),2)
        self.assertEqual(s.reconstruir(self.sheet.rows)[-1]['textos']['Evaluación'],'Captura en pestaña A')
        self.assertEqual(other['textos']['Evaluación'],'Captura en pestaña B')


class CandadosTests(unittest.TestCase):
    def test_espera_del_mismo_documento_es_acotada(self):
        from services.planeacion_estabilidad import candado, GuardadoPendiente
        entered, release = Event(), Event()
        def ocupante():
            with candado('ficticio-ocupado'):
                entered.set()
                release.wait(2)
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(ocupante)
            self.assertTrue(entered.wait(1))
            try:
                with self.assertRaises(GuardadoPendiente):
                    with candado('ficticio-ocupado', espera_maxima=.01):
                        self.fail('No debe obtener el candado ocupado')
                with candado('ficticio-libre', espera_maxima=.01):
                    pass
            finally:
                release.set()
            future.result(1)


class ReintentosTests(unittest.TestCase):
    def test_backoff_limite_y_conservacion_de_captura(self):
        from services.reintentos_edicion import programar
        state={'p_doc':{'texto':'Captura ficticia'},'p_pending':True}
        detalle={'espera':20,'accion':'Reintentar'}
        with patch('services.reintentos_edicion.time.monotonic',return_value=100):
            programar(state,'p',detalle)
            self.assertEqual(state['p_retry_at'],120)
            programar(state,'p',detalle)
            self.assertEqual(state['p_retry_at'],140)
            mensaje=programar(state,'p',detalle)
        self.assertEqual(state['p_retry_at'],float('inf'))
        self.assertIn('pausaron',mensaje['accion'])
        self.assertTrue(state['p_pending'])
        self.assertEqual(state['p_doc']['texto'],'Captura ficticia')

    def test_error_no_transitorio_no_se_reintenta_solo(self):
        from services.reintentos_edicion import programar
        state={}
        programar(state,'p',{'espera':0},fecha='_reintentar_en')
        self.assertEqual(state['p_reintentar_en'],float('inf'))

    def test_pdf_se_genera_al_descargar_con_snapshot_aislado(self):
        from documents.descarga_diferida import preparar
        from unittest.mock import Mock
        datos={'texto':'Versión visible al preparar'}
        generar=Mock(return_value=b'PDF ficticio')
        descarga=preparar(generar,datos)
        generar.assert_not_called()
        datos['texto']='Otra captura posterior'
        self.assertEqual(descarga(),b'PDF ficticio')
        generar.assert_called_once_with({'texto':'Versión visible al preparar'})


class EPPParalelasTests(unittest.TestCase):
    from tests.test_epp import EPPTests as _Fixture
    setUp=_Fixture.setUp
    tearDown=_Fixture.tearDown

    def test_epp_lenta_no_bloquea_informe_de_otro_alumno(self):
        from services import epp
        from services.epp_modelo import vacia
        from tests.test_epp import ALUMNO
        import pandas as pd
        entered,release=Event(),Event()
        with patch.object(epp.planes,'padron_autorizado',return_value=pd.DataFrame([ALUMNO,{**ALUMNO,'ID_Alumno':'FICTICIO-A2'}])):
            a=epp.crear(ALUMNO['ID_Alumno'],'2026-2027')
            b=epp.crear('FICTICIO-A2','2026-2027')
            append=self.sheet.append_rows
            def lento(rows,value_input_option):
                if rows[0][0]==a['alumno']:
                    entered.set();release.wait(3)
                append(rows,value_input_option)
            with patch.object(self.sheet,'append_rows',side_effect=lento),ThreadPoolExecutor(max_workers=2) as pool:
                future=pool.submit(epp.guardar,a,'Aprendizaje',vacia('Aprendizaje'),'')
                self.assertTrue(entered.wait(1))
                try:
                    other=pool.submit(epp.guardar,b,'Aprendizaje',vacia('Aprendizaje'),'').result(timeout=1)
                    self.assertTrue(other['revision'])
                finally:release.set()
                future.result(1)


if __name__ == '__main__':
    unittest.main()

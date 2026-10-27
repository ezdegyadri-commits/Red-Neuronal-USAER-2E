"""Red lenta ficticia, ningún dato ni escritura de producción."""
from concurrent.futures import Future
from copy import deepcopy
from threading import Event
from time import perf_counter
from unittest import TestCase
from unittest.mock import patch
import pandas as pd
from services import planeacion as s, trabajos_documento as jobs
from ui import guardado_asincrono as ui, epp_guardado_asincrono as eppui
from tests.test_planeacion_panel import documento, ACTOR, ALUMNO, PanelTests
from services.epp_modelo import vacia


def estado():
    return {'p_doc':documento(),'p_papel_nonce':'envio-1','escuelas_permitidas':'E1'}


class NoBloqueanteTests(TestCase):
    def test_red_lenta_veinte_clics_un_envio_y_entrada_inmediata(self):
        state=estado();liberar=Event();entrado=Event()
        def guardar(doc,estado):
            entrado.set();liberar.wait(3)
            return {**doc,'revision':'confirmada','guardado_en':'fecha-ficticia'}
        with patch.object(ui.st,'session_state',state),patch.object(s,'identidad',return_value=ACTOR),patch.object(s,'guardar',side_effect=guardar) as write:
            inicio=perf_counter();self.assertFalse(ui.persistir('p'))
            duracion=perf_counter()-inicio
            self.assertLess(duracion,.25);self.assertTrue(entrado.wait(1))
            try:
                for _ in range(20):self.assertFalse(ui.persistir('p'))
                self.assertTrue(state['p_pending']);self.assertNotIn('p_papel_aceptado',state)
                self.assertEqual(write.call_count,1)
            finally:liberar.set()
            state['p_trabajo_io']['future'].result(timeout=2)
            self.assertTrue(ui.persistir('p'));self.assertFalse(state['p_pending'])
            self.assertEqual(state['p_papel_aceptado'],'envio-1')

    def test_acuse_anterior_no_borra_redaccion_posterior(self):
        state=estado();sent=deepcopy(state['p_doc']);saved=deepcopy(sent)
        saved.update(revision='r-nueva',guardado_en='fecha')
        state['p_doc']['textos']['Evaluación']='Texto escrito después del envío'
        future=Future();future.set_result(saved)
        state['p_trabajo_io']={'future':future,'cuenta':ACTOR['cuenta'],'documento':sent['id'],'enviado':sent,'estado':'BORRADOR','nonce':'viejo'}
        with patch.object(ui.st,'session_state',state),patch.object(s,'identidad',return_value=ACTOR):
            self.assertFalse(ui.persistir('p'))
        self.assertEqual(state['p_doc']['revision'],'r-nueva')
        self.assertEqual(state['p_doc']['textos']['Evaluación'],'Texto escrito después del envío')
        self.assertTrue(state['p_pending']);self.assertNotIn('p_papel_aceptado',state)

    def test_fallo_no_confirma_conserva_borrador_y_libera_reintento(self):
        state=estado();future=Future();future.set_exception(ConnectionError('ficticia'))
        state['p_trabajo_io']={'future':future,'cuenta':ACTOR['cuenta'],'documento':state['p_doc']['id']}
        antes=deepcopy(state['p_doc'])
        with patch.object(ui.st,'session_state',state),patch.object(ui.st,'toast') as toast,patch.object(s,'identidad',return_value=ACTOR):
            self.assertFalse(ui.persistir('p'));toast.assert_called_once()
        self.assertEqual(state['p_doc'],antes);self.assertTrue(state['p_pending'])
        self.assertNotIn('p_trabajo_io',state);self.assertNotIn('p_papel_aceptado',state)

    def test_resultado_de_otra_cuenta_no_se_aplica(self):
        state=estado();future=Future();future.set_result(documento())
        state['p_trabajo_io']={'future':future,'cuenta':'otra','documento':state['p_doc']['id']}
        with patch.object(ui.st,'session_state',state),patch.object(s,'identidad',return_value=ACTOR):
            with self.assertRaises(PermissionError):ui.persistir('p')
        self.assertIn('p_trabajo_io',state)

    def test_navegar_transfiere_future_sin_copiarlo_ni_descartar(self):
        from ui.planeacion_pendientes import conservar
        state=estado();state['p_pending']=True;future=Future()
        state['p_trabajo_io']={'future':future,'documento':state['p_doc']['id']}
        with patch.object(ui.st,'session_state',state):destino=conservar('p','base')
        self.assertIs(state[destino+'_trabajo_io']['future'],future)
        self.assertTrue(state[destino+'_pending']);self.assertNotIn('p_trabajo_io',state)

    def test_cola_llena_falla_rapido_sin_crear_trabajo(self):
        with patch.object(jobs._capacidad,'acquire',return_value=False),patch.object(jobs._pool,'submit') as submit:
            from services.planeacion_estabilidad import GuardadoPendiente
            with self.assertRaises(GuardadoPendiente):jobs.enviar(ACTOR,'E1',lambda:None)
            submit.assert_not_called()

    def test_identidad_y_alcance_aislados_del_estado_streamlit(self):
        def leer():return s.identidad()['cuenta'],jobs.contexto()['escuelas']
        f1=jobs.enviar(ACTOR,'E1',leer)
        f2=jobs.enviar({**ACTOR,'cuenta':'especialista-2'},'E2',leer)
        self.assertEqual(f1.result(2),(ACTOR['cuenta'],'E1'))
        self.assertEqual(f2.result(2),('especialista-2','E2'))
        self.assertIsNone(jobs.contexto())

    def test_worker_reconsulta_matricula_no_reutiliza_snapshot_de_ui(self):
        with patch.object(s,'alumnos_visibles',return_value=pd.DataFrame([ALUMNO])) as visibles:
            f=jobs.enviar(ACTOR,'E1',s.padron_autorizado);frame=f.result(2)
        self.assertEqual(frame.iloc[0]['ID_Alumno'],'A1')
        visibles.assert_called_once_with(ACTOR['rol'],'E1',ACTOR['nombre'])


class PersistenciaRealTests(PanelTests):
    def test_usa_guardado_versionado_real_y_un_append(self):
        state=estado()
        with patch.object(ui.st,'session_state',state):
            self.assertFalse(ui.persistir('p'))
            state['p_trabajo_io']['future'].result(timeout=3)
            self.assertTrue(ui.persistir('p'))
        self.assertEqual(len(s.reconstruir(self.sheet.rows)),1)
        self.assertEqual(state['p_doc']['id'],'test')


class EPPTests(TestCase):
    def test_acuse_por_area_preserva_captura_posterior(self):
        value=vacia('Aprendizaje');value['campos']['5.1. Competencia curricular']='Primero'
        doc={'id':'epp-prueba','partes':{'Aprendizaje':{'contenido':value,'revision':'base'}}}
        sent=deepcopy(doc);saved={'contenido':deepcopy(value),'revision':'nueva','fecha':'ficticia'}
        future=Future();future.set_result(({'Aprendizaje':saved},None))
        doc['partes']['Aprendizaje']['contenido']['campos']['5.1. Competencia curricular']='Después'
        state={'p_doc':doc,'p_cola':{'Aprendizaje':{}},'p_trabajo_io':{'future':future,'cuenta':ACTOR['cuenta'],'documento':doc['id'],'enviado':sent,'nonce':'anterior'}}
        with patch.object(eppui.st,'session_state',state),patch.object(eppui.s,'actor',return_value=ACTOR):
            self.assertFalse(eppui.guardar('p'))
        self.assertEqual(doc['partes']['Aprendizaje']['contenido']['campos']['5.1. Competencia curricular'],'Después')
        self.assertEqual(state['p_cola']['Aprendizaje']['revision'],'nueva')
        self.assertTrue(state['p_pending']);self.assertNotIn('p_aceptado',state)

    def test_error_parcial_conserva_solo_areas_pendientes(self):
        sent={'id':'epp-prueba','partes':{'Aprendizaje':{'contenido':vacia('Aprendizaje'),'revision':''},'Conclusión':{'contenido':vacia('Conclusión'),'revision':''}}}
        saved={**sent['partes']['Aprendizaje'],'revision':'guardada'}
        f=Future();f.set_result(({'Aprendizaje':saved},ConnectionError('ficticia')))
        state={'p_doc':deepcopy(sent),'p_cola':{'Aprendizaje':{},'Conclusión':{}},'p_trabajo_io':{'future':f,'cuenta':ACTOR['cuenta'],'documento':sent['id'],'enviado':sent,'nonce':'n'}}
        with patch.object(eppui.st,'session_state',state),patch.object(eppui.st,'toast'),patch.object(eppui.s,'actor',return_value=ACTOR):
            self.assertFalse(eppui.guardar('p'))
        self.assertEqual(set(state['p_cola']),{'Conclusión'});self.assertTrue(state['p_pending'])
        self.assertEqual(state['p_doc']['partes']['Aprendizaje']['revision'],'guardada')


class EPPPersistenciaTests(TestCase):
    from tests.test_epp import EPPTests as _Fixture
    setUp=_Fixture.setUp
    tearDown=_Fixture.tearDown
    doc=_Fixture.doc

    def test_guardado_en_worker_reabre_mismo_informe_y_area(self):
        from services import epp as epp
        doc=self.doc();value=vacia('Aprendizaje')
        value['campos']['5.1. Competencia curricular']='Hallazgo ficticio recuperable'
        doc['partes']['Aprendizaje']={'contenido':value,'revision':''}
        state={'p_doc':doc,'p_cola':{'Aprendizaje':{'base':vacia('Aprendizaje'),'revision':''}},'p_nonce':'envio-ficticio'}
        with patch.object(eppui.st,'session_state',state):
            self.assertFalse(eppui.guardar('p',True))
            state['p_trabajo_io']['future'].result(timeout=3)
            self.assertTrue(eppui.guardar('p'))
        abierta=epp.listar()[0]
        self.assertEqual(abierta['id'],doc['id'])
        self.assertEqual(abierta['partes']['Aprendizaje']['contenido'],value)
        self.assertEqual(len(self.sheet.rows),2)

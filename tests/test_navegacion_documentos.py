from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import patch
import pandas as pd
from streamlit.testing.v1 import AppTest
from services import navegacion_planeaciones as nav,planeacion as s
from tests.test_planeacion_panel import documento,ACTOR,ALUMNO


_flag=patch.dict('os.environ',{'USAER_NAVEGACION_DOCUMENTOS':'1'})


def setUpModule():_flag.start()


def tearDownModule():_flag.stop()


def compartido():
    d=documento();d['cuenta']='otra-apoyo';d['id']='compartido-ficticio'
    d['metadatos'].update(modalidad_planeacion='grupal',vista_formato='guia')
    return d


class IndiceTests(unittest.TestCase):
    def setUp(self):
        self.own=documento();self.own['id']='propio-ficticio'
        self.shared=compartido()
        self.patches=[patch.object(s,'identidad',return_value=ACTOR),patch.object(s,'padron_autorizado',return_value=pd.DataFrame([ALUMNO])),
                      patch.object(s,'listar',return_value=[self.own]),patch.object(s,'compartidos',return_value=[self.shared])]
        for p in self.patches:p.start();self.addCleanup(p.stop)

    def test_propios_y_compartidos_sin_duplicar(self):
        with patch.object(s,'compartidos',return_value=[self.shared,self.own]),patch.object(s,'guardar') as guardar:
            docs=nav.indice()
        self.assertEqual({d['id'] for d in docs},{self.own['id'],self.shared['id']})
        guardar.assert_not_called()

    def test_url_opaca_no_contiene_cuenta_alumno_ni_escuela(self):
        token=nav.enlace_id(self.own['id'])
        self.assertEqual(len(token),64)
        for value in (self.own['id'],ACTOR['cuenta'],ALUMNO['ID_Alumno'],ALUMNO['ID_Escuela']):
            self.assertNotIn(value,token)
        self.assertEqual(nav.resolver(token)['id'],self.own['id'])

    def test_enlace_ajeno_y_token_arbitrario_no_abren_primera_opcion(self):
        for token in ('otro',nav.enlace_id('no-autorizado')):
            with self.assertRaises(PermissionError):nav.resolver(token)

    def test_revalida_permisos_aunque_tarjeta_haya_sido_visible(self):
        with patch.object(s,'autorizar',side_effect=PermissionError('Asignación cambiada')):
            self.assertEqual(nav.indice(),[])
            with self.assertRaises(PermissionError):nav.resolver(nav.enlace_id(self.own['id']))

    def test_contexto_no_depende_de_posicion_ni_modifica_modalidad(self):
        before=deepcopy(self.own)
        ctx=nav.contexto(self.own,ACTOR)
        self.assertEqual(ctx['documento'],self.own['id'])
        self.assertEqual(ctx['alumnos'],('A1',))
        self.assertEqual(self.own,before)
        with patch.object(s,'listar',return_value=[self.shared,self.own]):
            self.assertEqual(nav.resolver(nav.enlace_id(self.own['id']))['id'],self.own['id'])

    def test_filtros_opcionales_y_estados_no_cambian_documentos(self):
        docs=[self.own,self.shared];before=deepcopy(docs)
        self.assertEqual(len(nav.filtrar(docs,ACTOR['cuenta'])),2)
        self.assertEqual(nav.filtrar(docs,ACTOR['cuenta'],vista='Propias'),[self.own])
        self.assertEqual(nav.filtrar(docs,ACTOR['cuenta'],vista='Compartidas'),[self.shared])
        self.assertEqual(nav.filtrar(docs,ACTOR['cuenta'],vista='Pendientes',pendientes=[self.own['id']]),[self.own])
        self.assertEqual(nav.filtrar(docs,ACTOR['cuenta'],escuela='OTRA'),[])
        self.assertEqual(docs,before)

    def test_borrador_local_pendiente_autorizado_es_visible_y_recuperable(self):
        local=deepcopy(self.own);local['id']='pendiente-no-enviado';local['textos']['Evaluación']='Captura local'
        self.assertIn(local['id'],{d['id'] for d in nav.indice([local])})
        self.assertEqual(nav.resolver(nav.enlace_id(local['id']),[local])['textos']['Evaluación'],'Captura local')

    def test_vista_director_no_ofrece_edicion_ni_modifica_contrato(self):
        cell={'editable':True,'target':('texto','Evaluación'),'value':'Trabajo registrado'}
        spec={'cells':{'c1':cell},'tables':[{'rows':[[deepcopy(cell)]],'add':True,'delete':True}],'textos':[deepcopy(cell)]}
        view=nav.solo_lectura(spec)
        self.assertTrue(view['solo_lectura'])
        self.assertFalse(view['cells']['c1']['editable'])
        self.assertFalse(view['tables'][0]['rows'][0][0]['editable'])
        self.assertFalse(view['textos'][0]['editable'])
        self.assertFalse(view['tables'][0]['add'])
        self.assertTrue(spec['cells']['c1']['editable'])

    def test_guia_con_cuenta_reutilizada_abre_aporte_no_editor_de_apoyo(self):
        doc=compartido();doc['cuenta']=ACTOR['cuenta']
        self.assertEqual(nav.ruta(doc,{**ACTOR,'area':'Comunicación'}),'compartido')

    def test_modalidad_y_ruta_se_derivan_del_documento_no_del_filtro(self):
        self.assertEqual(nav.ruta(self.own,ACTOR),'propio')
        self.assertEqual(nav.ruta(self.shared,ACTOR),'compartido')
        self.assertEqual(nav.ruta(self.shared,{**ACTOR,'director':True}),'lectura')


class ListaUITests(unittest.TestCase):
    def app(self):
        return AppTest.from_file(str(Path(__file__).parent/'fixtures/mis_planeaciones_app.py'),default_timeout=30).run()

    def abrir(self,app,n):
        next(b for b in app.button if b.label.startswith('ALUMNO FICTICIO '+str(n))).click().run()
        self.assertFalse(app.exception)

    def test_un_clic_desde_lista_llega_al_editor_identificado(self):
        app=self.app();self.assertFalse(app.exception)
        self.assertTrue(any(h.value=='Mis planeaciones' for h in app.subheader))
        self.assertFalse(app.selectbox)
        self.abrir(app,1)
        self.assertTrue(any('EDITOR ficticio-1' in x.value for x in app.markdown))
        self.assertEqual(app.session_state['planeacion_qa_documento_contexto']['documento'],'ficticio-1')
        self.assertEqual(len(app.query_params['plan']),64)

    def test_inicio_abre_editor_en_una_seleccion(self):
        app=self.app();app.session_state['qa_inicio']=True;app.run()
        self.abrir(app,1)
        self.assertEqual(app.session_state['navegacion_principal'],'Planeación e intervención')
        self.assertTrue(any('EDITOR ficticio-1' in x.value for x in app.markdown))

    def test_compartido_abre_editor_sin_escuela_formato_grupo_ni_otro_boton(self):
        app=self.app();app.session_state['qa_especialista']=True;app.run()
        next(b for b in app.button if 'Compartida' in b.label and b.key.endswith('_abrir')).click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any('EDITOR COMPARTIDO ficticio-2' in x.value for x in app.markdown))
        self.assertFalse(any(x.label in ('Escuela del trabajo compartido','Documento compartido · grado y periodo','Grado y grupo') for x in app.selectbox))

    def test_pi_compartido_abre_tabla_real_sin_selectores_previos(self):
        app=self.app();app.session_state['qa_especialista']=True;app.session_state['qa_pi']=True;app.run()
        next(b for b in app.button if 'Compartida' in b.label and b.key.endswith('_abrir')).click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any(t.label=='Observaciones de mi área' for t in app.text_area))
        self.assertFalse(app.selectbox)

    def test_cambiar_documento_conserva_captura_pendiente(self):
        app=self.app();self.abrir(app,0)
        next(b for b in app.button if b.label=='Añadir texto ficticio pendiente').click().run()
        next(b for b in app.button if b.label=='← Mis planeaciones').click().run()
        self.assertFalse(app.exception)
        self.abrir(app,1)
        pendientes=[v for k,v in app.session_state._state.filtered_state.items() if k.endswith('_doc') and isinstance(v,dict) and v.get('id')=='ficticio-0']
        self.assertTrue(any(d['textos']['Evaluación']=='TEXTO PENDIENTE PROTEGIDO' for d in pendientes))

    def test_recarga_con_enlace_restablece_id_no_posicion(self):
        app=self.app();self.abrir(app,1)
        token=app.query_params['plan']
        fresh=AppTest.from_file(str(Path(__file__).parent/'fixtures/mis_planeaciones_app.py'),default_timeout=30)
        fresh.query_params['plan']=token;fresh.run()
        self.assertFalse(fresh.exception)
        self.assertEqual(fresh.session_state['planeacion_qa_documento_contexto']['documento'],'ficticio-1')

    def test_enlace_anterior_se_convierte_sin_cambiar_documento(self):
        app=AppTest.from_file(str(Path(__file__).parent/'fixtures/mis_planeaciones_app.py'),default_timeout=30)
        app.query_params['doc_id']='ficticio-1';app.run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['planeacion_qa_documento_contexto']['documento'],'ficticio-1')
        self.assertNotIn('doc_id',app.query_params)
        self.assertEqual(len(app.query_params['plan']),64)

    def test_buscar_filtra_sin_solicitar_selecciones_previas(self):
        app=self.app()
        next(x for x in app.text_input if x.label=='Buscar planeación').set_value('FICTICIO 1').run()
        self.assertFalse(app.exception)
        rows=[b for b in app.button if b.key.endswith('_abrir')]
        self.assertEqual(len(rows),1);self.assertTrue(rows[0].label.startswith('ALUMNO FICTICIO 1'))

    def test_eliminar_exige_dos_acciones_y_no_toca_los_demas(self):
        app=self.app()
        next(b for b in app.button if b.label=='Eliminar borrador').click().run()
        self.assertNotIn('qa_eliminados',app.session_state)
        next(b for b in app.button if b.label=='Confirmar eliminación').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['qa_eliminados'],['ficticio-1'])
        rows=[b for b in app.button if b.key.endswith('_abrir')]
        self.assertEqual(len(rows),2)
        self.assertTrue(any('ALUMNO FICTICIO 0' in b.label for b in rows))

    def test_enlace_denegado_regresa_a_lista_sin_abrir_otro(self):
        app=AppTest.from_file(str(Path(__file__).parent/'fixtures/mis_planeaciones_app.py'),default_timeout=30)
        app.query_params['plan']=nav.enlace_id('otra-cuenta-no-autorizada');app.run()
        self.assertFalse(app.exception)
        self.assertTrue(any('no está disponible' in w.value for w in app.warning))
        self.assertFalse(any('EDITOR ' in x.value for x in app.markdown))
        self.assertNotIn('planeacion_qa_documento_contexto',app.session_state)


class CreacionRealUITests(unittest.TestCase):
    from tests.test_planeacion_simple import RecorridoTests as _Anterior
    setUp=_Anterior.setUp
    tearDown=_Anterior.tearDown

    def test_creacion_abre_editor_real_y_regresa_a_lista(self):
        app=AppTest.from_file(str(Path(__file__).with_name('fixture_planeacion_viva.py')),default_timeout=30).run()
        self.assertFalse(app.exception)
        next(b for b in app.button if b.label=='＋ Nueva planeación').click().run()
        self.assertFalse(app.exception)
        self.assertFalse(any(w.label in ('Escuela asignada','Grado') for w in app.selectbox))
        next(b for b in app.button if b.label=='Abrir formato con mis alumnos').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len({d['id'] for d in app.session_state['versiones_ficticias']}),1)
        self.assertTrue(any(b.label=='← Mis planeaciones' for b in app.button))
        next(b for b in app.button if b.label=='← Mis planeaciones').click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any(h.value=='Mis planeaciones' for h in app.subheader))
        self.assertFalse(any(b.label=='Abrir formato con mis alumnos' for b in app.button))


class SeleccionTests(unittest.TestCase):
    def test_unica_opcion_contextual_no_crea_selector(self):
        from ui import seleccion_contextual as ui
        with patch.object(ui.st,'session_state',{}),patch.object(ui.st,'caption'),patch.object(ui.st,'selectbox') as select:
            self.assertEqual(ui.elegir('Escuela',['E1'],key='escuela'),'E1')
            select.assert_not_called()

    def test_opciones_multiples_conservan_decision_del_usuario(self):
        from ui import seleccion_contextual as ui
        with patch.object(ui.st,'selectbox',return_value='E2') as select:
            self.assertEqual(ui.elegir('Escuela',['E1','E2'],key='escuela'),'E2')
            select.assert_called_once()

    def test_filtros_recuerdan_preferencia_fuera_del_widget(self):
        from ui import mis_planeaciones as ui
        state={'f_preferencia':'E2'}
        with patch.object(ui.st,'session_state',state),patch.object(ui.st,'selectbox',return_value='E2'):
            self.assertEqual(ui._filtro('Escuela',{'E1':'Uno','E2':'Dos'},'f'),'E2')
            state.pop('f')  # Streamlit desmonta los widgets al cerrar el expansor.
            self.assertEqual(ui._filtro('Escuela',{'E1':'Uno','E2':'Dos'},'f'),'E2')
            self.assertEqual(state['f'],'E2')

    def test_reversion_sin_modificar_datos(self):
        with patch.dict('os.environ',{'USAER_NAVEGACION_DOCUMENTOS':'0'}):self.assertFalse(nav.habilitada())
        with patch.dict('os.environ',{'USAER_NAVEGACION_DOCUMENTOS':'1'}):self.assertTrue(nav.habilitada())


class ActualizacionTests(unittest.TestCase):
    def test_actualiza_una_vez_y_no_vacia_estado(self):
        from types import SimpleNamespace
        from ui import navegacion_actualizacion as ui
        entradas={n:SimpleNamespace(NAV_VERSION='anterior') for n in ui._ENTRADAS}
        def recargar(module):module.NAV_VERSION=ui.VERSION;return module
        with patch.dict(ui.sys.modules,entradas),patch.object(ui.importlib,'reload',side_effect=recargar) as reload:
            ui.preparar_entrada();cantidad=reload.call_count
            self.assertGreater(cantidad,0)
            ui.preparar_entrada();self.assertEqual(reload.call_count,cantidad)

    def test_desactivada_no_recarga_interfaces(self):
        from ui import navegacion_actualizacion as ui
        with patch.dict('os.environ',{'USAER_NAVEGACION_DOCUMENTOS':'0'}),patch.object(ui.importlib,'reload') as reload:
            ui.preparar_entrada();reload.assert_not_called()


if __name__=='__main__':unittest.main()

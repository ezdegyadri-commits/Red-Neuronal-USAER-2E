"""Acceso compartido y confirmaciones de guardado; solo datos ficticios."""
from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch
import pandas as pd
from tests.test_planeacion_panel import documento, ACTOR, ALUMNO
from services import planeacion as s
from services.planeacion_colaboracion import compartible, clave_guia


def grupal():
    d=documento()
    d['metadatos'].update(modalidad_planeacion='grupal',vista_formato='guia')
    return d


class AccesoTests(TestCase):
    def test_letra_pendiente_visible_sin_enlazar_otro_grupo(self):
        d=grupal();d['datos']['Alumnos'][0]['Grupo']=''
        anterior=deepcopy(d)
        self.assertTrue(compartible(d))
        self.assertIsNone(clave_guia(d))
        self.assertEqual(d,anterior)

    def test_no_comparte_modalidad_individual_eliminados_o_grupos_distintos(self):
        d=grupal();d['metadatos']['modalidad_planeacion']='individual'
        self.assertFalse(compartible(d))
        d=grupal();d['metadatos']['borrador_eliminado']=True
        self.assertFalse(compartible(d))
        d=grupal();d['datos']['Alumnos'].append({**d['datos']['Alumnos'][0],'ID_Alumno':'A2','Grupo':'C'})
        self.assertFalse(compartible(d))

    def test_solo_documentos_autorizados_no_solo_los_de_mi_cuenta(self):
        d=grupal();d['revision']='r1';d['cuenta']='apoyo'
        ajeno=deepcopy(d);ajeno['id']='otra-escuela';ajeno['datos']['ID_Escuela']='OTRA'
        ajeno['datos']['Alumnos'][0]['ID_Alumno']='NO_AUTORIZADO'
        for area in ('Psicología','Comunicación','Trabajo Social'):
            with self.subTest(area=area),patch.object(s,'identidad',return_value={**ACTOR,'cuenta':'especialista','area':area}),patch.object(s,'padron_autorizado',return_value=pd.DataFrame([ALUMNO])),patch.object(s,'versiones_actuales',return_value=[d,ajeno]):
                self.assertEqual([v['id'] for v in s.compartidos()],['test'])

    def test_entrada_directa_equipo_para_todas_las_areas(self):
        from ui import planeacion_viva as ui, planeacion as u, planeacion_colaboracion as equipo
        for area in ('Psicología','Comunicación','Trabajo Social'):
            with self.subTest(area=area),patch.object(ui,'st') as st,patch.object(s,'identidad',return_value={**ACTOR,'area':area}),patch.object(u,'_prefix',return_value='p'),patch.object(ui,'_entrada') as entrada,patch.object(equipo,'panel') as panel:
                st.session_state={}
                st.radio.side_effect=lambda label,options,**kwargs:options[0]
                ui.pagina()
                panel.assert_called_once_with('p_colaboracion')
                entrada.assert_called_once()
                st.tabs.assert_called_once_with(['Planeación del Equipo de Paradocentes','Planeaciones grupales del equipo'])

    def test_formato_propio_y_equipo_disponibles_en_pestanas_del_rol(self):
        from ui import planeacion_viva as ui, planeacion as u, planeacion_colaboracion as equipo
        with patch.object(ui,'st') as st,patch.object(s,'identidad',return_value={**ACTOR,'area':'Comunicación'}),patch.object(u,'_prefix',return_value='p'),patch.object(ui,'_entrada') as entrada,patch.object(equipo,'panel') as panel:
            st.session_state={};st.radio.return_value='Mi formato de especialista'
            ui.pagina()
            entrada.assert_called_once();panel.assert_called_once_with('p_colaboracion')

    def test_no_confirma_el_respaldo_del_editor_antes_de_persistir(self):
        from ui import planeacion_colaboracion as ui
        state={'p_doc':grupal(),'p_filas':[],'p_nonce':'n1','p_pending':True}
        with patch.object(ui.st,'session_state',state),patch.object(s,'guardar_aportacion',side_effect=RuntimeError('fallo ficticio')):
            ui._guardar('p')
        self.assertTrue(state['p_pending']);self.assertNotIn('p_ack',state)
        with patch.object(ui.st,'session_state',state),patch.object(s,'guardar_aportacion',return_value=grupal()):
            ui._guardar('p')
        self.assertFalse(state['p_pending']);self.assertEqual(state['p_ack'],'n1')

    def test_throttle_no_confirma_evento_nuevo(self):
        from ui import planeacion_colaboracion as ui
        state={'p_doc':grupal(),'p_filas':[],'p_nonce':'nuevo','p_ack':'anterior','p_intento':100}
        with patch.object(ui.st,'session_state',state),patch.object(ui.time,'monotonic',return_value=110),patch.object(s,'guardar_aportacion') as save:
            ui._guardar('p',automatic=True)
        save.assert_not_called();self.assertEqual(state['p_ack'],'anterior');self.assertTrue(state['p_pending'])


class RecorridoCompartidoTests(TestCase):
    def setUp(self):
        self.originales={k:getattr(s,k) for k in ('identidad','autorizar','compartidos','padron_autorizado','listar','refrescar','guardar_aportacion')}

    def tearDown(self):
        for k,v in self.originales.items():setattr(s,k,v)

    def test_dos_sesiones_fijan_documento_y_ven_apoyo_sin_moverse(self):
        from pathlib import Path
        from streamlit.testing.v1 import AppTest
        import streamlit as st
        from ui import planeacion_papel as ui
        def editor(**kwargs):
            st.session_state['qa_spec']=kwargs['hoja']
            return None
        with patch.object(ui,'editor',side_effect=editor):
            apps=[AppTest.from_file(str(Path(__file__).with_name('fixture_acceso_equipo.py')),default_timeout=30).run() for _ in range(2)]
            uno=grupal();uno['id']='segundo';uno['datos']['Alumnos'][0]['Grado']='2°'
            otro=deepcopy(uno);otro['id']='tercero';otro['datos']['Alumnos'][0]['Grado']='3°'
            for i,app in enumerate(apps):
                app.session_state['f_docs']=[deepcopy(uno),deepcopy(otro)]
                app.run()
                selector=next(w for w in app.selectbox if w.label.startswith('Documento compartido'))
                selector.set_value('segundo' if i==0 else 'tercero').run()
                next(w for w in app.button if w.label=='Abrir Anexo XIX compartido').click().run()
            # Otro integrante guarda 3°; cambia el orden de la lista y actualiza
            # apoyo en 2°. Ninguna sesión debe cambiar el documento seleccionado.
            uno['metadatos']['guia_grupal_manual']={'filas':[{'ID_Alumno':'A1','Aprendizaje':'Nuevo aporte de apoyo'}]}
            otro['guardado_en']='2099-01-01'
            for i,app in enumerate(apps):
                app.session_state['f_docs']=[deepcopy(otro),deepcopy(uno)]
                app.run();self.assertFalse(app.exception)
                self.assertEqual(app.session_state['qa_spec']['documento'],'segundo' if i==0 else 'tercero')
                self.assertFalse(any(w.label=='Grado y grupo' for w in app.selectbox))
            self.assertIn('Nuevo aporte de apoyo',str(apps[0].session_state['qa_spec']['tables']))

    def test_formato_visible_edicion_fallo_y_recuperacion_sin_copia(self):
        from pathlib import Path
        from streamlit.testing.v1 import AppTest
        import streamlit as st
        from ui import planeacion_papel as ui
        nombres=('identidad','autorizar','compartidos','padron_autorizado','listar','refrescar','guardar_aportacion')
        originales={k:getattr(s,k) for k in nombres}
        def editor(**kwargs):
            st.session_state['qa_spec']=kwargs['hoja']
            return st.session_state.pop('qa_event',None)
        try:
            with patch.object(ui,'editor',side_effect=editor):
                app=AppTest.from_file(str(Path(__file__).with_name('fixture_acceso_equipo.py')),default_timeout=30).run()
                self.assertFalse(app.exception)
                self.assertEqual([t.label for t in app.tabs],['Planeación del Equipo de Paradocentes','Planeaciones grupales del equipo'])
                self.assertTrue(any(w.label=='Grado y grupo' for w in app.selectbox))
                next(w for w in app.button if w.label=='Abrir Anexo XIX compartido').click().run()
                spec=app.session_state['qa_spec']
                self.assertEqual({c['label'] for c in spec['cells'].values() if c['editable']},{'Comunicación','Observaciones de mi área'})
                celda=next(k for k,c in spec['cells'].items() if c['editable'])
                next(w for w in app.checkbox if w.label=='Simular fallo de guardado').check().run()
                app.session_state['qa_event']={'documento':spec['documento'],'huella':spec['huella'],'nonce':'evento-ficticio','accion':'inicio','cambios':{celda:'Juego de turnos con apoyos visuales.'}}
                app.run();self.assertFalse(app.exception)
                base=next(k[:-8] for k in app.session_state.keys() if k.endswith('_pending'))
                self.assertTrue(app.session_state[base+'_pending'])
                self.assertTrue(any(k.endswith('_abierto') for k in app.session_state.keys()))
                self.assertNotIn(base+'_ack',app.session_state)
                next(w for w in app.checkbox if w.label=='Simular fallo de guardado').uncheck().run()
                actual=app.session_state['qa_spec']
                app.session_state['qa_event']={'documento':actual['documento'],'huella':actual['huella'],'nonce':'reintento-manual','accion':'guardar','cambios':{}}
                app.run()
                self.assertFalse(app.exception)
                self.assertFalse(app.session_state[base+'_pending'])
                self.assertEqual(app.session_state[base+'_ack'],'reintento-manual')
                docs=app.session_state['f_docs'];self.assertEqual(len(docs),1)
                self.assertEqual(docs[0]['id'],'test')
                self.assertIn('Juego de turnos',str(docs[0]['metadatos']['aportaciones_equipo']['Comunicación']))
                actual=app.session_state['qa_spec']
                app.session_state['qa_event']={'documento':actual['documento'],'huella':actual['huella'],'nonce':'salida-confirmada','accion':'inicio','cambios':{}}
                app.run();self.assertFalse(app.exception)
                self.assertFalse(any(k.endswith('_abierto') for k in app.session_state.keys()))
                self.assertTrue(any(w.label=='Grado y grupo' for w in app.selectbox))
        finally:
            for k,v in originales.items():setattr(s,k,v)

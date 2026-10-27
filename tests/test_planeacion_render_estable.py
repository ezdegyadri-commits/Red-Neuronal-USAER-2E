"""Autoguardado previo al render: datos ficticios, sin red ni escrituras reales."""
from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch,Mock
from services import planeacion as s,planeacion_papel as papel
from tests.test_planeacion_compartida import grupal,ACTOR
from ui import planeacion_papel as ui,planeacion_anexo_compartido as equipo


class RenderEstableTests(TestCase):
    def test_transporte_real_ejecuta_callback_antes_del_unico_render(self):
        import json
        from streamlit.testing.v1 import AppTest
        from streamlit.proto.WidgetStates_pb2 import WidgetStates
        app=AppTest.from_string('''
import streamlit as st
from ui.planeacion_papel import editor
st.session_state['renders']=st.session_state.get('renders',0)+1
def recibir(event):
    st.session_state['recibidos']=st.session_state.get('recibidos',0)+1
    st.session_state['ack']=event['nonce']
editor(key='editor_prueba',hoja={'documento':'ficticio'},on_edicion=recibir,
       aceptado_nonce=st.session_state.get('ack',''))
''',default_timeout=30).run()
        self.assertFalse(app.exception)
        component=app.get('bidi_component')[0]
        states=WidgetStates()
        states.widgets.add(id=component.proto.id,json_value=json.dumps({'evento':{'accion':'autoguardar','nonce':'uno'}}))
        app._run(states)
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['renders'],2)
        self.assertEqual(app.session_state['recibidos'],1)
        data=json.loads(app.get('bidi_component')[0].proto.json)
        self.assertEqual(data['aceptado_nonce'],'uno')

    def evento(self,doc,collaborativa=False):
        spec=papel.hoja(doc,colaborativa=collaborativa)
        target=('aporte',0,'Comunicación') if collaborativa else ('guia',0,'Aprendizaje')
        key=next(k for k,c in spec['cells'].items() if c['target']==target)
        return dict(documento=doc['id'],huella=spec['huella'],nonce='envio-1',accion='autoguardar',cambios={key:'Actividad ficticia'})

    def test_callback_solo_recibe_escrituras_y_no_recarga(self):
        callback=Mock();event={'accion':'autoguardar','nonce':'uno'}
        with patch.object(ui.st,'session_state',{'k':{'evento':event}}),patch.object(ui.st,'rerun') as rerun:
            ui._evento_editor('k',callback);callback.assert_called_once_with(event)
            event['accion']='inicio';ui._evento_editor('k',callback)
            self.assertEqual(callback.call_count,1);rerun.assert_not_called()

    def test_autor_guarda_una_vez_y_confirma_sin_segunda_recarga(self):
        from ui import planeacion as u
        doc=grupal();state={'p_doc':doc}
        def guardar(prefix,**kwargs):
            state['p_pending']=False;return True
        with patch.object(s,'autorizar',return_value=ACTOR),patch.object(ui.st,'session_state',state),patch.object(u.st,'session_state',state),patch.object(u,'_persist',side_effect=guardar) as persist,patch.object(ui.st,'rerun') as rerun:
            event=self.evento(doc)
            ui.recibir_edicion('p',event);ui.recibir_edicion('p',event)
            persist.assert_called_once();rerun.assert_not_called()
        self.assertEqual(state['p_papel_aceptado'],event['nonce'])
        self.assertIn('Actividad ficticia',str(state['p_doc']))

    def test_especialista_fallo_no_confirma_y_conserva_filas(self):
        actor={**ACTOR,'area':'Comunicación','cuenta':'com-ficticio'}
        doc=grupal();state={'p_doc':doc,'p_filas':[],'p_obs':''}
        from ui import planeacion_colaboracion as guardado
        with patch.object(s,'identidad',return_value=actor),patch.object(s,'autorizar',return_value=actor),patch.object(equipo.st,'session_state',state),patch.object(s,'guardar_aportacion',side_effect=RuntimeError('Sin red ficticia')),patch.object(equipo.st,'rerun') as rerun:
            event=self.evento(equipo._preview('p',actor),True)
            equipo.recibir_edicion('p',event);future=state['p_trabajo_io']['future']
            equipo.recibir_edicion('p',event)
            with self.assertRaises(RuntimeError):future.result(timeout=2)
            from ui.guardado_asincrono import persistir
            if 'p_trabajo_io' in state:persistir('p',aporte=True)
            rerun.assert_not_called()
        self.assertTrue(state['p_pending']);self.assertNotIn('p_ack',state)
        self.assertEqual(state['p_filas'][0]['Texto en formato'],'Actividad ficticia')

    def test_especialista_confirma_solo_guardado_persistido(self):
        actor={**ACTOR,'area':'Comunicación','cuenta':'com-ficticio'}
        doc=grupal();state={'p_doc':doc,'p_filas':[],'p_obs':''}
        with patch.object(s,'identidad',return_value=actor),patch.object(s,'autorizar',return_value=actor),patch.object(equipo.st,'session_state',state),patch.object(s,'guardar_aportacion',return_value=deepcopy(doc)) as write,patch.object(equipo.st,'rerun') as rerun:
            event=self.evento(equipo._preview('p',actor),True);event['accion']='guardar'
            equipo.recibir_edicion('p',event);future=state['p_trabajo_io']['future']
            equipo.recibir_edicion('p',event)
            future.result(timeout=2)
            from ui.guardado_asincrono import persistir
            if 'p_trabajo_io' in state:persistir('p',aporte=True)
            write.assert_called_once();rerun.assert_not_called()
        self.assertEqual(state['p_ack'],event['nonce']);self.assertFalse(state['p_pending'])

    def test_consulta_equipo_acotada_no_se_repite_por_cada_campo(self):
        doc=grupal();state={}
        with patch.object(ui.st,'session_state',state),patch.object(ui.time,'monotonic',side_effect=[100,101,109,110]),patch.object(s,'compartidos',return_value=[doc]) as consulta:
            self.assertEqual(ui.lectura_equipo('p',doc['id']),doc)
            self.assertIsNone(ui.lectura_equipo('p',doc['id']))
            self.assertIsNone(ui.lectura_equipo('p',doc['id']))
            self.assertEqual(ui.lectura_equipo('p',doc['id']),doc)
            self.assertEqual(consulta.call_count,2)

    def test_evento_invalido_no_guarda_ni_pierde_documento(self):
        from ui import planeacion as u
        doc=grupal();state={'p_doc':doc}
        with patch.object(s,'autorizar',return_value=ACTOR),patch.object(ui.st,'session_state',state),patch.object(u,'_persist') as write:
            ui.recibir_edicion('p',dict(documento='ajeno',huella='vieja',nonce='malo',accion='guardar',cambios={}))
            write.assert_not_called()
        self.assertEqual(state['p_doc'],doc);self.assertEqual(state['p_papel_rechazado'],'malo')

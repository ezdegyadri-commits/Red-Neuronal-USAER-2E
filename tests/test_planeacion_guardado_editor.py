"""Regresiones del intercambio navegador/guardado: datos exclusivamente ficticios."""
from pathlib import Path
import shutil
import subprocess
import unittest
from unittest.mock import patch


class ClienteTests(unittest.TestCase):
    def test_carga_acuses_reintentos_y_respaldo(self):
        node=shutil.which('node')
        if not node:self.skipTest('Node no está instalado para ejecutar el contrato del cliente.')
        result=subprocess.run([node,str(Path(__file__).with_name('planeacion_editor_cliente.cjs'))],
                              capture_output=True,text=True,encoding='utf-8',timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)


class ReciboTests(unittest.TestCase):
    def test_persistencia_fallida_conserva_texto_y_pendiente(self):
        from ui import planeacion as u
        from tests.test_planeacion_panel import documento
        doc=documento();doc['textos']['Evaluación']='Texto ficticio sin perder'
        state={'p_doc':doc}
        with patch.object(u.st,'session_state',state),patch.object(u.servicio,'guardar',side_effect=RuntimeError('Sin conexión')):
            self.assertFalse(u._persist('p'))
        self.assertTrue(state['p_pending'])
        self.assertEqual(state['p_doc']['textos']['Evaluación'],'Texto ficticio sin perder')

    def test_confirmacion_limpia_pendiente_no_solo_el_mensaje(self):
        from ui import planeacion as u
        from tests.test_planeacion_panel import documento
        doc=documento();saved={**doc,'guardado_en':'2026-10-15T20:00:00Z','revision':'confirmada'}
        state={'p_doc':doc,'p_pending':True,'p_error':'Sin conexión'}
        with patch.object(u.st,'session_state',state),patch.object(u.servicio,'guardar',return_value=saved):
            self.assertTrue(u._persist('p'))
        self.assertFalse(state['p_pending']);self.assertNotIn('p_error',state)
        self.assertEqual(state['p_doc']['revision'],'confirmada')

    def test_cierre_espera_confirmacion_y_no_pierde_sesion(self):
        import hashlib
        from ui import auth,planeacion as u
        base='planeacion_'+hashlib.sha256(b'ficticio').hexdigest()[:12]+'_individual'
        state={'usuario':'ficticio','autenticado':True,base+'_pending':True}
        def boton(label,**kw):return label=='Guardar cambios y cerrar sesión'
        with patch.object(auth.st,'session_state',state),patch.object(auth.st,'info'),patch.object(auth.st,'warning'),patch.object(auth.st,'checkbox',return_value=False),patch.object(auth.st,'button',side_effect=boton),patch.object(auth,'_cerrar') as cerrar:
            with patch.object(u,'_guardar_edicion_pendiente',return_value=False):auth.logout()
            cerrar.assert_not_called();self.assertTrue(state['autenticado'])
            with patch.object(u,'_guardar_edicion_pendiente',return_value=True):auth.logout()
            cerrar.assert_called_once()


class IntercambioTests(unittest.TestCase):
    def test_acuse_del_mismo_envio_permanece_y_no_duplica_version(self):
        import streamlit as st
        from ui import planeacion_papel as ui
        from tests.test_planeacion_papel import PapelUITests
        calls=[]
        def editor(**kwargs):
            calls.append(kwargs)
            return st.session_state.get('evento_editor_prueba')
        with patch.object(ui,'editor',side_effect=editor):
            app=PapelUITests().abrir('Trabajo Social');doc=app.session_state.versiones_ficticias[-1]
            from services.planeacion_papel import huella
            app.session_state.evento_editor_prueba={'nonce':'envio-ficticio-1','documento':doc['id'],
                'huella':huella(doc),'cambios':{},'accion':'agregar','tabla':'dosificacion'}
            app.run();self.assertFalse(app.exception)
            self.assertEqual(calls[-1]['aceptado_nonce'],'envio-ficticio-1')
            self.assertTrue(calls[-1]['aceptado']) # Compatibilidad con pestañas previas.
            total=len(app.session_state.versiones_ficticias)
            app.run();self.assertFalse(app.exception)
            self.assertEqual(calls[-1]['aceptado_nonce'],'envio-ficticio-1')
            self.assertFalse(calls[-1]['aceptado'])
            self.assertEqual(len(app.session_state.versiones_ficticias),total)

    def test_rechazo_envia_error_al_editor_sin_crear_version(self):
        import streamlit as st
        from ui import planeacion_papel as ui
        from tests.test_planeacion_papel import PapelUITests
        calls=[]
        def editor(**kwargs):
            calls.append(kwargs)
            return st.session_state.get('evento_editor_prueba')
        with patch.object(ui,'editor',side_effect=editor):
            app=PapelUITests().abrir('Trabajo Social');doc=app.session_state.versiones_ficticias[-1]
            total=len(app.session_state.versiones_ficticias)
            app.session_state.evento_editor_prueba={'nonce':'rechazo-ficticio','documento':doc['id'],
                'huella':'revision-obsoleta','cambios':{},'accion':'guardar'}
            app.run();self.assertFalse(app.exception)
            self.assertEqual(calls[-1]['rechazado'],'rechazo-ficticio')
            self.assertTrue(calls[-1]['error'])
            self.assertEqual(len(app.session_state.versiones_ficticias),total)

"""Pruebas del rediseño global de navegación estilo Google Drive / Docs para USAER 2E."""
from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch, MagicMock
from streamlit.testing.v1 import AppTest
from services import planeacion as s
from ui import planeacion_repositorio as repo_ui
from ui import planeacion_colaboracion as colab_ui
from tests.test_planeacion_heredada import ejemplo
from tests.test_planeacion_panel import ACTOR
import pandas as pd


class NavegacionDriveTests(TestCase):
    def test_listado_reune_propias_y_compartidas_del_equipo(self):
        propia = ejemplo()
        propia['id'] = 'propia-1'
        propia['cuenta'] = ACTOR['cuenta']
        propia['metadatos']['modalidad_planeacion'] = 'individual'

        compartida = deepcopy(propia)
        compartida['id'] = 'compartida-equipo-1'
        compartida['cuenta'] = 'otra_cuenta_maestra_apoyo'
        compartida['metadatos']['modalidad_planeacion'] = 'grupal'

        with patch.object(s, 'identidad', return_value=ACTOR), \
             patch.object(s, 'listar', return_value=[propia]), \
             patch.object(s, 'compartidos', return_value=[compartida]):
            docs = repo_ui.listado.__wrapped__('base_test', lambda *a: None)
            ids = [d['id'] for d in docs]
            self.assertIn('propia-1', ids)
            self.assertIn('compartida-equipo-1', ids)
            doc_comp = next(d for d in docs if d['id'] == 'compartida-equipo-1')
            self.assertTrue(doc_comp['metadatos'].get('es_compartida_equipo'))

    def test_apertura_directa_con_identificador_y_query_param(self):
        doc = ejemplo()
        doc['id'] = 'doc-seleccionado-directo'
        doc['metadatos']['modalidad_planeacion'] = 'individual'

        app = AppTest.from_string('''
import streamlit as st
from ui.planeacion_repositorio import panel
from tests.test_planeacion_heredada import ejemplo
d = ejemplo()
d['id'] = 'doc-seleccionado-directo'
d['metadatos']['modalidad_planeacion'] = 'individual'
def abrir(base, target):
    st.session_state['abierto_id'] = target['id']
panel('p', [d], abrir)
''').run()
        self.assertFalse(app.exception)
        btn = next(b for b in app.button if b.label == 'Continuar esta planeación')
        btn.click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['abierto_id'], 'doc-seleccionado-directo')
        qp = app.query_params['doc_id']
        val = qp[0] if isinstance(qp, list) else qp
        self.assertEqual(val, 'doc-seleccionado-directo')

    def test_cero_selectores_redundantes_cuando_solo_hay_una_opcion_en_colaboracion(self):
        doc = ejemplo()
        doc['id'] = 'doc-unico-xix'
        doc['datos']['ID_Escuela'] = 'ESC_01'
        doc['metadatos']['modalidad_planeacion'] = 'grupal'
        doc['metadatos']['guia_grupal_manual'] = {'filas': []}
        doc['formato'] = 'XXIII'

        padron = pd.DataFrame([{
            'ID_Alumno': 'A1',
            'Nombre_Completo': 'ALUMNO ÚNICO',
            'Nombre del alumno': 'ALUMNO ÚNICO',
            'ID_Escuela': 'ESC_01',
            'Nombre_Escuela': 'PRIMARIA BENITO JUÁREZ',
            'Grado': '1o.',
            'Grupo': 'A',
            'Estatus': 'ACTIVO'
        }])

        with patch.object(s, 'identidad', return_value=ACTOR), \
             patch.object(s, 'padron_autorizado', return_value=padron), \
             patch.object(s, 'compartidos', return_value=[doc]), \
             patch.object(s, 'autorizar', return_value=ACTOR):
            app = AppTest.from_string('''
import streamlit as st
from ui.planeacion_colaboracion import panel
panel('colab_auto')
''').run()
            self.assertFalse(app.exception)
            # Como solo hay 1 escuela, 1 formato y 1 grupo, no deben existir selectores redundantes
            labels_selectbox = [sb.label for sb in app.selectbox]
            self.assertNotIn('Escuela del trabajo compartido', labels_selectbox)
            self.assertNotIn('Grado y grupo', labels_selectbox)
            self.assertNotIn('Documento compartido · grado y periodo', labels_selectbox)
            # El documento queda resuelto y listo en sesión
            self.assertEqual(app.session_state['colab_auto_id'], 'doc-unico-xix')

    def test_seleccionar_alumno_autoselecciona_cuando_hay_un_solo_alumno(self):
        app = AppTest.from_string('''
import streamlit as st
from ui.pages import _seleccionar_alumno
import pandas as pd
df = pd.DataFrame([{'ID_Alumno': 'A100', 'Nombre_Completo': 'JUAN PÉREZ ÚNICO', 'Grado': '3o.', 'Grupo': 'B'}])
aid, fila = _seleccionar_alumno(df, "Alumno asignado", "clave_alumno_test")
st.session_state['resultado_id'] = aid
''').run()
        self.assertFalse(app.exception)
        # No genera selectbox porque solo hay 1 opción
        self.assertFalse(any(sb.label == "Alumno asignado" for sb in app.selectbox))
        self.assertEqual(app.session_state['resultado_id'], 'A100')
        self.assertEqual(app.session_state['clave_alumno_test'], 'A100')

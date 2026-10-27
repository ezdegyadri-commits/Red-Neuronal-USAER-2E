"""La recuperación aparece sin pulsar Actualizar; datos ficticios y sin red."""
from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from services import planeacion as s
from ui import planeacion_repositorio as ui
from tests.test_planeacion_heredada import ejemplo
from tests.test_planeacion_panel import ACTOR


class ActualizacionTests(TestCase):
    def test_dos_consultas_recuperan_nueva_tarjeta_sin_botones_ni_escrituras(self):
        primero=ejemplo();primero['metadatos']['modalidad_planeacion']='individual'
        segundo=deepcopy(primero);segundo['id']='recuperada-ficticia'
        state={'edicion_doc':deepcopy(primero),'edicion_pending':True}
        antes=deepcopy(state)
        with patch.object(ui.st,'session_state',state),patch.object(s,'identidad',return_value=ACTOR),patch.object(s,'listar',side_effect=[[primero],[primero,segundo]]),patch.object(ui,'panel') as panel,patch.object(ui.st,'caption'),patch.object(s,'refrescar') as refrescar,patch.object(s,'guardar') as guardar:
            # Ejecuta el cuerpo del mismo fragmento como dos ticks automáticos.
            funcion=ui.listado.__wrapped__
            self.assertEqual(len(funcion('p',lambda *a:None)),1)
            self.assertEqual(len(funcion('p',lambda *a:None)),2)
            self.assertEqual(len(panel.call_args.args[1]),2)
            refrescar.assert_not_called();guardar.assert_not_called()
        self.assertEqual(state,antes)

    def test_la_vista_muestra_dos_tarjetas_al_entrar_sin_actualizar(self):
        a=ejemplo();a['metadatos']['modalidad_planeacion']='individual'
        b=deepcopy(a);b['id']='segunda-ficticia'
        b['datos']['Alumnos'][0]['Nombre del alumno']='Segundo alumno ficticio'
        with patch.object(s,'identidad',return_value=ACTOR),patch.object(s,'listar',return_value=[a,b]):
            app=AppTest.from_string('''
from ui.planeacion_repositorio import listado
listado('prueba',lambda *a:None)
''').run()
        self.assertFalse(app.exception)
        self.assertEqual(app.tabs[0].label,'Individuales (2)')
        self.assertFalse(any('Actualizar' in b.label for b in app.button))
        self.assertEqual(sum(b.label=='Continuar esta planeación' for b in app.button),2)

    def test_consulta_fallida_no_guarda_no_crea_y_se_reintenta_en_otro_tick(self):
        with patch.object(s,'identidad',return_value=ACTOR),patch.object(s,'listar',side_effect=[ConnectionError('ficticia'),[]]),patch.object(ui.st,'warning') as warning,patch.object(ui.st,'caption'),patch.object(ui.st,'info'),patch.object(s,'nueva') as nueva:
            funcion=ui.listado.__wrapped__
            self.assertEqual(funcion('p',lambda *a:None),[])
            self.assertEqual(funcion('p',lambda *a:None),[])
            warning.assert_called_once();nueva.assert_not_called()

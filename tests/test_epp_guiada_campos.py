"""La vista guiada debe leer y editar el mismo contenido que guarda el informe."""
from copy import deepcopy
from pathlib import Path
from unittest import TestCase
from services.epp_modelo import vacia, recuperar_campos_guiados, validar_parte


class CanonicosTests(TestCase):
    def test_recupera_captura_antigua_sin_sobrescribir_canonica(self):
        v=vacia('Conclusión');v['7.1. Conclusión']='TEXTO-ANTIGUO-QA';antes=deepcopy(v)
        nuevo=validar_parte('Conclusión',v)
        self.assertEqual(nuevo['campos']['7.1. Conclusión'],'TEXTO-ANTIGUO-QA');self.assertEqual(v,antes)
        nuevo['campos']['7.1. Conclusión']='CORRECCION-QA'
        self.assertEqual(recuperar_campos_guiados('Conclusión',nuevo)['campos']['7.1. Conclusión'],'CORRECCION-QA')


class VistaGuiadaTests(TestCase):
    def test_boton_de_la_captura_llena_conclusion_y_tabla_nee_y_permite_editar(self):
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_file(str(Path(__file__).parent/'fixtures/epp_viva_app.py'),default_timeout=30)
        app.session_state['qa_conclusion_test']=True
        app.query_params['principal']='1'
        app.run();self.assertFalse(app.exception)
        from services.epp_modelo import campos
        self.assertTrue(next(t for t in app.text_area if t.label==campos('Aprendizaje')[0]).value)
        self.assertFalse(any(b.label=='🗑️ Vaciar' for b in app.button))
        next(w for w in app.button_group if w.label=='Modo de trabajo:').set_value('⚖️ Conclusión y NEE').run()
        next(b for b in app.button if 'Generar propuesta de NEE oficial SEGEY' in b.label).click().run()
        self.assertFalse(app.exception)
        conclusion=next(t for t in app.text_area if t.label=='7.1. Conclusión')
        self.assertTrue(conclusion.value)
        import hashlib
        from tests.test_epp import ACTOR, ALUMNO
        from services.epp_modelo import clave
        prefix='epp_'+hashlib.sha256(ACTOR['cuenta'].encode()).hexdigest()[:12]+'_edit_'+clave(ALUMNO['ID_Alumno'],'2026-2027')+'_Conclusión'
        self.assertTrue(any(r.get('NEE','').startswith('Necesita') for r in app.session_state[prefix+'_table_nee_base']))
        conclusion.set_value('CONCLUSION-EDITADA-QA').run();self.assertFalse(app.exception)
        import json
        ultimo=[json.loads(r[-1]) for r in app.session_state['qa_rows'] if r[2]=='Conclusión'][-1]
        self.assertEqual(ultimo['campos']['7.1. Conclusión'],'CONCLUSION-EDITADA-QA')

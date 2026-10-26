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
    def test_comunicacion_y_ts_ven_sus_campos_compartidos(self):
        from streamlit.testing.v1 import AppTest
        for area,fields in [('Comunicación',['4.1. Orientación temporal','4.3. Coordinación motriz fina','4.3. Coordinación motriz gruesa']),('Trabajo Social',['Domicilio','Nombre de la madre','Motivo de evaluación'])]:
            app=AppTest.from_file(str(Path(__file__).parent/'fixtures/epp_viva_app.py'),default_timeout=30)
            app.query_params['principal']='1';app.query_params['area']=area;app.run()
            self.assertFalse(app.exception)
            for field in fields:self.assertTrue(any(t.label==field and not t.disabled for t in app.text_area),field)

    def test_asistente_prepara_resumen_sin_enviar_ni_reemplazar(self):
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_file(str(Path(__file__).parent/'fixtures/epp_viva_app.py'),default_timeout=30)
        app.query_params['principal']='1';app.run();self.assertFalse(app.exception)
        next(b for b in app.button if b.label=='Proponer redacción').click().run();self.assertFalse(app.exception)
        next(t for t in app.text_area if t.label.startswith('Tus ideas')).set_value('Necesita apoyos visuales durante la tarea.').run()
        next(b for b in app.button if b.label=='Preparar texto para revisión').click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any('apoyos visuales' in t.value for t in app.text_area if t.label.startswith('Resumen que se enviará')))
        self.assertFalse(any(c.value for c in app.checkbox if c.label=='Revisé el resumen y autorizo enviarlo a IA'))

    def test_no_requiere_conserva_texto_y_permanece_reversible(self):
        from streamlit.testing.v1 import AppTest
        from services.epp_modelo import campos
        app=AppTest.from_file(str(Path(__file__).parent/'fixtures/epp_viva_app.py'),default_timeout=30)
        app.query_params['principal']='1';app.run();self.assertFalse(app.exception)
        campo=campos('Aprendizaje')[0]
        original=next(t for t in app.text_area if t.label==campo).value
        control=next(c for c in app.checkbox if c.key.endswith('_campos'+campo+'_no_req'))
        control.check().run();self.assertFalse(app.exception)
        self.assertEqual(next(t for t in app.text_area if t.label==campo).value,'No se requiere')
        self.assertTrue(next(t for t in app.text_area if t.label==campo).disabled)
        next(c for c in app.checkbox if c.key==control.key).uncheck().run();self.assertFalse(app.exception)
        self.assertEqual(next(t for t in app.text_area if t.label==campo).value,original)

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

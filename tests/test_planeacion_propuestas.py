from copy import deepcopy
from pathlib import Path
import unittest
from streamlit.testing.v1 import AppTest
from ai.planeacion_prompt import huella, solicitud, validar_respuesta

REFERENTES={'fuentes':[{'id':'SEP-PLAN2022','titulo':'Plan','url':'https://ejemplo.test'}],
    'referentes_por_grado':[{'id':'R1','grado':1,'pda':'Texto de prueba','contenido':'Contenido de prueba'}]}
PROPUESTA={k:'Texto de prueba' for k in ('necesidad','objetivo','descriptor','actividad','contexto',
    'temporalidad','recursos','evaluacion','fundamento')}
PROPUESTA.update(fuentes=['SEP-PLAN2022'],referentes=['R1'])

class PropuestasTests(unittest.TestCase):
    def setUp(self):
        import ui.planeacion as u
        self.ui=u
        self.originales=(u.proponer,u._persist,u.servicio.identidad)

    def tearDown(self):
        self.ui.proponer,self.ui._persist,self.ui.servicio.identidad=self.originales

    def test_huella_cambia_con_evidencia_referente_y_modo(self):
        key=huella('Evidencia A','XXIII','Aprendizaje',curriculo=REFERENTES)
        self.assertNotEqual(key,huella('Evidencia B','XXIII','Aprendizaje',curriculo=REFERENTES))
        self.assertNotEqual(key,huella('Evidencia A','XXIII','Aprendizaje',True,REFERENTES))
        changed=deepcopy(REFERENTES);changed['referentes_por_grado'][0]['pda']='Otro referente'
        self.assertNotEqual(key,huella('Evidencia A','XXIII','Aprendizaje',curriculo=changed))
        changed=deepcopy(REFERENTES);changed['fuentes'][0]['url']='Otro enlace'
        self.assertEqual(key,huella('Evidencia A','XXIII','Aprendizaje',curriculo=changed))

    def test_rechaza_referente_inventado_y_respuesta_incompleta(self):
        p=deepcopy(PROPUESTA);p['referentes']=['OTRO-GRADO']
        with self.assertRaises(ValueError):validar_respuesta({'propuestas':[p]},REFERENTES)
        p=deepcopy(PROPUESTA);p['actividad']=''
        with self.assertRaises(ValueError):validar_respuesta({'propuestas':[p]},REFERENTES)
        self.assertEqual(validar_respuesta({'propuestas':[PROPUESTA]},REFERENTES)['propuestas'][0]['referentes'],['R1'])

    def test_permite_pedir_evidencia_en_lugar_de_inventar(self):
        result=validar_respuesta({'propuestas':[],'faltantes':['¿Qué apoyo ha funcionado?']},REFERENTES)
        self.assertEqual(result['propuestas'],[])
        with self.assertRaises(ValueError):validar_respuesta({'propuestas':[]},REFERENTES)
        with self.assertRaises(ValueError):solicitud('','XXIII','Aprendizaje')

    def test_reabrir_editar_y_aceptar_no_repite_solicitudes(self):
        app=AppTest.from_file(str(Path(__file__).with_name('fixture_ai_planeacion.py')),default_timeout=30).run()
        app.text_area[0].set_value('Necesidad y apoyo documentados.').run()
        app.checkbox[0].check().run()
        next(b for b in app.button if b.label=='Proponer actividades con IA').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['calls'],1)
        next(b for b in app.button if b.label=='Añadir al borrador').click().run()
        self.assertEqual(app.session_state['calls'],1)
        self.assertTrue(next(b for b in app.button if b.label=='Ya añadida al borrador').disabled)
        next(b for b in app.button if b.label=='Volver a abrir el borrador').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['calls'],1)
        self.assertEqual(len(app.session_state['p_doc']['tablas']['aprendizajes']),1)
        app.text_area[0].set_value('Otra necesidad documentada.').run()
        self.assertFalse(any(b.label=='Ya añadida al borrador' for b in app.button))
        self.assertEqual(app.session_state['calls'],1)

if __name__=='__main__':unittest.main()

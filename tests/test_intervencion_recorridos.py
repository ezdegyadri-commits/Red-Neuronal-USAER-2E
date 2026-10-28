from concurrent.futures import Future,ThreadPoolExecutor
from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch
import pandas as pd
from streamlit.testing.v1 import AppTest
from services import planeacion as s,planeacion_grupo_unico as unico
from tests.test_planeacion_panel import PanelTests,ALUMNO,ACTOR,documento


class ServicioTests(PanelTests):
    def test_crear_guardar_y_continuar_anual_sin_tocar_trimestral(self):
        escuelas=pd.DataFrame([{'ID_Escuela':'E1','Nombre_Escuela':'Escuela de prueba','CCT':'TEST'}])
        with patch.object(s.repo,'escuelas',return_value=escuelas),patch.object(s,'padron_autorizado',return_value=pd.DataFrame([{**ALUMNO,'Tipo_Atencion':'Grupal'}])):
            viejo=s.nueva('XXIII',['A1'],modalidad='grupal',vista_formato='guia',trimestre=2)
            viejo=s.guardar(viejo);before=deepcopy(self.sheet.rows)
            anual=s.nueva('XXIII',['A1'],modalidad='grupal',vista_formato='guia',anual=True)
            anual['textos']['Evaluación']='Seguimiento del ciclo conservado'
            saved=s.guardar(anual)
            continua=s.nueva('XXIII',['A1'],modalidad='grupal',vista_formato='guia',anual=True,trimestre=3)
            self.assertEqual(continua['id'],saved['id']);self.assertEqual(continua['textos']['Evaluación'],'Seguimiento del ciclo conservado')
            self.assertEqual(self.sheet.rows[:len(before)],before)
            self.assertEqual(len(unico.documentos(s.reconstruir(self.sheet.rows))),2)
            self.assertNotEqual(saved['id'],viejo['id'])

    def test_20_sesiones_guardan_documentos_aislados_sin_perder_versiones(self):
        docs=[]
        for i in range(20):
            d=documento();d['id']='ficticio-'+str(i);d['textos']['Evaluación']='Registro ficticio '+str(i);docs.append(d)
        with ThreadPoolExecutor(max_workers=20) as pool:results=list(pool.map(s.guardar,docs))
        actuales=s.reconstruir(self.sheet.rows)
        self.assertEqual(len(actuales),20)
        self.assertEqual({d['textos']['Evaluación'] for d in actuales},{d['textos']['Evaluación'] for d in docs})
        self.assertEqual(len({d['id'] for d in results}),20)


class InterfazTests(TestCase):
    def test_lectura_iniciada_en_version_anterior_no_reemplaza_aporte_nuevo(self):
        from ui import lecturas_documento as lector
        viejo=Future();viejo.set_result(['versión anterior']);nuevo=Future()
        state={'consulta':{'cuenta':ACTOR['cuenta'],'firma':'anterior','future':viejo}}
        with patch.object(lector.st,'session_state',state),patch.object(s,'identidad',return_value=ACTOR),patch.object(lector,'enviar',return_value=nuevo):
            self.assertIsNone(lector.consultar('consulta',lambda:None,firma='nueva'))
            nuevo.set_result(['versión nueva'])
            self.assertEqual(lector.consultar('consulta',lambda:None,firma='nueva'),['versión nueva'])
    def test_rubrica_se_presenta_sin_calificar_y_sin_claves_duplicadas(self):
        source='''
import streamlit as st
from services import planeacion as s
from unittest.mock import patch
from tests.test_planeacion_local import documento
from tests.test_planeacion_panel import ACTOR
from ui.planeacion_calidad import panel
st.session_state.setdefault('prueba_doc',documento())
with patch.object(s,'identidad',return_value=ACTOR),patch.object(s,'autorizar',return_value=ACTOR):
    panel('prueba')
'''
        app=AppTest.from_string(source).run(timeout=30)
        self.assertFalse(app.exception)
        self.assertTrue(any('14 indicadores' in e.label for e in app.expander))
        self.assertEqual(len(app.dataframe),1)
        app.run(timeout=30);self.assertFalse(app.exception)
    def test_pendiente_ia_no_reenvia_y_resultado_no_cruza_documentos(self):
        from ui import planeacion_tareas as tareas
        d=documento();future=Future();state={'prueba_doc':d}
        with patch.object(tareas.st,'session_state',state),patch.object(s,'identidad',return_value=ACTOR),patch.object(s,'autorizar'),patch.object(tareas,'enviar',return_value=future) as send,patch('ai.planeacion.configuracion_trabajo',return_value={}):
            tareas.iniciar('prueba',{'resumen':'Ficticio'},d);tareas.iniciar('prueba',{'resumen':'Ficticio'},d)
            self.assertEqual(send.call_count,1);self.assertIsNone(tareas.recoger('prueba',d))
            future.set_result({'unidades':[]});otro=deepcopy(d);otro['id']='otro'
            self.assertIsNone(tareas.recoger('prueba',otro));self.assertIn('prueba_ia_trabajo',state)
            result=tareas.recoger('prueba',d);self.assertEqual(result['respuesta'],{'unidades':[]})
            self.assertNotIn('prueba_ia_trabajo',state)

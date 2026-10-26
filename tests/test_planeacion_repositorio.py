from copy import deepcopy
from unittest import TestCase
from streamlit.testing.v1 import AppTest
from services.planeacion_recuperacion import repositorios,titulo_tarjeta,detalle_tarjeta
from tests.test_planeacion_todos_grupos import documento


class RepositorioTests(TestCase):
    def test_busqueda_global_encuentra_documento_antiguo_sin_modalidad_ni_grado_actual(self):
        app=AppTest.from_string('''
import streamlit as st
from ui.planeacion_repositorio import panel
from tests.test_planeacion_todos_grupos import documento
d=documento(('A1',));d['id']='original-historico';d['metadatos'].pop('modalidad_planeacion',None)
d['datos']['Alumnos'][0]['Nombre del alumno']='ESTUDIANTE HISTORICO QA';d['datos']['Alumnos'][0]['Grado']='5o.'
st.session_state.setdefault('prueba_repositorio_Otros formatos guardados_buscar','No coincide')
def abrir(base,doc):st.session_state['abierto']=doc['id']
panel('prueba',[d],abrir)
''',default_timeout=30).run()
        self.assertFalse(app.exception)
        next(t for t in app.text_input if t.label=='Buscar alumno en todas mis planeaciones').set_value('HISTORICO QA').run()
        self.assertFalse(app.exception)
        self.assertTrue(any('ESTUDIANTE HISTORICO QA' in h.value for h in app.subheader))
        next(b for b in app.button if b.label=='Continuar esta planeación').click().run()
        self.assertFalse(app.exception);self.assertEqual(app.session_state['abierto'],'original-historico')

    def test_no_anuncia_sin_trabajo_cuando_la_guia_tiene_aportes(self):
        d=documento(('A1',));d['metadatos']['guia_grupal_manual']={'filas':[{'ID_Alumno':'A1','Aprendizaje':'Actividad ya redactada'}]}
        self.assertIn('Con trabajo redactado',detalle_tarjeta(d))
        self.assertNotIn('Sin actividades',detalle_tarjeta(d))

    def test_separa_sin_ocultar_historicos_ni_cambiar_documentos(self):
        docs=[]
        for i,tipo in enumerate(('individual','grupal','especialista','historico')):
            d=documento(('A1',));d['id']=str(i);d['metadatos']['modalidad_planeacion']=tipo;docs.append(d)
        antes=deepcopy(docs);grupos=repositorios(docs)
        self.assertEqual({k:len(v) for k,v in grupos.items()},{'Individuales':1,'Grupales':1,'Mi intervención':1,'Otros formatos guardados':1})
        self.assertEqual(docs,antes)
        self.assertIn(docs[0]['datos']['Alumnos'][0]['Nombre del alumno'],titulo_tarjeta(docs[0]))
        self.assertNotIn(docs[0]['id']+' ·',detalle_tarjeta(docs[0]))

    def test_tarjetas_continuan_id_correcto_sin_selector_mezclado_ni_pdf_anticipado(self):
        app=AppTest.from_string('''
import streamlit as st
from ui.planeacion_repositorio import panel
from tests.test_planeacion_todos_grupos import documento
docs=[]
for i,tipo in enumerate(('individual','grupal')):
    d=documento(('A1',));d['id']='doc-'+str(i);d['metadatos']['modalidad_planeacion']=tipo;docs.append(d)
def abrir(base,doc):st.session_state['abierto']=doc['id']
panel('prueba',docs,abrir)
''',default_timeout=30).run()
        self.assertFalse(app.exception)
        self.assertEqual([t.label for t in app.tabs],['Individuales (1)','Grupales (1)'])
        self.assertFalse(app.get('download_button'))
        self.assertFalse(any(s.label=='Mis planeaciones recientes' for s in app.selectbox))
        [b for b in app.button if b.label=='Continuar esta planeación'][1].click().run()
        self.assertFalse(app.exception);self.assertEqual(app.session_state['abierto'],'doc-1')

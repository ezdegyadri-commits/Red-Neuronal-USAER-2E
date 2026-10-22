from copy import deepcopy
from unittest import TestCase
from streamlit.testing.v1 import AppTest
from services.planeacion_recuperacion import repositorios,titulo_tarjeta,detalle_tarjeta
from tests.test_planeacion_todos_grupos import documento


class RepositorioTests(TestCase):
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

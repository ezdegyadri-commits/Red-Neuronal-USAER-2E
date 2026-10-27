"""Integración de cierre EPP: exclusivamente datos ficticios y motor sustituido."""
from copy import deepcopy
from pathlib import Path
import unittest
from services.epp_modelo import AREAS, CONCLUSION, NEE, BAP, campos, vacia
from services.epp_conclusion import fuentes, incorporar


def propuesta():
    return {'campos':{k:'Propuesta QA interdisciplinaria · '+k for k in CONCLUSION},
        'nee':[{**dict.fromkeys(NEE,''),'NEE':'Necesita comprender consignas con apoyos visuales.'}],
        'bap':[{**dict.fromkeys(BAP,''),'Tipo de barrera':'Consignas extensas sin apoyos documentadas en el aula.'}],
        'faltantes':[]}


class ConclusionTests(unittest.TestCase):
    def doc(self):
        return {'partes':{a:{'contenido':{**vacia(a),'campos':{k:'MARCADOR '+a+' '+('observación '*500) for k in campos(a)}}} for a in AREAS}}

    def test_resumen_incluye_cuatro_areas_sin_que_la_primera_desplace_a_las_otras(self):
        rows=fuentes(self.doc());self.assertEqual([r['referencia'] for r in rows],list(AREAS))
        for r in rows:self.assertIn('MARCADOR',r['texto']);self.assertLess(len(r['texto']),2400)

    def test_sintesis_y_evaluaciones_tambien_se_reunen(self):
        doc={'partes':{a:{'contenido':{**vacia(a),'sintesis':'SINTESIS-QA-'+a,
            'evaluaciones':[{'nombre':'INSTRUMENTO-QA','texto':'RESULTADO-QA'}]}} for a in AREAS}}
        for r in fuentes(doc):self.assertIn('SINTESIS-QA',r['texto']);self.assertIn('RESULTADO-QA',r['texto'])
        with self.assertRaises(ValueError):fuentes({'partes':{}})

    def test_cierre_se_llena_y_reintento_no_duplica_nee_ni_toca_origen(self):
        value=vacia('Conclusión');antes=deepcopy(value)
        result=incorporar(value,propuesta(),{'Aprendizaje':'r1'})
        self.assertEqual(value,antes);self.assertFalse(result['validada'])
        self.assertTrue(result['campos']['7.1. Conclusión'])
        again=incorporar(result,propuesta(),{'Aprendizaje':'r1'})
        self.assertEqual(again['nee'],result['nee']);self.assertEqual(again['bap'],result['bap'])

    def test_conserva_filas_docentes_y_actualiza_propuesta_sin_borrar_manual(self):
        value=incorporar(vacia('Conclusión'),propuesta(),{})
        value['nee'][0]['Apoyos']='EDICION-DOCENTE'
        otra=propuesta();otra['nee'][0]['NEE']='Necesita contar objetos mediante material concreto.'
        result=incorporar(value,otra,{})
        self.assertEqual(len(result['nee']),2);self.assertEqual(result['nee'][0]['Apoyos'],'EDICION-DOCENTE')
        self.assertEqual(len(incorporar(result,otra,{})['nee']),2)

    def test_respuesta_vacia_no_se_anuncia_como_integrada(self):
        with self.assertRaises(ValueError):incorporar(vacia('Conclusión'),{'campos':{},'nee':[],'bap':[]},{})


class PantallaConclusionTests(unittest.TestCase):
    def preparar(self,cambia=False):
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_file(str(Path(__file__).parent/'fixtures/epp_viva_app.py'),default_timeout=30)
        app.session_state['qa_conclusion_test']=True
        app.run()
        next(b for b in app.button if b.label=='Abrir EPP del alumno').click().run()
        next(c for c in app.checkbox if c.label.startswith('Autorizo usar los hallazgos')).check().run()
        self.assertFalse(app.exception)
        return app

    def generar(self,app,cambia=False):
        from concurrent.futures import Future
        from unittest.mock import patch
        from tests.test_epp_contextual import respuesta
        from ui import epp_contextual as ui
        def enqueue(p,config):
            r=respuesta(p);ref=p['datos']['fuentes'][0]['id']
            r['nee']=[dict(propuesta()['nee'][0],fuentes=[ref])]
            r['bap']=[dict(propuesta()['bap'][0],fuentes=[ref])]
            if cambia:
                import streamlit as st
                key=next(k for k in st.session_state if k.startswith('epp_viva_') and k.endswith('_doc'))
                doc=deepcopy(st.session_state[key])
                doc['partes']['Psicología']['contenido']['campos'][campos('Psicología')[0]]='Hallazgo actualizado durante IA'
                st.session_state[key]=doc
            future=Future();future.set_result(r);return future
        with patch('ai.epp_contextual.enviar',side_effect=enqueue),patch('ai.epp_contextual.configuracion',return_value={}),patch('ui.epp_viva.guardar',return_value=True):
            next(b for b in app.button if b.label=='✨ Redactar EPP Automáticamente').click().run()
        return app

    def test_genera_guarda_y_muestra_en_formato_sin_esperar_tick(self):
        app=self.generar(self.preparar())
        self.assertFalse(app.exception)
        spec=app.session_state['qa_spec']
        self.assertTrue(any(c['value'].startswith('Hallazgo documentado') for c in spec['cells'].values()))
        self.assertTrue(any(c['value']=='Necesita comprender consignas con apoyos visuales.' for c in spec['cells'].values()))
        # El borrador visible precede al acuse de guardado, gestionado por su cola.
        self.assertTrue(any(c['value'] for c in spec['cells'].values() if c.get('target')==['Conclusión','campos','7.1. Conclusión']))

    def test_hallazgos_nuevos_durante_ia_impiden_incorporar_cierre_obsoleto(self):
        app=self.generar(self.preparar(),cambia=True)
        self.assertFalse(app.exception)
        self.assertTrue(any('actualizó sus hallazgos' in x.value for x in app.warning))
        self.assertFalse(any(r[2]=='Conclusión' for r in app.session_state['qa_rows']))

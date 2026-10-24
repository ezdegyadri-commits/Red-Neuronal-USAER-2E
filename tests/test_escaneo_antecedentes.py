"""Documentos ficticios: recuperación persistente y reutilización sin OCR ni IA."""
import json
from datetime import date
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch
from services import documentos_sintesis as ds, evaluacion_archivo as ea


def fuente(tipo='Competencia curricular', ids=('QA-1',), ciclo='2026-2027'):
    return {'Revision':'qa-revision', 'resumen':'Hallazgo educativo ficticio revisado.',
        'necesidades':[], 'documento':{'ID_Documento':'DOC-QA', 'Tipo':tipo,
            'ID_Alumnos_JSON':json.dumps(ids), 'Ciclo':ciclo, 'Fecha':'2026-10-23',
            'Ambito':'individual' if len(ids)==1 else 'grupal'}}


class EscaneoAntecedentesTests(TestCase):
    def test_interfaz_archiva_al_guardar_y_permite_reintento_sin_duplicar_evaluacion(self):
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_file(str(Path(__file__).parent/'fixtures/epp_instrumentos_app.py'),default_timeout=30)
        for k,v in dict(qa_modo='externo',qa_extension='pdf',qa_fallo_archivo=True).items():app.session_state[k]=v
        app.run()
        next(b for b in app.button if b.label=='Leer foto o escaneo').click().run()
        next(t for t in app.text_input if t.label=='Instrumento o informe que emitió el profesional').set_value('Evaluación ficticia').run()
        app.date_input[0].set_value(date(2026,10,23)).run()
        next(c for c in app.checkbox if c.label.startswith('Verifiqué alumno')).check().run()
        next(b for b in app.button if b.label=='Guardar evaluación y preparar análisis').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.session_state.qa_value['evaluaciones']),1)
        self.assertTrue(any('no se confirmó el archivo' in w.value for w in app.warning))
        app.session_state['qa_fallo_archivo']=False
        next(b for b in app.button if b.label=='Guardar evaluación y preparar análisis').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.session_state.qa_value['evaluaciones']),1)
        self.assertEqual(app.session_state.qa_archivos,2)
        self.assertEqual(app.session_state.qa_ai_calls,0)
        self.assertTrue(any('Original y síntesis confirmados' in s.value for s in app.success))

    def test_prueba_revisada_alimenta_antecedentes_sin_convertirse_en_nee(self):
        with patch.object(ds,'listar',return_value={'DOC-QA':fuente()}):
            f=ds.fuentes_documentales({'QA-1'},'2026-2027')
        self.assertEqual(len(f),1)
        self.assertEqual(f[0]['tipo'],'DOCUMENTO_REVISADO')
        self.assertEqual(f[0]['documento_origen'],'DOC-QA')
        self.assertNotIn('NEE',json.loads(f[0]['texto']))
        self.assertIn('no de evaluación',f[0]['alcance'])

    def test_epp_sin_nee_tambien_aporta_su_sintesis(self):
        with patch.object(ds,'listar',return_value={'DOC-QA':fuente('EPP')}):
            f=ds.fuentes_epp({'QA-1'},'2026-2027')
        self.assertEqual(len(f),1)
        self.assertEqual(json.loads(f[0]['texto'])['NEE'],[])

    def test_excluye_identidad_terceros_ciclos_futuros_y_colectivos_incompletos(self):
        for r in (fuente('CURP'),fuente('Acta de nacimiento'),fuente(ids=('AJENO',)),
                  fuente(ciclo='2027-2028'),fuente(ids=('QA-1','AJENO'))):
            with self.subTest(r=r),patch.object(ds,'listar',return_value={'DOC-QA':r}):
                self.assertEqual(ds.fuentes_documentales({'QA-1'},'2026-2027'),[])

    def test_colectivo_solo_en_contexto_completo_y_con_alcance_claro(self):
        with patch.object(ds,'listar',return_value={'DOC-QA':fuente('Evaluación diagnóstica',('QA-1','QA-2'))}):
            f=ds.fuentes_documentales({'QA-1','QA-2'},'2026-2027')
        self.assertIn('colectiva',f[0]['alcance'])
        self.assertEqual(f[0]['alumno'],'QA-1,QA-2')

    def test_guarda_original_y_sintesis_sin_tocar_epp_ni_inferir_necesidades(self):
        doc={'alumno':'QA-1','id':'EPP-QA','ciclo':'2026-2027'}
        with patch.object(ea.archivo,'guardar',return_value='DOC-QA') as original, \
                patch.object(ea.sintesis,'guardar',return_value='REV-QA') as resumen:
            self.assertEqual(ea.guardar(doc,'Aprendizaje','prueba.pdf',b'ficticio','Hallazgo revisado.'),'DOC-QA')
        self.assertEqual(original.call_args.args[0],['QA-1'])
        self.assertEqual(original.call_args.args[1],'Competencia curricular')
        self.assertEqual(resumen.call_args.args[1]['necesidades'],[])

    def test_fallo_parcial_no_se_presenta_como_confirmado_y_no_borra_original(self):
        with patch.object(ea.archivo,'guardar',return_value='DOC-QA') as original, \
                patch.object(ea.sintesis,'guardar',side_effect=RuntimeError('Sin confirmar')):
            with self.assertRaises(RuntimeError):
                ea.guardar({'alumno':'QA-1','id':'EPP-QA','ciclo':'2026-2027'},'Aprendizaje','prueba.pdf',b'ficticio','Hallazgo revisado.')
        original.assert_called_once()

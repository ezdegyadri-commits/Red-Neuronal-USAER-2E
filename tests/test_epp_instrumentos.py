from copy import deepcopy
from pathlib import Path
import unittest
from datetime import date
from streamlit.testing.v1 import AppTest
from services import epp_instrumentos as m
from services.epp_modelo import vacia,validar_parte


class MotorTests(unittest.TestCase):
    def test_catalogo_reactivos_unicos_y_fuente(self):
        for code,d in m.DEFINICIONES.items():
            self.assertEqual(len(d['items']),len({q['id'] for q in d['items']}))
            self.assertTrue(d['paginas']);self.assertEqual(m.calcular(code,m.plantilla(code))['respondidos'],0)
        self.assertEqual(len(m.DEFINICIONES['XVI']['items']),19)

    def test_no_observado_no_equivale_a_no_ni_puntaje_clinico(self):
        c=m.plantilla('XI');c['respuestas']['1']['respuesta']='Sí';c['respuestas']['2']['respuesta']='No'
        r=m.calcular('XI',c)
        self.assertEqual(r['conteos'],{'Sí':1,'No':1});self.assertEqual(len(r['pendientes']),14)
        self.assertNotIn('puntaje',r);self.assertNotIn('diagnostico',r)
        c['respuestas']['3']['observaciones']='No pudo observarse por inasistencia.'
        r=m.calcular('XI',c)
        self.assertTrue(any('inasistencia' in h for h in r['hallazgos']));self.assertEqual(r['respondidos'],2)

    def test_frecuencias_no_se_suman_con_si_no(self):
        c=m.plantilla('XIV');c['respuestas']['8.1']['respuesta']='3 · Muy frecuente';c['respuestas']['9.1']['respuesta']='2 · Frecuente'
        r=m.calcular('XIV',c);self.assertEqual(r['respondidos'],2);self.assertNotIn('total',r)

    def test_rechaza_categoria_fecha_y_clave_ajena(self):
        for mutate in (lambda c:c['respuestas']['1'].update(respuesta='Siempre'),lambda c:c.update(fecha='2026-02-31'),lambda c:c['respuestas'].update(ajeno={})):
            c=m.plantilla('XI');mutate(c)
            with self.assertRaises(ValueError):m.validar('XI',c)

    def test_edicion_parcial_conserva_otras_frecuencias(self):
        c=m.plantilla('XIV');c['respuestas']['8.1']['respuesta']='3 · Muy frecuente'
        base=[{'Ítem':'1','Respuesta':'No observado','Observaciones':''}]
        edited=m.editar_respuestas('XIV',c,base,{'edited_rows':{0:{'Respuesta':'Sí'}}})
        self.assertEqual(edited['respuestas']['8.1'],c['respuestas']['8.1']);self.assertEqual(edited['respuestas']['1']['respuesta'],'Sí')
        with self.assertRaises(ValueError):m.editar_respuestas('XIV',c,base,{'edited_rows':{0:{'Ítem':'2'}}})

    def test_incorporacion_idempotente_preserva_texto_y_otras_areas(self):
        doc={'id':'epp-ficticia','partes':{'Aprendizaje':{'contenido':vacia('Aprendizaje')},'Psicología':{'contenido':vacia('Psicología')}}}
        doc['partes']['Aprendizaje']['contenido']['campos']['5.2. Estilo de aprendizaje']='Texto profesional previo'
        before=deepcopy(doc);c=m.plantilla('XIV');c['fecha']='2026-10-22';c['respuestas']['1']['respuesta']='Sí'
        v=m.incorporar(doc,'Aprendizaje','XIV',c,True)
        self.assertEqual(doc,before);self.assertEqual(v['campos']['5.2. Estilo de aprendizaje'],'Texto profesional previo')
        doc['partes']['Aprendizaje']['contenido']=v
        again=m.incorporar(doc,'Aprendizaje','XIV',c,True)
        self.assertEqual(len(again['evaluaciones']),1);self.assertFalse(again['validada'])
        with self.assertRaises(PermissionError):m.incorporar(doc,'Psicología','XIV',c,True)
        self.assertEqual(validar_parte('Aprendizaje',v),v)

    def test_requiere_revision_fecha_y_respuestas(self):
        doc={'id':'epp','partes':{}}
        with self.assertRaises(ValueError):m.incorporar(doc,'Aprendizaje','XIV',m.plantilla('XIV'),False)
        with self.assertRaises(ValueError):m.incorporar(doc,'Aprendizaje','XIV',m.plantilla('XIV'),True)
        v=vacia('Comunicación');v['aplicaciones_en_curso']={'XI':m.plantilla('XI')}
        with self.assertRaises(PermissionError):validar_parte('Comunicación',v)


class UITests(unittest.TestCase):
    def open(self,modo):
        app=AppTest.from_file(str(Path(__file__).with_name('fixtures')/'epp_instrumentos_app.py'),default_timeout=30)
        app.session_state['qa_modo']=modo
        return app.run()

    def test_formato_digital_recupera_borrador_y_finaliza_una_vez(self):
        app=self.open('digital');self.assertFalse(app.exception)
        self.assertTrue(any('1/' in x.value for x in app.markdown))
        next(c for c in app.checkbox if c.label.startswith('Revisé las respuestas')).check().run()
        next(b for b in app.button if b.label=='Resumir respuestas e incorporar al informe').click().run()
        self.assertFalse(app.exception);self.assertEqual(len(app.session_state.qa_value['evaluaciones']),1)
        self.assertEqual(app.session_state.qa_ai_calls,0)

    def test_externo_revisa_anonimiza_y_no_sobrescribe_redaccion(self):
        app=self.open('externo');self.assertFalse(app.exception)
        next(b for b in app.button if b.label=='Leer foto o escaneo').click().run()
        next(t for t in app.text_input if t.label=='Instrumento o informe que emitió el profesional').set_value('Informe externo ficticio').run()
        app.date_input[0].set_value(date(2026,10,22)).run()
        next(c for c in app.checkbox if c.label.startswith('Verifiqué alumno')).check().run()
        next(b for b in app.button if b.label=='Guardar evaluación y preparar análisis').click().run()
        self.assertFalse(app.exception);self.assertEqual(app.session_state.qa_ai_calls,0)
        self.assertTrue(next(b for b in app.button if b.label.startswith('Analizar resultados')).disabled)
        next(c for c in app.checkbox if c.label.startswith('Revisé el resumen anonimizado')).check().run()
        next(b for b in app.button if b.label.startswith('Analizar resultados')).click().run()
        self.assertFalse(app.exception);self.assertEqual(app.session_state.qa_ai_calls,1)
        self.assertEqual(app.session_state.qa_value['campos']['5.1. Competencia curricular'],'Redacción previa')
        self.assertEqual(app.session_state.qa_value['campos']['5.2. Estilo de aprendizaje'],'EV1: Propuesta ficticia revisable.')
        next(t for t in app.text_area if t.label.startswith('Síntesis del documento')).set_value('Contenido corregido de la lectura').run()
        self.assertTrue(next(b for b in app.button if b.label.startswith('Analizar resultados')).disabled)

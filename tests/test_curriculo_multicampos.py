"""Referentes de varios campos, con datos ficticios y sin llamadas a IA."""
from copy import deepcopy
import unittest
from unittest.mock import patch
from services.curriculo import CAMPOS,opciones,vincular,contexto_ia,campos_seleccionados
from services import planeacion_generacion as g
from documents.planeacion import generar_pdf
from tests.test_planeacion_completa import documento
from tests import test_planeacion_simple as simple


class MulticamposTests(unittest.TestCase):
    def preparar(self,area='Aprendizaje'):
        doc=documento(area)
        campos=['Lenguajes','De lo Humano y lo Comunitario']
        refs=[opciones(doc,c,[3])[0] for c in campos]
        return vincular(doc,campos,['Inclusión'],[r['id'] for r in refs]),campos,refs

    def test_cuatro_perfiles_preservan_texto_oficial_y_adaptaciones(self):
        for area in ('Aprendizaje','Psicología','Comunicación','Trabajo Social'):
            d,campos,refs=self.preparar(area)
            d=vincular(d,campos,['Inclusión'],[r['id'] for r in refs],adaptaciones={refs[1]['id']:{'pda':'Adaptación docente conservada'}})
            ctx=contexto_ia(d)
            self.assertEqual(set(ctx['campo']),set(campos))
            self.assertEqual({r['id'] for r in ctx['referentes_por_grado']},{r['id'] for r in refs})
            self.assertEqual(ctx['referentes_por_grado'][1]['pda'],refs[1]['pda'])
            self.assertEqual(ctx['adaptaciones_docentes'][refs[1]['id']]['pda'],'Adaptación docente conservada')
            for c in campos:self.assertIn(c,g.texto_curricular(d))
            self.assertEqual(d['datos']['Alumnos'][0]['Grado'],'5')

    def test_lectura_legacy_y_guardado_revalidado_sin_perdida(self):
        doc,campos,refs=self.preparar()
        cur=doc['metadatos']['curriculo']
        recuperado=vincular(doc,campos_seleccionados(cur),cur['ejes'],[r['id'] for r in cur['registros']])
        self.assertEqual(recuperado,doc)
        self.assertEqual(campos_seleccionados({'campo':'Lenguajes'}),['Lenguajes'])
        legacy=vincular(documento(),'Lenguajes',[],[refs[0]['id']])
        legacy['metadatos']['curriculo'].pop('campos')
        self.assertEqual(list(contexto_ia(legacy)['campo']),['Lenguajes'])

    def test_no_reduce_la_seleccion_manual_al_generar(self):
        doc,campos,refs=self.preparar()
        antes=deepcopy(doc)
        ajustes={**g.configuracion(doc),'campo_referencia':'Saberes y Pensamiento Científico','grado_referencia':1}
        self.assertEqual(g.sugerir_curriculo(doc,ajustes),antes)

    def test_no_acepta_referentes_de_campo_no_elegido(self):
        doc,campos,refs=self.preparar()
        with self.assertRaises(ValueError):vincular(doc,['Lenguajes'],[],[refs[1]['id']])
        with self.assertRaises(ValueError):vincular(doc,['Inventado'],[],[])

    def test_pdf_conserva_ambos_campos(self):
        import pymupdf
        doc,campos,_=self.preparar()
        with pymupdf.open(stream=generar_pdf(doc),filetype='pdf') as pdf:
            texto=''.join(p.get_text() for p in pdf)
        for c in campos:self.assertIn(c,texto)


class MulticamposUITests(unittest.TestCase):
    setUp=simple.RecorridoTests.setUp
    tearDown=simple.RecorridoTests.tearDown
    abrir=simple.RecorridoTests.abrir
    paso=simple.RecorridoTests.paso

    def test_cuatro_perfiles_guardan_recuperan_y_filtran_sin_perdida(self):
        for area in ('Aprendizaje','Psicología','Comunicación','Trabajo Social'):
            with self.subTest(area=area):
                app=self.abrir(area)
                next(t for t in app.toggle if t.label=='Buscar y adaptar referentes curriculares (PDA)').set_value(True).run()
                campos=['Lenguajes','De lo Humano y lo Comunitario']
                next(m for m in app.multiselect if m.label=='Campos formativos').set_value(campos).run()
                doc=app.session_state.versiones_ficticias[-1]
                refs=[opciones(doc,c,[3])[0]['id'] for c in campos]
                next(m for m in app.multiselect if m.label.startswith('Contenido y PDA')).set_value(refs).run()
                next(t for t in app.text_input if t.label.startswith('Encontrar contenidos')).set_value('inexistentezzzz').run()
                self.assertEqual(next(m for m in app.multiselect if m.label.startswith('Contenido y PDA')).value,refs)
                next(b for b in app.button if b.label=='Incorporar referentes al borrador').click().run()
                self.assertFalse(app.exception)
                doc=app.session_state.versiones_ficticias[-1]
                self.assertEqual(doc['metadatos']['curriculo']['campos'],campos)
                self.assertEqual([r['id'] for r in doc['metadatos']['curriculo']['registros']],refs)
                self.paso(app,0)
                next(b for b in app.button if b.label=='Continuar').click().run()
                self.assertFalse(app.exception)
                next(t for t in app.toggle if t.label=='Buscar y adaptar referentes curriculares (PDA)').set_value(True).run()
                self.assertEqual(next(m for m in app.multiselect if m.label=='Campos formativos').value,campos)
                self.assertEqual(app.session_state.llamadas_ficticias,0)

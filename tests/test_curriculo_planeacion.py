import unittest
from services.curriculo import catalogo, opciones, vincular, contexto_ia, CAMPOS, EJES
from services.planeacion_modelo import crear_plantilla
from documents.planeacion import generar_pdf

def documento():
    a={'ID_Alumno':'A1','Nombre_Completo':'Alumno ficticio','ID_Escuela':'E1','Nombre_Escuela':'Escuela de prueba','CCT_Escuela':'TEST','Grado':'1','Grupo':'A','Nivel_Educativo':'Primaria'}
    d=crear_plantilla('XXIII',['A1'],[a],autor='Docente ficticia',funcion='Aprendizaje');d.update(id='test',cuenta='prueba');return d

class CurriculoTests(unittest.TestCase):
    def test_catalogo_fuentes_y_cobertura(self):
        data=catalogo()
        self.assertEqual({r['grado'] for r in data['registros']},set(range(1,7)))
        self.assertEqual({r['campo'] for r in data['registros']},set(CAMPOS))
        self.assertEqual(len(EJES),7)
        self.assertEqual({s['organismo'] for s in data['fuentes']},{'SEP'})
        for r in data['registros']:
            self.assertGreater(r['pagina_pdf'],0);self.assertTrue(r['pda']);self.assertTrue(r['contenido'])
    def test_permite_referentes_de_otro_grado_sin_cambiar_padron(self):
        opts=opciones(documento(),'Lenguajes')
        self.assertTrue(opts);self.assertEqual({r['grado'] for r in opts},set(range(1,7)))
        other=next(r for r in catalogo()['registros'] if r['grado']==2 and r['campo']=='Lenguajes')
        doc=vincular(documento(),'Lenguajes',['Inclusión'],[other['id']],adaptaciones={other['id']:{'pda':'Identifica palabras con apoyo visual','contenido':'Lectura con apoyos'}})
        self.assertEqual(doc['datos']['Alumnos'][0]['Grado'],'1')
        self.assertEqual(doc['metadatos']['curriculo']['registros'][0]['pda'],other['pda'])
        self.assertEqual(contexto_ia(doc)['referentes_por_grado'][0]['grado'],2)
        self.assertEqual(doc['metadatos']['curriculo']['adaptaciones'][other['id']]['pda'],'Identifica palabras con apoyo visual')
        self.assertEqual({r['grado'] for r in opciones(doc,'Lenguajes',[3])},{3})
    def test_ia_tiene_fuentes_y_sin_nombre(self):
        d=documento();r=opciones(d,'Lenguajes')[0]
        d=vincular(d,'Lenguajes',['Inclusión'],[r['id']])
        ctx=contexto_ia(d)
        self.assertNotIn('Alumno ficticio',str(ctx));self.assertNotIn('A1',str(ctx))
        self.assertEqual(ctx['referentes_por_grado'][0]['pda'],r['pda'])
        self.assertIn('SEGEY-USAER',[s['id'] for s in ctx['fuentes']])
    def test_pdf_incluye_referentes_y_membrete(self):
        import pymupdf
        d=documento();r=opciones(d,'Lenguajes')[0];d=vincular(d,'Lenguajes',['Inclusión'],[r['id']])
        with pymupdf.open(stream=generar_pdf(d),filetype='pdf') as pdf:
            text=''.join(p.get_text() for p in pdf)
            self.assertIn('Vinculación curricular',text);self.assertIn('Fuentes oficiales',text)
            for page in pdf:self.assertGreaterEqual(len(page.get_images()),2)
    def test_pantalla_selecciona_referente_y_previsualiza(self):
        from pathlib import Path
        from streamlit.testing.v1 import AppTest
        at=AppTest.from_file(str(Path(__file__).with_name('fixture_planeacion_panel.py'))).run(timeout=30)
        next(s for s in at.selectbox if s.label=='Alumno en atención individual').set_value('A1').run()
        next(b for b in at.button if b.label=='Crear y guardar borrador').click().run()
        next(r for r in at.radio if r.label=='Cómo quieres trabajar').set_value('Edición guiada').run()
        next(s for s in at.selectbox if s.label=='Campo formativo').set_value('Lenguajes').run()
        selector=next(m for m in at.multiselect if m.label.startswith('Contenido y PDA'))
        self.assertTrue(selector.options)
        from services.curriculo import opciones
        saved=at.session_state.fixture_versions[-1]
        first=opciones(saved,'Lenguajes')[0]['id']
        selector.set_value([first]).run()
        next(b for b in at.button if b.label=='Incorporar referentes al borrador').click().run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state.fixture_versions[-1]['metadatos']['curriculo']['registros'][0]['id'],first)
        next(b for b in at.button if b.label=='Preparar PDF').click().run()
        self.assertFalse(at.exception)
        self.assertTrue(any(b.label=='Volver a editar' for b in at.button))

if __name__=='__main__':unittest.main()

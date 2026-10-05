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
    def test_no_mezcla_grados(self):
        opts=opciones(documento(),'Lenguajes')
        self.assertTrue(opts);self.assertEqual({r['grado'] for r in opts},{1})
        other=next(r for r in catalogo()['registros'] if r['grado']==2 and r['campo']=='Lenguajes')
        with self.assertRaises(ValueError):vincular(documento(),'Lenguajes',['Inclusión'],[other['id']])
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

if __name__=='__main__':unittest.main()

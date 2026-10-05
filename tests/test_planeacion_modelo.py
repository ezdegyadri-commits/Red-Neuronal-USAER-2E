import unittest
from datetime import date
from services.planeacion_modelo import crear_plantilla, vincular_evidencias, periodo_trimestral, fase_primaria, revisar_redaccion


class PlaneacionModeloTests(unittest.TestCase):
    def setUp(self):
        self.a = {'ID_Alumno':'A1','Nombre_Completo':'Alumno ficticio','ID_Escuela':'E1','Nombre_Escuela':'Escuela de prueba','CCT_Escuela':'TEST','Grado':'1°','Grupo':'B','Maestra de Apoyo':'Docente de prueba','Condicion_Discapacidad':'Dato registrado','Nivel_Educativo':'Primaria'}
    def crear(self, formato='XXIII', ids=None, alumnos=None):
        return crear_plantilla(formato, ids or ['A1'], alumnos or [self.a], autor='Autor ficticio', funcion='Aprendizaje', fecha=date(2026,10,4))
    def test_autorrelleno_sin_inventar_necesidades(self):
        d = self.crear('XXI')
        self.assertEqual(d['datos']['CCT'],'TEST')
        self.assertEqual(d['datos']['Alumnos'][0]['Maestro de apoyo'],'Docente de prueba')
        self.assertEqual(d['datos']['Necesidades educativas específicas asociadas a'],'')
        self.assertEqual(d['tablas']['necesidades'],[])
    def test_ids_no_autorizados(self):
        with self.assertRaises(PermissionError): self.crear(ids=['A2'])
    def test_plan_individual(self):
        with self.assertRaises(ValueError): self.crear('XXI',['A1','A2'])
    def test_escuelas_no_mezcladas(self):
        b={**self.a,'ID_Alumno':'A2','ID_Escuela':'E2'}
        with self.assertRaises(ValueError): self.crear(ids=['A1','A2'],alumnos=[self.a,b])
    def test_cct_contradictorio(self):
        b={**self.a,'ID_Alumno':'A2','CCT_Escuela':'OTRO'}
        with self.assertRaises(ValueError): self.crear(ids=['A1','A2'],alumnos=[self.a,b])
    def test_social_no_es_formato_psicologia(self):
        d=self.crear('XXV')
        self.assertEqual([r['Contextos'] for r in d['tablas']['dosificacion']],['Aula regular','Escuela','Familia','Comunidad'])
        self.assertNotIn('aprendizajes',d['tablas'])
        self.assertIn('Resultados obtenidos en los diferentes contextos',d['textos'])
    def test_temporalidad_oficial(self):
        self.assertEqual(periodo_trimestral(2026,2),('2027-01-01','2027-03-31'))
        self.assertEqual(periodo_trimestral(2026,3),('2027-04-01','2027-06-30'))
    def test_fuentes_no_atribuir_visita(self):
        r=[{'ID_Alumno':'A1','ID_Escuela':'E1','texto':'Avance documentado'},
           {'ID_Alumno':'A2','ID_Escuela':'E1','texto':'Otro alumno'},
           {'ID_Escuela':'E1','tipo':'ACTA','texto':'Visita escolar'},
           {'ID_Escuela':'E2','texto':'Otra escuela'},
           {'ID_Alumno':'A1','Estado':'RETIRADO'}]
        d=vincular_evidencias(self.crear(),r)
        self.assertEqual(len(d['metadatos']['fuentes']),2)
        self.assertEqual(d['metadatos']['fuentes'][1]['alcance'],'contexto escolar')
    def test_fase_no_asumida(self):
        self.assertEqual(fase_primaria('4°'),4)
        self.assertEqual(fase_primaria('6'),5)
        self.assertIsNone(fase_primaria('sin grado'))
    def test_original_no_mutado(self):
        d=self.crear();copia=vincular_evidencias(d,[{'ID_Alumno':'A1','texto':'Prueba'}])
        self.assertEqual(d['metadatos']['fuentes'],[])
        self.assertEqual(len(copia['metadatos']['fuentes']),1)
    def test_ayuda_verbos(self):
        self.assertTrue(revisar_redaccion('Mejorar la lectura'))
        self.assertEqual(revisar_redaccion('El alumno identifica palabras con apoyo visual.'),[])


if __name__ == '__main__': unittest.main()

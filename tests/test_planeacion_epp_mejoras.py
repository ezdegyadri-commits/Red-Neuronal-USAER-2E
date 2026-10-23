import unittest
from services.epp_analisis import identificar_instrumento_y_areas, distribuir_hallazgos_en_epp, proponer_nee_segey, incorporar_prueba_a_epp
from services.planeacion_compartida import excluir_alumno_grupal, restaurar_alumno_grupal, ampliar_matricula
from services.planeacion_modalidad import guia_grupal
import pandas as pd

class TestEPPAnalisisYPlaneacionMejoras(unittest.TestCase):
    def test_identificar_instrumento_wisc(self):
        texto = "Se aplicó la prueba WISC-IV. En comprensión verbal y memoria de trabajo obtuvo un CI de 85."
        res = identificar_instrumento_y_areas(texto, 'Psicología')
        self.assertTrue(len(res) >= 1)
        self.assertIn('WISC-IV', res[0]['instrumento'])
        self.assertIn('3.5. Cociente intelectual', res[0]['campos'])

    def test_identificar_instrumento_bender(self):
        texto = "En la prueba visomotora de Bender se observa distorsión de la forma e integración motriz fina por debajo de su edad cronológica."
        res = identificar_instrumento_y_areas(texto, 'Psicología')
        self.assertTrue(len(res) >= 1)
        self.assertIn('Bender', res[0]['instrumento'])

    def test_distribuir_hallazgos(self):
        texto = "Atención: Presenta dificultades de concentración y fácil distracción.\n\nMemoria: Muestra adecuada memoria de trabajo."
        campos = {'3.1. Atención': '', '3.2. Memoria': ''}
        nuevos = distribuir_hallazgos_en_epp('Psicología', texto, campos)
        self.assertIn('distracción', nuevos['3.1. Atención'])
        self.assertIn('memoria de trabajo', nuevos['3.2. Memoria'])

    def test_proponer_nee_segey_formula(self):
        doc = {
            'partes': {
                'Psicología': {
                    'contenido': {
                        'campos': {'3.1. Atención': 'Dificultades severas en atención sostenida y concentración.'},
                        'sintesis': 'Requiere pausas y apoyos visuales.'
                    }
                },
                'Aprendizaje': {
                    'contenido': {
                        'campos': {'5.1. Competencia curricular': 'En proceso de adquisición de la lectura y escritura.'},
                        'sintesis': 'Lectura alfabética inicial.'
                    }
                },
                'Comunicación': {
                    'contenido': {
                        'campos': {'4.1. Lenguaje oral: fonológico': 'Sustitución de fonemas /r/ y /s/.'},
                        'sintesis': 'Articulación en desarrollo.'
                    }
                },
                'Trabajo Social': {
                    'contenido': {
                        'campos': {'6.2. Contexto familiar': 'Familia comprometida con el proceso educativo.'},
                        'sintesis': 'Apoyo en casa.'
                    }
                }
            }
        }
        res = proponer_nee_segey(doc)
        self.assertIn('campos', res)
        self.assertIn('nee', res)
        self.assertEqual(len(res['nee']), 5)
        # Cada NEE debe comenzar con 'Necesita ' seguido de verbo observable
        for row in res['nee']:
            self.assertTrue(row['NEE'].startswith('Necesita '), f"NEE no sigue formato SEGEY: {row['NEE']}")

    def test_excluir_y_restaurar_alumno_grupal(self):
        doc = {
            'datos': {
                'ID_Escuela': 'ESC01',
                'Escuela regular': 'Escuela Primaria',
                'Curso escolar': '2026-2027',
                'Trimestre': 1,
                'Función': 'Aprendizaje',
                'Alumnos': [
                    {'ID_Alumno': '101', 'Nombre del alumno': 'Juan Perez', 'Grado': '1', 'Grupo': 'A', 'Tipo_Atencion': 'Grupal', 'Condición': 'TEA'},
                    {'ID_Alumno': '102', 'Nombre del alumno': 'Francisco Lopez', 'Grado': '1', 'Grupo': 'A', 'Tipo_Atencion': 'Grupal', 'Condición': 'TEA'},
                ]
            },
            'metadatos': {
                'modalidad_planeacion': 'grupal',
                'guia_grupal_manual': {'filas': []}
            }
        }
        padron = pd.DataFrame([
            {'ID_Alumno': '101', 'Nombre_Completo': 'Juan Perez', 'Grado': '1', 'Grupo': 'A', 'Tipo_Atencion': 'Grupal', 'ID_Escuela': 'ESC01', 'Estatus': 'ACTIVO'},
            {'ID_Alumno': '102', 'Nombre_Completo': 'Francisco Lopez', 'Grado': '1', 'Grupo': 'A', 'Tipo_Atencion': 'Grupal', 'ID_Escuela': 'ESC01', 'Estatus': 'ACTIVO'},
        ])
        
        # Excluir Francisco (102)
        doc = excluir_alumno_grupal(doc, '102', padron)
        self.assertIn('102', doc['metadatos']['alumnos_excluidos_grupal'])
        alumnos_ids = [a['ID_Alumno'] for a in doc['datos']['Alumnos']]
        self.assertNotIn('102', alumnos_ids)
        self.assertIn('101', alumnos_ids)

        # guia_grupal no debe contener a 102
        guia = guia_grupal(doc)
        filas_ids = [r['ID_Alumno'] for r in guia['filas']]
        self.assertNotIn('102', filas_ids)
        self.assertIn('101', filas_ids)

        # Reincorporar Francisco (102)
        doc = restaurar_alumno_grupal(doc, '102', padron)
        self.assertNotIn('102', doc['metadatos'].get('alumnos_excluidos_grupal', []))
        alumnos_ids_restaurados = [a['ID_Alumno'] for a in doc['datos']['Alumnos']]
        self.assertIn('102', alumnos_ids_restaurados)

    def test_incorporar_prueba_a_epp(self):
        doc = {'alumno': '101', 'ciclo': '2026-2027', 'partes': {}}
        texto = "Prueba Visomotora Bender:\nPresenta dificultades significativas en percepción visomotriz e integración de la forma. Coordinación motriz fina por debajo de su edad cronológica."
        res = incorporar_prueba_a_epp(doc, 'Psicología', texto)
        self.assertIn('Prueba Visomotora Bender', res['instrumento'])
        self.assertTrue(len(res['campos_afectados']) > 0)
        psi_cont = doc['partes']['Psicología']['contenido']
        self.assertIn('Bender', psi_cont['instrumentos'])
        self.assertEqual(len(psi_cont['evaluaciones']), 1)
        # Verifica propuesta de conclusión y NEE generada
        self.assertIn('Conclusión', doc['partes'])
        concl_cont = doc['partes']['Conclusión']['contenido']
        self.assertTrue(len(concl_cont['nee']) == 5)

if __name__ == '__main__':
    unittest.main()

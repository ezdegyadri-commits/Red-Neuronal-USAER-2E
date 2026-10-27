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
        self.assertIn('7.1. Conclusión', res['campos'])
        self.assertTrue(len(res['campos']['7.1. Conclusión']) > 100)
        self.assertIn('evaluación psicopedagógica interdisciplinaria', res['campos']['7.1. Conclusión'])
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

    def test_ensamblar_epp_completa_desde_documento(self):
        from services.epp_analisis import ensamblar_epp_completa_desde_documento
        doc = {'alumno': '101', 'ciclo': '2026-2027', 'partes': {}}
        texto_scan = """
        INFORME DE EVALUACIÓN PSICOPEDAGÓGICA
        
        2. DATOS SOBRE EL DESARROLLO Y CONTEXTO FAMILIAR
        Embarazo normoevolutivo sin complicaciones. Parto a término. Familia nuclear compuesta por padre, madre y dos hermanos. Dinámica familiar participativa y con apoyo en el hogar.
        
        3. ÁREA INTELECTUAL Y CONDUCTA ADAPTATIVA
        Se aplicó la Escala Wechsler WISC-IV y Test Bender. En atención sostenida presenta periodos breves de focalización. Muestra adecuada memoria de trabajo pero requiere apoyos visuales. Razonamiento lógico en nivel medio.
        
        4. ÁREA COMUNICATIVA Y LINGÜÍSTICA
        En lenguaje oral fonológico presenta sustitución de fonemas en habla espontánea. Intención comunicativa adecuada y comprensión receptiva conservada.
        
        5. COMPETENCIA CURRICULAR Y ESTILO DE APRENDIZAJE
        En lectura y escritura funcional se encuentra en proceso alfabético inicial. Canal de aprendizaje preponderantemente visual y kinestésico.
        
        7. CONCLUSIÓN Y DETERMINACIÓN DE NEE
        • Necesita focalizar y mantener la atención en consignas académicas mediante apoyos visuales.
        • Necesita consolidar la alfabetización inicial y la comprensión lectora funcional.
        • Necesita afianzar la pronunciación de fonemas en lenguaje oral.
        """
        res = ensamblar_epp_completa_desde_documento(doc, texto_scan, 'EPP_Escaneada_Juan.pdf')
        self.assertIn('Aprendizaje', res['areas_ensambladas'])
        self.assertIn('Psicología', res['areas_ensambladas'])
        self.assertIn('Comunicación', res['areas_ensambladas'])
        self.assertIn('Trabajo Social', res['areas_ensambladas'])
        self.assertIn('Conclusión y NEE', res['areas_ensambladas'])
        self.assertGreater(res['campos_modificados_totales'], 5)
        self.assertGreaterEqual(res['total_nee'], 3)
        self.assertGreaterEqual(res['total_bap'], 1)

        partes = doc['partes']
        self.assertIn('Psicología', partes)
        self.assertIn('WISC-IV', partes['Psicología']['contenido']['instrumentos'])
        self.assertTrue(len(partes['Psicología']['contenido']['campos']['3.1. Atención']) > 0)

        self.assertIn('Trabajo Social', partes)
        self.assertTrue(len(partes['Trabajo Social']['contenido']['campos']['2.1. Embarazo']) > 0)

        self.assertIn('Comunicación', partes)
        self.assertTrue(len(partes['Comunicación']['contenido']['campos']['4.1. Lenguaje oral: fonológico']) > 0)

        self.assertIn('Aprendizaje', partes)
        self.assertTrue(len(partes['Aprendizaje']['contenido']['campos']['5.2. Estilo de aprendizaje']) > 0)

        self.assertIn('Conclusión', partes)
        self.assertTrue(len(partes['Conclusión']['contenido']['nee']) >= 3)

    def test_insertar_fila_planeacion(self):
        from services.planeacion_formato import insertar_fila
        doc = {
            'datos': {
                'Acciones': [
                    {'Acciones': 'Acción 1', 'Objetivo': 'Obj 1', 'Fecha': '2026-10-01'},
                    {'Acciones': 'Acción 2', 'Objetivo': 'Obj 2', 'Fecha': '2026-10-02'}
                ]
            }
        }
        # Insertar al inicio (arriba de fila 0)
        doc = insertar_fila(doc, 'Acciones', 0)
        self.assertEqual(len(doc['datos']['Acciones']), 3)
        self.assertEqual(doc['datos']['Acciones'][0]['Acciones'], '')
        self.assertEqual(doc['datos']['Acciones'][1]['Acciones'], 'Acción 1')

        # Insertar abajo de fila 1 (índice 2)
        doc = insertar_fila(doc, 'Acciones', 2)
        self.assertEqual(len(doc['datos']['Acciones']), 4)

    def test_escuela_alias_elvira_parra_y_limpieza_abdiel(self):
        from services.planeacion_matricula import resolver_escuela, ALIASES_ESCUELAS, preparar
        self.assertEqual(resolver_escuela('Elvira Parra'), 'ESC-005')
        self.assertEqual(resolver_escuela('  ELVIRA PARRA  '), 'ESC-005')
        self.assertEqual(resolver_escuela('Escuela Primaria Elvira Parra Avila'), 'ESC-005')

        # Probar limpieza robusta en DataFrame
        raw_df = pd.DataFrame([
            {'ID_Alumno': ' 1001 ', 'Nombre_Completo': '  Abdiel Chan Cime  ', 'Nombre_Escuela': ' Elvira Parra ', 'ID_Escuela': 'ESC-005'},
            {'ID_Alumno': '1002', 'Nombre_Completo': 'JUAN PEREZ', 'Nombre_Escuela': 'ESC-001', 'ID_Escuela': 'ESC-001'}
        ])
        clean_df = preparar(raw_df)
        self.assertEqual(clean_df.loc[0, 'Nombre_Completo'], 'ABDIEL CHAN CIME')
        self.assertEqual(clean_df.loc[0, 'ID_Alumno'], '1001')
        self.assertEqual(clean_df.loc[0, 'ID_Escuela'], 'ESC-005')

    def test_asistente_redaccion_ia_epp(self):
        from ai.epp import redactar_apartado_epp
        texto = redactar_apartado_epp(
            apartado='3.1. Atención',
            notas='Periodos breves de concentración, requiere pausas activas y estímulos visuales',
            area='Psicología',
            alumno_contexto={'Nombre_Completo': 'Abdiel Chan Cime', 'Grado': '2', 'Grupo': 'B'}
        )
        self.assertTrue(len(texto) > 40)
        self.assertTrue('atención' in texto.lower() or 'concentración' in texto.lower())

    def test_exclusion_no_se_requiere_en_pdf(self):
        from documents.epp import generar_pdf
        doc = {
            'id': 'EPP-TEST-01',
            'alumno': '1001',
            'ciclo': '2026-2027',
            'metadatos': {
                'no_se_requiere': {
                    '4.1. Lenguaje oral: fonológico': True,
                    '4.3. Coordinación motriz fina': True
                }
            },
            'partes': {
                'META': {'estado': 'VIGENTE'},
                'Aprendizaje': {
                    'autor': 'Maestra Apoyo',
                    'contenido': {
                        'validada': True,
                        'generales': {'Motivo de evaluación': 'Evaluación integral inicial'},
                        'campos': {'5.1. Competencia curricular': 'En proceso de alfabetización'}
                    }
                },
                'Comunicación': {
                    'autor': 'Maestro Comunicación',
                    'contenido': {
                        'validada': True,
                        'no_se_requiere': {'4.1. Lenguaje oral: fonológico': True},
                        'campos': {
                            '4.1. Lenguaje oral: fonológico': 'NO DEBE APARECER',
                            '4.1. Comprensión receptiva': 'Comprensión contextual adecuada'
                        }
                    }
                },
                'Psicología': {
                    'autor': 'Psicóloga',
                    'contenido': {
                        'validada': True,
                        'campos': {'3.1. Atención': 'Atención selectiva conservada'}
                    }
                },
                'Trabajo Social': {
                    'autor': 'Trabajador Social',
                    'contenido': {
                        'validada': True,
                        'campos': {'6.2. Contexto familiar': 'Apoyo parental constante'}
                    }
                },
                'Conclusión': {
                    'autor': 'Equipo Colegiado',
                    'contenido': {
                        'validada': True,
                        'campos': {'7.1. Conclusión': 'Conclusión acordada por el equipo.'},
                        'nee': [{'NEE': 'Necesita apoyos visuales', 'Prioridad': 'Alta'}],
                        'bap': [{'BAP': 'Metodológica', 'Contexto': 'Escolar'}]
                    }
                }
            }
        }
        student = {
            'ID_Alumno': '1001',
            'Nombre_Completo': 'Abdiel Chan Cime',
            'Grado': '2',
            'Grupo': 'B',
            'Nombre_Escuela': 'Elvira Parra',
            'CCT_Escuela': '31EPR0000Z'
        }
        pdf_bytes = generar_pdf(doc, student)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 1000)

        # Verificar que el texto excluido no esté presente en el PDF generado
        import fitz
        pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        full_text = ""
        for page in pdf_doc:
            full_text += page.get_text()
        self.assertNotIn('NO DEBE APARECER', full_text)
        self.assertIn('Comprensión contextual adecuada', full_text)

    def test_rbac_granular_epp(self):
        from ui.epp import _puede_editar
        # 1. Datos Generales: solo TRABAJO SOCIAL o APOYO
        self.assertTrue(_puede_editar('Motivo de evaluación', 'generales', 'Aprendizaje', 'Aprendizaje', False, False, 'MAESTRO DE APOYO'))
        self.assertTrue(_puede_editar('Motivo de evaluación', 'generales', 'Aprendizaje', 'Trabajo Social', False, False, 'TRABAJO SOCIAL'))
        self.assertFalse(_puede_editar('Motivo de evaluación', 'generales', 'Aprendizaje', 'Psicología', False, False, 'PSICOLOGO'))
        self.assertFalse(_puede_editar('Motivo de evaluación', 'generales', 'Aprendizaje', 'Comunicación', False, False, 'MAESTRO DE COMUNICACION'))

        # 2. Temporalidad y Motricidad: APOYO o COMUNICACION
        self.assertTrue(_puede_editar('4.1. Orientación temporal', None, 'Comunicación', 'Aprendizaje', False, False, 'MAESTRO DE APOYO'))
        self.assertTrue(_puede_editar('4.3. Coordinación motriz fina', None, 'Comunicación', 'Comunicación', False, False, 'COMUNICACION'))
        self.assertTrue(_puede_editar('4.3. Coordinación motriz gruesa', None, 'Comunicación', 'Aprendizaje', False, False, 'APOYO'))
        self.assertFalse(_puede_editar('4.3. Coordinación motriz fina', None, 'Comunicación', 'Psicología', False, False, 'PSICOLOGA'))

        # 3. Director siempre puede editar todo
        self.assertTrue(_puede_editar('4.3. Coordinación motriz fina', None, 'Comunicación', 'Dirección', False, True, 'DIRECTOR'))

if __name__ == '__main__':
    unittest.main()



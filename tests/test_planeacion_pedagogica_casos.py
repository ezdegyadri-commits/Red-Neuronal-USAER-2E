"""Pruebas pedagógicas basadas en los casos de validación de FASE 7.

Validación de Zona de Desarrollo Próximo (ZDP), desvinculación de grado nominal,
estructura de 3 momentos, andamiaje, variantes multinivel y continuidad pedagógica.
"""
import unittest
from datetime import date
from copy import deepcopy
from unittest.mock import patch
from services import planeacion as s, planeacion_generacion as g
from services.planeacion_modelo import crear_plantilla
from ai.planeacion_completa import solicitud_completa, validar_completa
from services.planeacion_nee import resumir_plan_previo


class CasosPedagogicosTests(unittest.TestCase):

    def setUp(self):
        self.auth = patch.object(s, 'autorizar', return_value={'cuenta': 'cuenta-prueba', 'director': False})
        self.auth.start()
        self.addCleanup(self.auth.stop)

    def crear_caso(self, aid, nombre, grado, antecedentes_texto, enfoque=''):
        alumno = {
            'ID_Alumno': aid,
            'Nombre_Completo': nombre,
            'ID_Escuela': 'ESC-1',
            'Nombre_Escuela': 'Primaria Benito Juárez',
            'CCT_Escuela': '31EPR0001Z',
            'Grado': str(grado),
            'Grupo': 'A',
            'Tipo_Atencion': 'Grupal'
        }
        doc = crear_plantilla('XXIII', [aid], [alumno], autor='Docente Prueba', funcion='Aprendizaje', fecha=date(2026, 10, 20))
        doc.update(id=f'doc-{aid}', cuenta='cuenta-prueba', revision='', observaciones_director='')
        doc['metadatos']['fuentes'] = [{
            'tipo': 'EPP',
            'alumno': aid,
            'referencia': 'E1',
            'fecha': '2026-10-15',
            'registro': f'epp-{aid}',
            'parte': 'Pedagogía',
            'texto': antecedentes_texto,
            'vinculo_verificado': True,
            'alcance': 'individual'
        }]
        doc['metadatos'].update(
            resumen_educativo=f"Evaluación psicopedagógica: {antecedentes_texto}",
            necesidades_confirmadas='',
            referente_curricular=''
        )
        if enfoque:
            doc['metadatos']['configuracion_generacion'] = {'enfoque': enfoque}
        return doc

    def test_caso1_alumno_quinto_grado_lectura_inicial_presilabica(self):
        """Caso 1: Alumno de 5.° grado con habilidades iniciales de lectoescritura."""
        doc = self.crear_caso(
            'AL-5P',
            'Estudiante Ficticio Quinto',
            5,
            'Nivel de conceptualización de la lectoescritura: Presilábico. Identifica vocales aisladas con tarjetas ilustradas. '
            'Requiere mediación visual con letras móviles y objetos concretos para correspondencia grafofonética.'
        )
        ajustes = {**g.configuracion(doc), 'inicio': '2026-10-21', 'grado_referencia': 1}
        solicitud = g.preparar_solicitud(doc, ajustes)
        prompt = solicitud_completa(
            solicitud['resumen'], doc['formato'], doc['datos']['Función'],
            solicitud['contexto'], solicitud['ajustes'], solicitud['aliases'], solicitud['evidencias']
        )
        # Debe contener la directriz de ZDP y no infantilizar
        self.assertIn('ZONA DE DESARROLLO PRÓXIMO', prompt)
        self.assertIn('presilábico', prompt.lower())
        self.assertIn('NO infantilices', prompt)
        self.assertNotIn('Estudiante Quinto Presilábico', prompt)

    def test_caso2_alumno_tercero_letras_aisladas_sin_integrar_silabas(self):
        """Caso 2: Alumno de 3.° que identifica letras aisladas pero no integra sílabas."""
        doc = self.crear_caso(
            'AL-3S',
            'Estudiante Tercero Fonológico',
            3,
            'Identifica grafías aisladas del abecedario, pero aún no logra síntesis silábica. '
            'Responde favorablemente al modelado fónico con palmadas y rimas.'
        )
        ajustes = {**g.configuracion(doc), 'inicio': '2026-10-21', 'grado_referencia': 1}
        solicitud = g.preparar_solicitud(doc, ajustes)
        resumen = solicitud['resumen']
        self.assertIn('grafías aisladas', resumen)
        self.assertIn('síntesis silábica', resumen)

    def test_caso3_alumno_apoyos_comunicacion_organizacion(self):
        """Caso 3: Alumno que requiere apoyos en comunicación aumentativa y estructuración."""
        doc = self.crear_caso(
            'AL-COM',
            'Estudiante Comunicación Alternativa',
            2,
            'Requiere tablero de comunicación aumentativa con pictogramas para expresar elecciones. '
            'Estructuración visual de la rutina con tarjetas anticipatorias.'
        )
        ajustes = {**g.configuracion(doc), 'inicio': '2026-10-21', 'apoyos': 'Tablero de pictogramas SAAC'}
        solicitud = g.preparar_solicitud(doc, ajustes)
        self.assertIn('pictogramas', solicitud['ajustes']['apoyos'])

    def test_caso4_alumno_conteo_sin_operaciones_basicas(self):
        """Caso 4: Alumno que reconoce números 1-50 pero sin noción de operaciones básicas."""
        doc = self.crear_caso(
            'AL-NUM',
            'Estudiante Conteo Concreto',
            4,
            'Rango de conteo uno a uno hasta 30 con material concreto. '
            'Aún en desarrollo de la noción de adición y sustracción; requiere apoyo con regletas o fichas.'
        )
        ajustes = {**g.configuracion(doc), 'inicio': '2026-10-21', 'grado_referencia': 1}
        solicitud = g.preparar_solicitud(doc, ajustes)
        prompt = solicitud_completa(
            solicitud['resumen'], doc['formato'], doc['datos']['Función'],
            solicitud['contexto'], solicitud['ajustes'], solicitud['aliases'], solicitud['evidencias']
        )
        self.assertIn('conteo', prompt.lower())

    def test_caso5_continuidad_sin_saturacion_json(self):
        """Caso 5: Continuidad pedagógica desde un plan previo usando resumen pedagógico compacto."""
        plan_previo = {
            'id': 'plan-ant',
            'formato': 'XXIII',
            'metadatos': {
                'necesidades_confirmadas': 'Necesita fortalecer correspondencia fonema-grafema.',
                'equipo': {'sesiones': [{'actividad': 'Actividad con tarjetas de asociación visual.'}]}
            },
            'tablas': {
                'aprendizajes': [{
                    'Aprendizaje y/u objetivo': 'Identificar el sonido inicial de palabras cotidianas.',
                    'Apoyos o ajustes': 'Apoyo visual con alfabeto ilustrado.'
                }],
                'dosificacion': [{'Actividades': 'Juego de mesa fonológico con dados y fichas.'}]
            }
        }
        resumen_plan = resumir_plan_previo(plan_previo)
        self.assertIn('Planeación anterior (XXIII)', resumen_plan)
        self.assertIn('Necesidades previas: Necesita fortalecer correspondencia fonema-grafema', resumen_plan)
        self.assertIn('Objetivo previo: Identificar el sonido inicial', resumen_plan)
        self.assertIn('Apoyos previos: Apoyo visual con alfabeto ilustrado', resumen_plan)
        # Comprobar que no contiene brackets de JSON crudo
        self.assertNotIn('{"tablas"', resumen_plan)

    def test_validacion_actividad_multinivel_y_tres_momentos(self):
        """Verifica que el contrato acepta actividades estructuradas con inicio, desarrollo, cierre y variantes."""
        doc = self.crear_caso('AL-VAL', 'Estudiante Validación', 2, 'Evaluación inicial regular.')
        req = g.preparar_solicitud(doc, {**g.configuracion(doc), 'inicio': '2026-10-21'})
        respuesta = {
            'observaciones': 'Propuesta adaptada a la Zona de Desarrollo Próximo.',
            'faltantes': [],
            'sugerencia_familia': 'Orientar con un juego de palabras en casa.',
            'unidades': [{
                'necesidad': 'Necesita fortalecer el reconocimiento de sonido inicial.',
                'objetivo': 'El alumno identifica el sonido inicial de cinco palabras con apoyo de imágenes.',
                'descriptor': 'El alumno señala la imagen que inicia con el fonema indicado.',
                'actividad': (
                    'Inicio: anticipar la actividad mostrando 3 tarjetas con objetos del aula (5 min). '
                    'Desarrollo: el docente modela el sonido /m/ y solicita buscar objetos que inicien igual con apoyo de fichas (25 min). '
                    'Cierre: demostración individual seleccionando la tarjeta correcta (10 min). '
                    'Variante apoyo: usar solo 2 opciones con contraste fonológico alto. '
                    'Variante reto: nombrar una palabra adicional sin tarjeta.'
                ),
                'contexto': 'Aula regular',
                'apoyos': 'Tarjetas ilustradas de alta visibilidad y modelado fónico.',
                'recursos': 'Tarjetas de objetos cotidianos del aula y fichas de colores.',
                'evaluacion': 'Escala de valoración: registrar acierto autónomo o con modelado al cierre de la sesión.',
                'fundamento': 'Alineado al PDA de Fase 2/3 y al expediente pedagógico.',
                'evidencias': list(req['evidencias']),
                'fuentes': ['SEGEY-USAER'],
                'referentes': [r['id'] for r in req['contexto'].get('referentes_por_grado', [])][:1],
                'destinatarios': list(req['aliases']),
                'competencias': []
            }]
        }
        validada = validar_completa(respuesta, doc['formato'], 'Aprendizaje', req['contexto'], req['aliases'], req['evidencias'])
        self.assertEqual(len(validada['unidades']), 1)
        self.assertIn('Variante apoyo', validada['unidades'][0]['actividad'])


if __name__ == '__main__':
    unittest.main()

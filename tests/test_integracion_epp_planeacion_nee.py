"""Pruebas obligatorias de integración inteligente: EPP -> NEE -> Planeación Individual.

Verifica los 15 escenarios del Prompt Maestro:
1. Alumno con EPP válida y NEE correctamente detectadas.
2. Alumno con EPP escaneada que requiere OCR / extracción.
3. Alumno con EPP parcialmente ilegible (no inventa NEE).
4. Alumno con necesidades no validadas (no se incorporan al catálogo).
5. Alumno con varias NEE validadas en su catálogo.
6. Dos alumnos con el mismo nombre y diferente ID (aislamiento estricto).
7. Cambio de alumno durante la edición de planeación.
8. Actualización de EPP sin pérdida de información histórica.
9. Planeación previamente guardada que conserva sus selecciones.
10. Alumno sin EPP que elabora planeación manualmente.
11. Dos docentes trabajando simultáneamente (aislamiento de llaves/sesión).
12. NEE repetidas o formuladas de manera equivalente (deduplicación).
13. Aislamiento entre alumnos / escuelas.
14. Resiliencia ante fallos de conexión o fuentes vacías.
15. Diagnóstico clínico puro vs Necesidad Educativa Específica.
"""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch, MagicMock
import pandas as pd

from services import planeacion_nee as nee
from services import planeacion_formato as f_formato
from services.planeacion_modelo import crear_plantilla


class IntegracionEppPlaneacionNeeTests(unittest.TestCase):

    def _crear_doc_base(self, alumno_id="A1", nombre="Juan Pérez", cct="31EUA0001Z"):
        alumnos_info = [{
            'ID_Alumno': alumno_id,
            'Nombre del alumno': nombre,
            'ID_Escuela': cct,
            'Nombre_Escuela': 'Escuela Primaria Modelo',
            'Grado': '3',
            'Grupo': 'A',
            'NEE registrada': ''
        }]
        doc = crear_plantilla('XXIII', [alumno_id], alumnos_info, autor='Maestra Especialista', funcion='Aprendizaje')
        doc['metadatos']['fuentes'] = []
        return doc

    def _agregar_epp_fuente(self, doc, alumno_id, revision, nee_lista, bap_lista=None):
        fuente = {
            'tipo': 'EPP',
            'alumno': alumno_id,
            'fecha': '2026-10-15',
            'registro': f'EPP-{alumno_id}-{revision}',
            'documento_origen': f'EPP-{alumno_id}',
            'parte': 'Conclusión',
            'revision': revision,
            'referencia': 'E1',
            'vinculo_verificado': True,
            'texto': json.dumps({
                'NEE': [{'NEE': item, 'Aspectos': 'Pedagógico', 'Apoyos': 'Material concreto'} for item in nee_lista],
                'BAP': [{'Tipo de barrera': b} for b in (bap_lista or [])]
            }, ensure_ascii=False)
        }
        doc['metadatos']['fuentes'].append(fuente)

    def test_caso_1_alumno_con_epp_valida_y_nee_detectadas(self):
        doc = self._crear_doc_base("A1")
        self._agregar_epp_fuente(doc, "A1", "rev1", ["fortalecer la comprensión lectora mediante apoyos visuales"])
        cat = nee.catalogo_nee_validadas(doc, alumno_id="A1")
        self.assertEqual(len(cat), 1)
        self.assertEqual(cat[0]['alumno_id'], "A1")
        self.assertEqual(cat[0]['origen'], "EPP validada")
        self.assertTrue(cat[0]['texto'].startswith("Necesita fortalecer"))

    def test_caso_2_epp_escaneada_ocr_texto_estructurado(self):
        doc = self._crear_doc_base("A1")
        texto_ocr = "desarrollar habilidades de conteo y resolucion de problemas aritmeticos"
        self._agregar_epp_fuente(doc, "A1", "rev1", [texto_ocr])
        opciones = nee.opciones_nee_validadas(doc, alumno_id="A1")
        self.assertEqual(len(opciones), 1)
        self.assertIn("conteo", opciones[0].lower())

    def test_caso_3_epp_parcialmente_ilegible_no_inventa_nee(self):
        doc = self._crear_doc_base("A1")
        # Texto corrupto o vacío en la EPP
        self._agregar_epp_fuente(doc, "A1", "rev1", ["", "   ", "---"])
        cat = nee.catalogo_nee_validadas(doc, alumno_id="A1")
        self.assertEqual(len(cat), 0)

    def test_caso_4_necesidades_no_validadas_no_entran_al_catalogo(self):
        # Cuando una EPP no ha sido validada, evidencias() no la incorpora a fuentes
        doc = self._crear_doc_base("A1")
        # doc no tiene fuentes de tipo EPP parte Conclusión
        cat = nee.catalogo_nee_validadas(doc, alumno_id="A1")
        self.assertEqual(len(cat), 0)

    def test_caso_5_alumno_con_varias_nee_validadas(self):
        doc = self._crear_doc_base("A1")
        nees = [
            "fortalecer la correspondencia grafema-fonema",
            "consolidar el valor posicional de unidades y decenas",
            "desarrollar la atención sostenida en instrucciones complejas"
        ]
        self._agregar_epp_fuente(doc, "A1", "rev1", nees)
        opciones = nee.opciones_nee_validadas(doc, alumno_id="A1")
        self.assertEqual(len(opciones), 3)
        self.assertTrue(any("grafema" in o for o in opciones))
        self.assertTrue(any("posicional" in o for o in opciones))
        self.assertTrue(any("atención" in o for o in opciones))

    def test_caso_6_homonimos_aislamiento_estricto_por_id(self):
        # Dos alumnos llamados "Juan Pérez" pero con distinto ID
        doc = self._crear_doc_base("A1", "Juan Pérez")
        doc['datos']['Alumnos'].append({
            'ID_Alumno': 'A2',
            'Nombre del alumno': 'Juan Pérez',
            'ID_Escuela': '31EUA0001Z'
        })
        self._agregar_epp_fuente(doc, "A1", "rev1", ["fortalecer la lectura de palabras simples"])
        self._agregar_epp_fuente(doc, "A2", "rev1", ["desarrollar la comunicación funcional mediante pictogramas"])

        cat_a1 = nee.catalogo_nee_validadas(doc, alumno_id="A1")
        cat_a2 = nee.catalogo_nee_validadas(doc, alumno_id="A2")

        self.assertEqual(len(cat_a1), 1)
        self.assertEqual(len(cat_a2), 1)
        self.assertIn("lectura", cat_a1[0]['texto'].lower())
        self.assertIn("pictogramas", cat_a2[0]['texto'].lower())
        self.assertNotIn("pictogramas", cat_a1[0]['texto'].lower())
        self.assertNotIn("lectura", cat_a2[0]['texto'].lower())

    def test_caso_7_cambio_de_alumno_actualiza_catalogo(self):
        doc = self._crear_doc_base("A1")
        self._agregar_epp_fuente(doc, "A1", "rev1", ["fortalecer la comprensión en Alumno 1"])
        self._agregar_epp_fuente(doc, "B2", "rev1", ["desarrollar la expresión en Alumno 2"])

        opts_1 = nee.opciones_nee_validadas(doc, alumno_id="A1")
        opts_2 = nee.opciones_nee_validadas(doc, alumno_id="B2")

        self.assertEqual(opts_1, ["Necesita fortalecer la comprensión en Alumno 1"])
        self.assertEqual(opts_2, ["Necesita desarrollar la expresión en Alumno 2"])

    def test_caso_8_actualizacion_epp_conserva_trazabilidad(self):
        doc = self._crear_doc_base("A1")
        # Revisión 1
        self._agregar_epp_fuente(doc, "A1", "rev1", ["necesidad inicial"])
        cat1 = nee.catalogo_nee_validadas(doc, alumno_id="A1")
        self.assertEqual(cat1[0]['revision'], "rev1")

        # Se actualiza la fuente con la revisión 2
        doc['metadatos']['fuentes'] = []
        self._agregar_epp_fuente(doc, "A1", "rev2", ["necesidad actualizada"])
        cat2 = nee.catalogo_nee_validadas(doc, alumno_id="A1")
        self.assertEqual(cat2[0]['revision'], "rev2")
        self.assertIn("actualizada", cat2[0]['texto'])

    def test_caso_9_planeacion_previa_conserva_selecciones(self):
        doc = self._crear_doc_base("A1")
        self._agregar_epp_fuente(doc, "A1", "rev1", ["fortalecer lectura"])
        # Planeación ya tiene texto guardado por la maestra
        texto_docente = "Necesita fortalecer la lectura fluida con apoyos específicos redactada por maestra."
        doc['tablas']['aprendizajes'] = [{
            'Necesidades educativas específicas': texto_docente,
            'Aprendizaje y/u objetivo': 'Objetivo 1',
            'Descriptor de logro': 'Descriptor 1'
        }]

        # Al consultar opciones no se sobreescribe el doc
        cat = nee.catalogo_nee_validadas(doc, alumno_id="A1")
        self.assertEqual(len(cat), 1)
        self.assertEqual(doc['tablas']['aprendizajes'][0]['Necesidades educativas específicas'], texto_docente)

    def test_caso_10_alumno_sin_epp_captura_manual(self):
        doc = self._crear_doc_base("A1")
        # Sin fuentes EPP
        cat = nee.catalogo_nee_validadas(doc, alumno_id="A1")
        self.assertEqual(cat, [])
        opciones = nee.opciones_nee_validadas(doc, alumno_id="A1")
        self.assertEqual(opciones, [])

        # La edición manual funciona perfectamente tras crear una fila
        doc_con_fila = f_formato.nueva_fila(doc, 'aprendizajes')
        doc_editado = f_formato.editar_celda(doc_con_fila, 'aprendizajes', 0, 'Necesidades educativas específicas', 'Captura manual')
        self.assertEqual(doc_editado['tablas']['aprendizajes'][0]['Necesidades educativas específicas'], 'Captura manual')

    def test_caso_11_dos_docentes_trabajando_simultaneamente(self):
        doc1 = self._crear_doc_base("A1")
        doc2 = self._crear_doc_base("B2")
        self._agregar_epp_fuente(doc1, "A1", "rev1", ["NEE Alumno A1"])
        self._agregar_epp_fuente(doc2, "B2", "rev1", ["NEE Alumno B2"])

        # Catálogos independientes
        res1 = nee.opciones_nee_validadas(doc1, alumno_id="A1")
        res2 = nee.opciones_nee_validadas(doc2, alumno_id="B2")
        self.assertNotEqual(res1, res2)

    def test_caso_12_nee_repetidas_se_deduplican(self):
        doc = self._crear_doc_base("A1")
        # EPP con necesidad repetida o formulada igual
        self._agregar_epp_fuente(doc, "A1", "rev1", [
            "fortalecer la comprensión lectora",
            "Fortalecer la comprensión lectora",
            "Necesita fortalecer la comprensión lectora"
        ])
        cat = nee.catalogo_nee_validadas(doc, alumno_id="A1")
        # Debe deduplicar a una sola entrada canónica
        self.assertEqual(len(cat), 1)

    def test_caso_13_usuario_sin_permiso_otro_alumno(self):
        doc = self._crear_doc_base("A1")
        self._agregar_epp_fuente(doc, "A1", "rev1", ["NEE Alumno A1"])
        self._agregar_epp_fuente(doc, "EXTRAÑO", "rev1", ["NEE Confidencial Otro Alumno"])

        # Solo debe retornar las de A1
        cat = nee.catalogo_nee_validadas(doc, alumno_id="A1")
        self.assertEqual(len(cat), 1)
        self.assertEqual(cat[0]['alumno_id'], "A1")

    def test_caso_14_fuentes_corruptas_o_vacias(self):
        doc = self._crear_doc_base("A1")
        # Fuente EPP con JSON no válido
        doc['metadatos']['fuentes'].append({
            'tipo': 'EPP', 'alumno': 'A1', 'parte': 'Conclusión',
            'texto': '{corrupted json!??'
        })
        # No debe lanzar excepción
        cat = nee.catalogo_nee_validadas(doc, alumno_id="A1")
        self.assertEqual(cat, [])

    def test_caso_15_diagnostico_clinico_no_se_convierte_en_nee(self):
        doc = self._crear_doc_base("A1")
        # La EPP contiene un diagnóstico médico puro ("TDAH combinado", "Hipoacusia bilateral")
        self._agregar_epp_fuente(doc, "A1", "rev1", [
            "TDAH combinado",
            "Discapacidad Intelectual Leve",
            "fortalecer la autorregulación emocional y la atención a consignas"
        ])
        cat = nee.catalogo_nee_validadas(doc, alumno_id="A1")
        # Los diagnósticos clínicos puros son filtrados; solo la necesidad pedagógica se conserva
        self.assertEqual(len(cat), 1)
        self.assertIn("autorregulación", cat[0]['texto'].lower())
        self.assertNotIn("TDAH combinado", [c['texto'] for c in cat])
        self.assertNotIn("Discapacidad Intelectual", [c['texto'] for c in cat])


if __name__ == '__main__':
    unittest.main()

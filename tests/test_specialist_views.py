import unittest

import pandas as pd

from documents.listados import listado_alumnos_html, listado_alumnos_pdf
from data.repository import _siguiente_folio_oficio
from services.asignaciones import es_especialista


class SpecialistViewTests(unittest.TestCase):
    def test_automatic_officio_sequence_starts_at_22_and_respects_existing_numbers(self):
        self.assertEqual(_siguiente_folio_oficio([]), 22)
        self.assertEqual(_siguiente_folio_oficio(["1", "21"]), 22)
        self.assertEqual(_siguiente_folio_oficio(["1", "21", "24"]), 25)

    def test_specialist_roles_are_recognized_without_support_teacher_roles(self):
        self.assertTrue(es_especialista("Psicología"))
        self.assertTrue(es_especialista("Maestra de Comunicación"))
        self.assertTrue(es_especialista("Trabajo Social"))
        self.assertFalse(es_especialista("Maestra de Apoyo"))
        self.assertFalse(es_especialista("Director"))

    def test_nominal_list_adds_support_teacher_signature_when_supplied(self):
        roster = pd.DataFrame([{
            "ID_Alumno": "ALU-001",
            "Nombre_Completo": "ALUMNO DE PRUEBA",
            "Edad_1_Septiembre": 8,
            "Condicion_Discapacidad": "TEA",
            "Grado": "2do",
            "Grupo": "A",
        }])
        html = listado_alumnos_html(roster, "Escuela", "Maestra Ejemplo")
        pdf = listado_alumnos_pdf(roster, "Escuela", "Maestra Ejemplo")
        self.assertIn("Maestra Ejemplo", html)
        self.assertIn("Maestra/o de apoyo responsable", html)
        self.assertTrue(pdf.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()

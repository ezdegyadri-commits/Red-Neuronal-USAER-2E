import unittest
from unittest.mock import patch

import pandas as pd

from services.expedientes import alumnos_visibles


class SharedSupportScopeTest(unittest.TestCase):
    @patch("services.expedientes.repo.alumnos")
    def test_ichcaanziho_support_teachers_do_not_see_each_others_students(self, alumnos_mock):
        alumnos_mock.return_value = pd.DataFrame([
            {"ID_Alumno": "CEC-1", "ID_Escuela": "ESC-002", "Maestra de Apoyo": "Mtra. María Cecilia Solís Vázquez"},
            {"ID_Alumno": "MAR-1", "ID_Escuela": "ESC-002", "Maestra de Apoyo": "Mtra. Marycruz Caamal Coral"},
            {"ID_Alumno": "OTH-1", "ID_Escuela": "ESC-002", "Maestra de Apoyo": "Psic. Edgar Adrian Yam Briceño"},
        ])
        cecilia = alumnos_visibles("Maestra de Apoyo", "Ichcaanziho", "Mtra. María Cecilia Solís Vázquez")
        marycruz = alumnos_visibles("Maestra de Apoyo", "Ichcaanziho", "Marycruz Caamal Coral")
        especialista = alumnos_visibles("Psicología", "Ichcaanziho", "Especialista")
        self.assertEqual(cecilia["ID_Alumno"].tolist(), ["CEC-1"])
        self.assertEqual(marycruz["ID_Alumno"].tolist(), ["MAR-1"])
        self.assertEqual(set(especialista["ID_Alumno"]), {"CEC-1", "MAR-1", "OTH-1"})

    @patch("services.expedientes.repo.alumnos")
    def test_ichcaanziho_cecilia_name_variations_match(self, alumnos_mock):
        alumnos_mock.return_value = pd.DataFrame([
            {"ID_Alumno": "CEC-1", "ID_Escuela": "ESC-002", "Maestra de Apoyo": "Cecilia Solís"},
            {"ID_Alumno": "CEC-2", "ID_Escuela": "ESC-002", "Maestra de Apoyo": "Mtra. María Cecilia Solís"},
            {"ID_Alumno": "CEC-3", "ID_Escuela": "ESC-002", "Maestra de Apoyo": "Mtra. María Cecilia Solís Vázquez"},
            {"ID_Alumno": "MAR-1", "ID_Escuela": "ESC-002", "Maestra de Apoyo": "Mtra. Marycruz Caamal Coral"},
        ])
        cecilia = alumnos_visibles("Maestra de Apoyo", "Ichcaanziho", "Mtra. María Cecilia Solís Vázquez")
        self.assertEqual(cecilia["ID_Alumno"].tolist(), ["CEC-1", "CEC-2", "CEC-3"])

    @patch("services.planeacion.repo.alumnos")
    @patch("services.planeacion.identidad")
    def test_cecilia_planning_with_three_students_is_authorized(self, identidad_mock, alumnos_mock):
        from services import planeacion as p
        identidad_mock.return_value = {
            "cuenta": "cecilia", "nombre": "María Cecilia Solís Vázquez", "rol": "Maestra de Apoyo",
            "director": False, "area": "Aprendizaje", "perfil": None,
        }
        alumnos_mock.return_value = pd.DataFrame([
            {"ID_Alumno": "C1", "ID_Escuela": "ESC-002", "Nombre_Completo": "Alumno 1", "Grado": "3", "Grupo": "A"},
            {"ID_Alumno": "C2", "ID_Escuela": "ESC-002", "Nombre_Completo": "Alumno 2", "Grado": "3", "Grupo": "A"},
            {"ID_Alumno": "C3", "ID_Escuela": "ESC-002", "Nombre_Completo": "Alumno 3", "Grado": "3", "Grupo": "A"},
        ])
        doc = {
            "id": "plan-cecilia-3",
            "cuenta": "cecilia",
            "formato": "XXIII",
            "estado": "BORRADOR",
            "datos": {
                "ID_Escuela": "ESC-002",
                "Escuela regular": "Ichcaanziho",
                "Curso escolar": "2026-2027",
                "Trimestre": 1,
                "Alumnos": [
                    {"ID_Alumno": "C1", "Nombre del alumno": "Alumno 1", "Grado": "3", "Grupo": "A"},
                    {"ID_Alumno": "C2", "Nombre del alumno": "Alumno 2", "Grado": "3", "Grupo": "A"},
                    {"ID_Alumno": "C3", "Nombre del alumno": "Alumno 3", "Grado": "3", "Grupo": "A"},
                ],
            },
            "metadatos": {"modalidad_planeacion": "individual"},
        }
        # Incluso si el frame pasado inicialmente no contiene uno de los alumnos por asignación
        padron_parcial = pd.DataFrame([
            {"ID_Alumno": "C1", "ID_Escuela": "ESC-002"},
            {"ID_Alumno": "C2", "ID_Escuela": "ESC-002"},
        ])
        actor = p.autorizar(doc, escribir=True, frame=padron_parcial)
        self.assertEqual(actor["cuenta"], "cecilia")


if __name__ == "__main__":
    unittest.main()


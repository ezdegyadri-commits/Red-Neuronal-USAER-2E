import unittest
from unittest.mock import patch

import pandas as pd

from services.alumnos import alumnos_de_escuela
from services.expedientes import alumnos_visibles


class SchoolScopeTests(unittest.TestCase):
    def setUp(self):
        self.alumnos = pd.DataFrame([
            {
                "ID_Alumno": "TEST-ALU-1001",
                "Nombre_Completo": "ESTUDIANTE DE PRUEBA UNO",
                "Grado": "1°",
                "Grupo": "A",
                "ID_Escuela": "ESC-007",
                "Nombre_Escuela": "DOMINGO SOLÍS RODRÍGUEZ",
                "Maestra de Apoyo": "DOCENTE DE PRUEBA",
            },
            {
                "ID_Alumno": "TEST-ALU-1002",
                "Nombre_Completo": "ESTUDIANTE DE PRUEBA DOS",
                "ID_Escuela": "ESC-006",
                "Nombre_Escuela": "MANUEL SARRADO",
            },
        ])

    def test_directory_school_name_matches_central_school_id(self):
        result = alumnos_de_escuela(self.alumnos, "Domingo Solís Rodríguez")
        self.assertEqual(result["ID_Alumno"].tolist(), ["TEST-ALU-1001"])

    @patch("services.expedientes.repo.alumnos")
    def test_role_scope_uses_all_school_identity_columns(self, alumnos_mock):
        alumnos_mock.return_value = self.alumnos
        result = alumnos_visibles("Maestra de Apoyo", "Domingo Solís Rodríguez")
        self.assertEqual(result["ID_Alumno"].tolist(), ["TEST-ALU-1001"])

    def test_duplicate_roster_rows_are_collapsed_by_student_id(self):
        duplicated = pd.concat([self.alumnos, self.alumnos.iloc[[0]]])
        result = alumnos_de_escuela(duplicated, "ESC-007")
        self.assertEqual(result["ID_Alumno"].tolist(), ["TEST-ALU-1001"])


if __name__ == "__main__":
    unittest.main()


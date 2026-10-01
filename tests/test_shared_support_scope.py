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


if __name__ == "__main__":
    unittest.main()


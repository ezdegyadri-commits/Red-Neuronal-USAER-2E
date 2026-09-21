import unittest
from unittest.mock import patch

import pandas as pd

from services.alumnos import alumnos_de_escuela
from services.expedientes import alumnos_visibles, sugerencias_de_alumno
from services.padron_oficial import validar_identidad_padron
from data import repository


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

    def test_event_history_uses_student_id_not_homonymous_name(self):
        events = pd.DataFrame([
            {
                "ID_Evento": "EV-1",
                "ID_Alumno": "TEST-ALU-1001",
                "Nombre_Alumno": "NOMBRE DE PRUEBA COMPARTIDO",
                "Grado_Grupo": "1° A",
                "Evento": "Evento correcto",
            },
            {
                "ID_Evento": "EV-2",
                "ID_Alumno": "TEST-ALU-1002",
                "Nombre_Alumno": "NOMBRE DE PRUEBA COMPARTIDO",
                "Grado_Grupo": "1° A",
                "Evento": "Evento de otra persona",
            },
        ])
        with patch.object(repository, "anexo5", return_value=events), patch.object(
            repository, "read", return_value=pd.DataFrame()
        ):
            result = repository.eventos_alumno(
                "TEST-ALU-1001", "NOMBRE DE PRUEBA COMPARTIDO", "1° A"
            )
        self.assertEqual(result["ID_Evento"].tolist(), ["EV-1"])

    def test_anexo4_does_not_mix_suggestions_of_homonyms(self):
        suggestions = pd.DataFrame([
            {
                "ID_Anexo4": "SUG-1",
                "ID_Alumno": "TEST-ALU-1001",
                "Nombre_Alumno": "ESTUDIANTE DE PRUEBA UNO",
                "Escuela": "DOMINGO SOLÍS RODRÍGUEZ",
                "Grado_Grupo": "1° A",
            },
            {
                "ID_Anexo4": "SUG-2",
                "ID_Alumno": "TEST-ALU-1002",
                "Nombre_Alumno": "ESTUDIANTE DE PRUEBA UNO",
                "Escuela": "DOMINGO SOLÍS RODRÍGUEZ",
                "Grado_Grupo": "1° A",
            },
            {
                "ID_Anexo4": "SUG-3",
                "ID_Alumno": "",
                "Nombre_Alumno": "ESTUDIANTE DE PRUEBA UNO",
                "Escuela": "DOMINGO SOLÍS RODRÍGUEZ",
                "Grado_Grupo": "1° A",
            },
        ])
        result = sugerencias_de_alumno(suggestions, self.alumnos.iloc[0].to_dict())
        self.assertEqual(set(result["ID_Anexo4"]), {"SUG-1", "SUG-3"})

    def test_official_roster_rejects_duplicate_curp_instead_of_silently_dropping(self):
        duplicated = pd.DataFrame([
            {
                "ID_Alumno": "TEST-ALU-3001",
                "Nombre_Completo": "ESTUDIANTE PRUEBA TRES",
                "CURP": "TES000101HYNXXXA01",
            },
            {
                "ID_Alumno": "TEST-ALU-3002",
                "Nombre_Completo": "ESTUDIANTE PRUEBA CUATRO",
                "CURP": "TES000101HYNXXXA01",
            },
        ])
        with self.assertRaisesRegex(ValueError, "CURP duplicadas"):
            validar_identidad_padron(duplicated)

    def test_official_roster_rejects_named_student_without_valid_curp(self):
        invalid = pd.DataFrame([
            {
                "ID_Alumno": "TEST-ALU-4001",
                "Nombre_Completo": "ESTUDIANTE PRUEBA CINCO",
                "CURP": "CURP-INVALIDA",
            },
        ])
        with self.assertRaisesRegex(ValueError, "CURP ausente o inválida"):
            validar_identidad_padron(invalid)


if __name__ == "__main__":
    unittest.main()


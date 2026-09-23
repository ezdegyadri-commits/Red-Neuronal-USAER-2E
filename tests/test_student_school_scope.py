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

    def test_legacy_event_is_not_hidden_when_grade_differs_from_current_grade(self):
        events = pd.DataFrame([
            {
                "ID_Evento": "AN5-015",
                "Fecha": "2026-09-08",
                "Nombre_Alumno": "ROSADO BERMON GEORGE JOSEPH",
                "Grado_Grupo": "1ro A",
                "Evento": "Anotación anterior",
                "Especialista": "Mtra. Zuemmy del Carmen Pérez Basto",
                "Estado": "",
            },
            {
                "ID_Evento": "AN5-096",
                "Fecha": "2026-09-23",
                "Nombre_Alumno": "ROSADO BERMON GEORGE JOSEPH",
                "Grado_Grupo": "3ro A",
                "Evento": "Anotación de hoy",
                "Estado": "ACTIVO",
                "Especialista": "Mtra. Zuemmy del Carmen Pérez Basto",
            },
            {
                "ID_Evento": "AN5-097",
                "Fecha": "2026-09-23",
                "Nombre_Alumno": "OTRO ALUMNO",
                "Grado_Grupo": "3ro A",
                "Evento": "No debe mezclarse",
                "Estado": "ACTIVO",
            },
        ])
        relaciones = pd.DataFrame([
            {"ID_Alumno": "TEST-ROSADO", "Tipo_Registro": "ANEXO5", "ID_Registro": "AN5-096"},
        ])
        padron = pd.DataFrame([
            {"ID_Alumno": "TEST-ROSADO", "Nombre_Completo": "ROSADO BERMON GEORGE JOSEPH", "Grado": "3o.", "ID_Escuela": "ESC-007", "Nombre_Escuela": "DOMINGO SOLÍS RODRÍGUEZ"},
        ])
        with patch.object(repository, "anexo5", return_value=events), patch.object(
            repository,
            "read",
            side_effect=lambda name: relaciones if name == "Relaciones_Expediente" else pd.DataFrame(),
        ):
            result = repository.eventos_alumno(
                "TEST-ROSADO", "Rosado Bermon George Joseph", "3o.",
                id_escuela="ESC-007",
                escuela="DOMINGO SOLÍS RODRÍGUEZ",
                alumnos_referencia=padron,
            )
        self.assertEqual(result["ID_Evento"].tolist(), ["AN5-015", "AN5-096"])

    def test_unidentified_legacy_rows_are_not_collapsed_as_blank_duplicate_ids(self):
        events = pd.DataFrame([
            {"ID_Evento": "", "ID_Alumno": "", "Nombre_Alumno": "ALUMNO DE PRUEBA", "Grado_Grupo": "1ro", "Evento": "Uno"},
            {"ID_Evento": "", "ID_Alumno": "", "Nombre_Alumno": "ALUMNO DE PRUEBA", "Grado_Grupo": "1ro", "Evento": "Dos"},
        ])
        with patch.object(repository, "anexo5", return_value=events), patch.object(
            repository, "read", return_value=pd.DataFrame()
        ):
            result = repository.eventos_alumno("TEST-ALU-1", "ALUMNO DE PRUEBA", "3ro")
        self.assertEqual(result["Evento"].tolist(), ["Uno", "Dos"])

    def test_legacy_event_for_homonymous_students_is_flagged_not_mixed(self):
        events = pd.DataFrame([
            {
                "ID_Evento": "AN-AMB-1",
                "ID_Alumno": "",
                "Nombre_Alumno": "NOMBRE HOMONIMO",
                "Grado_Grupo": "2do A",
                "Evento": "Registro por verificar",
                "Estado": "ACTIVO",
                "Escuela": "DOMINGO SOLÍS RODRÍGUEZ",
            }
        ])
        roster = pd.DataFrame([
            {"ID_Alumno": "HOM-1", "Nombre_Completo": "NOMBRE HOMONIMO", "Grado": "1ro", "Grupo": "A", "ID_Escuela": "ESC-007", "Nombre_Escuela": "DOMINGO SOLÍS RODRÍGUEZ"},
            {"ID_Alumno": "HOM-2", "Nombre_Completo": "NOMBRE HOMONIMO", "Grado": "2do", "Grupo": "A", "ID_Escuela": "ESC-007", "Nombre_Escuela": "DOMINGO SOLÍS RODRÍGUEZ"},
        ])
        with patch.object(repository, "anexo5", return_value=events), patch.object(
            repository, "read", return_value=pd.DataFrame()
        ):
            result = repository.eventos_alumno(
                "HOM-2",
                "NOMBRE HOMONIMO",
                "2do A",
                id_escuela="ESC-007",
                escuela="DOMINGO SOLÍS RODRÍGUEZ",
                alumnos_referencia=roster,
            )
        self.assertTrue(result.empty)
        self.assertEqual(result.attrs["eventos_ambiguos"], 1)

    @patch("services.expedientes.df_sheet")
    @patch("services.expedientes.repo.eventos_alumno")
    @patch("services.expedientes.repo.anexo4", return_value=pd.DataFrame())
    @patch("services.expedientes.repo.anexo3", return_value=pd.DataFrame())
    @patch("services.expedientes.repo.ensure_expediente")
    @patch("services.expedientes.repo.alumnos")
    def test_timeline_includes_historical_anexo5_without_duplicate_current_event(
        self, alumnos_mock, _ensure_mock, _a3_mock, _a4_mock, eventos_mock, timeline_mock
    ):
        from services.expedientes import expediente

        alumno = {
            "ID_Alumno": "TEST-ALU-1001",
            "Nombre_Completo": "ESTUDIANTE DE PRUEBA UNO",
            "Grado": "3ro",
            "Grupo": "A",
            "ID_Escuela": "ESC-007",
            "Nombre_Escuela": "DOMINGO SOLÍS RODRÍGUEZ",
        }
        alumnos_mock.return_value = pd.DataFrame([alumno])
        eventos = pd.DataFrame([
            {"ID_Evento": "AN-015", "Fecha": "2026-09-08", "Especialista": "DOCENTE", "Evento": "Anterior"},
            {"ID_Evento": "AN-096", "Fecha": "2026-09-23", "Especialista": "DOCENTE", "Evento": "Hoy"},
        ])
        eventos_mock.return_value = eventos
        timeline_mock.return_value = pd.DataFrame([
            {"ID_Expediente": "EXP-TEST-ALU-1001", "Fecha": "2026-09-23", "Tipo": "SEGUIMIENTO", "Titulo": "Evento significativo registrado", "Descripcion": "Hoy", "Usuario": "DOCENTE"},
        ])

        resultado = expediente("TEST-ALU-1001")

        self.assertEqual(set(resultado["anexo5"]["ID_Evento"]), {"AN-015", "AN-096"})
        self.assertEqual(len(resultado["timeline"]), 2)
        self.assertEqual(set(resultado["timeline"]["Descripcion"]), {"Anterior", "Hoy"})

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


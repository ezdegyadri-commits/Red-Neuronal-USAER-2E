import unittest
from datetime import date
from unittest.mock import patch

from documents.cronogramas import generar_cronograma_pdf
from services import cronogramas
from services.cronogramas import fechas_habiles, perfil_especialista


class CronogramasTest(unittest.TestCase):
    def test_only_specialist_account_with_known_profile_is_allowed(self):
        perfil = perfil_especialista("María José Cupul Realpozo", "Psicóloga")
        self.assertEqual(perfil["area"], "Psicología")
        self.assertIsNone(perfil_especialista("Psic. Edgar Adrián Yam Briceño MD", "DIRECTOR"))
        self.assertIsNone(perfil_especialista("Cuenta desconocida", "ESPECIALISTA"))

    def test_month_calendar_skips_weekends_and_official_closures(self):
        dias = fechas_habiles("2026-09")
        self.assertTrue(all(dia.weekday() < 5 for dia in dias))
        self.assertNotIn(date(2026, 9, 16), dias)
        self.assertNotIn(date(2026, 9, 25), dias)

    def test_pdf_is_generated_with_the_official_assets(self):
        perfil = perfil_especialista("María José Cupul Realpozo", "Psicóloga")
        contenido = generar_cronograma_pdf(
            perfil,
            "Septiembre 2026",
            [{"fecha": "01/09/2026", "escuela": "DAMIÁN CARMONA", "actividad": "Reunión de trabajo"}],
        )
        self.assertTrue(contenido.startswith(b"%PDF"))
        self.assertGreater(len(contenido), 1000)

    def test_save_appends_new_rows_and_preserves_old_version(self):
        class FakeWorksheet:
            col_count = 26

            def __init__(self):
                self.appended = []
                self.updates = []
                self.headers = []

            def append_rows(self, rows, value_input_option):
                self.appended.extend(rows)

            def batch_update(self, updates, value_input_option):
                self.updates.extend(updates)

            def update_cell(self, row, column, value):
                self.headers.append((row, column, value))

        ws = FakeWorksheet()
        headers = cronogramas.ENCABEZADOS_CRONOGRAMA
        existing = [{
            "Especialista": "María José Cupul Realpozo",
            "Área": "Psicología",
            "Fecha": "2026-09-01",
            "Escuela": "DAMIÁN CARMONA",
            "Actividad": "Actividad previa",
            "Estado": "ACTIVO",
            "_fila": 2,
        }]
        with patch.object(cronogramas, "_leer_registros", return_value=(ws, headers, existing)):
            resultado = cronogramas.guardar_agenda(
                "María José Cupul Realpozo", "Psicología", "2026-09",
                ["Damián Carmona"],
                [{"fecha": "2026-09-02", "escuela": "Damián Carmona", "actividad": "Seguimiento"}],
            )
        self.assertEqual(resultado["filas"], 1)
        self.assertEqual(len(ws.appended), 1)
        self.assertEqual(ws.appended[0][5:7], ["2026-09-02", "Seguimiento"])
        self.assertEqual(ws.updates, [{"range": "H2", "values": [["SUSTITUIDO"]]}])

    def test_first_save_adds_status_column_without_rewriting_existing_rows(self):
        class FakeWorksheet:
            col_count = 26

            def __init__(self):
                self.appended = []
                self.headers = []
                self.updates = []

            def update_cell(self, row, column, value):
                self.headers.append((row, column, value))

            def append_rows(self, rows, value_input_option):
                self.appended.extend(rows)

            def batch_update(self, updates, value_input_option):
                self.updates.extend(updates)

        ws = FakeWorksheet()
        headers = cronogramas.ENCABEZADOS_CRONOGRAMA[:-1]
        existing = [{"Especialista": "María José Cupul Realpozo", "Fecha": "2026-09-01", "_fila": 2}]
        with patch.object(cronogramas, "_leer_registros", return_value=(ws, headers, existing)):
            cronogramas.guardar_agenda(
                "María José Cupul Realpozo", "Psicología", "2026-09",
                ["Damián Carmona"],
                [{"fecha": "2026-09-02", "escuela": "Damián Carmona", "actividad": "Seguimiento"}],
            )
        self.assertEqual(ws.headers, [(1, 8, "Estado")])
        self.assertEqual(len(ws.appended[0]), 8)
        self.assertEqual(ws.updates[0]["range"], "H2")


if __name__ == "__main__":
    unittest.main()

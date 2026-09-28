"""El historial de visitas se recupera sin alterar el registro central."""

import unittest
from unittest.mock import patch

import pandas as pd

from ui.pages import _clave_visita, _fecha_visita_guardada, _visitas_visibles
from data import repository as repo


class HistorialVisitasTest(unittest.TestCase):
    def setUp(self):
        self.registros = pd.DataFrame([
            {"ID_Visita": "VIS-001", "Fecha": "24/09/2026", "Escuela": "Domingo Solís Rodríguez", "Personal": "Abril Pérez", "Motivo": "Valoración"},
            {"ID_Visita": "VIS-002", "Fecha": "25/09/2026", "Escuela": "Domingo Solís Rodríguez", "Personal": "Diego Peralta Torres", "Motivo": "Entrevista"},
            {"ID_Visita": "VIS-003", "Fecha": "26/09/2026", "Escuela": "Ichcaanziho", "Personal": "Abril Pérez", "Motivo": "Seguimiento"},
            {"ID_Visita": "VIS-004", "Fecha": "27/09/2026", "Escuela": "Sede USAER", "Personal": "Edgar Yam", "Motivo": "Junta"},
        ])

    def test_specialist_sees_only_own_records_in_assigned_schools(self):
        visibles = _visitas_visibles(self.registros, "Abril Pérez", "Psicología", ["Domingo Solis Rodriguez"])
        self.assertEqual(visibles["ID_Visita"].tolist(), ["VIS-001"])

    def test_director_sees_all_assigned_schools_and_sede(self):
        visibles = _visitas_visibles(
            self.registros, "Edgar Yam", "Director",
            ["Domingo Solís Rodríguez", "Ichcaanziho"],
        )
        self.assertEqual(len(visibles), 4)

    def test_history_key_distinguishes_same_day_and_school(self):
        primero = self.registros.iloc[0].to_dict()
        segundo = dict(primero, ID_Visita="VIS-099")
        self.assertNotEqual(_clave_visita(primero), _clave_visita(segundo))

    def test_history_date_does_not_silently_use_today(self):
        self.assertEqual(_fecha_visita_guardada("24/09/2026").isoformat(), "2026-09-24")
        self.assertIsNone(_fecha_visita_guardada("fecha ilegible"))

    def test_legacy_columns_are_read_without_editing_original_rows(self):
        anterior = pd.DataFrame([{
            "Fecha": "22/09/2026", "Escuela": "Domingo Solís Rodríguez",
            "Especialista": "Abril Pérez", "Area": "Psicología", "Motivos": "Valoración",
        }])
        visible = _visitas_visibles(anterior, "Abril Pérez", "Psicología", ["Domingo Solis Rodriguez"])
        self.assertEqual(visible.iloc[0]["Personal"], "Abril Pérez")
        self.assertEqual(visible.iloc[0]["Motivo"], "Valoración")
        self.assertNotIn("Personal", anterior.columns)

    def test_new_visit_adds_missing_headers_before_appending(self):
        calls = []
        with patch.object(repo, "ensure_headers", side_effect=lambda *args: calls.append("headers")):
            with patch.object(repo, "next_numeric_id", return_value="VIS-010"):
                with patch.object(repo, "append_dict", side_effect=lambda *args: calls.append("append")):
                    self.assertEqual(repo.save_visita({"Fecha": "28/09/2026"}), "VIS-010")
        self.assertEqual(calls, ["headers", "append"])


if __name__ == "__main__":
    unittest.main()

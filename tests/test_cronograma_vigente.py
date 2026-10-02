import json
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

from services import cronogramas, horarios
from ui.cronogramas import _perfil_profesional


class CronogramaVigenteTest(unittest.TestCase):
    def test_month_save_has_no_drive_warning_and_renders_latest_pdf(self):
        app = AppTest.from_file(str(Path(__file__).parent / "fixtures" / "cronograma_guardar_app.py")).run()
        self.assertFalse(app.exception)
        next(b for b in app.button if b.label == "Guardar cambios y generar PDF").click().run()
        self.assertFalse(app.exception)
        self.assertTrue(app.success)
        self.assertNotIn("invalid_grant", " ".join(w.value for w in app.warning))
        self.assertEqual(app.session_state["cronograma_pdf_publicacion"], "actual")

    def test_latest_month_does_not_resurrect_removed_days_if_status_update_failed(self):
        rows = [
            {"Especialista": "Abril", "Fecha": "2026-10-01", "ID_Publicacion": "previa", "Estado": "ACTIVO"},
            {"Especialista": "Abril", "Fecha": "2026-10-02", "ID_Publicacion": "previa", "Estado": "ACTIVO"},
            {"Especialista": "Abril", "Fecha": "2026-10-05", "ID_Publicacion": "vigente", "Estado": "ACTIVO"},
            {"Especialista": "Diego", "Fecha": "2026-10-01", "ID_Publicacion": "diego", "Estado": "ACTIVO"},
        ]
        result = cronogramas._versiones_vigentes(rows, "2026-10")
        self.assertEqual([r["ID_Publicacion"] for r in result], ["vigente", "diego"])
        self.assertEqual(len(rows), 4)

    def test_notices_only_show_current_publication_and_preserve_source(self):
        rows = [{"Destinatario": "Cecilia", "Mes": "2026-10", "Escuela": "Ichcaanziho", "Especialista": "Elmy", "ID_Publicacion": pid} for pid in ("vieja", "nueva")]
        with patch.object(horarios, "_leer_avisos_cache", return_value=rows), patch.object(cronogramas, "cargar_agenda_global", return_value=[{"ID_Publicacion": "nueva"}]):
            self.assertEqual([r["ID_Publicacion"] for r in horarios.cargar_avisos_apoyo("Cecilia")], ["nueva"])
        self.assertEqual(len(rows), 2)

    def test_titles_are_taken_from_directory_not_inferred(self):
        from data import repository
        perfil = {"nombre": "Abril de María Chable Ríos", "area": "Psicología"}
        with patch.object(repository, "personal", return_value=pd.DataFrame([{"Nombre_Completo": perfil["nombre"], "Titulo_Profesional": "Psic."}])):
            self.assertEqual(_perfil_profesional(perfil)["nombre_profesional"], "Psic. Abril de María Chable Ríos")
        with patch.object(repository, "personal", return_value=pd.DataFrame()):
            self.assertNotIn("nombre_profesional", _perfil_profesional(perfil))

    def test_day_editor_can_apply_move_and_clear_without_replacing_occupied_date(self):
        app = AppTest.from_file(str(Path(__file__).parent / "fixtures" / "cronograma_calendar_app.py")).run()
        app.selectbox[1].select("Ichcaanziho")
        app.text_area[0].input("Acompañamiento")
        next(b for b in app.button if b.label == "Aplicar al calendario").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["test_dias"]["2026-10-01"]["actividad"], "Acompañamiento")
        app.selectbox[2].select("02/10/2026")
        next(b for b in app.button if b.label == "Aplicar al calendario").click().run()
        self.assertFalse(app.exception)
        self.assertNotIn("2026-10-01", app.session_state["test_dias"])
        self.assertIn("2026-10-02", app.session_state["test_dias"])
        app.selectbox[0].select("02/10/2026").run()
        next(b for b in app.button if b.label == "Dejar este día sin actividad").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["test_dias"], {})


if __name__ == "__main__":
    unittest.main()

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
        next(b for b in app.button if b.label == "Editar cronograma").click().run()
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

    def test_clearing_last_day_records_empty_version_without_deleting_history(self):
        from unittest.mock import Mock
        ws = Mock()
        row = {"Especialista": "Abril de María Chable Ríos", "Fecha": "2026-10-01", "ID_Publicacion": "previa", "Estado": "ACTIVO", "_fila": 2}
        with patch.object(cronogramas, "_leer_registros", return_value=(ws, cronogramas.ENCABEZADOS_CRONOGRAMA, [row])):
            resultado = cronogramas.guardar_agenda(row["Especialista"], "Psicología", "2026-10", [], [])
        self.assertEqual(resultado["filas"], 0)
        nueva = dict(zip(cronogramas.ENCABEZADOS_CRONOGRAMA, ws.append_rows.call_args.args[0][0]))
        self.assertEqual(nueva["Estado"], "VACIO")
        self.assertEqual(cronogramas._versiones_vigentes([row, nueva], "2026-10"), [])
        ws.clear.assert_not_called()
        ws.delete_rows.assert_not_called()

    def test_titles_are_taken_from_directory_not_inferred(self):
        from data import repository
        perfil = {"nombre": "Abril de María Chable Ríos", "area": "Psicología"}
        with patch.object(repository, "personal", return_value=pd.DataFrame([{"Nombre_Completo": perfil["nombre"], "Titulo_Profesional": "Psic."}])):
            self.assertEqual(_perfil_profesional(perfil)["nombre_profesional"], "Psic. Abril de María Chable Ríos")
        with patch.object(repository, "personal", return_value=pd.DataFrame()):
            self.assertNotIn("nombre_profesional", _perfil_profesional(perfil))

    def test_inline_editor_can_move_and_clear_a_day(self):
        app = AppTest.from_file(str(Path(__file__).parent / "fixtures" / "cronograma_calendar_app.py")).run()
        app.selectbox[0].select("Ichcaanziho").run()
        app.text_area[0].input("Acompañamiento").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["test_dias"]["2026-10-01"]["actividad"], "Acompañamiento")
        next(w for w in app.selectbox if w.label == "Nueva fecha").select("02/10/2026").run()
        next(b for b in app.button if b.label == "Mover actividad").click().run()
        self.assertFalse(app.exception)
        self.assertNotIn("2026-10-01", app.session_state["test_dias"])
        self.assertIn("2026-10-02", app.session_state["test_dias"])
        next(w for w in app.selectbox if w.key == "test_2026-10-02_escuela").select("Elegir escuela").run()
        next(w for w in app.text_area if w.key == "test_2026-10-02_actividad").input("").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["test_dias"], {})

    def test_editing_is_enabled_with_one_button_for_entire_month(self):
        app = AppTest.from_file(str(Path(__file__).parent / "fixtures" / "cronograma_guardar_app.py")).run()
        fields = [w for w in app.selectbox if w.label == "Escuela o junta"]
        self.assertTrue(all(w.disabled for w in fields))
        self.assertEqual(len([b for b in app.button if b.label == "Editar cronograma"]), 1)
        self.assertFalse(any(b.label == "Editar" for b in app.button))
        next(b for b in app.button if b.label == "Editar cronograma").click().run()
        self.assertFalse(app.exception)
        self.assertTrue(all(not w.disabled for w in app.selectbox if w.label == "Escuela o junta"))

    def test_history_can_open_months_older_than_twelve_months(self):
        app = AppTest.from_file(str(Path(__file__).parent / "fixtures" / "cronograma_guardar_app.py")).run()
        next(b for b in app.button if b.label == "Recuperar cronogramas de meses pasados").click().run()
        historia = next(w for w in app.selectbox if w.label == "Mes guardado a recuperar")
        self.assertEqual(historia.options, ["Septiembre 2026", "Abril 2024"])
        historia.select("Abril 2024").run()
        next(b for b in app.button if b.label == "Abrir mes recuperado para editar").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["cronograma_mes_Abril de María Chable Ríos"], "2024-04")

    def test_historical_month_lookup_is_own_and_read_only(self):
        from unittest.mock import Mock
        ws = Mock()
        rows = [{"Especialista": "Abril", "Fecha": "2024-04-01", "Estado": "SUSTITUIDO"},
                {"Especialista": "Abril", "Fecha": "01/09/2026"},
                {"Especialista": "Diego", "Fecha": "2023-01-03"}]
        cronogramas.meses_con_cronograma.clear()
        cronogramas._registros_cache.clear()
        with patch.object(cronogramas, "_leer_registros", return_value=(ws, [], rows)):
            self.assertEqual(cronogramas.meses_con_cronograma("Abril"), ["2026-09", "2024-04"])
        ws.append_rows.assert_not_called()
        ws.clear.assert_not_called()


if __name__ == "__main__":
    unittest.main()

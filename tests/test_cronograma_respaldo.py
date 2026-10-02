import json
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from streamlit.testing.v1 import AppTest
from services import borradores_cronogramas as drafts, cronogramas, horarios
from ui import cronogramas as ui


class CronogramaRespaldoTest(unittest.TestCase):
    def test_recovery_after_entire_new_session_and_no_write_on_rerun(self):
        saved = {}
        def save(nombre, mes, dias):
            saved[(nombre, mes)] = json.loads(json.dumps(dias))
        path = str(Path(__file__).parent / "fixtures" / "cronograma_respaldo_app.py")
        with patch.object(ui, "cargar_borrador", side_effect=lambda n, m, *args: saved.get((n, m))), \
             patch.object(ui, "guardar_borrador", side_effect=save) as write:
            at = AppTest.from_file(path, default_timeout=30).run()
            self.assertFalse(at.exception)
            next(s for s in at.selectbox if s.label == "Escuela o junta").select("Ichcaanziho").run()
            at.text_area[0].input("Seguimiento educativo con la maestra.").run()
            self.assertFalse(at.exception)
            count = write.call_count
            at.run()
            self.assertEqual(write.call_count, count)
            fresh = AppTest.from_file(path, default_timeout=30).run()
            self.assertFalse(fresh.exception)
            self.assertEqual(fresh.text_area[0].value, "Seguimiento educativo con la maestra.")
            self.assertEqual(next(s for s in fresh.selectbox if s.label == "Escuela o junta").value, "Ichcaanziho")
            self.assertEqual(write.call_count, count)

    def test_draft_private_partial_and_append_only(self):
        state = {"nombre": "María José Cupul Realpozo", "rol": "Psicología"}
        ws = Mock()
        dias = {"2026-10-01": {"escuela": "Ichcaanziho", "actividad": ""}}
        with patch.object(drafts.st, "session_state", state), patch.object(drafts, "_hoja", return_value=ws):
            drafts.guardar_borrador(state["nombre"], "2026-10", dias)
            self.assertEqual(ws.append_rows.call_args.kwargs["value_input_option"], "RAW")
            with self.assertRaises(PermissionError):
                drafts.cargar_borrador("Marilyn Pérez Lizama", "2026-10")
            with self.assertRaises(PermissionError):
                drafts.guardar_borrador(state["nombre"], "2026-10", {"2026-10-01": {"escuela": "Domingo Solís Rodríguez"}})
        ws.clear.assert_not_called()
        ws.delete_rows.assert_not_called()

    def test_empty_draft_not_confused_with_missing(self):
        state = {"nombre": "María José Cupul Realpozo", "rol": "Psicología"}
        with patch.object(drafts.st, "session_state", state), patch.object(drafts, "_registros", return_value=[{"Especialista": state["nombre"], "Mes": "2026-10", "Dias_JSON": "{}"}]):
            self.assertEqual(drafts.cargar_borrador(state["nombre"], "2026-10"), {})
            self.assertIsNone(drafts.cargar_borrador(state["nombre"], "2026-11"))

    def test_old_backup_cannot_override_a_newer_published_calendar(self):
        state = {"nombre": "María José Cupul Realpozo", "rol": "Psicología"}
        backup = {"Especialista": state["nombre"], "Mes": "2026-10", "Dias_JSON": "{}", "Guardado_En": "2026-10-02T08:00:00-06:00"}
        publicado = {"Especialista": state["nombre"], "Fecha": "2026-10-01", "Marca temporal": "02/10/2026 08:01:00.000001"}
        with patch.object(drafts.st, "session_state", state), patch.object(drafts, "_registros", return_value=[backup]), patch.object(drafts, "_registros_cache", return_value=([], [publicado])):
            self.assertIsNone(drafts.cargar_borrador(state["nombre"], "2026-10", {"2026-10-01": {"actividad": "Publicado"}}))
            backup["Guardado_En"] = "2026-10-02T08:02:00-06:00"
            self.assertEqual(drafts.cargar_borrador(state["nombre"], "2026-10", {"2026-10-01": {"actividad": "Publicado"}}), {})

    def test_shared_reads_for_different_accounts_and_panels(self):
        cronogramas._registros_cache.clear()
        cronogramas.cargar_agenda.clear()
        cronogramas.cargar_agenda_global.clear()
        cronogramas.meses_con_cronograma.clear()
        headers = cronogramas.ENCABEZADOS_CRONOGRAMA
        with patch.object(cronogramas, "_leer_registros", return_value=(Mock(), headers, [])) as read:
            cronogramas.cargar_agenda("María José", "2026-10")
            cronogramas.cargar_agenda("Marilyn", "2026-10")
            cronogramas.meses_con_cronograma("María José")
            cronogramas.cargar_agenda_global("2026-10")
            self.assertEqual(read.call_count, 1)
        cronogramas._registros_cache.clear()

    def test_notice_retry_reconstructed_after_session_loss(self):
        perfil = {"nombre": "Marilyn Pérez Lizama"}
        filas = [{"Especialista": perfil["nombre"], "ID_Publicacion": "PUB", "Fecha": "2026-10-01", "Escuela": "Domingo Solís Rodríguez", "Actividad": "Seguimiento"}]
        state = {}
        with patch.object(ui.st, "session_state", state), patch.object(ui, "cargar_agenda_global", return_value=filas), patch.object(ui, "avisar_maestras_apoyo", side_effect=RuntimeError("429")):
            ui._avisos_automaticos.__wrapped__(perfil, "2026-10")
        # Ningún dato pendiente de memoria es necesario para reconstruir el aviso.
        with patch.object(ui.st, "session_state", {}), patch.object(ui, "cargar_agenda_global", return_value=filas), patch.object(ui, "avisar_maestras_apoyo", return_value=1) as avisar:
            ui._avisos_automaticos.__wrapped__(perfil, "2026-10")
            self.assertEqual(avisar.call_args.args[0], "PUB")

    def test_notice_duplicate_does_not_write_or_open_sheet_again(self):
        p = {"Nombre": "Zuemmy del Carmen Pérez Basto", "Rol": "Maestra de Apoyo"}
        import pandas as pd
        existing = [{"ID_Publicacion": "PUB", "Destinatario": p["Nombre"], "Escuela": "Domingo Solís Rodríguez"}]
        ws = Mock()
        with patch.object(horarios.repo, "usuarios", return_value=pd.DataFrame([p])), patch.object(horarios, "_hoja_avisos", return_value=ws), patch.object(horarios, "_datos_avisos_cache", return_value=(horarios.AVISOS_HEADERS, existing)):
            self.assertEqual(horarios.avisar_maestras_apoyo("PUB", "Marilyn", "2026-10", [{"escuela": "Domingo Solís Rodríguez"}]), 0)
        ws.append_rows.assert_not_called()

    def test_quota_cooldown_not_immediate_repeated_attempts(self):
        from data.google import retry_google
        op = Mock(side_effect=[RuntimeError("429 quota exceeded"), RuntimeError("429 quota exceeded"), "ok"])
        with patch("data.google.time.sleep") as sleep, patch("data.google.random.uniform", return_value=0):
            self.assertEqual(retry_google(op), "ok")
        self.assertEqual([c.args[0] for c in sleep.call_args_list], [8, 16])


if __name__ == "__main__":
    unittest.main()

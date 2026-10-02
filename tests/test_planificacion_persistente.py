import json
import unittest
from datetime import time
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd
from pypdf import PdfReader
from streamlit.testing.v1 import AppTest

from services import borradores_horarios as drafts
from services import cronogramas
from services.horarios import DIAS, franjas_diarias
from documents.horarios_apoyo import generar_horario_apoyo_cuadricula_pdf
from documents.anexos import anexo4_pdf, anexo5_pdf


class PlanificacionTest(unittest.TestCase):
    def test_config_survives_a_new_streamlit_session_and_refresh_does_not_write(self):
        from ui import horarios_apoyo as ui
        guardado = {}
        def respaldar(nombre, escuela, datos):
            guardado.clear()
            guardado.update(json.loads(json.dumps(datos)))
        archivo = str(Path(__file__).parent / "fixtures" / "horario_draft_app.py")
        vacio = pd.DataFrame(columns=["ID_Alumno", "Nombre_Completo", "Grado", "Grupo"])
        with patch.object(drafts, "cargar_borrador", side_effect=lambda *args: dict(guardado)), patch.object(drafts, "guardar_borrador", side_effect=respaldar) as guardar, patch.object(ui, "_alumnos_de_maestra", return_value=(vacio, vacio)):
            app = AppTest.from_file(archivo).run()
            self.assertFalse(app.exception)
            next(w for w in app.text_input if w.label == "Lunes · minutos").input("45,60").run()
            next(w for w in app.text_input if w.label == "Descanso desde · HH:MM").input("10:00").run()
            next(w for w in app.text_input if w.label == "Descanso hasta · HH:MM").input("10:30").run()
            self.assertFalse(app.exception)
            self.assertEqual(guardado["widgets"]["dur_Lunes"], "45,60")
            self.assertEqual(guardado["widgets"]["descanso_fin"], "10:30")
            cantidad = guardar.call_count
            app.run()
            self.assertEqual(guardar.call_count, cantidad)
            nuevo = AppTest.from_file(archivo).run()
            self.assertFalse(nuevo.exception)
            self.assertEqual(next(w for w in nuevo.text_input if w.label == "Lunes · minutos").value, "45,60")
            self.assertEqual(next(w for w in nuevo.text_input if w.label == "Descanso hasta · HH:MM").value, "10:30")

    def test_draft_is_scoped_and_append_only(self):
        state = {"nombre": "Marycruz", "rol": "MAESTRA DE APOYO"}
        ws = Mock()
        datos = {"widgets": {"inicio": "07:00:00", "dur_Lunes": "45,60", "descanso_inicio": "10:00"},
                 "bloques": {"Lunes|07:00|07:45": {"Grupo": "1 B"}}}
        with patch.object(drafts.st, "session_state", state), patch.object(drafts, "escuelas_asignadas", return_value=["Ichcaanziho"]):
            with patch.object(drafts, "_ws", return_value=ws):
                drafts.guardar_borrador("Marycruz", "Ichcaanziho", datos)
            self.assertEqual(ws.append_rows.call_args.kwargs["value_input_option"], "RAW")
            with patch.object(drafts, "_leer", return_value=(ws, drafts.HEADERS, [
                {"Maestra": "Marycruz", "Escuela": "Ichcaanziho", "Datos_JSON": json.dumps(datos)},
                {"Maestra": "Cecilia", "Escuela": "Ichcaanziho", "Datos_JSON": '{"bloques": {}}'},
            ])):
                self.assertEqual(drafts.cargar_borrador("Marycruz", "Ichcaanziho"), datos)
            with self.assertRaises(PermissionError):
                drafts.cargar_borrador("Cecilia", "Ichcaanziho")
            with self.assertRaises(PermissionError):
                drafts.guardar_borrador("Marycruz", "Otra escuela", {})
        ws.clear.assert_not_called()
        ws.delete_rows.assert_not_called()

    def test_calendar_excludes_cte_and_server_rejects_blocked_dates(self):
        for fecha in ("2026-10-03", "2026-10-30", "2026-10-32"):
            with self.subTest(fecha=fecha), patch.object(cronogramas, "_leer_registros") as leer:
                with self.assertRaises(ValueError):
                    cronogramas.guardar_agenda("María José Cupul Realpozo", "Psicología", "2026-10",
                        ["Ichcaanziho"], [{"fecha": fecha, "escuela": "Ichcaanziho", "actividad": "Seguimiento"}])
                leer.assert_not_called()
        with self.assertRaises(ValueError):
            cronogramas.guardar_agenda("María José Cupul Realpozo", "Psicología", "2026-10",
                ["Domingo Solís Rodríguez"], [{"fecha": "2026-10-01", "escuela": "Domingo Solís Rodríguez", "actividad": "No asignada"}])

    def test_calendar_ui_has_only_working_days_and_assigned_schools(self):
        app = AppTest.from_file(str(Path(__file__).parent / "fixtures" / "cronograma_calendar_app.py")).run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.selectbox), len(cronogramas.fechas_habiles("2026-10")))
        self.assertTrue(all(w.options == ["Elegir escuela o junta", "Ichcaanziho", "Junta · Sede USAER"] for w in app.selectbox))
        self.assertIn("Consejo Técnico Escolar", [c.value for c in app.caption])

    def test_visits_are_filtered_by_school_not_specialist(self):
        state = {"nombre": "Marycruz", "rol": "APOYO"}
        with patch.object(cronogramas.st, "session_state", state), patch.object(cronogramas, "escuelas_asignadas", return_value=["Ichcaanziho"]), patch.object(cronogramas, "_agenda_visitas_cache", return_value=[
            {"Escuela": "Ichcaanziho", "Especialista": "María José"},
            {"Escuela": "Ichcaanziho", "Especialista": "Elmy"},
            {"Escuela": "Ichcaanziho", "Especialista": "Diego"},
            {"Escuela": "Domingo Solís Rodríguez", "Especialista": "Abril"},
        ]):
            self.assertEqual(len(cronogramas.cargar_visitas_escuela("Ichcaanziho", "2026-10")), 3)
            with self.assertRaises(PermissionError):
                cronogramas.cargar_visitas_escuela("Domingo Solís Rodríguez", "2026-10")

    def test_variable_daily_schedule_fits_one_page_without_purpose_block(self):
        diarios, filas = {}, []
        for dia, duracion in zip(DIAS, (60, 45, 50, 60, 40)):
            diario, _ = franjas_diarias(time(7), time(13), str(duracion), "10:00", "10:30")
            diarios[dia] = diario
            for inicio, fin in diario:
                filas.append({"Dia": dia, "Inicio": inicio, "Fin": fin, "Grupo": "1 B",
                    "Alumnos": "Rodríguez Quintal Iker Elian; Alpuche Bolio Victoria Ailed",
                    "Actividad": "PROPOSITO_EXTENSO_NO_IMPRIMIR"})
        franjas = sorted({f for diario in diarios.values() for f in diario})
        contenido = generar_horario_apoyo_cuadricula_pdf("Ichcaanziho", "Marycruz Pérez", filas, franjas, diarios)
        doc = PdfReader(BytesIO(contenido))
        self.assertEqual(len(doc.pages), 1)
        texto = doc.pages[0].extract_text()
        self.assertIn("Marycruz", texto)
        self.assertIn("VO. BO.", texto)
        self.assertNotIn("PROPOSITO_EXTENSO", texto)
        self.assertIn("07:00 - 07:45", texto)
        self.assertIn("Iker Rodríguez", texto)

    def test_short_suggestion_fits_and_long_event_keeps_signature_with_text(self):
        alumno = {"Nombre_Completo": "Alumno Ejemplo", "Grado": "1", "Grupo": "B"}
        sugerencia = anexo4_pdf(alumno, pd.DataFrame([{"Sugerencias": "Trabajar lectura compartida.", "Nivel_Cumplimiento_Resultados": "Avanza con apoyos.", "Quien_Brinda_Sugerencias": "Maestra de apoyo"}]))
        self.assertEqual(len(PdfReader(BytesIO(sugerencia)).pages), 1)
        evento = "Línea educativa de seguimiento con información que debe conservarse.\n" * 120
        doc = PdfReader(BytesIO(anexo5_pdf(alumno, pd.DataFrame([{"Fecha": "2026-10-01", "Especialista": "Psicóloga", "Evento": evento}]))))
        ultima = doc.pages[-1].extract_text()
        self.assertIn("Firma:", ultima)
        self.assertIn("Línea educativa", ultima)
        self.assertEqual(sum(p.extract_text().count("Línea educativa") for p in doc.pages), 120)


if __name__ == "__main__":
    unittest.main()

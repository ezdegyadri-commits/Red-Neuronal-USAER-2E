import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path
from streamlit.testing.v1 import AppTest

from services import calendario_eventos as eventos
from services import cronogramas

DIRECTOR = {"nombre": "Psic. Edgar Adrián Yam Briceño MD", "rol": "DIRECTOR"}


class CalendarioEventosTest(unittest.TestCase):
    def test_source_has_all_dated_occurrences_and_one_undated_campaign(self):
        fuente = eventos.calendario_base()
        self.assertEqual(len(fuente["eventos"]), 134)
        self.assertEqual(len({e["ID_Evento"] for e in fuente["eventos"]}), 134)
        self.assertEqual(fuente["pendientes"], [{"mes": "2027-03", "titulo": "Campaña de AYPRODA", "fecha_original": "Por definir"}])
        self.assertTrue(all("Informativo" not in e["Fecha"] for e in fuente["eventos"]))
        for e in fuente["eventos"]:
            date.fromisoformat(e["Fecha"])

    def test_pfsee_dates_and_weekend_only_exhibition_are_preserved(self):
        rows = eventos.calendario_base()["eventos"]
        presencial = [e["Fecha"] for e in rows if e["Fecha"].startswith("2026-10") and "Curso presencial" in e["Titulo"]]
        self.assertEqual(presencial, ["2026-10-01", "2026-10-02", "2026-10-26", "2026-10-27", "2026-10-28"])
        feria = [e for e in rows if "Xmatkuil" in e["Titulo"]]
        self.assertEqual(len(feria), 8)
        self.assertTrue(all(date.fromisoformat(e["Fecha"]).weekday() >= 5 for e in feria))

    def test_informative_event_does_not_block_academic_meeting_day(self):
        self.assertIn(date(2026, 10, 23), cronogramas.fechas_habiles("2026-10"))
        with patch.object(eventos, "_eventos_guardados", return_value=[]):
            self.assertTrue(any("Segunda reunión" in e["Titulo"] for e in eventos.cargar_eventos("2026-10") if e["Fecha"] == "2026-10-23"))

    def test_new_versions_replace_display_only_and_keep_old_rows(self):
        base = eventos.calendario_base()["eventos"][0]
        row = {**base, "Fecha": "2026-10-02", "Titulo": "Actualizado", "Revision": "nueva"}
        original = dict(base)
        latest = eventos.eventos_vigentes([base, row])
        self.assertEqual(next(e for e in latest if e["ID_Evento"] == base["ID_Evento"]), row)
        self.assertEqual(base, original)
        self.assertEqual(len(latest), 134)

    def test_only_director_can_write_even_if_ui_is_bypassed(self):
        for perfil in ({"nombre": "Abril de María Chable Ríos", "rol": "Psicología"},
                       {"nombre": "Marycruz Caamal Coral", "rol": "APOYO"},
                       {"nombre": "Persona ajena", "rol": "DIRECTOR"}):
            with patch.object(eventos, "st", SimpleNamespace(session_state=perfil)), patch.object(eventos, "ensure_headers") as write:
                with self.assertRaises(PermissionError):
                    eventos.guardar_evento("2026-10-02", "Reunión")
                write.assert_not_called()

    def test_director_save_is_raw_append_only_and_accepts_weekend_event(self):
        ws = SimpleNamespace(row_values=lambda n: eventos.HEADERS, append_rows=lambda rows, **kw: writes.append((rows, kw)))
        writes = []
        with patch.object(eventos, "st", SimpleNamespace(session_state=DIRECTOR)), \
             patch.object(eventos, "_eventos_guardados", return_value=[]), \
             patch.object(eventos, "ensure_headers", return_value=ws):
            identifier = eventos.guardar_evento("2026-10-03", "=Aviso literal", "Para todos", "prueba")
        self.assertEqual(identifier, "prueba")
        self.assertEqual(len(writes), 1)
        self.assertEqual(writes[0][1]["value_input_option"], "RAW")
        row = dict(zip(eventos.HEADERS, writes[0][0][0]))
        self.assertEqual(row["Titulo"], "=Aviso literal")
        self.assertEqual(row["Fecha"], "2026-10-03")

    def test_repeated_identical_submission_does_not_duplicate(self):
        row = {"ID_Evento": "uno", "Fecha": "2026-10-03", "Titulo": "Reunión", "Detalle": "", "Revision": "r1"}
        with patch.object(eventos, "st", SimpleNamespace(session_state=DIRECTOR)), \
             patch.object(eventos, "_eventos_guardados", return_value=[row]), \
             patch.object(eventos, "ensure_headers") as write:
            self.assertEqual(eventos.guardar_evento("2026-10-03", "Reunión", id_evento="uno", revision_esperada="r1"), "uno")
            write.assert_not_called()

    def test_stale_edit_is_rejected_without_write(self):
        row = {"ID_Evento": "uno", "Fecha": "2026-10-03", "Titulo": "Reunión", "Detalle": "", "Revision": "r2"}
        with patch.object(eventos, "st", SimpleNamespace(session_state=DIRECTOR)), \
             patch.object(eventos, "_eventos_guardados", return_value=[row]), \
             patch.object(eventos, "ensure_headers") as write:
            with self.assertRaisesRegex(ValueError, "otra sesión"):
                eventos.guardar_evento("2026-10-03", "Nuevo", id_evento="uno", revision_esperada="r1")
            write.assert_not_called()

    def test_director_options_are_not_granted_to_specialists(self):
        director = cronogramas.perfil_especialista(DIRECTOR["nombre"], DIRECTOR["rol"])
        especialista = cronogramas.perfil_especialista("Abril de María Chable Ríos", "Psicología")
        self.assertEqual(len(director["escuelas"]), 8)
        self.assertTrue({"Sede", "Junta de Zona", "Junta de USAER", "Reunión Académica"}.issubset(cronogramas.lugares_cronograma(director)))
        self.assertNotIn("Junta de Zona", cronogramas.lugares_cronograma(especialista))
        with patch.object(cronogramas, "_leer_registros") as write:
            with self.assertRaises(ValueError):
                cronogramas.guardar_agenda(especialista["nombre"], "Psicología", "2026-10", especialista["escuelas"],
                    [{"fecha": "2026-10-02", "escuela": "Junta de Zona", "actividad": "Reunión"}])
            write.assert_not_called()

    def test_school_summary_never_exposes_other_schools_or_unassigned_people(self):
        rows = [
            {"Fecha": "2026-10-02", "Especialista": "María José Cupul Realpozo", "Área": "Psicología", "Escuela": "Ichcaanziho", "Actividad": "Evaluación", "ID_Publicacion": "privado"},
            {"Fecha": "2026-10-02", "Especialista": "Abril de María Chable Ríos", "Área": "Psicología", "Escuela": "Ichcaanziho", "Actividad": "No asignada"},
            {"Fecha": "2026-10-02", "Especialista": "María José Cupul Realpozo", "Área": "Psicología", "Escuela": "Damián Carmona", "Actividad": "Otra escuela"},
            {"Fecha": "2026-10-02", "Especialista": "Diego Peralta Torres", "Área": "Trabajo Social", "Escuela": "Ichcaanziho", "Actividad": "Seguimiento"},
        ]
        resumen = cronogramas.resumir_visitas_escuela(rows, "Ichcaanziho")
        self.assertEqual(len(resumen), 2)
        self.assertEqual(resumen[0]["Fecha"], "02/10/2026")
        self.assertEqual(resumen[0]["Día"], "Viernes")
        self.assertNotIn("ID_Publicacion", resumen[0])
        self.assertNotIn("Escuela", resumen[0])

    def test_director_can_save_all_four_extra_destinations(self):
        writes = []
        ws = SimpleNamespace(append_rows=lambda rows, **kw: writes.extend(rows))
        perfil = cronogramas.perfil_especialista(DIRECTOR["nombre"], DIRECTOR["rol"])
        destinos = ["Sede", "Junta de Zona", "Junta de USAER", "Reunión Académica"]
        agenda = [{"fecha": f"2026-10-{dia}", "escuela": lugar, "actividad": "Actividad directiva"}
                  for dia, lugar in zip(("02", "05", "06", "07"), destinos)]
        with patch.object(cronogramas, "_leer_registros", return_value=(ws, cronogramas.ENCABEZADOS_CRONOGRAMA, [])):
            resultado = cronogramas.guardar_agenda(perfil["nombre"], "Dirección", "2026-10", perfil["escuelas"], agenda)
        self.assertEqual(resultado["filas"], 4)
        self.assertEqual([row[4] for row in writes], destinos)

    def test_director_calendar_has_eight_schools_and_extra_destinations(self):
        app = AppTest.from_file(str(Path(__file__).parent / "fixtures" / "calendario_comun_app.py")).run()
        self.assertFalse(app.exception)
        opciones = next(s.options for s in app.selectbox if s.label == "Escuela o junta")
        self.assertEqual(len(opciones), 14)  # vacío + ocho escuelas + cinco lugares compatibles
        self.assertIn("Junta de Zona", opciones)
        self.assertIn("Reunión Académica", opciones)
        self.assertEqual(len([t for t in app.text_area if t.label == "Actividad"]), 21)

    def test_director_event_publication_is_visible_to_specialist_and_support(self):
        app = AppTest.from_file(str(Path(__file__).parent / "fixtures" / "calendario_comun_app.py")).run()
        next(t for t in app.text_input if t.label == "Actividad").set_value("Actividad común de prueba")
        next(t for t in app.date_input if t.label == "Fecha de la actividad").set_value(date(2026, 10, 5))
        next(b for b in app.button if b.label == "Publicar actividad para todos").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.session_state["eventos_simulados"]), 1)
        app.radio[0].set_value("Especialista").run()
        self.assertFalse(app.exception)
        self.assertTrue(any(w.value == "Actividad común de prueba" for w in app.markdown))
        app.radio[0].set_value("Apoyo").run()
        self.assertFalse(app.exception)
        self.assertTrue(any(w.value == "Actividad común de prueba" for w in app.markdown))
        tabla = app.dataframe[0].value
        self.assertEqual(len(tabla), 1)
        self.assertEqual(tabla.iloc[0]["Especialista"], "María José Cupul Realpozo")
        self.assertNotIn("Escuela", tabla.columns)
        self.assertNotIn("ID_Publicacion", tabla.columns)

    def test_specialist_fields_remain_editable_on_informative_event_day(self):
        app = AppTest.from_file(str(Path(__file__).parent / "fixtures" / "calendario_comun_app.py")).run()
        app.radio[0].set_value("Especialista").run()
        self.assertFalse(app.exception)
        self.assertEqual(len([s for s in app.selectbox if s.label == "Escuela o junta"]), 21)
        self.assertTrue(all(not s.disabled for s in app.selectbox if s.label == "Escuela o junta"))
        self.assertTrue(any("Segunda reunión académica" in m.value for m in app.markdown))


if __name__ == "__main__":
    unittest.main()

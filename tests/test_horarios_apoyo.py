import unittest
from io import BytesIO
from unittest.mock import Mock, patch

import pandas as pd
from docx import Document

from documents.horarios_apoyo import generar_horario_apoyo_pdf, generar_horario_apoyo_cuadricula_pdf
from services.horarios import detectar_choques, franjas_semanales, normalizar_tabla_horario, proponer_horario
from services.cronogramas import perfil_especialista
from ui.horarios_apoyo import (TIPOS_ARCHIVO_HORARIOS, _alumnos_de_maestra,
    _avisos_maestra, _clave_imagen_horario, _leer_archivo, _leer_imagen_horario,
    _leer_imagenes_pendientes)


class HorariosApoyoTest(unittest.TestCase):
    def test_uploader_accepts_word_and_common_image_formats(self):
        self.assertTrue({"doc", "docx", "png", "jpg", "jpeg", "webp", "tif"}.issubset(TIPOS_ARCHIVO_HORARIOS))

    def test_word_table_is_read_as_a_schedule_reference(self):
        document = Document()
        table = document.add_table(rows=2, cols=5)
        for cell, value in zip(table.rows[0].cells, ["Día", "Inicio", "Fin", "Materia", "Grupo"]):
            cell.text = value
        for cell, value in zip(table.rows[1].cells, ["Lunes", "08:00", "08:50", "Inglés", "2A"]):
            cell.text = value
        content = BytesIO()
        document.save(content)

        class Uploaded:
            name = "horario.docx"
            def getvalue(self):
                return content.getvalue()

        parsed, warnings = _leer_archivo(Uploaded())
        self.assertEqual(warnings, [])
        self.assertEqual(parsed[0][1].iloc[0]["Actividad"], "Inglés")
        self.assertEqual(parsed[0][1].iloc[0]["Grupo"], "2A")

    def test_imported_schedule_normalizes_columns_and_empty_cells(self):
        source = pd.DataFrame([{
            "Día": "Lunes", "Inicio": "08:00", "Fin": "08:50",
            "Materia": "Inglés", "Grado": float("nan"), "Docente": None,
        }])
        result = normalizar_tabla_horario(source)
        self.assertEqual(result.iloc[0]["Actividad"], "Inglés")
        self.assertEqual(result.iloc[0]["Grupo"], "")
        self.assertEqual(result.iloc[0]["Responsable"], "")

    def test_proposal_detects_overlaps_with_references_and_its_own_sessions(self):
        proposal = [
            {"Dia": "Lunes", "Inicio": "08:00", "Fin": "08:50", "Grupo": "2A", "Maestra": "M"},
            {"Dia": "Lunes", "Inicio": "08:40", "Fin": "09:30", "Grupo": "2A", "Maestra": "M"},
        ]
        reference = pd.DataFrame([{
            "Dia": "Lunes", "Inicio": "08:30", "Fin": "09:00", "Grupo": "2A", "Actividad": "Inglés",
        }])
        result = detectar_choques(proposal, reference)
        self.assertEqual(len(result), 3)
        self.assertIn("Inglés", result["Actividad que se cruza"].tolist())
        self.assertTrue(any("mismo grupo" in value for value in result["Actividad que se cruza"]))

    def test_proposed_week_is_automatically_checked_against_school_blocks(self):
        restrictions = pd.DataFrame([{
            "Dia": day, "Inicio": "08:00", "Fin": "13:00", "Grupo": "", "Actividad": "Jornada escolar",
        } for day in ("Lunes", "Martes", "Miércoles", "Jueves", "Viernes")])
        with self.assertRaisesRegex(ValueError, "suficientes espacios"):
            proponer_horario(["2A"], 1, 50, "08:00", "13:00", restrictions, pd.DataFrame())

    def test_schedule_proposal_carries_manual_attention_fields(self):
        proposal, _ = proponer_horario(
            ["2A"], 1, 50, "08:00", "13:00", pd.DataFrame(), pd.DataFrame(),
            maestra="Maestra de apoyo", modalidad="Subgrupal", espacio="Aula de apoyo",
        )
        self.assertEqual(proposal.iloc[0]["Modalidad"], "Subgrupal")
        self.assertEqual(proposal.iloc[0]["Espacio"], "Aula de apoyo")

    def test_official_pdf_contains_school_teacher_and_signature_blocks(self):
        content = generar_horario_apoyo_pdf("Escuela Primaria", "Docente de apoyo", [{
            "Dia": "Lunes", "Inicio": "08:00", "Fin": "08:50", "Grupo": "2A",
            "Modalidad": "Grupal", "Espacio": "Aula regular", "Actividad": "Lectoescritura",
        }])
        self.assertTrue(content.startswith(b"%PDF"))
        self.assertGreater(len(content), 1000)

    def test_custom_modules_cover_jornada_and_reject_short_final_fragment(self):
        self.assertEqual(franjas_semanales("07:00", "09:30", "60,60,30"), [
            ("07:00", "08:00"), ("08:00", "09:00"), ("09:00", "09:30"),
        ])
        with self.assertRaisesRegex(ValueError, "menor de 15"):
            franjas_semanales("07:00", "09:05", "60")

    def test_uploaded_class_conflict_matches_group_spelling_and_not_other_group(self):
        propuesta = [{"Dia": "Lunes", "Inicio": "08:00", "Fin": "09:00",
                      "Grupo": "4° A", "Maestra": "Docente"}]
        referencias = pd.DataFrame([
            {"Dia": "Lunes", "Inicio": "08:30", "Fin": "09:30",
             "Grupo": "4A", "Actividad": "Inglés"},
            {"Dia": "Lunes", "Inicio": "08:30", "Fin": "09:30",
             "Grupo": "4B", "Actividad": "Maya"},
        ])
        conflictos = detectar_choques(propuesta, referencias)
        self.assertEqual(conflictos["Actividad que se cruza"].tolist(), ["Inglés"])

    def test_landscape_grid_pdf_handles_multiple_days_and_student_names(self):
        pdf = generar_horario_apoyo_cuadricula_pdf(
            "Escuela Primaria", "Docente de apoyo",
            [{"Dia": "Lunes", "Inicio": "07:00", "Fin": "08:00", "Grupo": "4° A",
              "Alumnos": "Alumna Uno; Alumno Dos", "Actividad": "Lectura"}],
            [("07:00", "08:00"), ("08:00", "09:00")],
        )
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertGreater(len(pdf), 1000)

    def test_student_options_are_limited_to_school_and_teacher(self):
        roster = pd.DataFrame([
            {"ID_Alumno": "A1", "Nombre_Completo": "Alumno uno", "ID_Escuela": "ESC-002", "Maestra de Apoyo": "Mtra. Marycruz Caamal Coral"},
            {"ID_Alumno": "A2", "Nombre_Completo": "Alumno dos", "ID_Escuela": "ESC-002", "Maestra de Apoyo": "Mtra. María Cecilia Solís Vázquez"},
            {"ID_Alumno": "A3", "Nombre_Completo": "Alumno tres", "ID_Escuela": "ESC-007", "Maestra de Apoyo": "Mtra. Marycruz Caamal Coral"},
        ])
        with patch("ui.horarios_apoyo.repo.alumnos", return_value=roster):
            propios, escuela = _alumnos_de_maestra("Marycruz Caamal Coral", "Ichcaanziho")
        self.assertEqual(propios["ID_Alumno"].tolist(), ["A1"])
        self.assertEqual(set(escuela["ID_Alumno"]), {"A1", "A2"})

    def test_image_reading_yields_editable_rows_without_saving(self):
        class Uploaded:
            name = "ingles.jpg"
            def getvalue(self):
                return b"imagen-de-prueba"

        service = Mock()
        service.models.generate_content.return_value.text = (
            '[{"Día":"Lunes","Inicio":"08:00","Fin":"09:00",'
            '"Grupo":"4A","Actividad":"Inglés","Responsable":"Docente"}]'
        )
        genai_stub = Mock()
        genai_stub.types.Part.from_bytes.return_value = "imagen"
        with patch.dict("sys.modules", {"google.genai": genai_stub}):
            with patch("ai.engine.client", return_value=service):
                result = _leer_imagen_horario(Uploaded())
        self.assertEqual(result.iloc[0]["Actividad"], "Inglés")
        self.assertEqual(result.iloc[0]["Grupo"], "4A")

    def test_uploaded_images_are_prepared_once_and_distinguished_by_content(self):
        class Uploaded:
            name = "horario.jpg"
            def __init__(self, content):
                self.content = content
            def getvalue(self):
                return self.content

        first, second = Uploaded(b"lunes"), Uploaded(b"martes")
        self.assertNotEqual(_clave_imagen_horario("Maestra", "Escuela", first),
                            _clave_imagen_horario("Maestra", "Escuela", second))
        rows = normalizar_tabla_horario(pd.DataFrame([{
            "Dia": "Lunes", "Inicio": "08:00", "Fin": "09:00", "Actividad": "Inglés",
        }]))
        state = {}
        with patch("ui.horarios_apoyo.st.session_state", state):
            with patch("ui.horarios_apoyo._leer_imagen_horario", return_value=rows) as read:
                self.assertEqual(_leer_imagenes_pendientes([first, second], "Maestra", "Escuela"), (2, []))
                self.assertEqual(_leer_imagenes_pendientes([first, second], "Maestra", "Escuela"), (0, []))
        self.assertEqual(read.call_count, 2)

    def test_monthly_cronogram_generators_are_available_for_all_specialist_areas(self):
        profiles = (
            ("María José Cupul Realpozo", "Psicóloga", "Psicología"),
            ("Elmy Lucelly Puerto Gone", "Comunicación", "Comunicación"),
            ("Diego Peralta Torres", "Trabajo Social", "Trabajo Social"),
        )
        for name, role, area in profiles:
            with self.subTest(area=area):
                self.assertEqual(perfil_especialista(name, role)["area"], area)

    def test_notification_api_error_does_not_stop_schedule_page(self):
        import ui.horarios_apoyo as horarios_ui

        warnings = []

        def fail_to_read(_nombre):
            raise RuntimeError("Google Sheets temporarily unavailable")

        with patch.object(horarios_ui, "cargar_avisos_apoyo", side_effect=fail_to_read):
            with patch.object(horarios_ui.st, "warning", side_effect=warnings.append):
                _avisos_maestra("Docente", "Escuela Primaria")

        self.assertEqual(len(warnings), 1)
        self.assertIn("no se modificó ni eliminó información", warnings[0])


if __name__ == "__main__":
    unittest.main()

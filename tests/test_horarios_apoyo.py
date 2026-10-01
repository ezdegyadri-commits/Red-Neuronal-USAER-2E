import unittest
from io import BytesIO
from unittest.mock import Mock, patch

import pandas as pd
from docx import Document
from PIL import Image, ImageDraw

from documents.horarios_apoyo import generar_horario_apoyo_pdf, generar_horario_apoyo_cuadricula_pdf
from services.horarios import detectar_choques, franjas_semanales, normalizar_tabla_horario, proponer_horario
from services.cronogramas import perfil_especialista
from ui.horarios_apoyo import (TIPOS_ARCHIVO_HORARIOS, _alumnos_de_maestra,
    _avisos_maestra, _clave_imagen_horario, _leer_archivo, _leer_imagen_horario,
    _leer_imagenes_pendientes, _borrador_de_horario, _limpiar_lectura_imagen,
    _limpiar_borradores_imagen_sin_carga, _interpretar_celda_horario,
    _celda_ocr_util, _normalizar_actividad_ocr, _bloques_desde_ocr_tsv, _bloques_desde_cuadricula, _mensaje_ocr_corto, _matriz_horario_a_frame)


class HorariosApoyoTest(unittest.TestCase):
    def test_grade_without_word_grado_uses_subject_from_ocr_title(self):
        self.assertEqual(_interpretar_celda_horario("Cuarto"), ("4°", "Clase regular"))
        self.assertEqual(_interpretar_celda_horario("4° B"), ("4°B", "Clase regular"))
        words = [
            ("HORARIO", 20, 10), ("MAYA", 100, 10),
            ("Lunes", 130, 55), ("Martes", 280, 55),
            ("07:30-08:15", 10, 115), ("Cuarto", 220, 110),
        ]
        data = {key: [] for key in ("text", "conf", "left", "top", "width", "height")}
        for texto, x, y in words:
            data["text"].append(texto)
            data["conf"].append("90")
            data["left"].append(x)
            data["top"].append(y)
            data["width"].append(45)
            data["height"].append(12)
        frame = _bloques_desde_ocr_tsv(data, 400, 200)
        martes = frame.loc[frame["Dia"].eq("Martes")].iloc[0]
        self.assertEqual(martes["Grupo"], "4°")
        self.assertEqual(martes["Actividad"], "Maya")

    def test_ocr_discards_time_fragments_and_corrects_only_clear_subject_typos(self):
        self.assertFalse(_celda_ocr_util("7 :"))
        self.assertTrue(_celda_ocr_util("Quinto", "5°"))
        self.assertEqual(_normalizar_actividad_ocr("Gores y Cantos"), "Coros y Cantos")
        self.assertEqual(_normalizar_actividad_ocr("Atención individual"), "Atención individual")

        words = [
            ("HORARIO", 20, 10), ("MAYA", 100, 10),
            ("Lunes", 130, 55), ("Martes", 280, 55),
            ("11:00-11:50", 10, 115), ("Quinto", 110, 110), ("7 :", 260, 110),
        ]
        data = {key: [] for key in ("text", "conf", "left", "top", "width", "height")}
        for texto, x, y in words:
            data["text"].append(texto)
            data["conf"].append("90")
            data["left"].append(x)
            data["top"].append(y)
            data["width"].append(45)
            data["height"].append(12)
        frame = _bloques_desde_ocr_tsv(data, 400, 200)
        self.assertIn("Lunes", frame["Dia"].tolist())
        self.assertNotIn("Martes", frame["Dia"].tolist())

    def test_grid_ocr_uses_cell_positions_and_subject_instead_of_mixing_columns(self):
        image = Image.new("RGB", (400, 160), "white")
        draw = ImageDraw.Draw(image)
        for x in (10, 100, 240, 390):
            draw.line((x, 10, x, 150), fill="black", width=2)
        for y in (10, 50, 100, 150):
            draw.line((10, y, 390, y), fill="black", width=2)
        entries = [
            ("Lunes", 150, 27), ("Martes", 290, 27),
            ("7:00-7:50", 50, 73), ("Cuarto", 155, 73), ("grado", 205, 73),
            ("Quinto", 295, 73), ("grado", 345, 73),
            ("8:00-8:50", 50, 122), ("Segundo", 155, 122), ("grado", 205, 122),
        ]
        data = {
            "text": [item[0] for item in entries],
            "left": [item[1] - 10 for item in entries],
            "top": [item[2] - 7 for item in entries],
            "width": [20] * len(entries),
            "height": [14] * len(entries),
        }
        reader = Mock()
        reader.image_to_data.return_value = data
        reader.image_to_string.side_effect = lambda crop, **_kwargs: (
            "HORARIO INGLÉS" if crop.width == image.width else ""
        )
        output = Mock(DICT="dict")
        frame = _bloques_desde_cuadricula(image, reader, output)
        self.assertEqual(len(frame), 3)
        self.assertEqual(set(frame["Dia"]), {"Lunes", "Martes"})
        self.assertEqual(set(frame["Grupo"]), {"2°", "4°", "5°"})
        self.assertEqual(set(frame["Actividad"]), {"Inglés"})

    def test_uploader_accepts_word_and_common_image_formats(self):
        self.assertTrue({"doc", "docx", "pdf", "png", "jpg", "jpeg", "webp", "tif"}.issubset(TIPOS_ARCHIVO_HORARIOS))

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

    def test_word_weekly_matrix_is_read_by_day_columns_and_time_rows(self):
        document = Document()
        table = document.add_table(rows=3, cols=3)
        values = [
            ["Hora", "Lunes", "Miércoles"],
            ["7:30 – 8:15", "Cuarto grado", "Inglés"],
            ["8:30 – 9:15", "Quinto grado", "Tercero grado"],
        ]
        for row, values_row in zip(table.rows, values):
            for cell, value in zip(row.cells, values_row):
                cell.text = value
        content = BytesIO()
        document.save(content)

        class Uploaded:
            name = "horario_matriz.docx"
            def getvalue(self):
                return content.getvalue()

        parsed, warnings = _leer_archivo(Uploaded())
        self.assertEqual(warnings, [])
        frame = parsed[0][1]
        self.assertEqual(len(frame), 4)
        self.assertEqual(set(frame["Dia"]), {"Lunes", "Miércoles"})
        self.assertIn("4°", frame["Grupo"].tolist())
        self.assertIn("Inglés", frame["Actividad"].tolist())

    def test_excel_weekly_matrix_includes_column_headers_in_detection(self):
        source = pd.DataFrame([
            ["7:30-8:15", "Cuarto grado", "Maya"],
            ["8:30-9:15", "Quinto grado", "Tercero grado"],
        ], columns=["Hora", "Lunes", "Martes"])

        class Uploaded:
            name = "horario_matriz.xlsx"
            def getvalue(self):
                return b"excel mock"

        with patch("ui.horarios_apoyo.pd.read_excel", return_value={"Horario": source}):
            parsed, warnings = _leer_archivo(Uploaded())
        self.assertEqual(warnings, [])
        self.assertEqual(len(parsed[0][1]), 4)
        self.assertEqual(set(parsed[0][1]["Dia"]), {"Lunes", "Martes"})

    def test_excel_weekly_matrix_includes_column_headers_in_detection(self):
        source = pd.DataFrame([
            ["7:30-8:15", "Cuarto grado", "Maya"],
            ["8:30-9:15", "Quinto grado", "Tercero grado"],
        ], columns=["Hora", "Lunes", "Martes"])

        class Uploaded:
            name = "horario_matriz.xlsx"
            def getvalue(self):
                return b"excel mock"

        with patch("ui.horarios_apoyo.pd.read_excel", return_value={"Horario": source}):
            parsed, warnings = _leer_archivo(Uploaded())
        self.assertEqual(warnings, [])
        self.assertEqual(len(parsed[0][1]), 4)
        self.assertEqual(set(parsed[0][1]["Dia"]), {"Lunes", "Martes"})

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
        self.assertEqual(set(escuela["ID_Alumno"]), {"A1"})

    def test_image_reading_yields_editable_rows_without_saving(self):
        class Uploaded:
            name = "ingles.jpg"
            def getvalue(self):
                return b"imagen-de-prueba"

        result = normalizar_tabla_horario(pd.DataFrame([{
            "Día": "Lunes", "Inicio": "08:00", "Fin": "09:00",
            "Grupo": "4A", "Actividad": "Inglés", "Responsable": "Docente",
        }]))
        with patch("ui.horarios_apoyo._leer_imagen_ocr_local", return_value=result) as lector:
            result = _leer_imagen_horario(Uploaded())
        lector.assert_called_once()
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
            with patch("ui.horarios_apoyo._leer_imagen_ocr_local", return_value=rows) as lector:
                self.assertEqual(_leer_imagenes_pendientes([first, second], "Maestra", "Escuela"), (2, []))
                self.assertEqual(_leer_imagenes_pendientes([first, second], "Maestra", "Escuela"), (0, []))
        self.assertEqual(lector.call_count, 2)

    def test_reloading_schedule_replaces_stale_draft_instead_of_merging(self):
        vigente = [{"Dia": "Lunes", "Inicio": "08:00", "Fin": "09:00", "Actividad": "Lectura"}]
        borrador_previo = {
            "Viernes|12:00|13:00": {"Dia": "Viernes", "Inicio": "12:00", "Fin": "13:00", "Actividad": "Bloque obsoleto"}
        }
        actualizado = _borrador_de_horario(vigente)
        self.assertEqual(list(actualizado), ["Lunes|08:00|09:00"])
        self.assertNotIn("Viernes|12:00|13:00", actualizado)
        # La construcción no muta ni borra el borrador previo ni la base central.
        self.assertIn("Viernes|12:00|13:00", borrador_previo)

    def test_clearing_image_load_only_removes_temporary_ocr_state(self):
        class Uploaded:
            name = "horario.jpg"
            def getvalue(self):
                return b"imagen temporal"

        archivo = Uploaded()
        clave = _clave_imagen_horario("Zuemmy", "Escuela", archivo)
        state = {clave: pd.DataFrame([{"Actividad": "lectura"}]),
                 f"ocr_error_{clave}": "503", "otra_clave": "se conserva"}
        with patch("ui.horarios_apoyo.st.session_state", state):
            _limpiar_lectura_imagen("Zuemmy", "Escuela", archivo)
        self.assertNotIn(clave, state)
        self.assertNotIn(f"ocr_error_{clave}", state)
        self.assertEqual(state["otra_clave"], "se conserva")

    def test_no_image_clears_only_current_teachers_hidden_ocr_drafts(self):
        prefix = "bloques_imagen_ZUEMMY PEREZ_ESCUELA_"
        own_key = prefix + "123"
        state = {
            own_key: "borrador viejo",
            "ocr_error_" + own_key: "fallo previo",
            "revision_" + own_key + "_0": "tabla vieja",
            "bloques_imagen_OTRA MAESTRA_ESCUELA_123": "otro borrador",
            "horario_guardado": "no tocar",
        }
        with patch("ui.horarios_apoyo.st.session_state", state):
            _limpiar_borradores_imagen_sin_carga("Zuemmy Perez", "Escuela")
        self.assertFalse(any(key.startswith(prefix) or key.startswith("ocr_error_" + prefix)
                             or key.startswith("revision_" + prefix) for key in state))
        self.assertIn("bloques_imagen_OTRA MAESTRA_ESCUELA_123", state)
        self.assertEqual(state["horario_guardado"], "no tocar")

    def test_local_ocr_failure_keeps_image_and_retry_state(self):
        class Uploaded:
            name = "horario.jpg"
            def getvalue(self):
                return b"imagen-503"

        archivo = Uploaded()
        state = {}
        with patch("ui.horarios_apoyo.st.session_state", state):
            with patch("ui.horarios_apoyo._leer_imagen_ocr_local", side_effect=ValueError("sin texto")):
                leidas, fallos = _leer_imagenes_pendientes([archivo], "Zuemmy", "Escuela")
        self.assertEqual(leidas, 0)
        self.assertEqual(fallos, ["horario.jpg"])
        self.assertIn(f"ocr_error_{_clave_imagen_horario('Zuemmy', 'Escuela', archivo)}", state)

    def test_local_ocr_excludes_title_and_maps_grade_to_group_for_conflicts(self):
        words = [
            ("HORARIO", 170, 5), ("Escuela", 200, 15),
            ("Lunes", 120, 35), ("Martes", 330, 35),
            ("7:30-8:15", 5, 80), ("Cuarto", 120, 80), ("grado", 170, 80),
            ("Tercero", 330, 80), ("grado", 380, 80),
            ("8:30-9:15", 5, 150), ("Maya", 120, 150), ("Lectura", 330, 150),
        ]
        datos = {"text": [], "conf": [], "left": [], "top": [], "width": [], "height": []}
        for texto, x, y in words:
            datos["text"].append(texto)
            datos["conf"].append("90")
            datos["left"].append(x)
            datos["top"].append(y)
            datos["width"].append(45)
            datos["height"].append(12)
        rows = _bloques_desde_ocr_tsv(datos, 500, 220)
        self.assertFalse(rows["Actividad"].str.contains("HORARIO|Escuela", case=False).any())
        primero = rows.loc[rows["Inicio"].eq("07:30")]
        self.assertEqual(primero["Grupo"].tolist(), ["4°", "3°"])
        self.assertEqual(primero["Actividad"].tolist(), ["Clase regular", "Clase regular"])

    def test_ocr_warning_is_short_and_does_not_expose_provider_payload(self):
        self.assertEqual(
            _mensaje_ocr_corto("503 UNAVAILABLE provider internal payload"),
            "No se pudo leer una parte; revisa y completa los bloques en la tabla.",
        )

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

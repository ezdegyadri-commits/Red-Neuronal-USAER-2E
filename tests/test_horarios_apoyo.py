import unittest

import pandas as pd

from documents.horarios_apoyo import generar_horario_apoyo_pdf
from services.horarios import detectar_choques, normalizar_tabla_horario, proponer_horario
from services.cronogramas import perfil_especialista


class HorariosApoyoTest(unittest.TestCase):
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

    def test_monthly_cronogram_generators_are_available_for_all_specialist_areas(self):
        profiles = (
            ("María José Cupul Realpozo", "Psicóloga", "Psicología"),
            ("Elmy Lucelly Puerto Gone", "Comunicación", "Comunicación"),
            ("Diego Peralta Torres", "Trabajo Social", "Trabajo Social"),
        )
        for name, role, area in profiles:
            with self.subTest(area=area):
                self.assertEqual(perfil_especialista(name, role)["area"], area)


if __name__ == "__main__":
    unittest.main()


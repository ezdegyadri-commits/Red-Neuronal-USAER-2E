"""El Anexo IV debe ofrecer captura a todos los perfiles con escuela asignada."""

import unittest
from contextlib import nullcontext
from datetime import date
from unittest.mock import patch

import pandas as pd

from ui import sugerencias


class SugerenciasAccessTest(unittest.TestCase):
    def test_support_specialist_and_director_can_save_new_suggestion(self):
        alumnos = pd.DataFrame([{
            "ID_Alumno": "ALU-001", "Nombre_Completo": "Alumno de prueba",
            "Grado": "4°", "Grupo": "A", "ID_Escuela": "ESC-002",
            "Nombre_Escuela": "Ichcaanziho",
        }])
        historial = pd.DataFrame(columns=["ID_Anexo4", "Nombre_Alumno", "Estado"])
        for nombre, rol in (
            ("Mtra. Marycruz Caamal Coral", "Apoyo"),
            ("Elmy Lucelly Puerto Gone", "Comunicacion"),
            ("Psic. Edgar Adrian Yam Briceño", "Director"),
        ):
            with self.subTest(rol=rol):
                with patch.object(sugerencias.st, "session_state", {"nombre": nombre, "rol": rol}):
                    with patch.object(sugerencias, "hero"):
                        with patch.object(sugerencias, "escuelas_asignadas", return_value=["Ichcaanziho"]):
                            with patch.object(sugerencias.st, "selectbox", side_effect=["Ichcaanziho", "ALU-001"]):
                                with patch.object(sugerencias.st, "expander", return_value=nullcontext()) as expander:
                                    with patch.object(sugerencias.st, "text_input", return_value="Aprendizaje"):
                                        with patch.object(sugerencias.st, "text_area", side_effect=lambda label, **kwargs: "Leer en grupo" if label == "Sugerencia nueva" else ""):
                                            with patch.object(sugerencias.st, "date_input", return_value=date(2026, 9, 28)):
                                                with patch.object(sugerencias.st, "button", side_effect=lambda label, **kwargs: label == "Guardar nueva sugerencia") as button:
                                                    with patch.object(sugerencias.repo, "anexo4", return_value=historial):
                                                        with patch.object(sugerencias.repo, "save_anexo4", return_value="AN4-001") as save:
                                                            with patch.object(sugerencias.repo, "ensure_expediente"):
                                                                with patch.object(sugerencias.repo, "link_record"):
                                                                    with patch.object(sugerencias.repo, "timeline"):
                                                                        with patch.object(sugerencias, "anexo4_html", return_value="<html></html>"):
                                                                            with patch.object(sugerencias, "anexo4_pdf", return_value=b"%PDF"):
                                                                                with patch.object(sugerencias.components, "html"):
                                                                                    with patch.object(sugerencias.st, "download_button"):
                                                                                        with patch.object(sugerencias.st, "rerun"):
                                                                                            sugerencias.anexo4_page(alumnos)
                expander.assert_called_once_with("➕ Añadir nueva sugerencia", expanded=True)
                self.assertTrue(any(call.args[0] == "Guardar nueva sugerencia" for call in button.call_args_list))
                self.assertEqual(save.call_count, 1)
                self.assertEqual(save.call_args.args[0]["ID_Alumno"], "ALU-001")
                self.assertEqual(save.call_args.args[0]["Quien_Brinda_Sugerencias"], nombre)


if __name__ == "__main__":
    unittest.main()


from io import BytesIO
import sys
from types import ModuleType
import unittest
from unittest.mock import patch

import pandas as pd
from openpyxl import load_workbook

# The repository imports the application's Google connector at module load.
# Tests replace that boundary so they stay local and never contact Google.
google_stub = ModuleType("data.google")
for function_name in (
    "clear_cache", "df_sheet", "append_dict", "ensure_sheet", "ensure_headers",
    "google_append_rows_raw", "next_numeric_id", "read_personal_responses",
    "retry_google", "worksheet",
):
    setattr(google_stub, function_name, lambda *args, **kwargs: None)
sys.modules.setdefault("data.google", google_stub)

from data import repository
from documents.reportes import generar_formato_personal


def _response(name, role, email, schools, school_cct="", **extra):
    row = {
        "Dirección de correo electrónico": email,
        "2. Zona": "001",
        "3. N° USAER": "02 E",
        "4. Clave de Centro de Trabajo de la USAER": "31FUA0002Y",
        "5. Turno": "Matutino",
        "6. Nombre del docente de apoyo/paradocentes (Apellido Paterno, Materno y Nombres)": name,
        "7. Sexo": "Mujer",
        "8. Función que desempeña": role,
        "9. Teléfono (10 dígitos)": "999 123 4567",
        "10. Base/Contrato": "Base",
        "11. Sostenimiento": "Estatal",
        "12. Horario de trabajo (Ej. 07:00 a 12:00)": "07:00 a 12:00",
        "13. ¿Presenta alguna Discapacidad?": "No",
        "14. En caso afirmativo, elija la categoría de discapacidad (Elija \"Ninguna\" si no aplica)": "Ninguna",
        "15. ¿Es usted Maya Hablante?": "No",
        "16. Número de escuelas (Progresivo)": str(len(schools.split(";"))),
        "17. Nombre de la escuela que atiende": schools,
        "18. Clave de Centro de Trabajo de la escuela regular": school_cct,
        "19. Nivel educativo de la escuela regular": "Primaria",
        "20. Modalidad (general, indígena, técnica, telesecundaria, etc.)": "General",
        "21. Horario en el que la escuela regular permanece abierta": "07:00 a 12:00",
        "22. No. Total de grupos que tiene la escuela": "12",
        "23. DIRECCIÓN de la escuela (Calle, número, cruzamiento, colonia, CP.)": "Calle 1",
        "24. Localidad de la escuela regular": "Mérida",
        "25. Municipio de la escuela regular": "Mérida",
    }
    row.update(extra)
    return row


class PersonalFormSourceTests(unittest.TestCase):
    @patch("data.repository.read_personal_responses")
    def test_response_sheet_is_mapped_without_reading_empty_central_tab(self, read_source):
        read_source.return_value = [
            _response("Apoyo Apellido Nombre", "Maestro de Apoyo", "apoyo@example.com", "Ichcaanzihó", "31DPR0232G"),
            _response("Administrativo Apellido Nombre", "Administrativo", "admin@example.com", "Damián Carmona"),
            _response("Equipo Apellido Nombre", "Trabajador Social", "ts@example.com", "Damián Carmona; Ichcaanzihó"),
        ]
        with patch("data.repository.personal", side_effect=AssertionError("no debe recurrir a la tabla vacía")):
            frame = repository.personal_para_formato()

        self.assertEqual(len(frame), 3)
        self.assertEqual(frame.iloc[0]["Email"], "apoyo@example.com")
        self.assertEqual(frame.iloc[0]["Telefono"], "9991234567")
        self.assertTrue(frame["Fuente_Formulario"].all())

    def test_generator_writes_response_fields_in_official_order(self):
        people = pd.DataFrame([
            {
                "ID_Personal": "apoyo@example.com", "Nombre_Completo": "Apoyo Apellido Nombre",
                "Rol": "Maestro de Apoyo", "Email": "apoyo@example.com", "Telefono": "9991234567",
                "Sexo": "Mujer", "Base_Contrato": "Base", "Sostenimiento": "Estatal",
                "Presenta_Discapacidad": "No", "Horario": "07:00 a 12:00", "Discapacidad": "Ninguna",
                "Maya_Hablante": "No", "Zona": "001", "Numero_USAER": "02-E",
                "CCT_USAER": "31FUA0002Y", "Turno_USAER": "Matutino", "Escuelas_Atendidas": "Ichcaanzihó",
                "CCT_Escuela": "31DPR0232G", "Nivel_Escuela": "Primaria", "Modalidad_Escuela": "General",
                "Horario_Escuela": "07:00 a 12:00", "Grupos_Escuela": "12", "Direccion_Escuela": "Calle 1",
                "Localidad_Escuela": "Mérida", "Municipio_Escuela": "Mérida", "Escuela_Asignada": "Ichcaanzihó",
                "Fuente_Formulario": True,
            },
            {
                "ID_Personal": "admin@example.com", "Nombre_Completo": "Administrativo Apellido Nombre",
                "Rol": "Administrativo", "Email": "admin@example.com", "Telefono": "9991234568",
                "Sexo": "Mujer", "Base_Contrato": "Base", "Sostenimiento": "Estatal",
                "Presenta_Discapacidad": "No", "Horario": "07:00 a 12:00", "Discapacidad": "Ninguna",
                "Maya_Hablante": "No", "Zona": "001", "Numero_USAER": "02-E",
                "CCT_USAER": "31FUA0002Y", "Turno_USAER": "Matutino", "Escuelas_Atendidas": "",
                "Fuente_Formulario": True,
            },
        ])
        result = generar_formato_personal(people, pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
        workbook = load_workbook(BytesIO(result), data_only=False)
        sheet = workbook["1. SÁBANA DE PERSONAL DE USAER"]

        self.assertEqual(sheet["H10"].value, "Administrativo")
        self.assertEqual(sheet["Q10"].value, "SEDE")
        self.assertIsNone(sheet["I10"].hyperlink)
        self.assertEqual(sheet["H11"].value, "Maestro de Apoyo")
        self.assertEqual(sheet["S11"].value, "31DPR0232G")
        self.assertEqual(sheet["B11"].number_format, "@")

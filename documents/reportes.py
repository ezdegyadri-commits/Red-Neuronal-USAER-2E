from copy import copy
from datetime import date
from io import BytesIO
from pathlib import Path
import unicodedata

import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side


TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "assets" / "plantillas"
PADRON_TEMPLATE = "padron_usaer_2026_2027.xlsx"
PERSONAL_TEMPLATE = "personal_usaer_2026_2027.xlsx"

SERVICE = {
    "zona": "001",
    "numero": "02-E",
    "cct": "31FUA0002Y",
    "turno": "Matutino",
}


def _text(value):
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def _norm(value):
    return "".join(
        char for char in unicodedata.normalize("NFD", _text(value).upper())
        if unicodedata.category(char) != "Mn"
    )


def _value(row, *keys, default=""):
    for key in keys:
        if key in row and _text(row.get(key)):
            return _text(row.get(key))
    return default


def _yes(value):
    return _norm(value) in {"SI", "S", "YES", "TRUE", "1"}



def _edad_al_primero_de_septiembre(curp):
    curp = _text(curp).upper()
    try:
        year_two_digits = int(curp[4:6])
        nacimiento = date(
            2000 + year_two_digits if year_two_digits <= 26 else 1900 + year_two_digits,
            int(curp[6:8]),
            int(curp[8:10]),
        )
    except (ValueError, IndexError):
        return ""
    corte = date(2026, 9, 1)
    return corte.year - nacimiento.year - (
        (corte.month, corte.day) < (nacimiento.month, nacimiento.day)
    )

def _school_index(escuelas):
    if escuelas is None or escuelas.empty:
        return {}
    resultado = {}
    for _, row in escuelas.fillna("").iterrows():
        registro = row.to_dict()
        for key in ("ID_Escuela", "Nombre_Escuela"):
            valor = _norm(registro.get(key, ""))
            if valor:
                resultado[valor] = registro
    return resultado


def _copy_row_style(worksheet, source_row, target_row):
    for column in range(1, worksheet.max_column + 1):
        source = worksheet.cell(source_row, column)
        target = worksheet.cell(target_row, column)
        if source.has_style:
            target._style = copy(source._style)
        if source.number_format:
            target.number_format = source.number_format
        if source.alignment:
            target.alignment = copy(source.alignment)
        if source.fill:
            target.fill = copy(source.fill)
        if source.font:
            target.font = copy(source.font)
        if source.border:
            target.border = copy(source.border)
        if source.protection:
            target.protection = copy(source.protection)
    worksheet.row_dimensions[target_row].height = (
        worksheet.row_dimensions[source_row].height
    )


def _prepare_rows(
    worksheet, first_row, total_rows, source_row, template_last_row
):
    required_last = max(
        template_last_row, first_row + max(total_rows, 1) - 1
    )
    for row in range(template_last_row + 1, required_last + 1):
        _copy_row_style(worksheet, source_row, row)
    for row in range(first_row, required_last + 1):
        for column in range(1, worksheet.max_column + 1):
            worksheet.cell(row, column).value = None


def _style_header(cell, fill):
    cell.fill = PatternFill("solid", fgColor=fill)
    cell.font = Font(name="Arial", size=8, bold=True)
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    cell.border = Border(
        left=Side(style="thin", color="666666"),
        right=Side(style="thin", color="666666"),
        top=Side(style="thin", color="666666"),
        bottom=Side(style="thin", color="666666"),
    )


def _crear_padron_base():
    workbook = Workbook()
    instrucciones = workbook.active
    instrucciones.title = "INSTRUCTIVO"
    instrucciones["A1"] = "PADRÓN DE ALUMNOS ATENDIDOS EN EL CURSO ESCOLAR 2026-2027"
    instrucciones["A3"] = "El nombre inicia con apellido paterno, materno y nombre(s)."
    instrucciones["A4"] = "La CURP debe contener 18 caracteres."
    worksheet = workbook.create_sheet("ALUMNOS USAER")
    worksheet.merge_cells("A3:Y3")
    worksheet["A3"] = "PADRÓN DE ALUMNOS ATENDIDOS POR LA USAER CURSO ESCOLAR 2026-2027"
    worksheet["A3"].font = Font(name="Arial", size=12, bold=True)
    worksheet["A3"].alignment = Alignment(horizontal="center")
    headers = [
        "No.", "Zona", "N° USAER", "Clave de USAER", "Escuela atendida",
        "Turno", "CCT de la escuela", "Dirección de la escuela", "Localidad",
        "Municipio", "Apellido paterno, materno y nombre(s) del alumno",
        "CURP (18 dígitos)", "Edad (1 sept)", "Sexo", "Discapacidad o condición",
        "Preescolar", "Primaria", "Secundaria", "Situación del alumno",
        "Tipo de atención", "Lengua indígena / mayahablante",
        "Afrodescendiente", "Migrante", "", "",
    ]
    for column, header in enumerate(headers, start=1):
        cell = worksheet.cell(6, column)
        cell.value = header
        _style_header(cell, "B4A7C5")
        worksheet.column_dimensions[cell.column_letter].width = 15
        worksheet.cell(8, column).border = Border(
            left=Side(style="thin", color="999999"),
            right=Side(style="thin", color="999999"),
            top=Side(style="thin", color="999999"),
            bottom=Side(style="thin", color="999999"),
        )
    worksheet.row_dimensions[6].height = 58
    worksheet.freeze_panes = "A7"
    return workbook


def _crear_personal_base():
    workbook = Workbook()
    instrucciones = workbook.active
    instrucciones.title = "INSTRUCCIONES"
    instrucciones["A1"] = "FORMATO DE PERSONAL DE USAER 2026-2027"
    worksheet = workbook.create_sheet("1. SÁBANA DE PERSONAL DE USAER")
    worksheet.merge_cells("A3:CP3")
    worksheet["A3"] = "SÁBANA DE PERSONAL DE USAER"
    worksheet["A3"].font = Font(name="Arial", size=12, bold=True)
    worksheet["A3"].alignment = Alignment(horizontal="center")
    worksheet["A5"] = "Fecha de llenado:"
    headers = [
        "No.", "Zona", "N° USAER", "Clave de USAER", "Turno",
        "Nombre del docente de apoyo/paradocentes", "Sexo", "Función",
        "Correo electrónico", "Teléfono", "Base/Contrato", "Sostenimiento",
        "¿Presenta alguna discapacidad?", "Horario de trabajo", "¿Cuál?",
        "¿Es maya hablante?", "Número de escuela", "Nombre de la escuela que atiende",
        "CCT de la escuela regular", "Nivel educativo", "Modalidad",
        "Horario de la escuela", "Total de grupos", "Dirección de la escuela",
        "Localidad", "Municipio", "Nombre del director(a)", "Teléfono del director",
        "Nombre del supervisor(a)", "Teléfono del supervisor", "Zona escolar",
        "Sector", "Región", "Alumnos grupales", "Alumnos individuales",
        "Total alumnos", "EPP vigentes", "EPP anteriores", "Total EPP",
        "Ceguera H", "Ceguera M", "Baja visión H", "Baja visión M", "Sordera H",
        "Sordera M", "Hipoacusia H", "Hipoacusia M", "Sordoceguera H",
        "Sordoceguera M", "Motriz H", "Motriz M", "Intelectual H", "Intelectual M",
        "Psicosocial H", "Psicosocial M", "TEA H", "TEA M", "Múltiple H",
        "Múltiple M", "TDA H", "TDA M", "TDAH H", "TDAH M", "AS intelectual H",
        "AS intelectual M", "AS artístico H", "AS artístico M", "AS psicomotriz H",
        "AS psicomotriz M", "AS socioafectiva H", "AS socioafectiva M",
        "AS creativa H", "AS creativa M", "Aprendizaje H", "Aprendizaje M",
        "Conducta H", "Conducta M", "Comunicación H", "Comunicación M",
        "Otras condiciones H", "Otras condiciones M", "Otras total",
        "Total alumnos H", "Total alumnos M", "Total alumnos",
        "Maya hablantes H", "Maya hablantes M", "Afrodescendientes H",
        "Afrodescendientes M", "Migrantes H", "Migrantes M",
        "Doble vulnerabilidad H", "Doble vulnerabilidad M",
        "Doble vulnerabilidad total",
    ]
    for column, header in enumerate(headers, start=1):
        cell = worksheet.cell(8, column)
        cell.value = header
        fill = "9DC3E6" if column <= 5 else "B6D7A8" if column <= 16 else "F8CBAD"
        _style_header(cell, fill)
        worksheet.column_dimensions[cell.column_letter].width = 15
        worksheet.cell(10, column).border = Border(
            left=Side(style="thin", color="999999"),
            right=Side(style="thin", color="999999"),
            top=Side(style="thin", color="999999"),
            bottom=Side(style="thin", color="999999"),
        )
    worksheet.row_dimensions[8].height = 72
    worksheet.freeze_panes = "A9"
    return workbook


def _workbook_from_template(filename):
    path = TEMPLATES_DIR / filename
    if path.exists():
        return load_workbook(BytesIO(path.read_bytes()))
    if filename == PADRON_TEMPLATE:
        return _crear_padron_base()
    if filename == PERSONAL_TEMPLATE:
        return _crear_personal_base()
    raise FileNotFoundError(f"No se encontró la plantilla oficial: {filename}")


def _to_excel(workbook):
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def generar_padron_usaer(alumnos, escuelas):
    """Genera el padrón USAER en la plantilla oficial de supervisión."""
    workbook = _workbook_from_template(PADRON_TEMPLATE)
    worksheet = workbook["ALUMNOS USAER"]
    registros = [] if alumnos is None else alumnos.fillna("").to_dict("records")
    catalogo = _school_index(escuelas)
    first_row = 8
    _prepare_rows(worksheet, first_row, len(registros), first_row, 30)

    for number, student in enumerate(registros, start=1):
        row = first_row + number - 1
        school = catalogo.get(_norm(student.get("ID_Escuela", "")), {})
        level = _value(student, "Nivel_Educativo", default=_value(school, "Nivel"))
        grade = _value(student, "Grado")
        level_norm = _norm(level)
        values = {
            1: number,
            2: SERVICE["zona"],
            3: SERVICE["numero"],
            4: SERVICE["cct"],
            5: _value(student, "Nombre_Escuela", default=_value(school, "Nombre_Escuela", default=student.get("ID_Escuela", ""))),
            6: _value(student, "Turno_Escuela", default=_value(school, "Turno")),
            7: _value(student, "CCT_Escuela", default=_value(school, "CCT")),
            8: _value(student, "Direccion_Escuela", default=_value(school, "Direccion", "Dirección")),
            9: _value(student, "Localidad_Escuela", default=_value(school, "Localidad")),
            10: _value(student, "Municipio_Escuela", default=_value(school, "Municipio")),
            11: _value(student, "Nombre_Completo"),
            12: _value(student, "CURP"),
            13: _edad_al_primero_de_septiembre(student.get("CURP", "")),
            14: _value(student, "Sexo"),
            15: _value(student, "Condicion_Discapacidad"),
            19: _value(student, "Situacion_Alumno"),
            20: _value(student, "Tipo_Atencion"),
            21: _value(student, "Lengua_Indigena_Mayahablante"),
            22: _value(student, "Afrodescendiente"),
            23: _value(student, "Migrante"),
        }
        if "PREESCOLAR" in level_norm:
            values[16] = grade
        elif "SECUNDARIA" in level_norm:
            values[18] = grade
        else:
            values[17] = grade
        for column, value in values.items():
            worksheet.cell(row, column).value = _text(value)
        worksheet.cell(row, 2).number_format = "@"
    return _to_excel(workbook)


def _students_for_school(alumnos, school_id):
    if alumnos is None or alumnos.empty:
        return []
    target = _norm(school_id)
    return [
        row for row in alumnos.fillna("").to_dict("records")
        if _norm(row.get("ID_Escuela", "")) == target
    ]


def _sex_count(records, predicate=lambda record: True):
    selected = [row for row in records if predicate(row)]
    men = sum(_norm(row.get("Sexo", "")) == "H" for row in selected)
    women = sum(_norm(row.get("Sexo", "")) == "M" for row in selected)
    return men, women


def _write_condition_counts(worksheet, row, students):
    columns = {
        "CEGUERA": 40,
        "BAJA VISION": 42,
        "SORDERA": 44,
        "HIPOACUSIA": 46,
        "SORDOCEGUERA": 48,
        "MOTORA": 50,
        "INTELECTUAL": 52,
        "PSICOSOCIAL": 54,
        "TEA": 56,
        "MULTIPLE": 58,
        "TDA": 60,
        "TDAH": 62,
        "AS": 64,
        "APRENDIZAJE": 74,
        "CONDUCTA": 76,
        "COMUNICACION": 78,
    }
    for condition, column in columns.items():
        def matches(student):
            recorded = _norm(student.get("Condicion_Discapacidad", ""))
            if condition == "TDA":
                return recorded == "TDA"
            if condition == "TDAH":
                return "TDAH" in recorded
            return condition in recorded
        men, women = _sex_count(students, matches)
        worksheet.cell(row, column).value = men
        worksheet.cell(row, column + 1).value = women


def _assignment_rows(personal, asignaciones):
    people = [] if personal is None else personal.fillna("").to_dict("records")
    assignments = [] if asignaciones is None else asignaciones.fillna("").to_dict("records")
    by_person = {}
    for item in assignments:
        by_person.setdefault(_norm(item.get("ID_Personal", "")), []).append(
            _text(item.get("ID_Escuela", ""))
        )
    rows = []
    for person in people:
        assigned = by_person.get(_norm(person.get("ID_Personal", "")), [""])
        for school_id in assigned or [""]:
            rows.append((person, school_id))
    return rows


def generar_formato_personal(personal, escuelas, alumnos, asignaciones):
    """Genera la sábana de personal usando la plantilla de supervisión."""
    workbook = _workbook_from_template(PERSONAL_TEMPLATE)
    worksheet = workbook["1. SÁBANA DE PERSONAL DE USAER"]
    worksheet["B5"] = date.today().strftime("%d/%m/%Y")
    rows = _assignment_rows(personal, asignaciones)
    schools = _school_index(escuelas)
    first_row = 10
    _prepare_rows(worksheet, first_row, len(rows), first_row, 60)

    for number, (person, school_id) in enumerate(rows, start=1):
        row = first_row + number - 1
        school = schools.get(_norm(school_id), {})
        students = _students_for_school(alumnos, school_id)
        group_count = sum(
            _norm(student.get("Tipo_Atencion", "")) == "GRUPAL"
            for student in students
        )
        individual_count = sum(
            _norm(student.get("Tipo_Atencion", "")) == "INDIVIDUAL"
            for student in students
        )
        values = {
            1: number,
            2: SERVICE["zona"],
            3: SERVICE["numero"],
            4: SERVICE["cct"],
            5: SERVICE["turno"],
            6: _value(person, "Nombre_Completo", "Nombre"),
            7: _value(person, "Sexo"),
            8: _value(person, "Rol", "Funcion"),
            9: _value(person, "Email", "Correo_Electronico"),
            10: _value(person, "Telefono", "Teléfono"),
            11: _value(person, "Base_Contrato"),
            12: _value(person, "Sostenimiento"),
            13: _value(person, "Presenta_Discapacidad", default="No"),
            14: _value(person, "Horario"),
            15: _value(person, "Discapacidad"),
            16: _value(person, "Maya_Hablante", default="No"),
            17: _value(school, "Numero_Escuela"),
            18: _value(school, "Nombre_Escuela"),
            19: _value(school, "CCT"),
            20: _value(school, "Nivel"),
            21: _value(school, "Modalidad"),
            22: _value(school, "Horario"),
            23: _value(school, "Total_Grupos"),
            24: _value(school, "Direccion", "Dirección"),
            25: _value(school, "Localidad"),
            26: _value(school, "Municipio"),
            27: _value(school, "Director"),
            28: _value(school, "Telefono_Director"),
            29: _value(school, "Supervisor"),
            30: _value(school, "Telefono_Supervisor"),
            31: _value(school, "Zona_Escolar"),
            32: _value(school, "Sector"),
            33: _value(school, "Region"),
            34: group_count,
            35: individual_count,
            36: len(students),
            37: individual_count,
            38: 0,
            39: individual_count,
        }
        for column, value in values.items():
            worksheet.cell(row, column).value = value
        worksheet.cell(row, 2).number_format = "@"

        _write_condition_counts(worksheet, row, students)
        men, women = _sex_count(students)
        worksheet.cell(row, 83).value = men
        worksheet.cell(row, 84).value = women
        worksheet.cell(row, 85).value = len(students)

        for condition, column in (
            ("Lengua_Indigena_Mayahablante", 86),
            ("Afrodescendiente", 88),
            ("Migrante", 90),
        ):
            men, women = _sex_count(
                students, lambda student, field=condition: _yes(student.get(field, ""))
            )
            worksheet.cell(row, column).value = men
            worksheet.cell(row, column + 1).value = women
        men, women = _sex_count(
            students,
            lambda student: any(
                _yes(student.get(field, ""))
                for field in (
                    "Lengua_Indigena_Mayahablante", "Afrodescendiente", "Migrante"
                )
            ),
        )
        worksheet.cell(row, 92).value = men
        worksheet.cell(row, 93).value = women
        worksheet.cell(row, 94).value = men + women
    return _to_excel(workbook)


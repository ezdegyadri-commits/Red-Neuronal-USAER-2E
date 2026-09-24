"""PDF institucional del horario semanal de atención de apoyo USAER."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from fpdf import FPDF
from fpdf.enums import MethodReturnValue

from config.settings import SCHOOL_YEAR
from documents.anexos import _fpdf_text


ROOT = Path(__file__).resolve().parents[1]
PAGE_WIDTH = 255.4
TABLE_WIDTHS = (23, 28, 25, 39, 43, 97.4)
TABLE_LABELS = ("Día", "Horario", "Grado/grupo", "Modalidad", "Espacio", "Actividad / propósito")


class _HorarioPDF(FPDF):
    def header(self):
        header_image = ROOT / "encabezado.png"
        if header_image.exists():
            header_width = 218
            self.image(str(header_image), x=(279.4 - header_width) / 2, y=3, w=header_width)
        self.set_y(31)

    def footer(self):
        footer_image = ROOT / "pie_pagina.png"
        if footer_image.exists():
            footer_width = 170
            self.image(str(footer_image), x=(279.4 - footer_width) / 2, y=189, w=footer_width)
        self.set_y(184)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(100, 110, 120)
        self.cell(PAGE_WIDTH, 4, _fpdf_text(f"USAER 02-E · Ciclo escolar {SCHOOL_YEAR} · Página {self.page_no()}"), align="R")


def _texto(item, campo, fallback=""):
    value = item.get(campo, fallback)
    if value is None or str(value).strip().lower() in {"nan", "none"}:
        value = ""
    return _fpdf_text("" if value is None else value)


def generar_horario_apoyo_pdf(escuela: str, docente: str, filas: list[dict]) -> bytes:
    """Genera horario de trabajo con encabezado, pie institucional y espacios de firma."""
    if not filas:
        raise ValueError("No hay sesiones para generar el horario.")

    pdf = _HorarioPDF(orientation="L", unit="mm", format="letter")
    pdf.set_margins(12, 12, 12)
    pdf.set_auto_page_break(auto=False)

    def iniciar_pagina(titulo=True, encabezado_tabla=True):
        pdf.add_page()
        if titulo:
            pdf.set_y(31)
            pdf.set_font("Helvetica", "B", 14)
            pdf.set_text_color(22, 56, 82)
            pdf.cell(PAGE_WIDTH, 8, _fpdf_text("HORARIO SEMANAL DE ATENCIÓN DE APOYO"), align="C", new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(31, 6, _fpdf_text("Escuela:"))
            pdf.set_font("Helvetica", "", 9)
            pdf.cell(145, 6, _texto({"value": escuela}, "value"))
            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(28, 6, _fpdf_text("Ciclo escolar:"))
            pdf.set_font("Helvetica", "", 9)
            pdf.cell(PAGE_WIDTH - 204, 6, _fpdf_text(SCHOOL_YEAR), new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(39, 6, _fpdf_text("Docente que elabora:"))
            pdf.set_font("Helvetica", "", 9)
            pdf.cell(PAGE_WIDTH - 39, 6, _texto({"value": docente}, "value"), new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "I", 8)
            pdf.cell(PAGE_WIDTH, 5, _fpdf_text("Atención organizada por día, horario, grado/grupo, modalidad y espacio de trabajo."), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(3)
        if encabezado_tabla:
            tabla_encabezado()

    def tabla_encabezado():
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_fill_color(226, 235, 242)
        for width, label in zip(TABLE_WIDTHS, TABLE_LABELS):
            pdf.cell(width, 8, _fpdf_text(label), border=1, align="C", fill=True)
        pdf.ln()
        pdf.set_font("Helvetica", "", 8)

    iniciar_pagina()
    for row in filas:
        cells = [
            _texto(row, "Dia"),
            f"{_texto(row, 'Inicio')} - {_texto(row, 'Fin')}",
            _texto(row, "Grupo"),
            _texto(row, "Modalidad"),
            _texto(row, "Espacio"),
            _texto(row, "Actividad"),
        ]
        line_counts = [
            max(1, len(pdf.multi_cell(width - 3, 4.2, value, dry_run=True, output=MethodReturnValue.LINES)))
            for width, value in zip(TABLE_WIDTHS, cells)
        ]
        row_height = max(line_counts) * 4.2 + 3
        if pdf.get_y() + row_height > 188:
            iniciar_pagina(titulo=False)
        start_x, start_y = pdf.get_x(), pdf.get_y()
        for width, value in zip(TABLE_WIDTHS, cells):
            x = pdf.get_x()
            pdf.rect(x, start_y, width, row_height)
            pdf.set_xy(x + 1.5, start_y + 1.5)
            pdf.multi_cell(width - 3, 4.2, value)
            pdf.set_xy(x + width, start_y)
        pdf.set_xy(start_x, start_y + row_height)

    # Deja las firmas juntas al final; si la tabla agotó la página, usa una hoja final institucional.
    if pdf.get_y() + 39 > 190:
        iniciar_pagina(titulo=False, encabezado_tabla=False)
    else:
        pdf.ln(6)
    y = pdf.get_y()
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(PAGE_WIDTH, 6, _fpdf_text("VALIDACIÓN"), align="C", new_x="LMARGIN", new_y="NEXT")
    firmas = (
        (12, 120, "DOCENTE DE APOYO QUE ELABORA", docente),
        (147.4, 120, "VO. BO. DIRECTOR DE LA USAER 02-E", "Psic. Edgar Adrián Yam Briceño MD\nDirector de la USAER 02-E"),
    )
    for x, width, titulo, nombre in firmas:
        pdf.set_xy(x, y + 9)
        pdf.set_font("Helvetica", "", 8)
        pdf.cell(width, 5, _fpdf_text(titulo), align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.set_xy(x + 12, y + 24)
        pdf.cell(width - 24, 5, "________________________________________", align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.set_xy(x, y + 30)
        pdf.set_font("Helvetica", "", 8)
        pdf.multi_cell(width, 4, _fpdf_text(nombre), align="C")

    pdf.set_creation_date(datetime.now(ZoneInfo("America/Mexico_City")))
    return bytes(pdf.output())


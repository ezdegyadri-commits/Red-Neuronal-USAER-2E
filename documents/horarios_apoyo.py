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


def _nombre_breve(nombre):
    """Padrón institucional: apellido paterno, materno y nombre(s). Solo impresión."""
    palabras = str(nombre).strip().split()
    return " ".join((palabras[2], palabras[0])) if len(palabras) > 2 else " ".join(palabras)


def generar_horario_apoyo_pdf(escuela: str, docente: str, filas: list[dict]) -> bytes:
    if not filas:
        raise ValueError("No hay sesiones para generar el horario.")
    franjas = sorted({(str(r.get("Inicio", "")), str(r.get("Fin", ""))) for r in filas})
    return generar_horario_apoyo_cuadricula_pdf(escuela, docente, filas, franjas)


def generar_horario_apoyo_cuadricula_pdf(
    escuela: str, docente: str, filas: list[dict], franjas: list[tuple[str, str]],
    franjas_por_dia: dict | None = None,
) -> bytes:
    """Horario institucional horizontal con lunes a viernes y firmas al final."""
    if not franjas:
        raise ValueError("Configura al menos un módulo para imprimir el horario.")
    dias = ("Lunes", "Martes", "Miércoles", "Jueves", "Viernes")
    ancho_hora = 34.0
    ancho_dia = (PAGE_WIDTH - ancho_hora) / 5
    pdf = _HorarioPDF(orientation="L", unit="mm", format="letter")
    pdf.set_margins(12, 12, 12)
    pdf.set_auto_page_break(auto=False)
    por_celda = {}
    for item in filas:
        clave = (str(item.get("Dia", "")), str(item.get("Inicio", "")), str(item.get("Fin", "")))
        por_celda.setdefault(clave, []).append(item)

    def nueva_pagina():
        pdf.add_page()
        pdf.set_y(31)
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(22, 56, 82)
        pdf.cell(PAGE_WIDTH, 7, _fpdf_text("HORARIO SEMANAL DE ATENCIÓN DE APOYO"),
                 align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(PAGE_WIDTH, 5, _fpdf_text(f"Escuela: {escuela}   |   Docente: {docente}"),
                 new_x="LMARGIN", new_y="NEXT")
        pdf.cell(PAGE_WIDTH, 5, _fpdf_text(f"USAER 02-E   |   Ciclo escolar {SCHOOL_YEAR}"),
                 new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(218, 232, 242)
        pdf.cell(ancho_hora, 7, "HORARIO", border=1, align="C", fill=True)
        for dia in dias:
            pdf.cell(ancho_dia, 7, _fpdf_text(dia.upper()), border=1, align="C", fill=True)
        pdf.ln()

    nueva_pagina()
    celdas = []
    diarios = franjas_por_dia or {dia: franjas for dia in dias}
    distintos = len({tuple(diarios.get(dia, [])) for dia in dias}) > 1
    posiciones = range(max(len(diarios.get(dia, [])) for dia in dias)) if distintos else range(len(franjas))
    for posicion in posiciones:
        inicio, fin = (f"Módulo {posicion + 1}", "") if distintos else franjas[posicion]
        textos = []
        for dia in dias:
            partes = []
            intervalos = diarios.get(dia, [])
            if distintos and posicion >= len(intervalos):
                textos.append("")
                continue
            desde, hasta = intervalos[posicion] if distintos else (inicio, fin)
            if distintos:
                partes.append(f"{desde} - {hasta}")
            for item in por_celda.get((dia, desde, hasta), []):
                partes.append("\n".join(filter(None, (
                    str(item.get("Grupo", "")).strip() if not str(item.get("Alumnos", "")).strip() else "",
                    "; ".join(_nombre_breve(n) for n in str(item.get("Alumnos", "")).split(";") if n.strip()),
                    str(item.get("Actividad", "")).strip() if not (str(item.get("Alumnos", "")).strip() or str(item.get("Grupo", "")).strip()) else "",
                ))))
            textos.append(_fpdf_text("\n".join(partes)))
        celdas.append((inicio, fin, textos))
    # Medir antes de imprimir: reduce aire y tipografía solo hasta un mínimo legible.
    for fuente, interlineado, minimo in ((8.5, 3.8, 11), (8, 3.5, 9), (7.5, 3.3, 7), (7, 3.1, 6)):
        pdf.set_font("Helvetica", "", fuente)
        alturas = [max(minimo, interlineado * max(
            len(pdf.multi_cell(ancho_dia - 4, interlineado, t, dry_run=True,
                              output=MethodReturnValue.LINES)) if t else 1 for t in textos
        ) + 2) for _, _, textos in celdas]
        if sum(alturas) <= 181 - pdf.get_y() - 40:
            break
    for indice, ((inicio, fin, textos), alto) in enumerate(zip(celdas, alturas)):
        reserva = 40 if indice == len(celdas) - 1 else 0
        if pdf.get_y() + alto + reserva > 181:
            nueva_pagina()
        pdf.set_font("Helvetica", "", fuente)
        x0, y0 = pdf.get_x(), pdf.get_y()
        pdf.set_fill_color(245, 248, 251)
        pdf.rect(x0, y0, ancho_hora, alto, style="DF")
        pdf.set_xy(x0 + 1, y0 + 1.5)
        pdf.set_font("Helvetica", "B", fuente)
        pdf.multi_cell(ancho_hora - 2, interlineado, f"{inicio} - {fin}" if fin else inicio, align="C")
        pdf.set_font("Helvetica", "", fuente)
        for indice, texto_celda in enumerate(textos):
            x = x0 + ancho_hora + indice * ancho_dia
            pdf.rect(x, y0, ancho_dia, alto)
            pdf.set_xy(x + 2, y0 + 1)
            if texto_celda:
                pdf.multi_cell(ancho_dia - 4, interlineado, texto_celda, align="C")
        pdf.set_xy(x0, y0 + alto)

    y = pdf.get_y() + 4
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_xy(12, y)
    pdf.cell(PAGE_WIDTH, 6, "VALIDACIÓN", align="C")
    for x, titulo, nombre in (
        (12, "DOCENTE DE APOYO QUE ELABORA", docente),
        (148, "VO. BO. DIRECTOR DE LA USAER 02-E", "Psic. Edgar Adrián Yam Briceño MD"),
    ):
        pdf.set_font("Helvetica", "", 8)
        pdf.set_xy(x, y + 8)
        pdf.cell(119, 5, _fpdf_text(titulo), align="C")
        pdf.set_xy(x + 13, y + 22)
        pdf.cell(93, 5, "_____________________________________", align="C")
        pdf.set_xy(x, y + 29)
        pdf.cell(119, 5, _fpdf_text(nombre), align="C")
    pdf.set_creation_date(datetime.now(ZoneInfo("America/Mexico_City")))
    return bytes(pdf.output())

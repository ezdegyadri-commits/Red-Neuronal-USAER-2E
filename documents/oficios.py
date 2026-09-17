from datetime import date
from pathlib import Path

from fpdf import FPDF


MESES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)
RAIZ = Path(__file__).resolve().parents[1]


def _fecha_larga(fecha):
    if isinstance(fecha, str):
        try:
            fecha = date.fromisoformat(fecha)
        except ValueError:
            return fecha
    return f"{fecha.day:02d} de {MESES[fecha.month - 1]} de {fecha.year}"


def _archivo(nombre):
    ruta = RAIZ / nombre
    return str(ruta) if ruta.exists() else None


def cargo_direccion(nombre):
    nombre = str(nombre or "").upper()
    return "Directora" if "MTRA" in nombre or "MAESTRA" in nombre else "Director"


class OficioInstitucional(FPDF):
    def header(self):
        encabezado = _archivo("encabezado.png")
        if encabezado:
            self.image(encabezado, x=10, y=8, w=190)
        self.set_y(42)

    def footer(self):
        pie = _archivo("pie_pagina.png")
        if pie:
            self.image(pie, x=10, y=267, w=190)
        self.set_y(-18)
        self.set_font("Helvetica", size=8)
        self.cell(0, 5, "C.c.p. Archivo de la USAER 02-E", new_x="LMARGIN", new_y="NEXT")


def generar_oficio_comision(registro):
    """Genera un oficio PDF institucional de comisión para una maestra de apoyo."""
    pdf = OficioInstitucional(orientation="P", unit="mm", format="letter")
    pdf.set_auto_page_break(auto=True, margin=38)
    pdf.set_margins(25, 20, 25)
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)

    fecha_emision = registro.get("Fecha_Emision") or str(date.today())
    fecha_comision = registro.get("Fecha_Comision", "")
    folio = int(registro.get("Folio", 0) or 0)
    escuela = str(registro.get("Escuela", "")).strip()
    directora = str(registro.get("Director_Escuela", "")).strip()
    if not directora:
        directora = f"{cargo_direccion('')} de la escuela"
    responsable = str(registro.get("Maestra_Apoyo", "")).upper()
    asunto = str(registro.get("Asunto", "COMISIÓN")).upper()
    destino = str(registro.get("Destino", "")).strip()
    horario = str(registro.get("Horario", "")).strip() or "en su horario laboral"

    pdf.cell(
        0, 6, f"Mérida, Yucatán, a {_fecha_larga(fecha_emision)}",
        align="R", new_x="LMARGIN", new_y="NEXT",
    )
    pdf.cell(
        0, 6, f"Oficio No. SE/DEE-USAER No. 02-E/{folio:03d}/26-27",
        align="R", new_x="LMARGIN", new_y="NEXT",
    )
    pdf.ln(7)
    pdf.set_font("Helvetica", style="B", size=11)
    pdf.cell(0, 6, f"Asunto: {asunto}", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)
    pdf.cell(0, 6, directora, new_x="LMARGIN", new_y="NEXT")
    pdf.cell(
        0, 6, f"{cargo_direccion(directora)} de la escuela primaria",
        new_x="LMARGIN", new_y="NEXT",
    )
    pdf.cell(0, 6, f'"{escuela}"', new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, "PRESENTE", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)

    pdf.set_font("Helvetica", size=11)
    texto = (
        f"Por este medio le comunico que la maestra de apoyo {responsable} "
        f"ha sido comisionada para {destino} el día {_fecha_larga(fecha_comision)}, "
        f"{horario}. La comisión se realiza para atender actividades propias del "
        "servicio de apoyo de la USAER 02-E en la escuela a su cargo.\n\n"
        "Agradezco las facilidades brindadas para el cumplimiento de esta comisión "
        "y aprovecho la ocasión para enviarle un cordial saludo."
    )
    pdf.multi_cell(0, 6, texto, align="J")
    pdf.ln(12)

    firma = _archivo("firma.png")
    sello = _archivo("sello.png")
    y = pdf.get_y()
    if firma:
        pdf.image(firma, x=82, y=y, w=43)
    if sello:
        pdf.image(sello, x=138, y=y - 2, w=30)
    pdf.ln(23)
    pdf.cell(
        0, 5, "________________________________________",
        align="C", new_x="LMARGIN", new_y="NEXT",
    )
    pdf.set_font("Helvetica", style="B", size=11)
    pdf.cell(
        0, 5, "Psic. Edgar Adrián Yam Briceño MD",
        align="C", new_x="LMARGIN", new_y="NEXT",
    )
    pdf.set_font("Helvetica", size=11)
    pdf.cell(
        0, 5, "Director de la USAER 02-E",
        align="C", new_x="LMARGIN", new_y="NEXT",
    )
    return bytes(pdf.output())

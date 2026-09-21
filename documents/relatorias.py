from datetime import date
from html import escape
from pathlib import Path
import re

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parents[1]


class MembreteCanvas(canvas.Canvas):
    """Canvas que repite encabezado y pie oficiales en todas las páginas."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._paginas_guardadas = []

    def showPage(self):
        self._paginas_guardadas.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._paginas_guardadas)
        for estado in self._paginas_guardadas:
            self.__dict__.update(estado)
            self._dibujar_membrete(total)
            super().showPage()
        super().save()

    def _dibujar_membrete(self, total):
        ancho, alto = letter
        encabezado = ROOT / "encabezado.png"
        pie = ROOT / "pie_pagina.png"
        if encabezado.exists():
            self.drawImage(
                str(encabezado), 0, alto - 104, width=ancho, height=104,
                preserveAspectRatio=True, anchor="n", mask="auto",
            )
        if pie.exists():
            self.drawImage(
                str(pie), 0, 0, width=ancho, height=58,
                preserveAspectRatio=True, anchor="s", mask="auto",
            )


def _texto_parrafo(texto):
    """Escapa texto externo y convierte negritas Markdown sin permitir HTML arbitrario."""
    fragmentos = re.split(r"\*\*(.+?)\*\*", str(texto))
    salida = []
    for indice, fragmento in enumerate(fragmentos):
        limpio = escape(fragmento).replace("\n", "<br/>")
        salida.append(f"<b>{limpio}</b>" if indice % 2 else limpio)
    return "".join(salida)


def _fecha_espanol(fecha):
    meses = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
    ]
    valor = fecha if isinstance(fecha, date) else date.today()
    return f"Mérida, Yucatán a {valor.day:02d} de {meses[valor.month - 1]} de {valor.year}"


def _frase_apertura(fecha):
    meses = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
    ]
    valor = fecha if isinstance(fecha, date) else date.today()
    return (
        f"siendo las 7 horas del día {valor.day} del mes de "
        f"{meses[valor.month - 1]} del año {valor.year},"
    )


def generar_pdf_oficial(
    contenido_relatoria,
    num_asistentes,
    fecha=None,
    sesion="",
    tema="",
    tipo_junta="Junta de USAER",
    modalidad_junta="Junta Académica",
):
    """Crea la relatoría oficial carta con membrete, sello y espacios de asistencia."""
    estilos = getSampleStyleSheet()
    fecha_estilo = ParagraphStyle(
        "RelatoriaFecha", parent=estilos["Normal"], fontName="Helvetica",
        fontSize=10, leading=14, alignment=2,
    )
    titulo_estilo = ParagraphStyle(
        "RelatoriaTitulo", parent=estilos["Normal"], fontName="Helvetica-Bold",
        fontSize=14, leading=18, alignment=1, spaceAfter=6,
    )
    meta_estilo = ParagraphStyle(
        "RelatoriaMeta", parent=estilos["Normal"], fontName="Helvetica",
        fontSize=10, leading=14, alignment=1,
    )
    seccion_estilo = ParagraphStyle(
        "RelatoriaSeccion", parent=estilos["Normal"], fontName="Helvetica-Bold",
        fontSize=12, leading=16, spaceBefore=10, spaceAfter=5,
    )
    cuerpo_estilo = ParagraphStyle(
        "RelatoriaCuerpo", parent=estilos["Normal"], fontName="Helvetica",
        fontSize=11, leading=15, alignment=4, spaceAfter=7,
    )
    firma_estilo = ParagraphStyle(
        "RelatoriaFirma", parent=estilos["Normal"], fontName="Helvetica",
        fontSize=10, leading=13, alignment=1,
    )
    firma_negrita = ParagraphStyle(
        "RelatoriaFirmaNegrita", parent=firma_estilo, fontName="Helvetica-Bold",
    )

    elementos = [
        Paragraph(escape(_fecha_espanol(fecha)), fecha_estilo),
        Spacer(1, 10),
        Paragraph("RELATORÍA", titulo_estilo),
    ]
    meta = []
    meta.append(f"<b>Tipo de junta:</b> {escape(str(tipo_junta))}")
    if modalidad_junta:
        meta.append(f"<b>Modalidad:</b> {escape(str(modalidad_junta))}")
    if sesion:
        meta.append(f"<b>Sesión de CTE:</b> {escape(str(sesion))}")
    if tema:
        meta.append(f"<b>Tema central:</b> {escape(str(tema))}")
    if meta:
        elementos.extend([Paragraph("<br/>".join(meta), meta_estilo), Spacer(1, 10)])
    elementos.extend([
        Paragraph(escape(_frase_apertura(fecha)), cuerpo_estilo),
        Spacer(1, 6),
    ])

    for linea in str(contenido_relatoria or "").splitlines():
        limpio = linea.strip()
        if not limpio:
            continue
        nivel = len(limpio) - len(limpio.lstrip("#"))
        if nivel:
            titulo = limpio.lstrip("#").strip()
            elementos.append(Paragraph(escape(titulo), seccion_estilo))
        else:
            elementos.append(Paragraph(_texto_parrafo(limpio), cuerpo_estilo))

    elementos.append(Spacer(1, 24))
    if str(tipo_junta).strip().casefold() != "junta de zona":
        columna_firma = [
            Paragraph("___________________________________", firma_estilo),
            Paragraph("Psic. Edgar Adrián Yam Briceño MD", firma_negrita),
            Paragraph("Director de la USAER 02 Estatal", firma_estilo),
        ]
        sello_path = ROOT / "sello.png"
        if sello_path.exists():
            sello = Image(str(sello_path), width=1.15 * inch, height=1.15 * inch)
            sello.hAlign = "CENTER"
        else:
            sello = Paragraph("", firma_estilo)
        bloque_direccion = Table(
            [[columna_firma, sello]],
            colWidths=[4.6 * inch, 1.8 * inch],
        )
        bloque_direccion.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elementos.append(bloque_direccion)
    elementos.extend([
        Spacer(1, 20),
        Paragraph("FIRMAS DEL PERSONAL ASISTENTE", seccion_estilo),
        Spacer(1, 6),
    ])

    filas = [["Nombre del docente / especialista", "Función", "Firma"]]
    filas.extend([["", "", ""] for _ in range(max(1, min(int(num_asistentes), 30)))])
    tabla_asistencia = Table(
        filas,
        colWidths=[3.2 * inch, 1.7 * inch, 2.0 * inch],
        rowHeights=[26] * len(filas),
        repeatRows=1,
    )
    tabla_asistencia.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.7, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
    ]))
    elementos.append(tabla_asistencia)

    import io
    salida = io.BytesIO()
    documento = SimpleDocTemplate(
        salida, pagesize=letter, leftMargin=54, rightMargin=54,
        topMargin=112, bottomMargin=72, title="Relatoría CTE USAER 02-E",
    )
    documento.build(elementos, canvasmaker=MembreteCanvas)
    return salida.getvalue()

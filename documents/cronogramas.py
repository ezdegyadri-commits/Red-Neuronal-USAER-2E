"""Generación del PDF oficial mensual de cronogramas para especialistas."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from fpdf import FPDF
from fpdf.enums import MethodReturnValue

from config.settings import CRONOGRAMAS_FOLDER_ID
from documents.anexos import _fpdf_text


ROOT = Path(__file__).resolve().parents[1]
ANCHO_UTIL = 180


def generar_cronograma_pdf(perfil: dict, mes_label: str, filas: list[dict], firma_especialista=None,
                           firma_direccion=None, sello=None) -> bytes:
    """Crea una versión descargable con encabezado, pie, tabla y área de firmas."""
    pdf = FPDF(orientation="P", unit="mm", format="letter")
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=24)

    def encabezado():
        ruta = ROOT / "encabezado.png"
        if ruta.exists():
            pdf.image(str(ruta), x=15, y=7, w=ANCHO_UTIL)
        pdf.set_y(35)
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(247, 127, 35)
        pdf.cell(ANCHO_UTIL, 8, _fpdf_text("CRONOGRAMA DE ACTIVIDADES"), align="C",
                 new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(ANCHO_UTIL, 6, _fpdf_text(f"{perfil['nombre']}  |  {perfil['area']}"), align="C",
                 new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(ANCHO_UTIL, 6, _fpdf_text(f"Mes: {mes_label}"), align="C",
                 new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)

    def pie():
        ruta = ROOT / "pie_pagina.png"
        if ruta.exists():
            pdf.image(str(ruta), x=15, y=267, w=ANCHO_UTIL)

    def nueva_pagina():
        pdf.add_page()
        encabezado()

    def encabezado_tabla():
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(235, 238, 242)
        for ancho, texto in ((31, "Fecha"), (54, "Escuela"), (95, "Actividad")):
            pdf.cell(ancho, 8, _fpdf_text(texto), border=1, align="C", fill=True)
        pdf.ln()
        pdf.set_font("Helvetica", "", 9)

    nueva_pagina()
    encabezado_tabla()
    for item in filas:
        fecha = _fpdf_text(item.get("fecha", ""))
        escuela = _fpdf_text(item.get("escuela", ""))
        actividad = _fpdf_text(item.get("actividad", ""))
        alturas = [
            len(pdf.multi_cell(31, 5, fecha, dry_run=True, output=MethodReturnValue.LINES)),
            len(pdf.multi_cell(54, 5, escuela, dry_run=True, output=MethodReturnValue.LINES)),
            len(pdf.multi_cell(95, 5, actividad, dry_run=True, output=MethodReturnValue.LINES)),
        ]
        alto = max(alturas + [1]) * 5 + 3
        if pdf.get_y() + alto > 250:
            pie()
            nueva_pagina()
            encabezado_tabla()
        x0, y0 = pdf.get_x(), pdf.get_y()
        for ancho, texto in zip((31, 54, 95), (fecha, escuela, actividad)):
            x = pdf.get_x()
            pdf.rect(x, y0, ancho, alto)
            pdf.set_xy(x + 1.5, y0 + 1.5)
            pdf.multi_cell(ancho - 3, 5, texto, border=0)
            pdf.set_xy(x + ancho, y0)
        pdf.set_xy(x0, y0 + alto)

    if pdf.get_y() + 42 > 250:
        pie()
        nueva_pagina()
    else:
        pdf.ln(8)
    ancho_firma = 86
    y_firma = pdf.get_y()
    pdf.set_font("Helvetica", "", 9)
    for x, titulo, nombre, imagen in (
        (15, "Elaboró", perfil["nombre"], firma_especialista),
        (109, "Vo. Bo.", "Psic. Edgar Adrián Yam Briceño MD\nDirector de la USAER 02-E", firma_direccion),
    ):
        pdf.set_xy(x, y_firma)
        pdf.cell(ancho_firma, 5, _fpdf_text(titulo), align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.set_xy(x, y_firma + 6)
        if imagen:
            try:
                pdf.image(BytesIO(imagen), x=x + 23, y=y_firma + 5, w=40)
            except Exception:
                pass
        pdf.set_xy(x, y_firma + 22)
        pdf.cell(ancho_firma, 5, "____________________________", align="C",
                 new_x="LMARGIN", new_y="NEXT")
        pdf.set_xy(x, y_firma + 28)
        pdf.multi_cell(ancho_firma, 4.5, _fpdf_text(nombre), align="C")
        if x == 109 and sello:
            try:
                pdf.image(BytesIO(sello), x=x + 66, y=y_firma + 8, w=18)
            except Exception:
                pass
    pie()
    return bytes(pdf.output())


def guardar_pdf_drive(pdf_bytes: bytes, nombre_archivo: str) -> str:
    """Guarda una copia en la carpeta institucional; el PDF también se descarga desde la app."""
    from googleapiclient.http import MediaIoBaseUpload
    from data.google import drive_service

    servicio = drive_service()
    archivo = servicio.files().create(
        body={"name": nombre_archivo, "mimeType": "application/pdf", "parents": [CRONOGRAMAS_FOLDER_ID]},
        media_body=MediaIoBaseUpload(BytesIO(pdf_bytes), mimetype="application/pdf", resumable=False),
        fields="id,webViewLink",
        supportsAllDrives=True,
    ).execute()
    return str(archivo.get("webViewLink", ""))

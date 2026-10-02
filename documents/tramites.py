"""Respuesta institucional para revisión y firma, vinculada al folio central."""
from documents.oficios import OficioInstitucional, _fecha_larga
from documents.paginacion import texto_con_cierre


def _texto(valor):
    # La fuente institucional actual es Latin-1; normaliza comillas tipográficas.
    texto = str(valor).replace("\u201c", '"').replace("\u201d", '"').replace("\u2019", "'").replace("\u2013", "-").replace("\u2014", "-")
    try:
        texto.encode("latin-1")
    except UnicodeEncodeError as exc:
        raise ValueError("El oficio contiene símbolos no compatibles con la fuente institucional.") from exc
    return texto


def generar_respuesta(registro):
    pdf = OficioInstitucional(format="letter")
    pdf.set_margins(25, 20, 25)
    pdf.set_auto_page_break(True, margin=38)
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)
    pdf.cell(0, 6, f"Mérida, Yucatán, a {_fecha_larga(registro['Fecha_Emision'])}", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Oficio No. SE/DEE-USAER No. 02-E/{int(registro['Folio']):03d}/26-27", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(7)
    pdf.set_font("Helvetica", "B", 11)
    pdf.multi_cell(0, 6, "Asunto: Respuesta a solicitud de expedientes", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)
    pdf.multi_cell(0, 6, _texto(registro.get("Director_Escuela", "")), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, "PRESENTE", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(7)
    pdf.set_font("Helvetica", size=11)
    texto_con_cierre(pdf, 0, 6, _texto(registro.get("Destino", "")), 52)
    pdf.ln(8)
    pdf.cell(0, 6, "ATENTAMENTE", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(18)
    pdf.cell(0, 5, "________________________________________", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, "Psic. Edgar Adrián Yam Briceño MD", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, "Director de la USAER 02-E", align="C", new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())

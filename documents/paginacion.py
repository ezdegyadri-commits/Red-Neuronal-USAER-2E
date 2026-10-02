"""Saltos de página que conservan texto de cierre junto al espacio de firmas."""
from math import floor
from fpdf.enums import MethodReturnValue


def texto_con_cierre(pdf, ancho, alto_linea, texto, reserva, border=0):
    ancho = ancho or pdf.w - pdf.l_margin - pdf.r_margin
    pdf.set_x(pdf.l_margin)
    lineas = pdf.multi_cell(ancho, alto_linea, texto or " ", dry_run=True,
                           output=MethodReturnValue.LINES)
    lineas = lineas or [" "]
    while lineas:
        espacio = pdf.page_break_trigger - pdf.get_y()
        if len(lineas) * alto_linea + reserva <= espacio:
            pdf.multi_cell(ancho, alto_linea, "\n".join(lineas), border=border,
                           new_x="LMARGIN", new_y="NEXT")
            return
        cantidad = min(floor(espacio / alto_linea) - 1, len(lineas) - 2)
        if cantidad > 0:
            pdf.multi_cell(ancho, alto_linea, "\n".join(lineas[:cantidad]), border=border,
                           new_x="LMARGIN", new_y="NEXT")
            lineas = lineas[cantidad:]
        pdf.add_page()

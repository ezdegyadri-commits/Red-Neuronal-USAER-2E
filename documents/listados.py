"""Vistas oficiales imprimibles de listados nominales de alumnos."""

import base64
import html
from io import BytesIO

import pandas as pd
from fpdf import FPDF

from config.settings import ESCUELAS_USAER, SCHOOL_YEAR, SERVICE_NAME
from documents.anexos import _fpdf_text, header_b64


def _datos_listado(frame):
    datos = pd.DataFrame(index=frame.index)
    datos["Nombre"] = frame.get("Nombre_Completo", pd.Series("", index=frame.index)).fillna("").astype(str).str.strip()
    datos["Edad"] = frame.get("Edad_1_Septiembre", pd.Series("", index=frame.index)).fillna("").astype(str).str.strip()
    datos["Condición"] = frame.get("Condicion_Discapacidad", pd.Series("", index=frame.index)).fillna("").astype(str).str.strip()
    datos["Grado"] = frame.get("Grado", pd.Series("", index=frame.index)).fillna("").astype(str).str.strip()
    datos["Grupo"] = frame.get("Grupo", pd.Series("", index=frame.index)).fillna("").astype(str).str.strip()
    datos["Grado y grupo"] = (datos["Grado"] + " " + datos["Grupo"]).str.strip()
    datos["Escuela"] = frame.get("Nombre_Escuela", pd.Series("", index=frame.index)).fillna("").astype(str).str.strip()
    if "ID_Escuela" in frame.columns:
        codigos = {
            str(codigo).strip().upper(): nombre
            for nombre, codigo in ESCUELAS_USAER.items()
        }
        nombres_canonicos = (
            frame["ID_Escuela"].fillna("").astype(str).str.strip().str.upper()
            .map(codigos)
        )
        datos["Escuela"] = datos["Escuela"].mask(
            datos["Escuela"].eq(""), nombres_canonicos
        )
    if "ID_Alumno" in frame.columns:
        datos["ID_Alumno"] = frame["ID_Alumno"].fillna("").astype(str).str.strip()
        datos = datos.drop_duplicates(subset=["ID_Alumno"], keep="first")
    datos = datos.loc[datos["Nombre"].ne("")].copy()
    datos = datos.sort_values(["Escuela", "Grado y grupo", "Nombre"], kind="stable")
    return datos.reset_index(drop=True)


def listado_alumnos_html(frame, ambito, firma_nombre=""):
    datos = _datos_listado(frame)
    head = header_b64()
    incluir_escuela = "toda la usaer" in str(ambito).casefold()
    columnas = ["Escuela", "Nombre", "Edad", "Condición", "Grado y grupo"] if incluir_escuela else ["Nombre", "Edad", "Condición", "Grado y grupo"]
    filas = "".join(
        "<tr>" + "".join(f"<td>{html.escape(str(row.get(col, '')))}</td>" for col in columnas) + "</tr>"
        for row in datos.to_dict("records")
    )
    encabezados = "".join(f"<th>{html.escape(col)}</th>" for col in columnas)
    return (
        "<!doctype html><html><head><meta charset='utf-8'><style>"
        "@page{size:letter portrait;margin:14mm}body{font-family:Arial,sans-serif;color:#111;font-size:10pt}"
        "header{text-align:center;margin-bottom:10px}header img{max-width:100%;max-height:90px}"
        "h2{text-align:center;margin:8px 0}p{margin:5px 0 12px}table{width:100%;border-collapse:collapse}"
        "thead{display:table-header-group}tr{page-break-inside:avoid}th,td{border:1px solid #222;padding:5px;text-align:left;vertical-align:top}"
        "th{background:#edf2f6}@media print{button{display:none}}"
        "</style></head><body><header>"
        f"<img src='{head}'></header><h2>Listado nominal de alumnos</h2>"
        f"<p><b>Servicio:</b> {html.escape(SERVICE_NAME)} &nbsp; <b>Ciclo escolar:</b> {html.escape(SCHOOL_YEAR)}<br>"
        f"<b>Ámbito:</b> {html.escape(str(ambito))} &nbsp; <b>Total:</b> {len(datos)}</p>"
        f"<table><thead><tr>{encabezados}</tr></thead><tbody>{filas}</tbody></table>"
        + (
            "<div style='margin:38px auto 0;max-width:320px;text-align:center'>"
            "_______________________________<br>"
            f"{html.escape(str(firma_nombre))}<br>Maestra/o de apoyo responsable</div>"
            if firma_nombre else ""
        )
        + "</body></html>"
    )


def listado_alumnos_pdf(frame, ambito, firma_nombre=""):
    datos = _datos_listado(frame)
    incluir_escuela = "toda la usaer" in str(ambito).casefold()
    columnas = ["Escuela", "Nombre", "Edad", "Condición", "Grado y grupo"] if incluir_escuela else ["Nombre", "Edad", "Condición", "Grado y grupo"]
    anchos = [40, 52, 15, 48, 30] if incluir_escuela else [68, 17, 68, 32]
    alto_linea = 4.5

    class ListadoPDF(FPDF):
        def header(self):
            head = header_b64()
            if head:
                try:
                    self.image(BytesIO(base64.b64decode(head.split(",", 1)[1])), x=15, y=7, w=180)
                except Exception:
                    pass
            self.set_y(34)
            self.set_font("Helvetica", "B", 13)
            self.cell(0, 7, _fpdf_text("Listado nominal de alumnos"), align="C", new_x="LMARGIN", new_y="NEXT")
            self.set_font("Helvetica", "", 9)
            self.cell(0, 5, _fpdf_text(f"Servicio: {SERVICE_NAME}   Ciclo escolar: {SCHOOL_YEAR}"), new_x="LMARGIN", new_y="NEXT")
            self.cell(0, 5, _fpdf_text(f"Ambito: {ambito}   Total de alumnos: {len(datos)}"), new_x="LMARGIN", new_y="NEXT")
            self.ln(2)
            self._encabezados()

        def _encabezados(self):
            self.set_font("Helvetica", "B", 8)
            self.set_fill_color(237, 242, 246)
            for titulo, ancho in zip(columnas, anchos):
                self.cell(ancho, 7, _fpdf_text(titulo), border=1, align="C", fill=True)
            self.ln()

        def footer(self):
            self.set_y(-10)
            self.set_font("Helvetica", "", 8)
            self.cell(0, 5, _fpdf_text(f"Pagina {self.page_no()}"), align="C")

    pdf = ListadoPDF(orientation="P", unit="mm", format="letter")
    pdf.set_margins(15, 12, 15)
    pdf.set_auto_page_break(auto=True, margin=13)
    pdf.add_page()
    pdf.set_font("Helvetica", "", 8)

    for _, registro in datos.iterrows():
        valores = [str(registro.get(col, "") or "") for col in columnas]
        lineas = []
        for valor, ancho in zip(valores, anchos):
            ancho_util = max(ancho - 2, 5)
            linea = ""
            resultado = []
            for palabra in valor.split():
                prueba = f"{linea} {palabra}".strip()
                if pdf.get_string_width(_fpdf_text(prueba)) <= ancho_util:
                    linea = prueba
                else:
                    if linea:
                        resultado.append(linea)
                    linea = palabra
            if linea or not resultado:
                resultado.append(linea)
            lineas.append(resultado)
        alto = max(len(items) for items in lineas) * alto_linea + 2
        if pdf.get_y() + alto > pdf.page_break_trigger:
            pdf.add_page()
            pdf.set_font("Helvetica", "", 8)
        x_inicial, y_inicial = pdf.get_x(), pdf.get_y()
        x = x_inicial
        for items, ancho in zip(lineas, anchos):
            pdf.rect(x, y_inicial, ancho, alto)
            pdf.set_xy(x + 1, y_inicial + 1)
            pdf.multi_cell(ancho - 2, alto_linea, _fpdf_text("\n".join(items)), border=0)
            x += ancho
        pdf.set_xy(x_inicial, y_inicial + alto)

    if firma_nombre:
        if pdf.get_y() + 24 > pdf.page_break_trigger:
            pdf.add_page()
        pdf.ln(10)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 5, _fpdf_text("_______________________________"), align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 5, _fpdf_text(firma_nombre), align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 5, _fpdf_text("Maestra/o de apoyo responsable"), align="C", new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())

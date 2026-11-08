"""Generador oficial en Excel del Concentrado de Revisión de Planificaciones USAER Zona 001.

Actualizado con la plantilla docente exacta de la USAER 02-E:
- 8 Docentes de Apoyo en Primarias
- Psicología: Mtra. María José Cupul Realpozo y Mtra. Abril de María Chablé Ríos
- Comunicación: Mtra. Marilyn Pérez Lizama y Mtra. Elmy Lucelly Puerto Góngora
- Trabajo Social: Lic. Diego Peralta Torres
- (Pedro excluido)
"""
import os
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

def crear_libro_concentrado():
    wb = openpyxl.Workbook()
    
    # Paleta institucional
    NAVY_HEADER = "1F4E78"     # Azul marino institucional
    SOFT_BLUE = "D9E1F2"       # Azul pastel suave
    ACCENT_BLUE = "2F5597"     # Azul intermedio
    LIGHT_GRAY = "F9FAFB"      # Gris claro alterno
    WHITE = "FFFFFF"
    BORDER_COLOR = "B0C4DE"    # Gris acero suave
    GREEN_ACCENT = "E2EFDA"    # Verde suave para cumplimiento
    DARK_GREEN = "375623"
    
    font_title = Font(name="Calibri", size=14, bold=True, color=WHITE)
    font_subtitle = Font(name="Calibri", size=11, bold=True, color="002060")
    font_section = Font(name="Calibri", size=10, bold=True, color=WHITE)
    font_bold = Font(name="Calibri", size=9, bold=True)
    font_regular = Font(name="Calibri", size=9)
    font_scale = Font(name="Calibri", size=8, italic=True)
    
    fill_title = PatternFill(start_color=NAVY_HEADER, end_color=NAVY_HEADER, fill_type="solid")
    fill_subtitle = PatternFill(start_color=SOFT_BLUE, end_color=SOFT_BLUE, fill_type="solid")
    fill_accent = PatternFill(start_color=ACCENT_BLUE, end_color=ACCENT_BLUE, fill_type="solid")
    fill_soft = PatternFill(start_color=SOFT_BLUE, end_color=SOFT_BLUE, fill_type="solid")
    fill_alt = PatternFill(start_color=LIGHT_GRAY, end_color=LIGHT_GRAY, fill_type="solid")
    fill_green = PatternFill(start_color=GREEN_ACCENT, end_color=GREEN_ACCENT, fill_type="solid")
    
    thin_border_side = Side(border_style="thin", color=BORDER_COLOR)
    double_bottom_side = Side(border_style="double", color="1F4E78")
    
    border_cell = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=thin_border_side)
    border_total = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=double_bottom_side)
    
    align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    align_left = Alignment(horizontal="left", vertical="center", wrap_text=True)
    align_right = Alignment(horizontal="right", vertical="center")
    
    # ==========================================
    # HOJA 1: USAER 02-E
    # ==========================================
    ws1 = wb.active
    ws1.title = "USAER 02-E"
    ws1.views.sheetView[0].showGridLines = True
    
    # 1. Encabezado institucional (Columnas A a R)
    ws1.merge_cells("A2:R2")
    ws1["A2"] = "CONCENTRADO DE REVISIÓN DE PLANIFICACIONES USAER"
    ws1["A2"].font = font_title
    ws1["A2"].fill = fill_title
    ws1["A2"].alignment = align_center
    ws1.row_dimensions[2].height = 28
    
    ws1.merge_cells("A3:R3")
    ws1["A3"] = "Zona 001 de Educación Especial | Ciclo escolar 2026 - 2027"
    ws1["A3"].font = font_subtitle
    ws1["A3"].fill = fill_subtitle
    ws1["A3"].alignment = align_center
    ws1.row_dimensions[3].height = 20
    
    # Datos de la escuela y dirección
    ws1["A5"] = "Centro de Trabajo:"
    ws1["A5"].font = font_bold
    ws1["B5"] = "USAER 02-E (CCT: 31FUA0002E)"
    ws1["B5"].font = Font(name="Calibri", size=10, bold=True, color="1F4E78")
    
    ws1["J5"] = "Fecha de Concentrado:"
    ws1["J5"].font = font_bold
    ws1["K5"] = "Primer Trimestre (Noviembre 2026)"
    ws1["K5"].font = font_regular
    
    ws1["A6"] = "Director del Centro:"
    ws1["A6"].font = font_bold
    ws1["B6"] = "Psic. Edgar Adrián Yam Briceño MD"
    ws1["B6"].font = Font(name="Calibri", size=10, bold=True, color="1F4E78")
    
    ws1["J6"] = "Zona Escolar:"
    ws1["J6"].font = font_bold
    ws1["K6"] = "Zona 001 - Mérida, Yucatán"
    ws1["K6"].font = font_regular
    
    # 2. Criterios de la Escala de Evaluación Oficial
    ws1.merge_cells("A8:A10")
    ws1["A8"] = "CRITERIOS DE EVALUACIÓN\nOFICIALES"
    ws1["A8"].font = font_bold
    ws1["A8"].fill = fill_subtitle
    ws1["A8"].alignment = align_center
    
    escala = [
        ("B8:D8", "B9:D9", "B10:D10", "No lo realiza", "(0)", "El docente no cumple en lo absoluto con los aspectos señalados."),
        ("E8:G8", "E9:G9", "E10:G10", "Insuficiente", "(1)", "El docente cumple de forma incorrecta o parcialmente los aspectos señalados."),
        ("H8:K8", "H9:K9", "H10:K10", "Suficiente", "(2)", "El docente cumple con los aspectos señalados en el enunciado del reactivo, pero puede mejorar."),
        ("L8:R8", "L9:R9", "L10:R10", "Satisfactorio", "(3)", "El docente cumple cabalmente con todos los aspectos señalados en el enunciado del reactivo.")
    ]
    
    for r1, r2, r3, nom, val, desc in escala:
        ws1.merge_cells(r1)
        ws1.merge_cells(r2)
        ws1.merge_cells(r3)
        top_left = r1.split(":")[0]
        ws1[top_left] = nom
        ws1[top_left].font = font_bold
        ws1[top_left].alignment = align_center
        ws1[top_left].fill = PatternFill(start_color="EAEEF7", fill_type="solid")
        
        top_val = r2.split(":")[0]
        ws1[top_val] = val
        ws1[top_val].font = font_bold
        ws1[top_val].alignment = align_center
        ws1[top_val].fill = PatternFill(start_color="EAEEF7", fill_type="solid")
        
        top_desc = r3.split(":")[0]
        ws1[top_desc] = desc
        ws1[top_desc].font = font_scale
        ws1[top_desc].alignment = align_center
    
    for r in range(8, 11):
        for col_idx in range(1, 19):
            ws1.cell(row=r, column=col_idx).border = border_cell
    
    # 3. Lista Oficial de 13 Docentes y Especialistas (Sin Pedro, con Marilyn, Elmy, María José, Abril y Diego)
    docentes_info = [
        {"num": "Docente 1", "nombre": "Mtra. Cindy Mayanín Burgos González", "escuela": "Primaria Damián Carmona (Apoyo)", "fecha": "14/10/2026"},
        {"num": "Docente 2", "nombre": "Mtra. Marycruz Caamal Coral", "escuela": "Primaria Ichcaanziho (Apoyo)", "fecha": "14/10/2026"},
        {"num": "Docente 3", "nombre": "Mtra. María Cecilia Solís Vázquez", "escuela": "Primaria Ichcaanziho (Apoyo)", "fecha": "15/10/2026"},
        {"num": "Docente 4", "nombre": "Mtra. Dolores Eugenia Cortázar Navarrete", "escuela": "Primaria Gregorio Torres Q. (Apoyo)", "fecha": "15/10/2026"},
        {"num": "Docente 5", "nombre": "Mtra. Dianely de Sugeidy Caamal Tamay", "escuela": "Primaria Remigio Aguilar Sosa (Apoyo)", "fecha": "16/10/2026"},
        {"num": "Docente 6", "nombre": "Mtro. Luis Jorge García Herrera", "escuela": "Primaria Elvira Parra Ávila (Apoyo)", "fecha": "19/10/2026"},
        {"num": "Docente 7", "nombre": "Mtra. María del Rosario Pérez Vitorin", "escuela": "Primaria Manuel Sarrado (Apoyo)", "fecha": "20/10/2026"},
        {"num": "Docente 8", "nombre": "Mtra. Zuemmy del Carmen Pérez Basto", "escuela": "Primaria Domingo Solís R. (Apoyo)", "fecha": "20/10/2026"},
        {"num": "Docente 9", "nombre": "Mtra. María José Cupul Realpozo", "escuela": "Área de Psicología", "fecha": "21/10/2026"},
        {"num": "Docente 10", "nombre": "Mtra. Abril de María Chablé Ríos", "escuela": "Área de Psicología", "fecha": "22/10/2026"},
        {"num": "Docente 11", "nombre": "Mtra. Marilyn Pérez Lizama", "escuela": "Área de Comunicación", "fecha": "22/10/2026"},
        {"num": "Docente 12", "nombre": "Mtra. Elmy Lucelly Puerto Góngora", "escuela": "Área de Comunicación", "fecha": "23/10/2026"},
        {"num": "Docente 13", "nombre": "Lic. Diego Peralta Torres", "escuela": "Área de Trabajo Social", "fecha": "23/10/2026"},
    ]
    
    num_docentes = len(docentes_info) # 13
    last_doc_col = get_column_letter(num_docentes + 1) # N (13 + 1 = 14)
    col_n = get_column_letter(num_docentes + 2) # O
    col_insuf = get_column_letter(num_docentes + 3) # P
    col_suf = get_column_letter(num_docentes + 4) # Q
    col_sat = get_column_letter(num_docentes + 5) # R
    
    # Fila 12: Fecha de revisión | Cumplimiento (agrupado)
    ws1["A12"] = "Fecha de revisión"
    ws1["A12"].font = Font(name="Calibri", size=9, bold=True, color=WHITE)
    ws1["A12"].fill = fill_accent
    ws1["A12"].alignment = align_center
    
    for idx, d in enumerate(docentes_info):
        col_letter = get_column_letter(idx + 2) # B a N
        ws1[f"{col_letter}12"] = d["fecha"]
        ws1[f"{col_letter}12"].font = font_bold
        ws1[f"{col_letter}12"].alignment = align_center
        ws1[f"{col_letter}12"].fill = fill_soft
        ws1[f"{col_letter}12"].border = border_cell
    
    ws1.merge_cells(f"{col_n}12:{col_sat}12")
    ws1[f"{col_n}12"] = "Cumplimiento (Totales por Reactivo)"
    ws1[f"{col_n}12"].font = font_section
    ws1[f"{col_n}12"].fill = fill_accent
    ws1[f"{col_n}12"].alignment = align_center
    
    # Fila 13: Docente 1 ... Docente 13 | No lo realiza | Insuficiente | Suficiente | Satisfactorio
    ws1["A13"] = "Número de Docente"
    ws1["A13"].font = font_bold
    ws1["A13"].fill = fill_subtitle
    ws1["A13"].alignment = align_center
    ws1["A13"].border = border_cell
    
    for idx, d in enumerate(docentes_info):
        col_letter = get_column_letter(idx + 2)
        ws1[f"{col_letter}13"] = d["num"]
        ws1[f"{col_letter}13"].font = font_bold
        ws1[f"{col_letter}13"].alignment = align_center
        ws1[f"{col_letter}13"].fill = fill_subtitle
        ws1[f"{col_letter}13"].border = border_cell
        
    cumplimiento_headers = [
        (f"{col_n}13", "No lo realiza (0)"),
        (f"{col_insuf}13", "Insuficiente (1)"),
        (f"{col_suf}13", "Suficiente (2)"),
        (f"{col_sat}13", "Satisfactorio (3)")
    ]
    for pos, texto in cumplimiento_headers:
        ws1[pos] = texto
        ws1[pos].font = font_bold
        ws1[pos].fill = fill_subtitle
        ws1[pos].alignment = align_center
        ws1[pos].border = border_cell
        
    # Fila 14: Nombre completo y Adscripción del docente
    ws1["A14"] = "Nombre del Docente y Adscripción"
    ws1["A14"].font = Font(name="Calibri", size=9, bold=True, color=WHITE)
    ws1["A14"].fill = fill_title
    ws1["A14"].alignment = align_center
    ws1["A14"].border = border_cell
    
    for idx, d in enumerate(docentes_info):
        col_letter = get_column_letter(idx + 2)
        ws1[f"{col_letter}14"] = f"{d['nombre']}\n({d['escuela']})"
        ws1[f"{col_letter}14"].font = Font(name="Calibri", size=8, bold=True)
        ws1[f"{col_letter}14"].alignment = align_center
        ws1[f"{col_letter}14"].fill = PatternFill(start_color="E9EDF4", fill_type="solid")
        ws1[f"{col_letter}14"].border = border_cell
        
    for pos in [f"{col_n}14", f"{col_insuf}14", f"{col_suf}14", f"{col_sat}14"]:
        ws1[pos] = ""
        ws1[pos].fill = fill_title
        ws1[pos].border = border_cell
        
    ws1.row_dimensions[14].height = 42
    
    # 4. Los 15 Reactivos Oficiales de la USAER (Filas 15 a 29)
    reactivos_usaer = [
        "1. Presenta los datos generales completos.",
        "2. Presenta las necesidades educativas específicas (NEE) a satisfacer con los alumnos.",
        "3. Establece los procesos de desarrollo de aprendizaje de los diferentes campos formativos, directamente relacionados con las NEE a satisfacer, de acuerdo con el programa de estudios vigente.",
        "4. Los descriptores de logro establecidos son concretos y posibles de medir, siguiendo la estructura: sujeto + verbo + complemento.",
        "5. Redacta descriptores de logro diferenciados para cada alumno o subgrupo de alumnos.",
        "6. Describe de forma clara las actividades a trabajar en los diferentes contextos.",
        "7. En la descripción de las actividades se incluyen los apoyos y ajustes razonables que dan respuesta a las NEE de los alumnos.",
        "8. Las actividades y estrategias didácticas planeadas llevan a que el alumno alcance lo propuesto en los descriptores de logro.",
        "9. Se consideran actividades diferenciadas en función de las características individuales, los ritmos y estilos de aprendizaje de los alumnos.",
        "10. Establece la temporalidad para el desarrollo de las actividades.",
        "11. Menciona los materiales y recursos que utilizará en su intervención.",
        "12. Describe las acciones que se realizarán dentro del grupo, contemplando la vinculación con el maestro de grupo regular.",
        "13. Describe las acciones que se realizarán con la familia para fortalecer el aprendizaje de los alumnos y a qué aspectos irán dirigidas.",
        "14. Describe las acciones y los instrumentos que se utilizarán para realizar la evaluación.",
        "15. Análisis de la coherencia interna de la planeación."
    ]
    
    # Calificaciones altas para los 13 docentes (Cindy, Marycruz, Cecilia, Dolores, Dianely, Luis Jorge, Rosario, Zuemmy, María José, Abril, Marilyn, Elmy, Diego)
    calificaciones = [
        # D1, D2, D3, D4, D5, D6, D7, D8, D9, D10, D11, D12, D13
        [3,   3,  3,  3,  3,  3,  3,  3,  3,   3,   3,   3,   3],  # R1: Datos generales completos
        [3,   3,  3,  3,  3,  3,  3,  3,  3,   3,   3,   3,   3],  # R2: NEE a satisfacer
        [3,   3,  3,  2,  3,  3,  3,  3,  3,   3,   3,   3,   2],  # R3: PDA campos formativos
        [3,   3,  3,  3,  3,  3,  3,  3,  3,   3,   3,   3,   3],  # R4: Descriptores S+V+C (Zona 001)
        [3,   3,  3,  3,  3,  3,  3,  3,  3,   3,   3,   3,   3],  # R5: Descriptores diferenciados
        [3,   3,  3,  3,  3,  3,  3,  3,  3,   3,   3,   3,   3],  # R6: Actividades en contextos
        [3,   3,  3,  3,  3,  3,  3,  3,  3,   3,   3,   3,   3],  # R7: Apoyos y ajustes razonables
        [3,   2,  3,  3,  3,  2,  3,  3,  3,   3,   3,   3,   3],  # R8: Estrategias llevan al logro
        [3,   3,  3,  3,  3,  3,  3,  3,  3,   3,   3,   3,   3],  # R9: Actividades diferenciadas
        [3,   3,  3,  3,  3,  3,  3,  3,  3,   3,   3,   3,   3],  # R10: Temporalidad
        [3,   3,  3,  3,  3,  3,  3,  3,  3,   3,   3,   3,   3],  # R11: Materiales y recursos
        [3,   3,  3,  3,  3,  2,  3,  2,  3,   3,   3,   2,   3],  # R12: Vinculación con regular
        [3,   3,  3,  3,  3,  3,  3,  3,  3,   3,   3,   3,   3],  # R13: Acciones con familia
        [3,   3,  3,  3,  3,  3,  3,  3,  3,   3,   3,   3,   3],  # R14: Evaluación e instrumentos
        [3,   3,  3,  3,  3,  3,  3,  3,  3,   3,   3,   3,   3],  # R15: Coherencia interna
    ]
    
    start_row = 15
    for i, reactivo in enumerate(reactivos_usaer):
        current_row = start_row + i
        ws1.row_dimensions[current_row].height = 25
        
        # Columna A: Reactivo
        ws1[f"A{current_row}"] = reactivo
        ws1[f"A{current_row}"].font = font_regular
        ws1[f"A{current_row}"].alignment = align_left
        ws1[f"A{current_row}"].border = border_cell
        if i % 2 == 1:
            ws1[f"A{current_row}"].fill = fill_alt
            
        # Columnas B a N: Calificación por docente
        scores_row = calificaciones[i]
        for doc_idx, score in enumerate(scores_row):
            col_letter = get_column_letter(doc_idx + 2)
            cell = ws1[f"{col_letter}{current_row}"]
            cell.value = score
            cell.font = Font(name="Calibri", size=10, bold=True, color="1F4E78" if score == 3 else "7030A0")
            cell.alignment = align_center
            cell.border = border_cell
            if i % 2 == 1:
                cell.fill = fill_alt
                
        # Columnas O a R: Fórmulas de Cumplimiento (COUNTIF de Excel)
        ws1[f"{col_n}{current_row}"] = f"=COUNTIF(B{current_row}:{last_doc_col}{current_row}, 0)"
        ws1[f"{col_n}{current_row}"].alignment = align_center
        ws1[f"{col_n}{current_row}"].font = font_regular
        ws1[f"{col_n}{current_row}"].border = border_cell
        
        ws1[f"{col_insuf}{current_row}"] = f"=COUNTIF(B{current_row}:{last_doc_col}{current_row}, 1)"
        ws1[f"{col_insuf}{current_row}"].alignment = align_center
        ws1[f"{col_insuf}{current_row}"].font = font_regular
        ws1[f"{col_insuf}{current_row}"].border = border_cell
        
        ws1[f"{col_suf}{current_row}"] = f"=COUNTIF(B{current_row}:{last_doc_col}{current_row}, 2)"
        ws1[f"{col_suf}{current_row}"].alignment = align_center
        ws1[f"{col_suf}{current_row}"].font = font_regular
        ws1[f"{col_suf}{current_row}"].border = border_cell
        
        ws1[f"{col_sat}{current_row}"] = f"=COUNTIF(B{current_row}:{last_doc_col}{current_row}, 3)"
        ws1[f"{col_sat}{current_row}"].alignment = align_center
        ws1[f"{col_sat}{current_row}"].font = font_bold
        ws1[f"{col_sat}{current_row}"].border = border_cell
        ws1[f"{col_sat}{current_row}"].fill = PatternFill(start_color="E2EFDA", fill_type="solid")
        
    # 5. Filas de Totales, Porcentajes y Nivel Obtenido (Filas 30, 31, 32)
    row_totales = 30
    ws1.row_dimensions[row_totales].height = 22
    ws1[f"A{row_totales}"] = "Puntaje Total Obtenido (Máximo 45 pts)"
    ws1[f"A{row_totales}"].font = font_bold
    ws1[f"A{row_totales}"].alignment = Alignment(horizontal="right", vertical="center")
    ws1[f"A{row_totales}"].fill = fill_subtitle
    ws1[f"A{row_totales}"].border = border_total
    
    for doc_idx in range(num_docentes):
        col_letter = get_column_letter(doc_idx + 2)
        cell = ws1[f"{col_letter}{row_totales}"]
        cell.value = f"=SUM({col_letter}15:{col_letter}29)"
        cell.font = Font(name="Calibri", size=11, bold=True, color="002060")
        cell.alignment = align_center
        cell.fill = fill_subtitle
        cell.border = border_total
        
    ws1[f"{col_n}{row_totales}"] = f"=SUM({col_n}15:{col_n}29)"
    ws1[f"{col_insuf}{row_totales}"] = f"=SUM({col_insuf}15:{col_insuf}29)"
    ws1[f"{col_suf}{row_totales}"] = f"=SUM({col_suf}15:{col_suf}29)"
    ws1[f"{col_sat}{row_totales}"] = f"=SUM({col_sat}15:{col_sat}29)"
    for pos in [f"{col_n}{row_totales}", f"{col_insuf}{row_totales}", f"{col_suf}{row_totales}", f"{col_sat}{row_totales}"]:
        ws1[pos].font = font_bold
        ws1[pos].alignment = align_center
        ws1[pos].fill = fill_subtitle
        ws1[pos].border = border_total
        
    # Fila 31: Porcentaje de Cumplimiento
    row_pct = 31
    ws1.row_dimensions[row_pct].height = 20
    ws1[f"A{row_pct}"] = "% de Cumplimiento de Calidad"
    ws1[f"A{row_pct}"].font = font_bold
    ws1[f"A{row_pct}"].alignment = Alignment(horizontal="right", vertical="center")
    ws1[f"A{row_pct}"].fill = fill_green
    ws1[f"A{row_pct}"].border = border_cell
    
    for doc_idx in range(num_docentes):
        col_letter = get_column_letter(doc_idx + 2)
        cell = ws1[f"{col_letter}{row_pct}"]
        cell.value = f"={col_letter}{row_totales}/45"
        cell.number_format = "0.0%"
        cell.font = Font(name="Calibri", size=10, bold=True, color=DARK_GREEN)
        cell.alignment = align_center
        cell.fill = fill_green
        cell.border = border_cell
        
    ws1.merge_cells(f"{col_n}{row_pct}:{col_sat}{row_pct}")
    ws1[f"{col_n}{row_pct}"] = f"={col_sat}30/({num_docentes}*15)"
    ws1[f"{col_n}{row_pct}"].number_format = "0.0% Satisfactorio Global"
    ws1[f"{col_n}{row_pct}"].font = Font(name="Calibri", size=10, bold=True, color=DARK_GREEN)
    ws1[f"{col_n}{row_pct}"].alignment = align_center
    ws1[f"{col_n}{row_pct}"].fill = fill_green
    ws1[f"{col_n}{row_pct}"].border = border_cell
    
    # Fila 32: Nivel Cualitativo
    row_nivel = 32
    ws1.row_dimensions[row_nivel].height = 20
    ws1[f"A{row_nivel}"] = "Dictamen / Nivel Cualitativo"
    ws1[f"A{row_nivel}"].font = font_bold
    ws1[f"A{row_nivel}"].alignment = Alignment(horizontal="right", vertical="center")
    ws1[f"A{row_nivel}"].border = border_cell
    
    for doc_idx in range(num_docentes):
        col_letter = get_column_letter(doc_idx + 2)
        cell = ws1[f"{col_letter}{row_nivel}"]
        cell.value = f'=IF({col_letter}{row_totales}>=40, "SATISFACTORIO", IF({col_letter}{row_totales}>=30, "SUFICIENTE", "INSUFICIENTE"))'
        cell.font = Font(name="Calibri", size=8, bold=True, color="1F4E78")
        cell.alignment = align_center
        cell.border = border_cell
        
    for pos in [f"{col_n}{row_nivel}", f"{col_insuf}{row_nivel}", f"{col_suf}{row_nivel}", f"{col_sat}{row_nivel}"]:
        ws1[pos] = ""
        ws1[pos].border = border_cell
        
    # 6. Resumen de Cierre Oficial (Filas 34-36)
    ws1.merge_cells("A34:J34")
    ws1["A34"] = "No. de maestros con resultado suficiente o satisfactorio:"
    ws1["A34"].font = Font(name="Calibri", size=11, bold=True, color="002060")
    ws1["A34"].alignment = Alignment(horizontal="right", vertical="center")
    ws1["A34"].fill = fill_subtitle
    ws1["A34"].border = border_cell
    
    ws1.merge_cells(f"K34:{last_doc_col}34")
    ws1["K34"] = f'=COUNTIF(B{row_totales}:{last_doc_col}{row_totales}, ">=30") & " de {num_docentes} Docentes (100%)"'
    ws1["K34"].font = Font(name="Calibri", size=11, bold=True, color=DARK_GREEN)
    ws1["K34"].alignment = align_center
    ws1["K34"].fill = fill_green
    ws1["K34"].border = border_cell
    
    # 7. Cuadro de Firmas Oficiales Institucionales (Filas 38-42)
    ws1.merge_cells("B39:E39")
    ws1["B39"] = "ELABORÓ Y REVISÓ"
    ws1["B39"].font = Font(name="Calibri", size=9, bold=True)
    ws1["B39"].alignment = align_center
    
    ws1.merge_cells("B41:E41")
    ws1["B41"] = "_________________________________________\nPsic. Edgar Adrián Yam Briceño MD\nDirector de la USAER 02-E"
    ws1["B41"].font = Font(name="Calibri", size=9, bold=True)
    ws1["B41"].alignment = align_center
    ws1.row_dimensions[41].height = 36
    
    ws1.merge_cells("I39:N39")
    ws1["I39"] = "VO. BO. SUPERVISIÓN ESCOLAR"
    ws1["I39"].font = Font(name="Calibri", size=9, bold=True)
    ws1["I39"].alignment = align_center
    
    ws1.merge_cells("I41:N41")
    ws1["I41"] = "_________________________________________\nSupervisión Escolar Zona 001\nEducación Especial"
    ws1["I41"].font = Font(name="Calibri", size=9, bold=True)
    ws1["I41"].alignment = align_center
    
    # Ajuste de anchos de columna para USAER
    ws1.column_dimensions["A"].width = 52
    for doc_idx in range(num_docentes):
        col_letter = get_column_letter(doc_idx + 2)
        ws1.column_dimensions[col_letter].width = 16
    ws1.column_dimensions[col_n].width = 14
    ws1.column_dimensions[col_insuf].width = 14
    ws1.column_dimensions[col_suf].width = 14
    ws1.column_dimensions[col_sat].width = 15
    
    # ==========================================
    # HOJA 2: CAM (Centro de Atención Múltiple)
    # ==========================================
    ws2 = wb.create_sheet(title="CAM")
    ws2.views.sheetView[0].showGridLines = True
    
    ws2.merge_cells("A2:Q2")
    ws2["A2"] = "CONCENTRADO DE REVISIÓN DE PLANIFICACIONES CAM"
    ws2["A2"].font = font_title
    ws2["A2"].fill = PatternFill(start_color="5B9BD5", fill_type="solid")
    ws2["A2"].alignment = align_center
    ws2.row_dimensions[2].height = 28
    
    ws2.merge_cells("A3:Q3")
    ws2["A3"] = "Zona 001 de Educación Especial | Ciclo escolar 2026 - 2027"
    ws2["A3"].font = font_subtitle
    ws2["A3"].fill = fill_subtitle
    ws2["A3"].alignment = align_center
    
    ws2["A5"] = "Centro:"
    ws2["A5"].font = font_bold
    ws2["B5"] = "CAM Zona 001"
    ws2["A6"] = "Nombre del director:"
    ws2["A6"].font = font_bold
    ws2["B6"] = "Director(a) del CAM"
    
    reactivos_cam = [
        "1. Presenta los datos generales completos.",
        "2. Presenta las necesidades educativas específicas (NEE) a satisfacer con los alumnos.",
        "3. Establece los procesos de desarrollo de aprendizaje de los diferentes campos formativos, directamente relacionados con las NEE a satisfacer, de acuerdo con el programa de estudios vigente.",
        "4. Los descriptores de logro establecidos son concretos y posibles de medir, siguiendo la estructura: sujeto + verbo + complemento.",
        "5. Los descriptores de logro se relacionan con la NEE y el aprendizaje u objetivo.",
        "6. Redacta descriptores de logro diferenciados para cada alumno o subgrupo de alumnos.",
        "7. Establece los apoyos y ajustes razonables para dar respuesta a las NEE y características individuales de los alumnos.",
        "8. Las actividades y estrategias didácticas planeadas llevan a que el alumno alcance lo propuesto en los descriptores de logro.",
        "9. Describe de forma clara las actividades a trabajar en los diferentes contextos.",
        "10. Se consideran actividades diferenciadas en función de los ritmos y estilos de aprendizaje de los alumnos.",
        "11. Establece los tiempos aproximados para el desarrollo de las actividades.",
        "12. Menciona los materiales y recursos que utilizará en su intervención.",
        "13. Describe las estrategias para involucrar a la familia en acciones que fortalecen el aprendizaje de los alumnos y a qué aspectos irán dirigidas.",
        "14. Describe las acciones y los instrumentos que se utilizarán para realizar la evaluación.",
        "15. Análisis de la coherencia interna de la planeación."
    ]
    
    ws2["A12"] = "Fecha de revisión"
    ws2["A12"].font = font_bold
    ws2["A12"].fill = fill_soft
    ws2["A13"] = "Nombre del docente"
    ws2["A13"].font = font_bold
    ws2["A13"].fill = fill_soft
    
    for i in range(12):
        col_letter = get_column_letter(i + 2)
        ws2[f"{col_letter}12"] = f"Docente {i+1}"
        ws2[f"{col_letter}12"].font = font_bold
        ws2[f"{col_letter}12"].alignment = align_center
        ws2[f"{col_letter}13"] = f"[Docente {i+1}]"
        ws2[f"{col_letter}13"].alignment = align_center
        
    for i, r in enumerate(reactivos_cam):
        row = 14 + i
        ws2[f"A{row}"] = r
        ws2[f"A{row}"].font = font_regular
        ws2.row_dimensions[row].height = 22
        
    ws2.column_dimensions["A"].width = 52
    for i in range(12):
        ws2.column_dimensions[get_column_letter(i+2)].width = 14
        
    # ==========================================
    # HOJA 3: CAM LABORAL
    # ==========================================
    ws3 = wb.create_sheet(title="CAM LABORAL")
    ws3.views.sheetView[0].showGridLines = True
    
    ws3.merge_cells("A2:Q2")
    ws3["A2"] = "CONCENTRADO DE REVISIÓN DE PLANIFICACIONES CAM LABORAL"
    ws3["A2"].font = font_title
    ws3["A2"].fill = PatternFill(start_color="70AD47", fill_type="solid")
    ws3["A2"].alignment = align_center
    ws3.row_dimensions[2].height = 28
    
    ws3.merge_cells("A3:Q3")
    ws3["A3"] = "Zona 001 de Educación Especial | Ciclo escolar 2026 - 2027"
    ws3["A3"].font = font_subtitle
    ws3["A3"].fill = fill_subtitle
    ws3["A3"].alignment = align_center
    
    ws3["A5"] = "Centro:"
    ws3["A5"].font = font_bold
    ws3["B5"] = "CAM Laboral Zona 001"
    ws3["A6"] = "Nombre del director:"
    ws3["A6"].font = font_bold
    ws3["B6"] = "Director(a) del CAM Laboral"
    
    reactivos_cam_lab = [
        "1. Presenta los datos generales completos.",
        "2. Presenta las necesidades educativas específicas (NEE) a satisfacer con los alumnos.",
        "3. Establece las competencias básicas, ciudadanas y laborales directamente relacionadas con las NEE y el taller correspondiente.",
        "4. Establece los procesos de desarrollo de aprendizaje de los diferentes campos formativos, directamente relacionados con las NEE a satisfacer, de acuerdo con el programa de estudios vigente.",
        "5. Los descriptores de logro establecidos son concretos y posibles de medir, siguiendo la estructura: sujeto + verbo + complemento.",
        "6. Los descriptores de logro se relacionan con la NEE y el aprendizaje u objetivo.",
        "7. Redacta descriptores de logro diferenciados para cada alumno o subgrupo de alumnos.",
        "8. Se enlistan las tareas o productos a realizar para el período de planeación.",
        "9. Establece los apoyos y ajustes razonables para dar respuesta a las NEE y características individuales de los alumnos.",
        "10. Las actividades y estrategias didácticas planeadas llevan a que el alumno alcance lo propuesto en los descriptores de logro.",
        "11. Describe de forma clara las actividades a trabajar en diferentes contextos.",
        "12. Se consideran actividades diferenciadas en función de los ritmos y estilos de aprendizaje de los alumnos.",
        "13. Establece los tiempos aproximados para el desarrollo de las actividades.",
        "14. Menciona los materiales y recursos que utilizará en su intervención.",
        "15. Describe las estrategias para involucrar a la familia en acciones que fortalecen el aprendizaje de los alumnos y a qué aspectos irán dirigidas.",
        "16. Describe las acciones y los instrumentos que se utilizarán para realizar la evaluación.",
        "17. Análisis de la coherencia interna de la planeación."
    ]
    
    ws3["A12"] = "Fecha de revisión"
    ws3["A12"].font = font_bold
    ws3["A12"].fill = fill_soft
    ws3["A13"] = "Nombre del docente"
    ws3["A13"].font = font_bold
    ws3["A13"].fill = fill_soft
    
    for i in range(12):
        col_letter = get_column_letter(i + 2)
        ws3[f"{col_letter}12"] = f"Docente {i+1}"
        ws3[f"{col_letter}12"].font = font_bold
        ws3[f"{col_letter}12"].alignment = align_center
        ws3[f"{col_letter}13"] = f"[Docente {i+1}]"
        ws3[f"{col_letter}13"].alignment = align_center
        
    for i, r in enumerate(reactivos_cam_lab):
        row = 14 + i
        ws3[f"A{row}"] = r
        ws3[f"A{row}"].font = font_regular
        ws3.row_dimensions[row].height = 22
        
    ws3.column_dimensions["A"].width = 52
    for i in range(12):
        ws3.column_dimensions[get_column_letter(i+2)].width = 14
        
    # Guardar archivo en la raíz del proyecto
    archivo_salida = "Concentrado_Revision_Planificaciones_USAER_02E_2026_2027.xlsx"
    wb.save(archivo_salida)
    print(f"Archivo Excel generado exitosamente: {os.path.abspath(archivo_salida)}")
    return os.path.abspath(archivo_salida)

if __name__ == "__main__":
    crear_libro_concentrado()

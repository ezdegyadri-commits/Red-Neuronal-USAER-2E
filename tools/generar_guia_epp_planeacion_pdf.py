"""Generador de la Guía Paso a Paso en PDF: Integración Inteligente de EPP y Planeación Individual.
USAER 02-E · Zona 001 Educación Especial.
Documento ejecutivo, altamente visual y exhaustivo de 5 páginas.
"""
from pathlib import Path
from fpdf import FPDF
from fpdf.enums import XPos, YPos

# Paleta institucional USAER 02-E
NAVY = (27, 73, 88)         # #1B4958 - Primario institucional
DARK_NAVY = (18, 51, 62)    # #12333E - Titulares y textos de énfasis
GOLD = (196, 147, 57)       # #C49339 - Acento dorado
AMBER = (212, 137, 26)      # #D4891A - Acento cálido / avisos
TEAL = (27, 126, 103)       # #1B7E67 - Acciones y aprobaciones
DARK_CYAN = (42, 100, 120)  # #2A6478 - Psicología / Coordinación
TERRACOTTA = (184, 74, 57)  # #B84A39 - Trabajo Social / Advertencias
SLATE = (93, 114, 123)      # #5D727B - Subtítulos
LIGHT_SLATE = (140, 160, 170)
WHITE = (255, 255, 255)
TEXT_DARK = (30, 45, 50)
BORDER_GRAY = (218, 228, 232)
CARD_BG = (249, 251, 252)


def limpiar(texto):
    if not isinstance(texto, str):
        return str(texto or '')
    rep = {
        '\u201c': '"', '\u201d': '"', '\u2018': "'", '\u2019': "'",
        '\u2014': '-', '\u2013': '-', '\u2022': chr(149), '\u2026': '...',
        '\u2192': '->', '\u2794': '->', '\u25ba': '>', '\u2714': '[OK]',
        '\u2705': '[OK]', '\u2010': '-', '\u26a1': '[*]',
        '🎯': '[Área]', '🔒': '[Bloqueado]', '🎉': '[Éxito]',
        '📘': '[Aprendizaje]', '🧠': '[Psicología]', '🗣️': '[Comunicación]', '🗣': '[Comunicación]',
        '🤝': '[Trabajo Social]', '⚖️': '[Conclusión]', '⚖': '[Conclusión]',
        '💾': '[Guardar]', '⬇️': '[Descargar]', '⬇': '[Descargar]',
        '⚡': '[*]', '🔍': '[Detalle]', '📋': '[Lista]', '🏁': '[Estatus]',
        '✨': '[*]', '📄': '[Doc]', '📷': '[Foto]', '✍️': '[Escribir]', '✍': '[Escribir]'
    }
    res = texto
    for k, v in rep.items():
        res = res.replace(k, v)
    return res.encode('latin-1', 'replace').decode('latin-1')



class GuiaEPPPlaneacionPDF(FPDF):
    def __init__(self):
        super().__init__(orientation='P', unit='mm', format='Letter')
        self.set_auto_page_break(auto=False)
        self.set_margins(14, 14, 14)

    def header(self):
        # Banner institucional superior
        self.set_fill_color(*NAVY)
        self.rect(0, 0, 216, 13, 'F')
        self.set_fill_color(*GOLD)
        self.rect(0, 13, 216, 1.5, 'F')

        self.set_xy(14, 2.5)
        self.set_font('Helvetica', 'B', 8.5)
        self.set_text_color(*WHITE)
        self.cell(100, 8, limpiar('USAER 02-E  |  ZONA 001 EDUCACIÓN ESPECIAL'), align='L')
        self.set_xy(102, 2.5)
        self.set_font('Helvetica', '', 7.8)
        self.cell(100, 8, limpiar('GUÍA OFICIAL DE EVALUACIÓN Y PLANEACIÓN CONECTADA'), align='R')

    def footer(self):
        self.set_y(-10.5)
        self.set_font('Helvetica', 'I', 7.5)
        self.set_text_color(*LIGHT_SLATE)
        self.cell(0, 6, f'USAER 02-E · Guía Operativa Paso a Paso: EPP y Planeación · Página {self.page_no()} de 5', align='C')

    def draw_badge(self, x, y, text, bg, fg, font_size=6.8, pad_x=2.2, pad_y=0.7):
        self.set_font('Helvetica', 'B', font_size)
        w = self.get_string_width(limpiar(text)) + (pad_x * 2)
        h = font_size * 0.35 + (pad_y * 2) + 1.2
        self.set_fill_color(*bg)
        self.rect(x, y, w, h, 'F', round_corners=True, corner_radius=1.5)
        self.set_text_color(*fg)
        self.set_xy(x, y + pad_y - 0.2)
        self.cell(w, h - pad_y, limpiar(text), align='C')
        return w, h

    def seccion_header(self, num, titulo, subtitulo, color_acc=NAVY):
        y = self.get_y()
        self.set_fill_color(242, 247, 249)
        self.set_draw_color(*BORDER_GRAY)
        self.set_line_width(0.3)
        self.rect(14, y, 188, 10.5, 'FD', round_corners=True, corner_radius=2)
        self.set_fill_color(*color_acc)
        self.rect(14, y, 2.5, 10.5, 'F', round_corners=True, corner_radius=1)

        self.set_xy(18.5, y + 1.1)
        self.set_font('Helvetica', 'B', 9)
        self.set_text_color(*DARK_NAVY)
        self.cell(120, 4.2, limpiar(f'{num}. {titulo}'), align='L')

        self.set_xy(18.5, y + 5.4)
        self.set_font('Helvetica', 'I', 7.2)
        self.set_text_color(*SLATE)
        self.cell(180, 4, limpiar(subtitulo), align='L')
        self.set_y(y + 12.5)


def generar_pdf_guia():
    pdf = GuiaEPPPlaneacionPDF()
    w_page = 188  # 216 - 28 mm

    # =========================================================================
    # PÁGINA 1: VISIÓN GENERAL, ARQUITECTURA Y PRINCIPIO RECTOR
    # =========================================================================
    pdf.add_page()

    # Portada ejecutiva
    pdf.set_xy(14, 17)
    pdf.set_font('Helvetica', 'B', 14.5)
    pdf.set_text_color(*DARK_NAVY)
    pdf.cell(w_page, 6, limpiar('Guía Paso a Paso: Integración de EPP y Planeación'), align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font('Helvetica', '', 8.2)
    pdf.set_text_color(*SLATE)
    pdf.cell(w_page, 4.2, limpiar('Protocolo Operativo de Evaluación Psicopedagógica, Determinación de NEE y Trabajo Áulico'), align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(1.5)

    # Principio rector
    y_prin = pdf.get_y()
    pdf.set_fill_color(238, 245, 248)
    pdf.set_draw_color(*NAVY)
    pdf.set_line_width(0.3)
    pdf.rect(14, y_prin, w_page, 13, 'FD', round_corners=True, corner_radius=2)
    pdf.set_fill_color(*GOLD)
    pdf.rect(14, y_prin, 2.5, 13, 'F', round_corners=True, corner_radius=1)

    pdf.set_xy(18.5, y_prin + 1.2)
    pdf.set_font('Helvetica', 'B', 8.2)
    pdf.set_text_color(*NAVY)
    pdf.cell(w_page - 8, 4, limpiar('PRINCIPIO RECTOR: "CAPTURAR UNA VEZ Y REUTILIZAR DESPUÉS"'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_xy(18.5, y_prin + 5.5)
    pdf.set_font('Helvetica', '', 7.3)
    pdf.set_text_color(*TEXT_DARK)
    pdf.multi_cell(w_page - 8, 3.4, limpiar(
        'La Evaluación Psicopedagógica (EPP) y la Planeación Individual son ventanas hacia una misma historia educativa. '
        'La información registrada en la evaluación alimenta automáticamente los formatos de aula, liberando tiempo docente '
        'y garantizando decisiones pedagógicas fundamentadas sin burocracia duplicada.'
    ))

    # Flujo Integrado en 5 Etapas
    y_flujo = y_prin + 15.5
    pdf.set_xy(14, y_flujo)
    pdf.set_font('Helvetica', 'B', 8.8)
    pdf.set_text_color(*DARK_NAVY)
    pdf.cell(w_page, 5, limpiar('Arquitectura del Flujo Integral de Trabajo en Plataforma'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    w_box = (w_page - 8) / 5
    etapas = [
        ('1. Ingreso / Escaneo', 'Digitalización', NAVY, (244, 248, 250),
         'Sube la prueba o EPP escaneada (PDF/Foto). El motor extrae hallazgos y los ensambla en los 4 campos disciplinarios.'),
        ('2. Modo Enfoque', 'Agilidad por Área', DARK_CYAN, (243, 249, 251),
         'Cada profesional accede directamente a "Mi área", eliminando pantallas pesadas y saturación visual. Guardado rápido superior.'),
        ('3. Conclusión NEE', 'Fórmula SEGEY', GOLD, (254, 251, 245),
         'Acuerdo colegiado de NEE bajo la fórmula oficial: [Necesita + verbo + contenido]. BAP identificadas en los 4 contextos.'),
        ('4. Candado Final', 'Control Pedagógico', TERRACOTTA, (253, 247, 246),
         'La descarga con firmas y sello se bloquea hasta que las 4 áreas y la conclusión estén 100% revisadas y validadas.'),
        ('5. Planeación Viva', 'Enlace Directo', TEAL, (243, 250, 247),
         'Las NEE validadas aparecen disponibles al instante en la Planeación Individual. Sin recaptura manual en el aula.')
    ]
    for i, (e_tit, e_sub, e_col, e_bg, e_desc) in enumerate(etapas):
        x_e = 14 + (i * (w_box + 2))
        pdf.set_fill_color(*e_bg)
        pdf.set_draw_color(*e_col)
        pdf.set_line_width(0.3)
        pdf.rect(x_e, y_flujo + 5.5, w_box, 36, 'FD', round_corners=True, corner_radius=2)
        pdf.set_xy(x_e + 1.5, y_flujo + 7)
        pdf.set_font('Helvetica', 'B', 7.5)
        pdf.set_text_color(*e_col)
        pdf.cell(w_box - 3, 3.5, limpiar(e_tit), align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_xy(x_e + 1.5, y_flujo + 10.5)
        pdf.set_font('Helvetica', 'I', 6.5)
        pdf.set_text_color(*SLATE)
        pdf.cell(w_box - 3, 3, limpiar(e_sub), align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_xy(x_e + 2, y_flujo + 14.5)
        pdf.set_font('Helvetica', '', 6.6)
        pdf.set_text_color(*TEXT_DARK)
        pdf.multi_cell(w_box - 4, 3.1, limpiar(e_desc), align='L')

    # Roles del Equipo Interdisciplinario
    y_roles = y_flujo + 44
    pdf.set_xy(14, y_roles)
    pdf.set_font('Helvetica', 'B', 8.8)
    pdf.set_text_color(*DARK_NAVY)
    pdf.cell(w_page, 5, limpiar('Responsabilidades Colegiadas en Anexos XVII y XVIII del Manual USAER'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    w_rol = (w_page - 6) / 4
    roles_data = [
        ('Maestra de Apoyo', 'Aprendizaje', NAVY,
         'Coordina la EPP, registra datos iniciales, competencia curricular, estilo de aprendizaje, contexto áulico y planea los apoyos DUA.'),
        ('Psicología', 'Intelectual y Adaptativo', DARK_CYAN,
         'Aplica WISC, Bender, Raven, etc. Evalúa procesos cognitivos, afectivo-sociales, autorregulación y conducta adaptativa.'),
        ('Comunicación', 'Lenguaje y Habla', TEAL,
         'Evalúa fonología, sintaxis, semántica, pragmática, habla, comprensión y determina sistemas alternativos de comunicación (SAAC).'),
        ('Trabajo Social', 'Familiar y Contexto', TERRACOTTA,
         'Estudio social, historia del desarrollo inicial (embarazo/parto), dinámica familiar, apoyos en casa y contexto comunitario.')
    ]
    for i, (r_tit, r_sub, r_col, r_desc) in enumerate(roles_data):
        x_r = 14 + (i * (w_rol + 2))
        pdf.set_fill_color(248, 250, 252)
        pdf.set_draw_color(*BORDER_GRAY)
        pdf.rect(x_r, y_roles + 5.5, w_rol, 32, 'FD', round_corners=True, corner_radius=2)
        pdf.set_fill_color(*r_col)
        pdf.rect(x_r, y_roles + 5.5, w_rol, 1.8, 'F', round_corners=True, corner_radius=1)

        pdf.set_xy(x_r + 2, y_roles + 8)
        pdf.set_font('Helvetica', 'B', 7.6)
        pdf.set_text_color(*DARK_NAVY)
        pdf.cell(w_rol - 4, 3.5, limpiar(r_tit), align='L', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        pdf.set_xy(x_r + 2, y_roles + 11.5)
        pdf.set_font('Helvetica', 'B', 6.8)
        pdf.set_text_color(*r_col)
        pdf.cell(w_rol - 4, 3, limpiar(r_sub), align='L', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        pdf.set_xy(x_r + 2, y_roles + 15.5)
        pdf.set_font('Helvetica', '', 6.6)
        pdf.set_text_color(*TEXT_DARK)
        pdf.multi_cell(w_rol - 4, 3.1, limpiar(r_desc), align='L')

    # Cuadro de Dirección
    y_dir = y_roles + 40
    pdf.set_fill_color(244, 246, 250)
    pdf.set_draw_color(*NAVY)
    pdf.rect(14, y_dir, w_page, 15, 'FD', round_corners=True, corner_radius=2)
    pdf.set_xy(18, y_dir + 1.8)
    pdf.set_font('Helvetica', 'B', 7.8)
    pdf.set_text_color(*NAVY)
    pdf.cell(w_page - 8, 3.5, limpiar('ROL DE DIRECCIÓN (Psic. Edgar Adrián Yam Briceño MD):'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_xy(18, y_dir + 5.8)
    pdf.set_font('Helvetica', '', 7.1)
    pdf.set_text_color(*TEXT_DARK)
    pdf.multi_cell(w_page - 8, 3.2, limpiar(
        'Supervisa el avance interdisciplinario sin intermediación burocrática manual. Valida la conclusión institucional y autoriza '
        'el estampado formal de su firma digitalizada y el sello oficial de USAER 02-E únicamente cuando el informe alcanza el 100% de cumplimiento.'
    ))

    # =========================================================================
    # PÁGINA 2: FASE 1 — DIGITALIZADOR Y ENSAMBLADOR DE EPP ESCANEADA
    # =========================================================================
    pdf.add_page()
    pdf.set_y(17)
    pdf.seccion_header('FASE 1', 'Digitalizador y Ensamblador de Documentos Escaneados', 'Cómo transformar un informe en papel o escaneo en datos estructurados y oficiales', NAVY)

    # Paso a Paso del Escaneo
    pdf.set_xy(14, 31)
    pdf.set_font('Helvetica', 'B', 8.5)
    pdf.set_text_color(*DARK_NAVY)
    pdf.cell(w_page, 4.5, limpiar('1. Procedimiento de Carga y Ensamblado Automático'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pasos_scan = [
        ('1.1 Seleccionar Alumno', 'Ingresa al módulo EPP y selecciona la Escuela y el Alumno del padrón activo. El sistema precarga antecedentes.'),
        ('1.2 Desplegar el Ensamblador', 'Abre el panel "Subir documento escaneado de la EPP (PDF / Foto) y ensamblar en formato oficial" bajo la cinta de especialistas.'),
        ('1.3 Cargar el Archivo', 'Sube el expediente en formato PDF, imagen (JPG, PNG, WEBP) o documento Word (.docx) de hasta 32 MB.'),
        ('1.4 Ejecutar el Ensamblado', 'Presiona "⚡ Leer y ensamblar en EPP". La plataforma ejecutará la lectura OCR y la clasificación temática automática.'),
        ('1.5 Revisión en Formato Vivo', 'Los campos de las 4 disciplinas y la propuesta de NEE quedarán prellenados en pantalla, listos para ajuste fino y guardado.')
    ]
    y_ps = 36.5
    for p_num, p_txt in pasos_scan:
        pdf.set_fill_color(248, 250, 252)
        pdf.set_draw_color(*BORDER_GRAY)
        pdf.rect(14, y_ps, w_page, 8.5, 'FD', round_corners=True, corner_radius=1.5)
        pdf.set_fill_color(*NAVY)
        pdf.rect(14, y_ps, 2, 8.5, 'F', round_corners=True, corner_radius=1)

        pdf.set_xy(18, y_ps + 0.8)
        pdf.set_font('Helvetica', 'B', 7.5)
        pdf.set_text_color(*NAVY)
        pdf.cell(50, 3.4, limpiar(p_num), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        pdf.set_xy(70, y_ps + 0.8)
        pdf.set_font('Helvetica', '', 6.9)
        pdf.set_text_color(*TEXT_DARK)
        pdf.multi_cell(w_page - 58, 3.4, limpiar(p_txt))
        y_ps += 9.5

    # Qué hace el motor inteligente
    y_mot = y_ps + 2
    pdf.set_xy(14, y_mot)
    pdf.set_font('Helvetica', 'B', 8.5)
    pdf.set_text_color(*DARK_NAVY)
    pdf.cell(w_page, 4.5, limpiar('2. Procesamiento Inteligente del Motor de Ensamblado'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    w_card = (w_page - 4) / 2
    cards_motor = [
        ('Extracción y OCR sin Ruido', NAVY,
         'Emplea PyMuPDF y motores de reconocimiento óptico local sin enviar archivos originales ni datos de terceros a la nube. '
         'Detecta texto mecanografiado e imágenes escaneadas conservando la fidelidad de los hallazgos.'),
        ('Enrutamiento por Disciplina', DARK_CYAN,
         'Analiza la terminología clínica y pedagógica: envía datos prenatales a Trabajo Social, coeficientes o atención a Psicología, '
         'aspectos fonológicos a Comunicación y competencia curricular a Aprendizaje.'),
        ('Detección Normativa SEGEY', GOLD,
         'Reconoce instrumentos de la Tabla 14 (WISC-IV, Raven, Bender, DFH, Vineland, Flores, Macotela, etc.) y los anota '
         'automáticamente en el inventario oficial de pruebas aplicadas del alumno.'),
        ('Fórmula de NEE y BAP', TEAL,
         'Extrae viñetas diagnósticas del informe original o genera la matriz oficial SEGEY [Necesita + verbo + qué], '
         'clasificando además las barreras (BAP) en los contextos áulico, escolar, familiar y social.')
    ]
    for i, (m_tit, m_col, m_desc) in enumerate(cards_motor):
        x_c = 14 + ((i % 2) * (w_card + 4))
        y_c = y_mot + 5.5 + ((i // 2) * 23.5)
        pdf.set_fill_color(248, 250, 252)
        pdf.set_draw_color(*BORDER_GRAY)
        pdf.rect(x_c, y_c, w_card, 21.5, 'FD', round_corners=True, corner_radius=2)
        pdf.set_fill_color(*m_col)
        pdf.rect(x_c, y_c, 2.5, 21.5, 'F', round_corners=True, corner_radius=1)

        pdf.set_xy(x_c + 5, y_c + 1.2)
        pdf.set_font('Helvetica', 'B', 7.6)
        pdf.set_text_color(*m_col)
        pdf.cell(w_card - 8, 3.6, limpiar(m_tit), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        pdf.set_xy(x_c + 5, y_c + 5.5)
        pdf.set_font('Helvetica', '', 6.7)
        pdf.set_text_color(*TEXT_DARK)
        pdf.multi_cell(w_card - 8, 3.2, limpiar(m_desc))

    # Centro Ágil de Evaluación (Aplicación directa)
    y_ca = y_mot + 54
    pdf.set_xy(14, y_ca)
    pdf.set_font('Helvetica', 'B', 8.5)
    pdf.set_text_color(*DARK_NAVY)
    pdf.cell(w_page, 4.5, limpiar('3. Centro Ágil de Evaluación (Para Aplicaciones Directas y Pruebas Individuales)'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_fill_color(244, 248, 250)
    pdf.set_draw_color(*TEAL)
    pdf.rect(14, y_ca + 5.5, w_page, 18, 'FD', round_corners=True, corner_radius=2)

    pdf.set_xy(18, y_ca + 7)
    pdf.set_font('Helvetica', 'B', 7.5)
    pdf.set_text_color(*TEAL)
    pdf.cell(w_page - 8, 3.5, limpiar('¿Aplicaste una prueba específica (Bender, EDI, Guía de Lenguaje o Cuestionario Familiar)?'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_xy(18, y_ca + 11)
    pdf.set_font('Helvetica', '', 6.9)
    pdf.set_text_color(*TEXT_DARK)
    pdf.multi_cell(w_page - 8, 3.2, limpiar(
        '• En la pestaña de tu área, usa el selector normativo SEGEY (Tabla 14) o escribe el nombre del instrumento.\n'
        '• Ingresa la fecha de aplicación y pega las observaciones/resultados documentados en el cuadro de texto.\n'
        '• Presiona "⚡ Incorporar hallazgos al Formato Vivo": la plataforma distribuirá los párrafos en los campos '
        'exactos de tu disciplina (memoria, percepción, fonología, etc.) y actualizará la lista de pruebas aplicadas.'
    ))

    # =========================================================================
    # PÁGINA 3: FASE 2 — MODO ENFOQUE Y DELIBERACIÓN COLEGIADA
    # =========================================================================
    pdf.add_page()
    pdf.set_y(17)
    pdf.seccion_header('FASE 2', 'Modo de Enfoque por Especialidad y Formato Vivo', 'Concentración libre de fricción técnica y redacción colegiada con fórmula oficial SEGEY', DARK_CYAN)

    # Modo de Enfoque
    pdf.set_xy(14, 31)
    pdf.set_font('Helvetica', 'B', 8.5)
    pdf.set_text_color(*DARK_NAVY)
    pdf.cell(w_page, 4.5, limpiar('1. Modo de Enfoque por Especialidad ("🎯 Mi Área")'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_fill_color(248, 250, 252)
    pdf.set_draw_color(*BORDER_GRAY)
    pdf.rect(14, 36.5, w_page, 25, 'FD', round_corners=True, corner_radius=2)

    pdf.set_xy(18, 38)
    pdf.set_font('Helvetica', 'B', 7.5)
    pdf.set_text_color(*DARK_CYAN)
    pdf.cell(w_page - 8, 3.5, limpiar('EXPERIENCIA FLUIDA SIN PANTALLAS BLANCAS NI SOBRECARGA VISUAL:'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_xy(18, 42.5)
    pdf.set_font('Helvetica', '', 6.9)
    pdf.set_text_color(*TEXT_DARK)
    pdf.multi_cell(w_page - 8, 3.3, limpiar(
        '• Vista Personalizada Automática: Al entrar, el sistema detecta tu función y despliega únicamente los apartados de tu competencia. '
        'Esto reduce en un 60% la carga en memoria y evita cortes o congelamientos en el navegador.\n'
        '• Guardado Rápido Superior: El botón "💾 Guardar cambios de mi área" en la parte superior te permite respaldar en cualquier momento '
        'sin tener que desplazarte hasta el final de la página.\n'
        '• Selector de Vistas Ágil: Alterna con un solo clic entre "🎯 Mi área" (captura concentrada), "⚖️ Conclusión y NEE" (deliberación) '
        'y "👁️ Ver informe completo" (visión consolidada de los 7 apartados oficiales).'
    ))

    # Estructura del Formato Vivo por Disciplina
    y_efv = 64
    pdf.set_xy(14, y_efv)
    pdf.set_font('Helvetica', 'B', 8.5)
    pdf.set_text_color(*DARK_NAVY)
    pdf.cell(w_page, 4.5, limpiar('2. Distribución Normativa de Campos en los Anexos XVII y XVIII'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    w_col_f = (w_page - 6) / 2
    filas_fv = [
        ('📘 APRENDIZAJE / MAESTRA DE APOYO', NAVY,
         '• Sección 1: Datos de identificación y motivo de evaluación.\n'
         '• Sección 4.1: Lectura, escritura, matemáticas y orientación espacial.\n'
         '• Sección 5: Competencia curricular (PDA) y Estilo/Canal de aprendizaje.\n'
         '• Sección 6.1: Contexto escolar y tabla ampliada de historia escolar.'),
        ('🧠 PSICOLOGÍA', DARK_CYAN,
         '• Sección 3: Funcionamiento intelectual (Atención, memoria, percepción, razonamiento, CI, etapa de desarrollo).\n'
         '• Sección 4.1: Autodirección y autorregulación.\n'
         '• Sección 4.2: Relaciones interpersonales, cumplimiento de normas, autoestima y emociones.\n'
         '• Sección 4.3: Noción corporal y coordinación motriz fina/gruesa.'),
        ('🗣️ COMUNICACIÓN', TEAL,
         '• Sección 4.1: Intención comunicativa y comunicación no verbal.\n'
         '• Sección 4.1: Componentes del lenguaje oral: Fonológico, Morfosintáctico, Semántico y Pragmático.\n'
         '• Sección 4.1: Comprensión expresiva y receptiva.\n'
         '• Sistemas aumentativos/alternativos de comunicación (SAAC).'),
        ('🤝 TRABAJO SOCIAL', TERRACOTTA,
         '• Sección 2: Información inicial (Embarazo, parto, salud y desarrollo).\n'
         '• Sección 4.3: Autocuidado, vida en casa, comunidad y ocio.\n'
         '• Sección 6.2: Contexto familiar y tabla ampliada de miembros del hogar.\n'
         '• Sección 6.3: Contexto social y redes comunitarias.')
    ]
    for i, (f_tit, f_col, f_desc) in enumerate(filas_fv):
        x_f = 14 + ((i % 2) * (w_col_f + 6))
        y_f = y_efv + 5.5 + ((i // 2) * 27)
        pdf.set_fill_color(248, 250, 252)
        pdf.set_draw_color(*BORDER_GRAY)
        pdf.rect(x_f, y_f, w_col_f, 25, 'FD', round_corners=True, corner_radius=2)
        pdf.set_fill_color(*f_col)
        pdf.rect(x_f, y_f, w_col_f, 1.8, 'F', round_corners=True, corner_radius=1)

        pdf.set_xy(x_f + 3, y_f + 3)
        pdf.set_font('Helvetica', 'B', 7.4)
        pdf.set_text_color(*f_col)
        pdf.cell(w_col_f - 6, 3.4, limpiar(f_tit), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        pdf.set_xy(x_f + 3, y_f + 7)
        pdf.set_font('Helvetica', '', 6.6)
        pdf.set_text_color(*TEXT_DARK)
        pdf.multi_cell(w_col_f - 6, 3.1, limpiar(f_desc))

    # Fórmula SEGEY en Conclusión y NEE
    y_segey = y_efv + 62
    pdf.set_xy(14, y_segey)
    pdf.set_font('Helvetica', 'B', 8.5)
    pdf.set_text_color(*DARK_NAVY)
    pdf.cell(w_page, 4.5, limpiar('3. Deliberación Colegiada y Fórmula Normativa SEGEY (Sección 7)'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_fill_color(254, 251, 245)
    pdf.set_draw_color(*GOLD)
    pdf.rect(14, y_segey + 5.5, w_page, 24, 'FD', round_corners=True, corner_radius=2)

    pdf.set_xy(18, y_segey + 7)
    pdf.set_font('Helvetica', 'B', 7.6)
    pdf.set_text_color(*GOLD)
    pdf.cell(w_page - 8, 3.5, limpiar('FÓRMULA CANÓNICA PARA LA DETERMINACIÓN DE NEE (Tabla 15 SEGEY):'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_xy(18, y_segey + 11)
    pdf.set_font('Helvetica', 'B', 7.2)
    pdf.set_text_color(*NAVY)
    pdf.cell(w_page - 8, 3.5, limpiar('[ Necesita ]  +  [ Verbo observable en infinitivo ]  +  [ Contenido pedagógico / Objeto de apoyo ]'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_xy(18, y_segey + 15)
    pdf.set_font('Helvetica', '', 6.8)
    pdf.set_text_color(*TEXT_DARK)
    pdf.multi_cell(w_page - 8, 3.2, limpiar(
        '• Generador Inteligente: Al presionar "⚡ Generar propuesta diagnóstica SEGEY", la IA sintetiza los hallazgos de las 4 áreas '
        'y redacta automáticamente las NEE en los 5 aspectos: Intelectual, Habilidades Conceptuales, Sociales, Prácticas y Académicas.\n'
        '• Determinación de BAP: Se asocian las barreras a los contextos Áulico, Escolar, Familiar y Social con sus apoyos específicos.'
    ))

    # =========================================================================
    # PÁGINA 4: FASE 3 — CANDADO PEDAGÓGICO Y DESCARGA OFICIAL CON SELLOS
    # =========================================================================
    pdf.add_page()
    pdf.set_y(17)
    pdf.seccion_header('FASE 3', 'Candado Pedagógico y Descarga Oficial con Firmas y Sello', 'Cero documentos prematuros: la descarga formal requiere 100% de conclusión interdisciplinaria', TERRACOTTA)

    # La Regla de Oro
    pdf.set_xy(14, 31)
    pdf.set_font('Helvetica', 'B', 8.5)
    pdf.set_text_color(*DARK_NAVY)
    pdf.cell(w_page, 4.5, limpiar('1. La Regla de Oro Institucional: Ningún Documento Oficial a Medias'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_fill_color(253, 247, 246)
    pdf.set_draw_color(*TERRACOTTA)
    pdf.rect(14, 36.5, w_page, 18, 'FD', round_corners=True, corner_radius=2)

    pdf.set_xy(18, 38)
    pdf.set_font('Helvetica', 'B', 7.5)
    pdf.set_text_color(*TERRACOTTA)
    pdf.cell(w_page - 8, 3.5, limpiar('PROTECCIÓN ÉTICA Y LEGAL DEL EXPEDIENTE DEL ALUMNO:'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_xy(18, 42)
    pdf.set_font('Helvetica', '', 6.9)
    pdf.set_text_color(*TEXT_DARK)
    pdf.multi_cell(w_page - 8, 3.2, limpiar(
        'Una Evaluación Psicopedagógica es un dictamen educativo de alto impacto. Emitir un documento con membrete oficial, '
        'visto bueno de Dirección o sellos sin que todas las disciplinas hayan concluido genera diagnósticos incompletos y compromisos falsos. '
        'Por ello, la plataforma implementa un candado técnico infranqueable: el PDF oficial no se genera hasta concluir el 100% del proceso.'
    ))

    # El Tablero de Control de los 5 Pilares
    y_pil = 57.5
    pdf.set_xy(14, y_pil)
    pdf.set_font('Helvetica', 'B', 8.5)
    pdf.set_text_color(*DARK_NAVY)
    pdf.cell(w_page, 4.5, limpiar('2. El Tablero de Control y Verificación de los 5 Pilares Colegiados'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pilares = [
        ('Pilar 1: Aprendizaje Validado', 'La Maestra de Apoyo revisa competencia curricular, estilo y antecedentes escolares. Marca "Confirmar revisión de mi área".'),
        ('Pilar 2: Psicología Validada', 'El especialista revisa instrumentos intelectuales y conducta adaptativa. Confirma la validez de sus hallazgos.'),
        ('Pilar 3: Comunicación Validada', 'El especialista de lenguaje verifica componentes fonológicos y comunicativos. Marca su área como validada.'),
        ('Pilar 4: Trabajo Social Validado', 'El trabajador social confirma datos de contexto familiar, desarrollo inicial y factores socioeconómicos.'),
        ('Pilar 5: Conclusión Acordada y Vigente', 'El equipo acuerda las NEE con fórmula SEGEY y valida la Sección 7. Si alguien cambia un dato posterior, se exige revalidación.')
    ]
    y_pl = y_pil + 5.5
    for p_num, p_desc in pilares:
        pdf.set_fill_color(248, 250, 252)
        pdf.set_draw_color(*BORDER_GRAY)
        pdf.rect(14, y_pl, w_page, 8.5, 'FD', round_corners=True, corner_radius=1.5)
        pdf.set_fill_color(*(TEAL if 'Vigente' not in p_num else GOLD))
        pdf.rect(14, y_pl, 2, 8.5, 'F', round_corners=True, corner_radius=1)

        pdf.set_xy(18, y_pl + 0.8)
        pdf.set_font('Helvetica', 'B', 7.4)
        pdf.set_text_color(*DARK_NAVY)
        pdf.cell(56, 3.4, limpiar(p_num), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        pdf.set_xy(76, y_pl + 0.8)
        pdf.set_font('Helvetica', '', 6.8)
        pdf.set_text_color(*TEXT_DARK)
        pdf.multi_cell(w_page - 64, 3.4, limpiar(p_desc))
        y_pl += 9.5

    # Qué pasa antes vs después de la conclusión
    y_comp = y_pl + 2
    pdf.set_xy(14, y_comp)
    pdf.set_font('Helvetica', 'B', 8.5)
    pdf.set_text_color(*DARK_NAVY)
    pdf.cell(w_page, 4.5, limpiar('3. Comportamiento del Sistema: Borrador vs Documento Oficial'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    w_comp = (w_page - 4) / 2
    # Tarjeta izquierda: Borrador
    pdf.set_fill_color(253, 247, 246)
    pdf.set_draw_color(*TERRACOTTA)
    pdf.rect(14, y_comp + 5.5, w_comp, 36, 'FD', round_corners=True, corner_radius=2)
    pdf.set_xy(18, y_comp + 7)
    pdf.set_font('Helvetica', 'B', 7.6)
    pdf.set_text_color(*TERRACOTTA)
    pdf.cell(w_comp - 8, 3.5, limpiar('MIENTRAS FALTE ALGÚN PILAR (BORRADOR):'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_xy(18, y_comp + 11)
    pdf.set_font('Helvetica', '', 6.7)
    pdf.set_text_color(*TEXT_DARK)
    pdf.multi_cell(w_comp - 8, 3.2, limpiar(
        '• Botón Bloqueado: El botón de descarga oficial permanece inactivo rotulado como "🔒 PDF Oficial (Bloqueado)".\n'
        '• Semáforo Informativo: Un desplegable enumera los apartados pendientes por atender.\n'
        '• Sin Firmas ni Sello: Las vistas previas preliminares señalan "Borrador de trabajo en proceso" y omiten rigurosamente '
        'la firma y el sello de Dirección para evitar extravíos o usos no autorizados.'
    ))

    # Tarjeta derecha: Concluido
    x_c2 = 14 + w_comp + 4
    pdf.set_fill_color(243, 250, 247)
    pdf.set_draw_color(*TEAL)
    pdf.rect(x_c2, y_comp + 5.5, w_comp, 36, 'FD', round_corners=True, corner_radius=2)
    pdf.set_xy(x_c2 + 4, y_comp + 7)
    pdf.set_font('Helvetica', 'B', 7.6)
    pdf.set_text_color(*TEAL)
    pdf.cell(w_comp - 8, 3.5, limpiar('AL CONCLUIR AL 100% (DOCUMENTO OFICIAL):'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_xy(x_c2 + 4, y_comp + 11)
    pdf.set_font('Helvetica', '', 6.7)
    pdf.set_text_color(*TEXT_DARK)
    pdf.multi_cell(w_comp - 8, 3.2, limpiar(
        '• Botón Activo: Se habilita "⬇️ Descargar EPP oficial (firmas y sello)".\n'
        '• Membretes y Folios: Documento formal con encabezados, pies de página oficiales y paginación.\n'
        '• Tabla de Implicados: Registra nombre, función y estatus validado de cada especialista.\n'
        '• Firmas y Sello: Incluye el visto bueno del Director Escolar y el bloque formal de Dirección USAER 02-E '
        'con la firma digitalizada de Edgar Adrián Yam Briceño y el sello institucional.'
    ))

    # =========================================================================
    # PÁGINA 5: FASE 4 — DE LA EPP A LA PLANEACIÓN INDIVIDUAL EN AULA
    # =========================================================================
    pdf.add_page()
    pdf.set_y(17)
    pdf.seccion_header('FASE 4', 'De la EPP a la Planeación Individual en el Aula', 'Cero recaptura: las decisiones colegiadas se traducen directamente en actividades de aprendizaje', TEAL)

    # El Vínculo Automático
    pdf.set_xy(14, 31)
    pdf.set_font('Helvetica', 'B', 8.5)
    pdf.set_text_color(*DARK_NAVY)
    pdf.cell(w_page, 4.5, limpiar('1. Conexión Viva: La EPP Alimenta la Planeación Individual'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_fill_color(244, 250, 247)
    pdf.set_draw_color(*TEAL)
    pdf.rect(14, 36.5, w_page, 20, 'FD', round_corners=True, corner_radius=2)

    pdf.set_xy(18, 38)
    pdf.set_font('Helvetica', 'B', 7.5)
    pdf.set_text_color(*TEAL)
    pdf.cell(w_page - 8, 3.5, limpiar('EL CICLO VIRTUOSO DE LA ATENCIÓN EDUCATIVA:'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_xy(18, 42)
    pdf.set_font('Helvetica', '', 6.9)
    pdf.set_text_color(*TEXT_DARK)
    pdf.multi_cell(w_page - 8, 3.2, limpiar(
        '1. Al abrir la Planeación Individual de un alumno evaluado, el sistema consulta en tiempo real su EPP validada.\n'
        '2. En el menú desplegable de Necesidades Educativas Específicas (NEE), aparecen preseleccionadas y destacadas '
        'las necesidades acordadas en la Sección 7 del informe psicopedagógico.\n'
        '3. La Maestra de Apoyo no tiene que volver a teclear el diagnóstico ni inventar acuerdos paralelos: '
        'la planeación parte con fidelidad absoluta del expediente oficial.'
    ))

    # Herramientas del Módulo Planeación
    y_hp = 59
    pdf.set_xy(14, y_hp)
    pdf.set_font('Helvetica', 'B', 8.5)
    pdf.set_text_color(*DARK_NAVY)
    pdf.cell(w_page, 4.5, limpiar('2. Herramientas Integradas en la Planeación Individual'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    w_plan = (w_page - 4) / 2
    tools_plan = [
        ('Diseño Universal para el Aprendizaje (DUA)', TEAL,
         'La plataforma propone formas diversificadas de representación, acción, expresión y compromiso '
         'alineadas al Campo Formativo y a los Procesos de Desarrollo de Aprendizaje (PDA) del grado escolar.'),
        ('Asistente Pedagógico para Casos Singulares', DARK_CYAN,
         'Si un alumno presenta retos complejos o no hay suficiente evidencia curricular previa, el asistente de consulta '
         'interactiva permite describir la situación en lenguaje natural para obtener ajustes razonables inmediatos.'),
        ('Modo Hoja de Papel en Vivo', NAVY,
         'Permite redactar directamente sobre el formato visual del anexo oficial de planeación, combinando la familiaridad '
         'del diseño impreso con autocompletados y guardado en tiempo real sin recargas de página.'),
        ('Entrega y Archivo Electrónico Directo', GOLD,
         'Al finalizar, la planeación se entrega digitalmente para revisión directiva en 1 clic y se archiva automáticamente '
         'en el expediente histórico del alumno con su respectiva hoja de firmas oficiales.')
    ]
    for i, (t_tit, t_col, t_desc) in enumerate(tools_plan):
        x_p = 14 + ((i % 2) * (w_plan + 4))
        y_p = y_hp + 5.5 + ((i // 2) * 23.5)
        pdf.set_fill_color(248, 250, 252)
        pdf.set_draw_color(*BORDER_GRAY)
        pdf.rect(x_p, y_p, w_plan, 21.5, 'FD', round_corners=True, corner_radius=2)
        pdf.set_fill_color(*t_col)
        pdf.rect(x_p, y_p, 2.5, 21.5, 'F', round_corners=True, corner_radius=1)

        pdf.set_xy(x_p + 5, y_p + 1.2)
        pdf.set_font('Helvetica', 'B', 7.5)
        pdf.set_text_color(*t_col)
        pdf.cell(w_plan - 8, 3.6, limpiar(t_tit), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        pdf.set_xy(x_p + 5, y_p + 5.5)
        pdf.set_font('Helvetica', '', 6.7)
        pdf.set_text_color(*TEXT_DARK)
        pdf.multi_cell(w_plan - 8, 3.2, limpiar(t_desc))

    # Reglas de Oro del Equipo USAER 02-E
    y_ro = y_hp + 54
    pdf.set_xy(14, y_ro)
    pdf.set_font('Helvetica', 'B', 8.5)
    pdf.set_text_color(*DARK_NAVY)
    pdf.cell(w_page, 4.5, limpiar('3. Decálogo Operativo USAER 02-E: Calidad y Rigor Pedagógico'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_fill_color(244, 246, 250)
    pdf.set_draw_color(*NAVY)
    pdf.rect(14, y_ro + 5.5, w_page, 29, 'FD', round_corners=True, corner_radius=2)

    col_ro_w = (w_page - 8) / 2
    pdf.set_xy(18, y_ro + 7)
    pdf.set_font('Helvetica', 'B', 7.2)
    pdf.set_text_color(*NAVY)
    pdf.cell(col_ro_w, 3.5, limpiar('PRÁCTICAS INDISPENSABLES:'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_xy(18, y_ro + 11)
    pdf.set_font('Helvetica', '', 6.6)
    pdf.set_text_color(*TEXT_DARK)
    pdf.multi_cell(col_ro_w, 3.2, limpiar(
        '1. Capturar una vez y reutilizar siempre.\n'
        '2. Usar el escaneador para agilizar expedientes en papel.\n'
        '3. Formular NEE con: Necesita + verbo observable + contenido.\n'
        '4. Validar tu área apenas termines la revisión de hallazgos.\n'
        '5. Participar en la conclusión colegiada antes de emitir el informe.'
    ))

    pdf.set_xy(18 + col_ro_w + 4, y_ro + 7)
    pdf.set_font('Helvetica', 'B', 7.2)
    pdf.set_text_color(*TERRACOTTA)
    pdf.cell(col_ro_w, 3.5, limpiar('LO QUE DEBEMOS EVITAR:'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_xy(18 + col_ro_w + 4, y_ro + 11)
    pdf.set_font('Helvetica', '', 6.6)
    pdf.set_text_color(*TEXT_DARK)
    pdf.multi_cell(col_ro_w, 3.2, limpiar(
        '1. No generar ni circular borradores con firmas o sellos.\n'
        '2. No duplicar captura de datos que ya existen en el padrón.\n'
        '3. No modificar áreas sin avisar al equipo interdisciplinario.\n'
        '4. No redactar NEE vagas como "mejorar en lectura".\n'
        '5. No planear en aula al margen de la EPP oficial del alumno.'
    ))

    # Guardar en rutas del proyecto, Escritorio y Artifacts
    ruta_docs = Path(__file__).resolve().parents[1] / 'docs' / 'Guia_Paso_a_Paso_EPP_y_Planeacion_USAER_02E.pdf'
    ruta_docs.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(ruta_docs))

    ruta_desktop = Path(r'C:\Users\edgar\OneDrive\Escritorio\Guia_Paso_a_Paso_EPP_y_Planeacion_USAER_02E.pdf')
    try:
        pdf.output(str(ruta_desktop))
    except Exception:
        pass

    ruta_brain = Path(r'C:\Users\edgar\.gemini\antigravity-ide\brain\880375fd-87ab-4715-ae31-eb06455b86f3\Guia_Paso_a_Paso_EPP_y_Planeacion_USAER_02E.pdf')
    try:
        pdf.output(str(ruta_brain))
    except Exception:
        pass

    print(f'Guía Paso a Paso generada exitosamente en:\n1. {ruta_docs}\n2. {ruta_desktop}\n3. {ruta_brain}')
    return ruta_docs


if __name__ == '__main__':
    generar_pdf_guia()

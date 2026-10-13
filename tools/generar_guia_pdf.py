"""Generador de la Guia Rapida de Planeacion Visual para el Personal de USAER 02-E.
Diseno altamente visual, ejecutivo, paso a paso, con tarjetas, flujos e insignias.
"""
from pathlib import Path
from fpdf import FPDF
from fpdf.enums import XPos, YPos

# Paleta institucional USAER 02-E
NAVY = (27, 73, 88)         # #1B4958
DARK_NAVY = (18, 51, 62)    # #12333E
GOLD = (196, 147, 57)       # #C49339
AMBER = (212, 137, 26)      # #D4891A
TEAL = (27, 126, 103)       # #1B7E67
DARK_CYAN = (42, 100, 120)  # #2A6478
TERRACOTTA = (184, 74, 57)  # #B84A39
SLATE = (93, 114, 123)      # #5D727B
LIGHT_SLATE = (140, 160, 170)
WHITE = (255, 255, 255)
TEXT_DARK = (30, 45, 50)
BORDER_GRAY = (218, 228, 232)


def limpiar(texto):
    if not isinstance(texto, str):
        return texto
    return (texto.replace('\u201c', '"')
                 .replace('\u201d', '"')
                 .replace('\u2018', "'")
                 .replace('\u2019', "'")
                 .replace('\u2014', '-')
                 .replace('\u2013', '-')
                 .replace('\u2022', chr(149))
                 .replace('\u2026', '...')
                 .replace('\u2192', '->')
                 .replace('\u2794', '->')
                 .replace('\u25ba', '>')
                 .replace('\u2010', '-'))


class GuiaVisualPDF(FPDF):
    def __init__(self):
        super().__init__(orientation='P', unit='mm', format='Letter')
        self.set_auto_page_break(auto=False)
        self.set_margins(14, 14, 14)

    def header(self):
        # Banner superior institucional
        self.set_fill_color(*NAVY)
        self.rect(0, 0, 216, 15, 'F')
        self.set_fill_color(*GOLD)
        self.rect(0, 15, 216, 1.8, 'F')

        self.set_xy(14, 3.5)
        self.set_font('Helvetica', 'B', 9.5)
        self.set_text_color(*WHITE)
        self.cell(100, 8, limpiar('USAER 02-E  |  ZONA 001 EDUCACIÓN ESPECIAL'), align='L')
        self.set_xy(102, 3.5)
        self.set_font('Helvetica', '', 8.5)
        self.cell(100, 8, limpiar('SISTEMA INTEGRADO DE PLANEACIÓN PEDAGÓGICA'), align='R')

    def footer(self):
        self.set_y(-11)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(*LIGHT_SLATE)
        self.cell(0, 6, f'USAER 02-E · Plataforma Educativa Integrada · Página {self.page_no()}', align='C')

    def draw_badge(self, x, y, text, bg, fg, font_size=7.2, pad_x=2.5, pad_y=0.8):
        self.set_font('Helvetica', 'B', font_size)
        w = self.get_string_width(limpiar(text)) + (pad_x * 2)
        h = font_size * 0.35 + (pad_y * 2) + 1.2
        self.set_fill_color(*bg)
        self.rect(x, y, w, h, 'F', round_corners=True, corner_radius=1.5)
        self.set_text_color(*fg)
        self.set_xy(x, y + pad_y - 0.2)
        self.cell(w, h - pad_y, limpiar(text), align='C')
        return w, h


def generar():
    pdf = GuiaVisualPDF()
    w_page = 188 # 216 - 28

    # =========================================================================
    # PÁGINA 1: FLUJO EN 3 PASOS + RED DE SEGURIDAD
    # =========================================================================
    pdf.add_page()
    
    # Titular y Subtítulo
    pdf.set_xy(14, 19)
    pdf.set_font('Helvetica', 'B', 15)
    pdf.set_text_color(*DARK_NAVY)
    pdf.cell(w_page, 6.5, limpiar('Guía Rápida de Planeación Ágil'), align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.set_font('Helvetica', '', 8.5)
    pdf.set_text_color(*SLATE)
    pdf.cell(w_page, 4.5, limpiar('Objetivo: Diseñar planeaciones útiles, conectadas y sin burocracia en minutos.'), align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(1.5)

    # Banner Principio Rector Destacado
    y_principio = pdf.get_y()
    pdf.set_fill_color(238, 245, 248)
    pdf.set_draw_color(*NAVY)
    pdf.rect(14, y_principio, w_page, 10.5, 'FD', round_corners=True, corner_radius=2)
    # Franja dorada izquierda
    pdf.set_fill_color(*GOLD)
    pdf.rect(14, y_principio, 2.5, 10.5, 'F', round_corners=True, corner_radius=1)
    
    pdf.set_xy(18.5, y_principio + 1.2)
    pdf.set_font('Helvetica', 'B', 8.5)
    pdf.set_text_color(*NAVY)
    pdf.cell(w_page - 8, 4, limpiar('PRINCIPIO CLAVE: "CAPTURAR UNA VEZ, REUTILIZAR DESPUÉS"'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_xy(18.5, y_principio + 5.2)
    pdf.set_font('Helvetica', '', 7.8)
    pdf.set_text_color(*TEXT_DARK)
    pdf.cell(w_page - 8, 4, limpiar('La plataforma ya conoce expedientes, antecedentes y anexos de tus alumnos. No vuelvas a capturar lo que la USAER ya sabe.'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Barra visual de Flujo (Timeline en 3 pasos)
    y_flow = y_principio + 13.5
    pdf.set_xy(14, y_flow)
    col_w = (w_page - 8) / 3
    
    pasos_nav = [
        ('1. ¿A quién planeo?', 'Selección y Matrícula', NAVY, (235, 244, 248)),
        ('2. Antecedentes e IA', 'Conexión y Propuesta', GOLD, (254, 250, 242)),
        ('3. Mi Formato y Entrega', 'Edición y Envío Directo', TEAL, (238, 248, 244))
    ]
    for i, (p_tit, p_sub, color_acc, bg_pill) in enumerate(pasos_nav):
        x_pill = 14 + (i * (col_w + 4))
        pdf.set_fill_color(*bg_pill)
        pdf.set_draw_color(*color_acc)
        pdf.set_line_width(0.35)
        pdf.rect(x_pill, y_flow, col_w, 9.5, 'FD', round_corners=True, corner_radius=2)
        
        # Bolita con número
        pdf.set_fill_color(*color_acc)
        pdf.rect(x_pill + 2, y_flow + 1.8, 6, 6, 'F', round_corners=True, corner_radius=1.2)
        pdf.set_font('Helvetica', 'B', 7.5)
        pdf.set_text_color(*WHITE)
        pdf.set_xy(x_pill + 2, y_flow + 2.2)
        pdf.cell(6, 5, str(i + 1), align='C')
        
        # Texto
        pdf.set_xy(x_pill + 9.5, y_flow + 1)
        pdf.set_font('Helvetica', 'B', 7.8)
        pdf.set_text_color(*color_acc)
        pdf.cell(col_w - 11, 4, limpiar(p_tit), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_xy(x_pill + 9.5, y_flow + 5)
        pdf.set_font('Helvetica', '', 6.8)
        pdf.set_text_color(*SLATE)
        pdf.cell(col_w - 11, 3.5, limpiar(p_sub), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # -------------------------------------------------------------------------
    # TARJETA PASO 1
    # -------------------------------------------------------------------------
    y_p1 = y_flow + 12.5
    h_p1 = 37
    pdf.set_fill_color(252, 253, 254)
    pdf.set_draw_color(*BORDER_GRAY)
    pdf.set_line_width(0.3)
    pdf.rect(14, y_p1, w_page, h_p1, 'FD', round_corners=True, corner_radius=2.5)
    pdf.set_fill_color(*NAVY)
    pdf.rect(14, y_p1, 2.5, h_p1, 'F', round_corners=True, corner_radius=1)

    # Encabezado Paso 1
    pdf.set_xy(19, y_p1 + 2)
    pdf.set_font('Helvetica', 'B', 9.5)
    pdf.set_text_color(*DARK_NAVY)
    pdf.cell(65, 5, limpiar('PASO 1: ¿A quién planeo?'), align='L')
    pdf.draw_badge(85, y_p1 + 2.2, 'Tiempo estimado: 30 seg', NAVY, WHITE, font_size=6.8)
    pdf.draw_badge(148, y_p1 + 2.2, 'Modalidad Automática', (230, 240, 245), NAVY, font_size=6.8)

    # Sub-bloques Paso 1
    w_sub = (w_page - 12) / 2
    
    # Bloque A: Continuar borrador
    x_sub1 = 19
    y_sub1 = y_p1 + 8.5
    pdf.set_fill_color(244, 248, 250)
    pdf.set_draw_color(200, 218, 226)
    pdf.rect(x_sub1, y_sub1, w_sub, 25.5, 'FD', round_corners=True, corner_radius=2)
    pdf.set_xy(x_sub1 + 3, y_sub1 + 1.8)
    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_text_color(*NAVY)
    pdf.cell(w_sub - 6, 4, limpiar('A. Continuar donde me quedé (Borrador activo)'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font('Helvetica', '', 7.5)
    pdf.set_text_color(*TEXT_DARK)
    pdf.set_x(x_sub1 + 3)
    pdf.multi_cell(w_sub - 6, 3.8, limpiar(
        '• Si ya tienes una planeación en proceso, búscala en tu lista de borradores.\n'
        '• Pulsa el botón [ Continuar ] para abrirla inmediatamente con todos tus avances resguardados.'
    ))

    # Bloque B: Nueva planeación
    x_sub2 = x_sub1 + w_sub + 4
    pdf.set_fill_color(244, 248, 250)
    pdf.set_draw_color(200, 218, 226)
    pdf.rect(x_sub2, y_sub1, w_sub, 25.5, 'FD', round_corners=True, corner_radius=2)
    pdf.set_xy(x_sub2 + 3, y_sub1 + 1.8)
    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_text_color(*NAVY)
    pdf.cell(w_sub - 6, 4, limpiar('B. Nueva planeación (Desde matrícula)'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font('Helvetica', '', 7.5)
    pdf.set_text_color(*TEXT_DARK)
    pdf.set_x(x_sub2 + 3)
    pdf.multi_cell(w_sub - 6, 3.8, limpiar(
        '• Elige tu escuela asignada y selecciona tus alumnos.\n'
        '• El ciclo y trimestre se sugieren en automático por calendario.\n'
        '• Pulsa [ Crear mi borrador ] para reunir la información del equipo.'
    ))

    # -------------------------------------------------------------------------
    # TARJETA PASO 2: CONEXIÓN AUTOMÁTICA Y PROPUESTA IA
    # -------------------------------------------------------------------------
    y_p2 = y_p1 + h_p1 + 3
    h_p2 = 63
    pdf.set_fill_color(252, 253, 254)
    pdf.set_draw_color(*BORDER_GRAY)
    pdf.set_line_width(0.3)
    pdf.rect(14, y_p2, w_page, h_p2, 'FD', round_corners=True, corner_radius=2.5)
    pdf.set_fill_color(*GOLD)
    pdf.rect(14, y_p2, 2.5, h_p2, 'F', round_corners=True, corner_radius=1)

    # Encabezado Paso 2
    pdf.set_xy(19, y_p2 + 2)
    pdf.set_font('Helvetica', 'B', 9.5)
    pdf.set_text_color(*DARK_NAVY)
    pdf.cell(85, 5, limpiar('PASO 2: Preparar con IA y Conexión Automática'), align='L')
    pdf.draw_badge(105, y_p2 + 2.2, 'Tiempo estimado: 2 a 3 min', GOLD, WHITE, font_size=6.8)
    pdf.draw_badge(150, y_p2 + 2.2, 'Cero Captura Repetida', (254, 250, 240), GOLD, font_size=6.8)

    # 3 Columnas visuales Paso 2
    w_p2_col = (w_page - 14) / 3
    y_col2 = y_p2 + 8.5
    h_col2 = 51.5

    # Col 1: Antecedentes automáticos
    x_c1 = 19
    pdf.set_fill_color(254, 251, 245)
    pdf.set_draw_color(230, 205, 155)
    pdf.rect(x_c1, y_col2, w_p2_col, h_col2, 'FD', round_corners=True, corner_radius=2)
    pdf.set_xy(x_c1 + 2.5, y_col2 + 2)
    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_text_color(*GOLD)
    pdf.cell(w_p2_col - 5, 4, limpiar('1. Antecedentes del Expediente'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font('Helvetica', '', 7.3)
    pdf.set_text_color(*TEXT_DARK)
    pdf.set_x(x_c1 + 2.5)
    pdf.multi_cell(w_p2_col - 5, 3.6, limpiar(
        '• La plataforma lee Anexos III, IV, V, visitas y acuerdos vigentes.\n\n'
        '• Si un antecedente te sirve, pulsa:\n'
        '  [ + Usar en borrador ]\n\n'
        '• Se transfiere directamente a tu formato oficial como necesidad o barrera sin copiar ni pegar.'
    ))

    # Col 2: Referentes oficiales y PDA
    x_c2 = x_c1 + w_p2_col + 3
    pdf.set_fill_color(254, 251, 245)
    pdf.set_draw_color(230, 205, 155)
    pdf.rect(x_c2, y_col2, w_p2_col, h_col2, 'FD', round_corners=True, corner_radius=2)
    pdf.set_xy(x_c2 + 2.5, y_col2 + 2)
    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_text_color(*GOLD)
    pdf.cell(w_p2_col - 5, 4, limpiar('2. Referentes Oficiales y PDA'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font('Helvetica', '', 7.3)
    pdf.set_text_color(*TEXT_DARK)
    pdf.set_x(x_c2 + 2.5)
    pdf.multi_cell(w_p2_col - 5, 3.6, limpiar(
        '• Para Maestra de Apoyo: activa el selector oficial de la SEP.\n\n'
        '• Elige Campo Formativo y busca contenidos por palabra clave.\n\n'
        '• Adapta el PDA al contexto real de tu aula y presiona [ Incorporar referentes ] para vincularlos al borrador.'
    ))

    # Col 3: Propuesta con IA en 3 momentos
    x_c3 = x_c2 + w_p2_col + 3
    pdf.set_fill_color(254, 251, 245)
    pdf.set_draw_color(230, 205, 155)
    pdf.rect(x_c3, y_col2, w_p2_col, h_col2, 'FD', round_corners=True, corner_radius=2)
    pdf.set_xy(x_c3 + 2.5, y_col2 + 2)
    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_text_color(*GOLD)
    pdf.cell(w_p2_col - 5, 4, limpiar('3. Propuesta con IA en 3 Momentos'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font('Helvetica', '', 7.3)
    pdf.set_text_color(*TEXT_DARK)
    pdf.set_x(x_c3 + 2.5)
    pdf.multi_cell(w_p2_col - 5, 3.6, limpiar(
        '• Marca la casilla de revisión y pulsa [ Proponer actividades con IA ].\n\n'
        '• Secuencia concreta para educación especial:\n'
        '  - Inicio: Tangible / manipulable.\n'
        '  - Desarrollo: Andamiaje y apoyos.\n'
        '  - Cierre: Evaluación observable.\n\n'
        '• Pulsa [ Continuar a mi formato ] para pasar al editor final.'
    ))

    # -------------------------------------------------------------------------
    # TARJETA PASO 3: MI FORMATO Y ENTREGA
    # -------------------------------------------------------------------------
    y_p3 = y_p2 + h_p2 + 3
    h_p3 = 45
    pdf.set_fill_color(252, 253, 254)
    pdf.set_draw_color(*BORDER_GRAY)
    pdf.set_line_width(0.3)
    pdf.rect(14, y_p3, w_page, h_p3, 'FD', round_corners=True, corner_radius=2.5)
    pdf.set_fill_color(*TEAL)
    pdf.rect(14, y_p3, 2.5, h_p3, 'F', round_corners=True, corner_radius=1)

    # Encabezado Paso 3
    pdf.set_xy(19, y_p3 + 2)
    pdf.set_font('Helvetica', 'B', 9.5)
    pdf.set_text_color(*DARK_NAVY)
    pdf.cell(58, 5, limpiar('PASO 3: Mi Formato y Entrega'), align='L')
    pdf.draw_badge(79, y_p3 + 2.2, 'Control Total Docente', TEAL, WHITE, font_size=6.8)
    pdf.draw_badge(117, y_p3 + 2.2, 'Edición Directa', (235, 248, 244), TEAL, font_size=6.8)
    pdf.draw_badge(148, y_p3 + 2.2, 'Entrega sin Intermediarios', (235, 248, 244), TEAL, font_size=6.8)

    # 4 Acciones de la barra pegajosa inferior
    y_p3_acc = y_p3 + 8
    acciones = [
        ('1. [ Guardar borrador ]', 'Autoguardado en segundo plano cada 15 segundos + guardado confirmado en 1 clic. Conserva cada cambio.'),
        ('2. [ Ver PDF ]', 'Genera al instante la vista previa oficial para revisar presentación, descargar o imprimir cuando lo requieras.'),
        ('3. [ Enviar a Dirección ]', 'Entrega digital directa en 1 clic. La dirección recibe el formato de inmediato para revisión formativa, sin papeleo.'),
        ('4. [ Respaldo .json ]', 'Descarga tu respaldo editable local en 1 clic. Tu trabajo está siempre en tu poder y protegido ante cortes.')
    ]
    w_acc = (w_page - 14) / 4
    for i, (tit_a, desc_a) in enumerate(acciones):
        x_a = 19 + (i * (w_acc + 2))
        pdf.set_fill_color(240, 248, 245)
        pdf.set_draw_color(190, 225, 215)
        pdf.rect(x_a, y_p3_acc, w_acc, 34, 'FD', round_corners=True, corner_radius=2)
        pdf.set_xy(x_a + 2, y_p3_acc + 2)
        pdf.set_font('Helvetica', 'B', 7.5)
        pdf.set_text_color(*TEAL)
        pdf.cell(w_acc - 4, 4, limpiar(tit_a), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font('Helvetica', '', 7.1)
        pdf.set_text_color(*TEXT_DARK)
        pdf.set_x(x_a + 2)
        pdf.multi_cell(w_acc - 4, 3.5, limpiar(desc_a))

    # -------------------------------------------------------------------------
    # RED DE SEGURIDAD (Al pie de página)
    # -------------------------------------------------------------------------
    y_sec = y_p3 + h_p3 + 3
    h_sec = 23
    pdf.set_fill_color(238, 245, 248)
    pdf.set_draw_color(*NAVY)
    pdf.set_line_width(0.35)
    pdf.rect(14, y_sec, w_page, h_sec, 'FD', round_corners=True, corner_radius=2)
    pdf.set_fill_color(*NAVY)
    pdf.rect(14, y_sec, 2.5, h_sec, 'F', round_corners=True, corner_radius=1)

    pdf.set_xy(19, y_sec + 2)
    pdf.set_font('Helvetica', 'B', 8.5)
    pdf.set_text_color(*NAVY)
    pdf.cell(w_page - 10, 4, limpiar('RED DE SEGURIDAD: CERO PÉRDIDAS ANTE CORTES DE LUZ O WI-FI'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    w_sec_item = (w_page - 14) / 3
    seg_items = [
        ('Respaldo en 1 Clic (.json)', 'Pulsa [ Descargar respaldo editable ] al pie de la página para guardar tu archivo localmente.'),
        ('Restauración Inmediata', 'Si se apaga la laptop o se va la luz: al volver a entrar, abre [ Continuar donde me quedé ] o restaura tu archivo .json.'),
        ('Historial Protegido', 'Ningún borrador previo se borra. La plataforma conserva tus versiones de forma segura en la nube.')
    ]
    for i, (tit_s, desc_s) in enumerate(seg_items):
        x_s = 19 + (i * (w_sec_item + 2.5))
        pdf.set_xy(x_s, y_sec + 6.8)
        pdf.set_font('Helvetica', 'B', 7.5)
        pdf.set_text_color(*DARK_NAVY)
        pdf.cell(w_sec_item, 3.8, limpiar('• ' + tit_s), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font('Helvetica', '', 6.8)
        pdf.set_text_color(*SLATE)
        pdf.set_x(x_s + 2)
        pdf.multi_cell(w_sec_item - 2, 3.3, limpiar(desc_s))

    # =========================================================================
    # PÁGINA 2: RUTA ESPECÍFICA SEGÚN TU FUNCIÓN
    # =========================================================================
    pdf.add_page()

    # Titular Página 2
    pdf.set_xy(14, 19)
    pdf.set_font('Helvetica', 'B', 15)
    pdf.set_text_color(*DARK_NAVY)
    pdf.cell(w_page, 6.5, limpiar('Tu Ruta Específica según tu Función'), align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font('Helvetica', '', 8.5)
    pdf.set_text_color(*SLATE)
    pdf.cell(w_page, 4.5, limpiar('Cada integrante del equipo aporta a la misma historia educativa desde su especialidad.'), align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(1.5)

    # Tarjetas por Función
    y_card = 31.5
    h_card = 43.5

    roles = [
        {
            'num': '1',
            'titulo': 'MAESTRAS DE APOYO (Aprendizaje)',
            'subtitulo': 'Coordina el Plan de Intervención (XXI) y la Planeación Trimestral de aula (XXIII)',
            'color': NAVY,
            'bg': (246, 250, 252),
            'tag': 'Coordinación Pedagógica',
            'bullets': [
                ('Atención individual (XXI)', 'Selecciona al alumno con IEPP para crear el Plan de Intervención (anual o multianual). Los especialistas aportan sus estrategias desde la pestaña de Trabajo Colaborativo.'),
                ('Atención grupal (XXIII)', 'Selecciona a los alumnos del grupo para su planeación trimestral. Si incluyes a un alumno con atención individual en una sesión grupal, marca la casilla correspondiente.'),
                ('Dosificación ágil', 'Diseña secuencias de aula con Inicio (manipulable), Desarrollo (andamiaje) y Cierre (evaluación observable). Prioriza acciones pedagógicas reales.')
            ]
        },
        {
            'num': '2',
            'titulo': 'PSICOLOGÍA',
            'subtitulo': 'Planeación trimestral (XXIII) y aportaciones socioemocionales al Plan Individual',
            'color': DARK_CYAN,
            'bg': (244, 250, 252),
            'tag': 'Área Socioemocional',
            'bullets': [
                ('5 Competencias de Zona 001', 'Selecciona entre Autoconciencia, Autorregulación, Conciencia social, Relaciones interpersonales y Toma de decisiones responsables.'),
                ('Sesiones por subgrupos', 'Registra fecha, contexto de intervención (aula regular o aula de apoyo) y apoyos específicos.'),
                ('Aporte al Plan de Intervención', 'En la pestaña "Trabajo colaborativo", redacta tus sugerencias emocionales y conductuales para el Plan XXI con tu firma profesional.')
            ]
        },
        {
            'num': '3',
            'titulo': 'COMUNICACIÓN',
            'subtitulo': 'Planeación trimestral (XXIII) con énfasis en SAAC, lenguaje y participación activa',
            'color': GOLD,
            'bg': (254, 251, 245),
            'tag': 'Comunicación y Lenguaje',
            'bullets': [
                ('Canal comunicativo', 'Define si la intervención es oral, con Sistemas Aumentativos y Alternativos de Comunicación (SAAC), apoyos pictográficos o lectoescritura adaptada.'),
                ('Enfoque en el aula regular', 'Prioriza actividades que permitan al alumno comunicarse eficazmente con sus compañeros de grupo y docentes.'),
                ('Aporte al Plan de Intervención', 'Incorpora en "Trabajo colaborativo" recomendaciones de comunicación para que la maestra aplique en el día a día.')
            ]
        },
        {
            'num': '4',
            'titulo': 'TRABAJO SOCIAL',
            'subtitulo': 'Planeación (XXV) de barreras de contexto, apoyos sociofamiliares y redes',
            'color': TERRACOTTA,
            'bg': (254, 248, 247),
            'tag': 'Contexto y Redes',
            'bullets': [
                ('Formato XXV', 'Identifica las BAP en los contextos familiar, escolar y comunitario, estableciendo compromisos claros de corresponsabilidad.'),
                ('Visitas y acuerdos', 'Reutiliza antecedentes de visitas domiciliarias o acuerdos escolares previos sin volver a capturarlos.'),
                ('Aporte al Plan de Intervención', 'Vincula apoyos sociofamiliares, becas, canalizaciones externas y seguimiento de compromisos al Plan XXI.')
            ]
        },
        {
            'num': '5',
            'titulo': 'DIRECCIÓN (Acompañamiento Formativo)',
            'subtitulo': 'Monitoreo en tiempo real, retroalimentación formativa y validación ágil',
            'color': DARK_NAVY,
            'bg': (246, 248, 250),
            'tag': 'Supervisión sin Burocracia',
            'bullets': [
                ('Pestaña "Revisión directiva"', 'Consulta entregas en tiempo real organizadas por escuela y docente, sin intermediación técnica manual.'),
                ('Retroalimentación con criterio', 'Revisa planeaciones y emite observaciones constructivas respetando la autonomía profesional docente.'),
                ('Validación en 1 clic', 'Devuelve con observaciones o valida el documento para autorizar su archivo digital definitivo.')
            ]
        }
    ]

    for role in roles:
        pdf.set_fill_color(*role['bg'])
        pdf.set_draw_color(*BORDER_GRAY)
        pdf.set_line_width(0.3)
        pdf.rect(14, y_card, w_page, h_card, 'FD', round_corners=True, corner_radius=2.5)
        
        # Borde lateral de color
        pdf.set_fill_color(*role['color'])
        pdf.rect(14, y_card, 2.5, h_card, 'F', round_corners=True, corner_radius=1)

        # Encabezado
        pdf.set_xy(19, y_card + 2)
        pdf.set_font('Helvetica', 'B', 9)
        pdf.set_text_color(*role['color'])
        pdf.cell(100, 4.5, limpiar(role['num'] + '. ' + role['titulo']), new_x=XPos.RIGHT, new_y=YPos.TOP)
        
        # Badge de área a la derecha
        pdf.draw_badge(135, y_card + 2.2, role['tag'], role['color'], WHITE, font_size=6.8)

        # Subtítulo
        pdf.set_xy(19, y_card + 6.8)
        pdf.set_font('Helvetica', 'I', 7.5)
        pdf.set_text_color(*SLATE)
        pdf.cell(w_page - 10, 3.8, limpiar(role['subtitulo']), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # Bullets
        y_b = y_card + 11.2
        for b_tit, b_desc in role['bullets']:
            pdf.set_xy(19, y_b)
            pdf.set_font('Helvetica', 'B', 7.5)
            pdf.set_text_color(*TEXT_DARK)
            tit_str = limpiar('• ' + b_tit + ': ')
            w_tit = pdf.get_string_width(tit_str)
            pdf.cell(w_tit, 3.6, tit_str, new_x=XPos.RIGHT, new_y=YPos.TOP)
            
            pdf.set_font('Helvetica', '', 7.3)
            pdf.multi_cell(w_page - 10 - w_tit, 3.6, limpiar(b_desc))
            y_b = pdf.get_y() + 0.8

        y_card += h_card + 2.2

    # Guardar en archivo del proyecto y en el Escritorio
    ruta_docs = Path(__file__).resolve().parents[1] / 'docs' / 'Guia_Rapida_Planeacion_USAER_02E.pdf'
    ruta_docs.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(ruta_docs))

    # También actualizar copia en el Escritorio de Edgar
    ruta_desktop = Path(r'C:\Users\edgar\OneDrive\Escritorio\Guia_Rapida_Planeacion_USAER_02E.pdf')
    try:
        pdf.output(str(ruta_desktop))
    except Exception:
        pass

    # Y copiar a la carpeta brain artifacts
    ruta_brain = Path(r'C:\Users\edgar\.gemini\antigravity-ide\brain\880375fd-87ab-4715-ae31-eb06455b86f3\Guia_Rapida_Planeacion_USAER_02E.pdf')
    try:
        pdf.output(str(ruta_brain))
    except Exception:
        pass

    print(f'Guia visual generada exitosamente en:\n1. {ruta_docs}\n2. {ruta_desktop}\n3. {ruta_brain}')
    return ruta_docs


if __name__ == '__main__':
    generar()

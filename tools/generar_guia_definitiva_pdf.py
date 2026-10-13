"""Generador de la Guia Definitiva de Planeacion Pedagogica USAER 02-E.
Documento exhaustivo, abarcativo y altamente visual de 6 paginas.
Cubre absolutamente todas las funciones, herramientas, opciones, roles y seguridad.
"""
from pathlib import Path
from fpdf import FPDF
from fpdf.enums import XPos, YPos

# Paleta institucional USAER 02-E
NAVY = (27, 73, 88)         # #1B4958 - Primario
DARK_NAVY = (18, 51, 62)    # #12333E - Titulares oscuros
GOLD = (196, 147, 57)       # #C49339 - Acento dorado
AMBER = (212, 137, 26)      # #D4891A - Acento calido
TEAL = (27, 126, 103)       # #1B7E67 - Acciones y aprobacion
DARK_CYAN = (42, 100, 120)  # #2A6478 - Psicologia
TERRACOTTA = (184, 74, 57)  # #B84A39 - Trabajo Social
SLATE = (93, 114, 123)      # #5D727B - Subtitulos
LIGHT_SLATE = (140, 160, 170)
WHITE = (255, 255, 255)
TEXT_DARK = (30, 45, 50)
BORDER_GRAY = (218, 228, 232)
CARD_BG = (249, 251, 252)


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


class GuiaDefinitivaPDF(FPDF):
    def __init__(self):
        super().__init__(orientation='P', unit='mm', format='Letter')
        self.set_auto_page_break(auto=False)
        self.set_margins(14, 14, 14)

    def header(self):
        # Banner institucional superior
        self.set_fill_color(*NAVY)
        self.rect(0, 0, 216, 14, 'F')
        self.set_fill_color(*GOLD)
        self.rect(0, 14, 216, 1.8, 'F')

        self.set_xy(14, 3)
        self.set_font('Helvetica', 'B', 9)
        self.set_text_color(*WHITE)
        self.cell(100, 8, limpiar('USAER 02-E  |  ZONA 001 EDUCACIÓN ESPECIAL'), align='L')
        self.set_xy(102, 3)
        self.set_font('Helvetica', '', 8)
        self.cell(100, 8, limpiar('MANUAL INTEGRAL DE PLANEACIÓN PEDAGÓGICA'), align='R')

    def footer(self):
        self.set_y(-10.5)
        self.set_font('Helvetica', 'I', 7.8)
        self.set_text_color(*LIGHT_SLATE)
        self.cell(0, 6, f'USAER 02-E · Sistema Integrado de Planeación Pedagógica · Página {self.page_no()} de 6', align='C')

    def draw_badge(self, x, y, text, bg, fg, font_size=7, pad_x=2.2, pad_y=0.7):
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
        self.rect(14, y, 188, 11, 'FD', round_corners=True, corner_radius=2)
        self.set_fill_color(*color_acc)
        self.rect(14, y, 2.5, 11, 'F', round_corners=True, corner_radius=1)

        self.set_xy(18.5, y + 1.2)
        self.set_font('Helvetica', 'B', 9.5)
        self.set_text_color(*DARK_NAVY)
        self.cell(120, 4.5, limpiar(f'{num}. {titulo}'), align='L')

        self.set_xy(18.5, y + 5.8)
        self.set_font('Helvetica', 'I', 7.5)
        self.set_text_color(*SLATE)
        self.cell(180, 4, limpiar(subtitulo), align='L')
        self.set_y(y + 13)


def generar():
    pdf = GuiaDefinitivaPDF()
    w_page = 188 # 216 - 28

    # =========================================================================
    # PÁGINA 1: ARQUITECTURA, FILOSOFÍA Y RECORRIDO EN 3 PASOS
    # =========================================================================
    pdf.add_page()

    # Portada ejecutiva compacta
    pdf.set_xy(14, 18)
    pdf.set_font('Helvetica', 'B', 15)
    pdf.set_text_color(*DARK_NAVY)
    pdf.cell(w_page, 6.5, limpiar('Guía Definitiva de Planeación Pedagógica'), align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font('Helvetica', '', 8.5)
    pdf.set_text_color(*SLATE)
    pdf.cell(w_page, 4.5, limpiar('Manual Operativo Completo: Funciones, Herramientas, Conectividad y Rutas por Especialidad'), align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(1.5)

    # Banner Principio Rector
    y_prin = pdf.get_y()
    pdf.set_fill_color(238, 245, 248)
    pdf.set_draw_color(*NAVY)
    pdf.rect(14, y_prin, w_page, 12, 'FD', round_corners=True, corner_radius=2)
    pdf.set_fill_color(*GOLD)
    pdf.rect(14, y_prin, 2.5, 12, 'F', round_corners=True, corner_radius=1)

    pdf.set_xy(18.5, y_prin + 1.2)
    pdf.set_font('Helvetica', 'B', 8.5)
    pdf.set_text_color(*NAVY)
    pdf.cell(w_page - 8, 4, limpiar('PRINCIPIO FUNDAMENTAL: "CAPTURAR UNA VEZ, REUTILIZAR DESPUÉS"'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_xy(18.5, y_prin + 5.5)
    pdf.set_font('Helvetica', '', 7.6)
    pdf.set_text_color(*TEXT_DARK)
    pdf.cell(w_page - 8, 4, limpiar('USAER 02-E es un sistema integrado donde los datos de alumnos, escuelas y antecedentes forman parte de una historia educativa conectada.'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Las 3 Pestañas de la Plataforma
    y_pest = y_prin + 14.5
    pdf.set_xy(14, y_pest)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_text_color(*DARK_NAVY)
    pdf.cell(w_page, 5, limpiar('1. Estructura General de la Plataforma (Las 3 Pestañas)'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    w_tab = (w_page - 6) / 3
    tabs_data = [
        ('1. Mi Planeación', 'Recorrido Docente Ágil', NAVY, (244, 248, 250),
         'Espacio personal donde cada maestro diseña, edita y entrega su planeación en 3 sencillos pasos. Incluye autoguardado, conexión con el expediente y generación de PDF.'),
        ('2. Trabajo Colaborativo', 'Conexión Multidisciplinaria', DARK_CYAN, (243, 249, 251),
         'Módulo donde el equipo paradocente (Psicología, Comunicación y Trabajo Social) aporta estrategias al Plan de Intervención coordinado por la Maestra de Apoyo.'),
        ('3. Revisión Directiva', 'Supervisión sin Burocracia', GOLD, (254, 251, 245),
         'Vista exclusiva para Dirección con semáforo de entregas en tiempo real por escuela y docente, retroalimentación formativa y validación oficial en 1 clic.')
    ]
    for i, (tab_t, tab_sub, tab_c, tab_bg, tab_d) in enumerate(tabs_data):
        x_t = 14 + (i * (w_tab + 3))
        pdf.set_fill_color(*tab_bg)
        pdf.set_draw_color(*tab_c)
        pdf.set_line_width(0.35)
        pdf.rect(x_t, y_pest + 6, w_tab, 27, 'FD', round_corners=True, corner_radius=2)
        pdf.set_xy(x_t + 2.5, y_pest + 7.5)
        pdf.set_font('Helvetica', 'B', 8.2)
        pdf.set_text_color(*tab_c)
        pdf.cell(w_tab - 5, 4, limpiar(tab_t), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_xy(x_t + 2.5, y_pest + 11.5)
        pdf.set_font('Helvetica', 'I', 7.2)
        pdf.set_text_color(*SLATE)
        pdf.cell(w_tab - 5, 3.5, limpiar(tab_sub), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_xy(x_t + 2.5, y_pest + 15.5)
        pdf.set_font('Helvetica', '', 7.1)
        pdf.set_text_color(*TEXT_DARK)
        pdf.multi_cell(w_tab - 5, 3.4, limpiar(tab_d))

    # El Recorrido en 3 Pasos (Timeline Visual)
    y_time = y_pest + 36
    pdf.set_xy(14, y_time)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_text_color(*DARK_NAVY)
    pdf.cell(w_page, 5, limpiar('2. El Flujo de Trabajo en 3 Pasos (Para todo el Personal)'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pasos_h = [
        ('PASO 1: ¿A quién planeo?', 'Selección de matrícula y modalidad', NAVY, '30 segundos'),
        ('PASO 2: Antecedentes e IA', 'Conexión de evidencias y propuesta', GOLD, '2 minutos'),
        ('PASO 3: Mi Formato y Entrega', 'Edición directa, PDF y envío digital', TEAL, 'Control total')
    ]
    w_p_box = (w_page - 6) / 3
    for i, (p_t, p_s, p_col, p_tag) in enumerate(pasos_h):
        x_p = 14 + (i * (w_p_box + 3))
        pdf.set_fill_color(248, 250, 252)
        pdf.set_draw_color(*p_col)
        pdf.set_line_width(0.35)
        pdf.rect(x_p, y_time + 6, w_p_box, 11, 'FD', round_corners=True, corner_radius=2)
        
        pdf.set_fill_color(*p_col)
        pdf.rect(x_p + 2, y_time + 7.5, 6, 8, 'F', round_corners=True, corner_radius=1.2)
        pdf.set_font('Helvetica', 'B', 8)
        pdf.set_text_color(*WHITE)
        pdf.set_xy(x_p + 2, y_time + 8.5)
        pdf.cell(6, 6, str(i + 1), align='C')
        
        pdf.set_xy(x_p + 9.5, y_time + 7)
        pdf.set_font('Helvetica', 'B', 7.6)
        pdf.set_text_color(*p_col)
        pdf.cell(w_p_box - 11, 4, limpiar(p_t), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_xy(x_p + 9.5, y_time + 11.2)
        pdf.set_font('Helvetica', '', 6.7)
        pdf.set_text_color(*SLATE)
        pdf.cell(w_p_box - 11, 3.5, limpiar(p_s), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Detalle Paso 1: Configuración de Entrada
    y_det1 = y_time + 20
    pdf.set_xy(14, y_det1)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_text_color(*DARK_NAVY)
    pdf.cell(w_page, 5, limpiar('3. Paso 1 a Fondo: ¿Cómo iniciar o retomar tu trabajo?'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    h_card1 = 43
    pdf.set_fill_color(252, 254, 255)
    pdf.set_draw_color(*BORDER_GRAY)
    pdf.rect(14, y_det1 + 6, w_page, h_card1, 'FD', round_corners=True, corner_radius=2.5)
    pdf.set_fill_color(*NAVY)
    pdf.rect(14, y_det1 + 6, 2.5, h_card1, 'F', round_corners=True, corner_radius=1)

    col_p1_w = (w_page - 10) / 2
    # Lado Izquierdo: Continuar donde me quedé
    x_p1_l = 18.5
    y_p1_c = y_det1 + 8.5
    pdf.set_xy(x_p1_l, y_p1_c)
    pdf.set_font('Helvetica', 'B', 8.2)
    pdf.set_text_color(*NAVY)
    pdf.cell(col_p1_w, 4, limpiar('A. Continuar donde me quedé (Borrador Activo)'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font('Helvetica', '', 7.3)
    pdf.set_text_color(*TEXT_DARK)
    pdf.set_x(x_p1_l)
    pdf.multi_cell(col_p1_w - 2, 3.6, limpiar(
        '• Tarjetas de borradores: Muestran escuela, alumnos y periodo.\n'
        '• Semáforo de estados:\n'
        '   - [ Borrador ]: En edición activa por la docente.\n'
        '   - [ Por ajustar ]: Dirección devolvió con observaciones constructivas.\n'
        '   - [ Enviado ]: Entregado digitalmente a Dirección.\n'
        '   - [ Revisado ]: Validado y autorizado oficialmente.\n'
        '• Pulsa [ Continuar ] para abrir tu borrador exactamente donde te quedaste.'
    ))

    # Lado Derecho: Nueva Planeación
    x_p1_r = x_p1_l + col_p1_w + 3
    pdf.set_xy(x_p1_r, y_p1_c)
    pdf.set_font('Helvetica', 'B', 8.2)
    pdf.set_text_color(*NAVY)
    pdf.cell(col_p1_w, 4, limpiar('B. Nueva Planeación (Desde Matrícula Oficial)'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font('Helvetica', '', 7.3)
    pdf.set_text_color(*TEXT_DARK)
    pdf.set_x(x_p1_r)
    pdf.multi_cell(col_p1_w - 2, 3.6, limpiar(
        '• Escuela asignada: Si tienes varias escuelas, elige en el menú desplegable.\n'
        '• Selección de alumnos: Elige uno o varios alumnos de la lista de matrícula.\n'
        '• Modalidad automática: El sistema detecta si es Individual o Grupal.\n'
        '• Sesión grupal especial: Activa la casilla si deseas reunir alumnos de atención individual en una sesión de grupo.\n'
        '• Periodo oficial: Ciclo y trimestre sugeridos en automático por calendario SEP.\n'
        '• Pulsa [ Crear mi borrador ] para consolidar el contexto institucional.'
    ))

    # Sección de Recuperación y Respaldo en Paso 1
    y_rec = y_det1 + h_card1 + 8
    pdf.set_fill_color(240, 246, 249)
    pdf.set_draw_color(*DARK_CYAN)
    pdf.set_line_width(0.3)
    pdf.rect(14, y_rec, w_page, 15, 'FD', round_corners=True, corner_radius=2)
    pdf.set_xy(18, y_rec + 1.8)
    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_text_color(*DARK_CYAN)
    pdf.cell(w_page - 8, 4, limpiar('Recuperación de Respaldo (.json) en Paso 1:'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font('Helvetica', '', 7.3)
    pdf.set_text_color(*TEXT_DARK)
    pdf.set_x(18)
    pdf.multi_cell(w_page - 10, 3.5, limpiar(
        'En el menú "Recuperar un respaldo o consultar ayuda" puedes arrastrar un archivo .json guardado previamente en tu computadora. La plataforma lo valida contra tu cuenta y lo restaura en 2 segundos con todas sus tablas, fechas y adaptaciones intactas.'
    ))

    # =========================================================================
    # PÁGINA 2: FORMATOS OFICIALES Y PASO 2 (EXPEDIENTE, PDA E IA)
    # =========================================================================
    pdf.add_page()
    pdf.set_xy(14, 18)

    pdf.seccion_header('4', 'Los Formatos Oficiales y su Asignación por Función', 'Cada especialista cuenta con su formato normativo preconfigurado', NAVY)

    # Tabla comparativa de Formatos
    y_fmt = pdf.get_y()
    w_cols_fmt = [18, 42, 50, 72]
    headers_fmt = ['Formato', 'Denominacion', 'Quien lo utiliza', 'Proposito pedagogico y normativo']
    
    # Encabezado tabla
    pdf.set_fill_color(*NAVY)
    pdf.set_font('Helvetica', 'B', 7.5)
    pdf.set_text_color(*WHITE)
    x_curr = 14
    for i, h in enumerate(headers_fmt):
        pdf.set_xy(x_curr, y_fmt)
        pdf.cell(w_cols_fmt[i], 5.5, limpiar(h), align='C', fill=True, border=1)
        x_curr += w_cols_fmt[i]

    # Filas de la tabla
    filas_fmt = [
        ('XXI', 'Plan de Intervención (PI)', 'Maestra de Apoyo\n(Coordinación del Plan)', 'Plan anual o multianual con metas individuales. Los especialistas aportan en Trabajo Colaborativo. Las NEE y BAP se alimentan del expediente.'),
        ('XXIII', 'Planeación Trimestral', 'Maestra de Apoyo,\nPsicología y Comunicación', 'Dosificación de sesiones y aprendizajes trimestrales. Incluye Guía XIX (por alumno) y Guía XX (Aptitudes Sobresalientes).'),
        ('XXV', 'Planeación de Contexto', 'Trabajo Social', 'Intervención en barreras del contexto familiar, escolar y comunitario. Consolida compromisos de corresponsabilidad con familias y escuela.')
    ]
    y_row = y_fmt + 5.5
    for fmt_cod, fmt_nom, fmt_quien, fmt_desc in filas_fmt:
        h_row = 11.5
        x0 = 14
        x1 = x0 + w_cols_fmt[0]
        x2 = x1 + w_cols_fmt[1]
        x3 = x2 + w_cols_fmt[2]

        pdf.set_fill_color(252, 254, 255)
        pdf.set_draw_color(*BORDER_GRAY)
        pdf.rect(x0, y_row, w_cols_fmt[0], h_row, 'FD')
        pdf.rect(x1, y_row, w_cols_fmt[1], h_row, 'FD')
        pdf.rect(x2, y_row, w_cols_fmt[2], h_row, 'FD')
        pdf.rect(x3, y_row, w_cols_fmt[3], h_row, 'FD')

        # Col 0: Codigo
        pdf.set_xy(x0, y_row + 3.5)
        pdf.set_font('Helvetica', 'B', 8)
        pdf.set_text_color(*DARK_NAVY)
        pdf.cell(w_cols_fmt[0], 4, limpiar(fmt_cod), align='C')

        # Col 1: Denominacion
        pdf.set_xy(x1 + 1, y_row + 3.5)
        pdf.set_font('Helvetica', 'B', 7.2)
        pdf.set_text_color(*NAVY)
        pdf.cell(w_cols_fmt[1] - 2, 4, limpiar(fmt_nom), align='C')

        # Col 2: Quien lo utiliza
        pdf.set_xy(x2 + 1, y_row + 2.2)
        pdf.set_font('Helvetica', '', 6.8)
        pdf.set_text_color(*TEXT_DARK)
        pdf.multi_cell(w_cols_fmt[2] - 2, 3.4, limpiar(fmt_quien), align='C')

        # Col 3: Descripcion
        pdf.set_xy(x3 + 1.5, y_row + 1.5)
        pdf.set_font('Helvetica', '', 6.8)
        pdf.set_text_color(*TEXT_DARK)
        pdf.multi_cell(w_cols_fmt[3] - 3, 3.1, limpiar(fmt_desc), align='L')

        y_row += h_row

    # Paso 2 a Fondo
    pdf.set_y(y_row + 4)
    pdf.seccion_header('5', 'Paso 2 a Fondo: Conexión Automática, Currículo e Inteligencia Artificial', 'Aprovecha lo que el equipo ya documentó y dosifica en 3 momentos', GOLD)

    y_p2_box = pdf.get_y()
    w_p2_c = (w_page - 8) / 3
    h_p2_b = 64

    # Tarjeta 1: Antecedentes
    x_b1 = 14
    pdf.set_fill_color(254, 251, 245)
    pdf.set_draw_color(230, 205, 155)
    pdf.rect(x_b1, y_p2_box, w_p2_c, h_p2_b, 'FD', round_corners=True, corner_radius=2)
    pdf.set_xy(x_b1 + 2.5, y_p2_box + 2.5)
    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_text_color(*GOLD)
    pdf.cell(w_p2_c - 5, 4, limpiar('1. Antecedentes del Expediente'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font('Helvetica', '', 7.1)
    pdf.set_text_color(*TEXT_DARK)
    pdf.set_x(x_b1 + 2.5)
    pdf.multi_cell(w_p2_c - 5, 3.5, limpiar(
        '• Lectura automática: La plataforma lee antecedentes verificados (Anexos III, IV, V, visitas y acuerdos).\n\n'
        '• Botón [ + Usar en borrador ]:\n'
        'Transfiere el antecedente como necesidad o barrera directamente a tu formato oficial sin copiar ni pegar.\n\n'
        '• Trazabilidad: El texto conserva la etiqueta de su fuente original (ej. [Anexo III · fecha]) para sustentar la intervención ante supervisión.\n\n'
        '• Botón [ Actualizar ]: Consulta si hubo nuevos registros en el expediente.'
    ))

    # Tarjeta 2: Referentes Oficiales y PDA
    x_b2 = x_b1 + w_p2_c + 4
    pdf.set_fill_color(254, 251, 245)
    pdf.set_draw_color(230, 205, 155)
    pdf.rect(x_b2, y_p2_box, w_p2_c, h_p2_b, 'FD', round_corners=True, corner_radius=2)
    pdf.set_xy(x_b2 + 2.5, y_p2_box + 2.5)
    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_text_color(*GOLD)
    pdf.cell(w_p2_c - 5, 4, limpiar('2. Referentes Oficiales y PDA'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font('Helvetica', '', 7.1)
    pdf.set_text_color(*TEXT_DARK)
    pdf.set_x(x_b2 + 2.5)
    pdf.multi_cell(w_p2_c - 5, 3.5, limpiar(
        '• Catálogo SEP integrado: Disponible para maestras de apoyo. Selecciona entre los 4 Campos Formativos:\n'
        '  - Lenguajes\n'
        '  - Saberes y Pensamiento Científico\n'
        '  - Ética, Naturaleza y Sociedades\n'
        '  - De lo Humano y lo Comunitario\n\n'
        '• Ejes articuladores: Inclusión, pensamiento crítico, etc.\n\n'
        '• Buscador por palabra clave y filtro por grado escolar (1° a 6°).\n\n'
        '• Adaptación docente: Puedes adecuar el PDA oficial al ritmo del alumno.'
    ))

    # Tarjeta 3: Propuesta con IA
    x_b3 = x_b2 + w_p2_c + 4
    pdf.set_fill_color(254, 251, 245)
    pdf.set_draw_color(230, 205, 155)
    pdf.rect(x_b3, y_p2_box, w_p2_c, h_p2_b, 'FD', round_corners=True, corner_radius=2)
    pdf.set_xy(x_b3 + 2.5, y_p2_box + 2.5)
    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_text_color(*GOLD)
    pdf.cell(w_p2_c - 5, 4, limpiar('3. Propuesta Pedagógica con IA'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font('Helvetica', '', 7.1)
    pdf.set_text_color(*TEXT_DARK)
    pdf.set_x(x_b3 + 2.5)
    pdf.multi_cell(w_p2_c - 5, 3.5, limpiar(
        '• Calendario inteligente: Configura inicio, duración (15-180 min), días y sesiones. Omite asuetos y CTEs de SEP.\n\n'
        '• Secuencia en 3 momentos de educación especial:\n'
        '  - Inicio: Tangible / manipulable.\n'
        '  - Desarrollo: Con andamiaje y apoyos.\n'
        '  - Cierre: Evaluación observable.\n\n'
        '• Privacidad: La IA recibe un resumen anónimo sin nombres ni CURP.\n\n'
        '• Botón [ Preparar mi planeación ].'
    ))

    # Banner de Conciliación de Cambios
    y_concil = y_p2_box + h_p2_b + 4
    pdf.set_fill_color(238, 245, 248)
    pdf.set_draw_color(*TEAL)
    pdf.rect(14, y_concil, w_page, 15, 'FD', round_corners=True, corner_radius=2)
    pdf.set_xy(18, y_concil + 1.8)
    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_text_color(*TEAL)
    pdf.cell(w_page - 8, 4, limpiar('Comparador Inteligente: Conservación de Ediciones Docentes:'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font('Helvetica', '', 7.2)
    pdf.set_text_color(*TEXT_DARK)
    pdf.set_x(18)
    pdf.multi_cell(w_page - 10, 3.4, limpiar(
        'Si vuelves a generar con IA sobre un borrador existente, la plataforma te muestra una vista previa comparativa y te ofrece dos opciones: "Aplicar actualización conservando mis ediciones manuales" o "Conservar mi borrador intacto". Tu criterio y redacción previa nunca se sobreescriben a ciegas.'
    ))

    # =========================================================================
    # PÁGINA 3: PASO 3 A FONDO: MI FORMATO, GUÍAS Y ENTREGA DIGITAL
    # =========================================================================
    pdf.add_page()
    pdf.set_xy(14, 18)

    pdf.seccion_header('6', 'Paso 3 a Fondo: Mi Formato y Entrega (Control Docente Total)', 'Edición flexible celda por celda, tablas grupales y barra de acciones', TEAL)

    # Detalle de Tablas y Celdas Editables
    y_ed = pdf.get_y()
    pdf.set_font('Helvetica', 'B', 8.5)
    pdf.set_text_color(*DARK_NAVY)
    pdf.cell(w_page, 5, limpiar('A. Estructura de Tablas del Formato Oficial (Edición Directa)'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    w_box_ed = (w_page - 6) / 3
    h_box_ed = 42
    tablas_info = [
        ('1. Necesidades / Barreras', 'Aprendizajes y Descriptores', NAVY,
         '• Cada fila contiene la necesidad o barrera documentada.\n• Objetivo o aprendizaje esperado.\n• Descriptor de logro: Qué demostración observable se espera del alumno.\n• Botones para agregar filas o retirar filas manuales.'),
        ('2. Dosificación de Sesiones', 'Contexto, Tiempo y Recursos', TEAL,
         '• Fecha y duración de cada sesión.\n• Contexto: Aula regular o aula de apoyo.\n• Secuencia didáctica: Inicio, desarrollo y cierre.\n• Apoyos razonables y materiales requeridos.\n• Seguimiento observable del avance.'),
        ('3. Evaluación y Seguimiento', 'Resultados al Concluir', GOLD,
         '• La evaluación final se registra después de trabajar con el alumno, no como predicción.\n• Textos de acuerdos, compromisos y observaciones docentes.\n• Se conserva separada la voz docente de las sugerencias automáticas.')
    ]
    for i, (t_t, t_s, t_col, t_d) in enumerate(tablas_info):
        x_e = 14 + (i * (w_box_ed + 3))
        pdf.set_fill_color(248, 251, 252)
        pdf.set_draw_color(*t_col)
        pdf.set_line_width(0.3)
        pdf.rect(x_e, y_ed + 5.5, w_box_ed, h_box_ed, 'FD', round_corners=True, corner_radius=2)
        pdf.set_xy(x_e + 2.5, y_ed + 7)
        pdf.set_font('Helvetica', 'B', 8)
        pdf.set_text_color(*t_col)
        pdf.cell(w_box_ed - 5, 4, limpiar(t_t), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_xy(x_e + 2.5, y_ed + 11)
        pdf.set_font('Helvetica', 'I', 7.1)
        pdf.set_text_color(*SLATE)
        pdf.cell(w_box_ed - 5, 3.5, limpiar(t_s), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_xy(x_e + 2.5, y_ed + 15)
        pdf.set_font('Helvetica', '', 7.1)
        pdf.set_text_color(*TEXT_DARK)
        pdf.multi_cell(w_box_ed - 5, 3.4, limpiar(t_d))

    # Guías Grupales (XIX y XX)
    y_guias = y_ed + h_box_ed + 9
    pdf.set_xy(14, y_guias)
    pdf.set_font('Helvetica', 'B', 8.5)
    pdf.set_text_color(*DARK_NAVY)
    pdf.cell(w_page, 5, limpiar('B. Atención Focalizada en Grupo: Guía XIX y Guía XX (Aptitudes Sobresalientes)'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    w_g_box = (w_page - 4) / 2
    h_g_box = 32
    # Guía XIX
    pdf.set_fill_color(245, 250, 252)
    pdf.set_draw_color(*NAVY)
    pdf.rect(14, y_guias + 5.5, w_g_box, h_g_box, 'FD', round_corners=True, corner_radius=2)
    pdf.set_xy(17, y_guias + 7)
    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_text_color(*NAVY)
    pdf.cell(w_g_box - 6, 4, limpiar('Guía XIX: Actividades por Alumno y Área'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font('Helvetica', '', 7.1)
    pdf.set_text_color(*TEXT_DARK)
    pdf.set_x(17)
    pdf.multi_cell(w_g_box - 6, 3.4, limpiar(
        '• Permite desglosar las acciones pedagógicas individuales para cada alumno dentro de la planeación trimestral del grupo escolar.\n'
        '• Campos por alumno: Discapacidad/condición, actividades de aprendizaje, psicología, comunicación, trabajo social, situación inicial y final.\n'
        '• Incluye la opción "Editar texto completo por alumno" para redacciones amplias.'
    ))

    # Guía XX (AS)
    x_g2 = 14 + w_g_box + 4
    pdf.set_fill_color(254, 251, 245)
    pdf.set_draw_color(*GOLD)
    pdf.rect(x_g2, y_guias + 5.5, w_g_box, h_g_box, 'FD', round_corners=True, corner_radius=2)
    pdf.set_xy(x_g2 + 3, y_guias + 7)
    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_text_color(*GOLD)
    pdf.cell(w_g_box - 6, 4, limpiar('Guía XX (Anexo XX): Aptitudes Sobresalientes (AS)'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font('Helvetica', '', 7.1)
    pdf.set_text_color(*TEXT_DARK)
    pdf.set_x(x_g2 + 3)
    pdf.multi_cell(w_g_box - 6, 3.4, limpiar(
        '• Se activa opcionalmente cuando el alumno cuenta con aptitudes sobresalientes documentadas en su expediente.\n'
        '• Áreas de aptitud: Intelectual, Creativa, Socioafectiva, Psicomotriz, Artística.\n'
        '• Enfoque de enriquecimiento en 3 contextos: Áulico, Escolar y Extracurricular.\n'
        '• No se inventa por IA: solo se registra con evidencia previa de evaluación.'
    ))

    # Checklist de Calidad
    y_chk = y_guias + h_g_box + 8
    pdf.set_fill_color(240, 246, 249)
    pdf.set_draw_color(*DARK_CYAN)
    pdf.rect(14, y_chk, w_page, 15, 'FD', round_corners=True, corner_radius=2)
    pdf.set_xy(18, y_chk + 1.8)
    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_text_color(*DARK_CYAN)
    pdf.cell(w_page - 8, 4, limpiar('Checklist de Calidad: "Antes de enviar · Aspectos por completar":'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font('Helvetica', '', 7.2)
    pdf.set_text_color(*TEXT_DARK)
    pdf.set_x(18)
    pdf.multi_cell(w_page - 10, 3.4, limpiar(
        'La plataforma cuenta con un validador en tiempo real que previene errores y omisiones antes de compartir con Dirección. Te indicará amablemente si falta algún descriptor de logro o campo obligatorio. Cuando todo esté en orden, verás el mensaje de confirmación verde: "Listo para revisar y enviar a Dirección".'
    ))

    # La Barra Fija Inferior (Los 4 Botones Oficiales)
    y_bar = y_chk + 18
    pdf.set_xy(14, y_bar)
    pdf.set_font('Helvetica', 'B', 8.5)
    pdf.set_text_color(*DARK_NAVY)
    pdf.cell(w_page, 5, limpiar('C. La Barra de Acciones Pegajosa (Pie de Página)'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    w_act4 = (w_page - 6) / 4
    h_act4 = 28
    acciones_oficiales = [
        ('1. [ Guardar borrador ]', TEAL, (238, 248, 244),
         'Guarda inmediatamente cada cambio confirmado en la base de datos segura. Además, el autoguardado protege cada 15 segundos.'),
        ('2. [ Ver PDF ]', NAVY, (244, 248, 250),
         'Genera al instante la vista previa de impresión oficial. Pulsa [ Descargar PDF ] para tener tu documento o [ Volver a editar ].'),
        ('3. [ Enviar a Dirección ]', DARK_CYAN, (240, 248, 250),
         'Habilitado cuando se resuelven los pendientes. Notifica a Dirección para revisión formativa digital, sin imprimir papeleo.'),
        ('4. [ Respaldo .json ]', GOLD, (254, 251, 245),
         'Descarga tu archivo editable de respaldo en 1 clic a tu disco duro. Seguridad total ante apagones o desconexión de Wi-Fi.')
    ]
    for i, (b_t, b_c, b_bg, b_d) in enumerate(acciones_oficiales):
        x_ac = 14 + (i * (w_act4 + 2))
        pdf.set_fill_color(*b_bg)
        pdf.set_draw_color(*b_c)
        pdf.set_line_width(0.35)
        pdf.rect(x_ac, y_bar + 5.5, w_act4, h_act4, 'FD', round_corners=True, corner_radius=2)
        pdf.set_xy(x_ac + 2, y_bar + 7)
        pdf.set_font('Helvetica', 'B', 7.5)
        pdf.set_text_color(*b_c)
        pdf.cell(w_act4 - 4, 4, limpiar(b_t), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_xy(x_ac + 2, y_bar + 11.5)
        pdf.set_font('Helvetica', '', 6.8)
        pdf.set_text_color(*TEXT_DARK)
        pdf.multi_cell(w_act4 - 4, 3.3, limpiar(b_d))

    # =========================================================================
    # PÁGINA 4: RUTAS POR ESPECIALIDAD Y TRABAJO COLABORATIVO
    # =========================================================================
    pdf.add_page()
    pdf.set_xy(14, 18)

    pdf.seccion_header('7', 'Rutas Específicas según la Función Docente', 'Orientación práctica para cada integrante del equipo multidisciplinario', DARK_CYAN)

    y_roles = pdf.get_y()
    h_role_box = 32.5

    roles_guia = [
        ('1. MAESTRAS DE APOYO (Aprendizaje)', NAVY, (246, 250, 252), 'Coordinación Pedagógica',
         '• Plan de Intervención (XXI): Para alumnos con IEPP. Es el documento maestro anual donde los especialistas incorporarán sus aportaciones.\n'
         '• Planeación Trimestral (XXIII): Para la atención grupal en aula regular o apoyo. Permite dosificar secuencias por grado y campo.\n'
         '• Dosificación ágil: Diseña actividades con Inicio (manipulable), Desarrollo (andamiaje) y Cierre (evaluación observable). Evita párrafos burocráticos.'),

        ('2. PSICOLOGÍA', DARK_CYAN, (244, 250, 252), 'Área Socioemocional',
         '• 5 Competencias de Zona 001: Autoconciencia, Autorregulación, Conciencia social, Relaciones interpersonales y Toma de decisiones responsables.\n'
         '• Sesiones por subgrupos: Calendario de al menos 5 sesiones grupales, al menos 1 en aula regular y una sugerencia para familias.\n'
         '• Aporte colaborativo: Entra a "Trabajo colaborativo", abre el Plan XXI del alumno y redacta tus sugerencias con tu firma profesional.'),

        ('3. COMUNICACIÓN', GOLD, (254, 251, 245), 'Lenguaje y Participación',
         '• Canal comunicativo: Define si la intervención es oral, con SAAC (Sistemas Aumentativos y Alternativos), apoyos pictográficos o lectoescritura adaptada.\n'
         '• Enfoque en el aula regular: Actividades diseñadas para que el alumno participe y se comunique con sus compañeros de grupo y docentes.\n'
         '• Aporte colaborativo: Brinda recomendaciones de comunicación accesible para que la maestra de grupo las aplique en el día a día.'),

        ('4. TRABAJO SOCIAL', TERRACOTTA, (254, 248, 247), 'Contexto y Redes de Apoyo',
         '• Formato XXV: Identifica BAP en los 3 contextos: familiar, escolar y comunitario. Consolida compromisos claros de corresponsabilidad.\n'
         '• Reutilización de visitas: Reutiliza antecedentes de visitas domiciliarias o acuerdos escolares previos sin volver a capturarlos.\n'
         '• Aporte colaborativo: Vincula apoyos sociofamiliares, becas institucionales, canalizaciones externas y seguimiento al Plan XXI.')
    ]

    for r_tit, r_col, r_bg, r_tag, r_txt in roles_guia:
        pdf.set_fill_color(*r_bg)
        pdf.set_draw_color(*BORDER_GRAY)
        pdf.set_line_width(0.3)
        pdf.rect(14, y_roles, w_page, h_role_box, 'FD', round_corners=True, corner_radius=2.5)
        pdf.set_fill_color(*r_col)
        pdf.rect(14, y_roles, 2.5, h_role_box, 'F', round_corners=True, corner_radius=1)

        pdf.set_xy(18.5, y_roles + 2)
        pdf.set_font('Helvetica', 'B', 8.5)
        pdf.set_text_color(*r_col)
        pdf.cell(100, 4, limpiar(r_tit), new_x=XPos.RIGHT, new_y=YPos.TOP)

        pdf.draw_badge(142, y_roles + 2, r_tag, r_col, WHITE, font_size=6.7)

        pdf.set_xy(18.5, y_roles + 6.8)
        pdf.set_font('Helvetica', '', 7.1)
        pdf.set_text_color(*TEXT_DARK)
        pdf.multi_cell(w_page - 8, 3.4, limpiar(r_txt))

        y_roles += h_role_box + 2

    # Trabajo Colaborativo a Fondo
    pdf.set_y(y_roles + 2)
    pdf.seccion_header('8', 'El Ecosistema de Trabajo Colaborativo a Fondo', 'Cómo aporta todo el equipo en un solo documento maestro sin interferirse', NAVY)

    y_tc = pdf.get_y()
    pdf.set_fill_color(242, 248, 250)
    pdf.set_draw_color(*NAVY)
    pdf.rect(14, y_tc, w_page, 44, 'FD', round_corners=True, corner_radius=2.5)

    pdf.set_xy(18, y_tc + 2.5)
    pdf.set_font('Helvetica', 'B', 8.2)
    pdf.set_text_color(*NAVY)
    pdf.cell(w_page - 8, 4, limpiar('¿Cómo funciona el flujo de colaboración multidisciplinaria?'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font('Helvetica', '', 7.2)
    pdf.set_text_color(*TEXT_DARK)
    pdf.set_x(18)
    pdf.multi_cell(w_page - 10, 3.5, limpiar(
        '1. La Maestra de Apoyo crea el Plan de Intervención (XXI) o la Guía Grupal compartida desde su sesión.\n'
        '2. Los especialistas (Psicología, Comunicación y Trabajo Social) entran a la pestaña "Trabajo colaborativo".\n'
        '3. Eligen la escuela y seleccionan el documento maestro que desean enriquecer.\n'
        '4. Redactan sus aportaciones, estrategias y sugerencias desde su área disciplinar.\n'
        '5. Cada aportación se guarda de forma acotada y segura, firmada con el nombre, área y fecha del especialista.\n'
        '6. No se sobrescribe el trabajo de otros: cada profesional conserva su alcance de edición.\n'
        '7. En su planeación, la Maestra de Apoyo pulsa "Actualizar conexiones" para incorporar las aportaciones al documento final.\n'
        '8. Resultado: Un solo expediente integrado para el alumno, sin copias dispersas ni reuniones burocráticas innecesarias.'
    ))

    # =========================================================================
    # PÁGINA 5: EL MENÚ "MÁS HERRAMIENTAS" Y REVISIÓN DIRECTIVA
    # =========================================================================
    pdf.add_page()
    pdf.set_xy(14, 18)

    pdf.seccion_header('9', 'El Menú "Más Herramientas": Opciones Avanzadas', 'Arsenal de recursos disponibles cuando requieres profundizar o gestionar archivos', GOLD)

    y_herram = pdf.get_y()
    w_h_card = (w_page - 6) / 2
    h_h_card = 27.5

    herramientas_detalle = [
        ('1. Materiales y Escaneos', NAVY, (245, 250, 252),
         'Carga archivos en Word, PDF (hasta 1 000 pág), fotos de cuadernos o imágenes (hasta 32 MB). El sistema realiza OCR y transcribe hasta 10 páginas / 100 000 caracteres para incorporarlos a la planeación.'),

        ('2. Referentes Oficiales SEP', GOLD, (254, 251, 245),
         'Consulta permanente del catálogo curricular de la Nueva Escuela Mexicana: Campos Formativos, Ejes Articuladores, contenidos oficiales y Proceso de Desarrollo de Aprendizaje (PDA) por grado.'),

        ('3. Evidencias del Expediente', DARK_CYAN, (244, 250, 252),
         'Consulta las fuentes verificadas asociadas al alumno (evaluaciones psicopedagógicas, notas previas, visitas). Puedes pulsar "Actualizar información del expediente" para refrescar evidencias.'),

        ('4. Conexiones y Seguimiento', TEAL, (238, 248, 244),
         'Mantiene la cadena pedagógica: EPP (Evaluación) -> PI (Plan de Intervención) -> Planeación Trimestral. Integra aportaciones y permite registrar resultados reales con su respaldo documental.'),

        ('5. Organizar Sesiones del Equipo', DARK_CYAN, (244, 250, 252),
         'Herramienta para paradocentes: organiza subgrupos de alumnos, asigna fechas en calendario, define objetivos específicos y da seguimiento a las 5 competencias socioemocionales de Zona 001.'),

        ('6. Ideas Adicionales con IA', AMBER, (254, 250, 242),
         'Generador interactivo puntual: solicita sugerencias pedagógicas alternativas para una actividad específica con su propia revisión de privacidad, sin necesidad de regenerar el documento completo.'),

        ('7. Respaldo y Versiones Históricas', NAVY, (245, 250, 252),
         'Consulta el historial de todas las versiones guardadas en la nube. Puedes descargar cualquier revisión previa en formato JSON editable y conciliar ediciones pendientes.'),

        ('8. Guía Grupal XIX / XX', GOLD, (254, 251, 245),
         'Permite registrar los datos del maestro de grupo regular y activar la tabla de Aptitudes Sobresalientes (Anexo XX) con acciones de enriquecimiento áulico, escolar y extracurricular.')
    ]

    for i, (h_tit, h_col, h_bg, h_desc) in enumerate(herramientas_detalle):
        fila = i // 2
        col = i % 2
        x_pos = 14 + (col * (w_h_card + 6))
        y_pos = y_herram + (fila * (h_h_card + 3))

        pdf.set_fill_color(*h_bg)
        pdf.set_draw_color(*h_col)
        pdf.set_line_width(0.3)
        pdf.rect(x_pos, y_pos, w_h_card, h_h_card, 'FD', round_corners=True, corner_radius=2)
        pdf.set_fill_color(*h_col)
        pdf.rect(x_pos, y_pos, 2, h_h_card, 'F', round_corners=True, corner_radius=1)

        pdf.set_xy(x_pos + 3.5, y_pos + 2)
        pdf.set_font('Helvetica', 'B', 7.8)
        pdf.set_text_color(*h_col)
        pdf.cell(w_h_card - 6, 4, limpiar(h_tit), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        pdf.set_xy(x_pos + 3.5, y_pos + 6.2)
        pdf.set_font('Helvetica', '', 6.9)
        pdf.set_text_color(*TEXT_DARK)
        pdf.multi_cell(w_h_card - 6, 3.2, limpiar(h_desc))

    # El Módulo de Revisión Directiva
    y_dir = y_herram + (4 * (h_h_card + 3)) + 2
    pdf.set_y(y_dir)
    pdf.seccion_header('10', 'Revisión Directiva y Acompañamiento Formativo', 'Monitoreo ágil sin intermediación burocrática ni sobrecarga administrativa', DARK_NAVY)

    y_dir_box = pdf.get_y()
    pdf.set_fill_color(248, 250, 252)
    pdf.set_draw_color(*DARK_NAVY)
    pdf.rect(14, y_dir_box, w_page, 38, 'FD', round_corners=True, corner_radius=2.5)

    pdf.set_xy(18, y_dir_box + 2.5)
    pdf.set_font('Helvetica', 'B', 8.2)
    pdf.set_text_color(*DARK_NAVY)
    pdf.cell(w_page - 8, 4, limpiar('Funcionalidades para la Dirección Escolar:'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font('Helvetica', '', 7.2)
    pdf.set_text_color(*TEXT_DARK)
    pdf.set_x(18)
    pdf.multi_cell(w_page - 10, 3.5, limpiar(
        '• Semáforo de entregas en tiempo real: La dirección visualiza el estado de cada docente organizado por escuela y fecha.\n'
        '• Lectura inmediata del PDF: Abre cualquier documento en su formato oficial con un solo clic.\n'
        '• Retroalimentación formativa: En lugar de reescribir o rechazar sin explicación, la dirección redacta observaciones orientadoras.\n'
        '• Devolución "Por ajustar": Notifica a la docente para que realice adecuaciones específicas sin perder su borrador.\n'
        '• Validación en 1 clic: Autoriza el documento oficialmente. Queda registrado como [ Revisado / Validado ] en el expediente institucional.\n'
        '• Cero archivos en físico ni correos: Todo el ciclo de entrega, revisión y archivo vive en la plataforma.'
    ))

    # =========================================================================
    # PÁGINA 6: RED DE SEGURIDAD, PRIVACIDAD Y BUENAS PRÁCTICAS
    # =========================================================================
    pdf.add_page()
    pdf.set_xy(14, 18)

    pdf.seccion_header('11', 'Red de Seguridad Total (Cero Pérdidas ante Cortes de Luz o Wi-Fi)', 'Cómo la plataforma protege el trabajo docente contra cualquier eventualidad técnica', TEAL)

    y_seg = pdf.get_y()
    w_s_box = (w_page - 6) / 3
    h_s_box = 32

    seg_cards = [
        ('1. Autoguardado Activo', TEAL, (238, 248, 244),
         'La plataforma ejecuta un autoguardado en segundo plano cada 15 segundos mientras redactas. Ningún cambio reciente queda desprotegido en la nube.'),
        ('2. Respaldo Local .json', NAVY, (244, 248, 250),
         'En la barra inferior tienes el botón [ Descargar respaldo editable ]. Te entrega un archivo .json con tu planeación completa para guardarla en tu USB o laptop.'),
        ('3. Restauración en 2 Seg', GOLD, (254, 251, 245),
         'Si se desconecta el Wi-Fi o se apaga la computadora: vuelve a entrar y abre [ Continuar donde me quedé ] o sube tu archivo .json en Paso 1 para restaurar todo al instante.')
    ]
    for i, (st_t, st_c, st_bg, st_d) in enumerate(seg_cards):
        x_s = 14 + (i * (w_s_box + 3))
        pdf.set_fill_color(*st_bg)
        pdf.set_draw_color(*st_c)
        pdf.set_line_width(0.35)
        pdf.rect(x_s, y_seg, w_s_box, h_s_box, 'FD', round_corners=True, corner_radius=2)
        pdf.set_xy(x_s + 2.5, y_seg + 2.5)
        pdf.set_font('Helvetica', 'B', 7.8)
        pdf.set_text_color(*st_c)
        pdf.cell(w_s_box - 5, 4, limpiar(st_t), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_xy(x_s + 2.5, y_seg + 7.5)
        pdf.set_font('Helvetica', '', 6.9)
        pdf.set_text_color(*TEXT_DARK)
        pdf.multi_cell(w_s_box - 5, 3.4, limpiar(st_d))

    # Privacidad y Anonimización
    y_priv = y_seg + h_s_box + 4
    pdf.set_y(y_priv)
    pdf.seccion_header('12', 'Privacidad y Protección Ética de Datos', 'Cumplimiento normativo y resguardo de la identidad del alumnado', DARK_NAVY)

    y_priv_box = pdf.get_y()
    pdf.set_fill_color(248, 250, 252)
    pdf.set_draw_color(*DARK_NAVY)
    pdf.rect(14, y_priv_box, w_page, 28, 'FD', round_corners=True, corner_radius=2)

    pdf.set_xy(18, y_priv_box + 2)
    pdf.set_font('Helvetica', 'B', 7.8)
    pdf.set_text_color(*DARK_NAVY)
    pdf.cell(w_page - 8, 4, limpiar('Políticas de Seguridad Implementadas:'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font('Helvetica', '', 7.1)
    pdf.set_text_color(*TEXT_DARK)
    pdf.set_x(18)
    pdf.multi_cell(w_page - 10, 3.4, limpiar(
        '• Cero datos personales hacia la IA: Antes de solicitar propuestas, el sistema anonimiza automáticamente los textos, sustituyendo nombres por alias y eliminando CURP, teléfonos o domicilios.\n'
        '• Consentimiento explícito: La docente revisa el resumen en el panel "Ver qué se envía" antes de autorizar la consulta de IA.\n'
        '• Cuentas personales no compartidas: Cada maestro accede con sus credenciales institucionales. Nunca se deben usar cuentas compartidas.\n'
        '• Cierre de sesión seguro: El botón "Guardar cambios y cerrar sesión" solo cierra si el guardado fue confirmado; si hay una falla, mantiene la sesión abierta para no perder nada.'
    ))

    # Matriz de Buenas Prácticas Pedagógicas
    y_bp = y_priv_box + 32
    pdf.set_y(y_bp)
    pdf.seccion_header('13', 'Decálogo de Buenas Prácticas Pedagógicas USAER 02-E', 'Criterios clave para maximizar el impacto educativo y ahorrar tiempo administrativo', GOLD)

    y_bp_box = pdf.get_y()
    w_bp_c = (w_page - 4) / 2
    h_bp_b = 39

    # Lo que SÍ se debe hacer
    pdf.set_fill_color(240, 248, 245)
    pdf.set_draw_color(*TEAL)
    pdf.rect(14, y_bp_box, w_bp_c, h_bp_b, 'FD', round_corners=True, corner_radius=2)
    pdf.set_xy(17, y_bp_box + 2)
    pdf.set_font('Helvetica', 'B', 7.8)
    pdf.set_text_color(*TEAL)
    pdf.cell(w_bp_c - 6, 4, limpiar('LO QUE SÍ DEBEMOS HACER:'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font('Helvetica', '', 6.9)
    pdf.set_text_color(*TEXT_DARK)
    pdf.set_x(17)
    pdf.multi_cell(w_bp_c - 6, 3.4, limpiar(
        '• Reutilizar antecedentes con [+ Usar en borrador].\n'
        '• Diseñar secuencias ágiles: Inicio tangible, desarrollo con andamiaje y cierre observable.\n'
        '• Editar directamente el formato para adaptarlo al ritmo del grupo.\n'
        '• Registrar resultados finales después de la sesión con los alumnos.\n'
        '• Descargar tu respaldo .json al terminar cada jornada de planeación.'
    ))

    # Lo que se debe evitar
    x_bp_r = 14 + w_bp_c + 4
    pdf.set_fill_color(254, 248, 247)
    pdf.set_draw_color(*TERRACOTTA)
    pdf.rect(x_bp_r, y_bp_box, w_bp_c, h_bp_b, 'FD', round_corners=True, corner_radius=2)
    pdf.set_xy(x_bp_r + 3, y_bp_box + 2)
    pdf.set_font('Helvetica', 'B', 7.8)
    pdf.set_text_color(*TERRACOTTA)
    pdf.cell(w_bp_c - 6, 4, limpiar('LO QUE DEBEMOS EVITAR:'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font('Helvetica', '', 6.9)
    pdf.set_text_color(*TEXT_DARK)
    pdf.set_x(x_bp_r + 3)
    pdf.multi_cell(w_bp_c - 6, 3.4, limpiar(
        '• No volver a capturar lo que el expediente ya tiene registrado.\n'
        '• No redactar párrafos burocráticos extensos que no se apliquen en aula.\n'
        '• No inventar registros o antecedentes si no hay evidencia documental.\n'
        '• No predecir evaluaciones finales antes de trabajar con el alumno.\n'
        '• No imprimir ni enviar por correo: entregar siempre vía la plataforma.'
    ))

    # Guardar en las rutas oficiales
    ruta_docs = Path(__file__).resolve().parents[1] / 'docs' / 'Guia_Definitiva_Planeacion_USAER_02E.pdf'
    ruta_docs.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(ruta_docs))

    # Copia en el Escritorio
    ruta_desktop = Path(r'C:\Users\edgar\OneDrive\Escritorio\Guia_Definitiva_Planeacion_USAER_02E.pdf')
    try:
        pdf.output(str(ruta_desktop))
    except Exception:
        pass

    # Copia en los Artifacts del Brain
    ruta_brain = Path(r'C:\Users\edgar\.gemini\antigravity-ide\brain\880375fd-87ab-4715-ae31-eb06455b86f3\Guia_Definitiva_Planeacion_USAER_02E.pdf')
    try:
        pdf.output(str(ruta_brain))
    except Exception:
        pass

    print(f'Guia Definitiva generada exitosamente en:\n1. {ruta_docs}\n2. {ruta_desktop}\n3. {ruta_brain}')
    return ruta_docs


if __name__ == '__main__':
    generar()

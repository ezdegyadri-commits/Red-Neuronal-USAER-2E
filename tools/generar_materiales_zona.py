"""Generador de materiales ejecutivos para la junta de zona de USAER 02-E:
1. Folleto Ejecutivo (2 paginas, imprimible)
2. Infografia de Impacto (1 pagina, visual vertical)
3. Presentacion de Diapositivas (7 diapositivas apaisadas para proyector)
"""
from pathlib import Path
from fpdf import FPDF
from fpdf.enums import XPos, YPos

# Paleta institucional USAER 02-E
NAVY = (27, 73, 88)        # #1B4958
DARK_NAVY = (18, 51, 62)   # #12333E
GOLD = (196, 147, 57)      # #C49339
SLATE = (93, 114, 123)     # #5D727B
LIGHT_BG = (248, 250, 251) # #F8FAFB
CARD_BG = (241, 245, 247)  # #F1F5F7
WHITE = (255, 255, 255)
TEXT_DARK = (30, 45, 50)
BORDER_GRAY = (220, 230, 235)


def limpiar(texto):
    """Reemplaza caracteres fuera del set estandar latin-1 por equivalentes limpios."""
    if not isinstance(texto, str):
        return texto
    return (texto.replace('\u201c', '"')
                 .replace('\u201d', '"')
                 .replace('\u2018', "'")
                 .replace('\u2019', "'")
                 .replace('\u2014', '-')
                 .replace('\u2013', '-')
                 .replace('\u2022', '-')
                 .replace('\u2026', '...')
                 .replace('\u2010', '-'))


# ==============================================================================
# 1. FOLLETO EJECUTIVO (Brochure / One-Pager de 2 paginas)
# ==============================================================================
class FolletoPDF(FPDF):
    def __init__(self):
        super().__init__(orientation='P', unit='mm', format='Letter')
        self.set_auto_page_break(auto=True, margin=15)
        self.set_margins(16, 16, 16)

    def header(self):
        self.set_fill_color(*NAVY)
        self.rect(0, 0, 216, 15, 'F')
        self.set_fill_color(*GOLD)
        self.rect(0, 15, 216, 2, 'F')
        self.set_xy(16, 3.5)
        self.set_font('Helvetica', 'B', 9.5)
        self.set_text_color(*WHITE)
        self.cell(100, 8, 'USAER 02-E  |  ZONA 001 EDUCACION ESPECIAL', align='L')
        self.set_xy(100, 3.5)
        self.set_font('Helvetica', '', 8.5)
        self.cell(100, 8, 'INFORME EJECUTIVO PARA DIRECTORES Y SUPERVISION', align='R')
        self.ln(15)

    def footer(self):
        self.set_y(-12)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(*SLATE)
        self.cell(0, 8, f'USAER 02-E · De la Burocracia al Acompanamiento Pedagogico · Pagina {self.page_no()}', align='C')

    def seccion(self, titulo):
        self.ln(2)
        self.set_font('Helvetica', 'B', 11)
        self.set_text_color(*NAVY)
        self.cell(0, 6, limpiar(titulo), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(*GOLD)
        self.set_line_width(0.6)
        self.line(self.get_x(), self.get_y(), self.get_x() + 184, self.get_y())
        self.ln(2.5)

    def caja(self, titulo, texto, icono='*', border_color=NAVY, fill_color=CARD_BG):
        x = self.get_x()
        y = self.get_y()
        w = 184
        self.set_fill_color(*fill_color)
        self.set_draw_color(*border_color)
        self.set_line_width(0.3)
        self.set_font('Helvetica', 'B', 9.5)
        self.set_text_color(*border_color)
        self.set_xy(x + 4, y + 2)
        self.cell(w - 8, 5, limpiar(f'{icono} {titulo}'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font('Helvetica', '', 8.5)
        self.set_text_color(*TEXT_DARK)
        self.set_x(x + 4)
        self.multi_cell(w - 8, 4.3, limpiar(texto))
        y_fin = self.get_y() + 2
        alto = y_fin - y
        self.rect(x, y, w, alto, 'D')
        self.set_y(y_fin + 3)


def crear_folleto(ruta):
    pdf = FolletoPDF()
    pdf.add_page()

    # Encabezado
    pdf.set_font('Helvetica', 'B', 16)
    pdf.set_text_color(*DARK_NAVY)
    pdf.cell(0, 8, 'Hacia una Gestion Educativa Conectada', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font('Helvetica', 'I', 9.5)
    pdf.set_text_color(*SLATE)
    pdf.cell(0, 5, 'Por que nacio la plataforma USAER 02-E y como devuelve tiempo pedagogico al docente', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(3)

    # El dolor real
    pdf.seccion('1. El Diagnostico Inicial: La Burocracia Zombie')
    pdf.set_font('Helvetica', '', 8.8)
    pdf.set_text_color(*TEXT_DARK)
    pdf.multi_cell(184, 4.5, limpiar(
        'En la educacion publica suele cometerse un error al digitalizar: pasar formatos de papel a Word o formularios sueltos de Drive. '
        'Esto no innova; traslada el cansancio burocratico de la libreta a la pantalla. '
        'Los maestros invierten horas capturando el mismo nombre, CURP, escuela y diagnostico en el Anexo 3, en la Planeacion y en las Actas. '
        'La informacion quedaba aislada en carpetas que nadie volvia a consultar.'
    ))
    pdf.ln(2)

    # Los tres principios
    pdf.seccion('2. Filosofia y Principios Rectores')
    pdf.caja(
        'Principio 1: Capturar una vez, reutilizar despues',
        'Si Trabajo Social ya registro la entrevista familiar o Psicologia evaluo el canal comunicativo, la Maestra de Apoyo lo tiene a un clic. Nadie vuelve a escribir lo que la USAER ya sabe.',
        icono='[1]', border_color=NAVY
    )
    pdf.caja(
        'Principio 2: Automatizar la rutina; reservar a las personas para el criterio',
        'La plataforma llena encabezados, filtra programas de estudio y genera PDFs oficiales. El profesional se enfoca en lo irremplazable: la intervencion pedagogica y el acompanamiento empatico.',
        icono='[2]', border_color=GOLD
    )
    pdf.caja(
        'Principio 3: Trayectoria viva del alumno (Fuente unica de verdad)',
        'Los expedientes no se reinician de cero cada ciclo escolar. La historia de apoyos, barreras y avances viaja con el alumno para asegurar continuidad educativa real.',
        icono='[3]', border_color=DARK_NAVY
    )

    # PAGINA 2: Casos Practicos
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 15)
    pdf.set_text_color(*DARK_NAVY)
    pdf.cell(0, 8, 'Casos Reales: Como Favorece al Maestro en el Aula?', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)

    pdf.caja(
        'Caso A: El boton "+ Usar en borrador" (Antecedentes inmediatos)',
        'Antes: La docente buscaba expedientes fisicos de meses atras para copiar a mano los acuerdos de visitas o anexos.\n'
        'Hoy: Al abrir la planeacion, el sistema lee automaticamente los Anexos III, IV, V y actas. Con el boton "+ Usar en borrador", transfiere antecedentes y barreras a sus notas en un segundo sin recaptura.',
        icono='A', border_color=NAVY, fill_color=(245, 249, 250)
    )

    pdf.caja(
        'Caso B: Planeacion tangible en 3 momentos para Educacion Especial',
        'Antes: Copiar parrafos teoricos interminables de programas sinteticos de 400 paginas.\n'
        'Hoy: Busca el PDA oficial en un clic y solicita apoyo de IA que propone secuencias concretas:\n'
        '  - Inicio: Con material manipulable o detonador visual.\n'
        '  - Desarrollo: Con andamiaje multinivel y apoyos graduados.\n'
        '  - Cierre: Con evaluacion formativa observable y tangible.',
        icono='B', border_color=GOLD, fill_color=(254, 250, 242)
    )

    pdf.caja(
        'Caso C: Trabajo interdisciplinario sin colisiones ni cadenas de archivos',
        'Antes: La maestra de apoyo terminaba su Plan Individual (XXI) y debia circular archivos de Word a Psicologia, Comunicacion y Trabajo Social, desfasando versiones.\n'
        'Hoy: La maestra coordina el documento maestro; los especialistas aportan desde la pestana "Trabajo colaborativo". El sistema integra los aportes y genera el PDF oficial listo para firma.',
        icono='C', border_color=(140, 60, 50), fill_color=(253, 246, 246)
    )

    pdf.seccion('3. Tranquilidad y Cero Perdidas (Red de Seguridad)')
    pdf.set_font('Helvetica', '', 8.5)
    pdf.set_text_color(*TEXT_DARK)
    pdf.multi_cell(184, 4.3, limpiar(
        '- Autoguardado silencioso: Cada 15 segundos en segundo plano.\n'
        '- "Continuar donde me quede": Reanuda el borrador exacto con un solo clic.\n'
        '- Respaldo local .json: Cada maestro puede descargar su archivo propio con 1 clic para total certeza.\n'
        '- Experiencia movil (Android e iOS): Optimizado para telefonos y tabletas con toolbar inferior nativo.'
    ))
    pdf.ln(2)

    # Mensaje de cierre a directores
    pdf.set_fill_color(*NAVY)
    pdf.rect(16, pdf.get_y(), 184, 15, 'F')
    pdf.set_xy(18, pdf.get_y() + 2)
    pdf.set_font('Helvetica', 'I', 8.5)
    pdf.set_text_color(*WHITE)
    pdf.multi_cell(180, 4, limpiar(
        '"Un director no debe ser un recolector de formatos. Un maestro no debe ser un capturista de datos. '
        'La tecnologia debe asumir la rutina para que el equipo dedique su energia a lo verdaderamente humano: transformar vidas en el aula."'
    ))

    pdf.output(str(ruta))
    print(f'Folleto generado en: {ruta}')


# ==============================================================================
# 2. INFOGRAFIA EJECUTIVA (Vertical de Alto Impacto Visual)
# ==============================================================================
class InfografiaPDF(FPDF):
    def __init__(self):
        super().__init__(orientation='P', unit='mm', format='Letter')
        self.set_auto_page_break(auto=False)
        self.set_margins(14, 14, 14)


def crear_infografia(ruta):
    pdf = InfografiaPDF()
    pdf.add_page()

    # Banner superior
    pdf.set_fill_color(*NAVY)
    pdf.rect(0, 0, 216, 28, 'F')
    pdf.set_fill_color(*GOLD)
    pdf.rect(0, 28, 216, 2.5, 'F')

    pdf.set_xy(14, 5)
    pdf.set_font('Helvetica', 'B', 16)
    pdf.set_text_color(*WHITE)
    pdf.cell(188, 7, 'USAER 02-E  |  ECOSISTEMA EDUCATIVO INTEGRADO', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(220, 235, 240)
    pdf.cell(188, 6, 'Menos burocracia en pantalla · Mas acompanamiento pedagogico en el aula', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_y(34)

    # BLOQUE 1: El Gran Contraste (Antes vs Hoy)
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(*DARK_NAVY)
    pdf.cell(188, 6, 'EL GRAN CONTRASTE: EN QUE SE VA EL TIEMPO DOCENTE?', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(1)

    # Dos columnas comparativas
    y_col = pdf.get_y()
    w_col = 91

    # Columna izquierda: ANTES
    pdf.set_fill_color(253, 242, 242)
    pdf.set_draw_color(210, 80, 70)
    pdf.rect(14, y_col, w_col, 42, 'FD')
    pdf.set_xy(16, y_col + 2)
    pdf.set_font('Helvetica', 'B', 9.5)
    pdf.set_text_color(180, 40, 30)
    pdf.cell(w_col - 4, 5, 'MODELO TRADICIONAL (ISLAS)', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font('Helvetica', '', 8)
    pdf.set_text_color(*TEXT_DARK)
    items_antes = [
        '- Formatos dispersos en Word, Excel y carpetas.',
        '- Capturar nombre, CURP y escuela 5 veces por alumno.',
        '- Los antecedentes se pierden al cambiar de ciclo.',
        '- Archivos que nadie vuelve a abrir ni analizar.',
        '- Cansancio administrativo trasladado a la pantalla.'
    ]
    for it in items_antes:
        pdf.set_x(16)
        pdf.cell(w_col - 4, 4.3, limpiar(it), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Columna derecha: HOY
    pdf.set_fill_color(240, 248, 245)
    pdf.set_draw_color(35, 130, 95)
    pdf.rect(111, y_col, w_col, 42, 'FD')
    pdf.set_xy(113, y_col + 2)
    pdf.set_font('Helvetica', 'B', 9.5)
    pdf.set_text_color(20, 110, 80)
    pdf.cell(w_col - 4, 5, 'PLATAFORMA USAER 02-E (CONECTADA)', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font('Helvetica', '', 8)
    pdf.set_text_color(*TEXT_DARK)
    items_hoy = [
        '- Fuente unica de verdad: los datos se capturan una vez.',
        '- La planeacion lee automaticamente los anexos previos.',
        '- La trayectoria del alumno viaja viva en el tiempo.',
        '- Productos oficiales y PDFs generados en segundos.',
        '- Tecnologia que libera tiempo para la atencion directa.'
    ]
    for it in items_hoy:
        pdf.set_x(113)
        pdf.cell(w_col - 4, 4.3, limpiar(it), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_y(y_col + 45)

    # BLOQUE 2: Metricas de Impacto
    pdf.set_fill_color(*NAVY)
    pdf.rect(14, pdf.get_y(), 188, 22, 'F')
    y_met = pdf.get_y() + 2

    metricas = [
        ('-70%', 'Tiempo en captura repetitiva'),
        ('1 Clic', 'Para recuperar antecedentes'),
        ('15 seg', 'Autoguardado en la nube'),
        ('100%', 'Trayectoria conservada')
    ]
    ancho_m = 188 / 4
    for idx, (cifra, desc) in enumerate(metricas):
        x_m = 14 + (idx * ancho_m)
        pdf.set_xy(x_m, y_met)
        pdf.set_font('Helvetica', 'B', 13)
        pdf.set_text_color(*GOLD)
        pdf.cell(ancho_m, 6, cifra, align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_xy(x_m, y_met + 7)
        pdf.set_font('Helvetica', '', 7.5)
        pdf.set_text_color(*WHITE)
        pdf.multi_cell(ancho_m, 3.5, desc, align='C')

    pdf.set_y(y_met + 24)

    # BLOQUE 3: El Flujo en 4 Estaciones
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(*DARK_NAVY)
    pdf.cell(188, 6, 'EL FLUJO INTEGRADO EN 4 PASOS AGILES', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(1)

    pasos = [
        ('1. SELECCION INTELIGENTE', 'El docente entra con su cuenta; el padron, escuela, ciclo y trimestre se sugieren en automatico.'),
        ('2. CONEXION DE EVIDENCIA', 'Con el boton [+ Usar en borrador], traslada acuerdos de Anexos III, IV, V y actas sin teclear nada.'),
        ('3. IA DE APOYO TANGIBLE', 'Genera secuencias para Educacion Especial: Inicio (manipulable), Desarrollo (andamiaje), Cierre (evaluacion).'),
        ('4. REVISION Y ENTREGA', 'El director valida en tiempo real. Se exporta PDF oficial listo para firma y archivo escolar.')
    ]
    for num, (t_paso, d_paso) in enumerate(pasos):
        y_p = pdf.get_y()
        pdf.set_fill_color(*CARD_BG)
        pdf.set_draw_color(*BORDER_GRAY)
        pdf.rect(14, y_p, 188, 14, 'FD')
        
        # Insignia
        pdf.set_fill_color(*(NAVY if num % 2 == 0 else GOLD))
        pdf.rect(15, y_p + 1, 12, 12, 'F')
        pdf.set_xy(15, y_p + 3)
        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_text_color(*WHITE)
        pdf.cell(12, 8, str(num + 1), align='C')

        pdf.set_xy(30, y_p + 1.5)
        pdf.set_font('Helvetica', 'B', 8.5)
        pdf.set_text_color(*DARK_NAVY)
        pdf.cell(165, 4.5, t_paso, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_xy(30, y_p + 6.2)
        pdf.set_font('Helvetica', '', 7.8)
        pdf.set_text_color(*TEXT_DARK)
        pdf.cell(165, 4.5, d_paso, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        pdf.set_y(y_p + 16)

    pdf.ln(2)

    # BLOQUE 4: Colaboracion Interdisciplinaria (Las 4 Especialidades)
    pdf.set_font('Helvetica', 'B', 10.5)
    pdf.set_text_color(*DARK_NAVY)
    pdf.cell(188, 5, 'LA HISTORIA CONECTADA POR ESPECIALIDAD', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(1)

    y_esp = pdf.get_y()
    w_esp = 44.5
    roles = [
        ('Apoyo', 'Coordina el PI (XXI) y planeacion trimestral (XXIII).'),
        ('Psicologia', '5 competencias socioemocionales de Zona 001.'),
        ('Comunicacion', 'Enfoque en SAAC, lenguaje y participacion.'),
        ('Trabajo Social', 'Contexto familiar, BAP y corresponsabilidad.')
    ]
    for i, (r_tit, r_desc) in enumerate(roles):
        x_e = 14 + (i * (w_esp + 3.3))
        pdf.set_fill_color(245, 248, 250)
        pdf.set_draw_color(*BORDER_GRAY)
        pdf.rect(x_e, y_esp, w_esp, 23, 'FD')
        pdf.set_xy(x_e + 1, y_esp + 1.5)
        pdf.set_font('Helvetica', 'B', 8)
        pdf.set_text_color(*NAVY)
        pdf.cell(w_esp - 2, 4, r_tit, align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_xy(x_e + 2, y_esp + 6.5)
        pdf.set_font('Helvetica', '', 7)
        pdf.set_text_color(*TEXT_DARK)
        pdf.multi_cell(w_esp - 4, 3.4, r_desc, align='C')

    # Footer banner
    pdf.set_y(248)
    pdf.set_fill_color(*DARK_NAVY)
    pdf.rect(14, pdf.get_y(), 188, 14, 'F')
    pdf.set_xy(16, pdf.get_y() + 1.5)
    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_text_color(*GOLD)
    pdf.cell(184, 4, 'PRINCIPIO: "AUTOMATIZAR LA RUTINA; RESERVAR LO HUMANO PARA EL CRITERIO"', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_x(16)
    pdf.set_font('Helvetica', 'I', 7.5)
    pdf.set_text_color(*WHITE)
    pdf.cell(184, 4, 'USAER 02-E · Sistema disenado por y para educadores de Educacion Especial', align='C')

    pdf.output(str(ruta))
    print(f'Infografia generada en: {ruta}')


# ==============================================================================
# 3. PRESENTACION DE SLIDES (16:9 / Landscape para Proyector)
# ==============================================================================
class PresentacionPDF(FPDF):
    def __init__(self):
        super().__init__(orientation='L', unit='mm', format='Letter') # 279 x 216 mm
        self.set_auto_page_break(auto=False)
        self.set_margins(18, 18, 18)

    def slide_header(self, slide_num, total_slides=7):
        # Fondo limpio
        self.set_fill_color(*LIGHT_BG)
        self.rect(0, 0, 279, 216, 'F')
        # Franja superior
        self.set_fill_color(*NAVY)
        self.rect(0, 0, 279, 14, 'F')
        self.set_fill_color(*GOLD)
        self.rect(0, 14, 279, 2, 'F')

        self.set_xy(18, 3.5)
        self.set_font('Helvetica', 'B', 9.5)
        self.set_text_color(*WHITE)
        self.cell(120, 7, 'USAER 02-E  |  ZONA 001 EDUCACION ESPECIAL')
        self.set_xy(140, 3.5)
        self.set_font('Helvetica', '', 8.5)
        self.cell(121, 7, f'Presentacion Ejecutiva para Directores · {slide_num}/{total_slides}', align='R')

    def slide_footer(self, frase='Capturar una vez, reutilizar despues'):
        self.set_fill_color(*NAVY)
        self.rect(0, 204, 279, 12, 'F')
        self.set_xy(18, 205.5)
        self.set_font('Helvetica', 'I', 8.5)
        self.set_text_color(*WHITE)
        self.cell(243, 8, f'USAER 02-E · {frase}', align='C')


def crear_presentacion(ruta):
    pdf = PresentacionPDF()

    # SLIDE 1: PORTADA
    pdf.add_page()
    pdf.set_fill_color(*DARK_NAVY)
    pdf.rect(0, 0, 279, 216, 'F')
    pdf.set_fill_color(*GOLD)
    pdf.rect(0, 204, 279, 12, 'F')

    pdf.set_xy(25, 45)
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(*GOLD)
    pdf.cell(229, 8, 'USAER 02-E  ·  ZONA 001 EDUCACION ESPECIAL', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font('Helvetica', 'B', 24)
    pdf.set_text_color(*WHITE)
    pdf.cell(229, 14, 'De la Burocracia al Acompanamiento Pedagogico', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font('Helvetica', '', 14)
    pdf.set_text_color(210, 230, 238)
    pdf.cell(229, 9, 'Como un sistema conectado devuelve horas de valor al maestro frente a grupo', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(18)
    pdf.set_fill_color(27, 73, 88)
    pdf.rect(45, pdf.get_y(), 189, 24, 'F')
    pdf.set_xy(48, pdf.get_y() + 4)
    pdf.set_font('Helvetica', 'I', 11)
    pdf.set_text_color(*WHITE)
    pdf.cell(183, 7, '"Capturar una sola vez y reutilizar siempre:', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_x(48)
    pdf.cell(183, 7, 'La tecnologia debe liberar tiempo para ensenar, no crear una oficina digital."', align='C')

    # SLIDE 2: EL PROBLEMA REAL
    pdf.add_page()
    pdf.slide_header(2)
    pdf.set_xy(18, 25)
    pdf.set_font('Helvetica', 'B', 18)
    pdf.set_text_color(*DARK_NAVY)
    pdf.cell(0, 10, '1. La Pregunta Incomoda: Digitalizar Burocracia o Innovar?', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font('Helvetica', '', 11)
    pdf.set_text_color(*SLATE)
    pdf.cell(0, 6, 'Pasar un formato de papel a un archivo de Word no es innovar; es trasladar el cansancio a la pantalla.', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(6)

    # 3 Cajas comparativas
    w_box = 76
    y_box = pdf.get_y()
    boxes = [
        ('El Dolor del Maestro', 'Horas frente al teclado tecleando el mismo nombre, CURP y diagnostico en 4 formatos distintos.', (220, 60, 50)),
        ('Los "Formatos Isla"', 'Documentos aislados que se entregan a direccion pero nadie vuelve a leer ni conectar pedagogicamente.', (196, 147, 57)),
        ('El Alumno sin Historia', 'El alumno reinicia su expediente cada ciclo escolar como si nadie lo hubiera conocido antes.', (27, 73, 88))
    ]
    for idx, (b_tit, b_desc, b_col) in enumerate(boxes):
        x_b = 18 + (idx * 83)
        pdf.set_fill_color(*WHITE)
        pdf.set_draw_color(*b_col)
        pdf.set_line_width(0.6)
        pdf.rect(x_b, y_box, w_box, 90, 'FD')
        
        pdf.set_fill_color(*b_col)
        pdf.rect(x_b, y_box, w_box, 14, 'F')
        pdf.set_xy(x_b + 2, y_box + 3.5)
        pdf.set_font('Helvetica', 'B', 10.5)
        pdf.set_text_color(*WHITE)
        pdf.cell(w_box - 4, 7, b_tit, align='C')

        pdf.set_xy(x_b + 5, y_box + 22)
        pdf.set_font('Helvetica', '', 10)
        pdf.set_text_color(*TEXT_DARK)
        pdf.multi_cell(w_box - 10, 6, b_desc)

    pdf.slide_footer('Identificar la burocracia repetitiva es el primer paso para liberar al docente')

    # SLIDE 3: LA FILOSOFÍA CENTRAL
    pdf.add_page()
    pdf.slide_header(3)
    pdf.set_xy(18, 25)
    pdf.set_font('Helvetica', 'B', 18)
    pdf.set_text_color(*DARK_NAVY)
    pdf.cell(0, 10, '2. Los Tres Pilares de la Plataforma USAER 02-E', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font('Helvetica', '', 11)
    pdf.set_text_color(*SLATE)
    pdf.cell(0, 6, 'Principios de diseno pensados para respetar la dignidad profesional del maestro.', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(6)

    y_pilar = pdf.get_y()
    pilares = [
        ('Pilar 1: Fuente Unica de Verdad', 'Capturar una sola vez. Si un dato ya existe en la escuela o en el expediente, la plataforma lo ofrece automaticamente. Prohibido volver a capturar.'),
        ('Pilar 2: Automatizar la Rutina', 'Que el sistema arme los formatos, calcule ciclos y organice tablas. Dejemos a las personas para lo que requiere criterio, empatia y decision.'),
        ('Pilar 3: Trayectoria Educativa Viva', 'Los modulos no son tramites; son ventanas hacia la misma historia. El avance del alumno se conserva para aprender de el a lo largo de los anos.')
    ]
    for idx, (p_tit, p_desc) in enumerate(pilares):
        y_pos = y_pilar + (idx * 32)
        pdf.set_fill_color(*CARD_BG)
        pdf.set_draw_color(*(NAVY if idx == 0 else (GOLD if idx == 1 else DARK_NAVY)))
        pdf.set_line_width(0.5)
        pdf.rect(18, y_pos, 243, 27, 'FD')

        pdf.set_xy(24, y_pos + 3)
        pdf.set_font('Helvetica', 'B', 12)
        pdf.set_text_color(*NAVY)
        pdf.cell(230, 6, p_tit, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        pdf.set_xy(24, y_pos + 10)
        pdf.set_font('Helvetica', '', 9.8)
        pdf.set_text_color(*TEXT_DARK)
        pdf.multi_cell(230, 5, p_desc)

    pdf.slide_footer('La tecnologia debe simplificar el trabajo docente, no complicarlo')

    # SLIDE 4: CASO PRÁCTICO 1 (BOTÓN USAR EN BORRADOR)
    pdf.add_page()
    pdf.slide_header(4)
    pdf.set_xy(18, 25)
    pdf.set_font('Helvetica', 'B', 18)
    pdf.set_text_color(*DARK_NAVY)
    pdf.cell(0, 10, '3. Ejemplo Practico 1: El Boton [+ Usar en borrador]', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font('Helvetica', '', 11)
    pdf.set_text_color(*SLATE)
    pdf.cell(0, 6, 'Eliminando el copiado y pegado manual de antecedentes entre carpetas.', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(8)

    y_demo = pdf.get_y()
    # Caja antes
    pdf.set_fill_color(253, 245, 245)
    pdf.set_draw_color(210, 80, 70)
    pdf.rect(18, y_demo, 115, 85, 'FD')
    pdf.set_xy(22, y_demo + 4)
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(180, 40, 30)
    pdf.cell(107, 7, 'EL METODO ANTERIOR (15 min por alumno)', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font('Helvetica', '', 9.5)
    pdf.set_text_color(*TEXT_DARK)
    pdf.set_x(22)
    pdf.multi_cell(107, 5.5, limpiar(
        '1. Buscar la carpeta del ciclo anterior.\n'
        '2. Abrir el Anexo 3 o el Anexo 4 en papel o Word.\n'
        '3. Copiar a mano las BAP y los acuerdos de visitas.\n'
        '4. Pegarlo en la nueva planeacion trimestral.\n'
        '5. Riesgo de errores y horas perdidas de captura.'
    ))

    # Caja ahora
    pdf.set_fill_color(240, 248, 245)
    pdf.set_draw_color(35, 130, 95)
    pdf.rect(146, y_demo, 115, 85, 'FD')
    pdf.set_xy(150, y_demo + 4)
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(20, 110, 80)
    pdf.cell(107, 7, 'CON LA PLATAFORMA (1 segundo)', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font('Helvetica', '', 9.5)
    pdf.set_text_color(*TEXT_DARK)
    pdf.set_x(150)
    pdf.multi_cell(107, 5.5, limpiar(
        '1. Al elegir al alumno, el sistema reune sus antecedentes.\n'
        '2. Muestra acuerdos vigentes de Anexos III, IV, V y actas.\n'
        '3. La maestra pulsa [+ Usar en borrador].\n'
        '4. El texto se incorpora de inmediato a sus notas.\n'
        '5. Cero recaptura. 100% de coherencia historica.'
    ))

    pdf.slide_footer('La informacion ya existe; solo necesitabamos conectarla')

    # SLIDE 5: CASO PRÁCTICO 2 (PLANEACIÓN EN 3 MOMENTOS CON IA)
    pdf.add_page()
    pdf.slide_header(5)
    pdf.set_xy(18, 25)
    pdf.set_font('Helvetica', 'B', 18)
    pdf.set_text_color(*DARK_NAVY)
    pdf.cell(0, 10, '4. Ejemplo Practico 2: Planeacion Real para Educacion Especial', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font('Helvetica', '', 11)
    pdf.set_text_color(*SLATE)
    pdf.cell(0, 6, 'Inteligencia Artificial orientada a la practica docente, no a generar parrafos vacios.', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(6)

    # 3 Tarjetas de los 3 momentos
    y_mom = pdf.get_y()
    w_mom = 76
    momentos = [
        ('1. INICIO TANGIBLE', 'Detonador Concreto', 'Material manipulable, imagenes reales o preguntas directas vinculadas al entorno del alumno. Cero textos teoricos abstractos.', NAVY),
        ('2. DESARROLLO', 'Andamiaje Multinivel', 'Modelado explicito, apoyos visuales, consignas segmentadas paso a paso y tiempos adaptados al ritmo de aprendizaje.', GOLD),
        ('3. CIERRE FORMATIVO', 'Evaluacion Observable', 'Evidencia tangible: senalar, clasificar, verbalizar o producir un resultado concreto. Sin pruebas estandarizadas rigidas.', (35, 130, 95))
    ]
    for idx, (m_num, m_sub, m_desc, m_col) in enumerate(momentos):
        x_m = 18 + (idx * 83)
        pdf.set_fill_color(*WHITE)
        pdf.set_draw_color(*m_col)
        pdf.set_line_width(0.6)
        pdf.rect(x_m, y_mom, w_mom, 85, 'FD')

        pdf.set_fill_color(*m_col)
        pdf.rect(x_m, y_mom, w_mom, 16, 'F')
        pdf.set_xy(x_m + 2, y_mom + 2)
        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_text_color(*WHITE)
        pdf.cell(w_mom - 4, 6, m_num, align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_xy(x_m + 2, y_mom + 8)
        pdf.set_font('Helvetica', 'I', 8)
        pdf.cell(w_mom - 4, 5, m_sub, align='C')

        pdf.set_xy(x_m + 5, y_mom + 25)
        pdf.set_font('Helvetica', '', 9.5)
        pdf.set_text_color(*TEXT_DARK)
        pdf.multi_cell(w_mom - 10, 5.8, m_desc)

    pdf.slide_footer('La IA propone estrategias pedagogicas de aula; el maestro decide con su criterio profesional')

    # SLIDE 6: CASO PRÁCTICO 3 (TRABAJO COLABORATIVO)
    pdf.add_page()
    pdf.slide_header(6)
    pdf.set_xy(18, 25)
    pdf.set_font('Helvetica', 'B', 18)
    pdf.set_text_color(*DARK_NAVY)
    pdf.cell(0, 10, '5. Ejemplo Practico 3: Interdisciplina sin Colisiones', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font('Helvetica', '', 11)
    pdf.set_text_color(*SLATE)
    pdf.cell(0, 6, 'La pestana "Trabajo Colaborativo": integracion perfecta entre Apoyo y Paradocentes.', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(6)

    y_int = pdf.get_y()
    w_int = 117
    # Caja izquierda: Maestra de apoyo
    pdf.set_fill_color(*CARD_BG)
    pdf.set_draw_color(*NAVY)
    pdf.rect(18, y_int, w_int, 85, 'FD')
    pdf.set_xy(22, y_int + 4)
    pdf.set_font('Helvetica', 'B', 11.5)
    pdf.set_text_color(*NAVY)
    pdf.cell(w_int - 8, 6, 'MAESTRA DE APOYO (Coordinadora del PI)', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font('Helvetica', '', 9.2)
    pdf.set_text_color(*TEXT_DARK)
    pdf.set_x(22)
    pdf.multi_cell(w_int - 8, 5.2, limpiar(
        '- Es la autora y coordinadora del Plan de Intervencion (XXI).\n'
        '- Define los objetivos curriculares y la dosificacion de aula.\n'
        '- No tiene que perseguir a los especialistas pidiendo hojas sueltas.\n'
        '- Ve las aportaciones de Psicologia, Comunicacion y Trabajo Social integradas en su propio documento.'
    ))

    # Caja derecha: Paradocentes
    pdf.set_fill_color(*CARD_BG)
    pdf.set_draw_color(*GOLD)
    pdf.rect(144, y_int, w_int, 85, 'FD')
    pdf.set_xy(148, y_int + 4)
    pdf.set_font('Helvetica', 'B', 11.5)
    pdf.set_text_color(*GOLD)
    pdf.cell(w_int - 8, 6, 'EQUIPO PARADOCENTE (Aportaciones de Area)', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font('Helvetica', '', 9.2)
    pdf.set_text_color(*TEXT_DARK)
    pdf.set_x(148)
    pdf.multi_cell(w_int - 8, 5.2, limpiar(
        '- Entran a la pestana "Trabajo Colaborativo".\n'
        '- Psicologia: Conducta, autorregulacion y las 5 competencias.\n'
        '- Comunicacion: Canal comunicativo, SAAC y apoyos visuales.\n'
        '- Trabajo Social: Compromisos familiares y redes de apoyo.\n'
        '- Su aportacion queda firmada a su nombre en el PDF oficial.'
    ))

    pdf.slide_footer('Un solo documento oficial ensamblado automaticamente con la firma de cada especialista')

    # SLIDE 7: CIERRE Y COMPROMISO
    pdf.add_page()
    pdf.slide_header(7)
    pdf.set_xy(18, 30)
    pdf.set_font('Helvetica', 'B', 20)
    pdf.set_text_color(*DARK_NAVY)
    pdf.cell(0, 10, 'La Promesa a los Directores de la Zona Escolar', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(5)

    # Gran cita central
    y_cita = 48
    pdf.set_fill_color(*NAVY)
    pdf.rect(25, y_cita, 229, 58, 'F')
    pdf.set_xy(30, y_cita + 8)
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(*GOLD)
    pdf.cell(219, 8, '"Un director no debe ser un recolector de papeles.', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(*WHITE)
    pdf.cell(219, 8, 'Un maestro no debe ser un capturista de datos."', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)
    pdf.set_font('Helvetica', 'I', 11.5)
    pdf.set_text_color(220, 235, 240)
    pdf.cell(219, 7, 'La plataforma USAER 02-E existe para que la tecnologia cargue la rutina', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(219, 7, 'y nosotros nos dediquemos a lo que ninguna maquina puede hacer: transformar vidas.', align='C')

    pdf.set_y(128)
    pdf.set_font('Helvetica', 'B', 13)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 8, 'En resumen: Que gana la escuela regular y la USAER?', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)
    pdf.set_font('Helvetica', '', 11)
    pdf.set_text_color(*TEXT_DARK)
    pdf.cell(0, 7, '1. Maestros con mas tiempo de atencion directa   |   2. Expedientes completos y trazables   |   3. Revision agil sin burocracia', align='C')

    pdf.slide_footer('Gracias por su liderazgo pedagogico · USAER 02-E')

    pdf.output(str(ruta))
    print(f'Presentacion generada en: {ruta}')


def generar_todo():
    carpeta_docs = Path(__file__).resolve().parents[1] / 'docs'
    carpeta_escritorio = Path(r'C:\Users\edgar\OneDrive\Escritorio')

    archivos = {
        'folleto': ('Folleto_Ejecutivo_USAER_02E.pdf', crear_folleto),
        'infografia': ('Infografia_USAER_02E.pdf', crear_infografia),
        'presentacion': ('Presentacion_Directores_USAER_02E.pdf', crear_presentacion)
    }

    for clave, (nombre, func) in archivos.items():
        destino_docs = carpeta_docs / nombre
        func(destino_docs)
        if carpeta_escritorio.exists():
            import shutil
            destino_escritorio = carpeta_escritorio / nombre
            shutil.copy2(destino_docs, destino_escritorio)
            print(f'Copiado al Escritorio: {destino_escritorio}')


if __name__ == '__main__':
    generar_todo()

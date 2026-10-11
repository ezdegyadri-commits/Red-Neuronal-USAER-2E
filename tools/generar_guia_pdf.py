"""Generador de la Guía Rápida de Planeación para el Personal de USAER 02-E."""
from pathlib import Path
from fpdf import FPDF

class GuiaPDF(FPDF):
    def __init__(self):
        super().__init__(orientation='P', unit='mm', format='Letter')
        self.set_auto_page_break(auto=True, margin=15)
        self.set_margins(16, 16, 16)

    def header(self):
        # Header banner institucional
        self.set_fill_color(27, 73, 88) # Primary Navy #1B4958
        self.rect(0, 0, 216, 16, 'F')
        self.set_fill_color(196, 147, 57) # Gold Accent #C49339
        self.rect(0, 16, 216, 2, 'F')
        
        self.set_xy(16, 4)
        self.set_font('Helvetica', 'B', 10)
        self.set_text_color(255, 255, 255)
        self.cell(100, 8, 'USAER 02-E  |  ZONA 001 EDUCACIÓN ESPECIAL', align='L')
        self.set_xy(100, 4)
        self.set_font('Helvetica', '', 9)
        self.cell(100, 8, 'SISTEMA INTEGRADO DE PLANEACIÓN PEDAGÓGICA', align='R')
        self.ln(16)

    def footer(self):
        self.set_y(-12)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(120, 140, 150)
        self.cell(0, 8, f'USAER 02-E · Plataforma Educativa Integrada · Página {self.page_no()}', align='C')

    def seccion_titulo(self, texto, icono=''):
        self.ln(3)
        self.set_font('Helvetica', 'B', 12)
        self.set_text_color(27, 73, 88)
        self.cell(0, 7, f'{icono} {texto}'.strip(), ln=True)
        self.set_draw_color(196, 147, 57)
        self.set_line_width(0.6)
        self.line(self.get_x(), self.get_y(), self.get_x() + 184, self.get_y())
        self.ln(3)

    def tarjeta(self, titulo, subtitulo, items, color_borde=(27, 73, 88), bg=(248, 250, 251)):
        x = self.get_x()
        y = self.get_y()
        w = 184
        
        # Guardar posición para calcular altura
        self.set_fill_color(*bg)
        self.set_draw_color(*color_borde)
        self.set_line_width(0.3)
        
        # Encabezado de la tarjeta
        self.set_font('Helvetica', 'B', 10)
        self.set_text_color(*color_borde)
        
        # Primero calculamos texto
        self.set_x(x + 4)
        self.cell(w - 8, 6, titulo, ln=True)
        
        if subtitulo:
            self.set_font('Helvetica', 'I', 8.5)
            self.set_text_color(90, 110, 120)
            self.set_x(x + 4)
            self.multi_cell(w - 8, 4.5, subtitulo)
            self.ln(1)
            
        self.set_font('Helvetica', '', 8.5)
        self.set_text_color(30, 45, 50)
        for item in items:
            self.set_x(x + 4)
            self.cell(4, 5, chr(149), align='L') # bullet
            self.multi_cell(w - 12, 4.8, item)
            
        y_fin = self.get_y() + 2
        alto = y_fin - y
        
        # Dibujar rectángulo alrededor
        self.rect(x, y, w, alto, 'D')
        self.set_y(y_fin + 3)

def generar():
    pdf = GuiaPDF()
    pdf.add_page()
    
    # Título Principal
    pdf.set_font('Helvetica', 'B', 16)
    pdf.set_text_color(18, 51, 62)
    pdf.cell(0, 8, 'Guía Rápida de Planeación Ágil', ln=True, align='C')
    
    pdf.set_font('Helvetica', '', 9.5)
    pdf.set_text_color(93, 114, 123)
    pdf.cell(0, 5, 'Objetivo: Hacer la planeación más rápida, útil y conectada, reduciendo la carga burocrática.', ln=True, align='C')
    pdf.ln(3)
    
    # Principio Rector (Banner destacado)
    pdf.set_fill_color(232, 242, 245)
    pdf.set_draw_color(27, 73, 88)
    pdf.rect(16, pdf.get_y(), 184, 11, 'FD')
    pdf.set_xy(18, pdf.get_y() + 1.5)
    pdf.set_font('Helvetica', 'B', 8.5)
    pdf.set_text_color(27, 73, 88)
    pdf.cell(180, 4, 'PRINCIPIO CLAVE: "CAPTURAR UNA VEZ, REUTILIZAR DESPUÉS"', ln=True)
    pdf.set_x(18)
    pdf.set_font('Helvetica', '', 8)
    pdf.set_text_color(30, 50, 60)
    pdf.cell(180, 4, 'La plataforma ya conoce expedientes, antecedentes y anexos de tus alumnos. No vuelvas a capturar lo que la USAER ya sabe.')
    pdf.ln(7)

    # SECCIÓN 1: Flujo en 3 Pasos
    pdf.seccion_titulo('El Recorrido en 3 Pasos (Para todo el equipo)')
    
    pdf.set_font('Helvetica', 'B', 9.5)
    pdf.set_text_color(196, 147, 57)
    pdf.cell(0, 5, 'PASO 1: ¿A quién planeo?', ln=True)
    pdf.set_font('Helvetica', '', 8.5)
    pdf.set_text_color(30, 45, 50)
    pdf.multi_cell(184, 4.5, 
        '1. Inicia sesión con tu cuenta personal (nunca compartida).\n'
        '2. Si ya tenías un borrador iniciado, pulsa en [ Continuar donde me quedé ] para retomarlo de inmediato.\n'
        '3. Para uno nuevo: selecciona tu escuela y marca tus alumnos. El ciclo y trimestre se sugieren en automático.'
    )
    pdf.ln(1)

    pdf.set_font('Helvetica', 'B', 9.5)
    pdf.set_text_color(196, 147, 57)
    pdf.cell(0, 5, 'PASO 2: Preparar con IA y Conexión Automática', ln=True)
    pdf.set_font('Helvetica', '', 8.5)
    pdf.set_text_color(30, 45, 50)
    pdf.multi_cell(184, 4.5, 
        '1. Antecedentes automáticos: Revisa lo ya documentado (Anexos III, IV, V y visitas). Si un acuerdo te sirve, pulsa [ + Usar en borrador ] para transferirlo sin copiar y pegar.\n'
        '2. Referentes oficiales: Selecciona campo formativo y busca el PDA. Agrega tu contextualización y ajustes.\n'
        '3. Propuesta con IA: Marca la casilla de revisión y pulsa [ Proponer actividades con IA ]. La propuesta te dará una secuencia concreta en 3 momentos para educación especial (Inicio tangible, Desarrollo con andamiaje y Cierre observable).'
    )
    pdf.ln(1)

    pdf.set_font('Helvetica', 'B', 9.5)
    pdf.set_text_color(196, 147, 57)
    pdf.cell(0, 5, 'PASO 3: Guardar, Descargar y Enviar', ln=True)
    pdf.set_font('Helvetica', '', 8.5)
    pdf.set_text_color(30, 45, 50)
    pdf.multi_cell(184, 4.5, 
        '1. Autoguardado: La plataforma guarda en segundo plano cada 15 segundos mientras redactas.\n'
        '2. Vista previa: Pulsa [ Preparar PDF ] o [ Ver PDF ] cuando quieras revisar el formato terminado.\n'
        '3. Envío: Cuando esté lista, pulsa [ Enviar a Dirección ]. No necesitas imprimir ni mandar por correo.'
    )
    pdf.ln(2)

    # RED DE SEGURIDAD
    pdf.seccion_titulo('Red de Seguridad (Cero pérdidas ante cortes de Wi-Fi o luz)')
    pdf.set_font('Helvetica', '', 8.5)
    pdf.set_text_color(30, 45, 50)
    pdf.multi_cell(184, 4.5,
        '- Respaldo local en 1 clic: Pulsa [ Descargar respaldo editable ] al pie de página para tener tu archivo .json.\n'
        '- Si se cierra la ventana o se desconecta el internet: Al volver a entrar, abre [ Continuar donde me quedé ] o entra a la pestaña "Recuperar documentos" para restaurar tu archivo .json en 2 segundos.\n'
        '- Ningún trabajo previo se borra: Los borradores son aditivos y seguros en la nube.'
    )

    # PÁGINA 2: ESPECÍFICO POR FUNCIÓN
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 15)
    pdf.set_text_color(18, 51, 62)
    pdf.cell(0, 8, 'Tu Ruta Específica según tu Función', ln=True, align='C')
    pdf.ln(2)

    # 1. Maestra de Apoyo
    pdf.tarjeta(
        '1. MAESTRAS DE APOYO (Aprendizaje)',
        'Coordina el Plan de Intervención (XXI) y la Planeación Trimestral de aula (XXIII)',
        [
            'Atención individual: Selecciona al alumno con IEPP y elige "Plan de Intervención" (XXI). Es un plan anual o multianual donde los especialistas aportarán desde Trabajo Colaborativo.',
            'Atención grupal: Elige a los alumnos del grupo para su planeación trimestral (XXIII). Si incluyes a un alumno con atención individual en una sesión grupal, marca la casilla correspondiente.',
            'Dosificación ágil: Diseña la secuencia con Inicio (manipulable), Desarrollo (andamiaje) y Cierre (evaluación observable). Evita redactar párrafos burocráticos extensos; prioriza acciones concretas.'
        ],
        color_borde=(27, 73, 88), bg=(245, 249, 250)
    )

    # 2. Psicología
    pdf.tarjeta(
        '2. PSICOLOGÍA',
        'Planeación trimestral (XXIII) y aportaciones socioemocionales al Plan Individual',
        [
            '5 Competencias de Zona 001: Selecciona las competencias a trabajar (Autoconciencia, Autorregulación, Conciencia social, Relaciones interpersonales o Toma de decisiones responsables).',
            'Sesiones por subgrupos: Registra fecha, contexto (aula regular, aula de apoyo) y apoyos específicos.',
            'Aporte al Plan de Intervención (XXI): Ve a la pestaña "Trabajo colaborativo", elige al alumno y redacta tus sugerencias conductuales y emocionales. Tu aporte se firma con tu nombre y enriquece el documento maestro.'
        ],
        color_borde=(42, 100, 120), bg=(245, 249, 250)
    )

    # 3. Comunicación
    pdf.tarjeta(
        '3. COMUNICACIÓN',
        'Planeación trimestral (XXIII) con énfasis en SAAC, lenguaje y participación',
        [
            'Canal comunicativo: Define si la intervención es oral, con Sistemas Aumentativos y Alternativos de Comunicación (SAAC), apoyos pictográficos o lectoescritura adaptada.',
            'Enfoque en el aula: Prioriza actividades que permitan al alumno comunicarse con sus compañeros y docentes.',
            'Aporte al Plan de Intervención (XXI): En "Trabajo colaborativo", incorpora las recomendaciones de comunicación que la maestra de apoyo y la maestra de grupo aplicarán en el día a día.'
        ],
        color_borde=(196, 147, 57), bg=(254, 250, 242)
    )

    # 4. Trabajo Social
    pdf.tarjeta(
        '4. TRABAJO SOCIAL',
        'Planeación (XXV) de barreras de contexto, apoyos sociofamiliares y redes',
        [
            'Formato XXV: Registra las BAP del contexto familiar, escolar y comunitario, junto con compromisos de corresponsabilidad.',
            'Visitas y acuerdos: Reutiliza antecedentes de visitas domiciliarias o acuerdos escolares sin volver a capturarlos.',
            'Aporte al Plan de Intervención (XXI): Desde "Trabajo colaborativo", integra los apoyos de la familia, becas o canalizaciones institucionales.'
        ],
        color_borde=(140, 60, 50), bg=(253, 246, 246)
    )

    # 5. Dirección
    pdf.tarjeta(
        '5. DIRECCIÓN (Revisión y Acompañamiento)',
        'Monitoreo formativo sin burocracia ni intermediación técnica manual',
        [
            'Pestaña "Revisión directiva": Consulta entregas en tiempo real por escuela y docente.',
            'Retroalimentación con criterio: Revisa los documentos sin reescribir el trabajo docente.',
            'Validación en 1 clic: Devuelve con observaciones constructivas o valida el documento para autorizar su archivo.'
        ],
        color_borde=(30, 60, 70), bg=(245, 248, 250)
    )

    # Guardar en archivo
    salida = Path(__file__).resolve().parents[1] / 'docs' / 'Guia_Rapida_Planeacion_USAER_02E.pdf'
    salida.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(salida))
    print(f'PDF generado exitosamente en: {salida}')
    return salida

if __name__ == '__main__':
    generar()

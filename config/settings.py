import os

PAGE_TITLE = "USAER | Gestión Integral"
SERVICE_NAME = "USAER 02E"
SCHOOL_YEAR = "2026 – 2027"
FOLDER_ID_MAESTRO = "1btFuNK8l9BI5C2s3-Q0_RZBZkUOBhvtr"
URL_SPREADSHEET_MAESTRO = "https://docs.google.com/spreadsheets/d/15hEvBOkaUvUFvTPx38yn8D_O6zWpkDm6ReiQbNK3ewc"
URL_SPREADSHEET_RESPUESTAS_PERSONAL = "https://docs.google.com/spreadsheets/d/1wBeKwB9nwu-Rfdw5zzn9OXIxn32Gze2M44w5Ee6Ppho"
HOJA_RESPUESTAS_PERSONAL = "Respuestas de formulario 1"
def secret_or_default(name, default):
    """Lee una variable opcional sin importar Streamlit durante el arranque."""
    return os.environ.get(name, default)

GEMINI_MODEL = secret_or_default("GEMINI_MODEL", "gemini-3.6-flash")

ESCUELAS_USAER = {
    "Damián Carmona": "ESC-001",
    "Ichcaanziho": "ESC-002",
    "Gregorio Torres Quintero": "ESC-003",
    "Remigio Aguilar Sosa": "ESC-004",
    "Elvira Parra Ávila": "ESC-005",
    "Manuel Sarrado": "ESC-006",
    "Domingo Solís Rodríguez": "ESC-007",
    "Quintana Roo": "ESC-008",
}

BAP_ITEMS = [
    "El salón de clases cuenta con áreas de trabajo delimitadas (higiene, rincón de lectura, área de material didáctico).",
    "El docente se asegura de que el material didáctico con que cuenta en el aula sea pertinente a las características de todos sus alumnos.",
    "El docente emplea los materiales de que dispone en el aula para asegurar el aprendizaje significativo de todos los alumnos.",
    "El docente se asegura de que, en el salón de clases, el material didáctico (material concreto, libros, cuentos, fichas, etc.) sea accesible para todos.",
    "El docente contempla en la planeación las ayudas necesarias en las actividades de acuerdo con los ritmos y estilos de aprendizaje, para desarrollar el potencial de cada uno de los alumnos.",
    "El docente dedica el tiempo suficiente para motivar a todos los alumnos en su aprendizaje, antes, durante y después de las actividades.",
    "El docente indaga y toma en cuenta el conocimiento previo que los alumnos tienen sobre el tema que trata la actividad antes de abordarlo.",
    "El docente propicia el trabajo colaborativo.",
    "El docente realiza una evaluación continua y formativa, es decir, mediante las actividades diarias y tareas, que le permiten conocer los avances de sus alumnos.",
    "El docente realiza las evaluaciones tomando en cuenta las características de los alumnos.",
    "El docente diversifica la metodología para favorecer el logro de los aprendizajes esperados de los alumnos.",
    "El docente diseña actividades que permitan la accesibilidad de los aprendizajes esperados de los alumnos y mejoren el nivel de logro.",
    "El docente propicia el respeto y la empatia en las relaciones entre él y sus alumnos.",
    "El docente realiza actividades para fomentar la convivencia sana y pacífica entre los alumnos (respeto, compañerismo, ayuda mutua, práctica de valores, disciplina, otros).",
    "El docente trabaja de manera colaborativa con el personal de la escuela regular y de educación especial para favorecer el aprendizaje y la participación de los estudiantes con necesidades educativas específicas."
]

BAP_FRECUENCIAS = ["Nunca", "Pocas veces", "Muchas veces", "Siempre"]

ANEXO4_FIELDS = [
    "ID_Anexo4", "Nombre_Alumno", "Grado_Grupo", "Escuela", "Servicio_EE",
    "Sugerencias_Area", "Fecha_Elaboracion", "Motivo", "Fecha_Seguimiento",
    "Sugerencias", "Nivel_Cumplimiento_Resultados", "Quien_Brinda_Sugerencias",
    # Additive keys: existing rows and columns are preserved; these fields
    # link suggestions to a unique student and allow reversible removal.
    "ID_Alumno", "Estado"
]

WORKFLOW = [
    "CAPTURADA", "ANALIZADA", "SUGERENCIA GENERADA", "REVISIÓN HUMANA",
    "APROBADA", "APLICADA", "SEGUIMIENTO", "EVALUADA", "CERRADA"
]

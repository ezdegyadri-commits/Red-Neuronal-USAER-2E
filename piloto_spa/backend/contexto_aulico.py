"""Instrumento áulico original del Anexo III, integrado en la guía grupal."""
ITEMS = [
    "1. El salón de clases cuenta con áreas de trabajo delimitadas (higiene, rincón de lectura, área de material didáctico).",
    "2. El docente se asegura de que el material didáctico con que cuenta en el aula sea pertinente a las características de todos sus alumnos.",
    "3. El docente emplea los materiales de que dispone en el aula para asegurar el aprendizaje significativo de todos los alumnos.",
    "4. El docente se asegura de que, en el salón de clases, el material didáctico (material concreto, libros, cuentos, fichas, etc.) sea accesible para todos.",
    "5. El docente contempla en la planeación las ayudas necesarias en las actividades de acuerdo con los ritmos y estilos de aprendizaje, para desarrollar el potencial de cada uno de los alumnos.",
    "6. El docente dedica el tiempo suficiente para motivar a todos los alumnos en su aprendizaje, antes, durante y después de las actividades.",
    "7. El docente indaga y toma en cuenta el conocimiento previo que los alumnos tienen sobre el tema que trata la actividad antes de abordarlo.",
    "8. El docente propicia el trabajo colaborativo.",
    "9. El docente realiza una evaluación continua y formativa, es decir, mediante las actividades diarias y tareas, que le permiten conocer los avances de sus alumnos.",
    "10. El docente realiza las evaluaciones tomando en cuenta las características de los alumnos.",
    "11. El docente diversifica la metodología para favorecer el logro de los aprendizajes esperados de los alumnos.",
    "12. El docente diseña actividades que permitan la accesibilidad de los aprendizajes esperados de los alumnos y mejoren el nivel de logro.",
    "13. El docente propicia el respeto y la empatia en las relaciones entre él y sus alumnos.",
    "14. El docente realiza actividades para fomentar la convivencia sana y pacífica entre los alumnos (respeto, compañerismo, ayuda mutua, práctica de valores, disciplina, otros).",
    "15. El docente trabaja de manera colaborativa con el personal de la escuela regular y de educación especial para favorecer el aprendizaje y la participación de los estudiantes con necesidades educativas específicas."
]


from datetime import date

from fastapi import HTTPException

FRECUENCIAS = ("Siempre", "Muchas veces", "Pocas veces", "Nunca")


def validar(valor, autor):
    if not isinstance(valor, dict) or set(valor) - {"fecha", "observaciones", "respuestas", "autor"}:
        raise HTTPException(422, "Captura de contexto inválida.")
    fecha = valor.get("fecha", "")
    try:
        if fecha:
            date.fromisoformat(fecha)
    except (TypeError, ValueError):
        raise HTTPException(422, "Indica una fecha válida para la observación.") from None
    observaciones = valor.get("observaciones", "")
    if not isinstance(observaciones, str) or len(observaciones) > 12000:
        raise HTTPException(422, "Las observaciones superan el espacio del instrumento.")
    respuestas = valor.get("respuestas", {})
    if not isinstance(respuestas, dict) or set(respuestas) - {f"Item_{i+1}" for i in range(len(ITEMS))}:
        raise HTTPException(422, "Los reactivos no corresponden al Anexo III.")
    salida = {}
    for clave, fila in respuestas.items():
        if not isinstance(fila, dict) or set(fila) - {"frecuencia", "orientacion", "observacion", "pregunta"}:
            raise HTTPException(422, "Respuesta del instrumento inválida.")
        frecuencia = fila.get("frecuencia", "")
        observacion = fila.get("observacion", "")
        orientacion = fila.get("orientacion", False)
        if (frecuencia not in ("", *FRECUENCIAS) or not isinstance(orientacion, bool)
                or not isinstance(observacion, str) or len(observacion) > 2000):
            raise HTTPException(422, "Frecuencia u observación del instrumento inválida.")
        pregunta = ITEMS[int(clave.split("_")[1])-1]
        if fila.get("pregunta", pregunta) != pregunta:
            raise HTTPException(422, "La pregunta difiere del instrumento original.")
        if not frecuencia and (orientacion or observacion.strip()):
            raise HTTPException(422, "Selecciona la frecuencia del reactivo observado.")
        if frecuencia:
            salida[clave] = dict(pregunta=pregunta, frecuencia=frecuencia,
                                 orientacion=orientacion, observacion=observacion)
    if (salida or observaciones.strip()) and not fecha:
        raise HTTPException(422, "Indica la fecha de la observación.")
    return dict(fecha=fecha, observaciones=observaciones, respuestas=salida, autor=autor)


def resumen(captura):
    partes = [captura.get("observaciones", "")]
    partes.extend(f"{r['pregunta']} Frecuencia: {r['frecuencia']}. {r.get('observacion', '')}"
                  for r in captura.get("respuestas", {}).values())
    return "\n".join(p for p in partes if p.strip())

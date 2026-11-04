"""Asistente de diálogo pedagógico para levantar necesidades cuando falta evidencia documental."""
import json
import streamlit as st
from config.settings import GEMINI_MODEL
from ai.engine import client as get_client

PROMPT_SISTEMA = """Eres el Asistente Pedagógico de Diálogo de la USAER 02-E (Yucatán).
Tu función es dialogar de forma cálida, breve y profesional con las maestras de apoyo y especialistas para ayudarles a describir las necesidades educativas, estilo de aprendizaje, barreras y apoyos que requiere su alumno(a), cuando no cuentan aún con expedientes o informes previos cargados.

DIRECTRICES FUNDAMENTALES:
1. Sé conciso y pedagógico: respuestas de 1 a 2 párrafos breves. No abrumes a la docente con textos largos.
2. Formula máximo 1 o 2 preguntas concretas a la vez.
3. Pregunta por aspectos pedagógicos observables en el aula:
   - ¿Qué dificultades o barreras enfrenta en el aula regular (atención, lenguaje, lectura/escritura, cálculo, conducta)?
   - ¿En qué nivel real de desempeño se encuentra (ej. presilábico, silábico, alfabético; conteo básico con material, etc.)?
   - ¿Qué apoyos, materiales visuales/concretos o intereses personales le han funcionado?
4. NUNCA propongas diagnósticos clínicos ni etiquetes al alumno.
5. Usa un tono de colega empático, respetuoso y constructivo.
"""

def responder_chat(mensajes, alumno_info, funcion):
    """Genera una respuesta conversacional breve y orientadora para la docente."""
    cli = get_client()
    if cli is None:
        return "El servicio de IA no está configurado actualmente. Puedes describir directamente las necesidades en el campo de texto."
    
    contexto_alumno = f"Función del docente: {funcion}. Alumno(s): {alumno_info}."
    conversacion = f"{PROMPT_SISTEMA}\nCONTEXTO DEL CASO: {contexto_alumno}\n\nHISTORIAL DE DIÁLOGO:\n"
    for m in mensajes:
        rol = "Docente" if m["rol"] == "user" else "Asistente USAER"
        conversacion += f"{rol}: {m['texto']}\n"
    conversacion += "Asistente USAER:"
    
    try:
        resp = cli.models.generate_content(
            model=GEMINI_MODEL,
            contents=conversacion,
            config={'temperature': 0.4, 'max_output_tokens': 800}
        )
        return (getattr(resp, 'text', '') or '').strip()
    except Exception as exc:
        return f"No se pudo conectar con el asistente temporalmente ({exc}). Puedes escribir directamente las necesidades en tu planeación."


def sintetizar_necesidades(mensajes, alumno_info, funcion):
    """Sintetiza la conversación en un párrafo estructurado de necesidades pedagógicas para la planeación."""
    cli = get_client()
    textos_usuario = [m['texto'] for m in mensajes if m['rol'] == 'user']
    if cli is None or not textos_usuario:
        return "\n".join(textos_usuario)[:1500]
    
    dialogo = "\n".join(f"{'Docente' if m['rol']=='user' else 'Asistente'}: {m['texto']}" for m in mensajes)
    prompt = f"""Actúa como especialista de educación especial de USAER.
A partir de la conversación sostenida con la docente, redacta una síntesis técnica, precisa y observable de las necesidades educativas y apoyos requeridos para el alumno en su planeación.

CONVERSACIÓN:
{dialogo}

Estructura la síntesis en un párrafo fluido (máximo 600 caracteres) que detalle:
- Necesidad educativa específica observable en el aula (sin diagnósticos médicos).
- Nivel de desempeño pedagógico actual real.
- Ajustes razonables y apoyos recomendados (material manipulativo, apoyos visuales, andamiaje).
- Fortalezas o intereses que motivan al alumno.

Devuelve SOLO el texto de la síntesis, sin títulos, viñetas ni saludos.
"""
    try:
        resp = cli.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config={'temperature': 0.2, 'max_output_tokens': 600}
        )
        sintesis = (getattr(resp, 'text', '') or '').strip()
        return sintesis or "\n".join(textos_usuario)[:1500]
    except Exception:
        return "\n".join(textos_usuario)[:1500]

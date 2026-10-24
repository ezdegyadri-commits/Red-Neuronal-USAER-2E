"""Vista breve local y extractiva: nunca inventa NEE ni transmite originales a IA."""
import re
from utils.text import normalizar_texto

VERSION = 'sintesis-local-1'


def necesidades_explicitas(texto):
    """Solo necesidades enunciadas en el documento, no inferidas de diagnósticos."""
    resultado = []
    for linea in str(texto or '').splitlines():
        linea = re.sub(r'^\s*(?:[•*\-–]|\d+[.)])\s*', '', linea).strip()
        # Una mención dentro de un ejemplo o de un párrafo no es una NEE del alumno.
        if not re.match(r'^(?:Necesita|Requiere)\s+\w+', linea, re.I):
            continue
        if '[ilegible]' in linea.lower() or len(linea) > 600:
            continue
        if len(linea.split()) < 4:
            continue
        if normalizar_texto(linea) not in {normalizar_texto(v) for v in resultado}:
            resultado.append(linea)
    return resultado[:20]


def sintetizar(texto):
    """Fragmentos relevantes, acotados y etiquetados; no reemplaza la evaluación."""
    texto = str(texto or '')[:100000]
    lineas = []
    for fragmento in re.split(r'\n+|(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÑ])', texto):
        fragmento = ' '.join(fragmento.split()).strip()
        if len(fragmento) < 25 or re.search(r'\b(?:CURP|DOMICILIO|TEL[EÉ]FONO|CORREO)\b', fragmento, re.I):
            continue
        if fragmento not in lineas:
            lineas.append(fragmento)
    claves = ('NECESITA', 'REQUIERE', 'APOYO', 'DIFICULT', 'FORTALE', 'LOGRA', 'APREND', 'CONCLUSION')
    orden = sorted(enumerate(lineas), key=lambda p: (-sum(k in normalizar_texto(p[1]) for k in claves), p[0]))
    elegidas = sorted(orden[:3])
    resumen = ' '.join(v if len(v) <= 250 else v[:247].rsplit(' ', 1)[0] + '…' for _, v in elegidas)[:800]
    return {'version': VERSION, 'resumen': resumen,
            'necesidades': necesidades_explicitas(texto),
            'aviso': 'Síntesis local extractiva, no transcripción completa. Verifica con el original; no determina diagnósticos ni confirma necesidades por sí sola.'}

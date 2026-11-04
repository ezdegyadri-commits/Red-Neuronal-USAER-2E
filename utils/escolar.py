"""Claves escolares canónicas para captura nueva y comparación sin migración histórica."""
import re
from datetime import date
from utils.text import normalizar_texto


def grado_canonico(valor):
    text=normalizar_texto(valor).strip()
    if not text:return ''
    # Solo etiquetas completas: nunca extraer un dígito de un grupo, un ciclo
    # o una selección ambigua como «1 y 2».
    text=re.sub(r'^(?:GRADO|PRIMARIA|SECUNDARIA|PREESCOLAR)\s*[:.-]?\s+','',text)
    text=re.sub(r'\s+(?:(?:GRADO(?:\s+DE)?|DE)\s+)?(?:PRIMARIA|SECUNDARIA|PREESCOLAR)$','',text)
    text=re.sub(r'\s+GRADO$','',text).strip()
    nombres={'PRIMER':1,'PRIMERO':1,'SEGUNDO':2,'TERCER':3,'TERCERO':3,'CUARTO':4,'QUINTO':5,'SEXTO':6}
    if text in nombres:return str(nombres[text])+'°'
    match=re.fullmatch(r'0?([1-6])(?:\.0+|(?:\s*(?:[°ºO.]|ERO|ER|RO|DO|TO))*)',text)
    return match[1]+'°' if match else str(valor or '').strip()


def grupo_canonico(valor):
    return normalizar_texto(valor).strip()


def separar_grado_grupo(grado, grupo=''):
    """Separa etiquetas completas 2A/2º A sin inferir grado de otro dato."""
    g=normalizar_texto(grado).strip();s=grupo_canonico(grupo)
    patron=r'0?([1-6])\s*[°ºO.]?\s*([A-Z])'
    mg=re.fullmatch(patron,g);ms=re.fullmatch(patron,s)
    grados=[grado_canonico(m[1]) for m in (mg,ms) if m]
    canon=grado_canonico(grado) if not mg else grados[0]
    if grados and canon and canon!=grados[0]:raise ValueError('El grado y el grupo indican grados diferentes.')
    if len(set(grados))>1:raise ValueError('El grado y el grupo indican grados diferentes.')
    letra=ms[2] if ms else s or (mg[2] if mg else '')
    if mg and letra and letra!=mg[2]:raise ValueError('El grupo contradice la letra incluida en el grado.')
    return canon or (grados[0] if grados else ''),letra


def edad_septiembre(nacimiento,ciclo):
    if not isinstance(nacimiento,date):nacimiento=date.fromisoformat(str(nacimiento))
    corte=date(int(ciclo),9,1)
    if nacimiento>corte:raise ValueError('La fecha de nacimiento es posterior al corte escolar.')
    return corte.year-nacimiento.year-((corte.month,corte.day)<(nacimiento.month,nacimiento.day))

"""Rechaza copias literales y reformulaciones casi idénticas, sin adivinar semántica."""
import re
from difflib import SequenceMatcher
from utils.text import normalizar_texto


def repetida(actividad, anteriores):
    def limpio(t):return re.sub(r'[^A-Z0-9]+',' ',normalizar_texto(str(t))).strip()
    actual=limpio(actividad)
    for previa in anteriores:
        texto=limpio(previa)
        if not texto:continue
        if actual==texto:return True
        if len(actual)>=80 and actual in texto:return True
        if min(len(actual),len(texto))>=100 and SequenceMatcher(None,actual,texto,autojunk=False).ratio()>=.93:return True
    return False

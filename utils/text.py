import unicodedata
import pandas as pd


def normalizar_texto(valor):
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return ""
    texto = str(valor).strip().upper()
    texto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in texto if unicodedata.category(c) != "Mn").strip()


def safe_text(value):
    if value is None:
        return ""
    return str(value).strip()

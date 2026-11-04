"""Normaliza variantes de identificadores y nombres de escuelas USAER."""

from config.settings import ESCUELAS_USAER
from utils.text import normalizar_texto


_CANONICAL_DISPLAY = {
    "ICHCAANZIHO": "ICHCAANZIHÓ",
    "DOMINGO SOLIS RODRIGUEZ": "DOMINGO SOLÍS RODRÍGUEZ",
}
_EXTRA_ALIASES = {
    "ICHC AANZIHO": "Ichcaanziho",
    "IHC AANZIHO": "Ichcaanziho",
    "IHCAANZIHO": "Ichcaanziho",
    "ICHCAANZIHO": "Ichcaanziho",
    "DOMINGO SOLIS": "Domingo Solís Rodríguez",
    "DOMINGO SOLIS RODRIGUEZ": "Domingo Solís Rodríguez",
}


def _key(value):
    return " ".join(normalizar_texto(value).split())


def _display(value):
    text = str(value or "").strip()
    key = _key(text)
    return _CANONICAL_DISPLAY.get(key, text.upper())


def _put(index, value, canonical):
    key = _key(value)
    if key and key not in {"0", "NAN", "NONE"}:
        index[key] = canonical


def indice_escuelas(alumnos=None, escuelas=None):
    """Indexa alias, claves y CCT hacia un nombre canónico conocido."""
    index = {}
    for name, code in ESCUELAS_USAER.items():
        canonical = _display(name)
        _put(index, name, canonical)
        _put(index, code, canonical)
    for alias, canonical_name in _EXTRA_ALIASES.items():
        canonical = _display(canonical_name)
        _put(index, alias, canonical)

    # Propaga los CCT desde filas cuya escuela ya se puede resolver por nombre o clave.
    for frame in (escuelas, alumnos):
        if frame is None or not hasattr(frame, "to_dict") or frame.empty:
            continue
        for record in frame.fillna("").to_dict("records"):
            canonical = (
                index.get(_key(record.get("ID_Escuela", "")))
                or index.get(_key(record.get("Nombre_Escuela", "")))
            )
            if not canonical:
                continue
            for field in ("ID_Escuela", "Nombre_Escuela", "CCT_Escuela", "CCT"):
                _put(index, record.get(field, ""), canonical)
    return index


def nombre_escuela_canonico(nombre="", id_escuela="", cct="", index=None):
    """Resuelve la etiqueta mostrada/exportada por clave, CCT o nombre."""
    index = index or indice_escuelas()
    for value in (id_escuela, cct, nombre):
        key = _key(value)
        if key in index:
            return index[key]
    return str(nombre or id_escuela or "").strip()

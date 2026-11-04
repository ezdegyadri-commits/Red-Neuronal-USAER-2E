"""Huella determinista para propuestas locales y edición."""
import hashlib
import json


def huella(doc):
    return hashlib.sha256(json.dumps(doc, ensure_ascii=False, sort_keys=True).encode()).hexdigest()

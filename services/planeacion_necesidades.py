"""Opciones de NEE con procedencia y vínculo individual, sin consultar otro padrón."""
import json
from utils.text import normalizar_texto


def opciones(doc):
    ids = {str(a['ID_Alumno']) for a in doc['datos']['Alumnos']}
    result = []
    vistos = set()
    for f in doc.get('metadatos', {}).get('fuentes', []):
        if f.get('tipo') not in ('EPP', 'EPP_ESCANEADA') or not f.get('vinculo_verificado'): continue
        if f.get('tipo') == 'EPP' and f.get('parte') != 'Conclusión': continue
        aid = str(f.get('alumno', ''))
        if aid not in ids: continue  # Nunca atribuir un registro colectivo a uno de sus alumnos.
        try: rows = json.loads(f.get('texto', '{}')).get('NEE', [])
        except (ValueError, AttributeError, TypeError): continue
        if not isinstance(rows, list): continue
        for r in rows:
            if not isinstance(r, dict): continue
            need = str(r.get('NEE', '')).strip()
            if not need or len(need) > 2000: continue
            key = (aid, normalizar_texto(need))
            if key in vistos: continue
            vistos.add(key)
            result.append({'texto': need, 'alumno': aid, 'referencia': f.get('referencia', ''),
                           'documento': f.get('documento_origen', f.get('registro', '')),
                           'revision': f.get('revision', ''), 'fecha': f.get('fecha', ''), 'tipo': f['tipo']})
    return result

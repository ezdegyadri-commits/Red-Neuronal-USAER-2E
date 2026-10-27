"""Alcance explícito del Anexo XIX; un grupo vacío nunca significa Todos."""
from utils.escolar import grado_canonico, grupo_canonico


def ambito(doc):
    alumnos=doc['datos']['Alumnos']
    grados={grado_canonico(a.get('Grado')) for a in alumnos}
    if len(grados)!=1 or not next(iter(grados)):return None
    grado=next(iter(grados))
    alcance=doc.get('metadatos',{}).get('alcance_grupal',{})
    if alcance:
        if set(alcance)!={'grado','grupo'} or grado_canonico(alcance['grado'])!=grado:return None
        grupo=grupo_canonico(alcance['grupo'])
        grupos={grupo_canonico(a.get('Grupo')) for a in alumnos}
        if grupo!='*' and not grupos<={grupo,''}:return None
        return grado,grupo
    grupos={grupo_canonico(a.get('Grupo')) for a in alumnos}
    return (grado,next(iter(grupos))) if len(grupos)==1 else None


def etiqueta(doc):
    scope=ambito(doc)
    if scope:return scope[0]+(' · Todos los grupos' if scope[1]=='*' else ' '+scope[1] if scope[1] else ' · Sin grupo registrado')
    return ', '.join(sorted({(grado_canonico(a.get('Grado'))+' '+grupo_canonico(a.get('Grupo'))).strip()
                            for a in doc['datos']['Alumnos']}))

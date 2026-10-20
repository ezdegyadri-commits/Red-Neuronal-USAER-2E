"""Aplicación explícita y aditiva de propuestas sobre la hoja abierta."""
from copy import deepcopy
from services import planeacion as s
from services.planeacion_papel import huella


def conservar_redaccion(doc,propuesta):
    """Una propuesta no sustituye filas, textos o sesiones que ya existían."""
    if propuesta['id']!=doc['id'] or propuesta['datos']!=doc['datos']:
        raise ValueError('La propuesta no corresponde a los destinatarios de esta hoja.')
    result=deepcopy(propuesta)
    for tabla,rows in doc['tablas'].items():
        result['tablas'][tabla]=deepcopy(rows)+[deepcopy(r) for r in result['tablas'].get(tabla,[]) if r not in rows]
    for campo,valor in doc['textos'].items():
        if valor.strip():result['textos'][campo]=valor
    anterior=doc['metadatos'].get('equipo',{})
    nuevo=result['metadatos'].get('equipo',{})
    if anterior and nuevo:
        ids={r['id'] for r in anterior.get('sesiones',[])}
        nuevo['sesiones']=deepcopy(anterior.get('sesiones',[]))+[r for r in nuevo.get('sesiones',[]) if r['id'] not in ids]
    return result


def aplicar(doc,paquete):
    s.autorizar(doc,True)
    if paquete['base']!=huella(doc):
        raise ValueError('Tu hoja cambió después de preparar la propuesta. Se conserva tu edición; prepara una nueva propuesta.')
    return conservar_redaccion(doc,paquete['documento'])

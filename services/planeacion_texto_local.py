"""Recupera texto por ID de destinatario; nunca pisa una celda cambiada remotamente."""
from services import planeacion_papel as papel


def recuperar(doc,respaldo,colaborativa=False):
    spec=papel.hoja(doc,colaborativa=colaborativa)
    if respaldo.get('documento')!=doc['id'] or respaldo.get('cache_id')!=spec['cache_id']:
        raise PermissionError('El texto pendiente no corresponde a esta cuenta, área y documento.')
    entradas=respaldo.get('celdas',[])
    if not isinstance(entradas,list) or len(entradas)>2000:raise ValueError('El respaldo contiene una lista de celdas no válida.')
    cambios={}
    for entrada in entradas:
        if not isinstance(entrada,dict):raise ValueError('El respaldo de texto no tiene un formato válido.')
        matches=[(k,c) for k,c in spec['cells'].items() if c['editable'] and
            (c.get('destinatario')==entrada['destinatario'] and c['label']==entrada.get('label')
             if entrada.get('destinatario') else not c.get('destinatario') and list(c['target'])==entrada.get('target'))]
        if len(matches)!=1:raise ValueError('Una celda ya no pertenece a la matrícula o al área editable. Conserva el archivo; no se descartó su texto.')
        key,celda=matches[0];valor=str(entrada.get('valor',''))
        if key in cambios and cambios[key]!=valor:raise ValueError('El archivo contiene dos textos distintos para la misma celda. Conserva ambos antes de conciliarlos.')
        if celda['value'] not in (str(entrada.get('base','')),valor):
            raise RuntimeError('La celda «'+celda['label']+'» también cambió en la base central. Conserva el respaldo y compara ambas redacciones; no se sobrescribirá.')
        cambios[key]=valor
    if not cambios:raise ValueError('Este archivo no contiene celdas recuperables de texto pendiente.')
    event={'documento':doc['id'],'huella':spec['huella'],'accion':'guardar','cambios':cambios}
    return papel.aplicar_aporte(doc,event,con_observaciones=True) if colaborativa else papel.aplicar(doc,event)

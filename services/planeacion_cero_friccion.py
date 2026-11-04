"""Captura agrupada sobre el contrato del formato vivo; no sustituye persistencia."""
from services import planeacion_papel as papel, planeacion_formato as formato
from services.planeacion_compartida import es_guia
from services.planeacion_modelo import FORMATOS


def aplica(doc):
    # El Anexo XIX conserva su editor concurrente y su guardado por área.
    return not es_guia(doc) and doc.get('formato') in FORMATOS


def capturar(doc, spec, cambios, nuevas=None, retirar=None):
    """Una transacción local, conservando IDs, fuentes, sesiones y áreas protegidas."""
    if not aplica(doc):raise PermissionError('El Anexo XIX se continúa en la hoja compartida.')
    result=papel.aplicar(doc,{'documento':doc['id'],'huella':spec['huella'],
        'accion':'guardar','cambios':cambios})
    for tabla,indices in (retirar or {}).items():
        if tabla=='escala_trimestral':
            from services.planeacion_evaluacion import cambiar_fila
            for i in sorted(set(indices),reverse=True):result=cambiar_fila(result,i)
            continue
        if tabla not in FORMATOS[doc['formato']]['tablas']:raise ValueError('Tabla no reconocida.')
        for i in sorted(set(indices),reverse=True):
            result=formato.quitar_fila(result,tabla,i)
    for tabla,campos in (nuevas or {}).items():
        headers=FORMATOS[doc['formato']]['tablas'].get(tabla)
        if headers is None or not set(campos)<=set(headers):raise ValueError('Campos fuera del formato.')
        if any(not isinstance(v,str) or len(v)>20000 for v in campos.values()):raise ValueError('Revisa la extensión de la nueva fila.')
        if not any(v.strip() for v in campos.values()):continue
        result=formato.nueva_fila(result,tabla)
        for campo,valor in campos.items():
            result=formato.editar_celda(result,tabla,len(result['tablas'][tabla])-1,campo,valor)
    return result


def seleccionar_escuela(frame,escuela):
    """Nunca decide una escuela por subcadena, índice visual o nombre parecido."""
    if 'ID_Escuela' not in frame:raise ValueError('Falta el identificador de escuela.')
    return frame.loc[frame['ID_Escuela'].astype(str)==str(escuela)].copy()


def campos_del_rol(actor):
    if actor['director']:return ['Revisión directiva','Planeaciones grupales del equipo']
    if actor['area']=='Aprendizaje':return ['Planeación del Docente de Apoyo','Planeaciones grupales del equipo']
    if actor['area'] in ('Psicología','Comunicación','Trabajo Social'):
        return ['Planeación del Equipo de Paradocentes','Planeaciones grupales del equipo']
    raise PermissionError('No hay función de planeación asignada.')

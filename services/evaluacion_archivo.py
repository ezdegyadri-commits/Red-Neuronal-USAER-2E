"""Conecta una evaluación externa revisada con su original y sus antecedentes."""
from services import archivo_expediente as archivo, documentos_sintesis as sintesis

TIPO_AREA = {'Aprendizaje':'Competencia curricular', 'Psicología':'Estudio psicológico',
    'Comunicación':'Evaluación de comunicación y lenguaje', 'Trabajo Social':'Estudio social'}


def guardar(doc, area, nombre, data, resumen):
    if area not in TIPO_AREA:raise ValueError('Área de evaluación no válida.')
    value=sintesis.validar({'resumen':resumen,'necesidades':[]})
    # El archivo vuelve a comprobar usuario, asignación, contexto e integridad.
    did=archivo.guardar([doc['alumno']],TIPO_AREA[area],doc['ciclo'],nombre,data,
                        doc['id'],'EPP iniciada')
    sintesis.guardar(did,value)
    return did

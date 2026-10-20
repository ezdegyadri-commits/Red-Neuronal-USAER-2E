"""Recuperación visible, sin reescribir ni fusionar documentos guardados."""
from services.planeacion_matricula import clave_escuela


def actividades_redactadas(doc):
    return sum(bool(str(r.get('Actividades','') or '').strip()) for r in doc.get('tablas',{}).get('dosificacion',[]))


def ordenar(docs):
    # Una plantilla recién creada no desplaza al documento donde se escribió.
    # No se compara longitud como si más texto significara mejor planeación.
    return sorted(docs,key=lambda d:(bool(actividades_redactadas(d)),d.get('guardado_en','')),reverse=True)


def etiqueta(doc):
    from services.planeacion_compartida import etiqueta as original
    texto=original(doc)
    if doc.get('metadatos',{}).get('modalidad_planeacion')=='individual':
        texto+=' · '+', '.join(a['Nombre del alumno'] for a in doc['datos']['Alumnos'])
    n=actividades_redactadas(doc)
    return texto+(' · '+str(n)+' actividad(es) redactada(s)' if n else ' · Sin actividades redactadas')


def equivalentes(docs,actor,formato,ids,escuela,ciclo,trimestre,modalidad):
    """Coincidencia exacta y misma autoría; no une escuelas, alumnos ni periodos."""
    alumnos=set(map(str,ids));resultado=[]
    if not alumnos:return []
    for doc in docs:
        datos=doc['datos'];meta=doc.get('metadatos',{})
        if (doc.get('cuenta')!=actor['cuenta'] or doc.get('formato')!=formato
            or datos.get('Función')!=actor['area'] or meta.get('borrador_eliminado')
            or doc.get('estado')!='BORRADOR' or meta.get('modalidad_planeacion')!=modalidad
            or clave_escuela(datos.get('ID_Escuela'))!=clave_escuela(escuela)
            or str(datos.get('Curso escolar','')).replace('–','-')!=str(ciclo)+'-'+str(int(ciclo)+1)
            or str(datos.get('Trimestre'))!=str(trimestre)
            or {str(a['ID_Alumno']) for a in datos['Alumnos']}!=alumnos):continue
        resultado.append(doc)
    return ordenar(resultado)

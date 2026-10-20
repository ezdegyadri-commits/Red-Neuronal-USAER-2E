"""Escala docente complementaria: indicadores, no resultados inventados ni nueva norma."""
from copy import deepcopy
import hashlib

ESCALA=('Sin valorar','Requiere apoyo constante','En proceso con apoyos','Logrado con autonomía','No observado')
CAMPOS=('Alumno','Indicador de logro','Actividad vinculada','Valoración','Observaciones')


def filas(doc):
    if doc['metadatos'].get('modalidad_planeacion')!='individual':return []
    prev=doc['metadatos'].get('escala_trimestral',{})
    rows=deepcopy(prev.get('filas',[]));presentes={r.get('_origen') for r in rows}
    borrados=set(prev.get('retirados',[]))
    for tabla,clave in [('aprendizajes','Descriptor de logro'),('necesidades','Descriptor de Logro'),('curriculo','Descriptor de logro'),('dosificacion','_indicador_propuesto')]:
        for r in doc['tablas'].get(tabla,[]):
            indicador=str(r.get(clave,'') or '').strip()
            if not indicador:continue
            ids=r.get('_alumnos_apartados') or r.get('_alumnos_locales') or r.get('_alumnos_planeacion') or [a['ID_Alumno'] for a in doc['datos']['Alumnos']]
            for a in doc['datos']['Alumnos']:
                if a['ID_Alumno'] not in ids:continue
                origen=hashlib.sha256((a['ID_Alumno']+'|'+indicador).encode()).hexdigest()[:20]
                if origen in presentes or origen in borrados:continue
                actividades=[str(x.get('Actividades','')) for x in doc['tablas'].get('dosificacion',[]) if
                    (not (x.get('_alumnos_locales') or x.get('_alumnos_planeacion')) or a['ID_Alumno'] in (x.get('_alumnos_locales') or x.get('_alumnos_planeacion'))) and x.get('Actividades')]
                rows.append({'ID_Alumno':a['ID_Alumno'],'Alumno':a['Nombre del alumno'],'Indicador de logro':indicador,
                    'Actividad vinculada':'\n'.join(actividades)[:3000],'Valoración':'Sin valorar','Observaciones':'','_origen':origen})
                presentes.add(origen)
    return rows


def editar(doc,indice,campo,valor):
    if campo not in CAMPOS[1:]:raise PermissionError('Conserva el vínculo del alumno.')
    rows=filas(doc)
    if not 0<=indice<len(rows):raise ValueError('El indicador ya no está en la escala.')
    if campo=='Valoración' and valor not in ESCALA:raise ValueError('Elige una valoración de la escala.')
    result=deepcopy(doc);rows[indice][campo]=valor
    result['metadatos'].setdefault('escala_trimestral',{})['filas']=rows
    return result


def cambiar_fila(doc,indice=None,alumno=None):
    result=deepcopy(doc);rows=filas(doc);meta=result['metadatos'].setdefault('escala_trimestral',{})
    if indice is None:
        a=next((a for a in doc['datos']['Alumnos'] if a['ID_Alumno']==alumno),None) if alumno else doc['datos']['Alumnos'][0]
        if a is None:raise PermissionError('Selecciona un alumno de esta planeación.')
        rows.append({'ID_Alumno':a['ID_Alumno'],**{c:a['Nombre del alumno'] if c=='Alumno' else 'Sin valorar' if c=='Valoración' else '' for c in CAMPOS}})
    else:
        if not 0<=indice<len(rows):raise ValueError('Selecciona un indicador existente.')
        origen=rows.pop(indice).get('_origen')
        if origen:meta.setdefault('retirados',[]).append(origen)
    meta['filas']=rows
    return result

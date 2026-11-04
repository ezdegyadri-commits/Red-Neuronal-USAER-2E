"""Repara únicamente copias mecánicas de instrumentos; conserva su procedencia."""
from copy import deepcopy
import re
from services.planeacion_nee import es_bapse,necesidad,propuesta_logro
from services.planeacion_modelo import FORMATOS


def tiene_contenido(doc,tabla,row):
    campos=FORMATOS[doc['formato']]['tablas'][tabla]
    return any(str(row.get(k,'') or '').strip() for k in campos if not (tabla=='dosificacion' and k=='Contextos'))


def normalizar(doc):
    result=deepcopy(doc)
    if doc['formato']!='XXIII':return result
    personas=doc['datos']['Alumnos']
    fuentes=doc['metadatos'].get('fuentes',[])
    for row in result['tablas']['aprendizajes']:
        raw=str(row.get('Necesidades educativas específicas',''))
        if not es_bapse({'texto':raw}):continue
        # Una adición docente explícita a una copia antigua exige revisión manual.
        if 'EDITADO POR DOCENTE' in raw:continue
        ids=row.get('_alumnos_apartados',[])
        referencia=re.search(r'\[\s*III\s*[·-]\s*(E\d+)\s*\]',raw,re.I)
        if not ids and referencia:
            f=next((f for f in fuentes if f.get('referencia')==referencia[1]),{})
            ids=str(f.get('alumno','')).split(',')
        alumno=next((a for a in personas if ids==[a['ID_Alumno']]),personas[0] if len(personas)==1 else {})
        propias=[f for f in fuentes if alumno.get('ID_Alumno') and f.get('vinculo_verificado') and str(f.get('alumno','')).split(',')==[alumno['ID_Alumno']] and not es_bapse(f)]
        nee,origen=necesidad(alumno,propias,[],doc['datos']['Función'])
        row['Necesidades educativas específicas']=nee
        row['_nee_origen']=origen
        objetivo,descriptor=propuesta_logro(nee)
        if not str(row.get('Aprendizaje y/u objetivo','') or '').strip():row['Aprendizaje y/u objetivo']=objetivo
        if not str(row.get('Descriptor de logro','') or '').strip():row['Descriptor de logro']=descriptor
        row.setdefault('_nee_reparada',{'anterior':raw,'motivo':'copia de instrumento en campo NEE'})
    return result

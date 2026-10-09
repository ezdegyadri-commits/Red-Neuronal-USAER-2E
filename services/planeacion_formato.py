"""Adaptador del formato familiar sobre el documento canónico existente."""
from copy import deepcopy
from services.planeacion_modelo import FORMATOS

TITULOS={'aprendizajes':'Necesidades educativas específicas, aprendizaje y descriptor de logro',
 'dosificacion':'Organización de las actividades de aprendizaje','barreras':'Barreras para el aprendizaje y la participación',
 'necesidades':'Necesidades educativas específicas y apoyos','curriculo':'Apoyos y ajustes al currículo',
 'participantes':'Personas implicadas','evaluacion_final':'Evaluación final del plan de intervención'}

def editar_celda(doc,tabla,indice,campo,valor):
    if campo not in FORMATOS[doc['formato']]['tablas'].get(tabla,[]):raise ValueError('Campo fuera del formato.')
    if not 0<=indice<len(doc['tablas'][tabla]):raise ValueError('La fila cambió; vuelve a abrir el documento.')
    if doc['tablas'][tabla][indice].get('_sesion_equipo'):raise ValueError('Edita esta actividad en sus sesiones vinculadas.')
    result=deepcopy(doc);result['tablas'][tabla][indice][campo]=str(valor or '');return result

def nueva_fila(doc,tabla):
    headers=FORMATOS[doc['formato']]['tablas'].get(tabla)
    if headers is None:raise ValueError('Tabla fuera del formato.')
    if len(doc['tablas'][tabla])>=100:raise ValueError('Revisa las cien filas existentes antes de añadir otra.')
    result=deepcopy(doc);result['tablas'][tabla].append(dict.fromkeys(headers,''));return result

def quitar_fila(doc,tabla,indice):
    if tabla not in FORMATOS[doc['formato']]['tablas']:raise ValueError('Tabla fuera del formato.')
    if not 0<=indice<len(doc['tablas'][tabla]):raise ValueError('La fila cambió.')
    if doc['tablas'][tabla][indice].get('_sesion_equipo'):raise ValueError('Retira esta actividad desde sus sesiones vinculadas.')
    result=deepcopy(doc);result['tablas'][tabla].pop(indice);return result

def editar_guia(doc,parche,base):
    if doc['metadatos'].get('guia_compartida'):raise PermissionError('Edita la guía compartida desde sus aportaciones.')
    from services.planeacion_modalidad import GUIA_XIX
    permitidos=set(GUIA_XIX)-{'Nombre alumno','Discapacidad o condición'}
    ids={a['ID_Alumno'] for a in doc['datos']['Alumnos']}
    if any(r.get('ID_Alumno') not in ids for r in base):raise PermissionError('La guía incluye alumnos ajenos.')
    result=deepcopy(doc);rows=deepcopy(base)
    for i,campos in parche.get('edited_rows',{}).items():
        if 0<=int(i)<len(rows):rows[int(i)].update({k:str(v or '') for k,v in campos.items() if k in permitidos})
    previo=result['metadatos'].get('guia_grupal_manual',{})
    result['metadatos']['guia_grupal_manual']={**previo,'filas':rows};return result

"""Lectura contextual y edición acotada de la hoja viva, sin persistencia nueva."""
from copy import deepcopy
from services import planeacion as s, planeacion_formato as formato
from services.planeacion_generacion import fuentes_pertinentes
from services.planeacion_modalidad import GUIA_XIX, guia_grupal


def campos_guia(doc):
    """Identidades y aportaciones de otras áreas no se editan en esta vista."""
    area=doc['datos']['Función']
    if doc['metadatos'].get('guia_compartida'):return []
    return ['Fecha derivación',area,'Situación inicial','Situación final'] if area in GUIA_XIX else []


def editar_guia(doc,parche,base):
    s.autorizar(doc,True)
    actuales=guia_grupal(doc).get('filas',[])
    if [r['ID_Alumno'] for r in base]!=[r['ID_Alumno'] for r in actuales]:
        raise ValueError('La selección cambió. Vuelve a abrir el formato antes de editar.')
    permitidos=campos_guia(doc)
    limpio={'edited_rows':{}}
    for indice,campos in parche.get('edited_rows',{}).items():
        if not 0<=int(indice)<len(base):raise ValueError('La fila ya no pertenece al formato.')
        if any(k not in permitidos for k in campos):raise PermissionError('Conserva las identidades y aportaciones de cada área.')
        limpio['edited_rows'][indice]={k:str(v or '') for k,v in campos.items()}
    return formato.editar_guia(doc,limpio,base)


def ficha(doc,alumno):
    """El ID, nunca el parecido del nombre, decide qué antecedentes se muestran."""
    s.autorizar(doc)
    persona=next((a for a in doc['datos']['Alumnos'] if a['ID_Alumno']==alumno),None)
    if persona is None:raise PermissionError('Elige un alumno de esta planeación.')
    fuentes=fuentes_pertinentes(doc)
    propias=[f for f in fuentes if alumno in str(f.get('alumno','')).split(',')]
    generales=[f for f in fuentes if f.get('tipo')=='MATERIAL' and not f.get('alumno')]
    propias.sort(key=lambda f:str(f.get('fecha','')),reverse=True)
    return {'alumno':deepcopy(persona),'antecedentes':propias,'materiales_generales':generales}


def opciones_padron(frame,escuela,tipo,grado='',grupo='',incluir=False):
    from services.planeacion_modalidad import filtrar
    rows=filtrar(frame,tipo,incluir)
    rows=rows.loc[rows['ID_Escuela'].astype(str)==str(escuela)]
    if grado:rows=rows.loc[rows['Grado'].astype(str)==str(grado)]
    if grupo:rows=rows.loc[rows['Grupo'].astype(str)==str(grupo)]
    return rows.copy()

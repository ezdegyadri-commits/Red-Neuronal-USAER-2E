"""Incorporación explícita al mismo Anexo XIX, sin modificar el padrón."""
from services import planeacion as s
from services.planeacion_ambito import ambito
from services.planeacion_compartida import es_guia, alumno_padron, ampliar_matricula
from services.planeacion_matricula import clave_escuela
from services.planeacion_modalidad import modalidad, guia_grupal
from utils.escolar import grado_canonico, grupo_canonico
from utils.text import normalizar_texto


def elegibles(doc, frame, incluir_individuales=False):
    scope=ambito(doc)
    if not es_guia(doc) or not scope:raise ValueError('Abre la planeación del grado y grupo para añadir alumnos.')
    grado,grupo=scope
    return frame.loc[[
        clave_escuela(r.get('ID_Escuela'))==clave_escuela(doc['datos']['ID_Escuela'])
        and grado_canonico(r.get('Grado'))==grado
        and (grupo=='*' or grupo_canonico(r.get('Grupo')) in {grupo,''})
        and modalidad(r) in ({'grupal','individual'} if incluir_individuales else {'grupal'})
        and normalizar_texto(r.get('Estatus','')) not in {'BAJA','INACTIVO','RETIRADO','ELIMINADO'}
        for r in frame.to_dict('records')]].copy()


def validar_incorporaciones(doc,frame):
    ids=set(map(str,doc['metadatos'].get('alumnos_incluidos_grupal',[])))&{str(a['ID_Alumno']) for a in doc['datos']['Alumnos']}
    if not ids:return
    from services.planeacion_excepciones import autorizadas
    disponibles=set(elegibles(doc,frame,True)['ID_Alumno'].astype(str))
    if not ids<=disponibles:raise PermissionError('Un alumno incorporado ya no corresponde a la matrícula grupal autorizada de este grado. Tu edición se conserva; revisa su grado, escuela y tipo de atención.')
    individuales={str(r['ID_Alumno']) for r in frame.to_dict('records') if str(r['ID_Alumno']) in ids and modalidad(r)=='individual'}
    if not individuales<=autorizadas(doc):raise PermissionError('Confirma la excepción individual para esta hoja antes de incorporarlo. No se cambió su modalidad ni su planeación individual.')


def incorporar(doc,ids,frame=None,autorizar_individuales=False):
    frame=s.padron_autorizado() if frame is None else frame
    actor=s.autorizar(doc,True,frame=frame)
    if not ids or len(ids)!=len(set(map(str,ids))):raise ValueError('Selecciona uno o varios alumnos sin duplicados.')
    if type(autorizar_individuales) is not bool:raise ValueError('Confirma si se autoriza una excepción individual.')
    rows=elegibles(doc,frame,autorizar_individuales)
    seleccion=rows.loc[rows['ID_Alumno'].astype(str).isin(set(map(str,ids)))]
    if len(seleccion)!=len(ids):raise PermissionError('Solo puedes incorporar alumnado activo de atención grupal del mismo grado y escuela; no se cambia su modalidad ni se mezcla otro grupo.')
    from services.planeacion_edicion import borrador
    result=borrador(doc);grado,grupo=ambito(doc)
    result['metadatos']['alcance_grupal']={'grado':grado,'grupo':grupo}
    incluidos=list(dict.fromkeys([*result['metadatos'].get('alumnos_incluidos_grupal',[]),*map(str,ids)]))
    result['metadatos']['alumnos_incluidos_grupal']=incluidos
    for row in seleccion.to_dict('records'):
        if modalidad(row)=='individual':
            result['metadatos'].setdefault('excepciones_individuales_grupal',{})[str(row['ID_Alumno'])]={
                'documento':doc['id'],'cuenta':actor['cuenta'],'confirmada':True,'grado':grado,'grupo':grupo}
    result['metadatos']['alumnos_excluidos_grupal']=[i for i in result['metadatos'].get('alumnos_excluidos_grupal',[]) if str(i) not in set(map(str,ids))]
    presentes={str(a['ID_Alumno']) for a in result['datos']['Alumnos']}
    for row in seleccion.to_dict('records'):
        if str(row['ID_Alumno']) not in presentes:result['datos']['Alumnos'].append(alumno_padron(row))
    result=ampliar_matricula(result,frame)
    result['metadatos']['guia_grupal_manual']=guia_grupal(result)
    # El mismo ID, actividades, aportaciones y modalidad de cada alumno.
    return result

"""Borradores aislados por hoja y recuperación de referencias autorizadas."""
import json
from services.expediente_contexto import ids_contexto


def filtrar_borrador(datos,frame):
    """La misma cuenta puede haber perdido una escuela desde el respaldo."""
    resultado=dict(datos)
    try:historial=json.loads(resultado.get('evento_borradores_json','{}'))
    except (TypeError,ValueError):historial={}
    if not isinstance(historial,dict):historial={}
    historial={k:v for k,v in historial.items() if isinstance(v,str) and ids_contexto(frame,k)}
    resultado['evento_borradores_json']=json.dumps(historial,ensure_ascii=False)
    actual=str(resultado.get('evento_contexto_actual',''))
    if not actual or not ids_contexto(frame,actual):
        for k in ('evento_contexto_actual','evento_descripcion','evento_alumno','evento_escuela_individual','evento_escuela_grupo','evento_grado','evento_grupo'):
            resultado.pop(k,None)
    return resultado


def cambiar_contexto(state, identificador):
    try: anteriores=json.loads(state.get('evento_borradores_json','{}'))
    except (ValueError,TypeError):anteriores={}
    if not isinstance(anteriores,dict):anteriores={}
    previo=state.get('evento_contexto_actual')
    if previo:
        anteriores[previo]=str(state.get('evento_descripcion',''))
    if previo!=identificador:
        state['evento_descripcion']=str(anteriores.get(identificador,''))
    state['evento_contexto_actual']=identificador
    state['evento_borradores_json']=json.dumps(anteriores,ensure_ascii=False)


def hojas(frame, registros):
    alumnos={str(r['ID_Alumno']):r for r in frame.fillna('').to_dict('records')}
    resultado={}
    for r in registros:
        aid=str(r.get('ID_Alumno',''))
        vinculados=ids_contexto(frame,aid)
        if not vinculados:continue
        if aid.startswith('GRUPO-'):
            grupo=aid.rsplit('-',2)
            etiqueta='Grupo '+grupo[-2]+' '+grupo[-1]
        else:etiqueta=str(alumnos[aid].get('Nombre_Completo',''))
        escuela=str(alumnos[vinculados[0]].get('Nombre_Escuela',''))
        actual=resultado.setdefault(aid,{'id':aid,'etiqueta':escuela+' · '+etiqueta,'fecha':'','cantidad':0})
        actual['cantidad']+=1
        actual['fecha']=max(actual['fecha'],str(r.get('Fecha',''))[:10])
    return sorted(resultado.values(),key=lambda r:(r['fecha'],r['etiqueta']),reverse=True)

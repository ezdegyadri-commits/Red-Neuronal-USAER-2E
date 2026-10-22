"""Precarga del catálogo regular; no atribuye docentes por semejanza de nombres."""
from copy import deepcopy
from services.planeacion_ambito import ambito
from services.planeacion_compartida import es_guia
from services.planeacion_matricula import clave_escuela
from utils.escolar import grado_canonico, grupo_canonico
from utils.text import normalizar_texto


def aplicar(doc,registros):
    result=deepcopy(doc)
    if not es_guia(doc) or not ambito(doc):return result
    grado,grupo=ambito(doc)
    ciclo=str(doc['datos']['Curso escolar']).replace('–','-').replace(' ','')
    turno=normalizar_texto(doc['datos'].get('Turno','Matutino'))
    candidatos=[r for r in registros
        if clave_escuela(r.get('ID_Escuela') or r.get('Nombre_Escuela'))==clave_escuela(doc['datos']['ID_Escuela'])
        and str(r.get('Ciclo_Escolar','')).replace('–','-').replace(' ','')==ciclo
        and grado_canonico(r.get('Grado'))==grado
        and normalizar_texto(r.get('Turno','Matutino'))==turno
        and str(r.get('Nombre_Docente','')).strip()]
    if grupo!='*':
        exactos=[r for r in candidatos if grupo_canonico(r.get('Grupo'))==grupo]
        # Una letra no capturada sólo se resuelve si hay un único grupo posible.
        candidatos=exactos or (candidatos if not grupo and len({grupo_canonico(r.get('Grupo')) for r in candidatos})==1 else [])
    if not candidatos:return result
    porgrupo={}
    for r in candidatos:
        g=grupo_canonico(r.get('Grupo'))
        if g not in porgrupo or str(r.get('Fecha_Registro',''))>str(porgrupo[g].get('Fecha_Registro','')):porgrupo[g]=r
    nombres=[(grado+' '+g+' · ' if len(porgrupo)>1 else '')+str(r['Nombre_Docente']).strip() for g,r in sorted(porgrupo.items())]
    texto='; '.join(dict.fromkeys(nombres))
    meta=result['metadatos'];manual=meta.setdefault('guia_grupal_manual',{})
    actual=manual.get('maestro_grupo','');anterior=meta.get('maestro_regular_autocompletado','')
    if not meta.get('maestro_regular_edicion_manual') and (not actual or actual==anterior):
        manual['maestro_grupo']=texto
        meta['maestro_regular_autocompletado']=texto
        meta['docentes_regulares_vinculados']=[{'registro':r.get('ID_Registro',''),'grupo':g,'nombre':r['Nombre_Docente']} for g,r in sorted(porgrupo.items())]
        meta.pop('docentes_regulares_sugeridos',None)
    elif actual!=texto:
        meta['docentes_regulares_sugeridos']=texto
    else:meta.pop('docentes_regulares_sugeridos',None)
    return result

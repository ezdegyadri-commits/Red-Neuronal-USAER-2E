"""Un Anexo XIX por escuela/grado/grupo/ciclo/trimestre, sin borrar fuentes.

La conciliación es una proyección determinista. La primera escritura confirmada
la incorpora como otra versión del documento más antiguo; los originales siguen
en Planeaciones_Versiones. No resuelve identidad ni permisos por nombre.
"""
from copy import deepcopy
import hashlib
import json
from services.planeacion_compartida import es_guia
from services.planeacion_matricula import clave_escuela
from utils.escolar import grado_canonico,grupo_canonico


def clave(doc):
    if not es_guia(doc) or not doc['datos']['Alumnos']:return None
    grupos={(grado_canonico(a.get('Grado')),grupo_canonico(a.get('Grupo'))) for a in doc['datos']['Alumnos']}
    if len(grupos)!=1:return None
    grado,grupo=next(iter(grupos))
    if not grado:return None
    # Sin letra significa planeación de ese grado; no se equipara a A/B/etc.
    return (clave_escuela(doc['datos']['ID_Escuela']),str(doc['datos']['Curso escolar']).replace('–','-'),
            str(doc['datos']['Trimestre']),grado,grupo)


def identificador(doc):
    return hashlib.sha256(('AnexoXIX|'+json.dumps(clave(doc),ensure_ascii=False)).encode()).hexdigest()[:32]


def _texto(a,b):
    a=str(a or '').strip();b=str(b or '').strip()
    if not b or a==b:return a
    if not a:return b
    # Evita duplicar párrafos ya conciliados, sin colapsar textos diferentes.
    return '\n\n'.join(dict.fromkeys(p for p in a.split('\n\n')+b.split('\n\n') if p))


def _unir_filas(a,b):
    rows=deepcopy(a);vistas={json.dumps(r,sort_keys=True,ensure_ascii=False) for r in rows}
    for r in b:
        firma=json.dumps(r,sort_keys=True,ensure_ascii=False)
        if firma not in vistas:rows.append(deepcopy(r));vistas.add(firma)
    return rows


def conciliar(base,otros):
    from services.planeacion_modalidad import guia_grupal,GUIA_XIX
    result=deepcopy(base);meta=result['metadatos']
    registro=meta.setdefault('unificacion_grupal',{'fuentes':{},'conflictos_area':[]})
    pendientes=[d for d in otros if registro['fuentes'].get(d['id'])!=d['revision']]
    if not pendientes:return result
    guia=guia_grupal(result);filas={r['ID_Alumno']:r for r in guia['filas']}
    alumnos={a['ID_Alumno']:a for a in result['datos']['Alumnos']}
    aportes=meta.setdefault('aportaciones_equipo',{})
    for d in pendientes:
        fuente=guia_grupal(d)
        for a in d['datos']['Alumnos']:alumnos.setdefault(a['ID_Alumno'],deepcopy(a))
        for r in fuente['filas']:
            fila=filas.setdefault(r['ID_Alumno'],deepcopy(r))
            for c in GUIA_XIX:fila[c]=_texto(fila.get(c),r.get(c))
        guia['maestro_grupo']=_texto(guia.get('maestro_grupo'),fuente.get('maestro_grupo'))
        guia['as']=_unir_filas(guia.get('as',[]),fuente.get('as',[]))
        for area,aporte in d['metadatos'].get('aportaciones_equipo',{}).items():
            previo=aportes.get(area)
            if previo and previo.get('cuenta')!=aporte.get('cuenta') and area not in registro['conflictos_area']:
                registro['conflictos_area'].append(area)
            if not previo:aportes[area]=deepcopy(aporte)
            else:
                previo['filas']=_unir_filas(previo.get('filas',[]),aporte.get('filas',[]))
                previo['observaciones']=_texto(previo.get('observaciones'),aporte.get('observaciones'))
            combinado=aportes[area]
            combinado['revision']=hashlib.sha256(json.dumps([combinado.get('revision'),aporte.get('revision'),d['id']],sort_keys=True).encode()).hexdigest()
            combinado['fecha']=max(str(combinado.get('fecha','')),str(aporte.get('fecha','')))
        for tabla,rows in d.get('tablas',{}).items():result['tablas'][tabla]=_unir_filas(result['tablas'].get(tabla,[]),rows)
        for campo,valor in d.get('textos',{}).items():result['textos'][campo]=_texto(result['textos'].get(campo),valor)
        registro['fuentes'][d['id']]=d['revision']
    guia['filas']=list(filas.values());result['datos']['Alumnos']=list(alumnos.values())
    # La columna visible y la aportación editable tienen exactamente el mismo
    # texto conciliado; ninguna revisión antigua vuelve a insertarse al borrar.
    for area,aporte in aportes.items():
        porid={r['ID_Alumno']:r for r in aporte.get('filas',[])}
        for aid,r in filas.items():
            if not r.get(area) and aid not in porid:continue
            porid.setdefault(aid,{'ID_Alumno':aid}).update({'Texto en formato':r.get(area,''),'_celda_viva':True})
        aporte['filas']=list(porid.values())
    meta['guia_grupal_manual']=guia
    return result


def documentos(versiones):
    """Conserva un ID estable, elegido por su primera versión (no último guardado)."""
    ultimas={};creados={}
    for d in versiones:
        ultimas[d['id']]=d
        creados[d['id']]=min(creados.get(d['id'],d.get('guardado_en','')),d.get('guardado_en',''))
    # Archivar la hoja unificada no debe revivir las copias que ya reunió.
    retirados={sid for d in ultimas.values() if d['metadatos'].get('borrador_eliminado')
        for sid in d['metadatos'].get('unificacion_grupal',{}).get('fuentes',{})}
    grupos={};salida=[]
    for d in ultimas.values():
        if d['id'] in retirados:continue
        k=clave(d)
        if not k or d['metadatos'].get('borrador_eliminado'):salida.append(deepcopy(d));continue
        grupos.setdefault(k,[]).append(d)
    for docs in grupos.values():
        # Una hoja ya consolidada es la raíz incluso si el llamador entrega
        # solamente las versiones más recientes (su fecha cambió al guardar).
        # No reactivar una copia antigua por tener una fecha de guardado anterior.
        ids={d['id'] for d in docs}
        docs.sort(key=lambda d:(-len(ids & set(d['metadatos'].get('unificacion_grupal',{}).get('fuentes',{}))),creados[d['id']],d['id']))
        salida.append(conciliar(docs[0],docs[1:]) if len(docs)>1 else deepcopy(docs[0]))
    return salida


def vigente(doc,versiones):
    k=clave(doc)
    if not k:return None
    return next((d for d in documentos(versiones) if clave(d)==k and not d['metadatos'].get('borrador_eliminado')),None)

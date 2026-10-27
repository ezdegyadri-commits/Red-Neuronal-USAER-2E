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


def clave(doc):
    if not es_guia(doc) or not doc['datos']['Alumnos']:return None
    from services.planeacion_ambito import ambito
    scope=ambito(doc)
    if not scope:return None
    grado,grupo=scope
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
    from services.planeacion_ambito import ambito
    scope=ambito(base)
    registro=meta.setdefault('unificacion_grupal',{'fuentes':{},'conflictos_area':[]})
    pendientes=[d for d in otros if registro['fuentes'].get(d['id'])!=d['revision']]
    if not pendientes:return result
    guia=guia_grupal(result);filas={r['ID_Alumno']:r for r in guia['filas']}
    alumnos={a['ID_Alumno']:a for a in result['datos']['Alumnos']}
    aportes=meta.setdefault('aportaciones_equipo',{})
    for d in pendientes:
        meta['alumnos_incluidos_grupal']=list(dict.fromkeys([*meta.get('alumnos_incluidos_grupal',[]),*d['metadatos'].get('alumnos_incluidos_grupal',[])]))
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
    if scope:meta['alcance_grupal']={'grado':scope[0],'grupo':scope[1]}
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


def reintegrar_copias(ultimas):
    """Copias adaptadas del mismo grupo vuelven a su raíz, sin tocar originales.

    Solo alcanza copias con origen comprobable; no convierte subgrupos
    trimestrales independientes ni mezcla grados, letras, autores o periodos.
    """
    from utils.escolar import grado_canonico,grupo_canonico
    from services.planeacion_modalidad import modalidad
    result=dict(ultimas)
    for did,doc in ultimas.items():
        if doc['metadatos'].get('vista_formato')!='trimestral' or doc['metadatos'].get('borrador_eliminado'):continue
        origen=doc;vistos={did}
        while (sid:=origen['metadatos'].get('copia_de',{}).get('documento')) and sid in ultimas and sid not in vistos:
            vistos.add(sid);origen=ultimas[sid]
        k=clave(origen)
        if not k or doc.get('cuenta')!=origen.get('cuenta') or doc.get('formato')!=origen.get('formato'):continue
        if (doc['datos'].get('Función')!='Aprendizaje' or doc['metadatos'].get('modalidad_planeacion')!='grupal'
            or clave_escuela(doc['datos']['ID_Escuela'])!=k[0]
            or str(doc['datos']['Curso escolar']).replace('–','-')!=k[1]
            or str(doc['datos']['Trimestre'])!=k[2]):continue
        alumnos=doc['datos']['Alumnos']
        if not alumnos or any(grado_canonico(a.get('Grado'))!=k[3] or modalidad(a)=='individual'
            or k[4]!='*' and grupo_canonico(a.get('Grupo')) not in {k[4],''} for a in alumnos):continue
        copia=deepcopy(doc);m=copia['metadatos']
        m['vista_formato']='guia';m['alcance_grupal']={'grado':k[3],'grupo':k[4]}
        m['reintegrada_grupal_en']=origen['id']
        m['alumnos_incluidos_grupal']=list(dict.fromkeys([*m.get('alumnos_incluidos_grupal',[]),*[str(a['ID_Alumno']) for a in alumnos if not grupo_canonico(a.get('Grupo'))]]))
        result[did]=copia
    return result


def documentos(versiones):
    """Conserva un ID estable, elegido por su primera versión (no último guardado)."""
    ultimas={};creados={}
    for d in versiones:
        ultimas[d['id']]=d
        creados[d['id']]=min(creados.get(d['id'],d.get('guardado_en','')),d.get('guardado_en',''))
    ultimas=reintegrar_copias(ultimas)
    # Archivar la hoja unificada no debe revivir las copias que ya reunió.
    retirados={sid for d in ultimas.values() if d['metadatos'].get('borrador_eliminado')
        for sid in d['metadatos'].get('unificacion_grupal',{}).get('fuentes',{})}
    grupos={};salida=[]
    for d in ultimas.values():
        if d['id'] in retirados:continue
        k=clave(d)
        if not k or d['metadatos'].get('borrador_eliminado'):salida.append(deepcopy(d));continue
        grupos.setdefault(k,[]).append(d)
    # Solo un alcance Todos expresamente guardado reúne las secciones previas.
    # No convierte documentos históricos sin letra en documentos de todo el grado.
    for k in list(grupos):
        if k[-1]!='*':continue
        for parcial in list(grupos):
            if parcial!=k and parcial[:4]==k[:4]:grupos[k].extend(grupos.pop(parcial))
    for docs in grupos.values():
        # Una hoja ya consolidada es la raíz incluso si el llamador entrega
        # solamente las versiones más recientes (su fecha cambió al guardar).
        # No reactivar una copia antigua por tener una fecha de guardado anterior.
        ids={d['id'] for d in docs}
        docs.sort(key=lambda d:(clave(d)[-1]!='*',bool(d['metadatos'].get('reintegrada_grupal_en')),-len(ids & set(d['metadatos'].get('unificacion_grupal',{}).get('fuentes',{}))),creados[d['id']],d['id']))
        salida.append(conciliar(docs[0],docs[1:]) if len(docs)>1 else deepcopy(docs[0]))
    return salida


def vigente(doc,versiones):
    k=clave(doc)
    if not k:return None
    docs=[d for d in documentos(versiones) if clave(d) and not d['metadatos'].get('borrador_eliminado')]
    # Si existe la hoja de todo el grado, cualquier acceso A/B abre esa misma hoja.
    total=next((d for d in docs if clave(d)[:4]==k[:4] and clave(d)[-1]=='*'),None)
    if total:return total
    if k[-1]!='*':return next((d for d in docs if clave(d)==k),None)
    candidatos=[d for d in docs if clave(d)[:4]==k[:4]]
    if not candidatos:return None
    # Ampliación solicitada por apoyo: reutiliza una raíz anterior, no otra copia.
    candidatos.sort(key=lambda d:(d.get('guardado_en',''),d['id']))
    raiz=deepcopy(candidatos[0])
    raiz['metadatos']['alcance_grupal']=deepcopy(doc['metadatos']['alcance_grupal'])
    return conciliar(raiz,candidatos[1:])

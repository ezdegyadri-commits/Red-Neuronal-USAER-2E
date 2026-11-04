"""Una intervención independiente por NEE, dentro de la misma planeación.

No transforma BAP en NEE ni migra la captura histórica o propuestas sin EPP.
El origen validado queda como instantánea, aunque cambie una evaluación después.
"""
from copy import deepcopy
import hashlib
from services.planeacion_nee import catalogo_nee_validadas
from services.nee_documentales import clave

CAMPOS=('NEE','Aprendizaje y/u objetivo','Descriptor de logro','Apoyos',
    'Ajustes razonables','Contextos','Actividades','Temporalidad','Recursos',
    'Evaluación y seguimiento')


def aplica(doc):
    return doc.get('formato') in ('XXI','XXIII','XXV') and doc.get('metadatos',{}).get('modalidad_planeacion')=='individual'


def catalogo(doc):
    if not aplica(doc):return []
    ids={str(a['ID_Alumno']) for a in doc['datos']['Alumnos']}
    from services.planeacion_necesidades import opciones
    verificadas=opciones(doc)
    # No sustituye la propuesta actual del alumno sin EPP por un flujo nuevo.
    candidatas=[r for aid in sorted(ids) for r in catalogo_nee_validadas(doc,alumno_id=aid)]
    result=[]
    for v in verificadas:
        aid=str(v.get('alumno'))
        # El catálogo validado vigente manda, incluso si las fuentes históricas
        # aún contienen otra revisión o una NEE posteriormente descartada.
        r=next((r for r in candidatas if str(r.get('alumno_id'))==aid
            and r.get('documento_origen')==v.get('documento')
            and clave(r.get('original',''))==clave(v.get('texto',''))),None)
        if not r:continue
        r=deepcopy(r);r.update(revision=v.get('revision',''),id_fuente=v['id'])
        r['id']=hashlib.sha256((aid+'|'+str(v['id'])).encode()).hexdigest()[:32]
        result.append(r)
    return result


def etiqueta(doc,campo):
    if campo!='Aprendizaje y/u objetivo':return campo
    return {'Psicología':'Objetivo de intervención psicológica',
        'Comunicación':'Objetivo de comunicación y lenguaje',
        'Trabajo Social':'Objetivo de intervención social'}.get(doc['datos'].get('Función'),campo)


def bloques(doc):
    ids={str(a['ID_Alumno']) for a in doc['datos']['Alumnos']}
    result=doc.get('metadatos',{}).get('intervenciones_nee',[])
    if not isinstance(result,list) or len(result)>40:raise ValueError('Revisa los bloques de intervención por NEE.')
    if any(not isinstance(r,dict) or str(r.get('alumno')) not in ids for r in result):
        raise PermissionError('Hay una intervención de NEE que no corresponde a los alumnos de esta planeación.')
    if len({r.get('id') for r in result})!=len(result):raise ValueError('Hay bloques de NEE con identificadores repetidos.')
    for r in result:
        if not isinstance(r.get('origen'),dict) or not isinstance(r.get('campos'),dict) or r['origen'].get('alumno_id')!=r['alumno']:
            raise ValueError('La procedencia de una intervención de NEE no es válida.')
        if any(not isinstance(r['campos'].get(c,''),str) or len(r['campos'].get(c,''))>20000 for c in CAMPOS):
            raise ValueError('Revisa los apartados de la intervención de NEE.')
    return deepcopy(result)


def incorporar(doc, seleccion):
    if not aplica(doc):raise ValueError('Las intervenciones por NEE corresponden a planeaciones individuales.')
    if not isinstance(seleccion,list) or len(seleccion)>40:raise ValueError('Selecciona hasta 40 NEE del catálogo del alumno.')
    if not seleccion:return deepcopy(doc)
    disponibles={r['id']:r for r in catalogo(doc)}
    if not set(seleccion)<=set(disponibles):raise PermissionError('Una NEE elegida ya no está disponible o no corresponde al alumno.')
    result=deepcopy(doc);rows=bloques(doc)
    usados={(r['alumno'],clave(r['origen']['texto'])) for r in rows}
    for rid in dict.fromkeys(seleccion):
        source=disponibles[rid];aid=str(source['alumno_id'])
        identificador=hashlib.sha256((doc['id']+'|'+aid+'|'+rid).encode()).hexdigest()[:32]
        if any(r['id']==identificador for r in rows) or (aid,clave(source['texto'])) in usados:continue
        if len(rows)>=40:raise ValueError('Conserva hasta 40 intervenciones por planeación.')
        campos=dict.fromkeys(CAMPOS,'');campos.update(NEE=source['texto'],Apoyos=source.get('apoyos',''),
            **{'Ajustes razonables':source.get('ajustes','')})
        rows.append({'id':identificador,'alumno':aid,'origen':deepcopy(source),'campos':campos})
        usados.add((aid,clave(source['texto'])))
    result['metadatos']['intervenciones_nee']=rows
    return result


def editar(doc,bid,campo,valor):
    if not aplica(doc) or campo not in CAMPOS:raise ValueError('Campo fuera de la intervención por NEE.')
    if not isinstance(valor,str) or len(valor)>20000:raise ValueError('Revisa la extensión del apartado.')
    result=deepcopy(doc);rows=bloques(doc)
    row=next((r for r in rows if r['id']==bid),None)
    if not row:raise ValueError('El bloque de NEE cambió. Recupera la revisión actual sin descartar tu texto.')
    row['campos'][campo]=valor
    result['metadatos']['intervenciones_nee']=rows;return result


def revisar(doc):
    pendientes=[]
    for i,b in enumerate(bloques(doc),1):
        required=('NEE','Aprendizaje y/u objetivo','Descriptor de logro','Actividades',
            'Temporalidad','Recursos','Evaluación y seguimiento')
        faltantes=[etiqueta(doc,c) for c in required if not b['campos'].get(c,'').strip()]
        if faltantes:pendientes.append('completar intervención NEE '+str(i)+': '+', '.join(faltantes))
    return pendientes

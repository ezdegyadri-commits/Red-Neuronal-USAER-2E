"""Anexo XXV: reutiliza barreras documentadas sin inferirlas de un instrumento.

La conclusión de EPP ya validada es provista por el adaptador de planeación.
Se conservan sus destinatarios y revisión; solo se completan espacios vacíos.
"""
from copy import deepcopy
import hashlib
import json
import re
from services.planeacion_nee import es_bapse

BARRERA='Barreras para el Aprendizaje y la Participación'
APOYO='Apoyos y/o ajustes razonables'


def extraer(fuente):
    if es_bapse(fuente):return []
    texto=str(fuente.get('texto',''))
    try:contenido=json.loads(texto)
    except (ValueError,TypeError):contenido=None
    if isinstance(contenido,dict):
        rows=contenido.get('BAP',[])
        if not isinstance(rows,list):return []
        return [{BARRERA:(str(r.get('Contextos','')).strip()+': ' if r.get('Contextos') else '')+str(r['Tipo de barrera']).strip(),
                 APOYO:str(r.get('Acciones generales','')).strip()} for r in rows
                if isinstance(r,dict) and isinstance(r.get('Tipo de barrera'),str) and r['Tipo de barrera'].strip()]
    # Solo un apartado explícito, nunca todo el informe ni una respuesta aislada
    # a una pregunta de BAPSE. Su pertinencia sigue a cargo de Trabajo Social.
    return [{BARRERA:m.group(1).strip(),APOYO:''} for m in re.finditer(
        r'(?im)^\s*(?:BAP|Barrera(?:s)?(?: para el aprendizaje y la participaci[oó]n)?)\s*:\s*([^\n]+)',texto)]


def proponer(doc):
    from services import planeacion as s
    from services.planeacion_generacion import fuentes_pertinentes
    s.autorizar(doc,True)
    result=deepcopy(doc)
    if doc['formato']!='XXV':return result
    rows=result['tablas']['barreras'];nombres={a['ID_Alumno']:a['Nombre del alumno'] for a in doc['datos']['Alumnos']}
    for f in fuentes_pertinentes(doc):
        ids=list(dict.fromkeys(str(f.get('alumno','')).split(',')))
        if not ids or any(i not in nombres for i in ids) or not f.get('vinculo_verificado'):continue
        for indice,valor in enumerate(extraer(f)):
            identidad=[f.get('tipo'),f.get('registro'),f.get('revision'),ids,indice,valor]
            key=hashlib.sha256(json.dumps(identidad,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
            if any(r.get('_bap_documentada')==key for r in rows):continue
            libres=[r for r in rows if not r.get('_aporte') and not r.get('_bap_documentada') and not r.get('_alumnos_apartados') and not any(str(r.get(k,'')).strip() for k in (BARRERA,APOYO))]
            row=libres[0] if libres else None
            if row is None:
                # No añadir propuestas paralelas a una decisión ya redactada sin
                # procedencia explícita. El usuario puede agregar otra fila.
                if any(not r.get('_bap_documentada') for r in rows) or len(rows)>=100:continue
                row={};rows.append(row)
            row.update({BARRERA:', '.join(nombres[i] for i in ids)+' · '+valor[BARRERA],APOYO:valor[APOYO],
                '_bap_documentada':key,'_alumnos_apartados':ids,
                '_origenes_apartados':[{k:f.get(k,'') for k in ('tipo','registro','revision','alumno','referencia','fecha')} ]})
    return result

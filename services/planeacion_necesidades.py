"""Opciones de NEE con procedencia y vínculo individual, sin consultar otro padrón."""
import json
from services.nee_documentales import clave, identificar


def opciones(doc):
    ids = {str(a['ID_Alumno']) for a in doc['datos']['Alumnos']}
    catalogo=doc.get('metadatos',{}).get('catalogo_nee_actual')
    if isinstance(catalogo,list):return [dict(r) for r in catalogo if str(r.get('alumno')) in ids]
    result = []
    vistos = set()
    for f in doc.get('metadatos', {}).get('fuentes', []):
        if f.get('tipo') not in ('EPP', 'EPP_ESCANEADA') or not f.get('vinculo_verificado'): continue
        if f.get('tipo') == 'EPP' and f.get('parte') != 'Conclusión': continue
        aid = str(f.get('alumno', ''))
        if aid not in ids: continue  # Nunca atribuir un registro colectivo a uno de sus alumnos.
        try: rows = json.loads(f.get('texto', '{}')).get('NEE', [])
        except (ValueError, AttributeError, TypeError): continue
        if not isinstance(rows, list): continue
        for i,r in enumerate(rows):
            if not isinstance(r, dict): continue
            need = str(r.get('NEE', '')).strip()
            if not need or len(need) > 2000: continue
            if r.get('Estado','Validada')!='Validada':continue
            key = (aid, clave(need))
            if key in vistos: continue
            vistos.add(key)
            result.append({'id':r.get('ID_NEE') or identificar(f.get('documento_origen',f.get('registro','')),aid,i),
                           'texto': need, 'alumno': aid, 'referencia': f.get('referencia', ''),
                           'fundamento':r.get('Fundamento',''),'pagina':r.get('Página',''),
                           'validada_en':r.get('Validada_En',f.get('fecha','')),
                           'documento': f.get('documento_origen', f.get('registro', '')),
                           'revision': f.get('revision', ''), 'fecha': f.get('fecha', ''), 'tipo': f['tipo']})
    return result


def actualizar_catalogo(doc):
    """Una consulta al abrir, sin OCR ni reemplazar texto/selecciones históricas."""
    from copy import deepcopy
    from services import planeacion as s
    from services.documentos_sintesis import fuentes_epp
    s.autorizar(doc)
    result=deepcopy(doc)
    ids={str(a['ID_Alumno']) for a in doc['datos']['Alumnos']}
    nuevos=fuentes_epp(ids,doc['datos']['Curso escolar'])
    fuentes=[f for f in doc['metadatos'].get('fuentes',[]) if f.get('tipo')=='EPP']
    for f in nuevos:
        f['vinculo_verificado']=True;f['referencia']='EPP escaneada · '+f['documento_origen'][:8]
    contexto={'datos':doc['datos'],'metadatos':{'fuentes':fuentes+nuevos}}
    result['metadatos']['catalogo_nee_actual']=opciones(contexto)
    return result

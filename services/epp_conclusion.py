"""Ensamblaje interdisciplinario sin alterar las aportaciones de cada área."""
from copy import deepcopy
import hashlib
import json
import re
from services.epp_modelo import AREAS, CONCLUSION, NEE, BAP, validar_parte


def fuentes(doc):
    result=[]
    for area in AREAS:
        p=doc['partes'].get(area,{}).get('contenido',{})
        items=[(k,str(v).strip()) for k,v in p.get('campos',{}).items() if str(v).strip()]
        if str(p.get('sintesis','')).strip():items.append(('Síntesis',p['sintesis']))
        items.extend(('Evaluación '+str(e.get('nombre','')),str(e.get('texto','')).strip())
            for e in p.get('evaluaciones',[]) if str(e.get('texto','')).strip())
        # Presupuesto por área: la primera nunca desplaza a las últimas.
        limite=max(1,(2300-sum(len(k)+4 for k,_ in items))//max(1,len(items)))
        body='\n'.join(k+': '+v[:limite] for k,v in items)
        result.append({'tipo':'EPP','referencia':area,'alcance':'área revisada' if p.get('validada') else 'hallazgos pendientes de revisión',
            'texto':body or 'Sin hallazgos registrados en esta área; no inferir resultados.'})
    if not any(p['texto']!='Sin hallazgos registrados en esta área; no inferir resultados.' for p in result):
        raise ValueError('Todavía no hay hallazgos del equipo para redactar la conclusión.')
    return result


def incorporar(value, propuesta, revisiones):
    """Actualiza el borrador solicitado; conserva textos anteriores y filas humanas."""
    result=deepcopy(value)
    anteriores=result.setdefault('campos',{})
    previas=result.get('propuesta_conclusion_ia',{})
    for campo in CONCLUSION:
        text=propuesta.get('campos',{}).get(campo,'').strip()
        if text:anteriores[campo]=text
    for name,cols,key in [('nee',NEE,'NEE'),('bap',BAP,'Tipo de barrera')]:
        old=set(previas.get(name,[]))
        rotulo='Aspectos' if name=='nee' else 'Contextos'
        rows=[deepcopy(r) for r in result.get(name,[]) if any(str(v).strip() for k,v in r.items() if k!=rotulo) and firma(r) not in old]
        usados={re.sub(r'\s+',' ',str(r.get(key,'')).strip()).casefold() for r in rows}
        for row in propuesta.get(name,[]):
            norm=re.sub(r'\s+',' ',str(row.get(key,'')).strip()).casefold()
            if norm and norm not in usados:rows.append({c:str(row.get(c,'')) for c in cols});usados.add(norm)
        result[name]=rows
    if not any(str(v).strip() for v in propuesta.get('campos',{}).values()) and not propuesta.get('nee'):
        raise ValueError('La IA no devolvió una conclusión ni NEE sustentadas. Revisa los hallazgos; el informe no cambió.')
    # Solo huellas; las versiones anteriores ya están en el diario del informe.
    result['propuesta_conclusion_ia']={k:[firma(r) for r in propuesta.get(k,[])] for k in ('nee','bap')}
    result['revisiones_propuesta_ia']=deepcopy(revisiones)
    result['pendientes_ia']=propuesta.get('faltantes',[])
    result['validada']=False
    return validar_parte('Conclusión',result)


def firma(row):
    return hashlib.sha256(json.dumps(row,ensure_ascii=False,sort_keys=True).encode()).hexdigest()

"""Minimización y propuesta por apartado, solo con ideas y resultados registrados."""
import re
from services.epp_modelo import campos

def preparar(doc,area,campo,ideas=''):
    from services import epp as s
    from services.epp_colaborativa import puede
    a=s.autorizar(doc)
    if campo not in campos(area) or not (puede(a,area,'campos',campo) or area=='Conclusión' and s.es_coordinadora(doc)):
        raise PermissionError('Este apartado no está habilitado para tu función.')
    partes=doc['partes'];contenido=partes.get(area,{}).get('contenido',{})
    lineas=['Apartado: '+campo]
    if ideas.strip():lineas.append('Ideas de la persona docente: '+ideas.strip()[:2500])
    if contenido.get('campos',{}).get(campo) and not contenido.get('no_requeridos',{}).get(campo):
        lineas.append('Redacción actual del apartado: '+contenido['campos'][campo][:2000])

    inst_aplicados = str(contenido.get('instrumentos', '') or '').strip()
    if inst_aplicados:
        lineas.append('Instrumentos aplicados en ' + area + ':\n' + inst_aplicados[:1000])

    evals = contenido.get('evaluaciones', [])
    if evals:
        hallazgos_evals = []
        for i, ev in enumerate(evals, 1):
            nom = ev.get('nombre', f'Evaluación {i}')
            txt = str(ev.get('texto', '') or '').strip()
            if txt:
                hallazgos_evals.append(f"[{nom}]:\n{txt[:2500]}")
        if hallazgos_evals:
            lineas.append('Hallazgos documentados de instrumentos cargados a la plataforma:\n' + '\n\n'.join(hallazgos_evals)[:5000])

    areas=('Aprendizaje','Psicología','Comunicación','Trabajo Social') if area=='Conclusión' else tuple(dict.fromkeys([area,a['area']]))
    for origen in areas:
        if origen == area and evals:
            continue
        v=partes.get(origen,{}).get('contenido',{})
        datos=[]
        if v.get('sintesis'):datos.append('Síntesis: '+v['sintesis'][:800])
        datos.extend(k+': '+str(t)[:400] for k,t in v.get('campos',{}).items() if t and k!=campo and not v.get('no_requeridos',{}).get(k))
        for i,e in enumerate(v.get('evaluaciones',[]),1):
            if e.get('texto'):datos.insert(0,'EV'+str(i)+f" ({e.get('nombre', 'Prueba')}): "+e['texto'][:1000])
        if datos:lineas.append(origen+' · hallazgos registrados: '+'\n'.join(datos)[:2500])
    if len(lineas)==1:raise ValueError('Escribe tus ideas o incorpora primero resultados de evaluación. No se inventarán hallazgos.')
    text='\n\n'.join(lineas)[:12000]
    alumno=s.alumno_autorizado(doc['alumno'])
    privados=[str(v) for k,v in alumno.items() if any(p in k.lower() for p in ('nombre','curp','domicilio','direccion','telefono','correo','id_')) and v]
    for parte in partes.values():
        if parte.get('autor'):privados.append(parte['autor'])
        for k,v in parte.get('contenido',{}).get('generales',{}).items():
            if v and any(p in k.lower() for p in ('nombre','domicilio')):privados.append(v)
    for token in sorted(set(privados),key=len,reverse=True):
        text=re.sub(r'(?<!\w)'+re.escape(token)+r'(?!\w)','[dato retirado]',text,flags=re.I)
    text=re.sub(r'\b[A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]\d\b','[CURP retirada]',text,flags=re.I)
    text=re.sub(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}','[contacto retirado]',text)
    text=re.sub(r'(?<!\d)(?:\+?52[\s-]*)?(?:\d[\s()-]*){10}(?!\d)','[contacto retirado]',text)
    return text

def generar(resumen,campo):
    from ai.planeacion import proponer
    if not isinstance(resumen,str) or not resumen.strip() or len(resumen)>12000:raise ValueError('Revisa el resumen antes de proponer redacción.')
    prompt=('Actúa como especialista de educación especial (USAER). Redacta el apartado '+campo+' para un Informe de Evaluación Psicopedagógica (EPP oficial SEGEY). '
            'Básate estrictamente en las observaciones, ideas y hallazgos de los instrumentos aplicados y registrados en la plataforma. '
            'Conserva los términos técnicos, edades de desarrollo, puntuaciones o hallazgos cualitativos indicados en los instrumentos (p. ej. WISC, Bender, DFH, pruebas de lenguaje o competencia curricular). '
            'Redacta de forma profesional, clara y pedagógica, distinguiendo fortalezas de barreras y necesidades de apoyo. No inventes antecedentes, diagnósticos ni datos no contenidos en el resumen. '
            'Devuelve JSON con la clave "redaccion", sin nombres propios ni identificadores personales.\nDATOS Y HALLAZGOS DE INSTRUMENTOS:\n'+resumen)
    def validar(r):
        if not isinstance(r,dict) or not isinstance(r.get('redaccion'),str) or not r['redaccion'].strip() or len(r['redaccion'])>6000:raise ValueError('La redacción no llegó completa; tu texto sigue intacto.')
        return r
    return proponer(resumen,'EPP','Redacción de apartado',_prompt=prompt,_schema={'type':'object','required':['redaccion'],'properties':{'redaccion':{'type':'string'}}},_validador=validar,_max_tokens=2000)['redaccion']

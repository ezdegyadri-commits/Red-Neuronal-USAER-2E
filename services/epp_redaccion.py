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

def generar(resumen, campo, area='Aprendizaje'):
    from ai.planeacion import proponer
    if not isinstance(resumen, str) or not resumen.strip() or len(resumen) > 12000:
        raise ValueError('Revisa el resumen antes de proponer redacción.')

    guias_rol = {
        'Aprendizaje': (
            'Especialista en Aprendizaje (Maestra de Apoyo). Focaliza en procesos de adquisición '
            'de la lectura, escritura, cálculo, estilo y ritmo de aprendizaje, competencia curricular (NEM) y barreras en el aula regular.'
        ),
        'Psicología': (
            'Especialista en Psicología. Focaliza en la esfera socioemocional, conducta adaptativa, '
            'funciones ejecutivas, dinámica vincular, autoconcepto, habilidades sociales y barreras actitudinales/escolares.'
        ),
        'Comunicación': (
            'Especialista en Comunicación y Lenguaje. Focaliza en los niveles del lenguaje (fonológico, '
            'semántico, morfosintáctico, pragmático), habla, voz, fluidez, sistemas alternativos/aumentativos (SAAC) y acceso comunicativo.'
        ),
        'Trabajo Social': (
            'Especialista en Trabajo Social. Focaliza en el contexto familiar y comunitario, dinámica '
            'de crianza, nivel socioeconómico, redes de apoyo, condiciones de habitabilidad y barreras contextuales del entorno.'
        ),
        'Conclusión': (
            'Equipo Interdisciplinario USAER. Síntesis colegiada integral que contrasta los hallazgos '
            'de todas las disciplinas para definir NEE (Fórmula SEGEY: Necesita + verbo infinitivo + qué) y BAP contextuales.'
        ),
    }
    enfoque_rol = guias_rol.get(area, f'Especialista de USAER en {area}')

    prompt = (
        f"Actúa como {enfoque_rol}.\n"
        f"Redacta el apartado oficial '{campo}' para un Informe de Evaluación Psicopedagógica (EPP oficial SEGEY).\n"
        f"Lineamientos pedagógicos rigurosos:\n"
        f"1. ROL Y PERSPECTIVA PROFESIONAL: Redacta estrictamente desde tu disciplina ({area}), respondiendo a las características particulares de la dimensión y apartado solicitado ('{campo}').\n"
        f"2. SUSTENTO DOCUMENTAL EN INSTRUMENTOS: Básate de forma directa y fehaciente en los hallazgos de las pruebas, escalas, baterías o instrumentos aplicados (ej. WISC, Bender, DFH, evaluación curricular, pruebas de lenguaje) registrados en la plataforma.\n"
        f"3. ESTILO TÉCNICO Y ACCESIBLE: Redacta en tercera persona con lenguaje profesional y descriptivo, claro para docentes y familias, sin diagnósticos clínicos no sustentados ni adjetivos peyorativos.\n"
        f"4. FORTALEZAS Y BARRERAS: Distingue claramente las capacidades y fortalezas demostradas por el alumno frente a las barreras del entorno o necesidades específicas de apoyo.\n"
        f"Devuelve exclusivamente un objeto JSON con la clave 'redaccion', sin nombres propios ni datos identificadores.\n\n"
        f"HALLAZGOS, INSTRUMENTOS Y OBSERVACIONES REGISTRADAS:\n" + resumen
    )

    def validar(r):
        if not isinstance(r, dict) or not isinstance(r.get('redaccion'), str) or not r['redaccion'].strip() or len(r['redaccion']) > 6000:
            raise ValueError('La redacción no llegó completa; tu texto sigue intacto.')
        return r

    return proponer(
        resumen,
        'EPP',
        'Redacción de apartado',
        _prompt=prompt,
        _schema={'type': 'object', 'required': ['redaccion'], 'properties': {'redaccion': {'type': 'string'}}},
        _validador=validar,
        _max_tokens=2500,
    )['redaccion']


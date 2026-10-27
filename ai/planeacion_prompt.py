"""Instrucciones revisables y comunes a los motores de planeación."""
import hashlib
import json

VERSION_PROMPT = 'usaer-propuestas-2026-10-10-aplicacion-real-v4'
MAX_PROPUESTAS = 3

INSTRUCCIONES = '''ROL:
Eres un Especialista Técnico-Pedagógico en Educación Especial y Educación Inclusiva (USAER 02-E / CAM), Zona 001, Yucatán, alineado a los campos formativos y fases de la Nueva Escuela Mexicana (NEM, Plan de Estudio 2022/2025). Tu tarea es redactar las Necesidades Educativas Específicas (NEE), los PDA, los Descriptores de Logro y las Actividades, basándote ESTRICTAMENTE en los antecedentes clínicos y pedagógicos del expediente del alumno. Cero alucinación, cero plantillas genéricas o relleno.

REGLAS DE GENERACIÓN Y BLINDAJE PEDAGÓGICO:

1. ANCLAJE OBLIGATORIO A LOS ANTECEDENTES Y ORIGEN DUAL OBLIGATORIO DE LAS NEE:
   - Analiza el diagnóstico (ej. TEA, TDAH, Dificultades Severas de Aprendizaje, discapacidad) y la fase/grado del alumno proporcionados en el contexto (<evaluacion_psicopedagogica> y <contexto_documentado>).
   - FILTRO DE NIVEL REAL DE DESARROLLO (PROHIBIDO DESFASAR CONTENIDOS):
     • Si el alumno está en una etapa inicial (ej. presilábico, silábico o conteo básico hasta 50), las NEE deben enfocarse en adquirir lectura/escritura y concepto de número. Queda ESTRICTAMENTE PROHIBIDO proponer PDAs o actividades de "comprensión lectora de textos complejos", "redacción autónoma formal" o algoritmos abstractos. Circunscribe las propuestas a conciencia fonológica, correspondencia grafofonética, lectura mediada con portadores o conteo con correspondencia uno a uno y uso indispensable de material concreto manipulativo.
     • Si está en un nivel intermedio, enfocar en sílabas inversas/complejas, ortografía básica o valor posicional hasta unidades de millar.
     • Si está avanzado, enfocar en fluidez, comprensión crítica y resolución de problemas de suma/resta contextualizadas.
   - Las Necesidades Educativas Específicas (NEE) deben extraerse EXCLUSIVAMENTE de dos fuentes:
     • Fuente A: La Evaluación Psicopedagógica (EPP) [<evaluacion_psicopedagogica>: nivel de competencia curricular, estilo de aprendizaje, diagnóstico y barreras (BAP)].
     • Fuente B: El Contexto Documentado del alumno [<contexto_documentado>: eventos significativos, actas de visita del equipo de apoyo y hojas de sugerencias/acuerdos previos].
     *Nota crítica:* Si en los eventos significativos o en las actas de visita el docente o el equipo de apoyo ya redactó explícitamente una NEE detectada, tómala como base prioritaria absoluta.

2. PROHIBICIÓN ESTRICTA DE TEXTOS GENÉRICOS (ANTI-PLANTILLAS):
   - Queda ESTRICTAMENTE PROHIBIDO usar frases de relleno como "participa en una actividad vinculada al antecedente" o "el alumno realiza la acción propuesta por un medio accesible".
   - Cada PDA debe corresponder al programa sintético de la NEM alineado a la Fase real del alumno (Fase 3, 4 o 5). Si se proporcionan referentes curriculares seleccionados, vincula sus identificadores; no inventes otros.
   - Los Descriptores de Logro deben ser acciones observables y medibles, estructuradas como rúbricas: [Acción observable] + [Contenido/habilidad] + [Apoyo o material concreto] + [Criterio de logro] (ej. "Lee y escribe su nombre con apoyo de sílabas móviles", "Resuelve situaciones problemáticas de conteo utilizando fichas y material concreto"). NUNCA verbos vagos o teóricos como «comprender», «interiorizar», «asimilar» o «concientizar».

3. ESTRUCTURACIÓN DE ACTIVIDADES TANGIBLES Y MATERIAL CONCRETO (MARCO DUA Y ACTIVIDADES DIVERSIFICADAS):
   - Las actividades deben dividirse claramente por contexto (Aula regular, Aula de apoyo).
   - Deben incluir el uso explícito de recursos didácticos físicos adaptados a la NEE (ej. sílabas móviles, bloques base diez, fichas de conteo, tarjetas de imágenes, tableros ARASAAC, plastilina, reloj de aula). Cero software costoso o tecnología inaccesible.
   - La redacción de la actividad debe mostrar el andamiaje del docente con mediación explícita:
     • Inicio (5-10 min): activación visual o manipulativa con material concreto y anticipación de la tarea.
     • Desarrollo (20-25 min): andamiaje escalonado (ej. "El docente modela el procedimiento...", "El alumno manipula el material concreto...", "El alumno explica oralmente o muestra su resolución...") y ajuste razonable explícito.
     • Cierre (10 min): comprobación formativa observable (producto o evidencia tangible donde el alumno demuestre el avance).
     • Variante multinivel: apoyo ante dificultad y reto si consolida rápido.

4. SUBORDINACIÓN ESTRICTA A EDICIONES MANUALES DEL DOCENTE (<ediciones_manuales_docente>):
   - Si el docente ya modificó o estableció manualmente las NEE, los PDAs o los descriptores en la plataforma (mostrados en <ediciones_manuales_docente>), esos valores son VERDAD ABSOLUTA Y PRIORIDAD TOTAL. Subordina al 100% las actividades, apoyos y estrategias a esos datos manuales, descartando cualquier propuesta previa o por defecto.

5. TRAZABILIDAD Y SUSTENTO DOCUMENTAL OBLIGATORIO:
   - Ninguna necesidad, PDA, estrategia DUA ni actividad puede generarse por default.
   - Cada elemento debe incluir explícitamente su etiqueta de origen: [Sustento: EPP / Acta de visita / Evento significativo / Hoja de acuerdos], citando el hallazgo o fecha concreta del registro.

6. ORIENTACIÓN POR FUNCIÓN:
   - Aprendizaje (Maestra de Apoyo): Ajustes razonables al currículo NEM (Plan 2022/2025). Focaliza en lectura/escritura con apoyos visuales y manipulativos, pensamiento matemático con material concreto y participación en el aula regular.
   - Psicología: Acciones educativas socioemocionales de la Zona 001 (5 competencias: Conciencia, Regulación, Autonomía, Competencia social y Bienestar). NUNCA abordajes clínicos ni terapias diagnósticas.
   - Comunicación: Lenguaje funcional, habla y acceso a la comunicación escolar. Propón tableros temáticos con pictogramas (ARASAAC), estimulación focalizada y modelado.
   - Trabajo Social: Entorno sociofamiliar y derribo de BAP escolares y comunitarias. Acuerdos viables sin culpar a las familias ni imponerles cargas irreales.

ESTRUCTURA DE SALIDA REQUERIDA (JSON O MARKDOWN VINCULADO A LA TABLA):
1. NEE Prioritarias (Con base en el nivel real de competencia).
2. PDA (Alineado al contenido nacional y al nivel del alumno).
3. Descriptor de Logro (Conducta observable sin ambigüedades).
4. Secuencia de Actividades (Por contexto, incluyendo inicio, desarrollo, cierre y materiales).

Devuelve solo JSON con observaciones (texto breve), faltantes (lista de preguntas) y propuestas (hasta tres objetos). Cada propuesta incluye necesidad, objetivo, descriptor, actividad, contexto, temporalidad, recursos, evaluacion, fundamento (textos), fuentes y referentes (listas de identificadores incluidos).
'''



def solicitud(resumen, formato, area, revisar=False, curriculo=None):
    resumen = str(resumen).strip()
    if not resumen or len(resumen) > 60000:
        raise ValueError('Revisa el resumen educativo: debe contener entre 1 y 60 000 caracteres.')
    if formato not in ('XXI', 'XXIII', 'XXV'):
        raise ValueError('Selecciona un formato de planeación válido.')
    original = curriculo or {}
    # Identificadores y textos pertinentes; enlaces y metadatos se muestran localmente.
    fuentes = [{k: s[k] for k in ('id', 'titulo', 'organismo', 'edicion') if k in s}
               for s in original.get('fuentes', [])]
    referencias = [{k: r[k] for k in ('id', 'fuente', 'grado', 'fase', 'campo',
                    'contenido', 'pda', 'pagina_pdf', 'continuacion') if k in r}
                   for r in original.get('referentes_por_grado', [])]
    contexto = {k: original[k] for k in ('campo', 'campos', 'ejes', 'guia_local', 'aviso', 'grados_del_padron', 'contextualizacion_docente') if k in original}
    contexto.update(fuentes=fuentes, referentes_por_grado=referencias)
    modo = ('Revisa el trabajo descrito: señala hasta tres ajustes concretos y cómo realizarlos. '
            'Si el resumen no contiene la planeación a revisar, pide ese contenido.' if revisar
            else 'Propón actividades y apoyos educativos a partir de la evidencia.')
    contenido = json.dumps({'modo': modo, 'anexo': formato, 'funcion': str(area),
                            'referentes_oficiales': contexto, 'resumen_revisado': resumen},
                           ensure_ascii=False, sort_keys=True)
    return INSTRUCCIONES + '\nDATOS DE CONSULTA:\n' + contenido


def huella(resumen, formato, area, revisar=False, curriculo=None):
    contenido = VERSION_PROMPT + '\n' + solicitud(resumen, formato, area, revisar, curriculo)
    return hashlib.sha256(contenido.encode('utf-8')).hexdigest()


def validar_respuesta(data, curriculo=None):
    if not isinstance(data, dict) or not isinstance(data.get('propuestas'), list):
        raise ValueError('Respuesta sin estructura de propuestas.')
    originales = data['propuestas']
    if len(originales) > MAX_PROPUESTAS:
        raise ValueError('Demasiadas propuestas en la respuesta.')
    if not isinstance(data.get('faltantes', []), list):
        raise ValueError('Lista de información faltante inválida.')
    campos = ('necesidad', 'objetivo', 'descriptor', 'actividad', 'contexto',
              'temporalidad', 'recursos', 'evaluacion', 'fundamento')
    fuentes = {s['id'] for s in (curriculo or {}).get('fuentes', [])}
    referentes = {r['id'] for r in (curriculo or {}).get('referentes_por_grado', [])}
    propuestas = []
    for p in originales:
        if not isinstance(p, dict) or any(not isinstance(p.get(k), str) or not p[k].strip() for k in campos):
            raise ValueError('La propuesta está incompleta.')
        if any(len(p[k]) > 2000 for k in campos):
            raise ValueError('La propuesta excede la extensión prevista.')
        if not isinstance(p.get('fuentes'), list) or not isinstance(p.get('referentes'), list):
            raise ValueError('Referencias inválidas.')
        if any(not isinstance(i, str) for i in p['fuentes'] + p['referentes']):
            raise ValueError('Identificador inválido.')
        if not set(p['fuentes']).issubset(fuentes) or not set(p['referentes']).issubset(referentes):
            raise ValueError('La propuesta cita un referente no suministrado.')
        if fuentes and not p['fuentes']:
            raise ValueError('La propuesta no cita su fundamento.')
        if referentes and not p['referentes']:
            raise ValueError('La propuesta no vincula los referentes seleccionados.')
        propuestas.append({**{k: p[k].strip() for k in campos},
                           'fuentes': list(dict.fromkeys(p['fuentes'])),
                           'referentes': list(dict.fromkeys(p['referentes']))})
    faltantes = [str(v)[:500] for v in data.get('faltantes', [])[:3]]
    observaciones = str(data.get('observaciones', ''))[:2000]
    if not propuestas and not (faltantes or observaciones.strip()):
        raise ValueError('Respuesta vacía.')
    return {'observaciones': observaciones, 'faltantes': faltantes, 'propuestas': propuestas}

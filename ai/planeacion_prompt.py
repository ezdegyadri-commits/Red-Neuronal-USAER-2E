"""Instrucciones revisables y comunes a los motores de planeación."""
import hashlib
import json

VERSION_PROMPT = 'usaer-propuestas-2026-10-10-aplicacion-real-v4'
MAX_PROPUESTAS = 3

INSTRUCCIONES = '''Eres un especialista técnico-pedagógico en educación inclusiva, educación especial (CAM / USAER) y diseño curricular adaptado de la USAER 02-E, Zona 001, Yucatán, alineado a los campos formativos y fases de la Nueva Escuela Mexicana (NEM, Plan de Estudio 2022/2025).
Tu función es construir la planeación pedagógica individual del alumno (NEE, PDA, descriptores de logro, DUA y actividades) con total fidelidad diagnóstica y apego estricto al expediente cargado. Cero alucinación, cero plantillas genéricas o relleno.

REGLAS DE ORO Y BLINDAJE PEDAGÓGICO OBLIGATORIO:

1. ORIGEN DUAL OBLIGATORIO DE LAS NEE:
   Las Necesidades Educativas Específicas (NEE) deben extraerse EXCLUSIVAMENTE de dos fuentes:
   - Fuente A: La Evaluación Psicopedagógica (EPP) [<evaluacion_psicopedagogica>: nivel de competencia curricular, estilo de aprendizaje, diagnóstico y barreras (BAP)].
   - Fuente B: El Contexto Documentado del alumno [<contexto_documentado>: eventos significativos, actas de visita del equipo de apoyo y hojas de sugerencias/acuerdos previos].
   *Nota crítica:* Si en los eventos significativos o en las actas de visita el docente o el equipo de apoyo ya redactó explícitamente una NEE detectada, tómala como base prioritaria absoluta.

2. FILTRO DE NIVEL REAL DE DESARROLLO (PROHIBIDO DESFASAR CONTENIDOS):
   Antes de proponer cualquier PDA, descriptor o actividad, verifica rigurosamente qué sabe y qué NO sabe hacer el alumno según sus registros:
   - Si el expediente indica que el alumno NO ha consolidado la lectoescritura (ej. nivel presilábico o silábico), queda ESTRICTAMENTE PROHIBIDO proponer PDAs o actividades de "comprensión lectora de textos", "redacción autónoma", lectura convencional o resúmenes. Circunscribe las propuestas a conciencia fonológica, asociación grafofonética, lectura mediada o identificación en portadores de texto según su nivel real.
   - Si en matemáticas se reporta que NO domina el concepto de número o valor posicional, queda ESTRICTAMENTE PROHIBIDO proponer operaciones abstractas, algoritmos formales o resolución de problemas complejos; enfócate en conteo con correspondencia uno a uno, seriación, clasificación, agrupación y uso indispensable de material concreto manipulativo.

3. TRAZABILIDAD Y SUSTENTO DOCUMENTAL OBLIGATORIO:
   Ninguna necesidad, PDA, estrategia DUA ni actividad puede generarse por default.
   Cada elemento debe incluir explícitamente su etiqueta de origen: [Sustento: EPP / Acta de visita / Evento significativo / Hoja de acuerdos], citando el hallazgo o fecha concreta del registro.

4. SUBORDINACIÓN ESTRICTA A EDICIONES MANUALES DEL DOCENTE (<ediciones_manuales_docente>):
   Si el docente ya modificó o estableció manualmente las NEE, los PDAs o los descriptores en la plataforma (mostrados en <ediciones_manuales_docente>), esos valores son VERDAD ABSOLUTA. Subordina al 100% las actividades, apoyos y estrategias DUA a esos cambios manuales, descartando cualquier propuesta previa o por defecto.

5. MARCO DUA Y ACTIVIDADES DIVERSIFICADAS (CERO REPETICIÓN O FRASES VACÍAS):
   - Queda prohibido repetir la misma actividad con diferente redacción o usar frases vacías como "usar material visual" o "fomentar la participación".
   - Genera actividades progresivas y diferenciadas.
   - Principio I (Compromiso / Motivación): Basado en los intereses reales y disparadores/autorregulación documentados.
   - Principio II (Representación): Modalidades visuales, auditivas y manipulativas concretas según las sugerencias del equipo.
   - Principio III (Acción y Expresión): Opciones de ejecución y andamiaje acordes a las posibilidades comunicativas y motrices.
   - Cada actividad debe detallar:
     • Inicio (5-10 min): activación con material visual o manipulativo concreto y anticipación de la tarea.
     • Desarrollo (20-25 min): mediación docente paso a paso con andamiaje (instrucciones segmentadas, modelado "Yo hago, Hacemos, Tú haces", apoyos gráficos o trabajo en binas) y ajuste razonable explícito.
     • Cierre (10 min): comprobación formativa observable (producto o evidencia tangible donde el alumno demuestre el avance).
   - Recursos: únicamente materiales escolares comunes y accesibles (cuaderno, tijeras, tarjetas ilustradas, fichas, plastilina, rotafolio, reloj de aula). Cero software costoso o tecnología inaccesible.

6. REDACCIÓN PEDAGÓGICA PRECISA Y OBSERVABLE:
   - Objetivos redactados en presente observable («El alumno señala, ordena, clasifica, comunica con apoyo de, resuelve con fichas»). NUNCA verbos vagos o teóricos como «comprender», «interiorizar», «asimilar» o «concientizar».
   - El descriptor de logro debe indicar cómo reconocer el avance de forma tangible: [Acción observable] + [Contenido/habilidad] + [Apoyo o material concreto] + [Criterio de logro].

7. ORIENTACIÓN POR FUNCIÓN:
   - Aprendizaje (Maestra de Apoyo): Ajustes razonables al currículo NEM (Plan 2022/2025). Focaliza en lectura/escritura con apoyos visuales, pensamiento matemático con material concreto y participación en el aula regular.
   - Psicología: Acciones educativas socioemocionales de la Zona 001 (5 competencias: Conciencia, Regulación, Autonomía, Competencia social y Bienestar). Dinámicas escolares reales (termómetro de emociones, rincón de la calma, acuerdos de convivencia). NUNCA abordajes clínicos ni terapias diagnósticas.
   - Comunicación: Lenguaje funcional, habla y acceso a la comunicación escolar. Propón tableros temáticos con pictogramas (ARASAAC), estimulación focalizada y modelado.
   - Trabajo Social: Entorno sociofamiliar y derribo de BAP escolares y comunitarias. Acuerdos de corresponsabilidad viables sin culpar a las familias ni imponerles cargas irreales.

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

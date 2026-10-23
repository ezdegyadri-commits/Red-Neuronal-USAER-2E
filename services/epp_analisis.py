"""Análisis de evaluaciones escaneadas, distribución por áreas de EPP y propuesta de NEE oficial SEGEY.

Principio: Capturar una vez y reutilizar. Del escaneo se identifican instrumentos normativos
y se canalizan los hallazgos a los apartados correspondientes del Manual USAER (Anexos XVII y XVIII),
redactando la propuesta de NEE con la fórmula oficial SEGEY: [Necesita + verbo observable + contenido pedagógico].
"""
import hashlib
import re
from copy import deepcopy
from services.epp_modelo import AREAS, SECCIONES, CONCLUSION, NEE, BAP, vacia

REGLAS_INSTRUMENTOS = [
    {
        'patron': r'\b(?:wisc|wechsler|ci\b|cociente intelectual|comprensi[oó]n verbal|memoria de trabajo|velocidad de procesamiento|razonamiento perceptual)\b',
        'instrumento': 'Escala Wechsler de Inteligencia para Niños (WISC-IV)',
        'area': 'Psicología',
        'campos': ['3.1. Atención', '3.2. Memoria', '3.4. Razonamiento', '3.5. Cociente intelectual']
    },
    {
        'patron': r'\b(?:raven|matrices progresivas|escala coloreada|escala general)\b',
        'instrumento': 'Test de Matrices Progresivas Raven',
        'area': 'Psicología',
        'campos': ['3.3. Percepción', '3.4. Razonamiento', '3.5. Cociente intelectual']
    },
    {
        'patron': r'\b(?:bender|visomotor|visomotora|maduraci[oó]n visomotriz|koppitz)\b',
        'instrumento': 'Prueba Visomotora Bender',
        'area': 'Psicología',
        'campos': ['3.3. Percepción', '4.3. Coordinación motriz fina', '4.3. Noción corporal']
    },
    {
        'patron': r'\b(?:dfh|figura humana|dibujo de la figura humana|goodenough|machover)\b',
        'instrumento': 'Dibujo de la Figura Humana (DFH)',
        'area': 'Psicología',
        'campos': ['3.6. Etapa de desarrollo', '4.2. Autoestima', '4.2. Autoconcepto', '4.3. Noción corporal']
    },
    {
        'patron': r'\b(?:figura compleja|rey-osterrieth|test de rey)\b',
        'instrumento': 'Test de la Figura Compleja (Rey)',
        'area': 'Psicología',
        'campos': ['3.1. Atención', '3.2. Memoria', '3.3. Percepción', '4.3. Coordinación motriz fina']
    },
    {
        'patron': r'\b(?:frostig|dptv|percepci[oó]n visual|constancia de forma|posici[oó]n en el espacio)\b',
        'instrumento': 'Test de Desarrollo de la Percepción Visual (Frostig)',
        'area': 'Psicología',
        'campos': ['3.3. Percepción', '4.3. Coordinación motriz fina']
    },
    {
        'patron': r'\b(?:abas|vineland|maduraci[oó]n social|conducta adaptativa|habilidades pr[aá]cticas|habilidades conceptuales|habilidades sociales)\b',
        'instrumento': 'Evaluación de la Conducta Adaptativa (ABAS-II / Vineland)',
        'area': 'Psicología',
        'campos': ['4.1. Autodirección', '4.2. Relaciones interpersonales', '4.2. Cumplimiento de normas', '4.2. Responsabilidad', '4.2. Identificación y autorregulación de emociones', '4.2. Autodeterminación']
    },
    {
        'patron': r'\b(?:bas|bater[ií]as de socializaci[oó]n|socializaci[oó]n)\b',
        'instrumento': 'Baterías de Socialización (BAS 1, 2 y 3)',
        'area': 'Psicología',
        'campos': ['4.2. Relaciones interpersonales', '4.2. Cumplimiento de normas', '4.2. Responsabilidad']
    },
    {
        'patron': r'\b(?:flores|laiz|fonol[oó]gico|morfosint[aá]ctico|sem[aá]ntico|pragm[aá]tico|articulaci[oó]n|habla|intenci[oó]n comunicativa|comprensi[oó]n expresiva|receptiva|saac|matriz de comunicaci[oó]n)\b',
        'instrumento': 'Evaluación de la comunicación y el lenguaje (Flores / Laiz / SEGEY)',
        'area': 'Comunicación',
        'campos': ['4.1. Comunicación y lenguaje: intención comunicativa', '4.1. Lenguaje oral: fonológico', '4.1. Lenguaje oral: morfosintáctico', '4.1. Lenguaje oral: semántico', '4.1. Lenguaje oral: pragmático', '4.1. Comprensión expresiva', '4.1. Comprensión receptiva']
    },
    {
        'patron': r'\b(?:estudio social|anexo xii|anexo xi|bap sociofamiliar|visita domiciliaria|entrevista a padres|embarazo|parto|autocuidado|contexto familiar)\b',
        'instrumento': 'Estudio Social y Cuestionario de BAP Sociofamiliar (Anexos XI y XII)',
        'area': 'Trabajo Social',
        'campos': ['2.1. Embarazo', '2.2. Parto', '2.3. Apariencia física', '2.4. Salud', '4.3. Autocuidado', '4.3. Actividades en la casa', '4.3. Utilización de la comunidad', '6.2. Contexto familiar', '6.3. Contexto social']
    },
    {
        'patron': r'\b(?:competencia curricular|estilo de aprendizaje|anexo xiv|anexo xiii|macotela|lectura funcional|matem[aá]ticas funcionales|escritura funcional|c[aá]lculo)\b',
        'instrumento': 'Evaluación de Competencia Curricular y Estilo de Aprendizaje (Anexo XIV)',
        'area': 'Aprendizaje',
        'campos': ['4.1. Lectura y escritura funcional', '4.1. Matemáticas funcionales', '5.1. Competencia curricular', '5.2. Estilo de aprendizaje', '6.1. Contexto escolar']
    }
]


def identificar_instrumento_y_areas(texto, area_usuario=None):
    """Detecta instrumentos aplicados y apartados de la EPP susceptibles de llenado."""
    texto_low = str(texto or '').lower()
    coincidencias = []
    for regla in REGLAS_INSTRUMENTOS:
        if area_usuario and regla['area'] != area_usuario:
            continue
        if re.search(regla['patron'], texto_low, re.IGNORECASE):
            coincidencias.append({
                'instrumento': regla['instrumento'],
                'area': regla['area'],
                'campos': regla['campos']
            })
    if not coincidencias and area_usuario:
        campos_area = [f for areas in SECCIONES.values() for f in areas.get(area_usuario, [])]
        coincidencias.append({
            'instrumento': f'Evaluación diagnóstica de {area_usuario}',
            'area': area_usuario,
            'campos': campos_area[:5]
        })
    return coincidencias


def distribuir_hallazgos_en_epp(area, texto, campos_actuales):
    """Distribuye párrafos de la prueba en los campos de la EPP respetando lo existente."""
    campos_nuevos = deepcopy(campos_actuales)
    parrafos = [p.strip() for p in str(texto or '').split('\n\n') if len(p.strip()) > 20]
    if not parrafos:
        parrafos = [p.strip() for p in str(texto or '').split('\n') if len(p.strip()) > 25]

    identificados = identificar_instrumento_y_areas(texto, area)
    campos_objetivo = []
    for match in identificados:
        for c in match['campos']:
            if c in campos_nuevos and c not in campos_objetivo:
                campos_objetivo.append(c)

    if not campos_objetivo:
        campos_objetivo = [f for areas in SECCIONES.values() for f in areas.get(area, [])]

    mapeo_terminos = {
        'Atención': ['atención', 'concentración', 'focalización', 'distracción'],
        'Memoria': ['memoria', 'retención', 'evocación', 'dígitos'],
        'Percepción': ['percepción', 'visomotor', 'figura', 'fondo', 'espacial', 'visual'],
        'Razonamiento': ['razonamiento', 'lógica', 'analogías', 'matrices', 'resolución'],
        'Cociente': ['cociente', 'ci', 'percentil', 'puntuación escalar', 'rango'],
        'Desarrollo': ['desarrollo', 'etapa', 'edad madurativa', 'esquema'],
        'Fonológico': ['fonológico', 'articulación', 'fonema', 'pronunciación', 'sustitución'],
        'Morfosintáctico': ['morfosintáctico', 'oración', 'sintaxis', 'estructura', 'concordancia'],
        'Semántico': ['semántico', 'vocabulario', 'concepto', 'definición', 'categoría'],
        'Pragmático': ['pragmático', 'intención', 'comunicación', 'contacto', 'interacción'],
        'Comprensión': ['comprensión', 'expresiva', 'receptiva', 'órdenes', 'instrucciones'],
        'Curricular': ['competencia', 'pda', 'grado', 'contenidos', 'lectura', 'matemáticas'],
        'Estilo': ['estilo', 'canal', 'visual', 'auditivo', 'kinestésico', 'motivación'],
        'Familiar': ['familia', 'padres', 'hogar', 'madre', 'padre', 'hermanos', 'dinámica'],
        'Salud': ['salud', 'enfermedad', 'médico', 'alergia', 'tratamiento', 'parto', 'embarazo'],
        'Motriz': ['motriz', 'coordinación', 'fina', 'gruesa', 'trazo', 'postura'],
    }

    asignados = set()
    for parrafo in parrafos:
        p_low = parrafo.lower()
        mejor_campo = None
        for campo in campos_objetivo:
            for clave, palabras in mapeo_terminos.items():
                if clave.lower() in campo.lower():
                    if any(w in p_low for w in palabras):
                        mejor_campo = campo
                        break
            if mejor_campo:
                break
        if not mejor_campo and campos_objetivo:
            candidatos = [c for c in campos_objetivo if c not in asignados]
            mejor_campo = candidatos[0] if candidatos else campos_objetivo[0]

        if mejor_campo:
            actual = str(campos_nuevos.get(mejor_campo, '') or '').strip()
            if actual:
                if parrafo not in actual:
                    campos_nuevos[mejor_campo] = actual + '\n\n' + parrafo
            else:
                campos_nuevos[mejor_campo] = parrafo
            asignados.add(mejor_campo)

    return campos_nuevos


def proponer_nee_segey(doc):
    """Genera propuesta de Conclusión y NEE con fórmula oficial SEGEY a partir de aportaciones del equipo."""
    partes = doc.get('partes', {})
    textos_areas = {}
    for area in AREAS:
        contenido = partes.get(area, {}).get('contenido', {})
        textos_campos = [f"{k}: {v}" for k, v in contenido.get('campos', {}).items() if str(v).strip()]
        sintesis = contenido.get('sintesis', '')
        if sintesis:
            textos_campos.append(f"Síntesis: {sintesis}")
        textos_areas[area] = '\n'.join(textos_campos)

    propuesta_nee = []

    # 1. Funcionamiento Intelectual
    txt_psi = textos_areas.get('Psicología', '').lower()
    if 'atención' in txt_psi or 'concentración' in txt_psi:
        nee_intelectual = 'Necesita focalizar y mantener periodos de atención sostenida en actividades académicas mediante apoyos visuales y consignas estructuradas.'
    elif 'razonamiento' in txt_psi or 'lógica' in txt_psi:
        nee_intelectual = 'Necesita consolidar el razonamiento lógico-concreto mediante material manipulativo y modelado explícito paso a paso.'
    else:
        nee_intelectual = 'Necesita afianzar procesos de procesamiento de la información mediante instrucciones segmentadas y mediación pedagógica constante.'
    propuesta_nee.append({
        'Aspectos': 'Funcionamiento intelectual',
        'Características relevantes': 'Ritmo de aprendizaje y estilo de procesamiento observados en las valoraciones.',
        'NEE': nee_intelectual,
        'Apoyos': 'Instrucciones breves, apoyos visuales, segmentación de actividades.',
        'Ajustes razonables': 'Dosificación del tiempo de trabajo y ubicación áulica estratégica.',
        'Responsables': 'Maestra de apoyo y Maestro de grupo regular',
        'Fecha o período': 'Ciclo escolar 2026-2027'
    })

    # 2. Habilidades conceptuales (Lectura, escritura, matemáticas)
    txt_apr = textos_areas.get('Aprendizaje', '').lower()
    if 'lectura' in txt_apr or 'alfabético' in txt_apr or 'escritura' in txt_apr:
        nee_conceptual = 'Necesita consolidar la alfabetización inicial y la comprensión de textos breves mediante mediación fonológica y vocabulario contextualizado.'
    elif 'matemática' in txt_apr or 'cálculo' in txt_apr or 'número' in txt_apr:
        nee_conceptual = 'Necesita construir la noción de número y resolución de problemas cotidianos mediante material concreto y secuencias gráficas.'
    else:
        nee_conceptual = 'Necesita acceder a los contenidos curriculares del grado mediante adaptaciones metodológicas y apoyos didácticos diversificados.'
    propuesta_nee.append({
        'Aspectos': 'Habilidades conceptuales de conducta adaptativa',
        'Características relevantes': 'Desempeño en competencias comunicativas y de pensamiento matemático funcional.',
        'NEE': nee_conceptual,
        'Apoyos': 'Material lúdico-manipulativo, guías paso a paso, lectura compartida.',
        'Ajustes razonables': 'Adaptación en longitud y complejidad de actividades escritas.',
        'Responsables': 'Maestra de apoyo y Docente regular',
        'Fecha o período': 'Trimestres 1, 2 y 3'
    })

    # 3. Habilidades sociales y afectivas
    if 'emocion' in txt_psi or 'regulación' in txt_psi or 'social' in txt_psi or 'frustración' in txt_psi:
        nee_social = 'Necesita reconocer y autorregular estados emocionales ante situaciones de frustración o reto escolar mediante estrategias de contención y acuerdos grupales.'
    else:
        nee_social = 'Necesita interactuar y cooperar asertivamente con sus pares en tareas colaborativas respetando turnos y normas áulicas.'
    propuesta_nee.append({
        'Aspectos': 'Habilidades sociales de conducta adaptativa',
        'Características relevantes': 'Respuestas socioemocionales e interacción con compañeros y figuras de autoridad.',
        'NEE': nee_social,
        'Apoyos': 'Refuerzo positivo, pausas activas, mediación docente en conflictos.',
        'Ajustes razonables': 'Uso de termómetro de emociones y asignación de roles colaborativos.',
        'Responsables': 'Psicología, Docente regular y Familia',
        'Fecha o período': 'Permanente'
    })

    # 4. Habilidades prácticas (Comunicación / Vida diaria / Motricidad)
    txt_com = textos_areas.get('Comunicación', '').lower()
    if 'articulación' in txt_com or 'fonem' in txt_com or 'habla' in txt_com:
        nee_practica = 'Necesita articular con precisión los fonemas esperados para su edad y estructurar enunciados completos mediante modelado y retroalimentación auditiva.'
    elif 'saac' in txt_com or 'alternativo' in txt_com:
        nee_practica = 'Necesita emplear un sistema aumentativo/alternativo de comunicación estructurado para expresar necesidades y deseos en contextos escolar y familiar.'
    else:
        nee_practica = 'Necesita fortalecer la autonomía personal y la coordinación visomotriz fina en tareas de trazo y actividades de vida diaria escolar.'
    propuesta_nee.append({
        'Aspectos': 'Habilidades prácticas de conducta adaptativa',
        'Características relevantes': 'Nivel de autonomía personal, comunicación funcional y destrezas motrices cotidianas.',
        'NEE': nee_practica,
        'Apoyos': 'Modelado comunicativo, ejercicios articulatorios funcionales y rutinas estables.',
        'Ajustes razonables': 'Tableros de comunicación / adaptadores de trazo si se requieren.',
        'Responsables': 'Área de Comunicación y Docente de grupo',
        'Fecha o período': 'Ciclo escolar 2026-2027'
    })

    # 5. Funcionamiento Académico
    propuesta_nee.append({
        'Aspectos': 'Funcionamiento académico',
        'Características relevantes': 'Nivel de competencia curricular y respuesta al estilo de enseñanza áulico.',
        'NEE': 'Necesita diversificar las formas de representación y expresión del aprendizaje bajo enfoque DUA para participar plenamente en las actividades del aula.',
        'Apoyos': 'Diseño Universal para el Aprendizaje, consignas multimodal (visual, auditivo, kinestésico).',
        'Ajustes razonables': 'Evaluación formativa diferenciada y apoyos específicos en PDA.',
        'Responsables': 'Equipo interdisciplinario USAER y Docente regular',
        'Fecha o período': 'Ciclo escolar 2026-2027'
    })

    # Propuesta de BAP
    propuesta_bap = [
        {
            'Contextos': 'Áulico',
            'Tipo de barrera': 'Metodológica / Pedagógica',
            'Acciones generales': 'Implementar estrategias DUA en las planeaciones de aula regular, diversificando materiales y tiempos.',
            'Responsables': 'Docente regular y Maestra de apoyo',
            'Fecha o período': 'Ciclo escolar 2026-2027'
        },
        {
            'Contextos': 'Escolar',
            'Tipo de barrera': 'Organización escolar y actitudinal',
            'Acciones generales': 'Promover un ambiente inclusivo y sensibilizar a la comunidad escolar sobre la diversidad y apoyos específicos.',
            'Responsables': 'Director, Colectivo docente y USAER',
            'Fecha o período': 'Trimestre 1'
        },
        {
            'Contextos': 'Familiar',
            'Tipo de barrera': 'Información y acompañamiento',
            'Acciones generales': 'Establecer canales de comunicación sistemáticos y orientar a la familia con sugerencias prácticas para el hogar.',
            'Responsables': 'Trabajo Social y Psicología',
            'Fecha o período': 'Permanente'
        },
        {
            'Contextos': 'Social',
            'Tipo de barrera': 'Acceso a oportunidades comunitarias',
            'Acciones generales': 'Vincular apoyos complementarios e incentivar la participación activa en eventos socioculturales de la comunidad.',
            'Responsables': 'Trabajo Social y Familia',
            'Fecha o período': 'Ciclo escolar 2026-2027'
        }
    ]

    conclusion_txt = (
        'A partir de la evaluación psicopedagógica interdisciplinaria, se determina que el alumno '
        'manifiesta fortalezas importantes que constituyen el punto de partida pedagógico. Requiere apoyos '
        'específicos para superar barreras en el aprendizaje y la participación (BAP) y consolidar las NEE acordadas '
        'por el equipo de USAER en corresponsabilidad con el personal de la escuela regular y la familia.'
    )

    campos_conclusion = {
        '7.1. Conclusión': conclusion_txt,
        'Énfasis de atención acordado': 'Atención interdisciplinaria combinada (individual y en contexto áulico) con seguimiento periódico a las NEE.',
        'Asociación educativa sustentada': 'Determinada con base en los instrumentos normativos aplicados y las evidencias recopiladas por las cuatro áreas de atención.',
        'Acuerdos y apoyos del equipo': 'Sesiones de acompañamiento docente, ajustes metodológicos bajo enfoque DUA y entrega de sugerencias a la familia.'
    }

    return {
        'campos': campos_conclusion,
        'nee': propuesta_nee,
        'bap': propuesta_bap
    }


def incorporar_prueba_a_epp(doc, area, texto, nombre_instrumento=None, fecha_aplicacion=None, auto_actualizar_conclusion=True):
    """Incorpora los hallazgos de una prueba (escaneada o directa) en el documento de EPP.
    Distribuye los hallazgos en los campos correspondientes del área, agrega el instrumento
    a la lista de instrumentos aplicados, añade la evaluación al registro y actualiza la propuesta
    de NEE oficial SEGEY.
    """
    if area not in AREAS:
        raise ValueError(f"Área '{area}' no válida para evaluación psicopedagógica.")

    texto_limpio = str(texto or '').strip()
    if not texto_limpio:
        raise ValueError("El texto o transcripción de la prueba no contiene información para procesar.")

    # 1. Identificar instrumento si no se indicó
    if not nombre_instrumento or str(nombre_instrumento).strip() in ('', '(Escribir o mantener personalizado)'):
        matches = identificar_instrumento_y_areas(texto_limpio, area)
        if matches:
            nombre_instrumento = matches[0]['instrumento']
        else:
            nombre_instrumento = f"Evaluación diagnóstica de {area}"

    # 2. Obtener contenido actual del área
    parte = doc.setdefault('partes', {}).setdefault(area, {})
    contenido = parte.setdefault('contenido', vacia(area))
    campos_previos = dict(contenido.setdefault('campos', {}))

    # 3. Distribuir hallazgos en campos del área
    nuevos_campos = distribuir_hallazgos_en_epp(area, texto_limpio, campos_previos)
    contenido['campos'] = nuevos_campos

    campos_afectados = [c for c, v in nuevos_campos.items() if v != campos_previos.get(c, '')]

    # 4. Actualizar lista de instrumentos aplicados
    inst_actual = str(contenido.get('instrumentos', '') or '').strip()
    if nombre_instrumento not in inst_actual:
        if inst_actual:
            contenido['instrumentos'] = f"{inst_actual}\n• {nombre_instrumento}"
        else:
            contenido['instrumentos'] = f"• {nombre_instrumento}"

    # 5. Fecha de aplicación si se proporcionó
    if fecha_aplicacion and str(fecha_aplicacion).strip():
        f_actual = str(contenido.get('fecha_aplicacion', '') or '').strip()
        if str(fecha_aplicacion).strip() not in f_actual:
            contenido['fecha_aplicacion'] = f"{f_actual}, {fecha_aplicacion}".strip(', ') if f_actual else str(fecha_aplicacion).strip()

    # 6. Registrar en evaluaciones
    digest = hashlib.sha256(texto_limpio.encode('utf-8')).hexdigest()
    evals = contenido.setdefault('evaluaciones', [])
    if not any(e.get('id') == digest for e in evals):
        evals.append({
            'id': digest,
            'texto': texto_limpio[:12000],
            'nombre': nombre_instrumento
        })

    contenido['validada'] = False

    # 7. Actualizar propuesta de Conclusión y NEE si está activado
    propuesta_nee = None
    if auto_actualizar_conclusion:
        propuesta_nee = proponer_nee_segey(doc)
        parte_conclusion = doc.setdefault('partes', {}).setdefault('Conclusión', {})
        cont_concl = parte_conclusion.setdefault('contenido', vacia('Conclusión'))
        # Si la conclusión está vacía o sin NEE, pre-llenar con la propuesta
        if not any(str(r.get('NEE', '')).strip() for r in cont_concl.get('nee', [])):
            cont_concl['nee'] = propuesta_nee['nee']
            cont_concl['bap'] = propuesta_nee['bap']
            for k, v in propuesta_nee['campos'].items():
                if not str(cont_concl.get('campos', {}).get(k, '')).strip():
                    cont_concl.setdefault('campos', {})[k] = v

    return {
        'instrumento': nombre_instrumento,
        'campos_afectados': campos_afectados,
        'propuesta_nee': propuesta_nee
    }

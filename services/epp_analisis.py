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

    unidades = []
    for p in parrafos:
        oraciones = [s.strip() for s in re.split(r'\.\s+(?=[A-ZÁÉÍÓÚÑ])', p) if len(s.strip()) > 15]
        if len(oraciones) > 1:
            unidades.extend(oraciones)
        else:
            unidades.append(p)
    if not unidades:
        unidades = parrafos

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
        'Embarazo': ['embarazo', 'gestación', 'prenatal', 'meses'],
        'Parto': ['parto', 'término', 'cesárea', 'apgar', 'incubadora', 'al nacer'],
        'Familiar': ['familia', 'padres', 'hogar', 'madre', 'padre', 'hermanos', 'dinámica'],
        'Salud': ['salud', 'enfermedad', 'médico', 'alergia', 'tratamiento'],
        'Motriz': ['motriz', 'coordinación', 'fina', 'gruesa', 'trazo', 'postura'],
        'Autocuidado': ['autocuidado', 'vestido', 'higiene', 'alimentación', 'esfínteres'],
        'Social': ['social', 'comunidad', 'amigos', 'vecinos', 'entorno'],
    }

    asignados = set()
    for parrafo in unidades:
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


def generar_texto_conclusion(doc):
    """Genera una redacción integradora y pedagógicamente sólida para el apartado 7.1. Conclusión."""
    partes = doc.get('partes', {})
    
    # Extraer síntesis y campos clave de cada área
    cont_apr = partes.get('Aprendizaje', {}).get('contenido', {})
    txt_apr = [str(v) for k, v in cont_apr.get('campos', {}).items() if str(v).strip()]
    if cont_apr.get('sintesis'): txt_apr.append(str(cont_apr['sintesis']))
    txt_apr_str = ' '.join(txt_apr).lower()
    
    cont_psi = partes.get('Psicología', {}).get('contenido', {})
    txt_psi = [str(v) for k, v in cont_psi.get('campos', {}).items() if str(v).strip()]
    if cont_psi.get('sintesis'): txt_psi.append(str(cont_psi['sintesis']))
    txt_psi_str = ' '.join(txt_psi).lower()
    
    cont_com = partes.get('Comunicación', {}).get('contenido', {})
    txt_com = [str(v) for k, v in cont_com.get('campos', {}).items() if str(v).strip()]
    if cont_com.get('sintesis'): txt_com.append(str(cont_com['sintesis']))
    txt_com_str = ' '.join(txt_com).lower()
    
    cont_ts = partes.get('Trabajo Social', {}).get('contenido', {})
    txt_ts = [str(v) for k, v in cont_ts.get('campos', {}).items() if str(v).strip()]
    if cont_ts.get('sintesis'): txt_ts.append(str(cont_ts['sintesis']))
    txt_ts_str = ' '.join(txt_ts).lower()
    
    focos = []
    if any(w in txt_apr_str for w in ('lectura', 'escritura', 'alfabético', 'matemática', 'cálculo', 'curricular', 'conteo')):
        focos.append("la consolidación de competencias curriculares básicas (lectura, escritura y pensamiento matemático funcional)")
    else:
        focos.append("el acceso y progresión en los contenidos curriculares del grado")
        
    if any(w in txt_psi_str for w in ('atención', 'concentración', 'impulsiv', 'autorregulación', 'emocion', 'conducta')):
        focos.append("procesos de atención sostenida y autorregulación socioemocional ante actividades estructuradas")
    elif 'razonamiento' in txt_psi_str:
        focos.append("el fortalecimiento del razonamiento lógico-concreto mediante mediación explícita")
        
    if any(w in txt_com_str for w in ('habla', 'articulación', 'fonol', 'lenguaje', 'expresiv', 'comunicación', 'saac')):
        focos.append("el desarrollo de habilidades de comunicación y lenguaje funcional en entornos áulico y social")
        
    if any(w in txt_ts_str for w in ('familia', 'acompañamiento', 'hogar', 'asistencia', 'entorno', 'visita')):
        focos.append("el acompañamiento sistemático y corresponsable desde el contexto sociofamiliar")

    focos_texto = ", ".join(focos) if focos else "el desarrollo integral de sus habilidades conceptuales, prácticas y adaptativas"

    return (
        f"A partir de la evaluación psicopedagógica interdisciplinaria coordinada por el equipo de USAER, "
        f"se determina que el/la alumno(a) manifiesta disposición al aprendizaje y fortalezas adaptativas que constituyen "
        f"el punto de partida pedagógico. Los resultados integrados indican que requiere apoyos educativos específicos "
        f"focalizados en {focos_texto}.\n\n"
        f"En concordancia con el modelo social de la inclusión educativa, las barreras para el aprendizaje y la participación (BAP) "
        f"identificadas corresponden a factores metodológicos y de organización áulica/escolar, las cuales deben atenderse prioritariamente "
        f"mediante el Diseño Universal para el Aprendizaje (DUA), ajustes razonables pertinentes y trabajo colaborativo permanente "
        f"entre los especialistas de USAER, los docentes de la escuela regular y la familia, garantizando el pleno ejercicio de su derecho a la educación."
    )


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

    conclusion_txt = generar_texto_conclusion(doc)

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


def ensamblar_epp_completa_desde_documento(doc, texto, nombre_archivo='Documento escaneado'):
    """Toma el texto extraído de un documento o escaneo completo de EPP,
    clasifica y ensambla los datos en los apartados oficiales de cada área
    (Aprendizaje, Psicología, Comunicación, Trabajo Social) y Conclusión (NEE/BAP).
    """
    texto_limpio = str(texto or '').strip()
    if not texto_limpio or len(texto_limpio) < 20:
        raise ValueError("El documento escaneado no contiene suficiente texto legible para ensamblar la EPP.")

    lineas = [l.strip() for l in texto_limpio.splitlines() if l.strip()]
    parrafos = [p.strip() for p in re.split(r'\n\s*\n', texto_limpio) if len(p.strip()) > 20]
    if not parrafos:
        parrafos = [l for l in lineas if len(l) > 25]

    claves_area = {
        'Trabajo Social': [
            'embarazo', 'parto', 'desarrollo motor', 'control de esfínteres', 'salud',
            'dinámica familiar', 'contexto familiar', 'visita domiciliaria', 'sociofamiliar',
            'estudio social', 'padre', 'madre', 'hermanos', 'hogar', 'vivienda', 'anexo xii', 'anexo xi'
        ],
        'Psicología': [
            'wisc', 'wechsler', 'raven', 'bender', 'dfh', 'figura humana', 'frostig', 'rey',
            'atención', 'memoria', 'percepción', 'razonamiento', 'cociente intelectual', 'ci',
            'intelectual', 'afectivo', 'conductual', 'emocional', 'autoestima', 'autoconcepto',
            'conducta adaptativa', 'socialización', 'vineland', 'abas', 'autorregulación'
        ],
        'Comunicación': [
            'lenguaje', 'comunicación', 'habla', 'fonológico', 'morfosintáctico', 'semántico',
            'pragmático', 'articulación', 'fonema', 'comprensión expresiva', 'comprensión receptiva',
            'saac', 'voz', 'fluidez', 'intención comunicativa', 'laiz', 'flores'
        ],
        'Aprendizaje': [
            'competencia curricular', 'estilo de aprendizaje', 'canal de aprendizaje',
            'lectura funcional', 'escritura funcional', 'matemáticas funcionales', 'cálculo',
            'contexto escolar', 'áulico', 'ritmo de aprendizaje', 'pda', 'anexo xiv', 'macotela',
            'historia escolar', 'grado escolar'
        ],
        'Conclusión': [
            'conclusión', 'determinación de nee', 'necesidades educativas específicas', 'nee',
            'bap', 'barreras para el aprendizaje', 'apoyos requeridos', 'acuerdos del equipo',
            'ajustes razonables', 'diagnóstico'
        ]
    }

    bloques_por_area = {a: [] for a in (*AREAS, 'Conclusión')}
    area_actual = 'Aprendizaje'

    for parrafo in parrafos:
        p_low = parrafo.lower()
        cambio = None
        if re.search(r'\b(?:1\.\s*datos generales|motivo de evaluaci[oó]n|informaci[oó]n inicial)\b', p_low):
            cambio = 'Aprendizaje'
        elif re.search(r'\b(?:2\.\s*datos sobre el desarrollo|historia familiar|estudio social|desarrollo)\b', p_low):
            cambio = 'Trabajo Social'
        elif re.search(r'\b(?:3\.\s*área intelectual|área psicol[oó]gica|psicol[oó]gico|conducta adaptativa)\b', p_low):
            cambio = 'Psicología'
        elif re.search(r'\b(?:4\.\s*área comunicativa|comunicaci[oó]n y lenguaje|lenguaje y habla)\b', p_low):
            cambio = 'Comunicación'
        elif re.search(r'\b(?:5\.\s*competencia curricular|estilo de aprendizaje|pedag[oó]gico)\b', p_low):
            cambio = 'Aprendizaje'
        elif re.search(r'\b(?:6\.\s*contextos|historia escolar|contexto familiar)\b', p_low):
            if 'familiar' in p_low or 'social' in p_low:
                cambio = 'Trabajo Social'
            else:
                cambio = 'Aprendizaje'
        elif re.search(r'\b(?:7\.\s*conclusi[oó]n|determinaci[oó]n de (?:las )?nee|identificaci[oó]n de bap|apoyos y acuerdos)\b', p_low):
            cambio = 'Conclusión'

        if cambio:
            area_actual = cambio
        else:
            puntuaciones = {k: sum(1 for c in v if c in p_low) for k, v in claves_area.items()}
            mejor = max(puntuaciones, key=puntuaciones.get)
            if puntuaciones[mejor] > 0:
                area_actual = mejor

        bloques_por_area[area_actual].append(parrafo)

    campos_modificados_totales = 0
    areas_ensambladas = []
    instrumentos_detectados = []

    for area in AREAS:
        texto_area = '\n\n'.join(bloques_por_area[area])
        if not texto_area.strip():
            continue

        parte = doc.setdefault('partes', {}).setdefault(area, {})
        contenido = parte.setdefault('contenido', vacia(area))
        campos_previos = dict(contenido.setdefault('campos', {}))

        nuevos_campos = distribuir_hallazgos_en_epp(area, texto_area, campos_previos)
        contenido['campos'] = nuevos_campos

        modificados = sum(1 for c, v in nuevos_campos.items() if v != campos_previos.get(c, ''))
        campos_modificados_totales += modificados

        matches = identificar_instrumento_y_areas(texto_area, area)
        for m in matches:
            inst_nombre = m['instrumento']
            if inst_nombre not in instrumentos_detectados:
                instrumentos_detectados.append(inst_nombre)
            inst_actual = str(contenido.get('instrumentos', '') or '').strip()
            if inst_nombre not in inst_actual:
                contenido['instrumentos'] = f"{inst_actual}\n• {inst_nombre}".strip()

        digest = hashlib.sha256((nombre_archivo + '|' + texto_area).encode('utf-8')).hexdigest()
        evals = contenido.setdefault('evaluaciones', [])
        if not any(e.get('id') == digest for e in evals):
            evals.append({
                'id': digest,
                'nombre': f"Escaneo: {nombre_archivo[:35]}",
                'texto': texto_area[:12000]
            })

        contenido['validada'] = False
        areas_ensambladas.append(area)

    texto_concl = '\n\n'.join(bloques_por_area['Conclusión'])
    parte_concl = doc.setdefault('partes', {}).setdefault('Conclusión', {})
    cont_concl = parte_concl.setdefault('contenido', vacia('Conclusión'))
    cont_concl['validada'] = False

    if texto_concl.strip():
        actual_71 = cont_concl.setdefault('campos', {}).get('7.1. Conclusión', '')
        if not actual_71:
            cont_concl['campos']['7.1. Conclusión'] = texto_concl[:1500]
            campos_modificados_totales += 1

    patron_nee = re.compile(r'(?:^|\n)[-•*\d.)\s]*(?:necesita|requiere|presenta necesidad de|apoyo para)\s+([^\n.]+)', re.IGNORECASE)
    matches_nee = patron_nee.findall(texto_limpio)

    if matches_nee and len(matches_nee) >= 2:
        nuevas_nee = []
        aspectos = ['Funcionamiento intelectual', 'Habilidades conceptuales', 'Habilidades sociales', 'Habilidades prácticas', 'Funcionamiento académico']
        for idx, m_txt in enumerate(matches_nee[:5]):
            m_limpio = m_txt.strip()
            verbo = 'Necesita ' if not m_limpio.lower().startswith(('necesita', 'requiere')) else ''
            nee_desc = f"{verbo}{m_limpio}."
            nuevas_nee.append({
                'Aspectos': aspectos[idx % len(aspectos)],
                'Características relevantes': 'Identificado en evaluación psicopedagógica escaneada.',
                'NEE': nee_desc,
                'Apoyos': 'Acompañamiento docente, apoyos visuales y mediación pedagógica.',
                'Ajustes razonables': 'Dosificación del tiempo y enfoque DUA en planeación de aula.',
                'Responsables': 'Maestra de apoyo y Docente regular',
                'Fecha o período': f"Ciclo escolar {doc.get('ciclo', '2026-2027')}"
            })
        cont_concl['nee'] = nuevas_nee
    propuesta = proponer_nee_segey(doc)
    if not cont_concl.get('nee'):
        cont_concl['nee'] = propuesta['nee']
    if not cont_concl.get('bap'):
        cont_concl['bap'] = propuesta['bap']
    for k, v in propuesta['campos'].items():
        if not str(cont_concl.get('campos', {}).get(k, '')).strip():
            cont_concl.setdefault('campos', {})[k] = v
            campos_modificados_totales += 1

    areas_ensambladas.append('Conclusión y NEE')

    return {
        'nombre_archivo': nombre_archivo,
        'areas_ensambladas': areas_ensambladas,
        'campos_modificados_totales': campos_modificados_totales,
        'instrumentos_detectados': instrumentos_detectados,
        'total_nee': len(cont_concl.get('nee', [])),
        'total_bap': len(cont_concl.get('bap', []))
    }


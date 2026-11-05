"""Propuestas educativas locales y transparentes; no usa motores ni inventa NEE."""
from copy import deepcopy
import re
from services.planeacion_huella import huella
from services.planeacion_generacion import fuentes_pertinentes
from services.curriculo import contexto_ia
from services.planeacion_modelo import FORMATOS
from utils.text import normalizar_texto


SECUENCIAS={
 'lectura':('Observar una imagen y anticipar de qué trata un texto breve.','Leer o escuchar el texto, elegir una imagen o palabra relacionada y explicar la elección con el canal de respuesta accesible.','Registrar una respuesta y revisar qué apoyo facilitó la participación.','Texto breve, imágenes y hoja; confirmar disponibilidad.'),
 'escritura':('Elegir una palabra o mensaje útil en una situación escolar.','Construirlo con letras móviles, dibujo o escritura, con modelado y ayuda graduada según se requiera.','Compartir el mensaje y conservar una muestra del proceso.','Hoja, lápiz y tarjetas de letras; confirmar disponibilidad.'),
 'numeros':('Presentar objetos y una pregunta de conteo o comparación ajustada al contenido elegido.','Agrupar, contar o representar cantidades con material concreto; permitir señalar, mover o expresar la respuesta.','Comprobar la solución y registrar el apoyo utilizado, sin atribuir un logro anticipado.','Objetos cotidianos, fichas y hoja; confirmar disponibilidad.'),
 'general':('Presentar una situación breve relacionada con el contenido elegido o el antecedente documentado.','Modelar una acción, ofrecer dos alternativas accesibles y dar tiempo para realizarla con apoyo graduado.','Pedir una respuesta observable y anotar qué funcionó para ajustar la siguiente sesión.','Material visual o concreto y hoja; confirmar disponibilidad.'),
 'Psicología':('Presentar una situación escolar cotidiana mediante imágenes.','Ensayar identificar una emoción y elegir una estrategia de regulación o convivencia, con modelado y sin evaluación clínica.','Compartir una alternativa de respuesta y registrar la participación y los apoyos que se necesitaron.','Imágenes de situaciones escolares y tarjetas de opciones; confirmar disponibilidad.'),
 'Comunicación':('Crear una situación funcional para elegir, pedir ayuda o compartir información.','Modelar una expresión y ofrecer respuesta oral, gestual, escrita o con apoyos visuales según el canal ya documentado o por confirmar.','Usar el mensaje en un intercambio breve y registrar el apoyo que facilitó la comunicación.','Objetos cotidianos, imágenes y tablero sencillo si está disponible.'),
 'Trabajo Social':('Retomar una barrera del entorno documentada o una rutina escolar que el equipo necesite revisar.','Proponer con las personas implicadas una alternativa viable de participación o acceso; preguntar por recursos reales sin suponer carencias ni culpar a la familia.','Registrar únicamente acuerdos que efectivamente se alcancen después de la actividad y definir su seguimiento.','Hoja de registro y recursos accesibles por confirmar; no supone una visita o acuerdo realizado.')}


# Actividades de acceso inicial: ninguna exige leer un texto o redactar sin apoyo.
INICIAL = (
    ("Presentar dos objetos familiares y modelar el sonido inicial de sus nombres.",
     "Escuchar un nombre, señalar su objeto y elegir entre dos letras móviles con apoyo visual. No se requiere leer palabras.",
     "Registrar si identifica el sonido inicial mediante señalamiento, con y sin modelado.",
     "Objetos familiares, imágenes y letras móviles.", "identifica el sonido inicial de un nombre con apoyo visual"),
    ("Mostrar una imagen conocida y nombrarla oralmente junto con el alumno.",
     "Separar oralmente el nombre en sílabas con palmadas o fichas. Permitir señalar o mover una ficha por sílaba; el docente lee cualquier etiqueta.",
     "Registrar si segmenta el nombre oralmente o con fichas y qué apoyo requirió.",
     "Imágenes y fichas de conteo.", "segmenta oralmente un nombre conocido mediante fichas o palmadas"),
    ("Modelar una elección funcional usando dos imágenes y sus etiquetas.",
     "Emparejar la imagen elegida con su etiqueta como modelo visual. Comunicar la elección señalando, dibujando o dictando al docente; no exigir redacción.",
     "Registrar si comunica su elección y empareja la imagen con el modelo con apoyo graduado.",
     "Imágenes, etiquetas de referencia y hojas.", "comunica una elección con imágenes y la empareja con un modelo visual"),
)


def acceso_inicial(fuentes):
    """Una restricción de acceso documentada no se convierte en diagnóstico."""
    patrones = r"NO (?:HA |HABIA )?(?:ADQUIRID[OA]|ADQUIERE|CONSOLIDAD[OA]|DOMINA) (?:LA )?LECTOESCRITURA|SIN (?:ADQUISICION DE )?LECTOESCRITURA|(?:NIVEL |ETAPA )?(?:PRESILABIC[OA]|PRE SILABIC[OA])|(?:AUN |TODAVIA )?NO (?:LOGRA |PUEDE |SABE )?(?:LEER|LEE|DECODIFICAR|DECODIFICA) (?:PALABRAS|TEXTOS|SILABAS|DE FORMA AUTONOMA)|(?:AUN |TODAVIA )?NO (?:RECONOCE|IDENTIFICA) (?:LAS )?(?:LETRAS|VOCALES)"
    validos = {"EPP", "EPP Anexo XVII", "NEE", "Informe educativo", "Plan de intervención", "Planeación previa", "Evento", "Contexto escolar"}
    for f in fuentes:
        if f.get('tipo') in validos and re.search(patrones, normalizar_texto(f['texto'])):
            return f['referencia']
    return ''


def apoyos_de_bap(fuentes):
    texto=normalizar_texto(' '.join(f['texto'] for f in fuentes if f.get('tipo')=='BAP'))
    ajustes=[]
    if re.search(r'RUIDO|DISTRACTORES',texto):ajustes.append('Reducir distractores del entorno durante el modelado.')
    if re.search(r'CONSIGNAS|INSTRUCCIONES|LENGUAJE ORAL',texto):ajustes.append('Presentar una consigna por vez con demostración o apoyo visual.')
    if re.search(r'MOVILIDAD|ACCESO FISICO',texto):ajustes.append('Colocar materiales al alcance y permitir un canal de respuesta accesible.')
    return ' '.join(ajustes)


def vincular_cadena_nee(actividad, necesidad, pda, conclusion):
    """Reutiliza solo los apoyos del renglón de la NEE elegida."""
    from services.planeacion_calidad import descriptor

    texto = necesidad["texto"].strip()
    fila = next((r for r in conclusion.get("nee", []) if str(r.get("NEE", "")).strip() == texto), {})
    apoyos = " · ".join(str(fila[k]).strip() for k in ("Apoyos", "Ajustes razonables") if str(fila.get(k) or "").strip())
    pda_oficial = " ".join(pda.split())
    verbo = re.match(r"^(identifica|reconoce|clasifica|forma|expresa|ordena|mantiene|sigue|compara|resuelve|solicita)\b",
                     pda_oficial, flags=re.I)
    if verbo and 8 <= len(pda_oficial[verbo.end():].strip().rstrip(".")) <= 500:
        observable = descriptor(actividad["nombre"], verbo[0], pda_oficial[verbo.end():])
    else:
        observable = descriptor(actividad["nombre"], "participa",
                                 "y demuestra el desempeño del PDA mediante una respuesta observable con los apoyos acordados")
    if actividad.get("acceso_inicial"):
        observable = actividad["descriptor"]
    return {
        "nee": texto, "pda": pda, "descriptor": observable,
        "apoyos": " · ".join(x for x in (apoyos, actividad.get("apoyos_acceso", "")) if x) or "Propuesta: usar modelado y opciones de respuesta accesibles. Ajustar con observación docente.",
        "temporalidad": str(fila.get("Fecha o período") or "").strip() or "Primera sesión. Ajustar tras observar el desempeño.",
        "evaluacion": actividad.get("evaluacion") or "Registrar el desempeño descrito, el apoyo efectivamente utilizado y el siguiente ajuste docente.",
    }


def preparar(doc,enfoque='',contexto_actividad=None):
    from services import planeacion as s
    s.autorizar(doc,True)
    return preparar_documento_autorizado(doc, enfoque, contexto_actividad)


def preparar_documento_autorizado(doc, enfoque='', contexto_actividad=None, *, alumno_id='', variante=0, metodo='', materiales_docentes=''):
    """Prepara propuestas; el adaptador debe validar previamente todos los alumnos."""
    contexto_actividad=contexto_actividad or ('Escuela' if doc['formato']=='XXV' else 'Aula regular')
    if doc['formato']!='XXI' and contexto_actividad not in FORMATOS[doc['formato']]['contextos']:raise ValueError('Elige un contexto de este formato.')
    fuentes=fuentes_pertinentes(doc)
    contexto=contexto_ia(doc)
    refs=contexto.get('referentes_por_grado',[])
    campos=list(dict.fromkeys(r['campo'] for r in refs)) or ['Sin PDA seleccionado']
    materiales=[f for f in fuentes if f.get('tipo')=='MATERIAL' and not f.get('alumno')]
    propios={a['ID_Alumno']:[f for f in fuentes if a['ID_Alumno'] in str(f.get('alumno','')).split(',')] for a in doc['datos']['Alumnos']}
    # La hoja ya redactada también es un punto de partida. No vuelve a pedir
    # la misma información en otro cuadro ni convierte la planeación en evidencia.
    tabla='barreras' if doc['formato'] in ('XXV','XXI') else 'aprendizajes'
    bases=[{h:str(r.get(h,'') or '') for h in FORMATOS[doc['formato']]['tablas'][tabla]} for r in doc['tablas'][tabla]]
    base_formato='\n'.join(h+': '+v for r in bases for h,v in r.items() if v.strip())[:6000]
    if not fuentes and not refs and not base_formato and not str(enfoque).strip() and not doc['metadatos'].get('necesidades_confirmadas','').strip():
        raise ValueError('Añade un antecedente, un contenido/PDA o una orientación docente para preparar propuestas locales. No necesitas IA.')
    propuestas=[]
    for a in doc['datos']['Alumnos']:
        if alumno_id and a['ID_Alumno']!=alumno_id:continue
        individuales=propios[a['ID_Alumno']]
        evidencia_inicial=acceso_inicial(individuales)
        apoyos_bap=apoyos_de_bap(individuales)
        for campo in campos:
            seleccionados=[r for r in refs if r['campo']==campo]
            datos=' '.join(f['texto'][:1500] for f in individuales+materiales)+' '+str(enfoque)+' '+' '.join(r['contenido'] for r in seleccionados)
            # Solo usa filas identificadas con este alumno, o las de una hoja
            # individual, para elegir el contenido de su propuesta local.
            propias_formato=[r for r in doc['tablas'][tabla] if r.get('_alumnos_apartados')==[a['ID_Alumno']] or len(doc['datos']['Alumnos'])==1]
            datos+=' '+' '.join(str(r.get(h,'') or '') for r in propias_formato for h in FORMATOS[doc['formato']]['tablas'][tabla])
            area=doc['datos']['Función'];clave=area
            if clave not in SECUENCIAS:
                normal=normalizar_texto(datos)
                clave='lectura' if any(t in normal for t in ('LECTURA','LEER','LECTO')) else 'escritura' if 'ESCRIT' in normal else 'numeros' if any(t in normal for t in ('NUMER','CONTEO','CANTIDAD','MATEMAT')) else 'general'
            inicio,desarrollo,cierre,recursos=SECUENCIAS[clave]
            descriptor_inicial=''
            # La evidencia individual manda sobre una palabra suelta en el PDA o en el enfoque.
            if evidencia_inicial and area not in ('Trabajo Social','Psicología','Comunicación') and (campo=='Lenguajes' or clave in ('lectura','escritura','general')):
                enfoque_metodo=normalizar_texto(metodo)
                base=2 if 'TRONCOSO' in enfoque_metodo or 'GLOBAL' in enfoque_metodo else 1 if 'SILAB' in enfoque_metodo else 0
                inicio,desarrollo,cierre,recursos,descriptor_inicial=INICIAL[(base+variante)%len(INICIAL)]
            elif variante:
                inicio += (' Usar un ejemplo distinto tomado de una rutina escolar.' if variante==1 else ' Comparar dos ejemplos concretos antes de elegir una respuesta.')
                cierre += (' Repetir con un objeto nuevo para comprobar transferencia.' if variante==1 else ' Ofrecer una segunda oportunidad con un apoyo menor, si resulta viable.')
            if metodo:desarrollo += ' Método indicado por el docente: '+metodo+'. Ajustar el modelado y los apoyos sin exigir un desempeño no documentado.'
            if materiales_docentes:recursos += ' Material seleccionado por el docente: '+materiales_docentes+'.'
            antecedentes=[f['referencia'] for f in individuales]
            alcance='Antecedentes propios: '+', '.join(antecedentes) if antecedentes else 'Propuesta curricular general: sin antecedente individual disponible; no atribuye necesidades al alumno.'
            if materiales:alcance+=' Materiales generales de apoyo: '+', '.join(f['referencia'] for f in materiales)+'. No equivalen a una evaluación individual.'
            referentes=[r['id'] for r in seleccionados]
            sustento='Referentes seleccionados: '+', '.join(referentes) if referentes else 'Sin PDA específico seleccionado. Revisar su vinculación antes de enviar.'
            if area=='Trabajo Social' and not referentes:sustento='Revisar la barrera documentada, los apoyos y el contexto elegido en el Anexo XXV.'
            if descriptor_inicial:alcance+=' Acceso inicial documentado en '+evidencia_inicial+'; el PDA se conserva como referente y se adapta la tarea, no se presume lectoescritura adquirida.'
            if base_formato:alcance+=' Se reutiliza la orientación escrita en el formato como propuesta de trabajo; no confirma una evaluación ni un resultado.'
            firma=huella({'doc':doc['id'],'alumno':a['ID_Alumno'],'campo':campo,'enfoque':enfoque,'fuentes':individuales+materiales,'referentes':seleccionados,'base_formato':bases,'contexto':contexto_actividad,'variante':variante,'metodo':metodo,'materiales':materiales_docentes,'version':3})
            propuestas.append({'id':firma,'alumno':a['ID_Alumno'],'nombre':a['Nombre del alumno'],'campo':campo,
                'actividad':(a['Nombre del alumno']+'\n' if len(doc['datos']['Alumnos'])>1 else '')+'Inicio: '+inicio+'\nDesarrollo: '+desarrollo+'\nCierre: '+cierre,
                'orientacion':alcance+'\n'+sustento,
                'recursos':recursos,'evidencias':antecedentes,'referentes':referentes,'contexto':contexto_actividad,
                'variante':variante,'acceso_inicial':bool(descriptor_inicial),'descriptor':a['Nombre del alumno']+' '+descriptor_inicial if descriptor_inicial else '',
                'apoyos_acceso':' '.join(x for x in ('Modelado oral, elección con imágenes y respuesta accesible; sin exigir lectura autónoma ni redacción.' if descriptor_inicial else '',apoyos_bap) if x),
                'evaluacion':cierre if descriptor_inicial else ''})
    return {'huella':huella(doc),'propuestas':propuestas,'enfoque':str(enfoque)}


def aplicar(doc,propuesta,ids):
    from services import planeacion as s, planeacion_edicion as ed
    s.autorizar(doc,True)
    if propuesta['huella']!=huella(doc):raise ValueError('La planeación cambió. Prepara otra vez la propuesta local antes de incorporarla.')
    disponibles={r['id']:r for r in propuesta['propuestas']}
    if not ids or not set(ids)<=set(disponibles):raise ValueError('Elige propuestas de esta preparación.')
    alumnos={a['ID_Alumno'] for a in doc['datos']['Alumnos']}
    if any(disponibles[i]['alumno'] not in alumnos for i in ids):raise PermissionError('La propuesta contiene otro alumno.')
    result=ed.borrador(doc);meta=result['metadatos'];aplicadas=set(meta.get('actividades_locales_aplicadas',[]))
    tabla='barreras' if doc['formato']=='XXI' else 'dosificacion'
    nuevas=[disponibles[i] for i in dict.fromkeys(ids) if i not in aplicadas]
    if len(result['tablas'][tabla])+len(nuevas)>100:raise ValueError('Esta tabla admite hasta cien filas. Selecciona menos propuestas o revisa las existentes.')
    for p in nuevas:
        row={h:'' for h in FORMATOS[doc['formato']]['tablas'][tabla]}
        row['Acciones para minimizarla o eliminarla' if doc['formato']=='XXI' else 'Actividades']=p['actividad']
        if 'Recursos' in row:row['Recursos']=p['recursos']
        if 'Contextos' in row:
            contexto=p.get('contexto') or ('Escuela' if doc['formato']=='XXV' else 'Aula regular')
            if contexto not in FORMATOS[doc['formato']]['contextos']:raise ValueError('El contexto propuesto no corresponde al formato.')
            row['Contextos']=contexto
        row['_actividad_local']=p['id'];row['_alumnos_locales']=[p['alumno']]
        result['tablas'][tabla].append(row);aplicadas.add(p['id'])
    if not nuevas:return deepcopy(doc)
    meta['actividades_locales_aplicadas']=sorted(aplicadas)
    meta['preparacion_local']={'requiere_revision_docente':True,'motor':'sin IA','aviso':'Son propuestas locales de actividad, no NEE, resultados ni evaluaciones. Completa objetivos, apoyos y tiempos con criterio profesional.'}
    return result

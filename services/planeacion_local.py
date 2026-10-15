"""Propuestas educativas locales y transparentes; no usa motores ni inventa NEE."""
from copy import deepcopy
from services import planeacion as s,planeacion_edicion as ed
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


def preparar(doc,enfoque='',contexto_actividad=None):
    s.autorizar(doc,True)
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
        individuales=propios[a['ID_Alumno']]
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
            antecedentes=[f['referencia'] for f in individuales]
            alcance='Antecedentes propios: '+', '.join(antecedentes) if antecedentes else 'Propuesta curricular general: sin antecedente individual disponible; no atribuye necesidades al alumno.'
            if materiales:alcance+=' Materiales generales de apoyo: '+', '.join(f['referencia'] for f in materiales)+'. No equivalen a una evaluación individual.'
            referentes=[r['id'] for r in seleccionados]
            sustento='Referentes seleccionados: '+', '.join(referentes) if referentes else 'Sin PDA específico seleccionado. Revisar su vinculación antes de enviar.'
            if area=='Trabajo Social' and not referentes:sustento='Revisar la barrera documentada, los apoyos y el contexto elegido en el Anexo XXV.'
            if base_formato:alcance+=' Se reutiliza la orientación escrita en el formato como propuesta de trabajo; no confirma una evaluación ni un resultado.'
            firma=ed.huella({'doc':doc['id'],'alumno':a['ID_Alumno'],'campo':campo,'enfoque':enfoque,'fuentes':individuales+materiales,'referentes':seleccionados,'base_formato':bases,'contexto':contexto_actividad,'version':2})
            propuestas.append({'id':firma,'alumno':a['ID_Alumno'],'nombre':a['Nombre del alumno'],'campo':campo,
                'actividad':(a['Nombre del alumno']+'\n' if len(doc['datos']['Alumnos'])>1 else '')+'Inicio: '+inicio+'\nDesarrollo: '+desarrollo+'\nCierre: '+cierre,
                'orientacion':alcance+'\n'+sustento,
                'recursos':recursos,'evidencias':antecedentes,'referentes':referentes,'contexto':contexto_actividad})
    return {'huella':ed.huella(doc),'propuestas':propuestas,'enfoque':str(enfoque)}


def aplicar(doc,propuesta,ids):
    s.autorizar(doc,True)
    if propuesta['huella']!=ed.huella(doc):raise ValueError('La planeación cambió. Prepara otra vez la propuesta local antes de incorporarla.')
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

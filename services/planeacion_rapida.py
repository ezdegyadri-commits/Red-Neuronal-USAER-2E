"""Selecciones rápidas y ensamblaje local; no diagnostica ni escribe registros."""
from copy import deepcopy
import hashlib
import json
from services import planeacion as s
from services.planeacion_generacion import fuentes_pertinentes
from services.planeacion_modelo import FORMATOS
from services.planeacion_nee import es_bapse
from services.planeacion_social import extraer,BARRERA
from services.planeacion_local import SECUENCIAS
from utils.text import normalizar_texto

PRIORIDADES={
 'lectura':('Comprensión de textos','Comprender información de un texto breve.','El alumno identifica información de un texto leído o escuchado.','lectura'),
 'escritura':('Escritura de mensajes','Elaborar un mensaje con intención comunicativa.','El alumno produce y comparte un mensaje mediante escritura o apoyos accesibles.','escritura'),
 'numeros':('Número y cantidades','Relacionar cantidades con sus representaciones.','El alumno representa una cantidad con objetos, imágenes o números.','numeros'),
 'consignas':('Comprensión de consignas','Comprender y realizar una consigna en una actividad breve.','El alumno realiza la acción solicitada con los apoyos previstos.','general'),
 'comunicacion':('Comunicación funcional','Comunicar una elección, petición o idea.','El alumno expresa una elección o petición mediante su canal de comunicación.','Comunicación'),
 'emociones':('Autorregulación y emociones','Reconocer una emoción y explorar una estrategia de regulación.','El alumno identifica una emoción y elige una alternativa de respuesta.','Psicología'),
 'convivencia':('Convivencia y participación','Participar en un intercambio respetando acuerdos de interacción.','El alumno participa en un intercambio con los apoyos previstos.','Psicología'),
 'acceso':('Acceso y participación','Proponer apoyos viables ante una barrera documentada.','El seguimiento registra los apoyos implementados y los pendientes de revisión.','Trabajo Social'),
 'familia':('Vinculación con familias','Construir alternativas de apoyo con las personas implicadas.','El seguimiento registra únicamente acuerdos que efectivamente se alcancen.','Trabajo Social'),
}
POR_AREA={'Aprendizaje':['lectura','escritura','numeros','consignas'],
 'Comunicación':['comunicacion','consignas'], 'Psicología':['emociones','convivencia','consignas'],
 'Trabajo Social':['acceso','familia']}
APOYOS={
 'visual':('Apoyos visuales','Presentar imágenes o claves visuales relacionadas con la consigna.'),
 'pasos':('Consignas por pasos','Dar una consigna breve por vez y comprobar su comprensión.'),
 'modelado':('Modelado','Mostrar cómo realizar la acción antes de invitar a realizarla.'),
 'tiempo':('Tiempo flexible','Ofrecer tiempo de respuesta y pausas de acuerdo con la participación.'),
 'respuesta':('Distintas formas de responder','Permitir respuestas orales, gestuales, escritas o apoyadas, según pertinencia.'),
 'concreto':('Material concreto','Usar material manipulable, confirmando su disponibilidad.'),
}
METODOS={'secuencia':'Secuencia didáctica','taller':'Taller práctico','proyecto':'Proyecto breve'}
FRECUENCIAS=['Una vez por semana','Dos veces por semana','En las sesiones de atención programadas']


def acuerdos(doc):
    """Solo acuerdos explícitos de CTE verificado para los destinatarios elegidos."""
    result={}
    for fuente in fuentes_pertinentes(doc):
        if fuente.get('tipo')!='CTE' or not fuente.get('vinculo_verificado'):continue
        try:data=json.loads(fuente['texto'])
        except (ValueError,TypeError):continue
        rows=data.get('acuerdos',data.get('Acuerdos',[])) if isinstance(data,dict) else []
        if not isinstance(rows,list):continue
        for i,row in enumerate(rows):
            value=row if isinstance(row,str) else row.get('acuerdo',row.get('texto','')) if isinstance(row,dict) else ''
            if not isinstance(value,str) or not value.strip():continue
            key=hashlib.sha256(json.dumps([fuente.get('registro'),fuente.get('revision'),i,value],ensure_ascii=False).encode()).hexdigest()
            result[key]={'texto':value.strip()[:2000],'fuente':fuente.get('referencia','CTE'),'revision':fuente.get('revision','')}
    return result


def estado(doc):
    s.autorizar(doc,True)
    if doc['formato'] not in ('XXIII','XXV'):raise ValueError('La preparación rápida corresponde a la planeación trimestral de cada área.')
    area=doc['datos']['Función'];permitidas=POR_AREA.get(area,[])
    if not permitidas:raise PermissionError('Esta función no tiene formato de preparación rápida.')
    fuentes=fuentes_pertinentes(doc)
    nee=[];bap=[]
    for row in doc['tablas'].get('aprendizajes',[]):
        text=str(row.get('Necesidades educativas específicas','')).strip()
        if text and not es_bapse({'texto':text}):nee.append(text)
    for f in fuentes:
        if f.get('tipo')=='EPP':
            bap.extend({**r,'fuente':f.get('referencia','EPP')} for r in extraer(f))
            if f.get('parte')=='Conclusión' and not es_bapse(f):
                try:contenido=json.loads(f.get('texto',''))
                except (ValueError,TypeError):contenido={}
                valores=contenido.get('NEE',[]) if isinstance(contenido,dict) else []
                if isinstance(valores,list):
                    for row in valores:
                        valor=row.get('NEE','') if isinstance(row,dict) else ''
                        if isinstance(valor,str) and valor.strip() and valor.strip() not in nee:nee.append(valor.strip())
    for row in doc['tablas'].get('barreras',[]):
        if row.get(BARRERA):bap.append({BARRERA:row[BARRERA],'fuente':'Formato actual'})
    textos=normalizar_texto(' '.join(nee))
    candidatas=[p for token,p in [('LECT','lectura'),('ESCRIT','escritura'),('CANTIDAD','numeros'),('NUMER','numeros'),('CONSIGNA','consignas'),('COMUNIC','comunicacion'),('EMOC','emociones'),('CONVIV','convivencia')] if token in textos and p in permitidas]
    guardado=doc['metadatos'].get('preparacion_rapida',{}).get('selecciones',{})
    if not isinstance(guardado,dict):guardado={}
    defaults={'prioridades':list(dict.fromkeys(candidatas))[:2] or [permitidas[0]],
       'apoyos':['pasos','respuesta'] if area!='Trabajo Social' else ['respuesta'],
       'metodo':'secuencia','contextos':list(FORMATOS[doc['formato']]['contextos']),
       'duracion':30,'frecuencia':FRECUENCIAS[0],'acuerdos':[],'completar':False,'tematica':''}
    for key in defaults:
        if key in guardado and type(guardado[key]) is type(defaults[key]):defaults[key]=deepcopy(guardado[key])
    if defaults['metodo'] not in METODOS:defaults['metodo']='secuencia'
    if defaults['duracion'] not in [15,20,30,45,60]:defaults['duracion']=30
    if defaults['frecuencia'] not in FRECUENCIAS:defaults['frecuencia']=FRECUENCIAS[0]
    defaults['prioridades']=[p for p in defaults['prioridades'] if p in permitidas]
    defaults['apoyos']=[p for p in defaults['apoyos'] if p in APOYOS]
    defaults['contextos']=[p for p in defaults['contextos'] if p in FORMATOS[doc['formato']]['contextos']]
    cte=acuerdos(doc);defaults['acuerdos']=[i for i in defaults['acuerdos'] if i in cte]
    return {'nee':nee,'bap':bap,'fuentes':[{k:f.get(k,'') for k in ('tipo','referencia','fecha','alumno')} for f in fuentes],
      'acuerdos':cte,'permitidas':permitidas,'defaults':defaults,'avisos':[] if nee or area=='Trabajo Social' else ['Sin NEE redactada en la hoja: la prioridad seleccionada será una orientación docente, no una NEE confirmada.']}


def validar(doc,selecciones):
    e=estado(doc);errors=[]
    if not isinstance(selecciones,dict):return ['Revisa las opciones de preparación.']
    for key,valid in [('prioridades',e['permitidas']),('apoyos',APOYOS),('contextos',FORMATOS[doc['formato']]['contextos']),('acuerdos',e['acuerdos'])]:
        values=selecciones.get(key,[])
        if not isinstance(values,list) or any(not isinstance(v,str) or v not in valid for v in values):errors.append('Revisa la selección de '+key+'.')
        elif len(values)!=len(set(values)):errors.append('Hay selecciones repetidas en '+key+'.')
        elif key in ('prioridades','contextos') and not values:errors.append('Elige al menos una opción en '+key+'.')
    if selecciones.get('metodo') not in METODOS:errors.append('Elige una metodología disponible.')
    if type(selecciones.get('duracion')) is not int or selecciones['duracion'] not in [15,20,30,45,60]:errors.append('Elige una duración disponible.')
    if selecciones.get('frecuencia') not in FRECUENCIAS:errors.append('Elige la frecuencia de trabajo.')
    if type(selecciones.get('completar',False)) is not bool:errors.append('Revisa la opción de autollenado.')
    if not isinstance(selecciones.get('tematica',''),str) or len(selecciones.get('tematica',''))>300:errors.append('Resume la temática en un máximo de 300 caracteres.')
    return errors


def orientaciones(doc,selecciones):
    errors=validar(doc,selecciones)
    if errors:raise ValueError(' '.join(errors))
    return {'enfoque':'Prioridades propuestas: '+', '.join(PRIORIDADES[p][0] for p in selecciones['prioridades'])+'. Metodología: '+METODOS[selecciones['metodo']]+'. '+('Temática propuesta por la docente (no evidencia diagnóstica): '+selecciones['tematica'].strip()+'.' if selecciones.get('tematica','').strip() else ''),
       'apoyos':' '.join(APOYOS[p][1] for p in selecciones['apoyos'])+' Contextos: '+', '.join(selecciones['contextos'])+'. Temporalidad propuesta: '+selecciones['frecuencia']+', '+str(selecciones['duracion'])+' minutos. '+
           ' '.join('Acuerdo CTE registrado ('+acuerdos(doc)[k]['fuente']+'): '+acuerdos(doc)[k]['texto'] for k in selecciones['acuerdos'])}


def ensamblar(doc,selecciones):
    """Resultado editable, aditivo e idempotente; ninguna escritura ni llamada IA."""
    orientaciones(doc,selecciones)
    selecciones=deepcopy(selecciones)
    for key in ('prioridades','apoyos','contextos','acuerdos'):selecciones[key]=sorted(selecciones[key])
    result=deepcopy(doc)
    if selecciones.get('completar'):
        from services.planeacion_apartados import proponer
        result=proponer(result)
        for tabla,rows in doc['tablas'].items():
            for i,original in enumerate(rows):
                if i<len(result['tablas'][tabla]) and result['tablas'][tabla][i]!=original:
                    result['tablas'][tabla][i]['_completar_fila_rapida']=hashlib.sha256(json.dumps(original,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    previos={r.get('_actividad_rapida') for r in result['tablas']['dosificacion']}
    cte=acuerdos(doc);fuentes=fuentes_pertinentes(doc)
    for alumno in doc['datos']['Alumnos']:
        aid=alumno['ID_Alumno'];referencias=[{k:f.get(k,'') for k in ('tipo','registro','revision','alumno')} for f in fuentes if aid in str(f.get('alumno','')).split(',')]
        for prioridad in selecciones['prioridades']:
            label,objetivo,descriptor,sequence=PRIORIDADES[prioridad]
            for contexto in selecciones['contextos']:
                firma=hashlib.sha256(json.dumps([doc['id'],aid,prioridad,contexto,selecciones,referencias],sort_keys=True,ensure_ascii=False).encode()).hexdigest()
                if firma in previos:continue
                inicio,desarrollo,cierre,recursos=SECUENCIAS[sequence]
                texto=alumno['Nombre del alumno']+'\n'+METODOS[selecciones['metodo']]+': '+label+'.\n'
                texto+='Propósito propuesto: '+objetivo+'\nInicio: '+inicio+'\nDesarrollo: '+desarrollo+'\nCierre: '+cierre
                if selecciones['metodo']=='taller':texto+='\nOrganización del taller: modelado, práctica acompañada y puesta en común.'
                if selecciones['metodo']=='proyecto':texto+='\nProducto propuesto: una muestra o registro de lo realizado, que el alumno pueda compartir por un medio accesible.'
                texto+='\nApoyos propuestos: '+' '.join(APOYOS[p][1] for p in selecciones['apoyos'])
                if selecciones.get('tematica','').strip():texto+='\nTemática propuesta por la docente: '+selecciones['tematica'].strip()+'. Adaptar la secuencia a esta temática antes de aplicarla.'
                texto+='\nIndicador para valorar después de la actividad: '+descriptor
                for key in selecciones['acuerdos']:texto+='\nVinculación con acuerdo CTE registrado ('+cte[key]['fuente']+'): '+cte[key]['texto']
                result['tablas']['dosificacion'].append({'Contextos':contexto,'Actividades':texto,
                    'Temporalidad':doc['datos']['Periodo']+' · '+selecciones['frecuencia']+' · '+str(selecciones['duracion'])+' minutos por sesión (propuesta)',
                    'Recursos':recursos,'_actividad_rapida':firma,'_alumnos_planeacion':[aid],'_origenes':referencias,
                    '_indicador_propuesto':descriptor,'_prioridad_docente':prioridad,'_cte_fuentes':[cte[k] for k in selecciones['acuerdos']]})
                previos.add(firma)
    if len(result['tablas']['dosificacion'])>100:raise ValueError('La propuesta supera cien filas. Reduce prioridades o contextos; tu documento se conserva.')
    if not result['textos'].get('Evaluación','').strip() and doc['formato']=='XXIII':
        result['textos']['Evaluación']='Propuesta de instrumento: lista de cotejo de los indicadores incluidos en las actividades. Registrar la respuesta observable y los apoyos utilizados al finalizar las sesiones y revisar los avances al cierre del trimestre. Los resultados se capturan después de la intervención.'
    result['metadatos']['preparacion_rapida']={'selecciones':deepcopy(selecciones),'requiere_revision':True,'motor':'ensamblaje local','aviso':'Prioridades, actividades y tiempos propuestos; no son diagnósticos, resultados ni acuerdos nuevos.'}
    return result

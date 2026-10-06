"""Prellenado documental, calendario y ensamble local del formato editable."""
from copy import deepcopy
from datetime import date,timedelta,datetime
from zoneinfo import ZoneInfo
import hashlib
import json
import re
from services.planeacion_modelo import FORMATOS
from services import planeacion_equipo as equipo
from services.curriculo import contexto_ia, CAMPOS, opciones, vincular
from utils.text import normalizar_texto
from ai.planeacion_completa import huella_completa, validar_completa

DIAS=('Lunes','Martes','Miércoles','Jueves','Viernes')


def configuracion(doc):
    desde,hasta=doc['datos']['Periodo'].split(' / ')
    hoy=datetime.now(ZoneInfo('America/Mexico_City')).date().isoformat()
    inicio=max(desde,hoy) if hoy<=hasta else desde
    cur=doc['metadatos'].get('curriculo',{})
    grados=[r['grado'] for r in cur.get('registros',[])]
    if not grados:
        grados=[int(m[1]) for a in doc['datos']['Alumnos'] if (m:=re.match(r'^\s*([1-6])(?:\D|$)',str(a.get('Grado',''))))]
    campo=cur.get('campo') or ('De lo Humano y lo Comunitario' if doc['datos']['Función'] in ('Psicología','Trabajo Social') else 'Lenguajes')
    return {'duracion':45,'sesiones':6 if doc['datos']['Función']=='Psicología' else 12,
            'dias':['Lunes','Jueves'],'inicio':inicio,'enfoque':'','apoyos':'','grado_referencia':min(grados) if grados else None,'campo_referencia':campo}


def sugerir_curriculo(doc,ajustes):
    cur=doc['metadatos'].get('curriculo',{})
    grado=ajustes.get('grado_referencia');campo=ajustes.get('campo_referencia',cur.get('campo'))
    if grado not in range(1,7) or campo not in CAMPOS:return deepcopy(doc)
    if cur.get('registros') and not cur.get('sugerido_automaticamente') and cur.get('campo')==campo and all(r['grado']==grado for r in cur['registros']):return deepcopy(doc)
    contenido=str(ajustes.get('enfoque',''))+' '+doc['metadatos'].get('necesidades_confirmadas','')+' '+' '.join(f['texto'][:1500] for f in fuentes_pertinentes(doc))
    texto=normalizar_texto(contenido)
    familias={'LECTURA':('LECTURA','LECTO','LEER'),'ESCRITURA':('ESCRITURA','LECTO','ESCRIB'),
              'EMOCIONES':('EMOCION','REGULACION','CONVIVENCIA'),'DIALOGO':('COMUNICACION','EXPRESION','DIALOG'),
              'NUMEROS':('NUMER','MATEMAT','CONTEO'),'BIENESTAR':('BIENESTAR','FAMILIA','PARTICIPACION')}
    tokens={k for k,variantes in familias.items() if any(v in texto for v in variantes)}
    if not tokens:return deepcopy(doc)
    rows=opciones(doc,campo,[grado])
    valoradas=sorted(((sum(t in normalizar_texto(r['contenido']+' '+r['pda']) for t in tokens),r) for r in rows),key=lambda p:(-p[0],p[1]['id']))
    elegidas=[r['id'] for score,r in valoradas if score>0][:3]
    if not elegidas:return deepcopy(doc)
    result=vincular(doc,campo,cur.get('ejes',['Inclusión']),elegidas,cur.get('contexto_local',''))
    result['metadatos']['curriculo']['sugerido_automaticamente']=True
    result['metadatos']['curriculo']['aviso']='Referentes oficiales sugeridos por coincidencia temática; revisa su pertinencia. No representan una evaluación del nivel del alumno.'
    return result


def fuentes_pertinentes(doc):
    ids={a['ID_Alumno'] for a in doc['datos']['Alumnos']};resultado=[]
    for fuente in doc['metadatos'].get('fuentes',[]):
        alumnos=set(str(fuente.get('alumno','')).split(','))-{''}
        material=fuente.get('tipo')=='MATERIAL'
        if alumnos and not alumnos<=ids:continue
        if not material and (not fuente.get('vinculo_verificado') or not alumnos or not alumnos<=ids):continue
        if fuente.get('texto'):resultado.append(deepcopy(fuente))
    return resultado


def texto_curricular(doc):
    cur=doc['metadatos'].get('curriculo',{});lineas=[]
    if cur.get('campo'):lineas.append('Campo formativo: '+cur['campo'])
    if cur.get('ejes'):lineas.append('Ejes: '+', '.join(cur['ejes']))
    for r in cur.get('registros',[]):
        lineas.append(f"{r['fuente']} · Fase {r['fase']} · {r['grado']}° · página PDF {r['pagina_pdf']}\nContenido: {r['contenido']}\nPDA oficial: {r['pda']}")
        ajuste=cur.get('adaptaciones',{}).get(r['id'],{})
        if ajuste:lineas.append('Adaptación docente: '+ajuste.get('contenido','')+'\nObjetivo adaptado: '+ajuste.get('pda',''))
    if cur.get('contexto_local'):lineas.append('Contextualización declarada: '+cur['contexto_local'])
    return '\n\n'.join(lineas)


def prellenar(doc):
    result=deepcopy(doc);meta=result['metadatos'];fuentes=fuentes_pertinentes(doc)
    anteriores=meta.setdefault('campos_autoprellenados',{})
    firma_fuentes=hashlib.sha256(json.dumps(fuentes,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    if meta.get('firma_fuentes_generacion')!=firma_fuentes:
        meta.pop('resumen_ia_completo',None)
        meta['firma_fuentes_generacion']=firma_fuentes
    necesidades='\n\n'.join(f"{f.get('referencia','')} · {f.get('fecha','')} · Registro documentado por confirmar:\n{f['texto'][:1800]}" for f in fuentes if f['tipo']!='MATERIAL' or f.get('alumno'))[:10000]
    valores={'necesidades_confirmadas':necesidades,'referente_curricular':texto_curricular(doc)}
    for campo,value in valores.items():
        if value and (not meta.get(campo) or meta.get(campo)==anteriores.get(campo)):
            meta[campo]=value;anteriores[campo]=value
    if not meta.get('resumen_educativo') and fuentes:
        from services.planeacion import resumen_previo
        meta['resumen_educativo']=resumen_previo(result,fuentes)
    return result


def fechas_sesiones(doc,ajustes):
    desde,hasta=(date.fromisoformat(v) for v in doc['datos']['Periodo'].split(' / '))
    inicio=date.fromisoformat(str(ajustes['inicio']))
    if not desde<=inicio<=hasta:raise ValueError('La fecha inicial debe quedar dentro del trimestre.')
    if not 15<=int(ajustes['duracion'])<=180:raise ValueError('Elige sesiones de 15 a 180 minutos.')
    if not 1<=int(ajustes['sesiones'])<=36:raise ValueError('Elige de una a 36 sesiones.')
    dias=set(ajustes['dias'])
    if not dias or not dias<=set(DIAS):raise ValueError('Selecciona días de lunes a viernes.')
    from services.cronogramas import DIAS_INHABILES
    fechas=[];cursor=inicio
    while cursor<=hasta and len(fechas)<int(ajustes['sesiones']):
        if cursor.weekday()<5 and DIAS[cursor.weekday()] in dias and cursor.isoformat() not in DIAS_INHABILES:fechas.append(cursor.isoformat())
        cursor+=timedelta(days=1)
    if len(fechas)<int(ajustes['sesiones']):raise ValueError('No caben todas las sesiones en estos días del trimestre. Ajusta días, inicio o cantidad.')
    return fechas


def preparar_solicitud(doc,ajustes):
    from services.planeacion import autorizar,resumen_previo
    autorizar(doc,True)
    if doc['formato'] not in ('XXIII','XXV'):raise ValueError('El generador completo trabaja los formatos trimestrales XXIII y XXV.')
    fechas_sesiones(doc,ajustes)
    aliases={'Alumno '+str(i+1):a['ID_Alumno'] for i,a in enumerate(doc['datos']['Alumnos'])}
    reversa={v:k for k,v in aliases.items()}
    evidencias={};fuentes=fuentes_pertinentes(doc)
    for f in fuentes:
        labels=[reversa[i] for i in str(f.get('alumno','')).split(',') if i in reversa]
        if labels:evidencias[f['referencia']]=labels
    notas=doc['metadatos'].get('necesidades_confirmadas','')
    autollenado=doc['metadatos'].get('campos_autoprellenados',{}).get('necesidades_confirmadas')
    if str(notas).strip() and notas!=autollenado:
        evidencias['DOCENTE']=list(aliases)
    if not evidencias:raise ValueError('Falta evidencia educativa del alumno. Actualiza el expediente, incorpora el informe o describe una necesidad documentada antes de generar.')
    contexto=contexto_ia(sugerir_curriculo(doc,ajustes))
    for adaptacion in contexto.get('adaptaciones_docentes',{}).values():
        for campo,value in list(adaptacion.items()):
            adaptacion[campo]=resumen_previo(doc,[{'referencia':'ADAPTACION','alcance':'redacción docente','texto':value}]).split('\n\n',1)[-1][:4000]
    # El resumen visible es lo único que se transmite. Los alias y ajustes no
    # contienen nombres reales; también se minimizan los campos libres.
    resumen=doc['metadatos'].get('resumen_educativo','').strip()
    notas=doc['metadatos'].get('necesidades_confirmadas','')
    extra=resumen_previo(doc,[{'referencia':'DOCENTE','alcance':'información para confirmar','texto':notas}]) if notas else ''
    resumen=(resumen[:9000]+'\n'+extra[:2800]).strip()
    if not resumen:resumen=resumen_previo(doc,fuentes)
    if doc['metadatos'].get('resumen_ia_completo'):
        resumen=doc['metadatos']['resumen_ia_completo'].strip()
    safe=deepcopy(ajustes)
    for campo in ('enfoque','apoyos'):
        safe[campo]=resumen_previo(doc,[{'referencia':'AJUSTE','alcance':'configuración docente; no evidencia de logro','texto':str(ajustes.get(campo,''))}]).split('\n\n',1)[-1][:1500] if ajustes.get(campo) else ''
    firma=huella_completa(resumen,doc['formato'],doc['datos']['Función'],contexto,safe,aliases,evidencias)
    alcance=hashlib.sha256(json.dumps({'documento':doc.get('id',''),'cuenta':doc.get('cuenta',''),'alumnos':sorted(aliases.values()),'escuela':doc['datos']['ID_Escuela'],'formato':doc['formato']},sort_keys=True).encode()).hexdigest()
    return {'resumen':resumen,'contexto':contexto,'ajustes':safe,'configuracion_original':deepcopy(ajustes),'aliases':aliases,'evidencias':evidencias,'huella':firma,'alcance':alcance}


def _quitar_generado_sin_borrar_ediciones(rows,previas):
    restantes=deepcopy(rows)
    for previa in previas:
        candidato=next((i for i,r in enumerate(restantes) if all(r.get(k,'')==v for k,v in previa.items())),None)
        if candidato is not None:restantes.pop(candidato)
    return restantes


def ensamblar(doc,respuesta,solicitud):
    actual=preparar_solicitud(doc,solicitud['configuracion_original'])
    if actual['alcance']!=solicitud['alcance'] or actual['huella']!=solicitud['huella']:raise ValueError('El expediente o los ajustes cambiaron. Revisa la información antes de aplicar la generación.')
    respuesta=validar_completa(respuesta,doc['formato'],doc['datos']['Función'],solicitud['contexto'],solicitud['aliases'],solicitud['evidencias'])
    if not respuesta['unidades']:return deepcopy(doc)
    result=prellenar(sugerir_curriculo(doc,solicitud['configuracion_original']));meta=result['metadatos'];anterior=meta.get('generacion_completa',{})
    for key,rows in anterior.get('filas_generadas',{}).items():
        result['tablas'][key]=_quitar_generado_sin_borrar_ediciones(result['tablas'][key],rows)
    generadas={};unidades=respuesta['unidades'];aliases=solicitud['aliases'];fechas=fechas_sesiones(doc,solicitud['ajustes'])
    if len(unidades)>len(fechas):raise ValueError('Se propusieron más secuencias que sesiones. Aumenta la cantidad o solicita menos secuencias; el borrador anterior se conserva.')
    formato=doc['formato'];area=doc['datos']['Función'];es_equipo=equipo.aplica(result)
    if es_equipo:
        result=equipo.preparar(result);e=result['metadatos']['equipo']
        e['sesiones']=[s for s in e['sesiones'] if not s.get('generada_ia')]
    grupos={};evaluaciones=[]
    for n,u in enumerate(unidades):
        destinatarios=[aliases[a] for a in u['destinatarios']]
        nombre=' / '.join(a['Nombre del alumno'] for a in doc['datos']['Alumnos'] if a['ID_Alumno'] in destinatarios)
        necesidad=nombre+': '+u['necesidad']+' ['+', '.join(u['evidencias'])+']'
        key='barreras' if formato=='XXV' else 'aprendizajes'
        row=({'Barreras para el Aprendizaje y la Participación':necesidad,'Apoyos y/o ajustes razonables':u['apoyos']} if formato=='XXV' else
             {'Necesidades educativas específicas':necesidad,'Aprendizaje y/u objetivo':u['objetivo'],'Descriptor de logro':u['descriptor']})
        generadas.setdefault(key,[]).append(row);result['tablas'][key].append(row)
        evaluaciones.append(u['objetivo']+'\n'+u['evaluacion'])
        if es_equipo:
            identidad=tuple(sorted(destinatarios))
            existente=next((g['nombre'] for g in e['subgrupos'] if tuple(sorted(g['alumnos']))==identidad),None)
            grupo=existente or 'Subgrupo propuesto '+str(len(e['subgrupos'])+1)
            while not existente and grupo in {g['nombre'] for g in e['subgrupos']}:grupo+=' nuevo'
            if not existente:e['subgrupos'].append({'nombre':grupo,'alumnos':destinatarios})
            grupos[n]=grupo
    # Las secuencias se dosifican en las sesiones configuradas. Cada fecha es una
    # propuesta de trabajo, no un registro de asistencia ni una reserva de horario.
    for i,fecha in enumerate(fechas):
        n=i%len(unidades);u=unidades[n]
        actividad=u['actividad']+'\nFundamento: '+u['fundamento']+' ['+', '.join(u['fuentes']+u['referentes'])+']'
        if not es_equipo:actividad+='\nApoyos: '+u['apoyos']+'\nSeguimiento: '+u['evaluacion']
        if es_equipo:
            e['sesiones'].append({'id':'ia-'+solicitud['huella'][:16]+'-'+str(i),'fecha':fecha,'subgrupo':grupos[n],'contexto':u['contexto'],
                'competencias':u['competencias'],'objetivo':u['objetivo'],'actividad':actividad,'apoyos':u['apoyos'],
                'recursos':u['recursos'],'seguimiento':u['evaluacion'],'duracion':int(solicitud['ajustes']['duracion']),'generada_ia':True})
        else:
            row={'Contextos':u['contexto'],'Actividades':actividad,'Temporalidad':fecha+' · '+str(solicitud['ajustes']['duracion'])+' minutos','Recursos':u['recursos']}
            result['tablas']['dosificacion'].append(row);generadas.setdefault('dosificacion',[]).append(row)
    if formato=='XXIII':
        previo=anterior.get('evaluacion_generada','')
        valor='\n\n'.join(dict.fromkeys(evaluaciones))
        if not result['textos'].get('Evaluación') or result['textos']['Evaluación']==previo:result['textos']['Evaluación']=valor
    else:valor=''
    if es_equipo and area=='Psicología':
        for c in e['competencias']:
            asociadas=[u for u in unidades if c['Competencia'] in u['competencias']]
            if asociadas and not any(c.get(k) for k in ('Necesidad documentada','Descriptor de logro','Actividad prevista')):
                c.update({'Necesidad documentada':'\n'.join(dict.fromkeys(u['necesidad'] for u in asociadas)),
                          'Descriptor de logro':'\n'.join(dict.fromkeys(u['descriptor'] for u in asociadas)),
                          'Actividad prevista':'\n'.join(dict.fromkeys(u['actividad'] for u in asociadas))})
        if not e.get('sugerencia_familia'):e['sugerencia_familia']=respuesta['sugerencia_familia']
    grupal=e['grupal'] if es_equipo else meta.setdefault('grupal_zona',[{'ID_Alumno':a['ID_Alumno'],'Fecha derivación':'','Actividades':'','Situación inicial':'','Situación final':''} for a in doc['datos']['Alumnos']])
    for r in grupal:
        alias=next((a for a,i in aliases.items() if i==r['ID_Alumno']),None)
        relevantes=[u for u in unidades if alias in u['destinatarios']]
        if relevantes and not r.get('Actividades'):r['Actividades']='\n'.join(dict.fromkeys(u['objetivo']+' · '+u['actividad'] for u in relevantes))
        fuentes=[f for f in fuentes_pertinentes(doc) if r['ID_Alumno'] in str(f.get('alumno','')).split(',') and f['tipo'] not in {'PLAN','MATERIAL'}]
        if fuentes and not r.get('Situación inicial'):r['Situación inicial']='\n'.join(f.get('referencia','')+' · '+f.get('fecha','')+': '+f['texto'][:900] for f in fuentes[:3])
    meta=result['metadatos']
    meta['generacion_completa']={'huella':solicitud['huella'],'alcance':solicitud['alcance'],'ajustes':deepcopy(solicitud['ajustes']),
       'resultado':deepcopy(respuesta),'configuracion_original':deepcopy(solicitud['configuracion_original']),'filas_generadas':deepcopy(generadas),'evaluacion_generada':valor,'pendientes':respuesta['faltantes'],
       'requiere_revision_docente':True}
    if es_equipo:result=equipo.sincronizar(result)
    return result

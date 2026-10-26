"""Contrato de la hoja Word editable; ningún HTML ni clave de navegador es autoridad."""
from copy import deepcopy
import hashlib
import json
from services import planeacion as s,planeacion_formato as f,planeacion_viva as viva
from services.planeacion_modalidad import guia_grupal,GUIA_XIX
from services.planeacion_modelo import FORMATOS
from services.planeacion_edicion import huella as huella_documento
from services.curriculo import contexto_ia
from services import planeacion_equipo as equipo
from services.planeacion_limpieza import normalizar,tiene_contenido


def huella(doc):
    """Un acuse de persistencia no invalida las celdas que siguen abiertas en el navegador."""
    from services.planeacion_compartida import es_guia,sin_aportes
    copia=sin_aportes(doc) if es_guia(doc) else deepcopy(doc)
    for k in ('revision','anterior','guardado_en','_orden'):copia.pop(k,None)
    for aporte in copia['metadatos'].get('aportaciones_equipo',{}).values():
        aporte.pop('revision',None);aporte.pop('fecha',None)
    return huella_documento(copia)


def hoja(doc,para_impresion=False,colaborativa=False,archivo=False):
    if archivo and not para_impresion:raise PermissionError('El acceso al archivo es solo para lectura e impresión.')
    actor=s.autorizar(doc,False,incluir_bajas=True) if archivo else s.autorizar(doc,not colaborativa and not para_impresion)
    if colaborativa:
        from services.planeacion_colaboracion import compartible
        if not compartible(doc) or actor.get('area') not in ('Psicología','Comunicación','Trabajo Social') or actor.get('director'):
            raise PermissionError('Esta vista permite aportar solo al área asignada del Anexo XIX.')
    aporte_propio=doc['metadatos'].get('aportaciones_equipo',{}).get(actor.get('area'),{})
    bloqueada=colaborativa and (actor['area'] in doc['metadatos'].get('unificacion_grupal',{}).get('conflictos_area',[]) or bool(aporte_propio and aporte_propio.get('cuenta')!=actor['cuenta']))
    firma=huella(doc);doc=normalizar(doc)
    from services.planeacion_necesidades import opciones as opciones_nee
    necesidades_epp=opciones_nee(doc) if not para_impresion else []
    cells={};tables=[]
    def celda(value,target=None,label='',readonly='',destinatario=''):
        key='c'+str(len(cells));cell={'id':key,'value':str(value or ''),'label':label,'editable':target is not None,'referente':readonly}
        if label=='Fecha derivación' and target is not None:
            from services.padron_catalogos import fecha_documental
            try:
                fecha=fecha_documental(value)
                cell.update(tipo='fecha',fecha_iso=fecha.isoformat() if fecha else '')
            except ValueError:pass  # Conservar fechas narrativas históricas, sin vaciarlas.
        if destinatario:cell['destinatario']=str(destinatario)
        if target is not None and label in ('Necesidades educativas específicas','NEE','Necesidad documentada') and not colaborativa:
            # Sugerencias, no un catálogo que sustituya la redacción existente.
            cell['sugerencias_nee']=[] if doc['metadatos'].get('modalidad_planeacion')=='individual' else necesidades_epp
        cells[key]={'target':target,**cell};return cell
    from services import planeacion_intervenciones_nee as intervenciones
    if intervenciones.aplica(doc) and not colaborativa:
        nombres={str(a['ID_Alumno']):a.get('Nombre del alumno',a['ID_Alumno']) for a in doc['datos']['Alumnos']}
        for numero,b in enumerate(intervenciones.bloques(doc),1):
            grupos=[('NEE, objetivo y logro',['NEE','Aprendizaje y/u objetivo','Descriptor de logro']),
                ('Apoyos y ajustes',['Apoyos','Ajustes razonables','Contextos']),
                ('Actividades y evaluación',['Actividades','Temporalidad','Recursos','Evaluación y seguimiento'])]
            for n,(titulo,headers_nee) in enumerate(grupos):
                tables.append({'id':'nee_'+b['id']+'_'+str(n),
                    'title':f'Intervención NEE {numero} · {nombres[b["alumno"]]} · {titulo}',
                    'headers':[intervenciones.etiqueta(doc,c) for c in headers_nee],'rows':[[celda(b['campos'].get(c,''),
                        None if para_impresion else ('intervencion_nee',b['id'],c),intervenciones.etiqueta(doc,c),destinatario=b['alumno']) for c in headers_nee]],
                    'add':False,'delete':False,'widths':[100/len(headers_nee)]*len(headers_nee)})
    grupal=doc['metadatos'].get('modalidad_planeacion')=='grupal' and doc['datos']['Función']=='Aprendizaje' and doc['metadatos'].get('vista_formato')!='trimestral'
    datos=doc['datos'];alumnos=datos['Alumnos'];cur=contexto_ia(doc)
    organizacion=doc['metadatos'].get('equipo',{}) if equipo.aplica(doc) else {}
    curricular='\n\n'.join('Contenido: '+r['contenido']+'\nPDA: '+r['pda']+'\n'+r['fuente']+' · p. '+str(r['pagina_pdf']) for r in cur.get('referentes_por_grado',[]))
    if grupal:
        rows=guia_grupal(doc)['filas'];permitidos=[] if bloqueada else [actor['area']] if colaborativa else viva.campos_guia(doc)
        tables.append({'id':'guia','title':'','headers':GUIA_XIX,'rows':[[celda(row.get(c,''),('aporte' if colaborativa else 'guia',i,c) if c in permitidos else None,c,destinatario=row['ID_Alumno']) for c in GUIA_XIX] for i,row in enumerate(rows)],'add':False,'delete':False,'widths':[14,12,9,14,12,12,12,8,7]})
    if doc['formato']=='XXV':
        tables.append({'id':'alumnos_ts','title':'','headers':['Nombre del alumno','Grado','Grupo'],
            'rows':[[celda(a.get(c,''),label=c) for c in ('Nombre del alumno','Grado','Grupo')] for a in alumnos],
            'add':False,'delete':False,'widths':[70,15,15]})
    if datos['Función']=='Psicología' and organizacion.get('competencias'):
        campos=('Necesidad documentada','Competencia','Descriptor de logro')
        tables.append({'id':'competencias','title':'','headers':['Necesidades Educativas Específicas','Competencias emocionales','Descriptor de logro'],
            'rows':[[celda(row.get(c,''),None if c=='Competencia' else ('competencia',i,c),c) for c in campos] for i,row in enumerate(organizacion['competencias'])],
            'add':False,'delete':False,'widths':[35,30,35]})
        for i,row in enumerate(organizacion['competencias']):
            if row.get('Actividad prevista'):
                celda(row.get('Actividad prevista',''),('competencia',i,'Actividad prevista'),'Actividad prevista')
    for table,headers in FORMATOS[doc['formato']]['tablas'].items():
        # El detalle existente se muestra en la misma hoja, sin copiarlo a otras
        # celdas ni exigir buscarlo en herramientas secundarias.
        if grupal and not any(tiene_contenido(doc,table,r) for r in doc['tablas'][table]):continue
        if table=='aprendizajes' and organizacion.get('competencias') and not doc['tablas'][table]:continue
        labelheaders=list(headers)
        if table=='aprendizajes' and datos['Función']=='Aprendizaje':labelheaders[1]='PDA: nacionales, nacionales contextualizados y/o locales (complementarios)'
        rows=[]
        indices=[]
        for i,row in enumerate(doc['tablas'][table]):
            if not tiene_contenido(doc,table,row) and (grupal or para_impresion or not row.get('_fila_manual')) and not (datos.get('Función')=='Psicología' and table=='dosificacion'):continue
            indices.append(i)
            sid=row.get('_sesion_equipo')
            linked=equipo.sesion_vinculada(doc,sid) if sid else None
            locked=bool(colaborativa or row.get('_aporte') or sid and linked is None)
            cells_row=[celda(row.get(c,''),None if locked else ('sesion',sid,c) if sid else ('tabla',table,i,c),c,
                curricular if table=='aprendizajes' and c=='Aprendizaje y/u objetivo' else '') for c in headers]
            if table=='aprendizajes' and row.get('_nee_origen'):
                cells_row[0]['nota']='NEE propuesta para valoración: puedes mantenerla, cambiarla o eliminarla.' if row['_nee_origen'].get('propuesta') else 'NEE tomada de '+row['_nee_origen']['origen']+'.'
            rows.append(cells_row)
        titulo={'aprendizajes':'Aprendizajes registrados' if grupal else '','dosificacion':'Organización de las actividades de aprendizaje'}.get(table,f.TITULOS.get(table,table))
        tables.append({'id':table,'title':('Detalle ya capturado · ' if grupal else '')+titulo,
            'headers':labelheaders,'rows':rows,'indices':indices,'add':not grupal,'delete':not grupal,
            'collapsed':'Otros aprendizajes y objetivos registrados · editables' if table=='aprendizajes' and organizacion.get('competencias') else '',
            'protected':[i for i,r in enumerate(doc['tablas'][table]) if r.get('_aporte') or r.get('_sesion_equipo') and equipo.sesion_vinculada(doc,r['_sesion_equipo']) is None],
            'widths':[18,52,15,15] if table=='dosificacion' else [26,47,27] if table=='aprendizajes' else []})
    from services import planeacion_evaluacion as evaluacion
    escala=evaluacion.filas(doc)
    if escala:
        tables.append({'id':'escala_trimestral','title':'Escala de valoración de indicadores · cierre del trimestre',
            'headers':list(evaluacion.CAMPOS),'rows':[[celda(r.get(c,''),None if c=='Alumno' else ('escala',i,c),c) for c in evaluacion.CAMPOS] for i,r in enumerate(escala)],
            'add':True,'delete':True,'widths':[17,30,25,13,15],'collapsed':'Evaluación al cierre del trimestre',
            'alumnos':[{'id':a['ID_Alumno'],'nombre':a['Nombre del alumno']} for a in alumnos]})
        for row in tables[-1]['rows']:row[3]['opciones']=list(evaluacion.ESCALA)
    if datos['Función'] == 'Psicología':
        textos = [celda(doc['textos'].get('Observaciones', ''), ('texto', 'Observaciones'), 'Observaciones')]
        if not para_impresion and organizacion:
            textos.append(celda(organizacion.get('sugerencia_familia', ''), ('equipo', 'sugerencia_familia'), 'Sugerencia prevista para la familia y referencia de su hoja'))
    else:
        textos=[celda(v,None if colaborativa else ('texto',k),k) for k,v in doc['textos'].items() if str(v or '').strip() or not (para_impresion or grupal)]
        if colaborativa:
            aporte=doc['metadatos'].get('aportaciones_equipo',{}).get(actor['area'],{})
            textos.append(celda(aporte.get('observaciones',''),None if bloqueada else ('aporte_obs',),'Observaciones de mi área'))
        if datos['Función']=='Psicología' and organizacion and (not para_impresion or str(organizacion.get('sugerencia_familia','')).strip()):
            textos.append(celda(organizacion.get('sugerencia_familia',''),('equipo','sugerencia_familia'),'Sugerencia prevista para la familia y referencia de su hoja'))
    header=[['Zona: '+str(datos['Zona']),'Servicio de Apoyo: '+datos['Servicio de apoyo']],
            ['Escuela Regular: '+datos['Escuela regular'],'Fase: '+', '.join(sorted({str(a.get('Fase de inscripción') or '') for a in alumnos}))],
            ['Nombre del alumno/a: '+', '.join(a['Nombre del alumno'] for a in alumnos),'Grado: '+', '.join(sorted({str(a['Grado'])+' '+str(a['Grupo']) for a in alumnos}))],
            ['Nombre del especialista: '+datos['Nombre del especialista'],'Trimestre: '+str(datos['Trimestre'])+' · '+datos['Periodo']],
            ['Condición: '+', '.join(sorted({a.get('Condición','') for a in alumnos})),'Función: '+datos['Función']+' · Curso '+datos['Curso escolar']]]
    if doc['formato']=='XXV':
        header=[['Servicio de apoyo: '+datos['Servicio de apoyo'],'Zona: '+str(datos['Zona'])],
                ['Periodo: '+datos['Periodo'],'Escuela Regular: '+datos['Escuela regular']]]
    elif grupal:
        from services.planeacion_ambito import etiqueta as etiqueta_grupo
        maestro=guia_grupal(doc)['maestro_grupo']
        campo_maestro=celda(maestro,('maestro_grupo',),'Maestro/a de grupo regular') if not colaborativa else 'Maestro de grupo: '+maestro
        header=[['Curso escolar: '+datos['Curso escolar'],campo_maestro],
                ['Escuela: '+datos['Escuela regular'],'Grado y grupo: '+etiqueta_grupo(doc)]]
    elif datos.get('Función') == 'Psicología':
        fases = ', '.join(sorted({str(a.get('Fase de inscripción') or '') for a in alumnos if a.get('Fase de inscripción')})) or '-'
        grados = ', '.join(sorted({str(a.get('Grado') or '') for a in alumnos if a.get('Grado')})) or '-'
        grupos = ', '.join(sorted({str(a.get('Grupo') or '') for a in alumnos if a.get('Grupo')})) or '-'
        header = [
            ['Zona: ' + str(datos.get('Zona', '')), 'Servicio de Apoyo: ' + str(datos.get('Servicio de apoyo', ''))],
            ['Escuela Regular: ' + str(datos.get('Escuela regular', '')), 'Fase: ' + fases, 'Grado: ' + grados, 'Grupo: ' + grupos, 'Trimestre: ' + str(datos.get('Trimestre', ''))],
            ['Nombre de los alumnos individuales:\n' + ', '.join(a.get('Nombre del alumno', '') for a in alumnos)],
            ['Nombre del especialista: ' + str(datos.get('Nombre del especialista', '')), 'Función: ' + str(datos.get('Función', ''))]
        ]
    else:
        header=[header[0],[header[1][0]+'\n'+header[2][0]+'\n'+header[3][0],
            header[1][1]+'\n'+header[2][1],header[3][1]+'\n'+header[4][0]+'\n'+header[4][1]]]
    from services.planeacion_revision import pendientes
    _,avisos=pendientes(doc)
    if grupal and not guia_grupal(doc)['maestro_grupo']:
        avisos.append({'mensaje':'Falta el nombre del maestro de grupo regular. Captúralo aquí o en el padrón.', 'target':('maestro_grupo',),'panel':'detalle'})
    if colaborativa:avisos=[]
    for aviso in avisos:
        aviso['celda']=next((k for k,c in cells.items() if c['target']==aviso['target']),None)
        if not aviso['celda'] and aviso['target'] and aviso['target'][0]=='tabla':aviso['panel']='tabla:'+aviso['target'][1]
    if colaborativa:
        # Las celdas de solo lectura pueden actualizarse sin invalidar el texto
        # en vuelo de esta área. La matrícula y los destinos sí son parte del contrato.
        contrato=[doc['id'],actor['cuenta'],actor['area'],
            [a['ID_Alumno'] for a in alumnos],
            [(k,c['target'],c['value']) for k,c in cells.items() if c['editable']]]
        firma=hashlib.sha256(json.dumps(contrato,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    return {'documento':doc['id'],'huella':firma,'titulo':'Guía de Planeación Grupal' if grupal else FORMATOS[doc['formato']]['titulo'],
        'nee_intervenciones':[{**r,'alumno_nombre':nombres.get(r['alumno_id'],r['alumno_id'])} for r in intervenciones.catalogo(doc)] if intervenciones.aplica(doc) and not colaborativa and not para_impresion else [],
        'header':header,'tables':tables,'textos':textos,'cells':cells,'grupal':grupal,'colaborativa':colaborativa,
        'cache_id':hashlib.sha256((actor.get('cuenta','')+'|'+actor.get('area','')+'|'+doc['id']).encode()).hexdigest(),
        'pendientes':avisos,
        'firma':datos['Nombre del especialista']+'\nTrabajo Social' if doc['formato']=='XXV' else 'Nombre y firma del Especialista','vobo':'Vo. Bo. Director del Servicio de Apoyo'}


def aplicar(doc,event):
    s.autorizar(doc,True)
    spec=hoja(doc)
    if not isinstance(event,dict) or event.get('documento')!=doc['id'] or event.get('huella')!=spec['huella']:
        raise ValueError('La hoja cambió. Tu texto debe conservarse en el respaldo antes de volver a aplicar.')
    cambios=event.get('cambios',{})
    if not isinstance(cambios,dict) or len(cambios)>1500:raise ValueError('Cambios fuera del formato.')
    result=normalizar(doc);patch={};base=guia_grupal(doc).get('filas',[])
    for key,value in cambios.items():
        cell=spec['cells'].get(key)
        if not cell or not cell['editable']:raise PermissionError('Esta celda procede del padrón o de otra aportación.')
        if not isinstance(value,str) or len(value)>20000:raise ValueError('Revisa la extensión del texto de la celda.')
        target=cell['target']
        if cell.get('tipo')=='fecha' and value.strip():
            from services.padron_catalogos import fecha_documental
            value=fecha_documental(value).strftime('%d/%m/%Y')
        if target[0]=='tabla':
            if target[2]==len(result['tablas'][target[1]]):result=f.nueva_fila(result,target[1])
            result=f.editar_celda(result,*target[1:],value)
            if doc['datos'].get('Función') == 'Psicología' and target[1] == 'dosificacion':
                fila = result['tablas']['dosificacion'][target[2]]
                ctx = str(fila.get('Contextos', '')).strip().lower()
                if ctx == 'familia' and target[3] == 'Actividades':
                    result['metadatos'].setdefault('equipo', {})['sugerencia_familia'] = value
                elif ctx in ('evaluación', 'evaluacion') and target[3] == 'Actividades':
                    result['textos']['Evaluación'] = value
        elif target[0]=='intervencion_nee':
            from services.planeacion_intervenciones_nee import editar
            result=editar(result,*target[1:],value)
        elif target[0]=='texto':
            result['textos'][target[1]]=value
            if doc['datos'].get('Función') == 'Psicología' and target[1] == 'Evaluación':
                for r in result['tablas'].get('dosificacion', []):
                    if str(r.get('Contextos', '')).strip().lower() in ('evaluación', 'evaluacion') and not r.get('_sesion_equipo'):
                        r['Actividades'] = value
        elif target[0]=='guia':patch.setdefault(target[1],{})[target[2]]=value
        elif target[0]=='sesion':result=equipo.editar_en_formato(result,*target[1:],value)
        elif target[0]=='competencia':result['metadatos']['equipo']['competencias'][target[1]][target[2]]=value
        elif target[0]=='equipo':
            result['metadatos']['equipo'][target[1]]=value
            if target[1] == 'sugerencia_familia':
                for r in result['tablas'].get('dosificacion', []):
                    if str(r.get('Contextos', '')).strip().lower() == 'familia' and not r.get('_sesion_equipo'):
                        r['Actividades'] = value
                        if not r.get('Recursos'): r['Recursos'] = 'Hoja de sugerencias.'
        elif target[0]=='maestro_grupo':
            result['metadatos'].setdefault('guia_grupal_manual',{})['maestro_grupo']=value
            result['metadatos']['maestro_regular_edicion_manual']=True
        elif target[0]=='escala':
            from services.planeacion_evaluacion import editar
            result=editar(result,*target[1:],value)
    if patch:result=viva.editar_guia(result,{'edited_rows':patch},base)
    action=event.get('accion','guardar')
    if action in ('agregar','retirar'):
        table=event.get('tabla')
        if table=='escala_trimestral' and not spec['grupal']:
            from services.planeacion_evaluacion import cambiar_fila
            if action=='retirar' and event.get('confirmado') is not True:raise ValueError('Confirma el retiro del indicador.')
            return cambiar_fila(result,event.get('fila') if action=='retirar' else None,event.get('alumno'))
        if table not in doc['tablas'] or spec['grupal']:raise ValueError('Selecciona una tabla del formato.')
        if action=='agregar':
            result=f.nueva_fila(result,table);result['tablas'][table][-1]['_fila_manual']=True
        else:
            i=event.get('fila')
            if not isinstance(i,int) or event.get('confirmado') is not True:raise ValueError('Confirma el retiro de la fila.')
            if not 0<=i<len(result['tablas'][table]) or result['tablas'][table][i].get('_aporte'):raise PermissionError('Conserva la aportación de su autor.')
            result=f.quitar_fila(result,table,i)
    elif action=='incorporar_nee':
        from services.planeacion_intervenciones_nee import incorporar
        result=incorporar(result,event.get('nee_ids'))
    elif action=='apartados':
        from services.planeacion_apartados import proponer
        result=proponer(result)
    elif action=='corregir':
        if event.get('panel') not in {a['panel'] for a in spec['pendientes']}:raise ValueError('Destino de corrección no válido.')
    elif action not in ('guardar','autoguardar','pdf','enviar','antecedentes','referentes','dua','ia','alumnos','detalle','inicio','equipo','opciones'):raise ValueError('Acción no reconocida.')
    return result


def aplicar_aporte(doc,event,con_observaciones=False):
    """Parche estrictamente acotado; ni el navegador ni el especialista reescriben otra área."""
    spec=hoja(doc,colaborativa=True);actor=s.identidad()
    if not isinstance(event,dict) or event.get('documento')!=doc['id'] or event.get('huella')!=spec['huella']:
        raise ValueError('El formato cambió. Conserva tu texto y actualiza antes de aplicar.')
    if event.get('accion') not in ('guardar','autoguardar','inicio'):raise PermissionError('Guarda tu aportación; la maestra coordina las demás acciones del Anexo XIX.')
    from services.planeacion_colaboracion import COLUMNAS
    filas=deepcopy(doc['metadatos'].get('aportaciones_equipo',{}).get(actor['area'],{}).get('filas',[]))
    observaciones=doc['metadatos'].get('aportaciones_equipo',{}).get(actor['area'],{}).get('observaciones','')
    cambios=event.get('cambios',{})
    if not isinstance(cambios,dict) or len(cambios)>500:raise ValueError('Revisa la aportación.')
    for key,value in cambios.items():
        c=spec['cells'].get(key)
        if not c or not c['editable'] or c['target'][0] not in ('aporte','aporte_obs'):raise PermissionError('Solo puedes cambiar tu columna del formato.')
        if not isinstance(value,str) or len(value)>4000:raise ValueError('Cada aportación admite hasta 4 000 caracteres.')
        if c['target'][0]=='aporte_obs':
            observaciones=value
            continue
        aid=doc['datos']['Alumnos'][c['target'][1]]['ID_Alumno']
        fila=next((r for r in filas if r['ID_Alumno']==aid),None)
        if fila is None:
            fila={k:'' for k in COLUMNAS};fila['ID_Alumno']=aid;filas.append(fila)
        fila['Texto en formato']=value
        fila['_celda_viva']=True
    return (filas,observaciones) if con_observaciones else filas

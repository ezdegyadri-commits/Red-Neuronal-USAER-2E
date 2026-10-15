"""Contrato de la hoja Word editable; ningún HTML ni clave de navegador es autoridad."""
from copy import deepcopy
from services import planeacion as s,planeacion_formato as f,planeacion_viva as viva
from services.planeacion_modalidad import guia_grupal,GUIA_XIX
from services.planeacion_modelo import FORMATOS
from services.planeacion_edicion import huella
from services.curriculo import contexto_ia
from services import planeacion_equipo as equipo


def hoja(doc):
    s.autorizar(doc,True)
    cells={};tables=[]
    def celda(value,target=None,label='',readonly=''):
        key='c'+str(len(cells));cell={'id':key,'value':str(value or ''),'label':label,'editable':target is not None,'referente':readonly}
        cells[key]={'target':target,**cell};return cell
    grupal=doc['metadatos'].get('modalidad_planeacion')=='grupal' and doc['datos']['Función']=='Aprendizaje' and doc['metadatos'].get('vista_formato')!='trimestral'
    datos=doc['datos'];alumnos=datos['Alumnos'];cur=contexto_ia(doc)
    organizacion=doc['metadatos'].get('equipo',{}) if equipo.aplica(doc) else {}
    curricular='\n\n'.join('Contenido: '+r['contenido']+'\nPDA: '+r['pda']+'\n'+r['fuente']+' · p. '+str(r['pagina_pdf']) for r in cur.get('referentes_por_grado',[]))
    if grupal:
        rows=guia_grupal(doc)['filas'];permitidos=viva.campos_guia(doc)
        tables.append({'id':'guia','title':'','headers':GUIA_XIX,'rows':[[celda(row.get(c,''),('guia',i,c) if c in permitidos else None,c) for c in GUIA_XIX] for i,row in enumerate(rows)],'add':False,'delete':False,'widths':[14,12,9,14,12,12,12,8,7]})
    if doc['formato']=='XXV':
        tables.append({'id':'alumnos_ts','title':'','headers':['Nombre del alumno','Grado','Grupo'],
            'rows':[[celda(a.get(c,''),label=c) for c in ('Nombre del alumno','Grado','Grupo')] for a in alumnos],
            'add':False,'delete':False,'widths':[70,15,15]})
    if datos['Función']=='Psicología' and organizacion.get('competencias'):
        campos=('Necesidad documentada','Competencia','Descriptor de logro')
        tables.append({'id':'competencias','title':'','headers':['Necesidades educativas específicas','Competencias emocionales','Descriptor de logro'],
            'rows':[[celda(row.get(c,''),None if c=='Competencia' else ('competencia',i,c),c) for c in campos] for i,row in enumerate(organizacion['competencias'])],
            'add':False,'delete':False,'widths':[34,33,33]})
    for table,headers in FORMATOS[doc['formato']]['tablas'].items():
        # La guía horizontal es el documento grupal principal; el detalle sigue
        # conectado y disponible sin convertir la hoja en tarjetas de edición.
        if grupal:continue
        if table=='aprendizajes' and organizacion.get('competencias') and not doc['tablas'][table]:continue
        labelheaders=list(headers)
        if table=='aprendizajes' and datos['Función']=='Aprendizaje':labelheaders[1]='PDA: nacionales, nacionales contextualizados y/o locales (complementarios)'
        rows=[]
        for i,row in enumerate(doc['tablas'][table] or [{}]):
            sid=row.get('_sesion_equipo')
            linked=equipo.sesion_vinculada(doc,sid) if sid else None
            locked=bool(row.get('_aporte') or sid and linked is None)
            cells_row=[celda(row.get(c,''),None if locked else ('sesion',sid,c) if sid else ('tabla',table,i,c),c,
                curricular if table=='aprendizajes' and c=='Aprendizaje y/u objetivo' else '') for c in headers]
            if table=='aprendizajes' and row.get('_nee_origen'):
                cells_row[0]['nota']='NEE propuesta para valoración: puedes mantenerla, cambiarla o eliminarla.' if row['_nee_origen'].get('propuesta') else 'NEE tomada de '+row['_nee_origen']['origen']+'.'
            rows.append(cells_row)
        tables.append({'id':table,'title':{'aprendizajes':'','dosificacion':'Organización de las actividades de aprendizaje'}.get(table,f.TITULOS.get(table,table)),
            'headers':labelheaders,'rows':rows,'add':True,'delete':True,
            'collapsed':'Otros aprendizajes y objetivos registrados · editables' if table=='aprendizajes' and organizacion.get('competencias') else '',
            'protected':[i for i,r in enumerate(doc['tablas'][table]) if r.get('_aporte') or r.get('_sesion_equipo') and equipo.sesion_vinculada(doc,r['_sesion_equipo']) is None],
            'widths':[18,52,15,15] if table=='dosificacion' else [26,47,27] if table=='aprendizajes' else []})
    textos=[celda(v,('texto',k),k) for k,v in doc['textos'].items()] if not grupal else []
    if datos['Función']=='Psicología' and organizacion:
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
        header=[['Curso escolar: '+datos['Curso escolar'],'Maestro de grupo: '+guia_grupal(doc)['maestro_grupo']],
                ['Escuela: '+datos['Escuela regular'],'Grado y grupo: '+', '.join(sorted({str(a['Grado'])+' '+str(a['Grupo']) for a in alumnos}))]]
    else:
        header=[header[0],[header[1][0]+'\n'+header[2][0]+'\n'+header[3][0],
            header[1][1]+'\n'+header[2][1],header[3][1]+'\n'+header[4][0]+'\n'+header[4][1]]]
    return {'documento':doc['id'],'huella':huella(doc),'titulo':'Guía de Planeación Grupal' if grupal else FORMATOS[doc['formato']]['titulo'],
        'header':header,'tables':tables,'textos':textos,'cells':cells,'grupal':grupal,
        'firma':datos['Nombre del especialista']+'\nTrabajo Social' if doc['formato']=='XXV' else 'Nombre y firma del Especialista','vobo':'Vo. Bo. Director del Servicio de Apoyo'}


def aplicar(doc,event):
    s.autorizar(doc,True)
    spec=hoja(doc)
    if not isinstance(event,dict) or event.get('documento')!=doc['id'] or event.get('huella')!=spec['huella']:
        raise ValueError('La hoja cambió. Tu texto debe conservarse en el respaldo antes de volver a aplicar.')
    cambios=event.get('cambios',{})
    if not isinstance(cambios,dict) or len(cambios)>1500:raise ValueError('Cambios fuera del formato.')
    result=deepcopy(doc);patch={};base=guia_grupal(doc).get('filas',[])
    for key,value in cambios.items():
        cell=spec['cells'].get(key)
        if not cell or not cell['editable']:raise PermissionError('Esta celda procede del padrón o de otra aportación.')
        if not isinstance(value,str) or len(value)>20000:raise ValueError('Revisa la extensión del texto de la celda.')
        target=cell['target']
        if target[0]=='tabla':
            if target[2]==len(result['tablas'][target[1]]):result=f.nueva_fila(result,target[1])
            result=f.editar_celda(result,*target[1:],value)
        elif target[0]=='texto':result['textos'][target[1]]=value
        elif target[0]=='guia':patch.setdefault(target[1],{})[target[2]]=value
        elif target[0]=='sesion':result=equipo.editar_en_formato(result,*target[1:],value)
        elif target[0]=='competencia':result['metadatos']['equipo']['competencias'][target[1]][target[2]]=value
        elif target[0]=='equipo':result['metadatos']['equipo'][target[1]]=value
    if patch:result=viva.editar_guia(result,{'edited_rows':patch},base)
    action=event.get('accion','guardar')
    if action in ('agregar','retirar'):
        table=event.get('tabla')
        if table not in doc['tablas'] or spec['grupal']:raise ValueError('Selecciona una tabla del formato.')
        if action=='agregar':result=f.nueva_fila(result,table)
        else:
            i=event.get('fila')
            if not isinstance(i,int) or event.get('confirmado') is not True:raise ValueError('Confirma el retiro de la fila.')
            if not 0<=i<len(result['tablas'][table]) or result['tablas'][table][i].get('_aporte'):raise PermissionError('Conserva la aportación de su autor.')
            result=f.quitar_fila(result,table,i)
    elif action=='apartados':
        from services.planeacion_apartados import proponer
        result=proponer(result)
    elif action not in ('guardar','autoguardar','pdf','enviar','antecedentes','referentes','dua','ia','alumnos','detalle'):raise ValueError('Acción no reconocida.')
    return result

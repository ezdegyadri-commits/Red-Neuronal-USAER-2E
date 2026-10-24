"""Contrato del Anexo XVII vivo. El navegador no decide alumno, área ni permisos."""
from copy import deepcopy
import hashlib
import json
from services import epp as s
from services.epp_modelo import AREAS, SECCIONES, GENERALES, CONCLUSION, NEE, BAP, HISTORIA, FAMILIA, vacia, validar_parte
from services.epp_entrada import precargar


def contenido(doc,area):
    v=vacia(area)
    saved=doc['partes'].get(area,{}).get('contenido',{})
    for k,x in saved.items():
        if isinstance(x,dict) and isinstance(v.get(k),dict):v[k].update(deepcopy(x))
        else:v[k]=deepcopy(x)
    return v


def editables(doc):
    a=s.autorizar(doc)
    if a['director'] or a['area'] not in AREAS:return []
    result=[a['area']]
    if s.es_coordinadora(doc):result.append('Conclusión')
    return result if doc['partes']['META']['estado']!='ELIMINADO' else []


def hoja(doc):
    allowed=editables(doc);a=s.actor();alumno=s.alumno_autorizado(doc['alumno'])
    values={area:contenido(doc,area) for area in (*AREAS,'Conclusión')}
    values['Aprendizaje']=precargar(values['Aprendizaje'],alumno)
    cells={};tables=[]
    def cell(area,section,field,label=None,index=None):
        target=[area,section,field] if index is None else [area,section,index,field]
        key='e'+hashlib.sha256(json.dumps(target,ensure_ascii=False).encode()).hexdigest()[:16]
        value=values[area].get(section,{}).get(field,'') if section and index is None else values[area].get(field,'') if not section else values[area][section][index].get(field,'')
        c={'id':key,'target':target,'value':str(value or ''),'label':label or field,'editable':area in allowed}
        cells[key]=c;return c
    general=[]
    for field in GENERALES:general.append([cell('Aprendizaje','generales',field)])
    tables.append({'id':'generales','title':'1. Datos generales','headers':['Datos del alumno y su familia'],
        'rows':[[{**c,'nota':c['label']} for c in row] for row in general], 'add':False,'delete':False})
    # El rótulo y el contenido se mantienen separados para no guardar etiquetas.
    tables[-1]['headers']=['Dato','Información registrada']
    tables[-1]['rows']=[[{'id':'label_'+c['id'],'value':c['label'],'label':c['label'],'editable':False,'target':None},c] for [c] in general]
    for row in tables[-1]['rows']:cells[row[0]['id']]=row[0]
    instruments=[]
    for area in AREAS:
        safe=hashlib.sha256(area.encode()).hexdigest()[:16]
        label={'id':'area_'+safe,'value':area,'label':'Área','editable':False,'target':None};cells[label['id']]=label
        author={'id':'autor_'+safe,'value':doc['partes'].get(area,{}).get('autor',''),'label':'Especialista que aplicó · '+area,'editable':False,'target':None};cells[author['id']]=author
        instruments.append([label,cell(area,None,'instrumentos','Instrumentos aplicados · '+area),author,cell(area,None,'fecha_aplicacion','Fechas de aplicación · '+area)])
    tables.append({'id':'instrumentos','title':'Instrumentos aplicados','headers':['Área','Instrumentos','Especialista que aplicó','Fecha(s)'],'rows':instruments,'add':False,'delete':False})
    def tabla(area,name,headers,title):
        values[area].setdefault(name,[])
        if not values[area][name]:values[area][name]=[dict.fromkeys(headers,'')]
        tables.append({'id':area+'|'+name,'title':title,'headers':headers,
            'rows':[[cell(area,name,f,index=i) for f in headers] for i in range(len(values[area][name]))],
            'add':area in allowed,'delete':area in allowed})
    for section,areas in SECCIONES.items():
        rows=[]
        for area,fields in areas.items():
            for field in fields:
                label={'id':'label_'+hashlib.sha256(field.encode()).hexdigest()[:16],'value':field+' · '+area,'label':field,'editable':False,'target':None};cells[label['id']]=label
                rows.append([label,cell(area,'campos',field)])
        tables.append({'id':section,'title':section,'headers':['Aspecto','Descripción y hallazgos'],'rows':rows,'widths':[28,72],'add':False,'delete':False})
        if section.startswith('6.'):
            tabla('Aprendizaje','historia',HISTORIA,'Historia escolar')
            tabla('Trabajo Social','familia',FAMILIA,'Composición familiar')
    rows=[]
    for field in CONCLUSION:
        label={'id':'label_'+hashlib.sha256(field.encode()).hexdigest()[:16],'value':field,'label':field,'editable':False,'target':None};cells[label['id']]=label
        rows.append([label,cell('Conclusión','campos',field)])
    tables.append({'id':'conclusion','title':'7. Conclusión interdisciplinaria','headers':['Aspecto','Acuerdo del equipo'],'rows':rows,'widths':[28,72],'add':False,'delete':False})
    tabla('Conclusión','nee',NEE,'7.2. Determinación de NEE, apoyos y ajustes razonables')
    tabla('Conclusión','bap',BAP,'7.3. Barreras para el aprendizaje y la participación')
    textos=[cell(area,None,'sintesis','Síntesis y aspectos por confirmar · '+area) for area in AREAS]
    own=[(k,c['target'],c['value']) for k,c in cells.items() if c['editable']]
    digest=hashlib.sha256(json.dumps([doc['id'],a['cuenta'],allowed,own],ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    return {'documento':doc['id'],'huella':digest,'tipo_documento':'epp','titulo':'Informe de Evaluación Psicopedagógica · Anexo XVII',
        'header':[['Servicio de Apoyo: USAER 02-E','Ciclo escolar: '+doc['ciclo']],
                  ['Escuela: '+str(alumno.get('Nombre_Escuela','')),'Grado y grupo: '+str(alumno.get('Grado',''))+' '+str(alumno.get('Grupo',''))],
                  ['Nivel educativo: '+str(alumno.get('Nivel_Educativo','')),'Zona escolar: 001'],
                  ['Fecha de elaboración: '+max((r.get('fecha','') for r in doc['partes'].values()),default='')[:10]],
                  ['Nombre del alumno/a: '+str(alumno.get('Nombre_Completo',''))],
                  ['CURP: '+str(alumno.get('CURP','')),'Mi función: '+a['area']]],
        'tables':tables,'cells':cells,'textos':textos,'colaborativa':True,'grupal':False,'pendientes':[],
        'cache_id':hashlib.sha256(('epp|'+a['cuenta']+'|'+doc['id']).encode()).hexdigest(),
        'firma':'Personas implicadas · Nombre, función y firma','vobo':'Directores de Escuela y Servicio de Apoyo · Firma y sello',
        'puede_editar':bool(allowed)}


def aplicar(doc,event,huella_esperada=None):
    spec=hoja(doc)
    if not isinstance(event,dict) or event.get('documento')!=doc['id'] or event.get('huella')!=(huella_esperada or spec['huella']):
        raise ValueError('La hoja cambió. Tu texto se conserva; respáldalo antes de revisar la versión reciente.')
    cambios=event.get('cambios',{})
    if not isinstance(cambios,dict) or len(cambios)>500:raise ValueError('Cambios fuera del formato EPP.')
    result=deepcopy(doc);modified=set()
    def value(area):
        result['partes'].setdefault(area,{'contenido':contenido(doc,area),'revision':''})
        return result['partes'][area]['contenido']
    for key,text in cambios.items():
        c=spec['cells'].get(key)
        if not c or not c['editable']:raise PermissionError('Solo puedes modificar los apartados de tu función.')
        if not isinstance(text,str) or len(text)>12000:raise ValueError('El texto supera el límite de este apartado.')
        area,section,*path=c['target'];v=value(area)
        if len(path)==2:
            index,field=path;v.setdefault(section,[])
            while len(v[section])<=index:v[section].append({})
            v[section][index][field]=text
        elif section:v.setdefault(section,{})[path[0]]=text
        else:v[path[0]]=text
        if section=='generales':v['generales_editados']=sorted(set(v.get('generales_editados',[]))|{path[0]})
        v['validada']=False;modified.add(area)
    action=event.get('accion','guardar')
    if action in ('agregar','retirar'):
        parts=str(event.get('tabla','')).split('|')
        if len(parts)!=2:raise ValueError('Tabla no editable.')
        area,name=parts
        if area not in editables(doc) or name not in {'familia','historia','nee','bap'}:raise PermissionError('Tabla fuera de tu función.')
        v=value(area);headers={'familia':FAMILIA,'historia':HISTORIA,'nee':NEE,'bap':BAP}[name]
        if action=='agregar':v.setdefault(name,[]).append(dict.fromkeys(headers,''))
        else:
            i=event.get('fila')
            if event.get('confirmado') is not True or not isinstance(i,int) or not 0<=i<len(v.get(name,[])):raise ValueError('Confirma una fila existente para retirarla.')
            v[name].pop(i)
        v['validada']=False;modified.add(area)
    elif action not in {'guardar','autoguardar','inicio','pdf','antecedentes','ia','opciones','equipo'}:raise ValueError('Acción EPP no reconocida.')
    for area in modified:result['partes'][area]['contenido']=validar_parte(area,result['partes'][area]['contenido'])
    return result,modified


def recuperar(doc,respaldo,area):
    """Recuperación explícita, acotada al mismo informe y función autorizada."""
    if area not in editables(doc):raise PermissionError('El respaldo debe corresponder a tu función.')
    if not isinstance(respaldo,dict) or respaldo.get('documento',respaldo.get('id',respaldo.get('informe')))!=doc['id']:
        raise ValueError('El respaldo pertenece a otra EPP; no se incorporó información.')
    if respaldo.get('tipo')=='usaer-texto-pendiente-v2':
        spec=hoja(doc);changes={}
        for entry in respaldo.get('celdas',[]):
            cell=next((c for c in spec['cells'].values() if c['editable'] and c['target']==entry.get('target') and c['target'][0]==area),None)
            if not cell:raise PermissionError('El respaldo contiene una celda fuera de tu función o una tabla que cambió.')
            if cell['value'] not in (entry.get('base'),entry.get('valor')):
                raise RuntimeError('El dato '+cell['label']+' tiene una edición más reciente. Compara el respaldo con la hoja y combina el texto manualmente; no se sobrescribió.')
            changes[cell['id']]=entry.get('valor')
        if not changes:raise ValueError('Este respaldo no contiene texto pendiente para tu área.')
        result,_=aplicar(doc,{'documento':doc['id'],'huella':spec['huella'],'cambios':changes,'accion':'guardar'})
        return contenido(result,area)
    if 'partes' in respaldo:value=respaldo['partes'].get(area,{}).get('contenido')
    else:
        if respaldo.get('area')!=area:raise PermissionError('El respaldo corresponde a otra área.')
        value=respaldo.get('contenido')
    value=validar_parte(area,value);value['validada']=False
    return value

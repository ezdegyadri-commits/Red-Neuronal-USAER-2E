"""Continuidad documental local. No crea diagnósticos, aprobaciones ni copias de expedientes."""
from copy import deepcopy
from datetime import date,datetime
from zoneinfo import ZoneInfo
import json


def actualizar_vinculos(doc):
    result=deepcopy(doc);meta=result['metadatos'];vinculos=[];avisos=[]
    anteriores=meta.get('vinculos_documentales',[])
    for alumno in doc['datos']['Alumnos']:
        aid=alumno['ID_Alumno']
        fuentes=[f for f in meta.get('fuentes',[]) if aid in str(f.get('alumno','')).split(',') and f.get('vinculo_verificado')]
        epps=[f for f in fuentes if f.get('tipo')=='EPP' and f.get('parte')=='Conclusión']
        pis=[f for f in fuentes if f.get('tipo')=='PLAN' and f.get('formato')=='XXI']
        for tipo,candidatos in [('EPP',epps),('PI',pis)]:
            por_id={f.get('documento_origen',f.get('registro')):f for f in candidatos}
            if len(por_id)>1:
                avisos.append(f'{tipo}: hay varios documentos vigentes para un alumno; coordina su revisión antes de elegir uno.');continue
            if not por_id:continue
            f=next(iter(por_id.values()))
            vinculos.append({'alumno':aid,'tipo':tipo,'documento':f.get('documento_origen',f['registro']),
                             'revision':f.get('revision',''),'referencia':f['referencia']})
    for old in anteriores:
        actual=next((v for v in vinculos if (v['alumno'],v['tipo'])==(old['alumno'],old['tipo'])),None)
        if actual!=old:avisos.append('Cambió o dejó de estar disponible una fuente vinculada. Revisa la coherencia de las actividades; tu redacción se conserva.')
    meta['vinculos_documentales']=vinculos
    meta['avisos_continuidad']=list(dict.fromkeys(avisos))
    if doc['formato']=='XXI':
        epp=next((v for v in vinculos if v['tipo']=='EPP'),None)
        if epp and not meta.get('fuente_iepp'):meta['fuente_iepp']=epp['documento']+' · revisión '+epp['revision']
    return result


def vigente_pi(plan,ciclo):
    try:
        inicio=int(plan['datos']['Curso escolar'].split('-')[0]);actual=int(ciclo.split('-')[0])
        vigencia=int(plan['datos'].get('Vigencia en cursos escolares') or 1)
        return 1<=vigencia<=3 and inicio<=actual<inicio+vigencia
    except (ValueError,TypeError,KeyError):return False


def trasladar_epp(doc):
    """Precarga solamente columnas vacías; la coordinación confirma pertinencia y prioridades."""
    if doc['formato']!='XXI':raise ValueError('Esta acción corresponde al Plan de Intervención.')
    result=deepcopy(doc)
    v=next((v for v in result['metadatos'].get('vinculos_documentales',[]) if v['tipo']=='EPP'),None)
    if not v:raise ValueError('Falta una conclusión vigente de EPP revisada por el equipo.')
    f=next(f for f in result['metadatos']['fuentes'] if f['referencia']==v['referencia'])
    datos=json.loads(f['texto'])
    tablas=result['tablas']
    if not tablas['necesidades']:
        tablas['necesidades']=[{'NEE':r.get('NEE',''),'Aprendizajes y/u Objetivos':'','Descriptor de Logro':'',
            'Apoyos o ajustes':' / '.join(str(r.get(k,'')) for k in ('Apoyos','Ajustes razonables') if r.get(k)),
            'Responsables':r.get('Responsables',''),'Temporalidad':r.get('Fecha o período',''),
            '_fuente':v} for r in datos.get('NEE',[]) if r.get('NEE')]
    if not tablas['barreras']:
        tablas['barreras']=[{'BAP':r.get('Tipo de barrera',''),'Acciones para minimizarla o eliminarla':r.get('Acciones generales',''),
            'Responsable':r.get('Responsables',''),'Temporalidad':r.get('Fecha o período',''),'_fuente':v}
            for r in datos.get('BAP',[]) if r.get('Tipo de barrera')]
    return result


def seguimiento(doc,fecha,hallazgos,decision,referencias):
    if date.fromisoformat(str(fecha))>datetime.now(ZoneInfo('America/Mexico_City')).date():raise ValueError('Un resultado observado no puede registrarse con fecha futura.')
    if decision not in ('Continuar','Ajustar','Retirar apoyo','Ampliar reto'):raise ValueError('Elige una decisión de seguimiento.')
    if not str(hallazgos).strip() or len(str(hallazgos))>6000:raise ValueError('Describe los resultados observados, hasta 6 000 caracteres.')
    admitidas={f['referencia'] for f in doc['metadatos'].get('fuentes',[]) if f.get('vinculo_verificado') and f.get('tipo') not in ('PLAN','MATERIAL')}
    if not referencias or not set(referencias)<=admitidas:raise ValueError('Relaciona el seguimiento con evidencias disponibles del alumno.')
    result=deepcopy(doc);rows=result['metadatos'].setdefault('seguimiento_formativo',[])
    row={'fecha':str(fecha),'hallazgos':str(hallazgos).strip(),'decision':decision,'referencias':list(dict.fromkeys(referencias))}
    row['origenes']=[{k:f.get(k,'') for k in ('tipo','registro','revision','alumno','fecha')} for f in doc['metadatos']['fuentes'] if f['referencia'] in referencias]
    if row not in rows:rows.append(row)
    result['metadatos'].pop('seguimiento_en_curso',None)
    return result

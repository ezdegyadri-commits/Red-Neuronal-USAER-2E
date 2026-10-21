"""Índice vivo del manual: referencias autorizadas, no copias ni migraciones."""
import json
from datetime import datetime
from services.padron_catalogos import fecha_documental
from utils.escolar import grado_canonico,grupo_canonico
from utils.text import normalizar_texto

SECCIONES={'generales':'Documentos generales','aprendizaje':'Área de aprendizaje','psicologia':'Área de psicología','comunicacion':'Área de comunicación','social':'Área de trabajo social','medica':'Área médica'}

def seccion(tipo,area=''):
    t=normalizar_texto(tipo);a=normalizar_texto(area)
    if any(v in t for v in ('MEDIC','ATENCION MEDICA')):return SECCIONES['medica']
    if any(v in t for v in ('SOCIAL','FAMILIAR')):return SECCIONES['social']
    if 'PSICOLOG' in t or 'PSICOLOG' in a:return SECCIONES['psicologia']
    if 'COMUNICACION' in t or 'LENGUAJE' in t or 'COMUNICACION' in a:return SECCIONES['comunicacion']
    if any(v in t for v in ('PEDAGOG','CURRICULAR','ESTILO DE APRENDIZAJE')) or 'APRENDIZAJE' in a:return SECCIONES['aprendizaje']
    return SECCIONES['generales']

def orden_cronologico(rows):
    def fecha(r):
        valor=r.get('Fecha_Documento') or r.get('Fecha','')
        try:return (fecha_documental(valor).isoformat() if valor else '9999',str(valor)[11:19] if 'T' in str(valor) else '',str(r.get('ID_Documento','')))
        except (ValueError,TypeError):return ('9999','',str(r.get('ID_Documento','')))
    return sorted(rows,key=fecha)


def organizar_archivados(rows,con_epp):
    """El expediente cambia por referencia; el binario/origen nunca se reescribe."""
    from services.archivo_expediente import CONTEXTUAL
    resultado=[]
    for original in rows:
        r=dict(original)
        try:ids=json.loads(r.get('ID_Alumnos_JSON','[]'))
        except (TypeError,ValueError):ids=[]
        if r.get('Ambito')=='grupal' and r.get('Tipo') in CONTEXTUAL and len(ids)==1 and str(ids[0]) in con_epp:
            r.update(Ambito='individual',Ambito_Origen='grupal',Organizacion='Documento específico: EPP iniciada')
        resultado.append(r)
    return orden_cronologico(resultado)

def documentos_vivos(ids,grupal=False):
    from services import archivo_expediente as archivo,planeacion,epp
    from data import repository as repo
    from services.expediente_contexto import ids_contexto
    frame=archivo.visibles().fillna('');ids=set(map(str,ids))
    alumnos={str(r['ID_Alumno']):r for r in frame.to_dict('records')}
    if not ids or not ids<=set(alumnos):raise PermissionError('Expediente fuera de tu asignación.')
    grupos={(str(alumnos[i]['ID_Escuela']),grado_canonico(alumnos[i].get('Grado')),grupo_canonico(alumnos[i].get('Grupo'))) for i in ids}
    if grupal and len(grupos)!=1:raise ValueError('Selecciona una escuela y grupo concreto.')
    resultado=[]
    informes=epp.listar(incluir_bajas=True)
    con_epp={d['alumno'] for d in informes}
    individual=not grupal and len(ids)==1 and bool(ids & con_epp)
    def agregar(tipo,ident,fecha,aid,origen,area='',estado='Registrado'):
        vinculos=set(ids_contexto(frame,str(aid))) if str(aid).startswith('GRUPO-') else {str(aid)}
        if not vinculos or not vinculos & ids:return
        colectivo=str(aid).startswith('GRUPO-')
        if colectivo and (not grupal or not vinculos<=ids):return
        if not colectivo and grupal and str(aid) in con_epp:return
        if not grupal and not individual and tipo not in archivo.INDIVIDUAL:return
        resultado.append({'ID_Documento':'VIVO:'+origen+':'+str(ident),'Tipo':tipo,'Nombre':tipo+' · '+str(ident),
            'Fecha':str(fecha),'Fecha_Documento':str(fecha),'Seccion':seccion(tipo,area),'Origen_Vivo':origen,
            'Estado':estado,'ID_Alumnos_JSON':json.dumps(sorted(vinculos)),'Ambito':'grupal' if grupal else 'individual'})
    # Las fuentes estructuradas ya existen: archivar consiste en relacionarlas,
    # no volver a capturarlas ni generar PDF durante cada consulta.
    fuentes=[('Anexo3_Deteccion','ID_Anexo3','BAP áulico','Anexo III BAP'),
             ('Anexo4_Sugerencias','ID_Anexo4','Sugerencias','Anexo IV Hoja de sugerencias'),
             ('Anexo5_Eventos','ID_Evento','Eventos significativos','Anexo V Eventos significativos'),
             ('Anexo7_Derivacion','ID_Anexo7','Derivación','Anexo VII Derivación')]
    for hoja,col,tipo,origen in fuentes:
        try:datos=repo.read(hoja).fillna('').to_dict('records')
        except Exception as exc:
            if type(exc).__name__=='WorksheetNotFound':continue
            raise
        for r in datos:
            if normalizar_texto(r.get('Estado','')) in ('ANULADO','ELIMINADO','RETIRADO','DUPLICADO'):continue
            aid=r.get('ID_Alumno','')
            if not aid:continue  # Una coincidencia de nombre no es autoridad.
            agregar(tipo,r.get(col,''),r.get('Fecha') or r.get('Fecha_Elaboracion',''),aid,origen,r.get('Sugerencias_Area',''))
    ultimas={d['id']:d for d in planeacion.versiones_actuales()}
    for d in ultimas.values():
        if d['metadatos'].get('borrador_eliminado'):continue
        elegidos={str(a['ID_Alumno']) for a in d['datos']['Alumnos']}
        if not elegidos & ids:continue
        try:planeacion.autorizar(d,incluir_bajas=True)
        except PermissionError:continue
        es_grupal=d['metadatos'].get('modalidad_planeacion')=='grupal'
        if es_grupal!=grupal:continue
        if grupal:
            contexto_doc={(str(d['datos']['ID_Escuela']),grado_canonico(a.get('Grado')),grupo_canonico(a.get('Grupo'))) for a in d['datos']['Alumnos']}
            if contexto_doc!=grupos:continue
        tipo='Planeación grupal' if es_grupal else 'Plan de intervención' if d['formato']=='XXI' else 'Planeación del servicio'
        resultado.append({'ID_Documento':'VIVO:PLAN:'+d['id'],'Tipo':tipo,'Nombre':tipo+' · '+d['datos'].get('Periodo',''),
            'Fecha':d.get('guardado_en',''),'Fecha_Documento':d['datos'].get('Fecha de elaboración') or d.get('guardado_en',''),
            'Seccion':seccion(tipo,d['datos']['Función']),'Origen_Vivo':'Planeación e intervención','Estado':d['estado'],'Ambito':'grupal' if grupal else 'individual'})
    if not grupal:
        for d in informes:
            if d['alumno'] not in ids:continue
            fechas=[p.get('fecha','') for p in d['partes'].values()]
            resultado.append({'ID_Documento':'VIVO:EPP:'+d['id'],'Tipo':'EPP','Nombre':'Informe EPP · '+d['ciclo'],
                'Fecha':max(fechas,default=''),'Seccion':SECCIONES['generales'],'Origen_Vivo':'EPP','Estado':'Informe en proceso','Ambito':'individual'})
    return orden_cronologico(resultado)

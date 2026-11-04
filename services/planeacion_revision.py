"""Pendientes con destino preciso, compartidos por las vistas de planeación."""
from services.planeacion_limpieza import tiene_contenido


def pendientes(doc):
    from services.planeacion import revisar
    faltas=revisar(doc);items=[]
    def agregar(mensaje,target=None,panel='detalle'):
        item={'mensaje':mensaje,'target':target,'panel':panel}
        if item not in items:items.append(item)
    requeridas={'aprendizajes':['Necesidades educativas específicas','Aprendizaje y/u objetivo','Descriptor de logro'],
        'barreras':['Barreras para el Aprendizaje y la Participación','Apoyos y/o ajustes razonables'] if doc['formato']=='XXV' else ['BAP','Acciones para minimizarla o eliminarla','Responsable','Temporalidad'],
        'necesidades':['NEE','Aprendizajes y/u Objetivos','Descriptor de Logro','Apoyos o ajustes','Temporalidad'],
        'curriculo':['NEE','Aprendizajes priorizados y/u objetivos','Descriptor de logro','Temporalidad'],
        'participantes':['Nombre','Función']}
    for falta in faltas:
        if falta.startswith('completar intervención NEE '):
            from services.planeacion_intervenciones_nee import bloques, etiqueta, CAMPOS
            for i,b in enumerate(bloques(doc),1):
                if not falta.startswith('completar intervención NEE '+str(i)+':'):continue
                for campo in CAMPOS:
                    if etiqueta(doc,campo) in falta and not b['campos'].get(campo,'').strip():
                        agregar('Completar '+etiqueta(doc,campo)+' · NEE '+str(i),('intervencion_nee',b['id'],campo))
            continue
        if falta=='capturar el maestro de grupo regular':
            agregar('Capturar el maestro de grupo regular',('maestro_grupo',));continue
        if falta in ('describir qué y cómo se trabaja en Aprendizaje para cada alumno','confirmar NI o RI y la situación inicial de cada alumno'):
            from services.planeacion_modalidad import guia_grupal
            campo='Aprendizaje' if falta.startswith('describir') else 'Situación inicial'
            for i,row in enumerate(guia_grupal(doc)['filas']):
                if not str(row.get(campo,'')).strip():agregar('Completar '+campo+' · '+row['Nombre alumno'],('guia',i,campo))
            continue
        detallada=False
        for tabla,campos in requeridas.items():
            if falta not in ('completar '+tabla,'completar las celdas requeridas de '+tabla):continue
            for i,row in enumerate(doc['tablas'].get(tabla,[])):
                if not tiene_contenido(doc,tabla,row):continue
                for campo in campos:
                    if not str(row.get(campo,'') or '').strip():
                        agregar('Completar '+campo.lower()+' · fila '+str(i+1),('tabla',tabla,i,campo));detallada=True
            if not detallada:
                agregar('Completar '+{'aprendizajes':'necesidades, objetivos y descriptores','barreras':'barreras y apoyos','necesidades':'necesidades y apoyos','curriculo':'apoyos al currículo','participantes':'personas implicadas'}[tabla],panel='tabla:'+tabla);detallada=True
        if detallada:continue
        if falta=='describir actividades, tiempos y recursos':
            for i,row in enumerate(doc['tablas'].get('dosificacion',[])):
                if not tiene_contenido(doc,'dosificacion',row):continue
                for campo in ('Actividades','Fecha' if doc['formato']=='XXV' else 'Temporalidad','Recursos'):
                    if not str(row.get(campo,'') or '').strip():
                        target=('sesion',row['_sesion_equipo'],campo) if row.get('_sesion_equipo') else ('tabla','dosificacion',i,campo)
                        agregar('Completar '+campo.lower()+' · actividad '+str(i+1),target);detallada=True
            if not detallada:agregar('Añadir actividades, tiempos y recursos',panel='tabla:dosificacion')
        elif falta=='describir la evaluación formativa':agregar('Completar la evaluación formativa',('texto','Evaluación'))
        elif falta=='completar el CCT':agregar('Completar el CCT de la escuela',panel='datos')
        else:
            target=None
            for i,c in enumerate(doc['metadatos'].get('equipo',{}).get('competencias',[])):
                if c['Competencia'] not in falta:continue
                campo=next((k for k in ('Necesidad documentada','Descriptor de logro') if not str(c.get(k,'')).strip()),None)
                if campo:target=('competencia',i,campo)
            agregar(falta[:1].upper()+falta[1:].replace('_',' '),target)
    return faltas,items

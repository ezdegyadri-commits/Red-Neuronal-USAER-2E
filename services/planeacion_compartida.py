"""Proyecciones aditivas del Anexo XIX; nunca migra ni reescribe el padrón."""
from copy import deepcopy
from datetime import datetime
from zoneinfo import ZoneInfo
from utils.text import normalizar_texto
from utils.escolar import grado_canonico, grupo_canonico


def es_guia(doc):
    return (doc['datos']['Función']=='Aprendizaje'
            and doc['metadatos'].get('modalidad_planeacion')=='grupal'
            and doc['metadatos'].get('vista_formato')!='trimestral')


def _fecha_corta(fecha_iso):
    if not fecha_iso:
        return ''
    try:
        val = str(fecha_iso)
        if 'T' in val:
            f, h = val.split('T', 1)
            h_corta = h[:8]
            partes = f.split('-')
            if len(partes) == 3:
                return f"{partes[2]}/{partes[1]}/{partes[0]} {h_corta}"
        return val[:16]
    except Exception:
        return str(fecha_iso)[:16]


def etiqueta(doc):
    from services.planeacion_ambito import etiqueta as etiqueta_grupo
    fecha = _fecha_corta(doc.get('guardado_en') or doc['datos'].get('Fecha de elaboración',''))
    return ' · '.join(filter(None, [doc['datos']['Escuela regular'],etiqueta_grupo(doc),
        doc['datos']['Curso escolar'],'T'+str(doc['datos']['Trimestre']),
        fecha,
        doc['datos']['Función'],doc['metadatos'].get('modalidad_planeacion','Por confirmar'),
        str(len(doc['datos']['Alumnos']))+' alumno(s)']))


def etiqueta_selector(doc):
    """La etiqueta de navegación no cambia cuando otra persona guarda."""
    from services.planeacion_ambito import etiqueta as etiqueta_grupo
    return ' · '.join([doc['datos']['Escuela regular'],etiqueta_grupo(doc),
        'Trimestre '+str(doc['datos']['Trimestre']),doc['datos']['Curso escolar']])


def actualizar_lectura(doc,reciente,area):
    """Refresca otras áreas sin mover documento ni aceptar una revisión propia ajena.

    Se conserva el aporte base del área: guardar_aportacion sigue detectando
    conflictos entre dos sesiones del mismo profesional antes de escribir.
    """
    if doc['id']!=reciente['id'] or doc['datos']['ID_Escuela']!=reciente['datos']['ID_Escuela']:
        raise ValueError('La actualización no corresponde a la planeación abierta.')
    nuevo=deepcopy(reciente)
    propio=doc['metadatos'].get('aportaciones_equipo',{}).get(area)
    aportes=nuevo['metadatos'].setdefault('aportaciones_equipo',{})
    if propio is None:aportes.pop(area,None)
    else:aportes[area]=deepcopy(propio)
    return nuevo


def alumno_padron(r):
    from services.planeacion_nee import nee_padron
    return {'ID_Alumno':str(r['ID_Alumno']), 'Nombre del alumno':str(r.get('Nombre_Completo','')),
        'Grado':grado_canonico(r.get('Grado')), 'Grupo':grupo_canonico(r.get('Grupo')),
        'Tipo_Atencion':str(r.get('Tipo_Atencion','') or ''),
        'Condición':str(r.get('Condicion_Discapacidad','') or ''),
        'Maestro de apoyo':str(r.get('Maestra de Apoyo','') or ''),
        'ID_Maestro_Regular':str(r.get('ID_Maestro_Regular','') or ''),
        'Situacion_Alumno':str(r.get('Situacion_Alumno','') or ''),
        'Fecha_Derivacion':str(r.get('Fecha_Derivacion','') or ''),
        'NEE registrada':nee_padron(r),
        'Edad de referencia del padrón':str(r.get('Edad_1_Septiembre','') or '')}


def ampliar_matricula(doc,frame):
    """Matrícula activa autorizada; las bajas y traslados conservan su historial."""
    from services.planeacion_modalidad import modalidad
    from services.planeacion_matricula import clave_escuela
    result=proyectar_retiros(doc,frame)
    if not es_guia(doc):return result
    from services.planeacion_ambito import ambito
    scope=ambito(doc)
    if not scope:return result
    grado,grupo=scope
    modalidades={'grupal'}
    presentes={a['ID_Alumno'] for a in result['datos']['Alumnos']}
    excluidos_manuales=set(map(str,doc.get('metadatos',{}).get('alumnos_excluidos_grupal',[])))
    contexto={}
    for r in frame.to_dict('records'):
        if (str(r.get('ID_Alumno','')) in presentes or modalidad(r) not in modalidades
            or str(r.get('ID_Alumno','')) in excluidos_manuales
            or clave_escuela(r.get('ID_Escuela'))!=clave_escuela(doc['datos']['ID_Escuela'])
            or grado_canonico(r.get('Grado'))!=grado
            or (grupo!='*' and grupo_canonico(r.get('Grupo'))!=grupo)
            or normalizar_texto(r.get('Estatus','')) in {'BAJA','INACTIVO','RETIRADO','ELIMINADO'}):continue
        result['datos']['Alumnos'].append(alumno_padron(r));presentes.add(str(r['ID_Alumno']))
    for r in frame.to_dict('records'):
        if str(r.get('ID_Alumno','')) in presentes and clave_escuela(r.get('ID_Escuela'))==clave_escuela(doc['datos']['ID_Escuela']):
            from services.planeacion_nee import nee_padron
            contexto[str(r['ID_Alumno'])]={'Situacion_Alumno':str(r.get('Situacion_Alumno','') or ''),
                'Fecha_Derivacion':str(r.get('Fecha_Derivacion','') or ''),
                'NEE registrada':nee_padron(r),'ID_Maestro_Regular':str(r.get('ID_Maestro_Regular','') or '')}
    result['metadatos']['contexto_padron_grupo']=contexto
    manual=result['metadatos'].setdefault('guia_grupal_manual',{})
    if not manual.get('maestro_grupo'):
        nombres=list(dict.fromkeys(r['ID_Maestro_Regular'] for r in contexto.values() if r['ID_Maestro_Regular']))
        if nombres:
            manual['maestro_grupo']=', '.join(nombres)
            result['metadatos']['maestro_regular_autocompletado']=manual['maestro_grupo']
    if result['datos']['Alumnos']!=doc['datos']['Alumnos']:
        from services.planeacion_modalidad import guia_grupal
        result['metadatos']['guia_grupal_manual']=guia_grupal(result)
    return result


def lectura_grupal_historica(doc,frame,actor,faltantes):
    """Solo el equipo de origen puede consultar el formato colectivo anterior."""
    if not es_guia(doc):return False
    from services.asignaciones import escuelas_asignadas
    from services.planeacion_matricula import clave_escuela
    from services.padron_movimientos import traslado_confirmado
    from data import repository as repo
    escuela=normalizar_texto(doc['datos']['Escuela regular'])
    asignadas={normalizar_texto(e) for e in escuelas_asignadas(actor['nombre'],actor['rol'])}
    if not actor['director'] and escuela not in asignadas:return False
    if actor['area']=='Aprendizaje' and doc.get('cuenta')!=actor['cuenta']:return False
    try:
        actuales={str(r['ID_Alumno']):r for r in repo.alumnos().fillna('').to_dict('records')}
        return all(aid in actuales and traslado_confirmado(aid,doc['datos']['ID_Escuela'],actuales[aid]['ID_Escuela']) for aid in faltantes)
    except Exception:return False


def proyectar_retiros(doc,frame):
    """Matrícula viva sin perder las filas previas de bajas/traslados.

    Solo retira de la vista activa una baja del mismo plantel o un traslado
    auditado. Los datos se conservan en metadatos y en las versiones anteriores.
    Un alumno ausente sin prueba nunca se retira por inferencia.
    """
    result=proyectar_individuales(doc,frame)
    if not es_guia(doc):return result
    vigentes=set(frame.get('ID_Alumno',[]).astype(str)) if 'ID_Alumno' in frame else set()
    pendientes={str(a['ID_Alumno']) for a in doc['datos']['Alumnos']}-vigentes
    if not pendientes:return result
    from data import repository as repo
    from services.padron_movimientos import traslado_confirmado
    from services.planeacion_matricula import clave_escuela
    try:padron=repo.alumnos().fillna('')
    except Exception:return result
    porid={str(a['ID_Alumno']):a for a in padron.to_dict('records')}
    retiros={}
    for aid in pendientes:
        actual=porid.get(aid)
        if not actual:continue
        mismo=clave_escuela(actual.get('ID_Escuela'))==clave_escuela(doc['datos']['ID_Escuela'])
        if mismo and normalizar_texto(actual.get('Estatus')) in {'BAJA','INACTIVO','RETIRADO','ELIMINADO'}:retiros[aid]='Baja'
        elif not mismo:
            try:
                if traslado_confirmado(aid,doc['datos']['ID_Escuela'],actual.get('ID_Escuela')):retiros[aid]='Traslado'
            except Exception:continue
    if not retiros:return result
    historia=result['metadatos'].setdefault('alumnos_retirados_del_grupo',{})
    manual={str(r['ID_Alumno']):r for r in doc['metadatos'].get('guia_grupal_manual',{}).get('filas',[])}
    for a in doc['datos']['Alumnos']:
        aid=str(a['ID_Alumno'])
        if aid in retiros:
            historia[aid]={'motivo':retiros[aid],'alumno':deepcopy(a),'fila':deepcopy(manual.get(aid,{})),
                'aportaciones':{area:[deepcopy(r) for r in aporte.get('filas',[]) if str(r.get('ID_Alumno'))==aid]
                    for area,aporte in doc['metadatos'].get('aportaciones_equipo',{}).items()}}
    result['datos']['Alumnos']=[a for a in result['datos']['Alumnos'] if str(a['ID_Alumno']) not in retiros]
    return result


def proyectar_individuales(doc,frame):
    """Excluye de la vista XIX, no del historial, la atención individual."""
    result=deepcopy(doc)
    if not es_guia(doc):return result
    from services.planeacion_modalidad import modalidad
    from services.planeacion_matricula import clave_escuela
    actuales={str(r['ID_Alumno']):r for r in frame.to_dict('records')
              if clave_escuela(r.get('ID_Escuela'))==clave_escuela(doc['datos']['ID_Escuela'])}
    excluidos_manuales=set(map(str,doc.get('metadatos',{}).get('alumnos_excluidos_grupal',[])))
    excluidos={str(a['ID_Alumno']) for a in doc['datos']['Alumnos']
               if modalidad(actuales.get(str(a['ID_Alumno']),a))=='individual' or str(a['ID_Alumno']) in excluidos_manuales}
    if not excluidos:return result
    meta=result['metadatos'];historia=meta.setdefault('alumnos_atencion_individual_archivados',{})
    filas={str(r['ID_Alumno']):r for r in meta.get('guia_grupal_manual',{}).get('filas',[])}
    for a in doc['datos']['Alumnos']:
        aid=str(a['ID_Alumno'])
        if aid not in excluidos:continue
        historia[aid]={'alumno':deepcopy(a),'fila':deepcopy(filas.get(aid,{})),
            'aportaciones':{area:[deepcopy(r) for r in aporte.get('filas',[]) if str(r.get('ID_Alumno'))==aid]
                           for area,aporte in meta.get('aportaciones_equipo',{}).items()}}
    result['datos']['Alumnos']=[a for a in doc['datos']['Alumnos'] if str(a['ID_Alumno']) not in excluidos]
    if 'guia_grupal_manual' in meta:meta['guia_grupal_manual']['filas']=[r for r in meta['guia_grupal_manual'].get('filas',[]) if str(r['ID_Alumno']) not in excluidos]
    if 'grupal_zona' in meta:
        for r in meta['grupal_zona']:
            if str(r['ID_Alumno']) in excluidos:historia[str(r['ID_Alumno'])]['grupal_zona']=deepcopy(r)
        meta['grupal_zona']=[r for r in meta['grupal_zona'] if str(r['ID_Alumno']) not in excluidos]
    return result


def situacion_inicial(alumno,fuentes):
    """No interpreta BAPSE como necesidad ni deduce NI/RI a partir de discapacidad."""
    from services.planeacion_nee import nee_padron,es_bapse
    status=normalizar_texto(alumno.get('Situacion_Alumno',''))
    if status not in {'NI','RI'}:return ''
    texto=nee_padron(alumno)
    if not texto:
        # Solo conclusiones estructuradas y verificadas del mismo alumno;
        # nunca interpretar preguntas/frecuencias de BAPSE como hallazgos.
        import json
        for f in fuentes:
            if f.get('tipo')!='EPP' or f.get('parte')!='Conclusión' or not f.get('vinculo_verificado') or es_bapse(f):continue
            if str(f.get('alumno','')).split(',')!=[str(alumno.get('ID_Alumno',''))]:continue
            try:datos=json.loads(f.get('texto',''))
            except (ValueError,TypeError):continue
            filas=datos.get('NEE',[]) if isinstance(datos,dict) else []
            if not isinstance(filas,list):continue
            texto=' '.join(str(r.get('NEE','')).strip() for r in filas if isinstance(r,dict))
            if texto and not es_bapse({'texto':texto}):break
            texto=''
    if texto:
        import re
        texto=re.sub(r'\s+',' ',texto).strip()
        # Una o dos ideas, sin cortar una palabra ni volcar el expediente.
        texto=' '.join(re.split(r'(?<=[.!?])\s+',texto)[:2])
        if len(texto)>230:texto=texto[:227].rsplit(' ',1)[0].rstrip(' ,;:')+'…'
        return status+' · '+texto
    epp=any(f.get('tipo')=='EPP' and f.get('vinculo_verificado') and str(f.get('alumno','')).split(',')==[str(alumno.get('ID_Alumno',''))] and not es_bapse(f) for f in fuentes)
    return status+' · '+('Cuenta con EPP vinculada; revisar los apoyos acordados.' if epp else
        'Nuevo ingreso; revisar la valoración inicial.' if status=='NI' else 'Reingreso; revisar antecedentes y continuidad de apoyos.')


def copia_instrumento(texto):
    """Reconoce copias técnicas antiguas, no prosa docente que debe conservarse."""
    from services.planeacion_nee import es_bapse
    import re
    valor=str(texto or '')
    return es_bapse({'texto':valor}) or bool(re.search(r'[\{\[]\s*[\"\'](?:Item_\d+|NEE|pregunta|Conclusion)[\"\']\s*:',valor,re.I) or
        re.search(r'(?:^|\n)E\d+\s*·\s*\d{4}-\d{2}-\d{2}\s*:',valor))


def junio(doc,ahora=None):
    hoy=ahora or datetime.now(ZoneInfo('America/Mexico_City')).date()
    try:fin=int(doc['datos']['Curso escolar'][:4])+1
    except (ValueError,KeyError):return False
    return (hoy.year,hoy.month)>=(fin,6)


def docente_grupo(doc):
    nombres=list(dict.fromkeys(str(a.get('ID_Maestro_Regular','') or '').strip()
        for a in doc['datos']['Alumnos'] if str(a.get('ID_Maestro_Regular','') or '').strip()))
    return ', '.join(nombres)


def sin_aportes(doc):
    """Huella de trabajo del autor, excluyendo SOLO las columnas de especialistas."""
    d=deepcopy(doc)
    for k in ('revision','anterior','guardado_en','_orden'):d.pop(k,None)
    for k in ('aportaciones_equipo','aportaciones_integradas','guia_aportes_integrados','avisos_integracion','firma_aprobada_por'):
        d['metadatos'].pop(k,None)
    for r in d['metadatos'].get('guia_grupal_manual',{}).get('filas',[]):
        for area in ('Psicología','Comunicación','Trabajo Social'):r.pop(area,None)
    return d


def _tres_vias(base,local,remoto):
    """Une cambios independientes; nunca elige un ganador para la misma celda."""
    if local==base:return deepcopy(remoto)
    if remoto==base or local==remoto:return deepcopy(local)
    if all(isinstance(v,dict) for v in (base,local,remoto)):
        ausente=object();salida={}
        for k in dict.fromkeys([*remoto,*local,*base]):
            b,l,r=(v.get(k,ausente) for v in (base,local,remoto))
            if l is ausente or r is ausente:
                if l==b:elegido=r
                elif r==b or l==r:elegido=l
                else:raise RuntimeError('Dos sesiones cambiaron el mismo campo. Tu texto se conserva; descarga el respaldo antes de recuperar la versión reciente.')
                if elegido is not ausente:salida[k]=deepcopy(elegido)
            elif b is ausente:
                if l!=r:raise RuntimeError('Dos sesiones añadieron valores distintos al mismo campo. Tu texto se conserva; descarga el respaldo para conciliarlos.')
                salida[k]=deepcopy(l)
            else:salida[k]=_tres_vias(b,l,r)
        return salida
    if all(isinstance(v,list) for v in (base,local,remoto)) and all(
        isinstance(r,dict) and r.get('ID_Alumno') for v in (base,local,remoto) for r in v):
        if all(len({r['ID_Alumno'] for r in v})==len(v) for v in (base,local,remoto)):
            unidos=_tres_vias(*({r['ID_Alumno']:r for r in v} for v in (base,local,remoto)))
            return list(unidos.values())
    raise RuntimeError('Dos sesiones modificaron el mismo campo. Tu edición se conserva; descarga el respaldo antes de recuperar la versión reciente.')


def conciliar_autor(doc,base,latest):
    if not es_guia(doc):
        raise RuntimeError('Otra sesión modificó la planeación. Tu edición se conserva; recupera la versión reciente antes de conciliar.')
    if any(base.get(k)!=latest.get(k) for k in ('id','cuenta','formato','estado')):
        raise RuntimeError('Cambió el estado de revisión o la identidad del documento. Conserva tu respaldo y abre la versión reciente antes de continuar.')
    result=_tres_vias(sin_aportes(base),sin_aportes(doc),sin_aportes(latest))
    for k in ('aportaciones_equipo','aportaciones_integradas','guia_aportes_integrados'):
        result['metadatos'][k]=deepcopy(latest['metadatos'].get(k,{}))
    # Las columnas ajenas siempre proceden de la versión reciente, no del editor del autor.
    recientes={r['ID_Alumno']:r for r in latest['metadatos'].get('guia_grupal_manual',{}).get('filas',[])}
    for r in result['metadatos'].get('guia_grupal_manual',{}).get('filas',[]):
        for area in ('Psicología','Comunicación','Trabajo Social'):
            r[area]=recientes.get(r['ID_Alumno'],{}).get(area,'')
    result['revision']=latest['revision']
    return result


def actualizar_aportes_autor(doc,latest):
    """Proyección de lectura; no adelanta la revisión base ni toca texto de apoyo."""
    if doc['id']!=latest['id']:raise ValueError('Documento distinto.')
    result=deepcopy(doc)
    for k in ('aportaciones_equipo','aportaciones_integradas','guia_aportes_integrados'):
        result['metadatos'][k]=deepcopy(latest['metadatos'].get(k,{}))
    recientes={r['ID_Alumno']:r for r in latest['metadatos'].get('guia_grupal_manual',{}).get('filas',[])}
    for r in result['metadatos'].get('guia_grupal_manual',{}).get('filas',[]):
        for area in ('Psicología','Comunicación','Trabajo Social'):
            if area in recientes.get(r['ID_Alumno'],{}):r[area]=recientes[r['ID_Alumno']][area]
    return result


def excluir_alumno_grupal(doc,aid,frame=None):
    """Excluye un alumno del Anexo XIX grupal para atenderlo individualmente."""
    meta=doc.setdefault('metadatos',{})
    excluidos=meta.setdefault('alumnos_excluidos_grupal',[])
    aid_str=str(aid)
    if aid_str not in excluidos:excluidos.append(aid_str)
    if frame is None:
        from services import planeacion as s
        try:frame=s.padron_autorizado()
        except Exception:pass
    if frame is not None:
        doc=proyectar_individuales(doc,frame)
    else:
        doc['datos']['Alumnos']=[a for a in doc['datos']['Alumnos'] if str(a['ID_Alumno'])!=aid_str]
    from services.planeacion_modalidad import guia_grupal
    meta['guia_grupal_manual']=guia_grupal(doc)
    return doc


def restaurar_alumno_grupal(doc,aid,frame=None):
    """Reincorpora a la planeación grupal un alumno previamente excluido."""
    meta=doc.setdefault('metadatos',{})
    excluidos=meta.get('alumnos_excluidos_grupal',[])
    aid_str=str(aid)
    if aid_str in excluidos:excluidos.remove(aid_str)
    if frame is None:
        from services import planeacion as s
        try:frame=s.padron_autorizado()
        except Exception:pass
    if frame is not None:
        doc=ampliar_matricula(doc,frame)
    from services.planeacion_modalidad import guia_grupal
    meta['guia_grupal_manual']=guia_grupal(doc)
    return doc

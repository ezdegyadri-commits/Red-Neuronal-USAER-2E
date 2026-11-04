"""Recuperación visible, sin reescribir ni fusionar documentos guardados."""
from services.planeacion_matricula import clave_escuela
from copy import deepcopy


def clasificar_heredada(doc,padron):
    """Proyección de lectura: recupera individuales antiguas sin otra copia.

    Se ejecuta después de autorizar. No infiere por nombres ni convierte
    planes ambiguos en guías grupales; el historial permanece idéntico.
    """
    if doc.get('metadatos',{}).get('modalidad_planeacion'):return doc
    alumnos=doc.get('datos',{}).get('Alumnos',[])
    ids=[str(a.get('ID_Alumno','')).strip() for a in alumnos]
    if not ids or not all(ids) or len(ids)!=len(set(ids)) or 'ID_Alumno' not in padron:return doc
    rows=padron.loc[padron['ID_Alumno'].astype(str).str.strip().isin(ids)]
    if len(rows)!=len(ids) or set(rows['ID_Alumno'].astype(str).str.strip())!=set(ids):return doc
    from services.planeacion_modalidad import modalidad
    if any(clave_escuela(r.get('ID_Escuela'))!=clave_escuela(doc['datos'].get('ID_Escuela'))
           or modalidad(r)!='individual' for r in rows.to_dict('records')):return doc
    copia=deepcopy(doc)
    copia.setdefault('metadatos',{})['modalidad_planeacion']='individual'
    copia['metadatos']['origen_modalidad']='Planeación anterior sin clasificación; atención individual verificada en el padrón autorizado.'
    return copia


def actividades_redactadas(doc):
    return sum(bool(str(r.get('Actividades','') or '').strip()) for r in doc.get('tablas',{}).get('dosificacion',[]))


def tiene_trabajo(doc):
    if actividades_redactadas(doc):return True
    meta=doc.get('metadatos',{})
    if meta.get('modalidad_planeacion')!='grupal':return False
    from services.planeacion_modalidad import guia_grupal
    return any(str(r.get(area,'') or '').strip() for r in guia_grupal(doc)['filas']
               for area in ('Aprendizaje','Psicología','Comunicación','Trabajo Social'))


def ordenar(docs):
    # Una plantilla recién creada no desplaza al documento donde se escribió.
    # No se compara longitud como si más texto significara mejor planeación.
    return sorted(docs,key=lambda d:(tiene_trabajo(d),d.get('guardado_en','')),reverse=True)


def repositorios(docs):
    """Clasificación visual, no copias ni escrituras ni inferencias por alumno."""
    grupos={'Individuales':[],'Grupales':[]}
    for doc in ordenar(docs):
        tipo=doc.get('metadatos',{}).get('modalidad_planeacion')
        nombre={'individual':'Individuales','grupal':'Grupales','especialista':'Mi intervención'}.get(tipo,'Otros formatos guardados')
        grupos.setdefault(nombre,[]).append(doc)
    return grupos


def titulo_tarjeta(doc):
    from services.planeacion_ambito import etiqueta as grupo
    tipo=doc.get('metadatos',{}).get('modalidad_planeacion')
    if tipo=='individual' or not tipo and len(doc['datos']['Alumnos'])==1:
        return ' · '.join(a['Nombre del alumno'] for a in doc['datos']['Alumnos']) or 'Planeación individual'
    return grupo(doc) or 'Planeación guardada'


def detalle_tarjeta(doc):
    from services.planeacion_compartida import _fecha_corta
    datos=doc['datos'];n=actividades_redactadas(doc)
    estado={'BORRADOR':'Borrador editable','ENVIADO':'Enviado a Dirección','VALIDADO':'Validado','CON_OBSERVACIONES':'Con observaciones'}.get(doc.get('estado'),doc.get('estado',''))
    return ' · '.join(filter(None,[datos.get('Escuela regular'),datos.get('Curso escolar'),
        ('Anual' if doc['metadatos'].get('periodicidad')=='anual' else 'Trimestre '+str(datos.get('Trimestre',''))), _fecha_corta(doc.get('guardado_en')),
        datos.get('Función'),estado,str(n)+' actividades redactadas' if n else 'Con trabajo redactado' if tiene_trabajo(doc) else 'Sin actividades redactadas']))


def etiqueta(doc):
    from services.planeacion_compartida import etiqueta as original
    texto=original(doc)
    if doc.get('metadatos',{}).get('modalidad_planeacion')=='individual':
        texto+=' · '+', '.join(a['Nombre del alumno'] for a in doc['datos']['Alumnos'])
    n=actividades_redactadas(doc)
    estado={'BORRADOR':'Borrador editable','ENVIADA':'Enviada','VALIDADA':'Validada'}.get(doc.get('estado'),doc.get('estado',''))
    return texto+' · '+estado+(' · '+str(n)+' actividad(es) redactada(s)' if n else ' · Sin actividades redactadas')


def equivalentes(docs,actor,formato,ids,escuela,ciclo,trimestre,modalidad):
    """Coincidencia exacta y misma autoría; no une escuelas, alumnos ni periodos."""
    alumnos=set(map(str,ids));resultado=[]
    if not alumnos:return []
    for doc in docs:
        datos=doc['datos'];meta=doc.get('metadatos',{})
        if (doc.get('cuenta')!=actor['cuenta'] or doc.get('formato')!=formato
            or datos.get('Función')!=actor['area'] or meta.get('borrador_eliminado')
            or doc.get('estado')!='BORRADOR' or meta.get('modalidad_planeacion')!=modalidad
            or clave_escuela(datos.get('ID_Escuela'))!=clave_escuela(escuela)
            or str(datos.get('Curso escolar','')).replace('–','-')!=str(ciclo)+'-'+str(int(ciclo)+1)
            or str(datos.get('Trimestre'))!=str(trimestre)
            or {str(a['ID_Alumno']) for a in datos['Alumnos']}!=alumnos):continue
        resultado.append(doc)
    return ordenar(resultado)

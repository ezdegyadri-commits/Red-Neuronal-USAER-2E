"""Panel de trabajo y revisión. Claves de sesión separadas por cuenta."""
from copy import deepcopy
import hashlib
import inspect
import json
import re
import time
import pandas as pd
import streamlit as st
from services import planeacion as servicio
from services.planeacion_modelo import FORMATOS, revisar_redaccion
from ai.planeacion import proponer, modelo_configurado
from ai.planeacion_prompt import huella, VERSION_PROMPT
from documents.planeacion import generar_pdf
from services.curriculo import CAMPOS, EJES, FUENTES_BASE, opciones, vincular, contexto_ia, catalogo
from services.materiales_planeacion import TIPOS, MAX_TEXTO, leer_material, incorporar, fuentes_materiales


def _resumen_complementos(current):
    base=re.split(r'\n\n(?:MATERIALES|ADAPTACIONES|COMPLEMENTOS) REVISADOS:\n',current['metadatos'].get('resumen_educativo',''),maxsplit=1)[0]
    complementos=[{**m,'texto':m['texto'][:600]} for m in fuentes_materiales(current)]
    complementos.extend({'referencia':'ADAPTACIÓN-'+i,'alcance':'redacción docente, no texto oficial ni resultado',
                         'texto':'Contenido: '+a.get('contenido','')[:150]+'\nObjetivo adaptado: '+a.get('pda','')[:400]}
                        for i,a in current['metadatos'].get('curriculo',{}).get('adaptaciones',{}).items())
    resumen=servicio.resumen_previo(current,complementos) if complementos else ''
    current['metadatos']['resumen_educativo']=base[:5500]+('\n\nCOMPLEMENTOS REVISADOS:\n'+resumen[:6200] if resumen else '')
    return current


def _actualizar_materiales(prefix,current):
    """Conserva el resumen docente y sustituye solo la sección de materiales."""
    fuentes=[f for f in current['metadatos'].get('fuentes',[]) if f.get('tipo')!='MATERIAL']
    materiales=fuentes_materiales(current)
    current['metadatos']['fuentes']=fuentes+materiales
    current=_resumen_complementos(current)
    _open(prefix,current);_persist(prefix);st.rerun()


def _materiales(prefix,doc):
    with st.expander('Añadir documentos o imágenes a mi planeación'):
        st.caption('Hasta 32 MB por archivo y PDF de hasta 1 000 páginas. Lectura local, sin enviar originales a IA. Puedes elegir páginas; hasta diez páginas escaneadas por lectura y 100 000 caracteres de transcripción. Incorpora solo el texto pertinente a esta planeación.')
        limite={'max_upload_size':32} if 'max_upload_size' in inspect.signature(st.file_uploader).parameters else {}
        archivos=st.file_uploader('Materiales de apoyo',type=TIPOS,accept_multiple_files=True,key=prefix+'_material_upload',**limite)
        desde,hasta=1,0
        if archivos and any(a.name.lower().endswith(('.pdf','.tif','.tiff')) for a in archivos):
            col1,col2=st.columns(2)
            desde=col1.number_input('Leer desde la página',min_value=1,max_value=1000,value=1,key=prefix+'_material_from')
            hasta=col2.number_input('Hasta la página (0: todas)',min_value=0,max_value=1000,value=0,key=prefix+'_material_to')
            st.caption('El intervalo se aplica a los PDF e imágenes multipágina. Cambia las páginas y vuelve a transcribir para continuar un documento largo.')
        def clave_lectura(a):
            intervalo=f':{desde}:{hasta}' if a.name.lower().endswith(('.pdf','.tif','.tiff')) else ''
            return hashlib.sha256(a.getvalue()+intervalo.encode()).hexdigest()
        if archivos and st.button('Transcribir archivos',key=prefix+'_material_read'):
            leidos=st.session_state.setdefault(prefix+'_material_readings',{})
            for archivo in archivos:
                digest=clave_lectura(archivo)
                if digest in leidos:continue
                try:
                    with st.spinner('Leyendo '+archivo.name+'…'):
                        multipagina=archivo.name.lower().endswith(('.pdf','.tif','.tiff'))
                        leidos[digest]=leer_material(archivo.name,archivo.getvalue(),desde if multipagina else 1,(hasta or None) if multipagina else None)
                        if multipagina:
                            leidos[digest]['id']=digest
                            leidos[digest]['nombre']+=f' · páginas {desde}–{hasta or "final"}'
                except Exception as exc:
                    st.warning(archivo.name+': '+(str(exc) if isinstance(exc,ValueError) else 'No se pudo transcribir. Usa una copia más clara o un PDF con texto.'))
        presentes={clave_lectura(a) for a in archivos or []}
        for digest,material in st.session_state.get(prefix+'_material_readings',{}).items():
            if digest not in presentes:continue
            with st.expander('Revisar lectura · '+material['nombre'],expanded=True):
                for aviso in material['avisos']:st.caption(aviso)
                texto=st.text_area('Texto útil para esta planeación: corrige o selecciona lo pertinente',value=material['texto'],max_chars=MAX_TEXTO,height=200,key=prefix+'_material_text_'+digest)
                st.caption('El material se vincula solo a esta planeación. Confirma qué información corresponde al alumno o al grupo. Para IA se preparan extractos que revisarás en el resumen educativo.')
                revisado=st.checkbox('Revisé el texto y su pertinencia',key=prefix+'_material_review_'+digest)
                if st.button('Incorporar texto revisado',disabled=not revisado or not texto.strip(),key=prefix+'_material_apply_'+digest):
                    try:_actualizar_materiales(prefix,incorporar(st.session_state[prefix+'_doc'],material,texto))
                    except ValueError as exc:st.info(str(exc))
        for material in doc['metadatos'].get('materiales',[]):
            with st.expander('Material incorporado · '+material['nombre']):
                texto=st.text_area('Editar material incorporado',value=material['texto'],max_chars=MAX_TEXTO,height=180,key=f"{prefix}_{st.session_state.get(prefix+'_generation',0)}_saved_material_{material['id']}")
                if st.button('Guardar cambios del material',key=prefix+'_material_update_'+material['id']):
                    try:_actualizar_materiales(prefix,incorporar(st.session_state[prefix+'_doc'],material,texto))
                    except ValueError as exc:st.info(str(exc))


def _curriculo(prefix,doc):
    generation=st.session_state.get(prefix+'_generation',0)
    key=f'{prefix}_{generation}_curriculum'
    seleccion=doc['metadatos'].get('curriculo',{})
    with st.expander('Campos, ejes y referentes oficiales',expanded=not bool(seleccion)):
        st.caption('Puedes trabajar contenidos de otro grado según las necesidades del alumno. Su grado escolar no cambia; el texto oficial y tu adaptación se conservan por separado.')
        campos=list(CAMPOS)
        campo=st.selectbox('Campo formativo',campos,index=campos.index(seleccion['campo']) if seleccion.get('campo') in campos else None,placeholder='Elige el campo que trabajarás',key=key+'_campo')
        ejes=st.multiselect('Ejes articuladores pertinentes',list(EJES),default=seleccion.get('ejes',['Inclusión']),key=key+'_ejes')
        if campo:
            st.caption(CAMPOS[campo]);rows=opciones(doc,campo);by_id={r['id']:r for r in rows}
            grado=st.selectbox('Explorar referentes de', ['Todos los grados',1,2,3,4,5,6],format_func=lambda g:g if isinstance(g,str) else f'{g}° de primaria',key=key+'_grado')
            query=st.text_input('Encontrar contenidos por palabra: lectura, números, convivencia…',key=key+'_query')
            visibles=[r for r in rows if grado=='Todos los grados' or r['grado']==grado]
            if query:
                from utils.text import normalizar_texto
                tokens=normalizar_texto(query).split()
                filtradas=[r for r in visibles if all(t in normalizar_texto(r['contenido']+' '+r['pda']) for t in tokens)]
            else:filtradas=visibles
            anteriores=[r['id'] for r in seleccion.get('registros',[]) if r['id'] in by_id]
            selector_key=key+'_ids_'+campo
            elegidos=[i for i in st.session_state.get(selector_key,anteriores) if i in by_id]
            opciones_ids=list(dict.fromkeys([r['id'] for r in filtradas]+elegidos+anteriores))
            ids=st.multiselect('Contenido y PDA por grado (hasta seis referentes)',opciones_ids,default=elegidos,format_func=lambda i:f"{by_id[i]['grado']}° · {by_id[i]['contenido']} · p. {by_id[i]['pagina_pdf']}",max_selections=6,key=selector_key)
            adaptaciones={}
            for i in ids:
                r=by_id[i];source=next(s for s in catalogo()['fuentes'] if s['id']==r['fuente'])
                with st.expander(f"PDA de {r['grado']}° · {r['contenido']}"):
                    st.write(r['pda']);st.caption('Extracto de la tabla oficial; consulta la página para verificar su continuidad.')
                    st.link_button(f"SEP · Fase {r['fase']} · página PDF {r['pagina_pdf']}",source['url']+'#page='+str(r['pagina_pdf']))
                    ajuste=seleccion.get('adaptaciones',{}).get(i,{})
                    adaptaciones[i]={
                        'contenido':st.text_area('Contenido para mi planeación',value=ajuste.get('contenido',r['contenido']),key=key+'_contenido_'+i),
                        'pda':st.text_area('PDA adaptado / objetivo de trabajo',value=ajuste.get('pda',r['pda']),key=key+'_pda_'+i)}
                    st.caption('Tu redacción es editable y se imprime como adaptación docente, no como cita oficial.')
            local=st.text_area('Contextualización: programa analítico de la escuela, lengua y entorno de la comunidad',value=seleccion.get('contexto_local',''),key=key+'_local')
            st.caption('No se presume que el programa analítico de cada escuela ya esté cargado. Aquí puedes añadir su referencia y los acuerdos pertinentes.')
            if st.button('Incorporar referentes al borrador',key=key+'_save'):
                updated=vincular(st.session_state[prefix+'_doc'],campo,ejes,ids,local,adaptaciones)
                if local:
                    local_resumen=servicio.resumen_previo(updated,[{'referencia':'CONTEXTO-ESCOLAR','alcance':'contextualización declarada; confirmar con el programa analítico','texto':local}])
                    previous=updated['metadatos'].get('resumen_educativo','')
                    updated['metadatos']['resumen_educativo']=previous[:8000]+'\n\n'+local_resumen[:3500]
                updated=_resumen_complementos(updated)
                _open(prefix,updated);_persist(prefix);st.rerun()
        for source in FUENTES_BASE:st.link_button(source['organismo']+' · '+source['titulo'],source['url'])


def _preview(prefix,pdf):
    import pymupdf
    with pymupdf.open(stream=pdf,filetype='pdf') as pages:
        st.subheader('Vista previa del formato para imprimir')
        total=len(pages)
        page=st.selectbox('Página del documento',range(total),format_func=lambda i,n=total:f'{i+1} de {n}',key=prefix+'_preview_page')
        pixmap=pages[page].get_pixmap(matrix=pymupdf.Matrix(1.6,1.6))
        st.image(pixmap.tobytes('png'),use_container_width=True)
    st.caption('Para corregir, modifica los campos anteriores y prepara de nuevo el PDF. Para imprimir, descarga el archivo y usa la opción Imprimir de tu lector PDF.')


def _prefix():
    return 'planeacion_'+hashlib.sha256(servicio.identidad()['cuenta'].encode()).hexdigest()[:12]


def _persist(prefix,estado='BORRADOR',automatic=False):
    doc=st.session_state[prefix+'_doc']
    st.session_state[prefix+'_pending']=True
    if automatic and time.monotonic()-st.session_state.get(prefix+'_last_attempt',0)<15:
        return False
    st.session_state[prefix+'_last_attempt']=time.monotonic()
    try:
        saved=servicio.guardar(doc,estado)
        st.session_state[prefix+'_doc']=saved
        st.session_state.pop(prefix+'_error',None)
        st.session_state.pop(prefix+'_pdf',None)
        st.session_state[prefix+'_pending']=False
        return True
    except Exception as exc:
        st.session_state[prefix+'_error']=str(exc) if isinstance(exc,(ValueError,PermissionError,RuntimeError)) else 'No se confirmó el guardado. Conserva el respaldo y vuelve a intentar.'
        return False


def _field(prefix,key,section,field):
    doc=deepcopy(st.session_state[prefix+'_doc'])
    doc[section][field]=st.session_state[key]
    st.session_state[prefix+'_doc']=doc
    st.session_state.pop(prefix+'_pdf',None)
    if section=='metadatos' and field=='resumen_educativo':
        st.session_state.pop(prefix+'_ia',None)
        consent_key=f'{prefix}_{st.session_state.get(prefix+"_generation",0)}_consent'
        if consent_key in st.session_state:st.session_state[consent_key]=False
    _persist(prefix,automatic=True)


def _table(prefix,key,name,base):
    patch=st.session_state.get(key,{})
    rows=deepcopy(base)
    for i,values in patch.get('edited_rows',{}).items():
        if int(i)<len(rows): rows[int(i)].update(values)
    deleted=set(patch.get('deleted_rows',[]))
    rows=[r for i,r in enumerate(rows) if i not in deleted]
    rows.extend(patch.get('added_rows',[]))
    headers=FORMATOS[st.session_state[prefix+'_doc']['formato']]['tablas'][name]
    rows=[{h:str(r.get(h,'') or '') for h in headers} for r in rows]
    doc=deepcopy(st.session_state[prefix+'_doc'])
    generadas=[r for r in doc['tablas'][name] if r.get('_sesion_equipo')]
    doc['tablas'][name]=rows+generadas
    st.session_state[prefix+'_doc']=doc
    st.session_state.pop(prefix+'_pdf',None)
    _persist(prefix,automatic=True)


def _open(prefix,doc):
    st.session_state[prefix+'_doc']=deepcopy(doc)
    st.session_state[prefix+'_generation']=st.session_state.get(prefix+'_generation',0)+1
    for suffix in ('_error','_pdf','_fuentes','_ia'):
        st.session_state.pop(prefix+suffix,None)
    st.session_state[prefix+'_pending']=False


@st.fragment(run_every=15)
def _autosave(prefix):
    if st.session_state.get(prefix+'_pending'):
        _persist(prefix,automatic=True)
    current=st.session_state[prefix+'_doc']
    if prefix+'_error' in st.session_state:st.warning(st.session_state[prefix+'_error'])
    elif st.session_state.get(prefix+'_pending'):st.caption('Cambios pendientes de autoguardado. Usa Guardar borrador antes de cerrar.')
    elif current.get('guardado_en'):st.caption('Guardado confirmado: '+current['guardado_en'][:19]+' · '+current['estado'])
    else:st.warning('Este borrador aún no tiene un guardado confirmado.')


def _text(prefix,section,field,label=None):
    doc=st.session_state[prefix+'_doc']
    key=f'{prefix}_{st.session_state.get(prefix+"_generation",0)}_{section}_{field}'
    st.text_area(label or field,value=str(doc[section].get(field,'') or ''),key=key,
                 on_change=_field,args=(prefix,key,section,field))


def _ai(prefix,doc,revision=False):
    modelo = modelo_configurado()
    st.caption('La IA se usa solo cuando solicitas propuestas. El expediente y los datos del formato se preparan automáticamente.')
    _text(prefix,'metadatos','resumen_educativo','Resumen educativo sin nombres, CURP, contactos ni identificadores')
    current=st.session_state[prefix+'_doc']
    resumen=current['metadatos'].get('resumen_educativo','')
    contexto=contexto_ia(current)
    try:
        firma=huella(resumen,current['formato'],current['datos']['Función'],revision,contexto) if resumen.strip() else ''
    except ValueError as exc:
        firma=''
        st.info(str(exc))
    record=(st.session_state.get(prefix+'_revision_ia_guardada',{}) if revision
            else current['metadatos'].get('propuestas_ia_guardadas',{}))
    coinciden=bool(firma and record.get('huella')==firma and record.get('motor')==modelo)
    if coinciden:
        st.session_state[prefix+'_ia']=record['resultado']
        st.caption('Estas propuestas ya están guardadas. Consultarlas y editar tu planeación no genera otra solicitud de IA.')
    else:
        st.session_state.pop(prefix+'_ia',None)
    approved=st.checkbox('Revisé el resumen: no contiene datos que identifiquen a las personas.',key=f'{prefix}_{st.session_state.get(prefix+"_generation",0)}_consent')
    label=('Revisar nuevamente con IA' if revision else 'Generar nuevas propuestas con IA') if coinciden else ('Revisar con IA' if revision else 'Proponer actividades con IA')
    if st.button(label,disabled=not approved or not firma,key=prefix+'_ai_button'):
        try:
            with st.spinner('Preparando propuestas…'):
                result=proponer(resumen,current['formato'],current['datos']['Función'],revision,curriculo=contexto)
                st.session_state[prefix+'_ia']=result
                guardado={'huella':firma,'motor':modelo,'version_prompt':VERSION_PROMPT,'resultado':result}
                if revision:
                    st.session_state[prefix+'_revision_ia_guardada']=guardado
                else:
                    current=deepcopy(st.session_state[prefix+'_doc'])
                    current['metadatos']['propuestas_ia_guardadas']=guardado
                    st.session_state[prefix+'_doc']=current
                    _persist(prefix,automatic=True)
        except (ValueError,RuntimeError) as exc:
            st.info(str(exc))
    diagnostico=st.session_state.get('planeacion_ia_diagnostico')
    if diagnostico:
        with st.expander('Diagnóstico de la última solicitud de IA'):
            st.caption('Puedes compartir este código con Dirección. No incluye datos del alumno ni la clave de conexión.')
            st.write('Motor: '+diagnostico['motor'])
            st.write('Código: '+str(diagnostico['codigo'] or 'No disponible'))
            st.write('Tipo de incidencia: '+diagnostico['tipo'])
    result=st.session_state.get(prefix+'_ia')
    if not result:return
    st.write(result['observaciones'])
    for missing in result['faltantes']:st.caption(missing)
    for i,proposal in enumerate(result['propuestas']):
        with st.expander(proposal['objetivo'] or f'Propuesta {i+1}'):
            for field,label in [('necesidad','Necesidad documentada a confirmar'),('descriptor','Cómo reconocer el avance'),('actividad','Actividad sugerida'),('contexto','Dónde'),('temporalidad','Cuándo'),('recursos','Con qué apoyos'),('evaluacion','Cómo dar seguimiento'),('fundamento','Fundamento curricular y local')]:
                if proposal.get(field):st.write(label+': '+proposal[field])
            if proposal.get('fuentes'):st.caption('Fuentes verificadas: '+', '.join(proposal['fuentes']))
            incluida=proposal in st.session_state[prefix+'_doc']['metadatos'].get('Propuestas IA revisadas',[])
            if not revision and st.button('Ya añadida al borrador' if incluida else 'Añadir al borrador',disabled=incluida,key=prefix+'_apply_'+str(i)):
                current=deepcopy(st.session_state[prefix+'_doc']);tables=current['tablas'];fmt=current['formato']
                if fmt=='XXIII':
                    tables['aprendizajes'].append({'Necesidades educativas específicas':proposal['necesidad'],'Aprendizaje y/u objetivo':proposal['objetivo'],'Descriptor de logro':proposal['descriptor']})
                elif fmt=='XXV':
                    tables['barreras'].append({'Barreras para el Aprendizaje y la Participación':proposal['necesidad'],'Apoyos y/o ajustes razonables':proposal['actividad']})
                else:
                    tables['necesidades'].append({'NEE':proposal['necesidad'],'Aprendizajes y/u Objetivos':proposal['objetivo'],'Descriptor de Logro':proposal['descriptor'],'Apoyos o ajustes':proposal['actividad'],'Temporalidad':proposal['temporalidad'],'Seguimiento':proposal['evaluacion']})
                if fmt!='XXI':
                    tables['dosificacion'].append({'Contextos':proposal['contexto'],'Actividades':proposal['actividad'],'Temporalidad' if fmt=='XXIII' else 'Fecha':proposal['temporalidad'],'Recursos':proposal['recursos']})
                current['metadatos'].setdefault('Propuestas IA revisadas',[]).append(proposal)
                _open(prefix,current);_persist(prefix);st.rerun()


def _editor(prefix):
    doc=st.session_state[prefix+'_doc']; servicio.autorizar(doc,True)
    if doc['metadatos'].get('version_contexto')!=servicio.VERSION_CONTEXTO:
        doc=servicio.preparar_contexto(doc)
        _open(prefix,doc)
        st.session_state[prefix+'_pending']=True
    st.subheader(FORMATOS[doc['formato']]['titulo'])
    st.write(doc['datos']['Escuela regular']+' · '+doc['datos'].get('CCT',''))
    if doc['metadatos'].get('aviso_contexto'):st.caption(doc['metadatos']['aviso_contexto'])
    if not doc['datos'].get('CCT'):_text(prefix,'datos','CCT','CCT no registrado: verifica y completa')
    alumnos_col,fuentes_col,estado_col=st.columns(3)
    alumnos_col.metric('Alumnos seleccionados',len(doc['datos']['Alumnos']))
    fuentes_col.metric('Evidencias recuperadas',len(doc['metadatos'].get('fuentes',[])))
    estado_col.metric('Tu trabajo',{'BORRADOR':'Borrador','ENVIADO':'Enviado','VALIDADO':'Revisado','CON_OBSERVACIONES':'Por ajustar'}.get(doc['estado'],doc['estado']))
    with st.expander('Datos precargados de los alumnos'):
        st.dataframe(pd.DataFrame(doc['datos']['Alumnos']),hide_index=True,use_container_width=True)
    st.caption('Autoguardado de cambios confirmados cada 15 segundos mientras trabajas. Antes de cerrar, pulsa Guardar borrador y confirma el guardado.')
    conocer,planear,revisar=st.tabs(['1. Conocer y elegir','2. Preparar actividades','3. Revisar y compartir'])
    with conocer:
        st.caption('Revisa el expediente, elige qué aprendizaje trabajarás y añade materiales solo si los necesitas. Los datos del alumno ya están completos cuando existen en el padrón.')
        st.markdown('#### Referentes y materiales para trabajar')
        _materiales(prefix,doc)
        _curriculo(prefix,doc)
        if doc.get('observaciones_director'):st.info('Dirección: '+doc['observaciones_director'])
        with st.expander('Evidencias del expediente y referente curricular'):
            if st.button('Actualizar información del expediente',key=prefix+'_sources'):
                current=servicio.preparar_contexto(st.session_state[prefix+'_doc'])
                st.session_state[prefix+'_doc']=current
                st.session_state[prefix+'_fuentes']=(current['metadatos']['fuentes'],current['metadatos']['fuentes_pendientes'])
                _persist(prefix)
            if prefix+'_fuentes' not in st.session_state and doc['metadatos'].get('contexto_cargado'):
                st.session_state[prefix+'_fuentes']=(doc['metadatos'].get('fuentes',[]),doc['metadatos'].get('fuentes_pendientes',[]))
            if prefix+'_fuentes' in st.session_state:
                sources,failed=st.session_state[prefix+'_fuentes']
                if failed:st.info('Parte de la evidencia no está disponible. Puedes continuar sin modificar esos registros.')
                for source in sources:
                    with st.expander(source['referencia']+' · '+source['tipo']+' · '+source['fecha']+' · '+source['alcance']):
                        st.write(source['texto'])
                if not sources:st.caption('No hay evidencia vinculada disponible. No se inferirán necesidades o resultados.')
                elif st.button('Preparar resumen educativo para revisar',key=prefix+'_summary'):
                    current=deepcopy(st.session_state[prefix+'_doc'])
                    current['metadatos']['resumen_educativo']=servicio.resumen_previo(current,sources)
                    _open(prefix,current);_persist(prefix);st.rerun()
                st.caption('El resumen se prepara localmente. Revisa posibles nombres o datos sensibles restantes antes de solicitar IA.')
            _text(prefix,'metadatos','necesidades_confirmadas','Necesidades y apoyos documentados (incluye la referencia de origen)')
            _text(prefix,'metadatos','referente_curricular','Campo formativo, fase, contenido y PDA verificado; referencia del programa')
            st.caption('Plan de Estudio 2022, edición 2025. El plan general no sustituye el catálogo de contenidos y PDA de cada fase.')
        if doc['formato']=='XXI':
            _text(prefix,'metadatos','fuente_iepp','Referencia del IEPP: fecha, folio o ubicación del informe')
            key=prefix+'_iepp_'+str(st.session_state.get(prefix+'_generation',0))
            st.checkbox('Las NEE fueron confirmadas en el IEPP.',value=bool(doc['metadatos'].get('NEE confirmadas desde IEPP')),key=key,on_change=_field,args=(prefix,key,'metadatos','NEE confirmadas desde IEPP'))
            for field in ('Necesidades educativas específicas asociadas a','Maestro de grupo','Vigencia en cursos escolares'):
                _text(prefix,'datos',field)
    with planear:
        from ui.planeacion_equipo import panel as panel_equipo
        panel_equipo(prefix,st.session_state[prefix+'_doc'],_persist,_open)
        st.caption('Empieza por una actividad posible en tu jornada: qué hará el alumno, qué apoyo necesita y cómo reconocerás su avance. Puedes escribirla tú o pedir hasta tres ideas al asistente.')
        with st.expander('Asistente de redacción y propuestas'):
            st.caption('Guía: el alumno identifica / relaciona / resuelve / explica… Evita verbos poco observables como “comprender”. Define evidencia y plazo.')
            for row in st.session_state[prefix+'_doc']['tablas'].get('aprendizajes',st.session_state[prefix+'_doc']['tablas'].get('necesidades',[])):
                descriptor=row.get('Descriptor de logro',row.get('Descriptor de Logro',''))
                if descriptor:
                    for consejo in revisar_redaccion(descriptor):st.caption(consejo)
            _ai(prefix,st.session_state[prefix+'_doc'])
        for name,headers in FORMATOS[doc['formato']]['tablas'].items():
            guias={'barreras':('Barreras y apoyos','¿Qué dificulta participar? Describe el apoyo que ayudará a reducir esa barrera.'),
                   'aprendizajes':('¿Qué queremos que logren?','Ejemplo: El alumno identifica palabras frecuentes con apoyo visual. Define cómo observarás el avance.'),
                   'necesidades':('Necesidades y objetivos','Parte del IEPP: necesidad, acción observable, apoyo y seguimiento.'),
                   'curriculo':('Apoyos en el aula regular','Vincula el aprendizaje priorizado con el programa verificado y los ajustes necesarios.'),
                   'dosificacion':('¿Cómo lo trabajaremos?','Describe una actividad concreta, dónde se realizará, cuándo y con qué recursos.'),
                   'evaluacion_final':('Resultados al finalizar','No necesitas llenar este apartado al comenzar.'),
                   'participantes':('¿Quiénes participarán?','Anota a las personas implicadas y su función.')}
            titulo,ayuda=guias[name]
            st.markdown('#### '+titulo);st.caption(ayuda)
            if name=='evaluacion_final':st.caption('Completar solo con resultados documentados al finalizar; no con predicciones.')
            key=f'{prefix}_{st.session_state.get(prefix+"_generation",0)}_table_{name}'
            basekey=key+'_base'
            if basekey not in st.session_state:
                st.session_state[basekey]=deepcopy([r for r in st.session_state[prefix+'_doc']['tablas'][name] if not r.get('_sesion_equipo')])
            base=st.session_state[basekey]
            st.data_editor(pd.DataFrame(base,columns=headers).fillna(''),num_rows='dynamic',hide_index=True,
                  use_container_width=True,key=key,on_change=_table,args=(prefix,key,name,base))
            if name=='dosificacion':
                automaticas=[r for r in st.session_state[prefix+'_doc']['tablas'][name] if r.get('_sesion_equipo')]
                if automaticas:
                    st.caption('Sesiones vinculadas: edítalas en Calendarizar y editar sesiones; no se duplican al guardar.')
                    st.dataframe(pd.DataFrame(automaticas).drop(columns=['_sesion_equipo']),hide_index=True,use_container_width=True)
    with revisar:
        st.caption('Completa las notas del formato y prepara el PDF para revisarlo. Puedes regresar a cualquiera de los pasos sin crear otro documento.')
        for field in doc['textos']:_text(prefix,'textos',field)
    current=st.session_state[prefix+'_doc']
    faltas=servicio.revisar(current)
    if faltas:
        with st.expander(f'Antes de enviar: {len(faltas)} aspectos por completar'):
            for falta in faltas:st.write('• '+falta)
    else:st.success('El formato está completo para enviarlo a Dirección. Revisa el PDF antes de compartir.')
    left,middle,right=st.columns(3)
    if left.button('Guardar borrador',key=prefix+'_save'):
        _persist(prefix);st.rerun()
    if middle.button('Enviar a Dirección',key=prefix+'_send',disabled=bool(faltas)):
        _persist(prefix,'ENVIADO');st.rerun()
    if right.button('Preparar PDF',key=prefix+'_makepdf'):
        _persist(prefix)
        st.session_state[prefix+'_pdf']=generar_pdf(st.session_state[prefix+'_doc'])
    _autosave(prefix)
    st.download_button('Descargar respaldo editable',json.dumps(current,ensure_ascii=False,indent=2),file_name='planeacion-'+current['id']+'.json',mime='application/json',key=prefix+'_backup')
    if prefix+'_pdf' in st.session_state:
        _preview(prefix,st.session_state[prefix+'_pdf'])
        if st.button('Volver a editar',key=prefix+'_edit_again'):
            st.session_state.pop(prefix+'_pdf',None);st.rerun()
        st.download_button('Descargar PDF',st.session_state[prefix+'_pdf'],file_name='planeacion-'+current['id']+'.pdf',mime='application/pdf',key=prefix+'_download')


def direccion_panel():
    if not servicio.identidad()['director']:raise PermissionError('Solo Dirección.')
    prefix=_prefix()+'_review'
    st.subheader('Planeaciones y planes de intervención del equipo')
    if st.button('Actualizar entregas',key=prefix+'_refresh'):servicio.refrescar()
    try:docs=servicio.listar()
    except Exception:
        st.info('No se pudieron consultar las entregas. No se modificó ningún documento.');return
    if not docs:st.caption('Todavía no hay documentos guardados.');return
    schools=['Todas']+sorted({d['datos']['Escuela regular'] for d in docs})
    school=st.selectbox('Escuela',schools,key=prefix+'_school')
    docs=[d for d in docs if school=='Todas' or d['datos']['Escuela regular']==school]
    selected=st.selectbox('Documento',range(len(docs)),format_func=lambda i:f"{docs[i]['datos']['Nombre del especialista']} · {docs[i]['formato']} · {docs[i]['datos'].get('Periodo','')} · {docs[i]['estado']}",key=prefix+'_selected')
    doc=docs[selected]
    if doc['metadatos'].get('version_contexto')!=servicio.VERSION_CONTEXTO:
        doc=servicio.preparar_contexto(doc)
    st.write(doc['datos']);
    from services.planeacion_equipo import tablas_salida, revisar as revisar_equipo
    for titulo,headers,rows in tablas_salida(doc):
        st.markdown('#### '+titulo)
        st.dataframe(pd.DataFrame(rows,columns=headers),hide_index=True,use_container_width=True)
    for pendiente in revisar_equipo(doc):st.caption('Acuerdos de zona: '+pendiente)
    for name,rows in doc['tablas'].items():
        st.markdown('#### '+name.replace('_',' ').capitalize());st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)
    for name,value in doc['textos'].items():st.write(name+': '+value)
    st.caption('La validación se registra como revisión de Dirección; no coloca una firma manuscrita automática.')
    with st.expander('Detectar áreas de mejora con IA'):
        resumen=st.text_area('Resumen educativo y de la planeación, sin identificadores',key=prefix+'_ia_resumen_'+doc['id'])
        consent=st.checkbox('Revisé que el resumen no identifica personas.',key=prefix+'_ia_consent_'+doc['id'])
        if st.button('Analizar áreas de mejora',disabled=not consent,key=prefix+'_ia_revisar'):
            try:
                contexto=contexto_ia(doc)
                firma=huella(resumen,doc['formato'],doc['datos']['Función'],True,contexto)
                cachekey=prefix+'_analisis_'+doc['id']
                previo=st.session_state.get(cachekey,{})
                if previo.get('huella')!=firma or previo.get('motor')!=modelo_configurado():
                    result=proponer(resumen,doc['formato'],doc['datos']['Función'],True,curriculo=contexto)
                    st.session_state[cachekey]={'huella':firma,'motor':modelo_configurado(),'resultado':result}
            except (ValueError,RuntimeError) as exc:st.info(str(exc))
        previo=st.session_state.get(prefix+'_analisis_'+doc['id'],{})
        try:firma_actual=huella(resumen,doc['formato'],doc['datos']['Función'],True,contexto_ia(doc))
        except ValueError:firma_actual=''
        if previo.get('huella')==firma_actual and previo.get('motor')==modelo_configurado():
            st.caption('Análisis conservado en esta sesión; volver a consultarlo no repite la solicitud.')
            st.write(previo['resultado']['observaciones'])
            for item in previo['resultado']['faltantes']:st.caption(item)
        diagnostico=st.session_state.get('planeacion_ia_diagnostico')
        if diagnostico:st.caption('Diagnóstico: '+str(diagnostico['codigo'] or diagnostico['tipo'])+' · '+diagnostico['motor'])
    observations=st.text_area('Áreas de mejora y observaciones de Dirección',value=doc.get('observaciones_director',''),key=prefix+'_notes_'+doc['revision'])
    for label,state in [('Devolver con observaciones','CON_OBSERVACIONES'),('Validar revisión','VALIDADO')]:
        if st.button(label,key=prefix+'_'+state):
            try:servicio.guardar(doc,state,observations);st.success('Revisión guardada.');st.rerun()
            except Exception as exc:st.warning(str(exc) if isinstance(exc,(ValueError,RuntimeError,PermissionError)) else 'No se confirmó la revisión. Vuelve a intentar.')
    st.download_button('PDF del documento',generar_pdf(doc),file_name='revision-'+doc['id']+'.pdf',mime='application/pdf',key=prefix+'_pdf_'+doc['revision'])


def planeacion_page():
    actor=servicio.identidad();prefix=_prefix()
    st.title('Planeación del equipo · '+actor['area'] if actor['area'] in ('Psicología','Comunicación','Trabajo Social') else 'Planeación e intervención')
    st.caption('1. Elige a quién acompañar  →  2. Revisa lo que ya sabemos  →  3. Planea, guarda y comparte con Dirección')
    editar,recuperar,revisar=st.tabs(['Mi trabajo','Recuperar documentos','Revisión directiva'] if actor['director'] else ['Mi trabajo','Recuperar documentos','Guía'])
    with recuperar:
        backup=st.file_uploader('Recuperar un respaldo editable (.json)',type=['json'],key=prefix+'_import')
        if backup and st.button('Recuperar este respaldo',key=prefix+'_restore'):
            try:
                if backup.size>500000:raise ValueError('El respaldo es demasiado extenso.')
                recovered=json.loads(backup.getvalue())
                servicio.autorizar(recovered,True)
                if recovered['cuenta']!=actor['cuenta']:raise PermissionError('El respaldo corresponde a otra cuenta.')
                latest=next((d for d in servicio.listar() if d['id']==recovered['id']),None)
                recovered['revision']=latest['revision'] if latest else ''
                _open(prefix,recovered);_persist(prefix);st.rerun()
            except Exception as exc:
                st.warning(str(exc) if isinstance(exc,(ValueError,PermissionError)) else 'No se pudo recuperar el respaldo. No se modificó el documento guardado.')
        if st.button('Actualizar documentos',key=prefix+'_reload'):servicio.refrescar()
        try:
            docs=[d for d in servicio.listar() if d['cuenta']==actor['cuenta']]
            if docs:
                i=st.selectbox('Mis documentos guardados',range(len(docs)),format_func=lambda i:f"{docs[i]['datos']['Escuela regular']} · Anexo {docs[i]['formato']} · {docs[i]['datos'].get('Periodo','')} · {docs[i]['estado']}",key=prefix+'_recover')
                if st.button('Abrir documento',key=prefix+'_open'):_open(prefix,docs[i]);st.rerun()
                with st.expander('Versiones anteriores (consulta y respaldo)'):
                    histories=[d for d in servicio.listar(True) if d['id']==docs[i]['id']]
                    for history in histories:
                        st.download_button(history['guardado_en'][:19]+' · '+history['estado'],json.dumps(history,ensure_ascii=False),file_name=history['revision']+'.json',mime='application/json',key=prefix+'_history_'+history['revision'])
            else:st.caption('Aún no tienes documentos guardados.')
        except Exception:st.info('No se pudieron recuperar los documentos. Tu edición actual se conserva.')
    with revisar:
        if actor['director']:direccion_panel()
        else:st.write('XXI: intervención individual basada en IEPP. XXIII: planeación trimestral de apoyo, psicología y comunicación. XXV: planeación de Trabajo Social. Las propuestas son orientaciones revisables, nunca diagnósticos o resultados automáticos.')
    with editar:
        with st.expander('Crear documento',expanded=prefix+'_doc' not in st.session_state):
            frame=servicio.padron_autorizado()
            if frame.empty:st.info('No hay alumnos asignados disponibles.');return
            schools=frame[['ID_Escuela','Nombre_Escuela']].drop_duplicates().to_dict('records')
            si=st.selectbox('Escuela asignada',range(len(schools)),format_func=lambda i:schools[i]['Nombre_Escuela'],key=prefix+'_newschool')
            options=frame.loc[frame['ID_Escuela'].astype(str)==str(schools[si]['ID_Escuela'])].to_dict('records')
            labels={str(a['ID_Alumno']):str(a['Nombre_Completo'])+' · '+str(a.get('Grado',''))+' '+str(a.get('Grupo','')) for a in options}
            formato=st.selectbox('Documento',['XXV' if actor['area']=='Trabajo Social' else 'XXIII','XXI'],format_func=lambda f:FORMATOS[f]['titulo'],key=prefix+'_newformat')
            ids=st.multiselect('Alumno o subgrupo de la misma escuela',list(labels),format_func=labels.get,key=prefix+'_newids')
            ciclo=st.number_input('Inicio del ciclo escolar',2020,2040,2026,key=prefix+'_cycle')
            trimestre=st.selectbox('Trimestre',[1,2,3],format_func=lambda t:{1:'Octubre–diciembre',2:'Enero–marzo',3:'Abril–junio'}[t],key=prefix+'_quarter')
            if st.button('Crear y guardar borrador',key=prefix+'_create',disabled=not ids):
                try:
                    with st.spinner('Reuniendo la información que ya registró el equipo…'):
                        doc=servicio.preparar_contexto(servicio.nueva(formato,ids,int(ciclo),trimestre))
                    _open(prefix,doc);_persist(prefix);st.rerun()
                except (ValueError,PermissionError) as exc:st.warning(str(exc))
        if prefix+'_doc' in st.session_state:_editor(prefix)

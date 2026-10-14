"""Una hoja de trabajo conectada sobre los mismos servicios, versiones y permisos."""
from copy import deepcopy
import json
import pandas as pd
import streamlit as st
from services import planeacion as s, planeacion_viva as viva
from services.planeacion_modelo import FORMATOS
from services.planeacion_modalidad import GUIA_XIX, guia_grupal


def _abrir(base,doc):
    from ui import planeacion as u
    from ui.planeacion_simple import _abrir as abrir
    from services.planeacion_modalidad import modalidad_documento
    prefix=base+'_'+modalidad_documento(doc,s.padron_autorizado())
    abrir(base,prefix,doc)
    return prefix


def _entrada(base,actor):
    from ui import planeacion as u
    from ui.planeacion_simple import periodo_actual,crear_borrador
    try:docs=[d for d in s.listar() if d['cuenta']==actor['cuenta']]
    except Exception:
        docs=[];st.warning('No se pudieron consultar tus documentos. No se eliminó ningún borrador.')
    if docs:
        with st.expander('Continuar una planeación guardada',expanded=True):
            porid={d['id']:d for d in sorted(docs,key=lambda d:d.get('guardado_en',''),reverse=True)}
            did=st.selectbox('Mis planeaciones',list(porid),format_func=lambda i:porid[i]['datos']['Escuela regular']+' · '+porid[i]['datos']['Periodo']+' · '+', '.join(a['Nombre del alumno'] for a in porid[i]['datos']['Alumnos']),key=base+'_viva_guardadas')
            if st.button('Abrir mi formato',key=base+'_viva_abrir'):
                try:_abrir(base,porid[did]);st.rerun()
                except (ValueError,PermissionError,RuntimeError) as exc:st.warning(str(exc))
    st.subheader('Elige a quién vas a planear')
    try:frame=s.padron_autorizado()
    except Exception:st.warning('No se pudo consultar la matrícula. Tus documentos se conservan.');return
    if frame.empty:st.info('No hay alumnos disponibles en tu asignación.');return
    schools=frame[['ID_Escuela','Nombre_Escuela']].drop_duplicates().to_dict('records')
    indice=st.selectbox('Escuela',range(len(schools)),format_func=lambda i:schools[i]['Nombre_Escuela'],key=base+'_viva_escuela') if len(schools)>1 else 0
    school=schools[indice];st.caption(school['Nombre_Escuela'])
    modo=st.segmented_control('Modalidad de planeación',['Individual','Grupal','Por grado'],default='Grupal',key=base+'_viva_modalidad') or 'Grupal'
    tipo='individual' if modo=='Individual' else 'grupal';ciclo,trimestre=periodo_actual();incluir=False
    with st.expander('Cambiar periodo o incluir atención individual en una sesión grupal'):
        ciclo=st.number_input('Inicio del ciclo escolar',2020,2040,ciclo,key=base+'_viva_ciclo')
        trimestre=st.selectbox('Trimestre',[1,2,3],index=trimestre-1,key=base+'_viva_trim')
        if tipo=='grupal' and modo!='Por grado':incluir=st.checkbox('Incluir alumnos de atención individual en esta sesión grupal',key=base+'_viva_incluir')
    if modo=='Por grado':
        incluir=True
        st.caption('Por grado reúne a sus alumnos individuales y grupales autorizados, sin cambiar su modalidad en el padrón.')
    rows=viva.opciones_padron(frame,school['ID_Escuela'],tipo,incluir=incluir)
    if rows.empty:st.info('No hay alumnos con esta modalidad registrada en esta escuela.');return
    grado=grupo=''
    if tipo=='grupal':
        left,right=st.columns(2)
        grado=left.selectbox('Grado',['Todos']+sorted(set(rows['Grado'].astype(str))),key=base+'_viva_grado')
        grados=rows if grado=='Todos' else rows.loc[rows['Grado'].astype(str)==grado]
        grupo=right.selectbox('Grupo',['Todos']+sorted(set(grados['Grupo'].astype(str))),key=base+'_viva_grupo_'+grado)
        rows=viva.opciones_padron(frame,school['ID_Escuela'],tipo,'' if grado=='Todos' else grado,'' if grupo=='Todos' else grupo,incluir)
        if modo=='Por grado' and grado=='Todos':
            st.info('Elige el grado para reunir a sus alumnos. La modalidad registrada no cambia.');return
    nombres={str(a['ID_Alumno']):a['Nombre_Completo'] for a in rows.to_dict('records')}
    selection_key=f'{base}_viva_alumnos_{school["ID_Escuela"]}_{tipo}_{grado}_{grupo}_{incluir}'
    if tipo=='grupal':
        if st.button('Seleccionar alumnos del grado' if modo=='Por grado' else 'Seleccionar todo este grupo',key=selection_key+'_todos'):st.session_state[selection_key]=list(nombres)
        ids=st.multiselect('Alumnos de mi formato',list(nombres),format_func=nombres.get,key=selection_key)
    else:
        elegido=st.selectbox('Alumno de mi formato',['']+list(nombres),format_func=lambda i:nombres.get(i,'Selecciona un alumno'),key=selection_key)
        ids=[elegido] if elegido else []
    fmt='XXV' if actor['area']=='Trabajo Social' else 'XXIII'
    presentacion=None
    if tipo=='grupal' and actor['area']=='Aprendizaje':
        elegido=st.selectbox('Formato para trabajar',['Guía grupal por alumno y área','Planeación trimestral del ejemplo'],key=base+'_papel_formato')
        presentacion='guia' if elegido.startswith('Guía') else 'trimestral'
    if tipo=='individual' and actor['area']=='Aprendizaje' and not actor['director']:
        opcion=st.selectbox('Formato',['Planeación trimestral','Plan de intervención anual'],key=base+'_viva_tipo')
        if opcion=='Plan de intervención anual':fmt='XXI'
    st.caption(f'Curso {ciclo}–{ciclo+1} · Trimestre {trimestre}. Se reúnen los antecedentes propios de los alumnos seleccionados.')
    if st.button('Abrir formato con mis alumnos',disabled=not ids,type='primary',key=base+'_viva_crear'):
        try:
            crear_borrador(base,fmt,ids,int(ciclo),trimestre,tipo,incluir,presentacion);st.rerun()
        except (ValueError,PermissionError,RuntimeError) as exc:st.warning(str(exc))
    with st.expander('Actualizar matrícula, recuperar un respaldo o consultar las guías'):
        if st.button('Actualizar matrícula disponible',key=base+'_viva_refresh'):s.refrescar_matricula();st.rerun()
        from ui.planeacion_simple import _recuperar
        _recuperar(base)
        from ui.planeacion_ayuda import panel
        panel(actor['area'])


def _matriz_cambio(prefix,key,base):
    from ui import planeacion as u
    try:
        st.session_state[prefix+'_doc']=viva.editar_guia(st.session_state[prefix+'_doc'],st.session_state[key],base)
        st.session_state.pop(prefix+'_pdf',None);u._persist(prefix,automatic=True)
    except (ValueError,PermissionError,RuntimeError) as exc:st.session_state[prefix+'_viva_error']=str(exc)


def _texto_guia(prefix,key,indice,campo,base):
    from ui import planeacion as u
    try:
        nuevo=viva.editar_guia(st.session_state[prefix+'_doc'],{'edited_rows':{indice:{campo:st.session_state[key]}}},base)
        u._open(prefix,nuevo);u._persist(prefix,automatic=True)
    except (ValueError,PermissionError,RuntimeError) as exc:st.session_state[prefix+'_viva_error']=str(exc)


def _matriz(prefix):
    doc=st.session_state[prefix+'_doc'];filas=guia_grupal(doc)['filas']
    st.markdown('#### Guía de planeación grupal')
    st.caption('Anexo XIX · Qué trabajar y cómo, en la misma fila de cada alumno. Las otras áreas conservan sus aportaciones.')
    gen=st.session_state.get(prefix+'_generation',0);key=f'{prefix}_{gen}_viva_matriz';bk=key+'_base'
    if bk not in st.session_state:st.session_state[bk]=deepcopy(filas)
    base=st.session_state[bk];editables=viva.campos_guia(doc)
    st.data_editor(pd.DataFrame(base,columns=['ID_Alumno',*GUIA_XIX]).drop(columns='ID_Alumno'),
        column_order=GUIA_XIX,hide_index=True,num_rows='fixed',row_height=100,
        height=min(520,70+100*len(base)),use_container_width=True,
        column_config={c:st.column_config.TextColumn(c,width={'Nombre alumno':180,'Discapacidad o condición':170,'Fecha derivación':140,'Situación inicial':130,'Situación final':130}.get(c,140)) for c in GUIA_XIX},
        disabled=[c for c in GUIA_XIX if c not in editables],key=key,on_change=_matriz_cambio,args=(prefix,key,base))
    if doc['metadatos'].get('guia_compartida'):st.caption('Guía vinculada: cada profesional edita su aportación en Trabajo colaborativo.')
    st.caption('Situación final: se registra después de la atención. No se genera como una predicción.')


def _ficha(prefix,grupal):
    from ui import planeacion as u
    doc=st.session_state[prefix+'_doc'];nombres={a['ID_Alumno']:a['Nombre del alumno'] for a in doc['datos']['Alumnos']}
    aid=st.selectbox('Alumno para consultar o completar',list(nombres),format_func=nombres.get,key=f'{prefix}_{doc["id"]}_viva_ficha')
    datos=viva.ficha(doc,aid);persona=datos['alumno']
    st.caption('Datos del padrón · '+str(persona.get('Grado',''))+'° '+str(persona.get('Grupo',''))+' · '+str(persona.get('Condición','')))
    with st.expander('Antecedentes de este alumno y documentos para enriquecer el formato'):
        if not datos['antecedentes']:st.caption('Aún no hay antecedentes individuales vinculados. Puedes incorporar un documento; no se usarán registros de otros alumnos.')
        for i,f in enumerate(datos['antecedentes']):
            with st.expander(str(f.get('fecha',''))+' · '+f['referencia'],expanded=i==0):
                st.write(f['texto']);st.caption('Antecedente documentado, no un resultado futuro ni una actividad propuesta.')
        if datos['materiales_generales']:st.caption('También hay materiales generales de apoyo; no equivalen a evaluaciones de este alumno.')
        if st.button('Actualizar antecedentes del expediente',key=prefix+'_viva_antecedentes'):
            try:
                s.refrescar_evidencias();u._open(prefix,s.preparar_contexto(st.session_state[prefix+'_doc']));u._persist(prefix);st.rerun()
            except Exception:st.warning('No se confirmó la actualización. Tu edición se conserva.')
        if st.toggle('Añadir documento o imagen',key=prefix+'_viva_documentos'):u._materiales(prefix,st.session_state[prefix+'_doc'])
    if grupal:
        filas=guia_grupal(st.session_state[prefix+'_doc'])['filas'];indice=next(i for i,r in enumerate(filas) if r['ID_Alumno']==aid)
        with st.expander('Escribir con más espacio en la fila de este alumno'):
            for campo in viva.campos_guia(doc):
                key=f'{prefix}_{st.session_state.get(prefix+"_generation",0)}_viva_texto_{aid}_{campo}'
                st.text_area(campo,value=str(filas[indice].get(campo,'') or ''),height=140,key=key,
                    on_change=_texto_guia,args=(prefix,key,indice,campo,filas))


def _referentes(prefix):
    from ui import planeacion as u
    from services.curriculo import contexto_ia
    doc=st.session_state[prefix+'_doc'];cur=contexto_ia(doc)
    with st.expander('Referentes oficiales · contenidos, PDA y contexto de la escuela'):
        registros=cur.get('referentes_por_grado',[])
        if not registros:st.caption('Selecciona los referentes pertinentes; no se deducen del diagnóstico ni cambian el grado del padrón.')
        for r in registros:
            st.write(r['campo']+' · '+str(r['grado'])+'° · '+r['contenido'])
            st.write(r['pda']);st.caption(r['fuente']+' · página PDF '+str(r['pagina_pdf']))
        if st.toggle('Elegir o ajustar contenidos y PDA',key=prefix+'_viva_referentes'):u._curriculo(prefix,doc)


def _ayuda(prefix):
    from ui import planeacion as u
    doc=st.session_state[prefix+'_doc']
    with st.expander('Preparar actividades para este formato · con mis datos o con IA'):
        st.caption('El formato siempre está disponible. Preparar actividades es opcional y no sustituye tu revisión.')
        from ui.planeacion_local import panel as local
        local(prefix)
        with st.expander('Añadir una orientación o necesidad documentada'):
            u._text(prefix,'metadatos','necesidades_confirmadas','Necesidades y apoyos documentados (incluye la referencia de origen)')
        if st.toggle('Solicitar propuesta con IA',key=prefix+'_viva_ia'):
            if doc['formato']=='XXI':u._ai(prefix,st.session_state[prefix+'_doc'])
            else:
                from ui.planeacion_generacion import panel_generacion
                panel_generacion(prefix,u._persist,u._open,compact=True)


def _acciones(prefix,pdf_provider=None,acciones_hoja=False):
    from ui import planeacion as u
    from ui.planeacion_simple import _pendientes
    doc=st.session_state[prefix+'_doc'];faltas,avisos=_pendientes(doc)
    with st.expander('Revisar antes de entregar · '+str(len(avisos))+' aspectos pendientes'):
        for aviso in avisos:st.write('• '+aviso)
        if not faltas:st.success('El formato está listo para tu revisión final.')
    # Solo un contenedor propio; el CSS no depende de clases internas de Streamlit.
    st.html('<style>.st-key-'+prefix+'_viva_acciones{position:sticky;bottom:0;z-index:10;background:var(--background-color,#fff);padding:.7rem;border-top:1px solid #c8d3d5}</style>')
    with st.container(horizontal=True,key=prefix+'_viva_acciones'):
        if not acciones_hoja:
            if st.button('Guardar borrador',key=prefix+'_viva_guardar'):u._persist(prefix);st.rerun()
            if st.button('Ver PDF',key=prefix+'_viva_pdf'):st.session_state[prefix+'_mostrar_pdf']=True;st.rerun()
            if st.button('Enviar a Dirección',disabled=bool(faltas),key=prefix+'_viva_enviar'):u._persist(prefix,'ENVIADO');st.rerun()
    if st.session_state.get(prefix+'_mostrar_pdf'):
        with st.expander('Documento para imprimir',expanded=True):
            try:
                pdf=u._pdf_sesion(prefix,doc,provider=pdf_provider) if pdf_provider else u._pdf_sesion(prefix,doc)
                u._preview(prefix+'_viva_preview',pdf)
                st.download_button('Descargar PDF',pdf,file_name='planeacion-'+doc['id']+'.pdf',mime='application/pdf',key=prefix+'_viva_descarga_pdf')
            except Exception:st.warning('No se pudo preparar la vista. El borrador se conserva.')
    with st.expander('Más opciones · alumnos, versiones, respaldo y herramientas'):
        from ui.planeacion_edicion import panel
        panel(prefix)
        from ui.planeacion_simple import _herramientas
        if st.toggle('Abrir herramientas complementarias',key=prefix+'_viva_tools'):_herramientas(prefix,s.identidad())
        st.download_button('Descargar respaldo editable',json.dumps(doc,ensure_ascii=False,indent=2),file_name='planeacion-'+doc['id']+'.json',mime='application/json',key=prefix+'_viva_respaldo')
        if st.button('Elegir otro formato o alumnos',key=prefix+'_viva_otro'):
            if st.session_state.get(prefix+'_pending') and not u._guardar_edicion_pendiente(prefix):st.warning('Primero confirma el guardado o descarga tu respaldo.')
            else:st.session_state[prefix.rsplit('_',1)[0]+'_viva_entrada']=True;st.rerun()


def hoja(prefix):
    from ui import planeacion as u
    from ui.planeacion_formato import _tabla
    doc=st.session_state[prefix+'_doc'];s.autorizar(doc,True)
    if doc['metadatos'].get('version_contexto')!=s.VERSION_CONTEXTO:
        u._open(prefix,s.preparar_contexto(doc));st.session_state[prefix+'_pending']=True
    doc=st.session_state[prefix+'_doc'];datos=doc['datos']
    grupal=doc['metadatos'].get('modalidad_planeacion')=='grupal'
    matriz_principal=grupal and datos['Función']=='Aprendizaje'
    u._autosave(prefix)
    if st.session_state.get(prefix+'_viva_error'):st.warning(st.session_state.pop(prefix+'_viva_error'))
    if doc.get('observaciones_director'):st.info('Dirección: '+doc['observaciones_director'])
    with st.container(border=True,key=prefix+'_viva_hoja'):
        st.subheader('Planeación grupal del Servicio de Apoyo' if matriz_principal else FORMATOS[doc['formato']]['titulo'])
        a,b=st.columns(2)
        a.write(datos['Escuela regular']+' · '+datos.get('CCT',''))
        a.caption(datos['Servicio de apoyo']+' · Zona '+str(datos['Zona']))
        b.write(datos['Nombre del especialista']+' · '+datos['Función'])
        b.caption('Curso '+datos['Curso escolar']+' · '+datos['Periodo'])
        st.caption('Grado y grupo: '+', '.join(sorted({str(a.get('Grado',''))+'° '+str(a.get('Grupo','')) for a in datos['Alumnos']})))
        if not datos.get('CCT'):u._text(prefix,'datos','CCT','CCT pendiente de confirmar')
        if matriz_principal:
            _matriz(prefix)
            with st.expander('Datos del grupo y complemento de aptitudes sobresalientes'):
                from ui.planeacion_simple import _guia_adicional
                _guia_adicional(prefix,st.session_state[prefix+'_doc'])
        else:st.dataframe(pd.DataFrame(datos['Alumnos'])[['Nombre del alumno','Grado','Grupo','Condición']],hide_index=True,use_container_width=True)
        _ficha(prefix,grupal)
        _referentes(prefix)
        _ayuda(prefix)
        if doc['formato']=='XXI':
            with st.expander('Fuente del IEPP y datos del plan anual'):
                u._text(prefix,'metadatos','fuente_iepp','Referencia del IEPP: fecha, folio o ubicación del informe')
                key=f'{prefix}_{st.session_state.get(prefix+"_generation",0)}_viva_iepp'
                st.checkbox('Las NEE fueron confirmadas en el IEPP.',value=bool(doc['metadatos'].get('NEE confirmadas desde IEPP')),key=key,on_change=u._field,args=(prefix,key,'metadatos','NEE confirmadas desde IEPP'))
                for campo in ('Necesidades educativas específicas asociadas a','Maestro de grupo','Vigencia en cursos escolares'):u._text(prefix,'datos',campo)
        if matriz_principal:
            with st.expander('Objetivos, descriptores, secuencias y evaluación · detalle trimestral'):
                for tabla in FORMATOS[doc['formato']]['tablas']:_tabla(prefix,tabla,u._persist,u._open)
                for campo in doc['textos']:u._text(prefix,'textos',campo)
        else:
            for tabla in FORMATOS[doc['formato']]['tablas']:
                if tabla=='evaluacion_final':
                    with st.expander('Resultados al finalizar'):_tabla(prefix,tabla,u._persist,u._open)
                else:_tabla(prefix,tabla,u._persist,u._open)
            for campo in doc['textos']:
                if campo=='Resultados obtenidos en los diferentes contextos':
                    with st.expander('Resultados después de la intervención'):u._text(prefix,'textos',campo)
                else:u._text(prefix,'textos',campo)
            if grupal:
                with st.expander('Conexión con la guía grupal por alumno'):_matriz(prefix)
        from services.planeacion_equipo import aplica,contexto_zona
        if aplica(doc):
            with st.expander('Sesiones y acuerdos específicos de '+datos['Función']):
                st.caption(contexto_zona(doc)['guia'])
                from ui.planeacion_equipo import panel
                panel(prefix,st.session_state[prefix+'_doc'],u._persist,u._open,compact=True)
    _acciones(prefix)


def pagina(render_hoja=None):
    from ui import planeacion as u
    actor=s.identidad();base=u._prefix()
    if st.session_state.get(base+'_viva_anterior'):
        if st.button('Volver al formato vivo',key=base+'_viva_volver'):st.session_state[base+'_viva_anterior']=False;st.rerun()
        from ui.planeacion_simple import pagina as anterior
        anterior();return
    if render_hoja:
        st.subheader('Planeación · '+actor['area'])
    else:
        st.title('Mi formato · '+actor['area'])
        st.caption('Planea en tu hoja de siempre. Los alumnos y sus antecedentes ya están conectados; tú decides qué trabajar y cómo.')
    labels=['Mi formato','Trabajo colaborativo']+(['Revisión directiva'] if actor['director'] else [])
    tabs=st.tabs(labels)
    with tabs[0]:
        activo=st.session_state.get(base+'_activa')
        if not activo:
            prefixes=[p for p in (base+'_individual',base+'_grupal') if p+'_doc' in st.session_state]
            activo=next((p for p in prefixes if st.session_state.get(p+'_pending')),next(iter(prefixes),None))
            if activo:st.session_state[base+'_activa']=activo
        if activo and activo+'_doc' in st.session_state and not st.session_state.get(base+'_viva_entrada'):
            (render_hoja or hoja)(activo)
        else:
            anterior=st.session_state.get(base+'_activa')
            _entrada(base,actor)
            if st.session_state.get(base+'_activa')!=anterior:st.session_state[base+'_viva_entrada']=False
            if activo and st.button('Volver al formato abierto',key=base+'_viva_retomar'):st.session_state[base+'_viva_entrada']=False;st.rerun()
        with st.expander('Vista anterior y ayuda'):
            if st.button('Usar el recorrido anterior',key=base+'_viva_legacy'):st.session_state[base+'_viva_anterior']=True;st.rerun()
    with tabs[1]:
        from ui.planeacion_colaboracion import panel
        panel(base+'_colaboracion')
    if actor['director']:
        with tabs[2]:u.direccion_panel()

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
    for key,value in list(st.session_state.items()):
        if key.startswith(base+'_') and key.endswith('_doc') and isinstance(value,dict) and st.session_state.get(key[:-4]+'_pending'):
            if not u._guardar_edicion_pendiente(key[:-4]):raise RuntimeError('El autoguardado aún no se confirmó; tu edición sigue abierta. Reintenta cuando vuelva la conexión.')
            if value.get('id')==doc.get('id'):doc=deepcopy(st.session_state[key])
    abrir(base,prefix,doc)
    for suffix in ('_papel_panel','_papel_nonce','_papel_aceptado','_papel_legacy','_papel_rechazado','_papel_error'):
        st.session_state.pop(prefix+suffix,None)
    return prefix


def _entrada(base,actor):
    from ui import planeacion as u
    from ui.planeacion_simple import periodo_actual,crear_borrador
    from ui.planeacion_borradores import papelera
    papelera(base)
    try:docs=[d for d in s.listar() if d['cuenta']==actor['cuenta']]
    except Exception:
        docs=[];st.warning('No se pudieron consultar tus documentos. No se eliminó ningún borrador.')
    if st.button('Actualizar mis planeaciones guardadas',key=base+'_viva_actualizar_documentos'):
        s.refrescar();st.rerun()
    if docs:
        with st.expander('Continuar una planeación guardada', expanded=True):
            from services.planeacion_recuperacion import ordenar, etiqueta, actividades_redactadas
            docs_ordenados = ordenar(docs)
            limite_defecto = 5
            mostrar_todos = False
            if len(docs_ordenados) > limite_defecto:
                mostrar_todos = st.toggle('Ver historial completo de planeaciones', key=base+'_viva_ver_todos', value=False)
            docs_visibles = docs_ordenados if mostrar_todos else docs_ordenados[:limite_defecto]
            porid = {d['id']: d for d in docs_visibles}
            if actividades_redactadas(next(iter(porid.values()))):
                st.caption('Mostrando las planeaciones más recientes y editadas. Selecciona una para continuar redactando o eliminar borradores que ya no ocupes.')
            did = st.selectbox('Mis planeaciones recientes', list(porid), format_func=lambda i: etiqueta(porid[i]), key=base+'_viva_guardadas')
            col_abrir, _ = st.columns([2, 1])
            with col_abrir:
                if st.button('✏️ Continuar editando este formato', type='primary', key=base+'_viva_abrir'):
                    try:
                        _abrir(base, porid[did])
                        st.rerun()
                    except (ValueError, PermissionError, RuntimeError) as exc:
                        st.warning(str(exc))
            from ui.planeacion_borradores import controles
            from documents.planeacion_papel import generar_pdf
            controles(base+'_lista_'+did, porid[did], generar_pdf, lambda: None)
    st.subheader('Elige a quién vas a planear')
    try:
        from services.planeacion_matricula import preparar
        frame=preparar(s.padron_autorizado())
    except Exception:st.warning('No se pudo consultar la matrícula. Tus documentos se conservan.');return
    if frame.empty:st.info('No hay alumnos disponibles en tu asignación.');return
    schools=frame[['ID_Escuela','Nombre_Escuela']].drop_duplicates().to_dict('records')
    por_escuela={str(e['ID_Escuela']):e for e in schools}
    escuela_key=base+'_escuela_exacta'
    if st.session_state.get(escuela_key) not in por_escuela:st.session_state[escuela_key]=next(iter(por_escuela))
    izquierda,derecha=st.columns([2,1])
    escuela=izquierda.selectbox('Escuela asignada',list(por_escuela),format_func=lambda i:por_escuela[i]['Nombre_Escuela'],key=escuela_key)
    school=por_escuela[escuela]
    especialista=actor['area'] in ('Psicología','Comunicación','Trabajo Social')
    if especialista:
        st.info('Aquí elaboras tu formato propio de especialista. Para continuar el Anexo XIX iniciado por apoyo, elige «Planeaciones del equipo» arriba.')
    modos=['Individual','Mi intervención'] if especialista else ['Individual','Grupal','Por grado']
    modo=derecha.segmented_control('Modalidad de planeación',modos,default='Mi intervención' if especialista else 'Grupal',key=base+'_viva_modalidad_v3') or modos[0]
    tipo='individual' if modo=='Individual' else 'grupal';ciclo,trimestre=periodo_actual();incluir=False
    with st.expander('Cambiar periodo o incluir atención individual en una sesión grupal'):
        ciclo=st.number_input('Inicio del ciclo escolar',2020,2040,ciclo,key=base+'_viva_ciclo')
        trimestre=st.selectbox('Trimestre',[1,2,3],index=trimestre-1,key=base+'_viva_trim')
        if tipo=='grupal' and modo!='Por grado':
            incluir=st.checkbox('Reunir alumnos de atención grupal e individual en este formato',value=not especialista,key=base+'_viva_incluir_v2')
    if tipo=='grupal' and not especialista:
        st.caption('La hoja grupal incluye por defecto a los alumnos del grado, también a quienes reciben atención individual. No cambia su tipo de atención en el padrón.')
    if modo=='Por grado':
        incluir=True
        st.caption('Por grado reúne a sus alumnos individuales y grupales autorizados, sin cambiar su modalidad en el padrón.')
    rows=frame.loc[frame['ID_Escuela']==school['ID_Escuela']].copy() if especialista and modo=='Mi intervención' else viva.opciones_padron(frame,school['ID_Escuela'],tipo,incluir=incluir)
    if rows.empty:st.info('No hay alumnos con esta modalidad registrada en esta escuela.');return
    grado=grupo=''
    if tipo=='grupal':
        left,right=st.columns(2)
        grado=left.selectbox('Grado',['Todos']+sorted(set(rows['Grado'].astype(str))),key=base+'_viva_grado')
        grados=rows if grado=='Todos' else rows.loc[rows['Grado'].astype(str)==grado]
        grupo=right.selectbox('Grupo',['Todos']+sorted(set(grados['Grupo'].astype(str))),key=base+'_viva_grupo_'+grado)
        if especialista:
            rows=grados if grupo=='Todos' else grados.loc[grados['Grupo'].astype(str)==grupo]
        else:rows=viva.opciones_padron(frame,school['ID_Escuela'],tipo,'' if grado=='Todos' else grado,'' if grupo=='Todos' else grupo,incluir)
        if modo=='Por grado' and grado=='Todos':
            st.info('Elige el grado para reunir a sus alumnos. La modalidad registrada no cambia.');return
    nombres={str(a['ID_Alumno']):a['Nombre_Completo'] for a in rows.to_dict('records')}
    selection_key=f'{base}_viva_alumnos_{school["ID_Escuela"]}_{tipo}_{grado}_{grupo}_{incluir}'
    # Clave nueva: una sesión abierta podía conservar el valor escalar del
    # selector individual anterior; no reutilizarlo como lista del multiselect.
    if tipo=='individual':selection_key+='_multiple'
    label='Seleccionar todos los alumnos individuales' if tipo=='individual' else 'Seleccionar alumnos del grado' if modo=='Por grado' else 'Seleccionar todo este grupo'
    if st.button(label,key=selection_key+'_todos'):st.session_state[selection_key]=list(nombres)
    ids=st.multiselect('Alumnos de mi formato',list(nombres),format_func=nombres.get,key=selection_key)
    if tipo=='individual':st.caption('Puedes reunir varios alumnos de atención individual en un formato trimestral; sus antecedentes se conservan vinculados a cada alumno.')
    fmt='XXV' if actor['area']=='Trabajo Social' else 'XXIII'
    presentacion=None
    if tipo=='grupal' and actor['area']=='Aprendizaje':
        elegido=st.selectbox('Formato para trabajar',['Guía grupal horizontal por alumno y área · Anexo XIX','Planeación trimestral para el subgrupo · Anexo XXIII'],key=base+'_papel_formato_v2')
        presentacion='guia' if elegido.startswith('Guía') else 'trimestral'
    if tipo=='individual' and len(ids)<=1 and actor['area']=='Aprendizaje' and not actor['director']:
        opcion=st.selectbox('Formato',['Planeación trimestral','Plan de intervención anual'],key=base+'_viva_tipo')
        if opcion=='Plan de intervención anual':fmt='XXI'
    elif tipo=='individual' and len(ids)>1 and actor['area']=='Aprendizaje':
        st.caption('El Plan de intervención anual se elabora por alumno y conserva su IEPP; esta selección abre la planeación trimestral.')
    st.caption(f'Curso {ciclo}–{ciclo+1} · Trimestre {trimestre}. Se reúnen los antecedentes propios de los alumnos seleccionados.')
    nuevo_independiente=False
    if ids and tipo=='individual':
        from services.planeacion_recuperacion import equivalentes
        existentes=equivalentes(docs,actor,fmt,ids,school['ID_Escuela'],ciclo,trimestre,tipo)
        if existentes:
            st.info('Ya tienes una planeación para estos alumnos y periodo. Al abrir el formato continuarás el documento guardado, sin crear otra plantilla.')
            nuevo_independiente=st.checkbox('Necesito crear otro borrador independiente; conservar el anterior',key=base+'_viva_otro_borrador')
    if presentacion=='guia':st.caption('Un único documento por escuela, grado, grupo y trimestre. Si ya existe, se continúa el mismo; no se crea otra copia.')
    if st.button('Abrir formato con mis alumnos',disabled=not ids,type='primary',key=base+'_viva_crear'):
        try:
            elegidos=rows.loc[rows['ID_Alumno'].astype(str).isin(ids)]
            if presentacion=='guia' and len(elegidos[['Grado','Grupo']].drop_duplicates())!=1:
                raise ValueError('Elige un grado y grupo concreto para el Anexo XIX compartido. Así se conectarán automáticamente sus altas nuevas.')
            crear_borrador(base,fmt,ids,int(ciclo),trimestre,'especialista' if especialista and modo=='Mi intervención' else tipo,incluir,presentacion,proponer_apartados=True,nuevo_independiente=nuevo_independiente);st.rerun()
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
    from utils.escolar import grado_canonico
    st.caption('Datos del padrón · '+grado_canonico(persona.get('Grado',''))+' '+str(persona.get('Grupo',''))+' · '+str(persona.get('Condición','')))
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
    if not acciones_hoja:
        with st.expander('Revisar antes de entregar · '+str(len(avisos))+' aspectos pendientes'):
            from ui.planeacion_revision import panel as revisar
            revisar(prefix)
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
                from ui.archivo_expediente import boton
                boton([a['ID_Alumno'] for a in doc['datos']['Alumnos']],
                    'Planeación grupal' if doc['metadatos'].get('modalidad_planeacion')=='grupal' else 'Plan de intervención' if doc['formato']=='XXI' else 'Planeación del servicio',
                    pdf,'planeacion-'+doc['id']+'.pdf',prefix+'_archivar',doc['id'],doc['datos']['Curso escolar'],
                    'EPP iniciada' if doc['metadatos'].get('modalidad_planeacion')=='individual' or doc['formato']=='XXI' else '',
                    disabled=bool(st.session_state.get(prefix+'_pending')))
            except Exception:st.warning('No se pudo preparar la vista. El borrador se conserva.')
    from ui.planeacion_borradores import controles,cerrar_editor
    controles(prefix+'_borrador',doc,pdf_provider or u.generar_pdf,lambda:cerrar_editor(prefix.rsplit('_',1)[0],prefix))
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
        from utils.escolar import grado_canonico
        st.caption('Grado y grupo: '+', '.join(sorted({grado_canonico(a.get('Grado',''))+' '+str(a.get('Grupo','')) for a in datos['Alumnos']})))
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
    from ui.planeacion_accesos import opciones,menu
    permitidas={id for id,_,_,_ in opciones(actor)}
    vista=st.session_state.get(base+'_submodulo')
    st.caption('Accesos claros · una sola hoja grupal por grado, grupo y periodo')
    if vista not in permitidas:
        menu(base,actor);return
    activo=st.session_state.get(base+'_activa')
    editando=(vista=='propio' and activo and activo+'_doc' in st.session_state and not st.session_state.get(base+'_viva_entrada')) or (vista=='equipo' and st.session_state.get(base+'_colaboracion_abierto'))
    # El editor dispone de su regreso protegido: no añadir un atajo que ignore
    # su texto todavía en el navegador o una aportación pendiente.
    if not editando and st.button('Volver a los accesos de Planeación',key=base+'_accesos_volver'):
        st.session_state.pop(base+'_submodulo',None);st.rerun()
    if vista=='revision':
        u.direccion_panel()
    elif vista=='propio':
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
        with st.expander('Ayuda y herramientas anteriores',expanded=False):
            if st.button('Usar el recorrido anterior',key=base+'_viva_legacy'):st.session_state[base+'_viva_anterior']=True;st.rerun()
    elif vista=='equipo':
        from ui.planeacion_colaboracion import panel
        panel(base+'_colaboracion')

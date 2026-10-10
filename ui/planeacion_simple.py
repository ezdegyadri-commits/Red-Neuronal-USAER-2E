"""Recorrido breve sobre los servicios canónicos; no crea otra persistencia."""
from copy import deepcopy
from datetime import datetime
from zoneinfo import ZoneInfo
import json
import pandas as pd
import streamlit as st
from services import planeacion as s, planeacion_equipo as equipo
from services.planeacion_modalidad import modalidad, GUIA_XIX, GUIA_XX, guia_grupal
from services.planeacion_modelo import FORMATOS

PASOS=('1. ¿A quién planeo?', '2. Preparar con IA', '3. Revisar y enviar')


def periodo_actual(hoy=None):
    hoy=hoy or datetime.now(ZoneInfo('America/Mexico_City')).date()
    return hoy.year if hoy.month>=8 else hoy.year-1, 2 if hoy.month<=3 else 3 if hoy.month<=6 else 1


def seleccion(frame,ids,incluir=False):
    """Presentación de la modalidad. La autorización definitiva sigue en nueva()."""
    rows=frame.loc[frame['ID_Alumno'].astype(str).isin(ids)].to_dict('records')
    if len(rows)!=len(set(ids)):raise ValueError('Revisa los alumnos de tu matrícula.')
    tipos={modalidad(r) for r in rows}
    if not tipos or 'por confirmar' in tipos:raise ValueError('Confirma la modalidad de atención en el padrón antes de continuar.')
    if tipos=={'individual'} and len(ids)==1 and not incluir:return 'individual'
    if 'individual' in tipos and not incluir:raise ValueError('Para reunir alumnos individuales, activa la opción avanzada de sesión grupal.')
    return 'grupal'


def _abrir(base,prefix,doc):
    from ui import planeacion as u
    # No cambiar de modalidad permite saltarse el resguardo de otra edición.
    for key,value in list(st.session_state.items()):
        if key.startswith(base+'_') and key.endswith('_doc') and isinstance(value,dict):
            previo=key[:-4]
            if st.session_state.get(previo+'_pending') and (value.get('id')!=doc.get('id') or value.get('revision')!=doc.get('revision')):
                raise RuntimeError('Guarda la edición pendiente antes de abrir otra planeación. Tu trabajo se conserva.')
    u._open(prefix,doc)
    st.session_state[prefix+'_mostrar_pdf']=False
    st.session_state[base+'_activa']=prefix
    st.session_state[base+'_paso_pendiente']=PASOS[2] if doc.get('metadatos',{}).get('generacion_completa') else PASOS[1]


def _entrada(base,actor):
    from ui import planeacion as u
    st.subheader(PASOS[0])
    try:docs=[d for d in s.listar() if d['cuenta']==actor['cuenta']]
    except Exception:
        docs=[];st.warning('No se pudieron consultar los borradores guardados. La edición abierta se conserva.')
    st.markdown('#### Continuar donde me quedé')
    if docs:
        pagina=st.number_input('Página de mis documentos',1,max(1,(len(docs)+4)//5),1,key=base+'_pagina_docs') if len(docs)>5 else 1
        for doc in sorted(docs,key=lambda d:d.get('guardado_en',''),reverse=True)[(pagina-1)*5:pagina*5]:
            with st.container(border=True):
                st.write(doc['datos']['Escuela regular']+' · '+', '.join(a['Nombre del alumno'] for a in doc['datos']['Alumnos']))
                st.caption({'CON_OBSERVACIONES':'Por ajustar','BORRADOR':'Borrador','ENVIADO':'Enviado','VALIDADO':'Revisado'}.get(doc['estado'],doc['estado'])+' · '+doc['datos'].get('Periodo',''))
                if st.button('Continuar',key=base+'_continuar_'+doc['id']):
                    try:
                        from services.planeacion_modalidad import modalidad_documento
                        _abrir(base,base+'_'+modalidad_documento(doc,s.padron_autorizado()),doc);st.rerun()
                    except (ValueError,PermissionError,RuntimeError) as exc:st.warning(str(exc))
    else:st.caption('Tus borradores aparecerán aquí después del primer guardado confirmado.')
    with st.expander('Recuperar un respaldo o consultar ayuda'):
        if st.button('Actualizar mis documentos',key=base+'_simple_refrescar'):
            s.refrescar();st.rerun()
        _recuperar(base)
        from ui.planeacion_ayuda import panel
        panel(actor['area'])
    st.markdown('#### Nueva planeación')
    frame=s.padron_autorizado()
    if frame.empty:st.info('No hay alumnos asignados disponibles.');return
    escuelas=frame[['ID_Escuela','Nombre_Escuela']].drop_duplicates().to_dict('records')
    indice=st.selectbox('Escuela asignada',range(len(escuelas)),format_func=lambda i:escuelas[i]['Nombre_Escuela'],key=base+'_escuela') if len(escuelas)>1 else 0
    escolar=frame.loc[frame['ID_Escuela'].astype(str)==str(escuelas[indice]['ID_Escuela'])]
    etiquetas={str(r['ID_Alumno']):str(r['Nombre_Completo'])+' · '+str(r.get('Grado',''))+' '+str(r.get('Grupo','')) for r in escolar.to_dict('records') if modalidad(r)!='por confirmar'}
    ids=st.multiselect('Alumno o alumnos para planear',list(etiquetas),format_func=etiquetas.get,key=base+'_alumnos_'+str(escuelas[indice]['ID_Escuela']))
    if len(etiquetas)<len(escolar):st.caption('Hay alumnos con atención por confirmar. No se asignan automáticamente a una modalidad.')
    ciclo,trimestre=periodo_actual();incluir=False
    with st.expander('Cambiar periodo u organizar una sesión grupal especial'):
        ciclo=st.number_input('Inicio del ciclo escolar',2020,2040,ciclo,key=base+'_ciclo')
        trimestre=st.selectbox('Trimestre',[1,2,3],index=trimestre-1,key=base+'_trimestre')
        incluir=st.checkbox('Incluir alumnos de atención individual en esta sesión grupal',key=base+'_incluir')
    st.caption(f'Curso {ciclo}–{ciclo+1} · Trimestre {trimestre}. La modalidad se toma del padrón; no lo modifica.')
    tipo=None
    if ids:
        try:tipo=seleccion(escolar,ids,incluir)
        except ValueError as exc:st.info(str(exc))
    fmt='XXV' if actor['area']=='Trabajo Social' else 'XXIII'
    if tipo=='individual' and actor['area']=='Aprendizaje' and not actor['director']:
        opcion=st.segmented_control('¿Qué documento necesitas?', ['Planeación trimestral','Plan de intervención'],default='Planeación trimestral',key=base+'_formato')
        fmt='XXI' if opcion=='Plan de intervención' else 'XXIII'
    if st.button('Crear mi borrador',type='primary',disabled=not tipo,key=base+'_crear'):
        try:
            # Guardar primero la edición actual; nunca crear ni desplazarla a ciegas.
            for key in list(st.session_state):
                if key.startswith(base+'_') and key.endswith('_doc') and st.session_state.get(key[:-4]+'_pending'):
                    if not u._guardar_edicion_pendiente(key[:-4]):raise RuntimeError('Primero confirma el guardado de tu edición pendiente.')
            with st.spinner('Reuniendo la información que ya registró el equipo…'):
                doc=s.preparar_contexto(s.nueva(fmt,ids,int(ciclo),trimestre,modalidad=tipo,incluir_individuales=incluir))
                if equipo.aplica(doc) and not doc['metadatos'].get('equipo',{}).get('subgrupos'):
                    doc=equipo.guardar_subgrupo(equipo.preparar(doc),'Subgrupo 1',ids)
                if fmt=='XXI' and any(v['tipo']=='EPP' for v in doc['metadatos'].get('vinculos_documentales',[])):
                    from services.planeacion_continuidad import trasladar_epp
                    doc=trasladar_epp(doc)
            prefix=base+'_'+tipo;_abrir(base,prefix,doc);u._persist(prefix);st.rerun()
        except (ValueError,PermissionError,RuntimeError) as exc:st.warning(str(exc))


def _herramientas(prefix,actor):
    from ui import planeacion as u
    doc=st.session_state[prefix+'_doc']
    herramienta=st.selectbox('Herramienta que necesito',['Elige una herramienta','Materiales y escaneos','Referentes oficiales','Evidencias del expediente','Conexiones y seguimiento','Organizar sesiones del equipo','Ideas adicionales con IA','Respaldo y versiones','Guía grupal XIX / XX','Ayuda paso a paso'],key=prefix+'_herramienta')
    if herramienta=='Materiales y escaneos':u._materiales(prefix,doc)
    elif herramienta=='Referentes oficiales':u._curriculo(prefix,doc)
    elif herramienta=='Evidencias del expediente':
        if st.button('Actualizar información del expediente',key=prefix+'_simple_fuentes'):
            try:s.refrescar_evidencias();u._open(prefix,s.preparar_contexto(doc));u._persist(prefix);st.rerun()
            except Exception:st.warning('No se confirmó la actualización. Tu edición se conserva.')
        for fuente in doc['metadatos'].get('fuentes',[]):
            with st.expander(fuente['referencia']+' · '+fuente['tipo']):
                st.write(fuente['texto']);st.caption('Ya se considera si su vínculo con estos alumnos está verificado.')
    elif herramienta=='Conexiones y seguimiento':
        from ui.planeacion_continuidad import panel
        panel(prefix,u._open,u._persist)
    elif herramienta=='Organizar sesiones del equipo':
        from ui.planeacion_equipo import panel
        panel(prefix,doc,u._persist,u._open,compact=True)
    elif herramienta=='Ideas adicionales con IA':u._ai(prefix,doc)
    elif herramienta=='Respaldo y versiones':_respaldo(prefix,doc)
    elif herramienta=='Guía grupal XIX / XX':
        _guia_adicional(prefix,doc)
    elif herramienta=='Ayuda paso a paso':
        from ui.planeacion_ayuda import panel
        panel(actor['area'])


def _respaldo(prefix,doc):
    from ui import planeacion as u
    st.download_button('Descargar respaldo editable',json.dumps(doc,ensure_ascii=False,indent=2),file_name='planeacion-'+doc['id']+'.json',mime='application/json',key=prefix+'_simple_backup')
    base=prefix.rsplit('_',1)[0]
    if st.session_state.get(prefix+'_pending'):
        st.warning('Descarga el respaldo antes de conciliar una edición pendiente con otra versión.')
        confirmar=st.checkbox('Ya respaldé mi edición y quiero conservarla para conciliar',key=prefix+'_simple_resguardar_confirm')
        if st.button('Conservar edición pendiente para conciliar',disabled=not confirmar,key=prefix+'_simple_resguardar'):
            u._resguardar_pendiente(prefix);st.rerun()
    for p in (base+'_individual',base+'_grupal'):
        for firma,resguardo in st.session_state.get(p+'_resguardos',{}).items():
            st.download_button('Descargar edición conservada para conciliar',json.dumps(resguardo,ensure_ascii=False),file_name='planeacion-conciliar-'+resguardo['id']+'.json',mime='application/json',key=p+'_simple_resguardo_'+firma)
    _recuperar(base)
    if st.toggle('Consultar versiones anteriores',key=prefix+'_simple_history'):
        for history in s.listar(True):
            if history['id']==doc['id']:
                st.download_button(history['guardado_en'][:19]+' · '+history['estado'],json.dumps(history,ensure_ascii=False),file_name=history['revision']+'.json',mime='application/json',key=prefix+'_simple_version_'+history['revision'])


def _recuperar(base):
    from ui import planeacion as u
    archivo=st.file_uploader('Recuperar un respaldo editable (.json)',type=['json'],key=base+'_simple_import')
    if archivo and st.button('Recuperar este respaldo',key=base+'_simple_restore'):
        try:
            if archivo.size>500000:raise ValueError('El respaldo es demasiado extenso.')
            recovered=json.loads(archivo.getvalue());s.autorizar(recovered,True)
            if recovered['cuenta']!=s.identidad()['cuenta']:raise PermissionError('El respaldo corresponde a otra cuenta.')
            actual=next((d for d in s.listar() if d['id']==recovered['id']),None)
            recovered['revision']=actual['revision'] if actual else ''
            from services.planeacion_modalidad import modalidad_documento
            prefix=base+'_'+modalidad_documento(recovered,s.padron_autorizado())
            _abrir(base,prefix,recovered);u._persist(prefix);st.rerun()
        except (ValueError,PermissionError,RuntimeError) as exc:st.warning(str(exc))


def _guia_adicional(prefix,doc):
    from ui import planeacion as u
    if doc['metadatos'].get('modalidad_planeacion')!='grupal':
        st.info('Estos complementos corresponden a la planeación grupal.');return
    guia=guia_grupal(doc);enlazada=bool(doc['metadatos'].get('guia_compartida'))
    st.caption('La tabla por alumno ya se edita en Revisar y enviar. Aquí están los complementos del mismo documento, no una nueva guía.')
    if enlazada:st.info('La guía está vinculada: sus aportaciones se editan en Trabajo colaborativo.')
    key=f'{prefix}_{st.session_state.get(prefix+"_generation",0)}_simple_anexos'
    maestro=st.text_input('Maestro de grupo regular',value=guia['maestro_grupo'],key=key+'_maestro',disabled=enlazada)
    as_rows=guia['as']
    if st.checkbox('Incluir guía AS (Anexo XX): solo aptitudes documentadas',value=bool(as_rows),key=key+'_as'):
        st.caption('Aptitudes y enriquecimiento requieren evidencia, no se asignan automáticamente.')
        defaults=as_rows or [{'Nombre alumno':a['Nombre del alumno'],**{h:'' for h in GUIA_XX[1:]}} for a in doc['datos']['Alumnos']]
        as_rows=st.data_editor(pd.DataFrame(defaults,columns=GUIA_XX),hide_index=True,disabled=True if enlazada else ['Nombre alumno'],key=key+'_xx').fillna('').to_dict('records')
    if st.button('Guardar complementos de la guía',key=key+'_save',disabled=enlazada):
        current=deepcopy(st.session_state[prefix+'_doc'])
        current['metadatos']['guia_grupal_manual']={**current['metadatos'].get('guia_grupal_manual',{}),'maestro_grupo':maestro,'filas':guia_grupal(current)['filas'],'as':as_rows}
        u._open(prefix,current);u._persist(prefix);st.rerun()


def _pendientes(doc):
    faltas=s.revisar(doc);resultado=[]
    for falta in faltas:
        if falta=='completar las celdas requeridas de aprendizajes':
            vacios=[i+1 for i,row in enumerate(doc['tablas']['aprendizajes']) if any(str(v or '').strip() for v in row.values()) and not str(row.get('Descriptor de logro','') or '').strip()]
            if vacios:
                resultado.extend('Falta el descriptor de logro en la fila '+str(i)+'.' for i in vacios)
        resultado.append(falta[:1].upper()+falta[1:].replace('_',' ')+'.')
    return faltas,resultado


def _editor(prefix,actor,paso):
    from ui import planeacion as u
    from ui.planeacion_formato import _tabla,_guia,_guia_texto
    doc=st.session_state[prefix+'_doc'];s.autorizar(doc,True)
    if doc['metadatos'].get('version_contexto')!=s.VERSION_CONTEXTO:
        u._open(prefix,s.preparar_contexto(doc));st.session_state[prefix+'_pending']=True;doc=st.session_state[prefix+'_doc']
    st.subheader(FORMATOS[doc['formato']]['titulo'])
    st.write(doc['datos']['Escuela regular']+' · '+doc['datos'].get('CCT',''))
    st.caption(', '.join(a['Nombre del alumno'] for a in doc['datos']['Alumnos'])+' · '+doc['datos']['Periodo'])
    u._autosave(prefix)
    if doc.get('observaciones_director'):st.info('Dirección: '+doc['observaciones_director'])
    if paso==PASOS[1]:
        st.subheader(PASOS[1]);st.caption('El expediente alimenta el borrador. La IA propone; tú decides y puedes editar todo.')
        if doc['metadatos'].get('fuentes_pendientes'):st.warning('Parte del expediente aún no pudo leerse. Comprueba las fuentes antes de solicitar propuestas.')
        if doc['formato']=='XXI':
            st.caption('Las NEE y BAP se precargan únicamente de una conclusión vigente de EPP. No se validan automáticamente.')
            u._text(prefix,'metadatos','fuente_iepp','Referencia del IEPP: fecha, folio o ubicación del informe')
            key=f'{prefix}_{st.session_state.get(prefix+"_generation",0)}_simple_iepp'
            st.checkbox('Las NEE fueron confirmadas en el IEPP.',value=bool(doc['metadatos'].get('NEE confirmadas desde IEPP')),key=key,on_change=u._field,args=(prefix,key,'metadatos','NEE confirmadas desde IEPP'))
            u._ai(prefix,doc)
        else:
            from ui.planeacion_generacion import panel_generacion
            panel_generacion(prefix,u._persist,u._open,compact=True)
        with st.expander('Añadir una necesidad documentada si hace falta evidencia'):
            u._text(prefix,'metadatos','necesidades_confirmadas','Necesidades y apoyos documentados (incluye la referencia de origen)')
    else:
        st.subheader(PASOS[2]);st.caption('Edita directamente en tu formato. Los resultados finales se registran después de trabajar con el alumno.')
        with st.expander('Datos generales del formato'):
            st.write(doc['datos'])
            if not doc['datos'].get('CCT'):u._text(prefix,'datos','CCT','CCT no registrado: verifica y completa')
            if doc['formato']=='XXI':
                for campo in ('Necesidades educativas específicas asociadas a','Maestro de grupo','Vigencia en cursos escolares'):u._text(prefix,'datos',campo)
        if doc['metadatos'].get('modalidad_planeacion')=='grupal':
            st.markdown('#### Actividades por alumno y área')
            guia=guia_grupal(doc);enlazada=doc['metadatos'].get('guia_compartida')
            key=f'{prefix}_{st.session_state.get(prefix+"_generation",0)}_simple_guia';bk=key+'_base'
            if bk not in st.session_state:st.session_state[bk]=deepcopy(guia['filas'])
            base=st.session_state[bk]
            st.data_editor(pd.DataFrame(base,columns=['ID_Alumno',*GUIA_XIX]).drop(columns='ID_Alumno'),hide_index=True,disabled=True if enlazada else ['Nombre alumno','Discapacidad o condición'],key=key,on_change=_guia,args=(prefix,key,base,u._persist))
            if enlazada:st.caption('Edita las aportaciones en Trabajo colaborativo y actualiza las conexiones.')
            else:
                with st.expander('Editar texto completo por alumno'):
                    for i,row in enumerate(guia_grupal(st.session_state[prefix+'_doc'])['filas']):
                        st.markdown('##### '+row['Nombre alumno'])
                        for campo in GUIA_XIX[2:]:
                            key=f'{prefix}_{st.session_state.get(prefix+"_generation",0)}_simple_guia_{i}_{campo}'
                            st.text_area(campo,value=str(row.get(campo,'') or ''),key=key,on_change=_guia_texto,args=(prefix,key,i,campo,u._persist,u._open))
        for tabla in FORMATOS[doc['formato']]['tablas']:
            if tabla=='evaluacion_final':
                with st.expander('Resultados al finalizar'):_tabla(prefix,tabla,u._persist,u._open)
            else:_tabla(prefix,tabla,u._persist,u._open)
        for campo in doc['textos']:u._text(prefix,'textos',campo)
    actual=st.session_state[prefix+'_doc'];faltas,avisos=_pendientes(actual)
    with st.expander('Antes de enviar · '+str(len(avisos))+' aspectos por completar'):
        for falta in avisos:st.write('• '+falta)
        if not faltas:st.success('Listo para revisar y enviar a Dirección.')
    # Solo la clase pública st-key del contenedor propio; no depende del DOM de
    # botones ni columnas internas. La barra acompaña el desplazamiento.
    st.html('<style>.st-key-'+prefix+'_acciones {position:sticky;bottom:0;z-index:10;background:var(--background-color,#fff);padding:0.65rem;border-top:1px solid #bbc8ca;} @media(max-width:640px){.st-key-'+prefix+'_acciones{padding:0.4rem;}}</style>')
    with st.container(horizontal=True,vertical_alignment='center',key=prefix+'_acciones'):
        if st.button('Guardar borrador',key=prefix+'_simple_save'):u._persist(prefix);st.rerun()
        if st.button('Ver PDF',key=prefix+'_simple_pdf'):
            st.session_state[prefix+'_mostrar_pdf']=True;st.rerun()
        if st.button('Enviar a Dirección',key=prefix+'_simple_send',disabled=bool(faltas)):u._persist(prefix,'ENVIADO');st.rerun()
    if st.session_state.get(prefix+'_mostrar_pdf'):
        if st.button('Volver a editar',key=prefix+'_simple_hidepdf'):
            st.session_state[prefix+'_mostrar_pdf']=False;st.rerun()
        try:
            pdf=u._pdf_sesion(prefix,actual);u._preview(prefix+'_simple_preview',pdf)
            st.download_button('Descargar PDF',pdf,file_name='planeacion-'+actual['id']+'.pdf',mime='application/pdf',key=prefix+'_simple_download')
        except Exception:st.warning('No se pudo preparar el PDF. Tu borrador se conserva.')
    if st.toggle('Más herramientas',key=prefix+'_mas_herramientas'):_herramientas(prefix,actor)


def pagina():
    from ui import planeacion as u
    actor=s.identidad();base=u._prefix()
    st.title('Mi planeación · '+actor['area'])
    st.caption('Elige alumnos, prepara tu propuesta y revisa el formato. Captura una vez; reutiliza lo que el equipo ya conoce.')
    labels=['Mi planeación','Trabajo colaborativo']+(['Revisión directiva'] if actor['director'] else [])
    tabs=st.tabs(labels)
    with tabs[0]:
        activo=st.session_state.get(base+'_activa')
        if not activo:
            # Compatibilidad con borradores abiertos antes de activar esta vista.
            prefixes=[p for p in (base+'_individual',base+'_grupal') if p+'_doc' in st.session_state]
            activo=next((p for p in prefixes if st.session_state.get(p+'_pending')),next(iter(prefixes),None))
            if activo:st.session_state[base+'_activa']=activo
        for p in (base+'_individual',base+'_grupal'):
            if p!=activo and st.session_state.get(p+'_pending') and p+'_doc' in st.session_state:
                st.warning('Hay otra edición pendiente de '+p.rsplit('_',1)[-1]+'. Se conserva sin reemplazarla.')
                st.download_button('Respaldar otra edición pendiente',json.dumps(st.session_state[p+'_doc'],ensure_ascii=False),file_name='planeacion-pendiente.json',key=p+'_simple_otro_respaldo')
                if st.button('Guardar otra edición pendiente',key=p+'_simple_otro_guardar'):u._persist(p);st.rerun()
        if activo and activo+'_doc' in st.session_state:
            if base+'_paso_pendiente' in st.session_state:
                st.session_state[base+'_paso']=st.session_state.pop(base+'_paso_pendiente')
            paso=st.segmented_control('Mi recorrido',PASOS,default=PASOS[1],key=base+'_paso') or PASOS[1]
            if paso==PASOS[0]:
                u._autosave(activo);_entrada(base,actor)
            else:_editor(activo,actor,paso)
        else:_entrada(base,actor)
    with tabs[1]:
        from ui.planeacion_colaboracion import panel
        panel(base+'_colaboracion')
    if actor['director']:
        with tabs[2]:u.direccion_panel()

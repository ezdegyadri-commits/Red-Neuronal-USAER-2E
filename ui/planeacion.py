"""Panel de trabajo y revisión. Claves de sesión separadas por cuenta."""
from copy import deepcopy
import hashlib
import json
import time
import pandas as pd
import streamlit as st
from services import planeacion as servicio
from services.planeacion_modelo import FORMATOS, revisar_redaccion
from ai.planeacion import proponer
from documents.planeacion import generar_pdf


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
    doc=deepcopy(st.session_state[prefix+'_doc']);doc['tablas'][name]=rows
    st.session_state[prefix+'_doc']=doc
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
    st.caption('Solo se envía el resumen que revises aquí; no se envían el padrón ni los archivos originales.')
    _text(prefix,'metadatos','resumen_educativo','Resumen educativo sin nombres, CURP, contactos ni identificadores')
    approved=st.checkbox('Revisé el resumen: no contiene datos que identifiquen a las personas.',key=prefix+'_consent')
    if st.button('Revisar con IA' if revision else 'Proponer actividades con IA',disabled=not approved,key=prefix+'_ai_button'):
        try:
            with st.spinner('Preparando propuestas…'):
                current=st.session_state[prefix+'_doc']
                st.session_state[prefix+'_ia']=proponer(current['metadatos'].get('resumen_educativo',''),doc['formato'],doc['datos']['Función'],revision)
        except (ValueError,RuntimeError) as exc:
            st.info(str(exc))
    result=st.session_state.get(prefix+'_ia')
    if not result:return
    st.write(result['observaciones'])
    for missing in result['faltantes']:st.caption(missing)
    for i,proposal in enumerate(result['propuestas']):
        with st.expander(proposal['objetivo'] or f'Propuesta {i+1}'):
            st.write(proposal)
            if not revision and st.button('Añadir al borrador',key=prefix+'_apply_'+str(i)):
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
    st.subheader(FORMATOS[doc['formato']]['titulo'])
    st.write(doc['datos']['Escuela regular']+' · '+doc['datos'].get('CCT',''))
    if not doc['datos'].get('CCT'):_text(prefix,'datos','CCT','CCT no registrado: verifica y completa')
    st.dataframe(pd.DataFrame(doc['datos']['Alumnos']),hide_index=True,use_container_width=True)
    st.caption('Autoguardado de cambios confirmados cada 15 segundos mientras trabajas. Antes de cerrar, pulsa Guardar borrador y confirma el guardado.')
    if doc.get('observaciones_director'):st.info('Dirección: '+doc['observaciones_director'])
    with st.expander('Evidencias del expediente y referente curricular'):
        if st.button('Consultar evidencia registrada',key=prefix+'_sources'):
            st.session_state[prefix+'_fuentes']=servicio.evidencias(doc)
            sources,_=st.session_state[prefix+'_fuentes']
            current=deepcopy(st.session_state[prefix+'_doc'])
            current['metadatos']['fuentes']=sources
            st.session_state[prefix+'_doc']=current
            _persist(prefix)
        if prefix+'_fuentes' in st.session_state:
            sources,failed=st.session_state[prefix+'_fuentes']
            if failed:st.info('Parte de la evidencia no está disponible. Puedes continuar sin modificar esos registros.')
            for source in sources:
                st.caption(source['referencia']+' · '+source['tipo']+' · '+source['fecha']+' · '+source['alcance'])
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
    for name,headers in FORMATOS[doc['formato']]['tablas'].items():
        st.markdown('#### '+name.replace('_',' ').capitalize())
        if name=='evaluacion_final':st.caption('Completar solo con resultados documentados al finalizar; no con predicciones.')
        key=f'{prefix}_{st.session_state.get(prefix+"_generation",0)}_table_{name}'
        basekey=key+'_base'
        if basekey not in st.session_state:
            st.session_state[basekey]=deepcopy(st.session_state[prefix+'_doc']['tablas'][name])
        base=st.session_state[basekey]
        st.data_editor(pd.DataFrame(base,columns=headers).fillna(''),num_rows='dynamic',hide_index=True,
              use_container_width=True,key=key,on_change=_table,args=(prefix,key,name,base))
    for field in doc['textos']:_text(prefix,'textos',field)
    with st.expander('Asistente de redacción y propuestas'):
        st.caption('Guía: el alumno identifica / relaciona / resuelve / explica… Evita verbos poco observables como “comprender”. Define evidencia y plazo.')
        for row in st.session_state[prefix+'_doc']['tablas'].get('aprendizajes',st.session_state[prefix+'_doc']['tablas'].get('necesidades',[])):
            descriptor=row.get('Descriptor de logro',row.get('Descriptor de Logro',''))
            if descriptor:
                for consejo in revisar_redaccion(descriptor):st.caption(consejo)
        _ai(prefix,st.session_state[prefix+'_doc'])
    current=st.session_state[prefix+'_doc']
    faltas=servicio.revisar(current)
    if faltas:st.caption('Por completar para enviar: '+'; '.join(faltas))
    left,middle,right=st.columns(3)
    if left.button('Guardar borrador',key=prefix+'_save'):
        _persist(prefix);st.rerun()
    if middle.button('Enviar a Dirección',key=prefix+'_send',disabled=bool(faltas)):
        _persist(prefix,'ENVIADO');st.rerun()
    if right.button('Preparar PDF',key=prefix+'_makepdf'):
        st.session_state[prefix+'_pdf']=generar_pdf(current)
    _autosave(prefix)
    st.download_button('Descargar respaldo editable',json.dumps(current,ensure_ascii=False,indent=2),file_name='planeacion-'+current['id']+'.json',mime='application/json',key=prefix+'_backup')
    if prefix+'_pdf' in st.session_state:
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
    st.write(doc['datos']);
    for name,rows in doc['tablas'].items():
        st.markdown('#### '+name.replace('_',' ').capitalize());st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)
    for name,value in doc['textos'].items():st.write(name+': '+value)
    st.caption('La validación se registra como revisión de Dirección; no coloca una firma manuscrita automática.')
    with st.expander('Detectar áreas de mejora con IA'):
        resumen=st.text_area('Resumen educativo y de la planeación, sin identificadores',key=prefix+'_ia_resumen_'+doc['id'])
        consent=st.checkbox('Revisé que el resumen no identifica personas.',key=prefix+'_ia_consent_'+doc['id'])
        if st.button('Analizar áreas de mejora',disabled=not consent,key=prefix+'_ia_revisar'):
            try:
                result=proponer(resumen,doc['formato'],doc['datos']['Función'],True)
                st.write(result['observaciones'])
                for item in result['faltantes']:st.caption(item)
            except (ValueError,RuntimeError) as exc:st.info(str(exc))
    observations=st.text_area('Áreas de mejora y observaciones de Dirección',value=doc.get('observaciones_director',''),key=prefix+'_notes_'+doc['revision'])
    for label,state in [('Devolver con observaciones','CON_OBSERVACIONES'),('Validar revisión','VALIDADO')]:
        if st.button(label,key=prefix+'_'+state):
            try:servicio.guardar(doc,state,observations);st.success('Revisión guardada.');st.rerun()
            except Exception as exc:st.warning(str(exc) if isinstance(exc,(ValueError,RuntimeError,PermissionError)) else 'No se confirmó la revisión. Vuelve a intentar.')
    st.download_button('PDF del documento',generar_pdf(doc),file_name='revision-'+doc['id']+'.pdf',mime='application/pdf',key=prefix+'_pdf_'+doc['revision'])


def planeacion_page():
    actor=servicio.identidad();prefix=_prefix()
    st.title('Planeación e intervención')
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
                    _open(prefix,servicio.nueva(formato,ids,int(ciclo),trimestre));_persist(prefix);st.rerun()
                except (ValueError,PermissionError) as exc:st.warning(str(exc))
        if prefix+'_doc' in st.session_state:_editor(prefix)

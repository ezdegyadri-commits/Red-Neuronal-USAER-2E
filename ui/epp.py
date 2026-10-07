"""Espacio colaborativo de EPP con guardado de cada campo confirmado."""
from copy import deepcopy
import hashlib
import json
import pandas as pd
import streamlit as st
from services import epp as s
from services.epp_modelo import AREAS, SECCIONES, campos, vacia, NEE, BAP, FAMILIA, HISTORIA, GENERALES, pendientes, conclusion_vigente
from services.materiales_planeacion import TIPOS, leer_material
from documents.epp import generar_pdf
from ai.epp import generar

def _save(prefix):
    try:
        doc=st.session_state[prefix+'_doc'];area=st.session_state[prefix+'_area']
        value=st.session_state[prefix+'_value'];revision=doc['partes'].get(area,{}).get('revision','')
        saved=s.guardar(doc,area,value,revision)
        doc['partes'][area]=saved
        st.session_state[prefix+'_value']=deepcopy(saved['contenido'])
        st.session_state.pop(prefix+'_error',None)
        st.session_state[prefix+'_saved']=saved['fecha']
    except Exception as exc:
        st.session_state[prefix+'_error']=str(exc) if isinstance(exc,(ValueError,PermissionError,RuntimeError)) else 'No se confirmó el guardado. Tu texto sigue en esta sesión: descarga el respaldo y vuelve a intentar.'

def _field(prefix,key,section,field):
    value=st.session_state[prefix+'_value']
    if section:value[section][field]=st.session_state[key]
    else:value[field]=st.session_state[key]
    if field!='validada':value['validada']=False
    _save(prefix)

def _table(prefix,key,name,base):
    rows=deepcopy(base);edits=st.session_state.get(key,{})
    for n,updates in edits.get('edited_rows',{}).items():rows[int(n)].update(updates)
    rows=[r for i,r in enumerate(rows) if i not in edits.get('deleted_rows',[])]
    rows.extend(edits.get('added_rows',[]))
    st.session_state[prefix+'_value'][name]=rows
    st.session_state[prefix+'_value']['validada']=False
    _save(prefix)

def _text(prefix,field,section=None,height=100):
    key=prefix+'_field_'+(section or '')+field
    value=st.session_state[prefix+'_value']
    text=value.get(section,{}).get(field,'') if section else value.get(field,'')
    labels={'instrumentos':'Instrumentos aplicados por mi área','fecha_aplicacion':'Fecha(s) de aplicación',
            'sintesis':'Síntesis de mi área y aspectos por confirmar'}
    st.text_area(labels.get(field,field),value=text,key=key,height=height,on_change=_field,args=(prefix,key,section,field))

def _grid(prefix,name,headers):
    base=deepcopy(st.session_state[prefix+'_value'].get(name,[]))
    key=prefix+'_table_'+name
    basekey=key+'_base'
    if basekey not in st.session_state:st.session_state[basekey]=base
    st.data_editor(pd.DataFrame(st.session_state[basekey],columns=headers).fillna(''),
        num_rows='dynamic',hide_index=True,use_container_width=True,key=key,
        on_change=_table,args=(prefix,key,name,st.session_state[basekey]))

def _abrir(prefix,doc,area):
    # Un espacio de edición por cuenta/documento/área; no reutiliza widgets de otro alumno.
    for k in list(st.session_state):
        if k.startswith(prefix+'_field_') or k.startswith(prefix+'_table_'):
            del st.session_state[k]
    st.session_state[prefix+'_doc']=deepcopy(doc)
    st.session_state[prefix+'_area']=area
    st.session_state[prefix+'_value']=deepcopy(doc['partes'].get(area,{}).get('contenido',vacia(area)))

def epp_page():
    a=s.actor()
    st.title('Evaluación psicopedagógica · Trabajo en equipo')
    st.caption('Un alumno, un informe. Cada profesional aporta y revisa sus hallazgos; la maestra de apoyo coordina la integración. Anexos XVII y XVIII del Manual USAER.')
    st.info('La IA ayuda a redactar a partir de hallazgos documentados. No aplica ni califica pruebas, ni emite diagnósticos clínicos. La conclusión educativa, NEE y apoyos requieren acuerdo del equipo.')
    prefix='epp_'+hashlib.sha256(a['cuenta'].encode()).hexdigest()[:12]
    try:docs=s.listar(True)
    except Exception:
        st.error('No fue posible consultar las EPP. No se modificó ningún documento.');return
    if s.puede_crear():
        with st.expander('Iniciar una EPP nueva'):
            frame=s.planes.padron_autorizado()
            if not frame.empty:
                labels={str(r['ID_Alumno']):str(r['Nombre_Completo'])+' · '+str(r.get('Nombre_Escuela','')) for r in frame.to_dict('records')}
                id_alumno=st.selectbox('Alumno de mi matrícula',list(labels),format_func=labels.get,key=prefix+'_nuevo_alumno')
                ciclo=st.text_input('Ciclo escolar','2026-2027',key=prefix+'_nuevo_ciclo')
                if st.button('Crear EPP y guardar',key=prefix+'_crear'):
                    try:s.crear(id_alumno,ciclo);st.rerun()
                    except Exception as exc:st.error(str(exc) if isinstance(exc,(ValueError,PermissionError)) else 'No se confirmó la creación; actualiza el listado antes de intentar de nuevo.')
    if st.button('Actualizar aportaciones del equipo',key=prefix+'_refresh'):
        from data.google import clear_cache
        clear_cache(s.HOJA)
        for k in list(st.session_state):
            if k.startswith(prefix+'_edit_'):del st.session_state[k]
        st.rerun()
    if not docs:st.caption('Aún no hay EPP en tus escuelas asignadas. La maestra de apoyo puede iniciar una.');return
    frame=s.planes.padron_autorizado()
    names={str(r['ID_Alumno']):str(r['Nombre_Completo'])+' · '+str(r.get('Nombre_Escuela','')) for r in frame.to_dict('records')}
    by_id={d['id']:d for d in docs}
    selected=st.selectbox('Informe compartido',list(by_id),format_func=lambda i:names.get(by_id[i]['alumno'],'')+' · '+by_id[i]['ciclo']+(' · Retirado' if by_id[i]['partes']['META']['estado']=='ELIMINADO' else ''),key=prefix+'_selected')
    doc=by_id[selected];s.autorizar(doc)
    if doc['partes']['META']['estado']=='ELIMINADO':
        st.warning('EPP retirada. Su historial se conserva.')
        if s.puede_crear() and doc['partes']['META']['cuenta']==a['cuenta'] and st.button('Recuperar EPP',key=prefix+'_restore'):
            s.retirar(doc,True);st.rerun()
        return
    st.subheader(names[doc['alumno']])
    status=[{'Área':area,'Profesional':doc['partes'].get(area,{}).get('autor','Por aportar'),
        'Estado':'Revisada' if doc['partes'].get(area,{}).get('contenido',{}).get('validada') else 'Borrador / pendiente'} for area in AREAS]
    st.dataframe(pd.DataFrame(status),hide_index=True,use_container_width=True)
    editable=[a['area']] if a['area'] in AREAS and not a['director'] else []
    if s.puede_crear() and doc['partes']['META']['cuenta']==a['cuenta']:editable.append('Conclusión')
    work,preview=st.columns([1.1,1],gap='large')
    with work:
        if editable:
            area=st.selectbox('Mis apartados',editable,key=prefix+'_area_select_'+selected)
            edit=prefix+'_edit_'+selected+'_'+area
            if edit+'_doc' not in st.session_state:_abrir(edit,doc,area)
            local=st.session_state[edit+'_doc']
            value=st.session_state[edit+'_value']
            st.caption('Los cambios de texto se guardan al salir del campo. Si falla la conexión, se muestra un aviso; conserva un respaldo antes de cerrar.')
            if area!='Conclusión':
                _text(edit,'instrumentos');_text(edit,'fecha_aplicacion')
                with st.expander('Cargar mis evaluaciones y revisar la lectura'):
                    st.caption('Hasta 32 MB; transcripción local. No se envían archivos originales a IA. Copia únicamente los hallazgos de este alumno, no cuadernillos completos ni pruebas con datos de terceros.')
                    upload=st.file_uploader('Evaluación de mi área',type=TIPOS,key=edit+'_upload')
                    if upload and st.button('Leer evaluación',key=edit+'_read'):
                        try:
                            read=leer_material(upload.name,upload.getvalue())
                            st.session_state[edit+'_transcripcion']=read['texto']
                            st.session_state[edit+'_avisos']=read['avisos']
                        except Exception as exc:st.warning(str(exc) if isinstance(exc,ValueError) else 'No se pudo transcribir. Usa un documento con texto o una imagen más clara.')
                    if edit+'_transcripcion' in st.session_state:
                        for warning in st.session_state.get(edit+'_avisos',[]):st.caption(warning)
                        trans=st.text_area('Hallazgos transcritos: revisa y corrige',value=st.session_state[edit+'_transcripcion'],max_chars=12000,height=180,key=edit+'_texto_upload')
                        reviewed=st.checkbox('Confirmo que estos hallazgos corresponden exclusivamente al alumno de esta EPP',key=edit+'_review_upload')
                        if st.button('Guardar evaluación revisada',disabled=not reviewed or not trans.strip(),key=edit+'_apply_upload'):
                            digest=hashlib.sha256(trans.encode()).hexdigest()
                            if not any(e['id']==digest for e in value['evaluaciones']):
                                value['evaluaciones'].append({'id':digest,'texto':trans,'nombre':'Evaluación de '+area})
                                value['validada']=False;_save(edit)
                                if edit+'_error' not in st.session_state:st.rerun()
                for ev in value['evaluaciones']:
                    with st.expander('Evaluación incorporada · '+ev['id'][:8]):
                        st.write(ev['texto'])
                        if st.button('Retirar esta evaluación de mi área',key=edit+'_remove_'+ev['id']):
                            value['evaluaciones']=[e for e in value['evaluaciones'] if e['id']!=ev['id']]
                            value['validada']=False;_save(edit);st.rerun()
            with st.expander('Preparar mis apartados con IA'):
                if st.button('Reunir expediente y evaluaciones',key=edit+'_context'):
                    try:
                        plan=s.contexto(doc)
                        st.session_state[edit+'_resumen']=s.resumen(doc,area,value,plan)
                        st.session_state.pop(edit+'_resumen_ia',None)
                    except Exception:st.error('No se pudo reunir el contexto completo. No se enviaron datos a IA; intenta actualizar.')
                if edit+'_resumen' in st.session_state:
                    text=st.text_area('Resumen educativo a enviar: retira datos que identifiquen a alumnos o familiares',value=st.session_state[edit+'_resumen'],height=200,max_chars=12000,key=edit+'_resumen_ia')
                    consent=st.checkbox('Revisé el resumen: sin nombres, CURP, domicilios ni contactos. Autorizo analizar estos hallazgos en Gemini.',key=edit+'_consent')
                    replace=st.checkbox('Sustituir los textos de mi área por un nuevo borrador; conservar evaluaciones e historial',key=edit+'_replace')
                    if st.button('Proponer conclusión interdisciplinaria' if area=='Conclusión' else 'Generar mis apartados',disabled=not consent or not replace,key=edit+'_generate'):
                        try:
                            from ai.planeacion import modelo_configurado
                            fingerprint=hashlib.sha256((doc['id']+area+modelo_configurado()+text).encode()).hexdigest()
                            if value.get('huella_ia')==fingerprint:
                                st.info('La propuesta para este resumen ya está guardada. Se conservan tus ediciones sin consumir otra solicitud de IA.')
                            else:
                                with st.spinner('Redactando con base en los hallazgos revisados…'):result=generar(text,area)
                                value['campos']=result['campos'];value['validada']=False
                                if area=='Conclusión':value['nee']=result['nee'];value['bap']=result['bap']
                                value['pendientes_ia']=result['faltantes'];value['huella_ia']=fingerprint;_save(edit)
                                if edit+'_error' not in st.session_state:_abrir(edit,st.session_state[edit+'_doc'],area);st.rerun()
                        except (ValueError,RuntimeError) as exc:st.warning(str(exc))
            if area=='Aprendizaje':
                with st.expander('Datos generales editables'):
                    for f in GENERALES:_text(edit,f,'generales')
                with st.expander('Historia escolar'):_grid(edit,'historia',HISTORIA)
            if area=='Trabajo Social':
                with st.expander('Composición familiar (permanece privada; no se incluye en el resumen automático de IA)'):_grid(edit,'familia',FAMILIA)
            if area=='Conclusión':
                for f in campos(area):_text(edit,f,'campos')
            else:
                for title,areas in SECCIONES.items():
                    if area not in areas:continue
                    with st.expander(title,expanded=title.startswith('5.')):
                        st.caption('Describe lo observado, fortalezas y apoyos que necesita. Si no se evaluó un aspecto, no inventes un resultado; registra por qué en la síntesis de tu área.')
                        for f in areas[area]:_text(edit,f,'campos')
            if area=='Conclusión':
                st.caption('NEE: Necesita + verbo + qué. BAP: barreras del contexto, no etiquetas del alumno. Completa apoyos, responsables y períodos acordados.')
                _grid(edit,'nee',NEE);_grid(edit,'bap',BAP)
            else:_text(edit,'sintesis',height=150)
            for p in value.get('pendientes_ia',[]):st.caption('Por confirmar: '+p)
            if st.button('Guardar mi borrador',key=edit+'_save'):_save(edit)
            if st.button('Confirmar revisión de mi área' if area!='Conclusión' else 'Validar conclusión acordada por el equipo',key=edit+'_validate'):
                if area=='Conclusión':
                    # Los campos de esta edición se conservan, pero se validan contra las áreas actuales.
                    actual=next(d for d in s.listar() if d['id']==doc['id'])
                    for other in AREAS:
                        if other in actual['partes']:st.session_state[edit+'_doc']['partes'][other]=deepcopy(actual['partes'][other])
                value['validada']=True;_save(edit)
            if edit+'_error' in st.session_state:st.error(st.session_state[edit+'_error'])
            elif edit+'_saved' in st.session_state:st.caption('Guardado confirmado: '+st.session_state[edit+'_saved'][:19])
            envelope={'informe':doc['id'],'area':area,'contenido':value}
            st.download_button('Respaldar mi edición antes de salir',json.dumps(envelope,ensure_ascii=False,indent=2),file_name='epp-'+doc['id'][:12]+'-'+area+'.json',mime='application/json',key=edit+'_backup')
            with st.expander('Recuperar mi respaldo editable'):
                backup=st.file_uploader('Respaldo de esta área (.json)',type=['json'],key=edit+'_restore_file')
                if backup and st.button('Recuperar y guardar mi área',key=edit+'_restore'):
                    try:
                        if backup.size>50000:raise ValueError('Respaldo demasiado extenso.')
                        from services.epp_modelo import validar_parte
                        envelope=json.loads(backup.getvalue())
                        if envelope.get('informe')!=doc['id'] or envelope.get('area')!=area:
                            raise ValueError('El respaldo corresponde a otro alumno, ciclo o área. No se incorporó su contenido.')
                        recovered=validar_parte(area,envelope['contenido'])
                        recovered['validada']=False
                        st.session_state[edit+'_value']=recovered;_save(edit)
                        if edit+'_error' not in st.session_state:_abrir(edit,st.session_state[edit+'_doc'],area);st.rerun()
                    except (ValueError,TypeError) as exc:st.warning(str(exc))
            with st.expander('Vaciar mis apartados (conservar historial)'):
                confirm=st.checkbox('Retirar mis textos y evaluaciones del informe actual',key=edit+'_clear_confirm')
                if st.button('Vaciar solamente mi área',disabled=not confirm,key=edit+'_clear'):
                    st.session_state[edit+'_value']=vacia(area);_save(edit)
                    if edit+'_error' not in st.session_state:_abrir(edit,st.session_state[edit+'_doc'],area);st.rerun()
            # La vista usa los campos de esta sesión y las aportaciones compartidas más recientes.
            doc=deepcopy(doc);doc['partes'][area]={**st.session_state[edit+'_doc']['partes'].get(area,{}), 'contenido':deepcopy(st.session_state[edit+'_value']),'fecha':st.session_state.get(edit+'_saved',''),'autor':a['nombre']}
            if edit+'_error' in st.session_state:doc['partes'][area]['contenido']['validada']=False
        else:st.caption('Puedes consultar el informe compartido. Cada integrante edita solamente su área.')
        if s.puede_crear() and doc['partes']['META']['cuenta']==a['cuenta']:
            with st.expander('Retirar EPP completa (recuperable)'):
                confirm=st.checkbox('Confirmo retirar el informe completo del listado vigente',key=prefix+'_retirar_confirm_'+selected)
                if st.button('Retirar EPP',disabled=not confirm,key=prefix+'_retirar_'+selected):s.retirar(doc);st.rerun()
    with preview:
        st.subheader('Informe único · Vista previa')
        for p in pendientes(doc):st.caption('Por completar: '+p)
        if not conclusion_vigente(doc):st.caption('Conclusión pendiente de revisión o hay hallazgos más recientes. No es un diagnóstico automático.')
        try:
            pdf=generar_pdf(doc,s.alumno_autorizado(doc['alumno']))
            from ui.planeacion import _preview
            _preview(prefix+'_preview_'+selected,pdf)
            st.download_button('Descargar informe único en PDF',pdf,file_name='EPP-'+doc['id'][:12]+'.pdf',mime='application/pdf',key=prefix+'_pdf_'+selected)
        except Exception:st.info('No se pudo actualizar el PDF. Los apartados guardados permanecen intactos.')

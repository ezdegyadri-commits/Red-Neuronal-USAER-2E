"""Edición acotada de aportaciones, con autoguardado y respaldo ante conflictos."""
from copy import deepcopy
import json
import time
import pandas as pd
import streamlit as st
from services import planeacion as s
from services.planeacion_colaboracion import COLUMNAS
from services.planeacion_modelo import FORMATOS
from services.planeacion_estabilidad import GuardadoPendiente


def _guardar(base,automatic=False):
    st.session_state[base+'_pending']=True
    if automatic and (time.monotonic()<st.session_state.get(base+'_retry_at',0) or time.monotonic()-st.session_state.get(base+'_intento',0)<st.session_state.get(base+'_intervalo',60)):return
    st.session_state[base+'_intento']=time.monotonic()
    try:
        saved=s.guardar_aportacion(st.session_state[base+'_doc'],st.session_state[base+'_filas'],st.session_state.get(base+'_obs',''))
        st.session_state[base+'_doc']=saved
        st.session_state[base+'_pending']=False
        if st.session_state.get(base+'_nonce'):
            st.session_state[base+'_ack']=st.session_state[base+'_nonce']
        st.session_state.pop(base+'_error',None)
        st.session_state.pop(base+'_guardado_diagnostico',None)
        st.session_state.pop(base+'_retry_at',None)
    except GuardadoPendiente as exc:
        from services.planeacion_guardado_estado import diagnostico
        st.session_state[base+'_guardado_diagnostico']=diagnostico(exc)
        st.session_state[base+'_retry_at']=time.monotonic()+exc.espera
        st.session_state[base+'_error']=str(exc)
    except Exception as exc:
        from services.planeacion_guardado_estado import diagnostico
        st.session_state[base+'_guardado_diagnostico']=diagnostico(exc)
        st.session_state[base+'_error']=str(exc) if isinstance(exc,(ValueError,PermissionError,RuntimeError)) else 'No se confirmó el guardado. Conserva el respaldo y vuelve a intentar.'


def _cambio(base,key,filas=None):
    if filas is not None:
        rows=deepcopy(filas)
        for i,campos in st.session_state.get(key,{}).get('edited_rows',{}).items():
            if 0<=int(i)<len(rows):rows[int(i)].update({k:str(v or '') for k,v in campos.items() if k in COLUMNAS[1:]})
        st.session_state[base+'_filas']=rows
    else:st.session_state[base+'_obs']=st.session_state[key]
    st.session_state[base+'_pending']=True
    _guardar(base,True)


@st.fragment(run_every=15)
def _estado(base):
    if st.session_state.get(base+'_pending'):
        _guardar(base,True)
        if not st.session_state.get(base+'_pending'):st.rerun(scope='app')
    if st.session_state.get(base+'_error'):st.warning(st.session_state[base+'_error'])
    elif st.session_state.get(base+'_pending'):st.caption('Aportación pendiente de autoguardado.')
    else:st.caption('Aportación recuperable: último guardado '+st.session_state[base+'_doc'].get('guardado_en','sin cambios')[:19])


def panel(prefix):
    actor=s.identidad()
    st.subheader('Continuar la planeación del equipo')
    st.caption('Elige tu escuela y grupo. Escribe en tu columna de la misma hoja iniciada por apoyo; las demás áreas conservan sus aportes.')
    if st.button('Actualizar planeaciones del equipo',key=prefix+'_actualizar_lista'):
        s.refrescar()
    try:
        from services.planeacion_grupo_unico import documentos
        docs=documentos(s.compartidos())
        # La defensa del selector tampoco puede ampliar asignaciones.
        for d in docs:s.autorizar(d,False)
    except Exception:
        st.warning('No se pudo consultar el trabajo del equipo. No se han alterado los documentos.');return
    # El documento abierto es un ID de esta sesión, no el primer resultado de
    # una lista que cambia cuando otro integrante guarda.
    abierto=st.session_state.get(prefix+'_abierto')
    if abierto:
        doc=next((d for d in docs if d['id']==abierto),None)
        if doc is None:
            raiz=next((d for d in docs if abierto in d['metadatos'].get('unificacion_grupal',{}).get('fuentes',{})),None)
            base_anterior=prefix+'_'+abierto+'_'+actor['area']
            if raiz and st.session_state.get(base_anterior+'_pending'):
                st.warning('Esta copia se reunió en la hoja única. Tu texto pendiente sigue protegido; descarga el respaldo antes de conciliarlo con la hoja del equipo.')
                st.download_button('Respaldar mi aporte pendiente',json.dumps({'filas':st.session_state.get(base_anterior+'_filas',[]),'observaciones':st.session_state.get(base_anterior+'_obs','')},ensure_ascii=False),file_name='aporte-pendiente.json',key=base_anterior+'_respaldo_union')
                return
            if raiz:
                doc=raiz;st.session_state[prefix+'_abierto']=raiz['id']
        if doc is None:
            st.warning('No se pudo recuperar la planeación abierta. No se abrirá otro grupo automáticamente.')
            return
        from services.planeacion_compartida import es_guia
        if es_guia(doc) and actor['area'] in ('Psicología','Comunicación','Trabajo Social'):
            from ui.planeacion_anexo_compartido import panel as hoja_compartida
            hoja_compartida(prefix,doc);return
        if es_guia(doc) and actor['area']=='Aprendizaje':
            try:s.autorizar(doc,True)
            except PermissionError:
                st.info('La maestra autora conserva la edición del formato. Puedes regresar a la lista sin modificarlo.')
                if st.button('Volver a la lista del equipo',key=prefix+'_volver_lectura'):
                    st.session_state.pop(prefix+'_abierto',None);st.rerun()
                return
            from ui import planeacion as u
            from ui.planeacion_papel import presentar
            base=prefix+'_autor_'+doc['id']
            if base+'_doc' not in st.session_state:u._open(base,doc)
            presentar(base,volver=lambda:st.session_state.pop(prefix+'_abierto',None));return
    from services.planeacion_matricula import clave_escuela
    frame=s.padron_autorizado()
    nombres={clave_escuela(r['ID_Escuela']):str(r.get('Nombre_Escuela',r['ID_Escuela'])) for r in frame.to_dict('records')}
    escuelas=list(nombres)
    if not escuelas:st.info('No hay escuelas con alumnos dentro de tu asignación actual.');return
    escuela=st.selectbox('Escuela del trabajo compartido',escuelas,format_func=nombres.get,key=prefix+'_escuela')
    docs=[d for d in docs if clave_escuela(d['datos']['ID_Escuela'])==escuela]
    from services.planeacion_compartida import etiqueta,etiqueta_selector,es_guia
    tipo=st.radio('Formato compartido',['Planeación grupal · Anexo XIX','Plan de intervención · Anexo XXI'],horizontal=True,key=prefix+'_tipo_compartido')
    docs=[d for d in docs if es_guia(d)] if tipo.startswith('Planeación grupal') else [d for d in docs if d['formato']=='XXI']
    if not docs:
        st.info('No hay formatos de este tipo disponibles en esta escuela. Si apoyo acaba de iniciar uno, confirma su guardado y pulsa «Actualizar planeaciones del equipo». No es necesario crear una copia ni enviarlo a Dirección para colaborar.');return
    from utils.escolar import grado_canonico,grupo_canonico
    from services.planeacion_ambito import etiqueta as grupos
    grados=['Todos']+sorted({grupos(d) for d in docs})
    grupo=st.selectbox('Grado y grupo',grados,key=prefix+'_grado_grupo')
    if grupo!='Todos':docs=[d for d in docs if grupos(d)==grupo]
    docs=sorted(docs,key=lambda d:d.get('guardado_en',''),reverse=True)
    st.caption(str(len(docs))+' formato(s) disponible(s). Se muestran también los borradores guardados por apoyo.')
    por_id={d['id']:d for d in docs}
    elegido=st.session_state.get(prefix+'_id')
    if elegido and elegido not in por_id:
        raiz=next((d['id'] for d in docs if elegido in d['metadatos'].get('unificacion_grupal',{}).get('fuentes',{})),None)
        if raiz:st.session_state[prefix+'_id']=raiz
    orden=sorted(por_id,key=lambda i:(grupos(por_id[i]),por_id[i]['datos']['Curso escolar'],str(por_id[i]['datos']['Trimestre'])))
    did=st.selectbox('Documento compartido · grado y periodo',orden,format_func=lambda i:etiqueta_selector(por_id[i]),key=prefix+'_id')
    doc=por_id[did]
    if doc['metadatos'].get('unificacion_grupal',{}).get('fuentes'):
        st.caption('Documento único del grupo: reúne el trabajo previo sin borrar sus documentos de origen. Todos los integrantes abren esta misma hoja.')
    st.caption('Último guardado: '+doc.get('guardado_en','por confirmar'))
    if es_guia(doc):
        from services.planeacion_modalidad import guia_grupal, GUIA_XIX
        guia = guia_grupal(doc)
        filas = guia.get('filas', [])
        st.markdown('### Guía de Planeación Grupal · Anexo XIX')
        c_m1, c_m2, c_m3 = st.columns(3)
        c_m1.markdown(f"**Maestro(a) de grupo:** {guia.get('maestro_grupo') or 'Por confirmar'}")
        c_m2.markdown(f"**Escuela:** {doc['datos'].get('Escuela regular','')}")
        c_m3.markdown(f"**Grado y grupo:** {grupos(doc)}")
        if filas:
            df_g = pd.DataFrame(filas)
            cols = [c for c in GUIA_XIX if c in df_g.columns]
            st.dataframe(df_g[cols], hide_index=True, use_container_width=True)
            st.caption('ℹ️ Esta tabla refleja lo capturado por la Maestra de Apoyo (columna Aprendizaje, situación inicial, derivación) y las aportaciones de cada especialista.')
        with st.expander('👥 Gestión de alumnos en esta planeación grupal (individuales / grupales)'):
            st.caption('Si en este grado hay alumnos que se atenderán de forma individual (con diferentes necesidades y descriptores), puedes excluirlos de la planeación grupal de las áreas.')
            alumnos_actuales = doc['datos']['Alumnos']
            if alumnos_actuales:
                c_ex1, c_ex2 = st.columns([2, 1])
                nom_dict = {str(a['ID_Alumno']): f"{a['Nombre del alumno']} ({a.get('Condición','')})" for a in alumnos_actuales}
                sel_excluir = c_ex1.selectbox('Alumno para trabajar individualmente', list(nom_dict), format_func=nom_dict.get, key=prefix+'_sel_excluir')
                if c_ex2.button('Quitar del Anexo XIX grupal', key=prefix+'_btn_excluir'):
                    from services.planeacion_compartida import excluir_alumno_grupal
                    doc_mod = excluir_alumno_grupal(doc, sel_excluir)
                    s.guardar(doc_mod, doc_mod.get('estado', 'BORRADOR'))
                    st.success(f'Alumno {nom_dict.get(sel_excluir)} retirado de la planeación grupal. Se conserva para su planeación individual.')
                    s.refrescar()
                    st.rerun()
            excluidos_ids = doc.get('metadatos', {}).get('alumnos_excluidos_grupal', [])
            if excluidos_ids:
                st.write(f'**Alumnos actualmente excluidos del Anexo XIX grupal ({len(excluidos_ids)}):**')
                c_res1, c_res2 = st.columns([2, 1])
                sel_restaurar = c_res1.selectbox('Alumno para reintegrar al grupo', excluidos_ids, key=prefix+'_sel_restaurar')
                if c_res2.button('Reintegrar a planeación grupal', key=prefix+'_btn_restaurar'):
                    from services.planeacion_compartida import restaurar_alumno_grupal
                    doc_mod = restaurar_alumno_grupal(doc, sel_restaurar)
                    s.guardar(doc_mod, doc_mod.get('estado', 'BORRADOR'))
                    st.success('Alumno reintegrado a la planeación grupal.')
                    s.refrescar()
                    st.rerun()
        if not actor['director']:
            c_op1,c_op2=st.columns([1,1])
            if c_op1.button('Abrir Anexo XIX compartido en hoja completa',key=prefix+'_abrir'):
                st.session_state[prefix+'_abierto']=did;st.rerun()
            c_op2.caption('O edita tus aportaciones directamente en la tabla ágil de abajo:')
    for area,aporte in doc['metadatos'].get('aportaciones_equipo',{}).items():
        with st.expander(area+' · '+aporte['autor']):
            st.dataframe(pd.DataFrame(aporte['filas']),hide_index=True)
            st.write(aporte['observaciones']);st.caption('Aportación por revisar · '+aporte['fecha'][:19])
    if actor['director']:st.caption('Dirección conserva la revisión del documento integrado.');return
    base=prefix+'_'+did+'_'+actor['area']
    if base+'_doc' not in st.session_state or (not st.session_state.get(base+'_pending') and doc.get('revision')!=st.session_state.get(base+'_doc',{}).get('revision')):
        aporte=doc['metadatos'].get('aportaciones_equipo',{}).get(actor['area'],{})
        rows=aporte.get('filas',[])
        for a in doc['datos']['Alumnos']:
            if not any(r['ID_Alumno']==a['ID_Alumno'] for r in rows):rows=rows+[{k:a['ID_Alumno'] if k=='ID_Alumno' else '' for k in COLUMNAS}]
        st.session_state[base+'_doc']=deepcopy(doc);st.session_state[base+'_filas']=deepcopy(rows)
        st.session_state[base+'_original']=deepcopy(rows);st.session_state[base+'_obs']=aporte.get('observaciones','')
    st.caption('Solo editas tu aportación. Confirma cada celda; los cambios se agrupan para guardar aproximadamente cada minuto. Guarda y verifica antes de cerrar.')
    st.data_editor(pd.DataFrame(st.session_state[base+'_original'],columns=COLUMNAS),disabled=['ID_Alumno'],hide_index=True,
        column_config={'Contexto':st.column_config.SelectboxColumn(options=FORMATOS[doc['formato']]['contextos'])},
        key=base+'_editor',on_change=_cambio,args=(base,base+'_editor',st.session_state[base+'_original']))
    st.text_area('Observaciones de mi área',value=st.session_state[base+'_obs'],key=base+'_notas',on_change=_cambio,args=(base,base+'_notas'))
    if st.button('Guardar mi aportación',key=base+'_save'):_guardar(base)
    if st.button('Actualizar documento conservando mi aportación',key=base+'_refresh'):
        s.refrescar()
        try:
            reciente=next(d for d in s.compartidos() if d['id']==did)
            anterior=st.session_state[base+'_doc']['metadatos'].get('aportaciones_equipo',{}).get(actor['area'])
            nueva=reciente['metadatos'].get('aportaciones_equipo',{}).get(actor['area'])
            if anterior!=nueva:st.warning('Otra sesión cambió tu área. Conserva el respaldo antes de conciliar las versiones; no se sobrescribirá.')
            else:
                st.session_state[base+'_doc']=reciente
                if st.session_state.get(base+'_pending'):_guardar(base)
                st.rerun()
        except Exception:st.warning('No se pudo actualizar. Tu aportación local se conserva.')
    _estado(base)
    st.download_button('Respaldo de mi aportación',json.dumps({'documento':did,'area':actor['area'],'filas':st.session_state[base+'_filas'],'observaciones':st.session_state[base+'_obs']},ensure_ascii=False),
        file_name='aporte-'+did+'.json',mime='application/json',key=base+'_backup')

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
    if automatic and (time.monotonic()<st.session_state.get(base+'_retry_at',0) or time.monotonic()-st.session_state.get(base+'_intento',0)<60):return
    st.session_state[base+'_intento']=time.monotonic()
    try:
        saved=s.guardar_aportacion(st.session_state[base+'_doc'],st.session_state[base+'_filas'],st.session_state.get(base+'_obs',''))
        st.session_state[base+'_doc']=saved
        st.session_state[base+'_pending']=False
        st.session_state.pop(base+'_error',None)
        st.session_state.pop(base+'_retry_at',None)
    except GuardadoPendiente as exc:
        st.session_state[base+'_retry_at']=time.monotonic()+exc.espera
        st.session_state[base+'_error']=str(exc)
    except Exception as exc:
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
    st.subheader('Trabajo colaborativo · PI y guía grupal')
    st.caption('Un documento compartido: cada profesional aporta desde su área. La coordinación integra lo acordado; las trimestrales conservan su formato propio.')
    try:docs=s.compartidos()
    except Exception:
        st.warning('No se pudo consultar el trabajo del equipo. No se han alterado los documentos.');return
    from services.planeacion_matricula import clave_escuela
    frame=s.padron_autorizado()
    nombres={clave_escuela(r['ID_Escuela']):str(r.get('Nombre_Escuela',r['ID_Escuela'])) for r in frame.to_dict('records')}
    escuelas=list(nombres)
    if not escuelas:st.info('No hay escuelas con alumnos dentro de tu asignación actual.');return
    escuela=st.selectbox('Escuela del trabajo compartido',escuelas,format_func=nombres.get,key=prefix+'_escuela')
    docs=[d for d in docs if clave_escuela(d['datos']['ID_Escuela'])==escuela]
    if not docs:st.info('Esta escuela aún no tiene un PI o Anexo XIX compartido. La maestra de apoyo inicia el formato.');return
    por_id={d['id']:d for d in docs}
    from services.planeacion_compartida import etiqueta,es_guia
    did=st.selectbox('Documento compartido · grado, grupo y fecha/hora',list(por_id),format_func=lambda i:etiqueta(por_id[i]),key=prefix+'_id')
    doc=por_id[did]
    if es_guia(doc) and actor['area'] in ('Psicología','Comunicación','Trabajo Social'):
        if st.session_state.get(prefix+'_cerrado')==did:
            if st.button('Abrir Anexo XIX compartido',key=prefix+'_reabrir'):st.session_state.pop(prefix+'_cerrado',None);st.rerun()
            return
        from ui.planeacion_anexo_compartido import panel as hoja_compartida
        hoja_compartida(prefix,doc);return
    for area,aporte in doc['metadatos'].get('aportaciones_equipo',{}).items():
        with st.expander(area+' · '+aporte['autor']):
            st.dataframe(pd.DataFrame(aporte['filas']),hide_index=True)
            st.write(aporte['observaciones']);st.caption('Aportación por revisar · '+aporte['fecha'][:19])
    if actor['director']:st.caption('Dirección conserva la revisión del documento integrado.');return
    base=prefix+'_'+did+'_'+actor['area']
    if base+'_doc' not in st.session_state:
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

"""Formato de junta con captura única y recuperación por docente y escuela."""
from datetime import date
from hashlib import sha256
import json
import time
import pandas as pd
import streamlit as st
from services import metas_personales as s


def _guardar_pendiente(key,manual=False):
    if not st.session_state.get(key+'_pending'):return True
    if not manual and (st.session_state.get(key+'_requiere_accion') or time.monotonic()-st.session_state.get(key+'_ultimo_intento',0)<15):return False
    captura=st.session_state[key+'_borrador']
    if captura.get('Cuenta')!=s.identidad()['cuenta']:raise PermissionError('La captura no corresponde a la cuenta activa.')
    st.session_state[key+'_ultimo_intento']=time.monotonic()
    try:
        doc=st.session_state.get(key+'_doc',{})
        nuevo=s.guardar(captura['ID_Escuela'],captura['Fecha_Sesion'],captura['Filas'],doc.get('Revision',''))
        st.session_state[key+'_doc']=nuevo;st.session_state[key+'_pending']=False
        st.session_state.pop(key+'_error',None);st.session_state.pop(key+'_requiere_accion',None)
        return True
    except Exception as exc:
        st.session_state[key+'_error']=str(exc) if isinstance(exc,(ValueError,PermissionError,RuntimeError)) else 'La base central no confirmó el guardado. Puedes reintentar o descargar el respaldo.'
        st.session_state[key+'_requiere_accion']=isinstance(exc,(ValueError,PermissionError,RuntimeError))
        return False


@st.fragment(run_every=15)
def _estado_guardado(key):
    _guardar_pendiente(key)
    if st.session_state.get(key+'_pending'):
        st.warning(st.session_state.get(key+'_error','Metas pendientes de envío agrupado. Conserva esta pestaña abierta o confirma con Guardar metas.'))
    elif st.session_state.get(key+'_doc'):
        st.caption('Guardado confirmado · '+st.session_state[key+'_doc'].get('Guardado_En',''))
    else:st.caption('Formato listo para comenzar.')


def proteger_salida(key):
    """No descartar metas pendientes al cerrar una sesión compartida."""
    cuenta=str(st.session_state.get('usuario',''))
    keys=[k[:-8] for k,v in list(st.session_state.items()) if k.startswith('metas_') and k.endswith('_pending') and v and st.session_state.get(k[:-8]+'_borrador',{}).get('Cuenta')==cuenta]
    if not keys:return True
    st.warning('Hay metas personales sin confirmación central. Guarda o descarga cada respaldo antes de cerrar.')
    for p in keys:
        st.download_button('Respaldar metas pendientes',json.dumps(st.session_state[p+'_borrador'],ensure_ascii=False,indent=2),file_name='metas-pendientes.json',mime='application/json',key=key+'_'+p+'_respaldo')
    if st.button('Reintentar guardado de metas',key=key+'_reintentar_metas'):
        resultados=[_guardar_pendiente(p,manual=True) for p in keys]
        if all(resultados):st.success('Metas guardadas. Ya puedes cerrar sesión.');return True
    return st.checkbox('Ya descargué los respaldos de metas; continuar al cierre',key=key+'_metas_respaldadas')


def page():
    st.header('Metas personales')
    st.caption('Segunda junta académica · apoyos y ajustes razonables. El formato conserva Alumno, Metas y Recursos necesarios.')
    try:
        actor=s.identidad();frame=s.planes.padron_autorizado().fillna('')
        escuelas={str(r['ID_Escuela']):str(r.get('Nombre_Escuela','') or r['ID_Escuela']) for r in frame.to_dict('records')}
        if not escuelas:st.info('No hay alumnos disponibles en tu asignación.');return
        c1,c2=st.columns([2,1])
        escuela=c1.selectbox('Escuela asignada',list(escuelas),format_func=escuelas.get,key='metas_escuela')
        fecha=c2.date_input('Fecha de la sesión',value=date(2026,10,23),format='DD/MM/YYYY',key='metas_fecha')
        st.write('Nombre del docente: '+actor['nombre'])
        key='metas_'+sha256(json.dumps([actor['cuenta'],escuela,str(fecha)]).encode()).hexdigest()[:20]
        if key+'_doc' not in st.session_state:
            st.session_state[key+'_doc']=s.recuperar(escuela,fecha) or {}
        guardado=st.session_state[key+'_doc']
        rows=s.matricula(escuela)
        mapa={str(r['ID_Alumno']):str(r['Nombre_Completo'])+' · '+str(r.get('Grado',''))+' '+str(r.get('Grupo','')) for r in rows}
        for r in guardado.get('Filas',[]):mapa.setdefault(r['ID_Alumno'],r['Alumno']+' · antecedente conservado')
        # Desambiguar homónimos sin usar el nombre como identidad persistida.
        labels={aid:(label+' · '+aid[-6:] if list(mapa.values()).count(label)>1 else label) for aid,label in mapa.items()}
        if key+'_base_editor' not in st.session_state:
            st.session_state[key+'_labels']=labels.copy()
            st.session_state[key+'_base_editor']=[{'Alumno':labels[r['ID_Alumno']],'Metas':r['Metas'],'Recursos necesarios':r['Recursos necesarios']} for r in guardado.get('Filas',[])] or [{'Alumno':None,'Metas':'','Recursos necesarios':''} for _ in range(8)]
        labels={**labels,**st.session_state[key+'_labels']};porlabel={v:k for k,v in labels.items()}
        # Streamlit limpia widgets al cambiar de módulo o escuela. Recuperar
        # la captura pendiente, no la base original, al reconstruir el editor.
        if key+'_editor' not in st.session_state and key+'_borrador' in st.session_state:
            st.session_state[key+'_base_editor']=[{'Alumno':labels.get(r['ID_Alumno']),'Metas':r['Metas'],'Recursos necesarios':r['Recursos necesarios']} for r in st.session_state[key+'_borrador']['Filas']] or [{'Alumno':None,'Metas':'','Recursos necesarios':''} for _ in range(8)]
        st.caption('Elige al alumno y escribe sus metas y recursos. El autoguardado agrupa los cambios cada 15 segundos; Guardar metas confirma de inmediato. Puedes añadir o retirar renglones; las versiones previas se conservan.')
        editado=st.data_editor(pd.DataFrame(st.session_state[key+'_base_editor']),hide_index=True,num_rows='dynamic',use_container_width=True,key=key+'_editor',
            column_config={'Alumno':st.column_config.SelectboxColumn('Alumno',options=list(porlabel),required=True),
                'Metas':st.column_config.TextColumn('Metas',max_chars=1500,width='large'),
                'Recursos necesarios':st.column_config.TextColumn('Recursos necesarios',max_chars=1000,width='large')})
        filas=[{'ID_Alumno':porlabel.get(str(r['Alumno'] or ''),''),'Metas':str(r['Metas'] or '').strip(),'Recursos necesarios':str(r['Recursos necesarios'] or '').strip()}
               for r in editado.fillna('').to_dict('records') if any(str(v or '').strip() for v in r.values())]
        captura={'Cuenta':actor['cuenta'],'Escuela':escuelas[escuela],'Docente':actor['nombre'],'ID_Escuela':escuela,'Fecha_Sesion':str(fecha),'Filas':filas}
        if st.session_state.get(key+'_borrador')!=captura:st.session_state.pop(key+'_requiere_accion',None)
        st.session_state[key+'_borrador']=captura
        anterior=[{k:r.get(k,'') for k in ('ID_Alumno','Metas','Recursos necesarios')} for r in guardado.get('Filas',[])]
        pendiente=filas!=anterior
        st.session_state[key+'_pending']=pendiente
        manual=st.button('Guardar metas',type='primary',key=key+'_guardar')
        if manual:
            if not pendiente and not guardado:st.session_state[key+'_pending']=True
            _guardar_pendiente(key,manual=True)
        _estado_guardado(key)
        respaldo=st.session_state[key+'_borrador']
        st.download_button('Descargar respaldo de mi captura',json.dumps(respaldo,ensure_ascii=False,indent=2),file_name='metas-personales-'+str(fecha)+'.json',mime='application/json',key=key+'_respaldo')
        with st.expander('Imprimir o descargar el formato'):
            if st.button('Preparar PDF',key=key+'_preparar_pdf'):
                from documents.metas_personales import generar_pdf
                printable={**respaldo,'Filas':[{**r,'Alumno':labels.get(r['ID_Alumno'],'Seleccionar alumno')} for r in filas]}
                st.session_state[key+'_pdf']=(json.dumps(respaldo,sort_keys=True),generar_pdf(printable))
            pdf=st.session_state.get(key+'_pdf')
            if pdf and pdf[0]==json.dumps(respaldo,sort_keys=True):
                st.download_button('Descargar PDF de mis metas',pdf[1],file_name='metas-personales-'+str(fecha)+'.pdf',mime='application/pdf',key=key+'_descargar_pdf')
            st.caption('El PDF contiene la captura actual. Descargarlo no equivale a confirmar el guardado central. No se añaden firmas ni sellos automáticamente.')
    except (ValueError,PermissionError,RuntimeError) as exc:st.warning(str(exc))
    except Exception:st.warning('No se pudo consultar el formato de metas. No se reemplazó tu captura ni se borró información.')

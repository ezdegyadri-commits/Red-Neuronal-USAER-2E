"""Descarga diferida y eliminación versionada del borrador seleccionado."""
import json
import streamlit as st
from services import planeacion as s


def eliminar_directo(key,doc,al_eliminar):
    try:actor=s.identidad()
    except PermissionError:return
    if doc['estado']!='BORRADOR' or doc['cuenta']!=actor['cuenta']:return
    if st.button('Eliminar borrador',key=key+'_eliminar_directo'):st.session_state[key+'_confirmar_directo']=True
    if st.session_state.get(key+'_confirmar_directo'):
        st.caption('Se enviará a la papelera. Las versiones y aportes guardados se conservarán.')
        a,b=st.columns(2)
        if a.button('Confirmar eliminación',key=key+'_si_directo'):
            try:
                s.eliminar_borrador(doc);st.session_state.pop(key+'_confirmar_directo',None)
                al_eliminar();st.rerun()
            except (ValueError,PermissionError,RuntimeError) as exc:st.warning(str(exc))
        if b.button('Conservar',key=key+'_no_directo'):
            st.session_state.pop(key+'_confirmar_directo',None);st.rerun()


def controles(key,doc,pdf_provider,al_eliminar):
    from copy import deepcopy
    copia=deepcopy(doc)
    from documents.planeacion_papel import preparar_descarga
    descarga=preparar_descarga(copia)
    with st.container(horizontal=True):
        st.download_button('Descargar borrador PDF',data=descarga,file_name='planeacion-'+doc['id']+'.pdf',mime='application/pdf',key=key+'_pdf',on_click='ignore')
        st.download_button('Descargar borrador editable',data=json.dumps(copia,ensure_ascii=False,indent=2),file_name='planeacion-'+doc['id']+'.json',mime='application/json',key=key+'_editable',on_click='ignore')
        if doc['estado']=='BORRADOR' and doc['cuenta']==s.identidad()['cuenta'] and st.button('Eliminar borrador',key=key+'_eliminar'):
            st.session_state[key+'_confirmar']=True
    if st.session_state.get(key+'_confirmar'):
        st.caption('Se retirará de tus borradores. Sus versiones guardadas se conservan en el historial.')
        a,b=st.columns(2)
        if a.button('Confirmar eliminación del borrador',key=key+'_confirmado'):
            try:
                s.eliminar_borrador(doc);st.session_state.pop(key+'_confirmar',None)
                al_eliminar();st.rerun()
            except (ValueError,PermissionError,RuntimeError) as exc:st.warning(str(exc))
        if b.button('Conservar borrador',key=key+'_cancelar'):st.session_state.pop(key+'_confirmar',None);st.rerun()


def cerrar_editor(base,prefix):
    for key in list(st.session_state):
        if key.startswith(prefix+'_'):st.session_state.pop(key,None)
    st.session_state.pop(base+'_activa',None)
    st.session_state[base+'_viva_entrada']=True


def papelera(base):
    if not st.toggle('Mostrar borradores eliminados',key=base+'_papelera'):return
    try:
        actuales={d['id']:d for d in s.listar(True)}
        retirados={i:d for i,d in actuales.items() if d['metadatos'].get('borrador_eliminado') and d['cuenta']==s.identidad()['cuenta']}
        if not retirados:st.caption('No hay borradores eliminados.');return
        did=st.selectbox('Borrador para recuperar',list(retirados),format_func=lambda i:retirados[i]['datos']['Escuela regular']+' · '+retirados[i]['datos']['Periodo'],key=base+'_recuperar_borrador')
        if st.button('Restaurar borrador',key=base+'_restaurar_borrador'):
            s.restaurar_borrador(retirados[did]);st.rerun()
    except (ValueError,PermissionError,RuntimeError) as exc:st.warning(str(exc))

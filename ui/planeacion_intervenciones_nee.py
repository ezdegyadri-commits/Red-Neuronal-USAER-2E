"""Misma intervención por NEE en las distintas vistas, sin otra persistencia."""
import streamlit as st
from services import planeacion_intervenciones_nee as servicio


def seleccionar(doc,key):
    catalogo=servicio.catalogo(doc)
    if not catalogo:return []
    nombres={str(a['ID_Alumno']):a.get('Nombre del alumno',a['ID_Alumno']) for a in doc['datos']['Alumnos']}
    porid={r['id']:r for r in catalogo}
    st.caption('Elige una o varias NEE. Cada una tendrá sus propios objetivos, apoyos, actividades y evaluación; no se mezclan en una sola celda.')
    return st.multiselect('NEE para trabajar con apartados propios',list(porid),
        format_func=lambda rid:nombres[porid[rid]['alumno_id']]+' · '+porid[rid]['texto'],key=key)


def panel(prefix,persist,abrir):
    doc=st.session_state[prefix+'_doc']
    if not servicio.aplica(doc):return
    selected=seleccionar(doc,prefix+'_seleccion_nee_por_bloque')
    if selected and st.button('Agregar NEE y sus apartados',key=prefix+'_agregar_bloques_nee'):
        try:
            nuevo=servicio.incorporar(doc,selected);abrir(prefix,nuevo);persist(prefix);st.rerun()
        except (ValueError,PermissionError,RuntimeError) as exc:st.warning(str(exc))
    for i,b in enumerate(servicio.bloques(doc),1):
        with st.expander('Intervención NEE '+str(i)+' · '+b['campos']['NEE'],expanded=True):
            st.caption('Fuente: '+b['origen'].get('origen','')+' · '+b['origen'].get('referencia','')+'. La BAP y la NEE se conservan como conceptos distintos.')
            cols=st.columns(2)
            for j,campo in enumerate(servicio.CAMPOS):
                key=prefix+'_nee_'+b['id']+'_'+campo
                def editar(k=key,bid=b['id'],c=campo):
                    st.session_state[prefix+'_doc']=servicio.editar(st.session_state[prefix+'_doc'],bid,c,st.session_state[k])
                    persist(prefix,automatic=True)
                with cols[j%2]:st.text_area(servicio.etiqueta(doc,campo),value=b['campos'].get(campo,''),key=key,on_change=editar)

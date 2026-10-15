"""Accesos de corrección que editan el mismo documento de la hoja."""
import streamlit as st
from services.planeacion_revision import pendientes


def panel(prefix):
    from ui import planeacion as u
    from services import planeacion_papel as papel
    doc=st.session_state[prefix+'_doc'];faltas,items=pendientes(doc)
    for i,item in enumerate(items):
        if st.button(item['mensaje']+' → Corregir',key=prefix+'_revision_'+str(i)):
            st.session_state[prefix+'_correccion']=item
    item=st.session_state.get(prefix+'_correccion')
    if item:
        spec=papel.hoja(doc)
        celda=next((c for c in spec['cells'].values() if c['target']==item['target']),None) if item.get('target') else None
        if celda:
            key=prefix+'_correccion_texto_'+spec['huella'][:12]
            value=st.text_area(item['mensaje'],value=celda['value'],key=key)
            if st.button('Guardar corrección en mi formato',key=prefix+'_correccion_guardar'):
                try:
                    nuevo=papel.aplicar(doc,{'documento':doc['id'],'huella':spec['huella'],'cambios':{celda['id']:value},'accion':'guardar'})
                    u._open(prefix,nuevo);u._persist(prefix);st.session_state.pop(prefix+'_correccion',None);st.rerun()
                except (ValueError,PermissionError,RuntimeError) as exc:st.warning(str(exc))
        elif item['panel'].startswith('tabla:'):
            from ui.planeacion_formato import _tabla
            from services.planeacion_formato import nueva_fila
            tabla=item['panel'].split(':',1)[1]
            if st.button('Añadir fila para completar',key=prefix+'_correccion_nueva'):
                u._open(prefix,nueva_fila(doc,tabla));u._persist(prefix);st.rerun()
            _tabla(prefix,tabla,u._persist,u._open)
        elif item['panel']=='datos':u._text(prefix,'datos','CCT','CCT de la escuela')
        else:
            from ui.planeacion_equipo import panel as equipo
            equipo(prefix,doc,u._persist,u._open,compact=True)
    if not faltas:st.success('El formato está listo para tu revisión final.')

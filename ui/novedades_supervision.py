"""Novedades de la ATP: consulta amable y privada para Dirección."""
import hashlib
import streamlit as st
from services import novedades_supervision as s

def novedades_page():
    try:s.autorizar()
    except PermissionError:
        st.warning('Este apartado es exclusivo de Dirección.');return
    st.title('Novedades de supervisión')
    st.caption('Documentos, acuerdos, actividades y orientaciones de la ATP. No modifican automáticamente los horarios ni las planeaciones del equipo.')
    try:docs,fuente=s.cargar()
    except Exception:
        st.info('No fue posible consultar las novedades. Los demás módulos y tus borradores se conservan. Intenta actualizar más tarde.');return
    if st.button('Actualizar novedades',key='supervision_actualizar'):
        s.refrescar();st.rerun()
    enlace=s.enlace_seguro(fuente.get('Enlace',''))
    if enlace:st.link_button('Abrir carpeta de supervisión',enlace)
    st.caption('Última sincronización: '+s.fecha_local(fuente.get('Sincronizado_En',''))+'. La revisión automática busca cambios cada hora mientras Codex está disponible; este botón vuelve a leer la última copia sincronizada.')
    if not docs:
        st.info('Aún no hay documentos sincronizados.');return
    nuevas=sum(bool(d['Nuevo']) for d in docs)
    c1,c2=st.columns(2);c1.metric('Documentos disponibles',len(docs));c2.metric('Nuevos o actualizados por revisar',nuevas)
    buscar=st.text_input('Buscar un documento o tema',placeholder='Plan de zona, planeación, CTE…',key='supervision_buscar')
    izq,der=st.columns(2)
    seccion=izq.selectbox('Apartado',['Todas']+sorted({d.get('Seccion','') for d in docs}),key='supervision_seccion')
    solo=der.checkbox('Mostrar solo lo que falta revisar',key='supervision_solo_nuevos')
    actividades=st.checkbox('Ver actividades, CTE y sugerencias',key='supervision_actividades')
    lista=s.filtrar(docs,buscar,seccion,solo,actividades)
    if not lista:st.info('No hay documentos con esos filtros. Puedes borrar la búsqueda o elegir Todas.');return
    paginas=(len(lista)+11)//12
    if st.session_state.get('supervision_pagina',1)>paginas:st.session_state['supervision_pagina']=1
    pagina=st.number_input('Página de documentos',min_value=1,max_value=paginas,value=1,key='supervision_pagina')
    for doc in lista[(pagina-1)*12:pagina*12]:
        with st.container(border=True):
            st.subheader(doc.get('Nombre','Documento'))
            st.caption(('Nuevo o actualizado · ' if doc['Nuevo'] else 'Revisado · ')+doc.get('Seccion','')+' · Modificado: '+s.fecha_local(doc.get('Modificado_En','')))
            if 'CAM' in doc.get('Nombre','').upper():st.caption('Documento de referencia CAM: no se traslada automáticamente como requisito de USAER.')
            if doc.get('Enlace'):st.link_button('Consultar documento original',doc['Enlace'])
            if doc.get('Extracto'):
                with st.expander('Leer información y orientaciones'):
                    st.caption(doc.get('Estado_Lectura','Extracto de consulta; verifica el documento original.'))
                    st.text(doc['Extracto'])  # Contenido de terceros, nunca HTML ni instrucciones del sistema.
            else:st.caption('Consulta el original para ver su información completa. No se infiere contenido a partir del título.')
            if doc['Nuevo']:
                key='supervision_visto_'+hashlib.sha256((doc['ID_Documento']+doc.get('Modificado_En','')).encode()).hexdigest()[:20]
                if st.button('Marcar esta versión como revisada',key=key):
                    try:s.marcar_revisado(doc['ID_Documento'],doc.get('Modificado_En',''));st.rerun()
                    except (ValueError,PermissionError) as exc:st.info(str(exc))
                    except Exception:st.info('No se pudo guardar la marca. El documento sigue disponible.')

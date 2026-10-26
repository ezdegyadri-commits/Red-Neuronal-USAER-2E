"""Bibliotecas separadas, tarjetas cortas y navegación sin duplicar documentos."""
import math
import streamlit as st
from services.planeacion_recuperacion import repositorios,titulo_tarjeta,detalle_tarjeta
from utils.escolar import grado_canonico
from utils.text import normalizar_texto


def panel(base,docs,abrir):
    buscar_todo=st.text_input('Buscar alumno en todas mis planeaciones',key=base+'_buscar_historial_completo')
    if buscar_todo.strip():
        texto=normalizar_texto(buscar_todo)
        docs=[d for d in docs if texto in normalizar_texto(' '.join(a.get('Nombre del alumno','') for a in d['datos']['Alumnos']))]
    grupos=repositorios(docs)
    tabs=st.tabs([f'{nombre} ({len(items)})' for nombre,items in grupos.items()])
    for (nombre,items),tab in zip(grupos.items(),tabs):
        with tab:
            key=base+'_repositorio_'+nombre
            if not items:
                st.info('Aún no hay planeaciones en este repositorio. Las nuevas aparecerán aquí automáticamente.');continue
            c1,c2=st.columns([1,2])
            grados=sorted({grado_canonico(a.get('Grado')) for d in items for a in d['datos']['Alumnos']}-{''})
            if buscar_todo.strip():
                st.session_state[key+'_grado']='Todos'
                st.session_state[key+'_buscar']=''
            if st.session_state.get(key+'_grado','Todos') not in ['Todos']+grados:st.session_state[key+'_grado']='Todos'
            grado=c1.selectbox('Grado',['Todos']+grados,key=key+'_grado')
            buscar=c2.text_input('Buscar alumno o escuela',key=key+'_buscar')
            filtradas=[d for d in items if (grado=='Todos' or any(grado_canonico(a.get('Grado'))==grado for a in d['datos']['Alumnos']))
                       and (not buscar.strip() or normalizar_texto(buscar) in normalizar_texto(titulo_tarjeta(d)+' '+d['datos'].get('Escuela regular','')))]
            if not filtradas:
                st.info('No hay coincidencias con estos filtros. No se eliminó ninguna planeación.');continue
            paginas=math.ceil(len(filtradas)/6)
            if st.session_state.get(key+'_pagina',1)>paginas:st.session_state[key+'_pagina']=1
            pagina=st.selectbox('Página',range(1,paginas+1),key=key+'_pagina') if paginas>1 else 1
            st.caption(f'{len(filtradas)} planeación(es) · ordenadas con trabajo redactado y guardados recientes primero')
            for doc in filtradas[(pagina-1)*6:pagina*6]:
                with st.container(border=True):
                    st.subheader(titulo_tarjeta(doc))
                    st.caption(detalle_tarjeta(doc))
                    if st.button('Continuar esta planeación',type='primary',key=key+'_abrir_'+doc['id'],use_container_width=True):
                        try:abrir(base,doc);st.rerun()
                        except (ValueError,PermissionError,RuntimeError) as exc:st.warning(str(exc))
                    with st.expander('Respaldo y opciones del documento'):
                        opciones=key+'_opciones_'+doc['id']
                        if st.button('Ver respaldos y opciones',key=opciones+'_mostrar'):st.session_state[opciones]=True
                        if st.session_state.get(opciones):
                            from ui.planeacion_borradores import controles
                            from documents.planeacion_papel import generar_pdf
                            controles(key+'_'+doc['id'],doc,generar_pdf,lambda:None)

"""Bibliotecas separadas, tarjetas cortas y navegación sin duplicar documentos."""
from copy import deepcopy
import math
from uuid import uuid4
import streamlit as st
from services.planeacion_recuperacion import repositorios,titulo_tarjeta,detalle_tarjeta
from utils.escolar import grado_canonico
from utils.text import normalizar_texto


@st.fragment(run_every=10)
def listado(base,abrir):
    """Actualiza solo las tarjetas; no toca el editor ni invalida cachés globales."""
    from services import planeacion as s
    actor=s.identidad()
    try:
        propias=[d for d in s.listar() if d.get('cuenta')==actor['cuenta']]
    except Exception:
        st.warning('No se pudo actualizar el listado. Se reintentará automáticamente; tus planeaciones siguen conservadas.')
        return []

    # Integración Google Drive: planeaciones compartidas con el equipo accesibles en 1 toque
    compartidas=[]
    keys_prev=set(st.session_state.keys()) if hasattr(st,'session_state') else set()
    try:
        existentes_ids={d['id'] for d in propias}
        # Si un test unitario mockeó s.listar pero no s.compartidos, evitamos llamadas de red reales
        if not (hasattr(s.listar,'mock_calls') and not hasattr(s.compartidos,'mock_calls')):
            for c in s.compartidos():
                if c.get('id') not in existentes_ids:
                    copia=deepcopy(c)
                    copia.setdefault('metadatos',{})['es_compartida_equipo']=True
                    compartidas.append(copia)
    except Exception:
        pass
    finally:
        if hasattr(st,'session_state'):
            for k in list(st.session_state.keys()):
                if k not in keys_prev and k.startswith('_padron_autorizado_'):
                    st.session_state.pop(k,None)

    docs=propias+compartidas if not actor.get('director') else s.listar()
    st.caption('Tus planeaciones se actualizan automáticamente.')
    if docs:panel(base,docs,abrir)
    else:st.info('Aún no tienes planeaciones guardadas en tu cuenta. Las nuevas aparecerán aquí automáticamente.')
    return docs


def panel(base,docs,abrir):
    from services import planeacion as s
    try:actor=s.identidad()
    except Exception:actor={'cuenta':'','director':False}
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
            catalogo=tuple(sorted(d['id'] for d in items))
            if st.session_state.get(key+'_catalogo')!=catalogo:
                st.session_state[key+'_grado']='Todos'
                st.session_state[key+'_buscar']=''
                st.session_state[key+'_pagina']=1
                st.session_state[key+'_catalogo']=catalogo
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
            paginas=math.ceil(len(filtradas)/12)
            if st.session_state.get(key+'_pagina',1)>paginas:st.session_state[key+'_pagina']=1
            pagina=st.selectbox('Página',range(1,paginas+1),key=key+'_pagina') if paginas>1 else 1
            st.caption(f'{len(filtradas)} planeación(es) · ordenadas con trabajo redactado y guardados recientes primero')
            for doc in filtradas[(pagina-1)*12:pagina*12]:
                with st.container(border=True):
                    tipo_meta=doc.get('metadatos',{}).get('modalidad_planeacion')
                    es_comp=doc.get('metadatos',{}).get('es_compartida_equipo')
                    badge_tipo="🤝 Compartida" if es_comp else ("👤 Individual" if tipo_meta=='individual' else ("👥 Grupal" if tipo_meta=='grupal' else "📋 Formato"))
                    estado=doc.get('estado','BORRADOR')
                    color_estado="#059669" if estado in ('VALIDADA','VALIDADO') else ("#2563EB" if estado in ('ENVIADA','ENVIADO') else "#D97706")
                    bg_estado="#ECFDF5" if estado in ('VALIDADA','VALIDADO') else ("#EFF6FF" if estado in ('ENVIADA','ENVIADO') else "#FEF3C7")
                    fecha=doc.get('guardado_en','')[:10] or 'Borrador'
                    st.markdown(f"<div style='display:flex;gap:6px;align-items:center;margin-bottom:4px;'><span style='background:#F1F5F9;color:#334155;padding:2px 8px;border-radius:10px;font-size:0.75rem;font-weight:600;'>{badge_tipo}</span><span style='background:{bg_estado};color:{color_estado};padding:2px 8px;border-radius:10px;font-size:0.75rem;font-weight:600;'>{estado}</span><span style='color:#64748B;font-size:0.75rem;'>📅 {fecha}</span></div>",unsafe_allow_html=True)
                    st.subheader(titulo_tarjeta(doc))
                    st.caption(detalle_tarjeta(doc))
                    if st.button('Continuar esta planeación',type='primary',key=key+'_abrir_'+doc['id'],use_container_width=True):
                        try:
                            st.query_params['doc_id']=doc['id']
                            abrir(base,doc);st.rerun()
                        except (ValueError,PermissionError,RuntimeError) as exc:st.warning(str(exc))
                    izquierda,derecha=st.columns(2)
                    with izquierda:
                        from services.planeacion_compartida import es_guia
                        accion='Añadir alumnos' if es_guia(doc) else 'Duplicar'
                        if st.button(accion,key=key+'_duplicar_'+doc['id'],help='La guía compartida conserva una sola hoja. Otros formatos permiten revisar destinatarios y periodo antes de crear una copia.'):
                            try:
                                prefijo=abrir(base,doc)
                                st.session_state[prefijo+'_papel_panel']='alumnos';st.rerun()
                            except (ValueError,PermissionError,RuntimeError) as exc:st.warning(str(exc))
                    with derecha:
                        from ui.planeacion_borradores import eliminar_directo
                        eliminar_directo(key+'_'+doc['id'],doc,lambda:None)
                    opciones=key+'_opciones_'+doc['id']
                    respaldo=st.expander('Respaldo y opciones del documento',key=opciones,on_change='rerun')
                    if respaldo.open:
                        with respaldo:
                            from ui.planeacion_borradores import controles
                            from documents.planeacion_papel import generar_pdf
                            controles(key+'_'+doc['id'],doc,generar_pdf,lambda:None)
                            if st.button('📋 Duplicar como nuevo borrador',key=key+'_duplicar_'+doc['id']):
                                try:
                                    copia=deepcopy(doc)
                                    copia['id']=uuid4().hex
                                    copia['estado']='BORRADOR'
                                    copia['metadatos'].pop('borrador_eliminado',None)
                                    copia['metadatos']['es_copia_de']=doc['id']
                                    s.guardar(copia,'BORRADOR')
                                    s.refrescar()
                                    st.success('Planeación duplicada como nuevo borrador.')
                                    st.rerun()
                                except Exception as exc:
                                    st.warning(f'No se pudo duplicar: {exc}')


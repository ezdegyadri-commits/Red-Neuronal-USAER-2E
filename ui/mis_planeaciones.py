"""Inicio por documentos; conserva editores, pendientes y permisos canónicos."""
from copy import deepcopy
import streamlit as st
from services import planeacion as s,navegacion_planeaciones as nav
from services.planeacion_ambito import etiqueta as grupo
from services.planeacion_recuperacion import titulo_tarjeta


def _locales(base):
    return [(k[:-4],d) for k,d in list(st.session_state.items())
            if k.startswith(base+'_') and k.endswith('_doc') and isinstance(d,dict)
            and d.get('id') and st.session_state.get(k[:-4]+'_pending')]


def volver(base):
    st.session_state.pop(base+'_documento_contexto',None)
    st.session_state.pop(base+'_crear_documento',None)
    st.session_state[base+'_viva_entrada']=True
    st.query_params.pop('plan',None)
    st.query_params.pop('doc_id',None)
    st.session_state.pop(base+'_url_resuelta',None)


def abrir(base,doc,desde_inicio=False):
    # No confiar en una tarjeta vieja o un contexto recuperado del navegador.
    doc=nav.resolver(nav.enlace_id(doc['id']),[d for _,d in _locales(base)])
    actor=s.identidad();s.autorizar(doc)
    ruta=nav.ruta(doc,actor)
    if ruta=='propio':
        from ui.planeacion_viva import _abrir
        prefix=_abrir(base,doc)
        doc=st.session_state[prefix+'_doc']
    else:
        prefix=base+'_colaboracion'
        st.session_state[prefix+'_abierto']=doc['id']
    st.session_state[base+'_documento_contexto']={**nav.contexto(doc,actor),'ruta':ruta,'prefix':prefix}
    st.session_state[base+'_viva_entrada']=False
    st.query_params.pop('doc_id',None)
    st.query_params['plan']=nav.enlace_id(doc['id'])
    st.session_state[base+'_url_resuelta']=st.query_params['plan']
    if desde_inicio:st.session_state['navegacion_principal']='Planeación e intervención'


def _recordar_filtro(key):
    st.session_state[key+'_preferencia']=st.session_state.get(key,'')


def _limpiar_filtros(base):
    for field in ('escuela','grupo','formato','ciclo'):
        key=base+'_lista_'+field
        st.session_state[key]=''
        st.session_state[key+'_preferencia']=''


def _filtro(label,opciones,key):
    if len(opciones)<=1:
        st.session_state[key+'_preferencia']=''
        return ''
    valores=['',*opciones]
    if key not in st.session_state:st.session_state[key]=st.session_state.get(key+'_preferencia','')
    if st.session_state.get(key,'') not in valores:st.session_state[key]=''
    elegido=st.selectbox(label,valores,format_func=lambda x:'Todas las opciones' if not x else opciones[x],key=key,
                         on_change=_recordar_filtro,args=(key,))
    st.session_state[key+'_preferencia']=elegido
    return elegido


def lista(base,desde_inicio=False):
    actor=s.identidad();locales=_locales(base)
    try:docs=nav.indice([d for _,d in locales])
    except Exception:
        st.warning('No se pudo consultar tu lista. Los documentos y las ediciones pendientes se conservan.')
        if st.button('Reintentar consulta',key=base+'_lista_reintentar'):st.rerun()
        return
    pendientes={d['id']:p for p,d in locales if any(x['id']==d['id'] for x in docs)}
    st.subheader('Mis planeaciones')
    if st.button('＋ Nueva planeación',type='primary',key=base+'_lista_nueva',width='stretch',disabled=actor['director']):
        volver(base);st.session_state[base+'_crear_documento']=True
        if desde_inicio:st.session_state['navegacion_principal']='Planeación e intervención'
        st.rerun(scope='app')
    for field,default in (('buscar',''),('vista','Todas')):
        key=base+'_lista_'+field
        if key not in st.session_state:st.session_state[key]=st.session_state.get(key+'_preferencia',default)
    buscar=st.text_input('Buscar planeación',placeholder='Alumno, escuela o grupo',key=base+'_lista_buscar',
                         on_change=_recordar_filtro,args=(base+'_lista_buscar',))
    vista=st.segmented_control('Mostrar',['Todas','Propias','Compartidas','Borradores','Pendientes'],key=base+'_lista_vista',
                               on_change=_recordar_filtro,args=(base+'_lista_vista',)) or 'Todas'
    filtros=st.expander('Filtrar por escuela, grupo, tipo o ciclo',key=base+'_lista_filtros',on_change='rerun')
    values={}
    if filtros.open:
        with filtros:
            catalogs={
                'escuela':{str(d['datos'].get('ID_Escuela','')):d['datos'].get('Escuela regular','') for d in docs},
                'grupo':{grupo(d):grupo(d) for d in docs if grupo(d)},
                'formato':{nav.tipo(d):nav.tipo(d) for d in docs},
                'ciclo':{d['datos'].get('Curso escolar',''):d['datos'].get('Curso escolar','') for d in docs}}
            for field,label in [('escuela','Escuela'),('grupo','Grado y grupo'),('formato','Tipo de planeación'),('ciclo','Ciclo escolar')]:
                catalog={k:v for k,v in catalogs[field].items() if k}
                values[field]=_filtro(label,catalog,base+'_lista_'+field)
            st.button('Quitar filtros',key=base+'_lista_limpiar',on_click=_limpiar_filtros,args=(base,))
    else:
        # Cerrar los filtros no cambia silenciosamente la consulta elegida.
        values={k:st.session_state.get(base+'_lista_'+k+'_preferencia','') for k in ('escuela','grupo','formato','ciclo')}
    filtradas=nav.filtrar(docs,actor['cuenta'],buscar,vista=vista,pendientes=pendientes,**values)
    st.caption(f'{len(filtradas)} documentos · recientes y cambios pendientes primero')
    if not filtradas:st.info('No hay coincidencias. Puedes quitar los filtros; no se eliminó ningún documento.')
    st.html('<style>.st-key-'+base+'_documentos button{min-height:44px;white-space:normal;overflow-wrap:anywhere}.st-key-'+base+'_documentos button[kind="secondary"]{text-align:left}@media(max-width:600px){.st-key-'+base+'_documentos [data-testid="stHorizontalBlock"]{flex-wrap:wrap;gap:.4rem}}</style>')
    limite=st.session_state.get(base+'_lista_limite',12)
    with st.container(key=base+'_documentos'):
        for doc in filtradas[:limite]:
            did=doc['id'];key=base+'_fila_'+nav.enlace_id(did)[:20]
            pending=pendientes.get(did)
            estado='Guardando' if pending and st.session_state.get(pending+'_trabajo_io') else 'Cambios pendientes' if pending else 'Guardado' if doc.get('guardado_en') else 'Sin confirmación de guardado'
            acceso='Propia' if doc['cuenta']==actor['cuenta'] else 'Compartida'
            fecha=doc.get('guardado_en','Sin guardado central')[:19].replace('T',' ')
            label=f'{titulo_tarjeta(doc)} · {nav.tipo(doc)}\n{doc["datos"].get("Escuela regular","")} · {doc["datos"].get("Curso escolar","")} · {acceso}\n{estado} · {fecha}'
            with st.container(border=True):
                if st.button(label,key=key+'_abrir',width='stretch',help='Abrir directamente este documento'):
                    try:abrir(base,doc,desde_inicio);st.rerun(scope='app')
                    except (ValueError,PermissionError,RuntimeError) as exc:st.warning(str(exc))
                with st.container(horizontal=True):
                    from documents.planeacion_papel import preparar_descarga
                    st.download_button('Exportar PDF',data=preparar_descarga(deepcopy(doc)),file_name='planeacion.pdf',mime='application/pdf',key=key+'_pdf',on_click='ignore')
                    if doc['cuenta']==actor['cuenta']:
                        from services.planeacion_compartida import es_guia
                        if not es_guia(doc) and st.button('Duplicar',key=key+'_duplicar'):
                            try:
                                abrir(base,doc,desde_inicio)
                                p=st.session_state[base+'_documento_contexto']['prefix']
                                st.session_state[p+'_papel_panel']='alumnos'
                                st.session_state[p+'_duplicar_desde_lista']=True
                                st.rerun(scope='app')
                            except (ValueError,PermissionError,RuntimeError) as exc:st.warning(str(exc))
                        if not pending:
                            from ui.planeacion_borradores import eliminar_directo
                            eliminar_directo(key,doc,lambda:None)
                        elif doc.get('estado')=='BORRADOR':st.caption('Confirma el guardado pendiente antes de eliminar.')
    if len(filtradas)>limite and st.button('Ver más documentos',key=base+'_lista_mas',width='stretch'):
        st.session_state[base+'_lista_limite']=limite+12;st.rerun()
    from ui.planeacion_borradores import papelera
    papelera(base)


def pagina(render_hoja=None):
    from ui import planeacion as u
    actor=s.identidad();base=u._prefix()
    from ui.planeacion_pendientes import panel as envios
    envios(base)
    token=st.query_params.get('plan','')
    anterior=st.query_params.get('doc_id','')
    if anterior and not token:
        try:
            doc=next((d for d in nav.indice([d for _,d in _locales(base)]) if d['id']==anterior),None)
            if doc is None:raise PermissionError('Documento fuera de tu asignación')
            abrir(base,doc)
            token=st.query_params.get('plan','')
        except (ValueError,PermissionError,RuntimeError):
            st.warning('El enlace anterior no está disponible en tu cuenta. No se abrió otro documento.')
            volver(base)
    if not token and st.session_state.get(base+'_url_resuelta'):volver(base)
    if token and token!=st.session_state.get(base+'_url_resuelta'):
        try:abrir(base,nav.resolver(token))
        except (ValueError,PermissionError,RuntimeError):
            st.warning('Este enlace no está disponible en tu cuenta. No se abrió otro alumno o grupo.')
            volver(base)
    ctx=st.session_state.get(base+'_documento_contexto')
    # Sesiones que ya estaban editando conservan su editor al activar el rediseño.
    if (not ctx or ctx['ruta']=='propio' and st.session_state.get(base+'_activa')!=ctx['prefix']) and not st.session_state.get(base+'_viva_entrada'):
        p=st.session_state.get(base+'_activa')
        if p and p+'_doc' in st.session_state:
            doc=st.session_state[p+'_doc'];s.autorizar(doc)
            ctx={**nav.contexto(doc,actor),'ruta':'propio','prefix':p}
            st.session_state[base+'_documento_contexto']=ctx
            st.session_state.pop(base+'_crear_documento',None)
            st.query_params['plan']=nav.enlace_id(doc['id'])
            st.session_state[base+'_url_resuelta']=st.query_params['plan']
    if ctx:
        if ctx['cuenta']!=actor['cuenta']:raise PermissionError('El contexto pertenece a otra cuenta.')
        if ctx['ruta']=='propio' and st.session_state.get(base+'_viva_entrada'):
            volver(base);ctx=None
        if ctx and st.button('← Mis planeaciones',key=base+'_lista_volver',width='stretch'):
            volver(base);st.rerun()
        if ctx:
            if ctx['ruta']=='propio':
                doc=st.session_state[ctx['prefix']+'_doc'];s.autorizar(doc,True)
                if doc['id']!=ctx['documento']:raise PermissionError('El contexto del documento cambió; vuelve a la lista.')
                if render_hoja is None:
                    from ui.planeacion_papel import presentar as render_hoja
                render_hoja(ctx['prefix']);return
            if ctx['ruta']=='compartido':
                prefix=ctx['prefix']
                if not st.session_state.get(prefix+'_abierto'):
                    volver(base);st.rerun()
                from ui.planeacion_colaboracion import panel
                panel(prefix);return
            doc=nav.resolver(nav.enlace_id(ctx['documento']))
            from services.planeacion_papel import hoja
            from ui.planeacion_papel import editor
            editor(hoja=nav.solo_lectura(hoja(doc,para_impresion=True)),key=base+'_lectura',default=None)
            if actor['director']:
                if st.button('Revisar entregas de Dirección',key=base+'_revision'):
                    st.session_state[base+'_revision_documentos']=True
                if st.session_state.get(base+'_revision_documentos'):u.direccion_panel()
            return
    if st.session_state.get(base+'_crear_documento'):
        if st.button('← Mis planeaciones',key=base+'_nueva_volver'):
            st.session_state.pop(base+'_crear_documento',None);st.rerun()
        from ui.planeacion_viva import _crear
        anterior=st.session_state.get(base+'_activa')
        _crear(base,actor)
        p=st.session_state.get(base+'_activa')
        if p and (p!=anterior or not st.session_state.get(base+'_viva_entrada')):
            doc=st.session_state[p+'_doc']
            st.session_state[base+'_documento_contexto']={**nav.contexto(doc,actor),'ruta':'propio','prefix':p}
            st.session_state.pop(base+'_crear_documento',None);st.rerun()
        return
    lista(base)
    with st.expander('Ayuda, recuperación y navegación anterior'):
        if st.button('Usar navegación anterior',key=base+'_navegacion_anterior'):
            st.session_state['_navegacion_documentos_anterior']=True;st.rerun(scope='app')
        from ui.planeacion_simple import _recuperar
        _recuperar(base)


def inicio():
    from ui.planeacion import _prefix
    lista(_prefix(),desde_inicio=True)

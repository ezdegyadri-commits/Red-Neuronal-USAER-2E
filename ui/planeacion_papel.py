"""Editor sobre el formato, sin tablas de aplicación ni escritura externa desde JS."""
from pathlib import Path
import re
import hashlib
import threading
import time
from weakref import WeakKeyDictionary
import streamlit as st
import streamlit.components.v2 as components
from streamlit.components.v2.get_bidi_component_manager import get_bidi_component_manager as _registro_componentes
from services import planeacion_papel as papel
from ui.planeacion_pendientes import raiz


def _definicion_editor():
    """Una sola hoja/renderizador; cambia únicamente el transporte de interfaz."""
    carpeta=Path(__file__).with_name('planeacion_papel_component')
    fuente=(carpeta/'index.html').read_text(encoding='utf-8')
    css=re.search(r'<style>(.*?)</style>',fuente,re.S).group(1).replace('body{',':host{')
    html=re.search(r'<body>(.*?)<script>',fuente,re.S).group(1)
    renderer=re.search(r'<script>(.*?)</script>',fuente,re.S).group(1)
    js=(carpeta/'native.js').read_text(encoding='utf-8').replace('/* USAER_RENDERER */',renderer)
    return html,css,js


def _evento_editor(key,on_edicion):
    """Procesa la escritura antes del render: un evento, una ejecución."""
    event=st.session_state.get(key,{}).get('evento')
    if on_edicion and event and event.get('accion') in ('guardar','autoguardar'):
        on_edicion(event)


_COMPONENTES=WeakKeyDictionary()
_COMPONENT_LOCK=threading.RLock()


def _componente_editor():
    # El registro pertenece al runtime activo, no a la sesión ni a un caché
    # global que pueda sobrevivir al reemplazo de ese runtime (AppTest/reinicio).
    registro=_registro_componentes()
    with _COMPONENT_LOCK:
        if registro not in _COMPONENTES:
            html,css,js=_definicion_editor()
            _COMPONENTES[registro]=components.component('usaer_formato_vivo_integrado_v1',html=html,css=css,js=js,isolate_styles=True)
        return _COMPONENTES[registro]


def editor(*,key,default=None,on_edicion=None,**datos):
    render=_componente_editor()
    stable='usaer_editor_'+hashlib.sha256(key.encode()).hexdigest()[:12]
    # La hoja tiene su propio respaldo/acuse. Una lectura de equipo no debe
    # atenuar su DOM persistente; no se alteran disabled, permisos ni avisos.
    st.html('<style>.st-key-'+stable+' [data-stale="true"]{opacity:1!important}</style>')
    with st.container(key=stable):
        result=render(key=key,data=datos,default={'evento':None},on_evento_change=lambda:_evento_editor(key,on_edicion),height='content')
    return result.get('evento',default)


def refrescar_editor():
    """Eventos/ticks reales actualizan solo su fragmento; entrada completa compatible."""
    from streamlit.runtime.scriptrunner import get_script_run_ctx
    ctx=get_script_run_ctx()
    st.rerun(scope='fragment' if ctx and ctx.fragment_ids_this_run else 'app')


def recibir_edicion(prefix,event):
    """Mismo validador y persistencia; sin una segunda recarga del editor."""
    from ui import planeacion as u
    if event.get('nonce')==st.session_state.get(prefix+'_papel_nonce'):return
    try:
        doc=st.session_state[prefix+'_doc']
        nuevo=papel.aplicar(doc,event)
        st.session_state[prefix+'_papel_nonce']=event['nonce']
        if nuevo!=doc:u._open(prefix,nuevo)
        if nuevo!=doc or event['accion']=='guardar':u._persist(prefix,automatic=event['accion']=='autoguardar')
        if not st.session_state.get(prefix+'_pending'):
            st.session_state[prefix+'_papel_aceptado']=event['nonce']
        st.session_state.pop(prefix+'_papel_rechazado',None)
        st.session_state.pop(prefix+'_papel_error',None)
    except (ValueError,PermissionError,RuntimeError) as exc:
        st.session_state[prefix+'_papel_nonce']=event.get('nonce')
        st.session_state[prefix+'_papel_rechazado']=event.get('nonce')
        st.session_state[prefix+'_papel_error']=str(exc)


def lectura_equipo(base,did):
    """La recepción de cada campo no dispara otra consulta del catálogo completo."""
    from services import planeacion as s
    from streamlit.runtime.scriptrunner import get_script_run_ctx
    ctx=get_script_run_ctx(suppress_warning=True)
    # La navegación/actualización explícita sí debe consultar en el momento.
    completa=bool(ctx and not ctx.fragment_ids_this_run)
    now=time.monotonic()
    if not completa and now-st.session_state.get(base+'_lectura_equipo',float('-inf'))<10:return None
    st.session_state[base+'_lectura_equipo']=now
    return next((d for d in s.compartidos() if d['id']==did),None)


def _sincronizar_equipo(prefix):
    from ui import planeacion as u
    from services.planeacion_compartida import es_guia,actualizar_aportes_autor
    doc=st.session_state[prefix+'_doc']
    if not es_guia(doc):return
    try:
        latest=lectura_equipo(prefix,doc['id'])
        if latest:
            nuevo=actualizar_aportes_autor(doc,latest)
            if nuevo!=doc:
                st.session_state[prefix+'_doc']=nuevo
    except Exception:
        st.caption('La actualización del equipo se reintentará. Tu edición se conserva.')


@st.fragment(run_every=10)
def hoja(prefix,volver=None):
    from ui import planeacion as u
    doc=st.session_state[prefix+'_doc']
    _sincronizar_equipo(prefix)
    doc=st.session_state[prefix+'_doc']
    from services.planeacion_compartida import ampliar_matricula
    ampliado=ampliar_matricula(doc,u.servicio.padron_autorizado())
    if ampliado!=doc:
        altas=len(ampliado['datos']['Alumnos'])-len(doc['datos']['Alumnos'])
        if not ampliado['datos']['Alumnos']:
            st.info('Este grupo ya no tiene alumnos activos. Sus versiones y aportaciones anteriores se conservan en el expediente; vuelve al inicio para trabajar otro grupo.')
            if st.button('Regresar al inicio',key=prefix+'_grupo_cerrado'):
                if volver:volver()
                else:st.session_state[raiz(prefix)+'_viva_entrada']=True
                st.rerun(scope='app')
            return
        if altas>0:ampliado=u.servicio.preparar_contexto(ampliado)
        u._open(prefix,ampliado);st.session_state[prefix+'_pending']=True
        doc=st.session_state[prefix+'_doc']
        if altas>0:st.info('Se añadieron las altas grupales nuevas del mismo grado y grupo. Las filas y aportes anteriores se conservan.')
        elif altas<0:st.info('La matrícula activa refleja las bajas y traslados confirmados. Las filas y aportes anteriores se conservan en el historial.')
    u.servicio.autorizar(doc,True)
    # Guardado y lectura remota viven en el mismo fragmento que la hoja:
    # ninguna pausa de escritura desmonta el módulo completo.
    if st.session_state.get(prefix+'_pending'):u._persist(prefix,automatic=True)
    doc=st.session_state[prefix+'_doc']
    event=editor(hoja=papel.hoja(doc),guardado=doc.get('guardado_en','') if not st.session_state.get(prefix+'_pending') else '',
        aceptado=st.session_state.pop(prefix+'_papel_legacy',False),
        aceptado_nonce=st.session_state.get(prefix+'_papel_aceptado',''),
        rechazado=st.session_state.get(prefix+'_papel_rechazado',''),
        error=st.session_state.get(prefix+'_papel_error',''),key=prefix+'_papel_'+doc['id'],default=None,
        on_edicion=lambda event:recibir_edicion(prefix,event))
    if event and event.get('nonce')!=st.session_state.get(prefix+'_papel_nonce'):
        try:
            nuevo=papel.aplicar(doc,event)
            st.session_state[prefix+'_papel_nonce']=event['nonce']
            action=event.get('accion')
            estado='ENVIADO' if action=='enviar' and not u.servicio.revisar(nuevo) else 'BORRADOR'
            if nuevo!=doc:
                u._open(prefix,nuevo);u._persist(prefix,estado,automatic=action=='autoguardar')
            st.session_state.pop(prefix+'_papel_rechazado',None)
            st.session_state.pop(prefix+'_papel_error',None)
            if action not in ('guardar','autoguardar','pdf','enviar','agregar','retirar','apartados','inicio','equipo'):st.session_state[prefix+'_papel_panel']=action
            if action=='corregir':st.session_state[prefix+'_papel_panel']=event['panel']
            if action=='guardar' and nuevo==doc:u._persist(prefix)
            if action=='enviar':
                if estado=='ENVIADO' and nuevo==doc:u._persist(prefix,'ENVIADO')
                elif estado!='ENVIADO':st.session_state[prefix+'_papel_aviso']='Completa los aspectos pendientes antes de enviar. Se conserva tu borrador.'
            if action=='pdf':st.session_state[prefix+'_mostrar_pdf']=True
            if action=='equipo':
                if not st.session_state.get(prefix+'_pending') or u._persist(prefix):
                    u.servicio.refrescar()
                    reciente=next((d for d in u.servicio.compartidos() if d['id']==doc['id']),None)
                    if reciente:u._open(prefix,reciente)
                else:st.session_state[prefix+'_papel_aviso']='Tu texto se conserva. Se actualizarán los aportes cuando se confirme el guardado.'
            if action=='inicio':
                if volver:volver()
                else:st.session_state[raiz(prefix)+'_viva_entrada']=True
                st.rerun(scope='app')
            if action=='apartados' and nuevo==doc:st.session_state[prefix+'_papel_aviso']='No hay nuevos vacíos vinculados con datos suficientes para proponer. Tu redacción se conserva; puedes conectar antecedentes o elegir referentes sin redactar de nuevo.'
            if not st.session_state.get(prefix+'_pending'):
                st.session_state[prefix+'_papel_aceptado']=event['nonce']
                st.session_state[prefix+'_papel_legacy']=True
            if action in ('pdf','antecedentes','referentes','dua','ia','alumnos','detalle','opciones','corregir'):
                st.rerun(scope='app')
            refrescar_editor()
        except (ValueError,PermissionError,RuntimeError) as exc:
            st.session_state[prefix+'_papel_nonce']=event.get('nonce')
            st.session_state[prefix+'_papel_rechazado']=event.get('nonce')
            st.session_state[prefix+'_papel_error']=str(exc)
            refrescar_editor()
    if st.session_state.get(prefix+'_papel_aviso'):st.info(st.session_state.pop(prefix+'_papel_aviso'))
    if st.session_state.get(prefix+'_error'):st.warning(st.session_state[prefix+'_error'])
    elif st.session_state.get(prefix+'_pending'):st.caption('Guardado pendiente. Tu texto permanece protegido en esta pestaña.')
    if doc['metadatos'].get('propuestas_apartados'):st.caption(doc['metadatos']['propuestas_apartados']['aviso'])


def _contenido_conexiones(prefix):
    """La ayuda no tiene reloj: no reconstruir formularios durante su captura."""
    from ui import planeacion as u
    action=st.session_state.get(prefix+'_papel_panel')
    if action and action!='opciones':
        with st.expander('Conexión con este formato',expanded=True):
            if st.button('Cerrar conexión y seguir en mi hoja',key=prefix+'_papel_cerrar'):
                st.session_state.pop(prefix+'_papel_panel',None);st.rerun(scope='app')
            from ui import planeacion_viva as viva
            current=st.session_state[prefix+'_doc']
            if action.startswith('tabla:'):
                from ui.planeacion_formato import _tabla
                tabla=action.split(':',1)[1]
                if st.button('Añadir fila para completar',key=prefix+'_corregir_nueva_'+tabla):
                    from services.planeacion_formato import nueva_fila
                    u._open(prefix,nueva_fila(current,tabla));u._persist(prefix);refrescar_editor()
                _tabla(prefix,tabla,u._persist,u._open)
            elif action=='datos':u._text(prefix,'datos','CCT','CCT de la escuela')
            elif action=='antecedentes':
                viva._ficha(prefix,False)
                from ui.planeacion_social import panel as panel_social
                panel_social(prefix,u._persist,u._open)
            elif action=='referentes':u._curriculo(prefix,current)
            elif action=='dua':
                from ui.planeacion_generacion import _ajuste
                from services.planeacion_generacion import configuracion
                config={**configuracion(current),**current['metadatos'].get('configuracion_generacion',{})}
                st.caption('DUA: opciones de participación y motivación, representación de la información y formas accesibles de acción y expresión. Elige apoyos según lo documentado, no según una etiqueta diagnóstica.')
                key=prefix+'_papel_dua_'+str(st.session_state.get(prefix+'_generation',0))
                st.text_area('Apoyos DUA y ajustes que deben guiar las actividades',value=config.get('apoyos',''),key=key,on_change=_ajuste,args=(prefix,key,'apoyos',u._persist))
            elif action=='ia':
                if current['formato']=='XXI':u._ai(prefix,current)
                else:
                    from ui.planeacion_asistente import panel
                    panel(prefix)
            elif action=='alumnos':
                from ui.planeacion_edicion import panel
                st.caption('Añade o retira destinatarios mediante una copia adaptada. Se conserva el documento previo y no se elimina ningún registro del padrón.')
                panel(prefix)
            elif action=='detalle':
                if current['formato']=='XXI':
                    u._text(prefix,'metadatos','fuente_iepp','Referencia del IEPP: fecha, folio o ubicación del informe')
                    key=prefix+'_papel_iepp_'+str(st.session_state.get(prefix+'_generation',0))
                    st.checkbox('Las NEE fueron confirmadas en el IEPP.',value=bool(current['metadatos'].get('NEE confirmadas desde IEPP')),key=key,on_change=u._field,args=(prefix,key,'metadatos','NEE confirmadas desde IEPP'))
                    for campo in ('Necesidades educativas específicas asociadas a','Maestro de grupo','Vigencia en cursos escolares'):u._text(prefix,'datos',campo)
                if current['metadatos'].get('modalidad_planeacion')=='grupal' and current['datos']['Función']=='Aprendizaje':
                    from ui.planeacion_formato import _tabla
                    from services.planeacion_modelo import FORMATOS
                    for tabla in FORMATOS[current['formato']]['tablas']:_tabla(prefix,tabla,u._persist,u._open)
                    for campo in current['textos']:u._text(prefix,'textos',campo)
                from ui.planeacion_equipo import panel
                panel(prefix,current,u._persist,u._open,compact=True)
    st.caption('Autoguardado activo: al pausar la escritura se transmite el texto y se confirma el guardado recuperable. Si falla la conexión, conserva esta ventana abierta: se reintenta sin borrar tu trabajo. Guardar es también una opción manual.')
    from ui.planeacion_viva import _acciones
    from documents.planeacion_papel import generar_pdf
    # Los expanders cerrados también ejecutan Python: no consultar versiones,
    # generar descargas o montar herramientas hasta una petición explícita.
    if action=='opciones' or st.session_state.get(prefix+'_mostrar_pdf'):
        _acciones(prefix,pdf_provider=generar_pdf,acciones_hoja=True)
        if st.button('Cerrar opciones y volver a mi hoja',key=prefix+'_cerrar_opciones'):
            st.session_state.pop(prefix+'_papel_panel',None)
            st.session_state.pop(prefix+'_mostrar_pdf',None);st.rerun(scope='app')


def conexiones(prefix):
    if not st.session_state.get(prefix+'_papel_panel') and not st.session_state.get(prefix+'_mostrar_pdf'):return
    def cerrar():
        st.session_state.pop(prefix+'_papel_panel',None)
        st.session_state.pop(prefix+'_mostrar_pdf',None)
    @st.dialog('Ayuda para mi formato',width='large',on_dismiss=cerrar)
    def mostrar():_contenido_conexiones(prefix)
    mostrar()


def presentar(prefix,volver=None):
    # Compatibilidad: una sesión con el formulario antiguo conserva sus campos
    # hasta un envío explícito. Las nuevas aperturas usan el documento directo.
    doc=st.session_state[prefix+'_doc']
    old=prefix+'_'+doc['id']+'_captura_'
    if not st.session_state.get(prefix+'_editor_directo') and any(str(k).startswith(old) for k in st.session_state):
        from ui.planeacion_cero_friccion import hoja as captura
        return captura(prefix,volver)
    hoja(prefix,volver)
    conexiones(prefix)


def pagina():
    from ui.planeacion_viva import pagina as base
    return base(render_hoja=presentar)


"""Editor sobre el formato, sin tablas de aplicación ni escritura externa desde JS."""
from pathlib import Path
import re
import streamlit as st
import streamlit.components.v2 as components
from services import planeacion_papel as papel


def _definicion_editor():
    """Una sola hoja/renderizador; cambia únicamente el transporte de interfaz."""
    carpeta=Path(__file__).with_name('planeacion_papel_component')
    fuente=(carpeta/'index.html').read_text(encoding='utf-8')
    css=re.search(r'<style>(.*?)</style>',fuente,re.S).group(1).replace('body{',':host{')
    html=re.search(r'<body>(.*?)<script>',fuente,re.S).group(1)
    renderer=re.search(r'<script>(.*?)</script>',fuente,re.S).group(1)
    js=(carpeta/'native.js').read_text(encoding='utf-8').replace('/* USAER_RENDERER */',renderer)
    return html,css,js


def _evento_editor():
    """El valor persistente llega al mismo validador y deduplicación de nonce."""


def editor(*,key,default=None,**datos):
    html,css,js=_definicion_editor()
    render=components.component('usaer_formato_vivo_integrado_v1',html=html,css=css,js=js,isolate_styles=True)
    result=render(key=key,data=datos,default={'evento':None},on_evento_change=_evento_editor,height='content')
    return result.get('evento',default)


@st.fragment(run_every=10)
def _sincronizar_equipo(prefix):
    from ui import planeacion as u
    from services.planeacion_compartida import es_guia,actualizar_aportes_autor
    doc=st.session_state[prefix+'_doc']
    if not es_guia(doc):return
    try:
        latest=next((d for d in u.servicio.compartidos() if d['id']==doc['id']),None)
        if latest:
            nuevo=actualizar_aportes_autor(doc,latest)
            if nuevo!=doc:
                st.session_state[prefix+'_doc']=nuevo
                st.rerun(scope='app')
    except Exception:
        st.caption('La actualización del equipo se reintentará. Tu edición se conserva.')


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
                else:st.session_state[prefix.rsplit('_',1)[0]+'_viva_entrada']=True
                st.rerun()
            return
        if altas>0:ampliado=u.servicio.preparar_contexto(ampliado)
        u._open(prefix,ampliado);st.session_state[prefix+'_pending']=True
        doc=st.session_state[prefix+'_doc']
        if altas>0:st.info('Se añadieron las altas grupales nuevas del mismo grado y grupo. Las filas y aportes anteriores se conservan.')
        elif altas<0:st.info('La matrícula activa refleja las bajas y traslados confirmados. Las filas y aportes anteriores se conservan en el historial.')
    u.servicio.autorizar(doc,True)
    u._autosave(prefix)
    doc=st.session_state[prefix+'_doc']
    event=editor(hoja=papel.hoja(doc),guardado=doc.get('guardado_en','') if not st.session_state.get(prefix+'_pending') else '',
        aceptado=st.session_state.pop(prefix+'_papel_legacy',False),
        aceptado_nonce=st.session_state.get(prefix+'_papel_aceptado',''),
        rechazado=st.session_state.get(prefix+'_papel_rechazado',''),
        error=st.session_state.get(prefix+'_papel_error',''),key=prefix+'_papel_'+doc['id'],default=None)
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
                if st.session_state.get(prefix+'_pending') and not u._persist(prefix):
                    st.session_state[prefix+'_papel_aviso']='Tu edición sigue abierta: no se confirmó aún el guardado. Se reintentará automáticamente.'
                elif volver:volver()
                else:st.session_state[prefix.rsplit('_',1)[0]+'_viva_entrada']=True
            if action=='apartados' and nuevo==doc:st.session_state[prefix+'_papel_aviso']='No hay nuevos vacíos vinculados con datos suficientes para proponer. Tu redacción se conserva; puedes conectar antecedentes o elegir referentes sin redactar de nuevo.'
            if not st.session_state.get(prefix+'_pending'):
                st.session_state[prefix+'_papel_aceptado']=event['nonce']
                st.session_state[prefix+'_papel_legacy']=True
            st.rerun()
        except (ValueError,PermissionError,RuntimeError) as exc:
            st.session_state[prefix+'_papel_nonce']=event.get('nonce')
            st.session_state[prefix+'_papel_rechazado']=event.get('nonce')
            st.session_state[prefix+'_papel_error']=str(exc)
            st.rerun()
    if st.session_state.get(prefix+'_papel_aviso'):st.info(st.session_state.pop(prefix+'_papel_aviso'))
    if doc['metadatos'].get('propuestas_apartados'):st.caption(doc['metadatos']['propuestas_apartados']['aviso'])
    action=st.session_state.get(prefix+'_papel_panel')
    if action:
        with st.expander('Conexión con este formato',expanded=True):
            if st.button('Cerrar conexión y seguir en mi hoja',key=prefix+'_papel_cerrar'):st.session_state.pop(prefix+'_papel_panel',None);st.rerun()
            from ui import planeacion_viva as viva
            current=st.session_state[prefix+'_doc']
            if action.startswith('tabla:'):
                from ui.planeacion_formato import _tabla
                tabla=action.split(':',1)[1]
                if st.button('Añadir fila para completar',key=prefix+'_corregir_nueva_'+tabla):
                    from services.planeacion_formato import nueva_fila
                    u._open(prefix,nueva_fila(current,tabla));u._persist(prefix);st.rerun()
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
                st.markdown('#### Añadir actividades a esta planeación')
                st.caption('Elige una ruta. Con IA, al generar se integran automáticamente al borrador. Sin IA, prepara la propuesta, revísala y pulsa «Incorporar actividades locales a mi formato». En ambos casos quedan editables en la hoja.')
                from ui.planeacion_generacion import panel_generacion
                if current['formato']=='XXI':u._ai(prefix,current)
                else:panel_generacion(prefix,u._persist,u._open,compact=True)
                from ui.planeacion_local import panel
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
    _acciones(prefix,pdf_provider=generar_pdf,acciones_hoja=True)


def pagina():
    from ui.planeacion_viva import pagina as base
    return base(render_hoja=hoja)


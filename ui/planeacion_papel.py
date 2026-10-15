"""Editor sobre el formato, sin tablas de aplicación ni escritura externa desde JS."""
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components
from services import planeacion_papel as papel

editor=components.declare_component('usaer_planeacion_papel',path=str(Path(__file__).with_name('planeacion_papel_component')))


def hoja(prefix):
    from ui import planeacion as u
    doc=st.session_state[prefix+'_doc'];u.servicio.autorizar(doc,True)
    u._autosave(prefix)
    event=editor(hoja=papel.hoja(doc),aceptado=st.session_state.get(prefix+'_papel_aceptado',False),key=prefix+'_papel_'+doc['id'],default=None)
    st.session_state[prefix+'_papel_aceptado']=False
    if event and event.get('nonce')!=st.session_state.get(prefix+'_papel_nonce'):
        try:
            nuevo=papel.aplicar(doc,event)
            st.session_state[prefix+'_papel_nonce']=event['nonce']
            action=event.get('accion')
            estado='ENVIADO' if action=='enviar' and not u.servicio.revisar(nuevo) else 'BORRADOR'
            if nuevo!=doc:
                u._open(prefix,nuevo);u._persist(prefix,estado,automatic=action=='autoguardar')
            st.session_state[prefix+'_papel_aceptado']=True
            if action not in ('guardar','autoguardar','pdf','enviar','agregar','retirar','apartados'):st.session_state[prefix+'_papel_panel']=action
            if action=='corregir':st.session_state[prefix+'_papel_panel']=event['panel']
            if action=='guardar' and nuevo==doc:u._persist(prefix)
            if action=='enviar':
                if estado=='ENVIADO' and nuevo==doc:u._persist(prefix,'ENVIADO')
                elif estado!='ENVIADO':st.session_state[prefix+'_papel_aviso']='Completa los aspectos pendientes antes de enviar. Se conserva tu borrador.'
            if action=='pdf':st.session_state[prefix+'_mostrar_pdf']=True
            if action=='apartados' and nuevo==doc:st.session_state[prefix+'_papel_aviso']='No hay nuevos vacíos vinculados con datos suficientes para proponer. Tu redacción se conserva; puedes conectar antecedentes o elegir referentes sin redactar de nuevo.'
            st.rerun()
        except (ValueError,PermissionError,RuntimeError) as exc:
            st.session_state[prefix+'_papel_nonce']=event.get('nonce');st.warning(str(exc))
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
    st.caption('La hoja transmite los cambios después de una pausa al escribir; el autoguardado conserva sus intervalos y reintentos. Antes de cerrar, pulsa Guardar cambios de la hoja y confirma el guardado. El respaldo de texto pendiente conserva las celdas aún no transmitidas.')
    from ui.planeacion_viva import _acciones
    from documents.planeacion_papel import generar_pdf
    _acciones(prefix,pdf_provider=generar_pdf,acciones_hoja=True)


def pagina():
    from ui.planeacion_viva import pagina as base
    return base(render_hoja=hoja)


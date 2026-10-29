"""Menú de edición en el mismo formato y con la persistencia existente."""
import streamlit as st
from services import planeacion as s,planeacion_edicion as e
from services.planeacion_modalidad import modalidad_documento
from services.planeacion_matricula import clave_escuela
from services.planeacion_modelo import FORMATOS
from ui.planeacion_pendientes import raiz


def _guardar(prefix,doc):
    from ui import planeacion as u
    u._open(prefix,doc)
    return u._persist(prefix)


def _confirmar_pendiente(prefix):
    from ui import planeacion as u
    if st.session_state.get(prefix+'_pending') and not u._persist(prefix):
        raise RuntimeError('No se confirmó el guardado de tu edición pendiente. Se conserva; respáldala antes de continuar.')
    return st.session_state[prefix+'_doc']


def abrir_guardada(base,doc):
    from ui.planeacion_simple import _abrir,PASOS
    # El abridor común recupera cualquier edición pendiente de ese ID y
    # conserva por separado otro documento, sin bloquear la navegación.
    from ui.planeacion_pendientes import pendientes
    local=next((p for p in pendientes(base) if st.session_state[p+'_doc'].get('id')==doc.get('id')),None)
    if local:doc=st.session_state[local+'_doc']
    _abrir(base,base+'_'+modalidad_documento(doc,s.padron_autorizado()),e.borrador(doc))
    st.session_state[base+'_paso_pendiente']=PASOS[2]


def _abrir_copia(prefix,doc):
    from ui import planeacion as u
    from ui.planeacion_simple import _abrir,PASOS
    if st.session_state.get(prefix+'_pending') and not u._persist(prefix):
        raise RuntimeError('No se confirmó el guardado del documento original. Tu edición se conserva.')
    # Reutilizar el mismo ID ante un fallo ambiguo; nunca crear otra copia a ciegas.
    saved=next((d for d in s.listar() if d['id']==doc['id']),None) or s.guardar(doc)
    base=raiz(prefix)
    destino=base+'_'+doc['metadatos']['modalidad_planeacion']
    _abrir(base,destino,saved)
    st.session_state[base+'_paso_pendiente']=PASOS[2]


def panel(prefix):
    doc=st.session_state[prefix+'_doc']
    desde_lista=st.session_state.pop(prefix+'_duplicar_desde_lista',False)
    if desde_lista:st.session_state[prefix+'_editar_opcion']='Alumnos o periodo · copia adaptada'
    with st.expander('Editar planeación · opciones',expanded=desde_lista):
        st.caption('Trabaja sobre el mismo formato. Al guardar modificaciones se crea una versión en borrador; el historial anterior se conserva.')
        from services.planeacion_compartida import es_guia
        opciones=['Elige una opción']+(['Añadir alumnos a esta planeación'] if es_guia(doc) else [])+['Actividades y orden','Alumnos o periodo · copia adaptada','Referentes oficiales','Reformular actividades con IA','Recuperar una versión anterior']
        opcion=st.selectbox('¿Qué quieres modificar?',opciones,key=prefix+'_editar_opcion')
        if opcion=='Añadir alumnos a esta planeación':
            from ui.planeacion_alumnos import panel as alumnos
            alumnos(prefix)
            return
        if opcion=='Actividades y orden':
            st.info('Edita las celdas del formato que aparecen debajo. Puedes añadir o retirar filas con sus botones. Aquí puedes cambiar su orden.')
            tablas=list(FORMATOS[doc['formato']]['tablas'])
            tabla=st.selectbox('Tabla que deseas ordenar',tablas,key=prefix+'_editar_tabla')
            rows=doc['tablas'][tabla]
            if not rows:st.caption('Añade una fila al formato para organizarla.');return
            indice=st.selectbox('Fila que deseas mover',range(len(rows)),format_func=lambda i:'Fila '+str(i+1),key=prefix+'_editar_fila_'+tabla+'_'+str(len(rows)))
            izq,der=st.columns(2)
            for col,label,delta in ((izq,'Subir fila',-1),(der,'Bajar fila',1)):
                if col.button(label,key=prefix+'_orden_'+str(delta),disabled=not 0<=indice+delta<len(rows)):
                    try:_guardar(prefix,e.reordenar(doc,tabla,indice,delta));st.rerun()
                    except (ValueError,PermissionError,RuntimeError) as exc:st.warning(str(exc))
        elif opcion=='Alumnos o periodo · copia adaptada':
            from services.planeacion_compartida import es_guia
            if es_guia(doc):st.info('El Anexo XIX del mismo grupo y trimestre es único: edita aquí o continúa la hoja del equipo. Una copia solo se permite para otro grupo/periodo; los subgrupos de varios grados usan el formato trimestral, no otra guía XIX.')
            st.caption('Cambiar alumnos o periodo crea otro borrador vinculado al original. Solo reutiliza propuestas de actividades, recursos y referentes oficiales. No copia resultados, NEE, evaluaciones, firmas ni aportaciones. Revisa la pertinencia de cada actividad.')
            frame=s.padron_autorizado()
            frame=frame.loc[frame['ID_Escuela'].map(clave_escuela)==clave_escuela(doc['datos']['ID_Escuela'])]
            nombres={str(r['ID_Alumno']):str(r['Nombre_Completo']) for r in frame.to_dict('records')}
            previos=[str(a['ID_Alumno']) for a in doc['datos']['Alumnos'] if str(a['ID_Alumno']) in nombres]
            ids=st.multiselect('Alumnos de la copia adaptada',list(nombres),default=previos,format_func=nombres.get,key=prefix+'_copia_alumnos')
            tipo=st.radio('Modalidad de la copia',['individual','grupal'],index=1 if modalidad_documento(doc,frame) in ('grupal','especialista') else 0,key=prefix+'_copia_modalidad')
            if s.identidad()['area'] in ('Comunicación','Psicología','Trabajo Social'):st.caption('La copia usa tu formato propio de especialista; no crea otra guía XIX del grupo.')
            incluir=st.checkbox('Incluir alumnos individuales en esta copia grupal',key=prefix+'_copia_incluir') if tipo=='grupal' else False
            ciclo=st.number_input('Ciclo de la copia (año de inicio)',2020,2040,int(doc['datos']['Curso escolar'][:4]),key=prefix+'_copia_ciclo')
            trimestre=st.selectbox('Trimestre de la copia',[1,2,3],index=int(doc['datos']['Trimestre'])-1,key=prefix+'_copia_trimestre')
            if doc['formato']=='XXI':
                st.caption('El PI sigue siendo individual y único por alumno y ciclo. Una copia grupal utiliza el formato trimestral XXIII.')
            revisar=st.checkbox('Revisé que las actividades reutilizadas sean pertinentes y no trasladen información individual de otros alumnos',key=prefix+'_copia_confirmar')
            if st.session_state.get(prefix+'_copia_pendiente'):
                st.warning('Hay una copia cuyo guardado o apertura quedó pendiente. Reintentar reutiliza esa misma copia; conserva los mismos alumnos, modalidad y periodo.')
            if st.button('Crear copia adaptada en borrador',disabled=not ids or not revisar,key=prefix+'_copia_crear'):
                try:
                    doc=_confirmar_pendiente(prefix)
                    firma=e.huella({'origen':doc['id'],'ids':ids,'ciclo':ciclo,'trimestre':trimestre,'tipo':tipo,'incluir':incluir})
                    copia=st.session_state.get(prefix+'_copia_pendiente')
                    if copia is not None and st.session_state.get(prefix+'_copia_solicitud')!=firma:
                        raise ValueError('La copia pendiente corresponde a otra selección. Recupera esa selección o consulta tus borradores antes de crear otra.')
                    if copia is None:
                        copia=e.copiar(doc,ids,ciclo,trimestre,tipo=='grupal',incluir)
                        st.session_state[prefix+'_copia_pendiente']=copia
                        st.session_state[prefix+'_copia_solicitud']=firma
                    _abrir_copia(prefix,copia)
                    st.session_state.pop(prefix+'_copia_pendiente',None);st.rerun()
                except Exception as exc:
                    st.warning(str(exc) if isinstance(exc,(ValueError,PermissionError,RuntimeError)) else 'No se confirmó la copia. El original se conserva; revisa tus borradores antes de volver a crearla.')
        elif opcion=='Referentes oficiales':
            from ui.planeacion import _curriculo
            _curriculo(prefix,doc)
        elif opcion=='Recuperar una versión anterior':
            try:versiones=[v for v in s.listar(True) if v['id']==doc['id'] and v.get('revision')!=doc.get('revision')]
            except Exception:
                st.warning('No se pudo consultar el historial. La edición abierta se conserva y puedes seguir trabajando en el formato.');return
            if not versiones:st.caption('Aún no hay versiones anteriores disponibles.');return
            indice=st.selectbox('Versión por recuperar',range(len(versiones)),format_func=lambda i:str(versiones[i].get('guardado_en',''))[:19]+' · '+versiones[i]['estado'],key=prefix+'_editar_version')
            confirmar=st.checkbox('Recuperar su contenido como un nuevo borrador, conservando el historial y las aportaciones actuales del equipo',key=prefix+'_editar_recuperar_confirm')
            if st.button('Recuperar versión como borrador',disabled=not confirmar,key=prefix+'_editar_recuperar'):
                try:_guardar(prefix,e.recuperar(_confirmar_pendiente(prefix),versiones[indice]));st.rerun()
                except (ValueError,PermissionError,RuntimeError) as exc:st.warning(str(exc))
        elif opcion=='Reformular actividades con IA':
            _ia(prefix,doc)


def _redactar_en_segundo_plano(doc,peticion,resumen,config,actor,escuelas):
    from services.trabajos_documento import como
    from ai.planeacion import conexion_trabajo
    with como(actor,escuelas),conexion_trabajo(config):
        return e.generar_revision(doc,peticion,resumen)


@st.fragment(run_every=2)
def _estado_redaccion(prefix):
    job=st.session_state.get(prefix+'_editar_ia_trabajo')
    if not job:return
    if job['cuenta']!=s.identidad()['cuenta']:return
    if job['future'].done():st.rerun(scope='app')
    st.status('Preparando la redacción solicitada… Puedes continuar editando.',state='running')


def _ia(prefix,doc):
    disponibles=e.actividades(doc)
    if not disponibles:st.caption('Añade primero una actividad al formato. También puedes continuar editando sin IA.');return
    refs=st.multiselect('Actividades por reformular (hasta tres)',list(disponibles),max_selections=3,
        format_func=lambda k:k.split(':')[0]+' · fila '+str(disponibles[k]['indice']+1)+' · '+disponibles[k]['texto'][:70],key=prefix+'_editar_ia_refs')
    if not refs:return
    accion=st.selectbox('Cómo te ayudo con esta redacción',e.ACCIONES_REDACCION,key=prefix+'_editar_ia_accion')
    try:peticion=e.preparar_revision(doc,refs,accion)
    except (ValueError,PermissionError) as exc:st.info(str(exc));return
    generation=e.huella(peticion)[:16]
    resumen=st.text_area('Resumen sin identificadores que analizará la IA',value=peticion['resumen'],max_chars=12000,height=180,key=f'{prefix}_{generation}_editar_ia_resumen')
    confirmar=st.checkbox('Revisé este resumen: no identifica personas. Solicitar solo la reformulación de las actividades elegidas.',key=f'{prefix}_{generation}_editar_ia_confirm')
    if st.button('Preparar reformulación de actividades',disabled=not confirmar or prefix+'_editar_ia_trabajo' in st.session_state,key=prefix+'_editar_ia_generar'):
        try:
            from ai.documento_json import enviar
            from ai.planeacion import configuracion_trabajo
            actor=s.identidad()
            st.session_state[prefix+'_editar_ia_trabajo']={'future':enviar(_redactar_en_segundo_plano,doc,peticion,resumen,configuracion_trabajo(),actor,st.session_state.get('escuelas_permitidas','')),'cuenta':actor['cuenta']}
        except (ValueError,RuntimeError,PermissionError) as exc:st.info(str(exc))
    job=st.session_state.get(prefix+'_editar_ia_trabajo')
    if job and job['cuenta']==s.identidad()['cuenta'] and job['future'].done():
        st.session_state.pop(prefix+'_editar_ia_trabajo',None)
        try:st.session_state[prefix+'_editar_ia_propuesta']=job['future'].result()
        except Exception:st.warning('No se completó la redacción. Tu documento se conserva; reintenta más tarde o continúa editando.')
    _estado_redaccion(prefix)
    propuesta=st.session_state.get(prefix+'_editar_ia_propuesta')
    if not propuesta:return
    if st.button('Descartar propuesta y conservar mi texto',key=prefix+'_editar_ia_descartar'):
        st.session_state.pop(prefix+'_editar_ia_propuesta',None);st.rerun()
    if propuesta['huella']!=e.huella(doc) or propuesta['refs']!=refs or propuesta.get('accion','Mejorar redacción')!=accion:
        st.caption('La edición o la selección cambió. La propuesta anterior no se aplicará sobre tu trabajo.');return
    for row in propuesta['cambios']:
        st.markdown('**Actividad actual**');st.write(disponibles[row['referencia']]['texto'])
        st.markdown('**Propuesta editable después de incorporar**');st.write(row['actividad'])
    if st.button('Aplicar únicamente estas actividades revisadas',key=prefix+'_editar_ia_aplicar'):
        try:
            _guardar(prefix,e.aplicar_revision(doc,propuesta))
            st.session_state.pop(prefix+'_editar_ia_propuesta',None);st.rerun()
        except (ValueError,PermissionError,RuntimeError) as exc:st.warning(str(exc))

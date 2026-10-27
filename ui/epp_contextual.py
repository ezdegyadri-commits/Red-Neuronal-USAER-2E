"""Instrumentos visibles y redacción contextual sin diálogos ni selección de motor."""
from copy import deepcopy
import streamlit as st
from services import epp as s
from services import epp_contextual as servicio
from services.epp_modelo import AREAS, vacia


def actual(prefix, doc):
    result=deepcopy(doc)
    for area in (*AREAS,'Conclusión'):
        edit=prefix+'_edit_'+doc['id']+'_'+area
        if edit+'_value' in st.session_state:
            result['partes'].setdefault(area,{})['contenido']=deepcopy(st.session_state[edit+'_value'])
    return result


def incorporar(prefix, nuevo, areas):
    from ui.epp import _abrir
    for area in areas:
        edit=prefix+'_edit_'+nuevo['id']+'_'+area
        if edit+'_doc' not in st.session_state:_abrir(edit,nuevo,area)
        st.session_state[edit+'_value']=deepcopy(nuevo['partes'][area]['contenido'])
        # Mantener la base del diario; nunca fingir que una propuesta ya está guardada.
        st.session_state[edit+'_pending']=True
        for key in list(st.session_state):
            if key.startswith(edit+'_field_') or key.startswith(edit+'_table_'):st.session_state.pop(key,None)
    # La confirmación final usa el flujo de guardado existente, sin I/O en el clic IA.
    key=prefix+'_ia_areas_pendientes_'+nuevo['id']
    st.session_state[key]=list(set(st.session_state.get(key,[]))|set(areas))


def _escribir(capturas):
    results={}
    for area,(doc,base,value,revision) in capturas.items():
        try:results[area]={'saved':s.guardar_cambios(doc,area,base,value,revision)}
        except Exception:results[area]={'error':True}
    return results


@st.fragment(run_every=2)
def guardados(prefix,docid):
    """La IA deja el borrador visible primero; el diario se confirma por separado."""
    key=prefix+'_contextual_io_'+docid
    pendientes=prefix+'_ia_areas_pendientes_'+docid
    job=st.session_state.get(key)
    if job:
        if job['cuenta']!=s.actor()['cuenta']:return
        if not job['future'].done():st.caption('Confirmando la redacción en el informe compartido… Puedes seguir editando.');return
        st.session_state.pop(key,None)
        try:results=job['future'].result()
        except Exception:
            st.session_state[key+'_fallo']=True
            st.warning('No se confirmó el guardado. Tu redacción se conserva; reintenta cuando mejore la conexión.')
            return
        failed=[]
        for area,result in results.items():
            edit=prefix+'_edit_'+docid+'_'+area
            if result.get('error'):failed.append(area);continue
            saved=result['saved'];sent=job['capturas'][area][2];local=st.session_state[edit+'_value']
            try:merged=s.combinar(sent,local,saved['contenido'])
            except RuntimeError:failed.append(area);continue
            st.session_state[edit+'_doc']['partes'][area]=saved
            st.session_state[edit+'_value']=merged
            st.session_state[edit+'_pending']=merged!=saved['contenido']
            st.session_state[edit+'_saved']=saved['fecha']
            if st.session_state[edit+'_pending']:failed.append(area)
        # Otra propuesta puede haber añadido áreas mientras este envío viajaba.
        nuevas=set(st.session_state.get(pendientes,[]))-set(job['capturas'])
        st.session_state[pendientes]=list(nuevas|set(failed))
        if failed:
            st.warning('La redacción está en tu formato; falta confirmar parte del guardado. Tu texto se conserva.')
            # No reintentar en bucle al fallar; la persona controla el reintento.
            st.session_state[key+'_fallo']=True
        else:st.toast('Redacción guardada en el informe compartido.',icon='✅')
    areas=st.session_state.get(pendientes,[])
    if not areas:return
    if st.session_state.get(key+'_fallo'):
        if not st.button('Reintentar guardado de la redacción',key=key+'_retry'):return
        st.session_state.pop(key+'_fallo',None)
    captures={}
    for area in areas:
        edit=prefix+'_edit_'+docid+'_'+area
        doc=st.session_state.get(edit+'_doc')
        if doc:
            old=doc['partes'].get(area,{})
            captures[area]=(deepcopy(doc),deepcopy(old.get('contenido',vacia(area))),deepcopy(st.session_state[edit+'_value']),old.get('revision',''))
    if captures:
        from services.trabajos_documento import enviar
        try:
            future=enviar(s.actor(),st.session_state.get('escuelas_permitidas',''),_escribir,captures)
            st.session_state[key]={'future':future,'capturas':captures,'cuenta':s.actor()['cuenta']}
        except Exception:st.warning('El guardado espera conexión. Tu texto se conserva; vuelve a intentarlo.');st.session_state[key+'_fallo']=True


def iniciar(key, doc, objetivo=None, ideas=''):
    if key+'_job' in st.session_state:return
    solicitud=servicio.preparar(doc,objetivo,ideas)
    if not solicitud['datos']['destinos'] and not solicitud['coordinadora']:
        raise ValueError('Tus apartados ya tienen redacción. Usa Autocompletar junto al campo que deseas ajustar.')
    from ai.epp_contextual import enviar,configuracion
    future=enviar(solicitud,configuracion())
    st.session_state[key+'_job']={'future':future,'solicitud':solicitud,'cuenta':s.actor()['cuenta'],'documento':doc['id']}
    st.session_state.pop(key+'_error',None)


@st.fragment(run_every=1)
def estado(key,get_doc,apply):
    job=st.session_state.get(key+'_job')
    if not job:
        if st.session_state.get(key+'_error'):st.warning(st.session_state[key+'_error'])
        return
    doc=get_doc()
    if (job['cuenta'],job['documento'])!=(s.actor()['cuenta'],doc['id']):
        st.warning('Esta propuesta corresponde a otra cuenta o EPP.');return
    if not job['future'].done():
        st.progress(35,text='Analizando los instrumentos y redactando los apartados… Puedes seguir escribiendo.')
        return
    st.session_state.pop(key+'_job',None)
    try:
        result=job['future'].result()
        st.session_state[key+'_ultima_propuesta']={'solicitud':job['solicitud'],'resultado':result}
        # No mezclar resultados basados en instrumentos que otro integrante actualizó.
        for area in AREAS:
            antes=servicio.contenido(job['solicitud']['base'],area)
            ahora=servicio.contenido(doc,area)
            if any(antes.get(k)!=ahora.get(k) for k in ('evaluaciones','campos','sintesis','no_requeridos')):
                raise ValueError('El equipo actualizó sus hallazgos durante la redacción. Conservamos la propuesta; vuelve a redactar con los hallazgos actuales.')
        nuevo,areas,conflictos=servicio.aplicar(doc,job['solicitud'],result)
        if areas:apply(nuevo,areas)
        if conflictos:
            st.session_state[key+'_error']='Se conservaron las ediciones más recientes en: '+', '.join(conflictos)+'. La propuesta permanece disponible para consulta.'
        elif not areas:st.session_state[key+'_error']='No hay apartados nuevos sustentados en la evidencia disponible. Revisa los instrumentos y los datos pendientes.'
        st.session_state[key+'_faltantes']=result['faltantes']
        if areas:st.toast('Redacción incorporada al formato. Revisa y confirma el guardado al terminar.',icon='✨')
    except Exception as exc:
        st.session_state[key+'_error']=str(exc) if isinstance(exc,(ValueError,PermissionError,RuntimeError)) else 'No se completó la redacción. Tu texto se conserva; puedes continuar y reintentar.'
    st.rerun(scope='app')


def barra(key,get_doc,apply):
    doc=get_doc();actor=s.actor()
    if actor.get('director'):return
    inventario=[]
    for area in AREAS:
        ev=servicio.contenido(doc,area).get('evaluaciones',[])
        inventario.append((area,sum(bool(str(x.get('texto','')).strip()) for x in ev)))
    total=sum(n for _,n in inventario)
    st.info('🔗 Instrumentos vinculados: '+str(total)+' · '+' · '.join(a+': '+str(n) for a,n in inventario))
    st.caption('Redacta los apartados vacíos de tu función con los resultados del equipo. Los campos escritos, los permisos y las marcas «No se requiere» se conservan. La coordinación integra conclusión, NEE y BAP.')
    consent=st.checkbox('Autorizo usar los hallazgos anonimizados de esta EPP en los motores de IA configurados',key=key+'_consent')
    busy=key+'_job' in st.session_state
    if st.button('✨ Redactar EPP Automáticamente',type='primary',use_container_width=True,key=key+'_global',disabled=busy or not consent):
        try:iniciar(key,get_doc());st.rerun()
        except (ValueError,PermissionError,RuntimeError) as exc:st.warning(str(exc))
    estado(key,get_doc,apply)
    if st.session_state.get(key+'_faltantes'):
        with st.expander('Datos pendientes para completar la EPP'):
            for text in st.session_state[key+'_faltantes']:st.write(text)
    if key+'_ultima_propuesta' in st.session_state:
        with st.expander('Consultar la última propuesta del asistente'):
            for item in st.session_state[key+'_ultima_propuesta']['resultado']['apartados']:
                st.markdown('**'+item['campo']+'**');st.write(item['redaccion'])


def inline(key,get_doc,area,campo,ideas=''):
    busy=key+'_job' in st.session_state
    consent=st.session_state.get(key+'_consent',False)
    if st.button('✨ Autocompletar',key=key+'_inline_'+area+'_'+campo,disabled=busy or not consent,
                 help='Redacta este apartado con los instrumentos vinculados y conserva una propuesta consultable.'):
        try:iniciar(key,get_doc(),(area,campo),ideas);st.rerun()
        except (ValueError,PermissionError,RuntimeError) as exc:st.warning(str(exc))


def instrumentos(doc,area,key,get_value,save_value):
    st.subheader('1. Carga y Aplicación de Instrumentos')
    st.caption('Sube los resultados o aplica un formato digital. Ambos se vinculan al mismo alumno e informe.')
    from ui.epp_instrumentos import externo,digital
    with st.expander('📎 Subir Instrumentos',expanded=True):
        externo(doc,area,key+'_upload',get_value,save_value,solo_carga=True)
    with st.expander('✍️ Aplicar Digitalmente'):
        from services.epp_instrumentos import DEFINICIONES
        codes=[c for c,v in DEFINICIONES.items() if v['area']==area]
        cols=st.columns(2)
        for i,code in enumerate(codes):
            if cols[i%2].button(DEFINICIONES[code]['nombre'],key=key+'_rapido_'+code,use_container_width=True):
                st.session_state[key+'_digital_activo']=code
        if not codes:st.caption('Registra los resultados de la evaluación externa mediante Subir Instrumentos.')
        active=st.session_state.get(key+'_digital_activo')
        if active in codes:digital(doc,area,key+'_digital',get_value,save_value,codigo_preseleccionado=active)

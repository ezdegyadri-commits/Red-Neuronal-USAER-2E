"""Añadir a la hoja abierta; nunca crea una copia adaptada."""
import hashlib
import streamlit as st
from services import planeacion as s, planeacion_alumnos as servicio


def panel(prefix):
    from ui import planeacion as ui
    doc=st.session_state[prefix+'_doc']
    key=prefix+'_incorporar_'+hashlib.sha256(doc['id'].encode()).hexdigest()[:12]
    st.subheader('Añadir alumno a esta planeación')
    st.caption('Se conserva la misma hoja, sus actividades y los aportes del equipo.')
    if st.button('Actualizar matrícula disponible',key=key+'_refrescar'):
        s.refrescar_matricula()
    try:frame=s.padron_autorizado()
    except Exception:
        st.warning('No se pudo consultar la matrícula. Tu planeación se conserva; reintenta actualizarla.');return
    autorizar=st.checkbox('Autorizar la incorporación excepcional de alumnos de atención individual solo en esta hoja',key=key+'_individuales')
    if autorizar:st.caption('Se conserva su atención individual en el padrón y su planeación individual. La autorización se registra para cada alumno que selecciones.')
    disponibles=servicio.elegibles(doc,frame,autorizar)
    presentes={str(a['ID_Alumno']) for a in doc['datos']['Alumnos']}
    disponibles=disponibles.loc[~disponibles['ID_Alumno'].astype(str).isin(presentes)]
    if disponibles.empty:
        st.info('Ya están incorporados los alumnos grupales disponibles. Si falta alguien, revisa su alta, escuela, grado y tipo de atención. Los alumnos de atención individual continúan en su planeación individual.');return
    rows={str(r['ID_Alumno']):r for r in disponibles.to_dict('records')}
    def etiqueta(aid):
        row=rows[aid];grupo=str(row.get('Grupo','')).strip()
        from services.planeacion_modalidad import modalidad
        return str(row.get('Nombre_Completo',''))+(' · '+grupo if grupo else ' · Sin grupo registrado')+(' · Atención individual' if modalidad(row)=='individual' else '')
    ids=st.multiselect('Alumnos para incorporar',list(rows),format_func=etiqueta,key=key+'_ids_'+str(st.session_state.get(key+'_version',0)))
    if any(not str(rows[i].get('Grupo','')).strip() for i in ids):
        st.info('El alumno sin grupo se añadirá expresamente a esta hoja. Su grupo en el padrón quedará sin cambios.')
    if st.button('Añadir a esta planeación',type='primary',width='stretch',disabled=not ids,key=key+'_confirmar'):
        try:
            nuevo=servicio.incorporar(st.session_state[prefix+'_doc'],ids,frame,autorizar_individuales=autorizar)
            aviso=''
            try:
                with st.spinner('Vinculando los antecedentes del alumno con la misma hoja…'):
                    nuevo=s.preparar_contexto(nuevo)
            except Exception:
                aviso=' No se pudieron actualizar sus antecedentes; puedes reintentarlo desde Consultar expediente y NEE.'
            ui._open(prefix,nuevo)
            confirmado=ui._persist(prefix)
            st.session_state[prefix+'_papel_aviso']=('Alumno incorporado a la misma planeación.' if confirmado else 'Alumno incorporado al borrador de esta hoja; la confirmación central sigue pendiente. Puedes continuar y reintentar el guardado.')+aviso
            st.session_state[key+'_version']=st.session_state.get(key+'_version',0)+1
            st.session_state.pop(prefix+'_papel_panel',None)
            st.rerun(scope='app')
        except (ValueError,PermissionError,RuntimeError) as exc:
            st.warning(str(exc))

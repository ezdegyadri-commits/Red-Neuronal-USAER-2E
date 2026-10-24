"""Acciones explícitas sobre un solo alumno; nunca borrado físico."""
import streamlit as st
from config.settings import ESCUELAS_USAER
from services import padron_movimientos as servicio
from services.asignaciones import es_direccion


def recuperar():
    pendiente=st.session_state.get('mov_padron_pendiente')
    if not pendiente:return
    st.warning('Hay un movimiento sin confirmación final. Verifícalo antes de iniciar otro; no se repetirá si ya quedó aplicado.')
    if st.button('Verificar y recuperar confirmación del movimiento',key='mov_padron_recuperar'):
        try:
            servicio.ejecutar(**pendiente)
            st.session_state.pop('mov_padron_pendiente',None)
            st.session_state['mov_padron_resultado']='Movimiento verificado y confirmado; no se duplicó.'
            st.rerun()
        except Exception as exc:st.error('Aún no se confirmó: '+str(exc))


def panel(frame):
    rol=st.session_state.get('rol','')
    if not es_direccion(rol) and 'APOYO' not in rol.upper():return
    with st.expander('Gestionar alumno · trasladar, dar de baja o reactivar'):
        st.caption('Conserva la misma identidad y toda su historia. La baja es recuperable; el traslado cambia su escuela y docente actuales, no los documentos históricos.')
        rows={str(r['ID_Alumno']):r for r in frame.fillna('').to_dict('records') if str(r.get('ID_Alumno','')).strip()}
        if not rows:st.info('No hay alumnos en esta escuela.');return
        aid=st.selectbox('Alumno que gestionarás',list(rows),format_func=lambda k:rows[k].get('Nombre_Completo',k),key='mov_padron_alumno')
        st.caption('Origen: '+str(rows[aid].get('Nombre_Escuela',''))+' · '+str(rows[aid].get('Grado',''))+' '+str(rows[aid].get('Grupo',''))+' · '+str(rows[aid].get('Maestra de Apoyo','')))
        acciones=['Trasladar','Baja recuperable','Reactivar']
        if servicio.permite_cambio_interno(rows[aid]):acciones.insert(1,'Cambiar maestra en la misma escuela')
        if st.session_state.get('mov_padron_accion') not in acciones:st.session_state['mov_padron_accion']=acciones[0]
        accion=st.radio('Acción',acciones,horizontal=True,key='mov_padron_accion')
        destino={}
        if accion=='Cambiar maestra en la misma escuela':
            from services.alumnos import _canonizar_docente_apoyo
            actual=_canonizar_docente_apoyo(rows[aid].get('Maestra de Apoyo',''))
            docentes=[n for n in servicio.docentes_destino('Ichcaanziho') if n!=actual]
            docente=st.selectbox('Maestra de apoyo que recibirá al alumno',docentes,key='mov_padron_interno_docente')
            destino=dict(escuela='Ichcaanziho',docente=docente)
            st.info('Solo cambiará la maestra responsable dentro de Ichcaanziho. Se conservan escuela, grado, grupo, atención, ID y expediente. Los documentos previos mantienen su autoría e historial.')
        if accion=='Trasladar':
            origen=str(rows[aid].get('ID_Escuela',''))
            opciones=[n for n,c in ESCUELAS_USAER.items() if str(c)!=origen]
            escuela=st.selectbox('Escuela de destino',opciones,key='mov_padron_destino')
            docentes=servicio.docentes_destino(escuela)
            if not docentes:st.warning('Dirección debe confirmar la maestra de apoyo de destino.');return
            docente=st.selectbox('Maestra de apoyo que recibirá al alumno',docentes,key='mov_padron_docente_'+escuela)
            from utils.escolar import grado_canonico,grupo_canonico
            grados=[f'{g}°' for g in range(1,7)];previo=grado_canonico(rows[aid].get('Grado',''))
            c1,c2=st.columns(2)
            grado=c1.selectbox('Grado de destino',grados,index=grados.index(previo) if previo in grados else None,key='mov_padron_grado_'+aid)
            grupo=c2.text_input('Grupo de destino',value=grupo_canonico(rows[aid].get('Grupo','')),max_chars=4,key='mov_padron_grupo_'+aid)
            regular=st.text_input('Docente regular de destino (si se conoce)',key='mov_padron_regular')
            destino=dict(escuela=escuela,docente=docente,grado=grado,grupo=grupo,regular=regular)
            st.info('Los documentos individuales siguen al mismo ID. Los documentos colectivos permanecen protegidos en su grupo de origen; no se comparten los datos de otros alumnos.')
        motivo=st.text_input('Motivo del movimiento',max_chars=500,key='mov_padron_motivo')
        if accion=='Baja recuperable':st.warning('Se retira del padrón activo, sin borrar al alumno ni sus documentos. Podrás reactivarlo desde esta misma sección.')
        import hashlib,json
        firma=hashlib.sha256(json.dumps([aid,accion,motivo,destino],sort_keys=True).encode()).hexdigest()
        confirma=st.checkbox('Revisé el alumno y el movimiento; confirmo aplicarlo',key='mov_padron_confirmar_'+firma)
        with st.container(key='padron_baja' if accion=='Baja recuperable' else 'padron_movimiento'):
            aplicar=st.button('Confirmar '+accion.lower(),type='primary',disabled=not confirma or len(motivo.strip())<8,key='mov_padron_aplicar')
        if aplicar:
            try:
                from uuid import uuid4
                op=st.session_state.setdefault('mov_padron_op_'+firma,uuid4().hex)
                origen={k:rows[aid].get(k,'') for k in ('ID_Escuela','Maestra de Apoyo','Grado','Grupo')}
                payload=dict(aid=aid,accion=accion,motivo=motivo,operacion=op,esperado_origen=origen,**destino)
                st.session_state['mov_padron_pendiente']=payload
                servicio.ejecutar(**payload)
                st.session_state.pop('mov_padron_pendiente',None)
                st.session_state['mov_padron_resultado']='Movimiento confirmado. Se conserva el expediente y la historia del alumno.'
                st.rerun()
            except Exception as exc:st.error('No se confirmó el movimiento: '+str(exc)+' No repitas el traslado si el alumno ya cambió de escuela; solicita a Dirección revisar el registro de movimientos.')

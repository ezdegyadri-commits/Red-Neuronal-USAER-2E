"""Vista previa y confirmación del Excel dentro del alta existente."""
import hashlib
import pandas as pd
import streamlit as st
from services import padron_importacion as motor


@st.fragment(run_every=2)
def _estado(key,nombre,rol):
    job=st.session_state.get(key+'_trabajo')
    if (nombre,rol)!=(st.session_state.get('nombre'),st.session_state.get('rol')):return
    if not job:
        result=st.session_state.get(key+'_resultado')
        if result:st.success(f"Importación confirmada: {result['altas']} alta(s), {result['actualizados']} alumno(s) actualizado(s). Historial y expedientes conservados.")
        if st.session_state.get(key+'_error'):st.warning(st.session_state[key+'_error'])
        return
    if not job.done():
        st.status('Guardando cambios e historial… Puedes continuar navegando; conserva esta sesión para recibir la confirmación.',state='running');return
    st.session_state.pop(key+'_trabajo',None)
    try:
        result=job.result();st.session_state[key+'_resultado']=result
        st.success(f"Altas: {result['altas']}. Alumnos actualizados: {result['actualizados']}. Historial y expedientes conservados.")
    except ValueError as exc:st.session_state[key+'_error']=str(exc)
    except PermissionError:st.session_state[key+'_error']='La cuenta o escuela ya no tiene autorización. El archivo permanece disponible.'
    except Exception:st.session_state[key+'_error']='No se recibió confirmación. El archivo y la vista previa se conservan. Revisa antes de reintentar: se comprobará lo ya guardado para evitar duplicados.'
    if st.session_state.get(key+'_error'):st.warning(st.session_state[key+'_error'])


def panel(escuelas,actuales,nombre,rol):
    st.markdown('### Carga por Excel: altas y actualización de alumnos')
    st.caption('Se conserva el ID y el expediente de cada CURP existente. Los campos vacíos y los alumnos ausentes del Excel no se eliminan ni se dan de baja.')
    upload=st.file_uploader('Subir Excel de alumnos',type=['xlsx'],max_upload_size=16,key='carga_masiva_alumnos')
    if not upload:return
    data=upload.getvalue();key='padron_importacion_'+hashlib.sha256((nombre+rol).encode()+data).hexdigest()
    if st.button('Revisar archivo y cambios',key=key+'_revisar',type='primary'):
        try:
            with st.status('Validando archivo y comparando con el padrón…',expanded=False) as status:
                lectura=motor.leer(data,escuelas)
                plan=motor.comparar(lectura['registros'],actuales.to_dict('records'),escuelas)
                st.session_state[key]={'lectura':lectura,'plan':plan}
                status.update(label='Comparación terminada',state='complete')
        except (ValueError,PermissionError) as exc:st.warning(str(exc)+'. El padrón sigue intacto.')
        except Exception:st.warning('El archivo no es un Excel .xlsx legible. Guarda una copia en ese formato y vuelve a cargarla. El padrón sigue intacto.')
    revision=st.session_state.get(key)
    if not revision:return
    plan=revision['plan'];errores=revision['lectura']['errores']+plan['conflictos']
    with st.expander('Campos reconocidos y encabezados pendientes',expanded=False):
        st.write(', '.join(revision['lectura'].get('columnas_reconocidas',[])))
        omitidos=revision['lectura'].get('encabezados_no_reconocidos',[])
        if omitidos:st.info('Estos encabezados no se copiarán como campos nuevos: '+', '.join(omitidos)+'. Si contienen información necesaria, usa los encabezados reconocidos antes de confirmar.')
    if errores:
        st.warning('Corrige las observaciones antes de confirmar. No se ha modificado el padrón.')
        for error in errores:st.write(error)
    rows=[]
    for row in plan['filas']:
        r=row['registro']
        rows.append({'Acción':row['tipo'],'Alumno':r['Nombre_Completo'],'Grado':r.get('Grado',''),'Grupo':r.get('Grupo',''),
            'Cambios':'; '.join(k+': '+str(row['anterior'].get(k,''))+' → '+str(v) for k,v in row['cambios'].items())})
    st.dataframe(pd.DataFrame(rows),hide_index=True,width='stretch')
    st.caption('Altas: '+str(sum(r['tipo']=='Alta' for r in plan['filas']))+' · Actualizaciones: '+str(sum(r['tipo']=='Actualizar' for r in plan['filas']))+' · Sin cambios: '+str(sum(r['tipo']=='Sin cambios' for r in plan['filas'])))
    checked=st.checkbox('Revisé los datos y confirmo estas altas y actualizaciones',key=key+'_confirmo')
    if st.button('Confirmar importación',key=key+'_guardar',type='primary',disabled=not checked or bool(errores) or not rows or key+'_trabajo' in st.session_state):
        try:
            from services.trabajos_documento import enviar
            st.session_state[key+'_trabajo']=enviar({'nombre':nombre,'rol':rol},','.join(e['ID_Escuela'] for e in escuelas),motor.confirmar,plan,escuelas,nombre,rol,upload.name)
            st.session_state.pop(key+'_resultado',None);st.session_state.pop(key+'_error',None)
        except ValueError as exc:st.warning(str(exc))
        except PermissionError:st.warning('La cuenta o escuela ya no tiene autorización. El archivo permanece disponible.')
        except Exception:st.warning('No se confirmó la operación. Tu archivo y la vista previa se conservan; reintenta revisar antes de confirmar. Se comprobará lo que ya esté guardado para evitar duplicados.')
    _estado(key,nombre,rol)

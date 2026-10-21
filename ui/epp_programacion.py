"""Una programación compartida, sin copias por especialista ni doble calendario."""
from datetime import date,time
import streamlit as st
import pandas as pd
from services import epp_programacion as s,epp

def panel(prefix):
    with st.expander('Cuadro de control y programación de EPP',expanded=False):
        if not st.checkbox('Abrir control compartido',key=prefix+'_control_abrir'):return
        try:
            registros=s.listar();frame=epp.planes.padron_autorizado().fillna('')
        except Exception:
            st.warning('No se pudo consultar la programación. No se han modificado fechas.');return
        nombres={str(r['ID_Alumno']):str(r.get('Nombre_Completo',''))+' · '+str(r.get('Nombre_Escuela','')) for r in frame.to_dict('records')}
        if not nombres:st.info('No hay alumnos disponibles en tu asignación.');return
        if registros:
            tabla=pd.DataFrame([{**r,'Alumno':nombres[r['ID_Alumno']]} for r in registros])
            st.dataframe(tabla[['Alumno','Area','Fecha','Hora','Aspectos','Instrumentos','Lugar','Estado']],hide_index=True,width='stretch')
        opciones=['Nueva programación'] if epp.puede_crear() else []
        porid={r['ID_Programacion']:r for r in registros};opciones+=list(porid)
        if not opciones:st.info('La maestra de apoyo inicia el control; su equipo asignado podrá continuar aquí.');return
        elegido=st.selectbox('Programación a continuar',opciones,format_func=lambda k:k if k not in porid else nombres[porid[k]['ID_Alumno']]+' · '+porid[k]['Area']+' · '+(porid[k]['Fecha'] or 'Por programar'),key=prefix+'_control_registro')
        r=porid.get(elegido,{});k=prefix+'_control_'+str(elegido)+'_'+r.get('Revision','nuevo')[:12]
        with st.form(k,clear_on_submit=False):
            a,b=st.columns(2)
            aid=a.selectbox('Alumno',list(nombres),format_func=nombres.get,index=list(nombres).index(r['ID_Alumno']) if r else 0,disabled=bool(r))
            ciclo=b.text_input('Ciclo escolar',r.get('Ciclo','2026-2027'),disabled=bool(r))
            a,b,c=st.columns(3)
            area=a.selectbox('Área o reunión',s.AREAS,index=s.AREAS.index(r.get('Area','Aprendizaje')))
            fecha=b.date_input('Fecha programada',value=date.fromisoformat(r['Fecha']) if r.get('Fecha') else None,format='DD/MM/YYYY')
            hora=c.time_input('Hora (opcional)',value=time.fromisoformat(r['Hora']) if r.get('Hora') else None)
            aspectos=st.text_area('Aspectos a evaluar',r.get('Aspectos',''),max_chars=3000)
            instrumentos=st.text_area('Instrumentos previstos',r.get('Instrumentos',''),max_chars=3000)
            lugar=st.text_input('Espacio o lugar',r.get('Lugar',''),max_chars=3000)
            estados=list(s.ESTADOS)
            if not epp.actor()['director'] and r.get('Estado')!='Validada por Dirección':estados.remove('Validada por Dirección')
            estado=st.selectbox('Estado',estados,index=estados.index(r.get('Estado','Por programar')))
            guardar=st.form_submit_button('Guardar programación',type='primary')
        st.caption('La fecha aparece automáticamente en el calendario del equipo autorizado. No contiene nombres ni resultados de evaluación en el calendario general. Dirección valida el cronograma; no se presume aprobación.')
        if guardar:
            try:
                s.guardar(aid,ciclo,area,fecha,hora.strftime('%H:%M') if hora else '',aspectos,instrumentos,lugar,estado,r.get('ID_Programacion'),r.get('Revision',''))
                st.success('Programación guardada y vinculada al calendario.');st.rerun()
            except (ValueError,PermissionError,RuntimeError) as exc:st.warning(str(exc))
            except Exception:st.warning('No se confirmó el guardado. Tu captura permanece aquí; actualiza antes de repetir.')

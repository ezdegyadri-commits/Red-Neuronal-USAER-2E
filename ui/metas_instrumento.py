"""Instrumento personal y proyección directiva de la misma fuente versionada."""
from copy import deepcopy
from datetime import date
from hashlib import sha256
import json
import time
import pandas as pd
import streamlit as st
from services import metas_personales as s
from services import metas_instrumento as r


def cambiar(key,aid,widget,field):
    capture=st.session_state[key+'_borrador']
    if field=='Periodo':capture[field]=st.session_state[widget]
    else:
        row=next((f for f in capture['Filas'] if f['ID_Alumno']==aid),None)
        if row is None:
            row={'ID_Alumno':aid,'Metas':'','Recursos necesarios':''};capture['Filas'].append(row)
        if field=='tabla':row['Instrumento']=r.editar(row.get('Instrumento',r.vacia()),st.session_state[widget])
        elif field.startswith('Indicador:'):row.setdefault('Instrumento',r.vacia())['Indicadores'][field.split(':')[1]]=st.session_state[widget]
        elif field in ('Coherencia','Observaciones'):row.setdefault('Instrumento',r.vacia())[field]=st.session_state[widget]
        else:row[field]=st.session_state[widget]
    st.session_state[key+'_pending']=True;st.session_state.pop(key+'_requiere_accion',None)


def director(fecha):
    if st.button('Actualizar respuestas del equipo'):s.clear_cache(s.HOJA)
    docs=s.consolidar(fecha)
    if not docs:st.info('No hay capturas confirmadas para esta sesión.');return
    filas=[]
    for doc in docs:
        for row in doc['Filas']:
            total=r.resumen(row['Instrumento']) if row.get('Instrumento') else None
            filas.append({'Escuela':doc['Escuela'],'Docente':doc['Docente'],'Función':doc.get('Area','No registrada en captura anterior'),
                'Alumno':row['Alumno'],'Metas':row['Metas'],'Recursos necesarios':row['Recursos necesarios'],
                'Indicadores':f"{total['Respondidos']}/14" if total else 'Sin valoración',
                'Total /42':total['Total'] if total else None,'Coherencia /3':total['Coherencia'] if total else None})
    st.caption('Cada aportación conserva autor, función, escuela y alumno. No se suman puntajes entre docentes.')
    st.dataframe(pd.DataFrame(filas),hide_index=True,width='stretch')
    digest=sha256(json.dumps(docs,sort_keys=True).encode()).hexdigest()
    if st.button('Integrar respuestas en un PDF',type='primary'):
        from documents.metas_personales import generar_consolidado
        st.session_state['metas_consolidado_pdf']=(digest,generar_consolidado(docs))
    pdf=st.session_state.get('metas_consolidado_pdf')
    if pdf and pdf[0]==digest:st.download_button('Descargar instrumento consolidado',pdf[1],file_name='instrumento-equipo-'+str(fecha)+'.pdf',mime='application/pdf')
    with st.expander('Consultar instrumentos completos por docente'):
        for doc in docs:st.write(doc['Docente']+' · '+doc['Escuela']);st.json(doc)


def page(fecha_sesion=None):
    from ui.metas_personales import _guardar_pendiente,_estado_guardado
    st.header('Metas e instrumento de planeación')
    st.caption('Tu copia conserva tus aportes. Dirección integra las respuestas del equipo sin sustituir las capturas originales.')
    try:
        actor=s.identidad();fecha=fecha_sesion or st.date_input('Fecha de la sesión',value=date.today(),format='DD/MM/YYYY',key='metas_fecha')
        if actor['director']:director(fecha);return
        from services.planeacion_matricula import preparar,clave_escuela
        rows=preparar(s.planes.padron_autorizado()).fillna('').to_dict('records')
        if not rows:st.info('No hay alumnos disponibles en tu asignación.');return
        account=sha256(actor['cuenta'].encode()).hexdigest()[:12]
        escuelas={str(a['ID_Escuela']):str(a.get('Nombre_Escuela') or a['ID_Escuela']) for a in rows}
        escuela=None
        if actor['area'] in {'Psicología','Comunicación','Trabajo Social'}:
            escuela=st.selectbox('Escuela asignada',list(escuelas),format_func=escuelas.get,key='metas_'+account+'_escuela')
            rows=[a for a in rows if a['ID_Escuela']==escuela]
        mapa={str(a['ID_Alumno']):a for a in rows}
        labels={aid:a['Nombre_Completo']+' · '+str(a.get('Grado',''))+' '+str(a.get('Grupo',''))+(' · '+escuelas[a['ID_Escuela']] if escuela is None and len(escuelas)>1 else '') for aid,a in mapa.items()}
        duplicated={v for v in labels.values() if list(labels.values()).count(v)>1}
        labels={aid:v+(' · registro '+aid if v in duplicated else '') for aid,v in labels.items()}
        aid=st.selectbox('Alumno de mi asignación',list(mapa),index=None,placeholder='Elige un alumno para comenzar o continuar',format_func=labels.get,key='metas_'+account+'_'+str(escuela)+'_alumno')
        with st.expander('Mis capturas guardadas para continuar'):
            for doc in s.propias():
                st.write(doc['Fecha_Sesion']+' · '+doc['Escuela']+' · '+str(len(doc['Filas']))+' alumnos')
                st.caption(' · '.join(a['Alumno'] for a in doc['Filas']))
                with st.expander('Consultar copia completa · '+doc['Fecha_Sesion']+' · '+doc['Escuela']):
                    st.dataframe(pd.DataFrame(doc['Filas']),hide_index=True,width='stretch')
                    st.caption('También se conservan los antecedentes de alumnos que ya no aparecen en el padrón activo. No se cambian desde esta consulta.')
            st.caption('Selecciona la fecha de esa sesión y el alumno para continuar su captura.')
        if aid is None:return
        escuela=clave_escuela(mapa[aid]['ID_Escuela'])
        key='metas_'+sha256(json.dumps([actor['cuenta'],escuela,str(fecha)]).encode()).hexdigest()[:20]
        if key+'_doc' not in st.session_state:st.session_state[key+'_doc']=s.recuperar(escuela,fecha) or {}
        doc=st.session_state[key+'_doc']
        if key+'_borrador' not in st.session_state:
            st.session_state[key+'_ultimo_intento']=time.monotonic()
            st.session_state[key+'_borrador']={'Cuenta':actor['cuenta'],'Docente':actor['nombre'],'Area':actor['area'],'Escuela':escuelas[escuela],
                'ID_Escuela':escuela,'Fecha_Sesion':str(fecha),'Periodo':doc.get('Periodo',''),'Filas':deepcopy(doc.get('Filas',[]))}
        capture=st.session_state[key+'_borrador'];row=next((a for a in capture['Filas'] if a['ID_Alumno']==aid),{})
        prefix=key+'_'+sha256(aid.encode()).hexdigest()[:12]
        st.subheader(labels[aid]);st.caption(actor['nombre']+' · '+actor['area']+' · '+escuelas[escuela])
        st.text_input('Período que abarca la planificación',value=capture.get('Periodo',''),max_chars=200,key=key+'_periodo',on_change=cambiar,args=(key,aid,key+'_periodo','Periodo'))
        c1,c2=st.columns(2)
        c1.text_area('Metas para este alumno',value=row.get('Metas',''),height=160,max_chars=1500,key=prefix+'_metas',on_change=cambiar,args=(key,aid,prefix+'_metas','Metas'))
        c2.text_area('Recursos necesarios',value=row.get('Recursos necesarios',''),height=160,max_chars=1000,key=prefix+'_recursos',on_change=cambiar,args=(key,aid,prefix+'_recursos','Recursos necesarios'))
        value=row.get('Instrumento',r.vacia())
        with st.expander('Valorar mi planeación · indicadores y coherencia'):
            st.caption('Autoevaluación de la planeación, no del alumno. Pendiente no equivale a No lo realiza.')
            for i,text in enumerate(r.INDICADORES,1):
                texto,control=st.columns([3,2],vertical_alignment='center')
                texto.write(str(i)+'. '+text)
                widget=prefix+'_indicador_'+str(i);score=value['Indicadores'][str(i)]
                control.selectbox('Indicador '+str(i),[None,0,1,2,3],index=0 if score is None else score+1,
                    format_func=lambda n:'Pendiente' if n is None else f'{n} · {r.ESCALA[n]}',key=widget,
                    on_change=cambiar,args=(key,aid,widget,'Indicador:'+str(i)))
            total=r.resumen(value)
            st.caption(f"Respondidos: {total['Respondidos']}/14 · "+('Total: '+str(total['Total'])+'/42' if total['Total'] is not None else 'Subtotal provisional: '+str(total['Subtotal'])+'; faltan indicadores.'))
            st.markdown('**Análisis de la coherencia interna de la planeación**');st.write(r.COHERENCIA)
            st.selectbox('Valoración de coherencia',list(r.ESCALA),index=value['Coherencia'],placeholder='Pendiente',format_func=lambda n:f'{n} · {r.ESCALA[n]}',key=prefix+'_coherencia',on_change=cambiar,args=(key,aid,prefix+'_coherencia','Coherencia'))
            if value['Coherencia'] is not None:st.info(r.DESCRIPTORES[value['Coherencia']])
            st.text_area('Observaciones y ajustes por realizar',value=value['Observaciones'],max_chars=2000,key=prefix+'_observaciones',on_change=cambiar,args=(key,aid,prefix+'_observaciones','Observaciones'))
        if st.button('Guardar instrumento',type='primary',key=key+'_guardar'):
            if _guardar_pendiente(key,manual=True):st.toast('Captura confirmada.' if st.session_state.get(key+'_doc') else 'No hay cambios pendientes.')
        _estado_guardado(key)
        st.caption('Los cambios se conservan al salir del campo y se envían agrupados cada 15 segundos. Cambiar de alumno no borra las aportaciones de los demás.')
        with st.expander('Respaldo y PDF de mi copia'):
            st.download_button('Descargar respaldo de mi captura',json.dumps(capture,ensure_ascii=False,indent=2),file_name='metas-'+str(fecha)+'.json',mime='application/json',key=key+'_respaldo')
            if st.button('Preparar PDF de mi instrumento',key=key+'_preparar_pdf'):
                from documents.metas_personales import generar_pdf
                printable=deepcopy(capture)
                for a in printable['Filas']:a['Alumno']=a.get('Alumno') or labels.get(a['ID_Alumno'],'Antecedente conservado')
                st.session_state[key+'_pdf']=(json.dumps(capture,sort_keys=True),generar_pdf(printable))
            pdf=st.session_state.get(key+'_pdf')
            if pdf and pdf[0]==json.dumps(capture,sort_keys=True):st.download_button('Descargar PDF de mi instrumento',pdf[1],file_name='instrumento-'+str(fecha)+'.pdf',mime='application/pdf',key=key+'_descargar_pdf')
        with st.expander('Aportaciones de mi copia en esta escuela'):
            for a in capture['Filas']:st.write((a.get('Alumno') or labels.get(a['ID_Alumno'],'Antecedente conservado'))+' — '+a['Metas'])
    except (ValueError,PermissionError,RuntimeError) as exc:st.warning(str(exc))
    except Exception:st.warning('No se pudo consultar o guardar el instrumento. Tu captura en sesión se conserva; descarga un respaldo antes de cerrar.')

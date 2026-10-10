"""Guía de trabajo de especialistas; reutiliza el guardado de planeación."""
import calendar
from copy import deepcopy
from datetime import date
import pandas as pd
import streamlit as st
from services import planeacion_equipo as equipo


def _campo(prefix,key,campo,persist):
    doc=deepcopy(st.session_state[prefix+'_doc'])
    value=st.session_state[key]
    if isinstance(value,date):value=value.isoformat()
    doc['metadatos']['equipo']['edicion_sesion'][campo]=value
    st.session_state[prefix+'_doc']=doc
    st.session_state.pop(prefix+'_pdf',None)
    persist(prefix,automatic=True)


def _tabla(prefix,key,tabla,base,persist):
    doc=deepcopy(st.session_state[prefix+'_doc']);rows=deepcopy(base)
    for i,values in st.session_state.get(key,{}).get('edited_rows',{}).items():
        rows[int(i)].update(values)
    doc['metadatos']['equipo'][tabla]=rows
    st.session_state[prefix+'_doc']=doc
    st.session_state.pop(prefix+'_pdf',None);persist(prefix,automatic=True)


def _familia(prefix,key,persist):
    doc=deepcopy(st.session_state[prefix+'_doc'])
    doc['metadatos']['equipo']['sugerencia_familia']=st.session_state[key]
    st.session_state[prefix+'_doc']=doc
    st.session_state.pop(prefix+'_pdf',None);persist(prefix,automatic=True)


def calendario(prefix,doc):
    e=doc['metadatos']['equipo'];desde,hasta=equipo.limites(doc)
    meses=[(desde.year,desde.month+i) for i in range(3)]
    meses=[(y,m) for y,m in meses if m<=12 and date(y,m,1)<=hasta]
    nombres=['','enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre']
    y,m=st.selectbox('Ver sesiones del mes',meses,format_func=lambda ym:nombres[ym[1]]+' '+str(ym[0]),key=prefix+'_equipo_month')
    from services.cronogramas import DIAS_INHABILES
    for col,label in zip(st.columns(7),['Lun','Mar','Mié','Jue','Vie','Sáb','Dom']):col.caption(label)
    for semana in calendar.Calendar().monthdayscalendar(y,m):
        for col,dia in zip(st.columns(7),semana):
            if not dia:continue
            fecha=date(y,m,dia);key=fecha.isoformat()
            with col:
                st.markdown('**'+str(dia)+'**')
                motivo=DIAS_INHABILES.get(key,'Fin de semana' if fecha.weekday()>4 else '')
                if motivo:st.caption('No lectivo · '+motivo)
                for s in e['sesiones']:
                    if s['fecha']==key:
                        st.write(s['subgrupo']);st.caption(s['contexto']+' · '+s['objetivo'])
    st.caption('El calendario muestra lo que tú planeaste; no publica avisos ni modifica el cronograma mensual.')


def panel(prefix,doc,persist,abrir,compact=False):
    if not equipo.aplica(doc):return
    if 'equipo' not in doc['metadatos']:
        st.info('Puedes incorporar la organización del equipo sin reemplazar lo que ya escribiste.')
        if st.button('Preparar organización del equipo',key=prefix+'_equipo_prepare'):
            abrir(prefix,equipo.preparar(doc));persist(prefix);st.rerun()
        return
    e=st.session_state[prefix+'_doc']['metadatos']['equipo'];area=doc['datos']['Función']
    generation=st.session_state.get(prefix+'_generation',0);base=f'{prefix}_{generation}_equipo'
    st.subheader('Organizar mi trabajo · '+area)
    st.caption('Define quiénes trabajarán juntos, prepara sesiones y revisa el formato. Los resultados se registran después de realizar las actividades.')
    with st.expander('Acuerdos de zona y guía de mi área'):
        st.write(equipo.contexto_zona(doc)['guia'])
        st.caption('Estos acuerdos son referentes de planeación. Las orientaciones del CAM no se trasladan automáticamente a la USAER.')
        for source in equipo.contexto_zona(doc)['fuentes']:st.caption('Fuente revisada: '+source['titulo']+' · '+source['edicion'])
        st.caption({'Psicología':'Objetivos educativos de convivencia, participación y bienestar; no diagnósticos ni tratamientos clínicos.',
                    'Comunicación':'Expresión y comprensión, medios de comunicación accesibles y participación en aula, según la evidencia.',
                    'Trabajo Social':'Barreras compartidas y apoyos viables en aula, escuela, familia y comunidad; no atribuirlas a todas las familias.'}[area])
    with st.expander('1. Organizar mis subgrupos',expanded=not bool(e['subgrupos'])):
        labels={a['ID_Alumno']:a['Nombre del alumno']+' · '+str(a['Grado'])+' '+str(a['Grupo']) for a in doc['datos']['Alumnos']}
        nombre=st.text_input('Nombre del subgrupo',key=base+'_group_name',placeholder='Ejemplo: Subgrupo 1',max_chars=100)
        ids=st.multiselect('Alumnos de este subgrupo',list(labels),format_func=labels.get,key=base+'_group_ids')
        st.caption('Para cambiar integrantes, escribe el mismo nombre y guarda la selección completa. No se incluyen alumnos de otras escuelas.')
        if st.button('Guardar subgrupo',disabled=not nombre.strip() or not ids,key=base+'_group_save'):
            try:abrir(prefix,equipo.guardar_subgrupo(st.session_state[prefix+'_doc'],nombre,ids));persist(prefix);st.rerun()
            except (ValueError,PermissionError) as exc:st.warning(str(exc))
        for g in e['subgrupos']:st.write(g['nombre']+': '+', '.join(labels[i] for i in g['alumnos'] if i in labels))
    if area=='Psicología' and (not compact or st.toggle('Editar metas de las cinco competencias',key=base+'_editar_competencias')):
        with st.expander('2. Preparar las cinco competencias emocionales',expanded=True):
            st.caption('Describe necesidades documentadas y metas observables; estos campos no se rellenan a partir del diagnóstico ni del ejemplo de zona.')
            key=base+'_competencias';bk=key+'_base'
            if bk not in st.session_state:st.session_state[bk]=deepcopy(e['competencias'])
            st.data_editor(pd.DataFrame(st.session_state[bk]),disabled=['Competencia'],hide_index=True,
                key=key,on_change=_tabla,args=(prefix,key,'competencias',st.session_state[bk],persist),use_container_width=True)
    with st.expander('3. Calendarizar y editar sesiones',expanded=True):
        st.caption('Cada sesión se incorpora a la dosificación del formato. El texto que ya redactaste a mano se conserva.')
        if not e['subgrupos']:st.info('Guarda primero un subgrupo para preparar sesiones.')
        else:
            byid={s['id']:s for s in e['sesiones']}
            seleccionado=st.selectbox('Sesión para trabajar',['Nueva sesión']+list(byid),format_func=lambda i:i if i=='Nueva sesión' else byid[i]['fecha']+' · '+byid[i]['subgrupo'],key=base+'_selected_session')
            if st.button('Abrir sesión seleccionada',key=base+'_open_session'):
                updated=deepcopy(st.session_state[prefix+'_doc'])
                updated['metadatos']['equipo']['edicion_sesion']=deepcopy(byid.get(seleccionado,{}))
                abrir(prefix,updated);persist(prefix);st.rerun()
            edit=e.get('edicion_sesion',{});desde,hasta=equipo.limites(doc)
            st.caption('Editando: '+(edit.get('fecha','')+' · '+edit.get('subgrupo','') if edit.get('id') else 'Nueva sesión'))
            def opciones(campo,label,opciones,default=None):
                value=edit.get(campo,default or opciones[0]);key=base+'_session_'+campo
                return st.selectbox(label,opciones,index=opciones.index(value) if value in opciones else 0,key=key,
                    on_change=_campo,args=(prefix,key,campo,persist))
            fecha=date.fromisoformat(edit.get('fecha') or desde.isoformat());key=base+'_session_fecha'
            fecha=st.date_input('Fecha de la sesión',value=fecha,min_value=desde,max_value=hasta,key=key,on_change=_campo,args=(prefix,key,'fecha',persist))
            grupo=opciones('subgrupo','Subgrupo',[g['nombre'] for g in e['subgrupos']])
            contexto=opciones('contexto','Dónde se realizará',equipo.contextos(doc))
            from services.cronogramas import DIAS_INHABILES
            if fecha.weekday()>4 or fecha.isoformat() in DIAS_INHABILES:st.warning('Fecha no lectiva: verifica su pertinencia y ajusta si se trata de atención a alumnos.')
            competencias=[]
            if area=='Psicología':
                key=base+'_session_competencias'
                competencias=st.multiselect('Competencias que se trabajarán',list(equipo.COMPETENCIAS),default=edit.get('competencias',[]),key=key,on_change=_campo,args=(prefix,key,'competencias',persist))
            campos={}
            for campo,label,ayuda in [('objetivo','Qué queremos lograr','El alumno identifica… / Los alumnos expresan…'),
                 ('actividad','Cómo lo trabajaremos','Inicio, desarrollo y cierre, con acciones concretas.'),
                 ('apoyos','Apoyos y ajustes','Cómo facilitarás el acceso y la participación.'),
                 ('recursos','Materiales y recursos','Solo materiales disponibles o por confirmar.'),
                 ('seguimiento','Cómo reconoceremos el avance','Qué observarás, qué registrarás y cuándo lo revisarás.')]:
                key=base+'_session_'+campo
                campos[campo]=st.text_area(label,value=edit.get(campo,''),placeholder=ayuda,key=key,max_chars=4000,on_change=_campo,args=(prefix,key,campo,persist))
            if st.button('Guardar sesión en la planeación',key=base+'_save_session'):
                try:
                    updated=equipo.guardar_sesion(st.session_state[prefix+'_doc'],{**campos,'fecha':fecha.isoformat(),'subgrupo':grupo,'contexto':contexto,'competencias':competencias},edit.get('id',''))
                    abrir(prefix,updated);persist(prefix);st.rerun()
                except (ValueError,PermissionError) as exc:st.warning(str(exc))
            if edit.get('id') and st.checkbox('Quitar esta sesión del borrador actual',key=base+'_delete_confirm'):
                if st.button('Quitar sesión',key=base+'_delete_session'):
                    abrir(prefix,equipo.quitar_sesion(st.session_state[prefix+'_doc'],edit['id']));persist(prefix);st.rerun()
            if not compact or st.toggle('Ver calendario',key=base+'_ver_calendario'):
                calendario(prefix,st.session_state[prefix+'_doc'])
    if not compact or st.toggle('Editar complemento horizontal de zona',key=base+'_ver_horizontal'):
      with st.expander('4. Planeación grupal horizontal de zona'):
        st.caption('Nombres y condiciones vienen del padrón. Registra la situación inicial con su fuente; deja la final pendiente hasta contar con resultados. Las fechas de derivación no se adivinan.')
        labels={a['ID_Alumno']:a['Nombre del alumno'] for a in doc['datos']['Alumnos']}
        key=base+'_grupal';bk=key+'_base'
        if bk not in st.session_state:st.session_state[bk]=[{**deepcopy(r),'Nombre del alumno':labels.get(r['ID_Alumno'],'')} for r in e['grupal']]
        st.data_editor(pd.DataFrame(st.session_state[bk]),disabled=['ID_Alumno','Nombre del alumno'],hide_index=True,key=key,
            column_config={'ID_Alumno':None},
            on_change=_tabla,args=(prefix,key,'grupal',st.session_state[bk],persist),use_container_width=True)
        st.dataframe(pd.DataFrame(equipo.tablas_salida(st.session_state[prefix+'_doc'])[-1][2]).drop(columns=['ID_Alumno'],errors='ignore'),hide_index=True,use_container_width=True)
    if area=='Psicología':
        key=base+'_familia'
        st.text_area('Sugerencia prevista para la familia y referencia de su hoja',value=e.get('sugerencia_familia',''),key=key,
                     on_change=_familia,args=(prefix,key,persist),help='Describe lo que propondrás. Un plan no demuestra que la sugerencia ya fue entregada.')
    pendientes=equipo.revisar(st.session_state[prefix+'_doc'])
    with st.expander('Revisar acuerdos antes de compartir',expanded=bool(pendientes)):
        if pendientes:
            for pendiente in pendientes:st.write('Pendiente: '+pendiente)
        else:st.success('La organización cumple los puntos revisables de los acuerdos. Confirma la pertinencia educativa.')

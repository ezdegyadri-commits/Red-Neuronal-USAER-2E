"""Repositorio de juntas por fecha; metas y cuadro de metodologías vivos."""
from copy import deepcopy
from datetime import date
from hashlib import sha256
import json
import time
import pandas as pd
import streamlit as st
from services import juntas_academicas as s
from services.juntas_metodologias_catalogo import CATALOGO,POR_ID


def _guardar(key,manual=False):
    if not st.session_state.get(key+'_pending'):return True
    if not manual and time.monotonic()-st.session_state.get(key+'_intento',0)<15:return False
    st.session_state[key+'_intento']=time.monotonic()
    capture=st.session_state[key+'_borrador']
    if capture['Cuenta']!=s.identidad()['cuenta']:raise PermissionError('La captura no corresponde a esta cuenta.')
    try:
        saved=s.guardar(capture['Fecha_Sesion'],capture['Captura'],st.session_state[key+'_doc'].get('Revision',''))
        st.session_state[key+'_doc']=saved;st.session_state[key+'_pending']=False;st.session_state.pop(key+'_error',None)
        return True
    except Exception as exc:
        st.session_state[key+'_error']=str(exc) if isinstance(exc,(ValueError,RuntimeError,PermissionError)) else 'La base no confirmó el guardado. Reintenta o descarga tu respaldo.'
        return False


@st.fragment(run_every=15)
def _estado(key):
    try:cuenta=s.identidad()['cuenta']
    except PermissionError:
        st.caption('Recupera la sesión para confirmar el guardado; las anotaciones pendientes no se descartaron.');return
    for k,v in list(st.session_state.items()):
        if k.startswith('juntas_') and k.endswith('_pending') and v and st.session_state.get(k[:-8]+'_borrador',{}).get('Cuenta')==cuenta:_guardar(k[:-8])
    if st.session_state.get(key+'_pending'):st.warning(st.session_state.get(key+'_error','Anotaciones pendientes de confirmación central.'))
    elif st.session_state[key+'_doc']:st.caption('Guardado confirmado · '+st.session_state[key+'_doc']['Guardado_En'])


def _cambio(key,code,widget,field):
    capture=st.session_state[key+'_borrador']['Captura']
    capture['Respuestas'].setdefault(code,s.registro_vacio())[field]=st.session_state[widget]
    st.session_state[key+'_pending']=True


def proteger_salida(key):
    keys=[k[:-8] for k,v in list(st.session_state.items()) if k.startswith('juntas_') and k.endswith('_pending') and v and st.session_state.get(k[:-8]+'_borrador',{}).get('Cuenta')==st.session_state.get('usuario')]
    if not keys:return True
    st.warning('Hay anotaciones de juntas pendientes. Confirma el guardado o descarga un respaldo antes de cerrar.')
    for p in keys:st.download_button('Respaldar cuadro de metodologías',json.dumps(st.session_state[p+'_borrador'],ensure_ascii=False,indent=2),file_name='metodologias-pendientes.json',mime='application/json',key=key+p)
    if st.button('Guardar anotaciones de juntas',key=key+'_guardar_juntas'):
        results=[_guardar(p,True) for p in keys]
        if all(results):return True
    return st.checkbox('Ya descargué los respaldos de juntas; continuar al cierre',key=key+'_respaldo_juntas')


def _cuadro(fecha):
    actor=s.identidad()
    st.subheader('Metodologías y estrategias específicas')
    st.caption('Material aportado por Dirección. A, C y P conservan las letras del original, sin atribuirles un significado. No son una recomendación automática para un alumno.')
    with st.expander('Consultar el cuadro de referencia completo'):
        st.caption('Las metodologías se conservan como material de consulta de la junta. Su pertinencia se decide con las necesidades y evidencias de cada alumno, no por diagnóstico automático.')
        st.dataframe(pd.DataFrame([{'Área':a[1],'Necesidades educativas específicas':a[2],'Metodologías, programas y estrategias específicas':a[3],'A':'','C':'','P':''} for a in CATALOGO]),hide_index=True,width='stretch')
    if actor['director']:
        if st.button('Actualizar cuadros del equipo',key='juntas_actualizar'):s.clear_cache(s.HOJA)
        docs=s.listar(fecha,equipo=True)
        filas=[]
        for d in docs:
            for code,row in d['Captura']['Respuestas'].items():filas.append({'Docente':d['Docente'],'Función':d['Area'],'Necesidad':POR_ID[code][2],**row})
        if not filas:st.info('No hay anotaciones confirmadas para esta fecha.');return
        st.dataframe(pd.DataFrame(filas),hide_index=True,width='stretch')
        if st.button('Preparar cuadro integrado en PDF'):
            from documents.juntas_academicas import generar_pdf
            st.session_state['juntas_pdf']=(json.dumps(docs,sort_keys=True),generar_pdf(docs,fecha))
        pdf=st.session_state.get('juntas_pdf')
        if pdf and pdf[0]==json.dumps(docs,sort_keys=True):st.download_button('Descargar cuadro integrado',pdf[1],file_name='metodologias-equipo-'+fecha+'.pdf',mime='application/pdf')
        return
    key='juntas_'+sha256(json.dumps([actor['cuenta'],fecha]).encode()).hexdigest()[:20]
    if key+'_doc' not in st.session_state:st.session_state[key+'_doc']=next(iter(s.listar(fecha)),{})
    if key+'_borrador' not in st.session_state:
        st.session_state[key+'_intento']=time.monotonic()
        st.session_state[key+'_borrador']={'Cuenta':actor['cuenta'],'Fecha_Sesion':fecha,'Captura':deepcopy(st.session_state[key+'_doc'].get('Captura',s.vacia()))}
    categorias=list(dict.fromkeys(a[1] for a in CATALOGO))
    categoria=st.selectbox('Área del cuadro',categorias,key=key+'_categoria')
    opciones=[a[0] for a in CATALOGO if a[1]==categoria]
    code=st.selectbox('Necesidad educativa específica',opciones,format_func=lambda c:POR_ID[c][2],key=key+'_'+categoria+'_necesidad')
    st.markdown('**Metodologías, programas y estrategias del documento**');st.text(POR_ID[code][3])
    row=st.session_state[key+'_borrador']['Captura']['Respuestas'].get(code,s.registro_vacio())
    for column,field in zip(st.columns(3),('A','C','P')):
        widget=key+'_'+code+'_'+field
        column.checkbox(field,value=row[field],key=widget,on_change=_cambio,args=(key,code,widget,field))
    for field in ('Aplicación prevista','Evidencia y seguimiento'):
        widget=key+'_'+code+'_'+field
        st.text_area(field,value=row[field],max_chars=1500,key=widget,on_change=_cambio,args=(key,code,widget,field))
    if st.button('Guardar mi cuadro',type='primary',key=key+'_guardar'):
        if _guardar(key,True):st.toast('Anotaciones confirmadas.' if st.session_state[key+'_doc'] else 'No hay cambios pendientes.')
    _estado(key)
    with st.expander('Mi cuadro completo y respaldo'):
        st.dataframe(pd.DataFrame([{'Necesidad':POR_ID[c][2],**v} for c,v in st.session_state[key+'_borrador']['Captura']['Respuestas'].items()]),hide_index=True,width='stretch')
        st.download_button('Descargar respaldo del cuadro',json.dumps(st.session_state[key+'_borrador'],ensure_ascii=False,indent=2),file_name='metodologias-'+fecha+'.json',mime='application/json',key=key+'_backup')
        if st.button('Preparar PDF de mi cuadro',key=key+'_pdf'):
            from documents.juntas_academicas import generar_pdf
            d={**st.session_state[key+'_borrador'],'Docente':actor['nombre'],'Area':actor['area']}
            st.session_state[key+'_pdf_data']=(json.dumps(d,sort_keys=True),generar_pdf([d],fecha))
        pdf=st.session_state.get(key+'_pdf_data');d={**st.session_state[key+'_borrador'],'Docente':actor['nombre'],'Area':actor['area']}
        if pdf and pdf[0]==json.dumps(d,sort_keys=True):st.download_button('Descargar PDF de mi cuadro',pdf[1],file_name='metodologias-'+fecha+'.pdf',mime='application/pdf',key=key+'_descargar')


def page():
    st.header('Juntas académicas')
    try:
        fechas=s.fechas()
        fecha=st.selectbox('Fecha de la junta',fechas,index=fechas.index(s.PRIMERA_SESION),format_func=lambda v:date.fromisoformat(v).strftime('%d/%m/%Y'),key='juntas_fecha')
        st.caption('Materiales y capturas de la sesión del '+date.fromisoformat(fecha).strftime('%d/%m/%Y'))
        material=st.segmented_control('Material de trabajo',['Metas e instrumento de planeación','Cuadro de metodologías'],default='Metas e instrumento de planeación',key='juntas_material')
        if material=='Cuadro de metodologías':_cuadro(fecha)
        elif material:
            from ui.metas_personales import page as metas
            metas(date.fromisoformat(fecha))
    except (ValueError,RuntimeError,PermissionError) as exc:st.warning(str(exc))
    except Exception:st.warning('No se pudo consultar la junta. Las capturas pendientes en esta sesión se conservan; no cierres sin respaldo.')

"""Accesos explícitos por rol: no monta editores ocultos ni cambia documentos."""
import streamlit as st


def opciones(actor):
    compartido=('equipo','Planeación grupal compartida','Continuar la misma hoja de apoyo, psicología, comunicación y trabajo social.','👥')
    if actor['director']:
        return [('revision','Revisión de Dirección','Consultar y revisar las planeaciones del equipo.','📋'),compartido]
    if actor['area']=='Aprendizaje':
        propio=('propio','Mi planeación de apoyo','Elegir alumnos individuales, un grupo o un grado y trabajar en mi formato.','📝')
    elif actor['area'] in ('Psicología','Comunicación','Trabajo Social'):
        propio=('propio','Mi planeación de '+actor['area'],'Preparar mi intervención individual o de subgrupo en el formato de mi área.','📝')
    else:raise PermissionError('Esta cuenta no tiene función de planeación.')
    return [propio,compartido]


def menu(base,actor):
    st.subheader('¿Dónde quieres trabajar?')
    st.caption('Abre una opción. Solo verás las herramientas de tu función.')
    for col,(id,titulo,detalle,icono) in zip(st.columns(2),opciones(actor)):
        with col:
            key=base+'_acceso_'+id
            st.html('<style>.st-key-'+key+' button{min-height:110px;font-size:1.15rem;font-weight:650;border:1px solid #72979d;border-radius:16px;box-shadow:0 5px 18px #173e4814;transition:transform .18s ease,box-shadow .18s ease;background:linear-gradient(135deg,#f0f8f7,#fff);color:#173e48}.st-key-'+key+' button:hover{transform:translateY(-3px);box-shadow:0 9px 23px #173e4826}.st-key-'+key+' button:active{transform:scale(.98)}.st-key-'+key+' button:focus-visible{outline:3px solid #147d88;outline-offset:3px}@media(prefers-reduced-motion:reduce){.st-key-'+key+' button{transition:none}.st-key-'+key+' button:hover,.st-key-'+key+' button:active{transform:none}}</style>')
            with st.container(key=key):
                if st.button(titulo,icon=icono,width='stretch',key=key+'_abrir'):
                    st.session_state[base+'_submodulo']=id;st.rerun()
            st.caption(detalle)

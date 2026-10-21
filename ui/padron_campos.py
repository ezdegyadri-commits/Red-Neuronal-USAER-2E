"""Mismos selectores para editar categorías sin inventar variantes."""
from datetime import date
import streamlit as st
from services.padron_catalogos import CATALOGOS,CONDICIONES,canonico,fecha_documental

def capturar(campo,etiqueta,valor,key):
    if campo=='Condiciones_Adicionales':
        import re
        seleccion=[canonico('Condicion_Discapacidad',v) for v in re.split(r'[;,]',str(valor)) if v.strip()]
        opciones=list(dict.fromkeys([*CONDICIONES,*seleccion]))
        return '; '.join(st.multiselect(etiqueta,opciones,default=seleccion,key=key))
    if campo in CATALOGOS:
        actual=canonico(campo,valor);opciones=['',*CATALOGOS[campo]]
        if actual and actual not in opciones:
            opciones.append(actual)
            st.caption('Se conserva el valor histórico; elige una categoría del catálogo para homologarlo.')
        return st.selectbox(etiqueta,opciones,index=opciones.index(actual),key=key,format_func=lambda v:v or 'Sin dato')
    if campo in ('Fecha_Derivacion','Fecha_Nacimiento'):
        try:actual=fecha_documental(valor)
        except ValueError:actual=None;st.caption('Fecha histórica por verificar: '+str(valor))
        elegida=st.date_input(etiqueta,value=actual,min_value=date(1900,1,1),format='DD/MM/YYYY',key=key)
        return elegida.isoformat() if elegida else valor
    if campo=='Edad_1_Septiembre':
        try:actual=int(float(valor)) if str(valor).strip() else None
        except ValueError:actual=None
        if actual is not None and not 0<=actual<=100:
            st.caption('Edad histórica por verificar: '+str(valor));actual=None
        elegida=st.number_input(etiqueta,min_value=0,max_value=100,value=actual,step=1,key=key)
        return str(elegida) if elegida is not None else valor
    return st.text_input(etiqueta,value=valor,key=key)

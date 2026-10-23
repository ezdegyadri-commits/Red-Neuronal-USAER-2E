"""Todo ficticio: sin Google, alumnos reales ni servicios de IA."""
from copy import deepcopy
from datetime import date
from unittest.mock import patch
import pandas as pd
import streamlit as st
from services import metas_personales as metas,juntas_academicas as juntas

actor={'cuenta':'cuenta-ficticia','nombre':'Docente ficticia','rol':'APOYO','area':'Aprendizaje','director':False}
actor.update(st.session_state.get('qa_actor',{}))
if st.query_params.get('perfil')=='especialista':actor.update(area='Comunicación',rol='COMUNICACION')
if st.query_params.get('perfil')=='direccion':actor.update(director=True,area='Dirección',rol='DIRECTOR')
padron=[{'ID_Alumno':'A1','ID_Escuela':'ESC-001','Nombre_Escuela':'Damián Carmona','Nombre_Completo':'Alumno ficticio Uno','Grado':'1°','Grupo':'A'},
        {'ID_Alumno':'A2','ID_Escuela':'ESC-001','Nombre_Escuela':'Damián Carmona','Nombre_Completo':'Alumno ficticio Dos','Grado':'6°','Grupo':'B'},
        {'ID_Alumno':'B1','ID_Escuela':'ESC-002','Nombre_Escuela':'Escuela ficticia Dos','Nombre_Completo':'Alumno ficticio Tres','Grado':'2°','Grupo':'A'}]
if not actor['director'] and actor['area']=='Aprendizaje':padron=padron[:2]
st.session_state.setdefault('qa_rows',{})
st.session_state.setdefault('qa_envios',0)


class Sheet:
    def __init__(self,name,headers):self.name=name;self.headers=headers
    def row_values(self,n):return self.headers
    def append_rows(self,rows,value_input_option):
        assert value_input_option=='RAW'
        if st.session_state.get('qa_fallo'):raise ConnectionError('Simulado')
        st.session_state.qa_rows.setdefault(self.name,[]).extend(dict(zip(self.headers,row)) for row in rows)
        st.session_state.qa_envios+=len(rows)


def sheet(name,headers):return Sheet(name,headers)
def read(name):return pd.DataFrame(deepcopy(st.session_state.qa_rows.get(name,[])))


# Los fragmentos periódicos también deben permanecer aislados después de que
# termine la ejecución principal del fixture en el navegador real.
metas.planes.identidad=lambda:actor
juntas.identidad=lambda:actor
metas.planes.padron_autorizado=lambda:pd.DataFrame(padron)
metas.repo.read=read
metas.ensure_headers=sheet
juntas.ensure_headers=sheet
metas.clear_cache=lambda *args:None
juntas.clear_cache=lambda *args:None
if st.session_state.get('qa_page')=='juntas' or st.query_params.get('juntas')=='1':
    from ui.juntas_academicas import page
    page()
else:
    from ui.metas_personales import page
    page(date(2026,10,23))

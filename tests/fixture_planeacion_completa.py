"""Demostración totalmente ficticia: no Sheets, Drive ni Gemini."""
from copy import deepcopy
import streamlit as st
import pandas as pd
from services import planeacion as s
from ui import planeacion_generacion as generador
from ui.planeacion import _planeacion_page_clasica as planeacion_page
from tests.test_planeacion_completa import resultado
st.set_page_config(layout='wide')
area=st.radio('Perfil ficticio',['Aprendizaje','Psicología','Comunicación','Trabajo Social','Dirección'])
actor={'cuenta':'demo-'+area,'nombre':'Autor ficticio','area':area,'director':area=='Dirección','rol':'APOYO' if area=='Aprendizaje' else area,'perfil':None}
st.session_state.update(autenticado=True,usuario=actor['cuenta'],nombre=actor['nombre'],rol=actor['rol'])
alumnos=[{'ID_Alumno':'A1','Nombre_Completo':'Alumno ficticio Uno','ID_Escuela':'E1','Nombre_Escuela':'Escuela ficticia','CCT_Escuela':'TEST','Grado':'5','Grupo':'A','Tipo_Atencion':'Grupal'}]
s.identidad=lambda:actor;s.padron_autorizado=lambda:pd.DataFrame(alumnos)
s.precargar_docentes_regulares=lambda doc:doc
s.repo.escuelas=lambda:pd.DataFrame([{'ID_Escuela':'E1','Nombre_Escuela':'Escuela ficticia','CCT':'TEST'}])
def evidencias(doc):
    return ([{'tipo':'ACTA','alumno':'A1','referencia':'E1','fecha':'2026-10-02','registro':'Registro ficticio','texto':'Participa en lectura con tarjetas. Necesita apoyos para expresar emociones y tomar turnos.','alcance':'individual','vinculo_verificado':True}],[])
s.evidencias=evidencias
st.session_state.setdefault('versiones_ficticias',[]);st.session_state.setdefault('llamadas_ficticias',0)
versiones_ficticias=st.session_state.versiones_ficticias
fallo_guardado_ficticio=st.session_state.get('fallo_guardado_ficticio')
def guardar(doc,estado='BORRADOR',observaciones=None):
    copia=deepcopy(doc);copia.update(estado=estado,revision=str(len(versiones_ficticias)+1),guardado_en='2026-10-06T11:00:00')
    versiones_ficticias.append(copia);return copia
def listar(todas=False):
    docs=[d for d in versiones_ficticias if actor['director'] or d['cuenta']==actor['cuenta']]
    return docs if todas else list({d['id']:d for d in docs}.values())
s.guardar=guardar;s.listar=listar;s.refrescar=lambda:None
s.versiones_actuales=lambda:versiones_ficticias
def aportar(doc,filas,observaciones):
    from services.planeacion_colaboracion import aportar as acotado
    actual=next(d for d in reversed(versiones_ficticias) if d['id']==doc['id'])
    if doc['revision']!=actual['revision']:raise RuntimeError('Documento actualizado por el equipo.')
    return guardar(acotado(actual,actor,filas,observaciones))
s.guardar_aportacion=aportar
def generar(resumen,formato,area,contexto,ajustes,aliases,evidencias):
    st.session_state.llamadas_ficticias+=1
    st.session_state.ultima_solicitud_ficticia={'resumen':resumen,'contexto':deepcopy(contexto),'ajustes':deepcopy(ajustes),'aliases':aliases,'evidencias':evidencias}
    propuesta=resultado({'contexto':contexto,'aliases':aliases,'evidencias':evidencias},area,n=contexto.get('actividades_solicitadas',6))
    if contexto.get('contextos_solicitados'):
        for i,row in enumerate(propuesta['unidades']):row['contexto']=contexto['contextos_solicitados'][i%len(contexto['contextos_solicitados'])]
    return propuesta
generador.generar_completa=generar
from ui import planeacion_tareas as tareas
from concurrent.futures import Future
from services.planeacion_edicion import huella
def iniciar_ficticio(prefix,solicitud,doc):
    future=Future()
    future.set_result(generar(solicitud['resumen'],doc['formato'],doc['datos']['Función'],solicitud['contexto'],solicitud['ajustes'],solicitud['aliases'],solicitud['evidencias']))
    st.session_state[prefix+'_ia_trabajo']={'future':future,'solicitud':solicitud,'cuenta':actor['cuenta'],'documento':doc['id'],'huella':huella(st.session_state[prefix+'_doc']),'revision':doc.get('revision','')}
tareas.iniciar=iniciar_ficticio
from ui import planeacion as u
st.session_state[u._prefix()+'_submodulo'] = 'revision' if actor['director'] else 'propio'
planeacion_page()

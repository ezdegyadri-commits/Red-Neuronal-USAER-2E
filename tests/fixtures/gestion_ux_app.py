"""QA visual aislada. Ningún servicio consulta o escribe la base institucional."""
from copy import deepcopy
from unittest.mock import patch
import pandas as pd
import streamlit as st
from data import repository as repo
from services import padron_movimientos as mv,archivo_expediente as ar,planeacion,epp,borradores_horarios as bh
from services import expedientes as ex
from ui import theme,estadisticas,horarios_apoyo as h
from tests.test_padron_archivo_ux import ALUMNO

st.set_page_config(layout='wide',page_title='USAER · QA gestión')
theme.inject()
st.session_state.update(autenticado=True,usuario='qa-sin-base-real',nombre='Mtra. Cindy Mayanín Burgos González',rol='APOYO',escuelas_permitidas='Damián Carmona')
if 'qa_padron' not in st.session_state:
    st.session_state.qa_padron=[{**ALUMNO,'ID_Alumno':'QA'+str(i),'Nombre_Completo':f'Estudiante de prueba {i:02d}',
        'Grado':'2°' if i%2 else '3°','Edad_1_Septiembre':7+i%3,'Sexo':'H' if i%2 else 'M','Condicion_Discapacidad':'Aprendizaje'} for i in range(1,32)]
frame=pd.DataFrame(st.session_state.qa_padron)
st.caption('ENTORNO DE PRUEBA · DATOS FICTICIOS · SIN CONEXIÓN A LA BASE REAL')
vista=st.sidebar.radio('Módulo',['Padrón','Horarios','Expedientes'])
catalogo=pd.DataFrame([{'ID_Escuela':c,'Nombre_Escuela':n,'CCT':'CCT-PRUEBA','Turno':'Matutino'} for n,c in mv.ESCUELAS_USAER.items()])
def guardar_borrador(nombre,escuela,datos):st.session_state['qa_borrador']=deepcopy(datos)
def movimiento(aid,accion,motivo,**kw):
    cambios=mv.preparar(next(r for r in st.session_state.qa_padron if r['ID_Alumno']==aid),accion,**{k:v for k,v in kw.items() if k in ('escuela','docente','grado','grupo','regular')})
    for r in st.session_state.qa_padron:
        if r['ID_Alumno']==aid:r.update(cambios)
    return 'QA-MOVIMIENTO'
with patch.object(repo,'alumnos',return_value=frame),patch.object(repo,'escuelas',return_value=catalogo),\
    patch.object(repo,'ensure_expediente',return_value=False),patch.object(repo,'read',return_value=pd.DataFrame()),\
    patch.object(ex,'df_sheet',return_value=pd.DataFrame()),\
    patch.object(repo,'anexo3',return_value=pd.DataFrame()),patch.object(repo,'anexo4',return_value=pd.DataFrame()),patch.object(repo,'anexo5',return_value=pd.DataFrame()),\
    patch.object(mv,'visibles',return_value=frame),patch.object(mv,'ejecutar',side_effect=movimiento),\
    patch.object(ar,'visibles',return_value=frame),patch.object(ar,'_rows',return_value=[]),\
    patch.object(ar,'guardar',side_effect=RuntimeError('La demostración no guarda documentos reales')),\
    patch.object(planeacion,'versiones_actuales',return_value=[]),patch.object(epp,'listar',return_value=[]),\
    patch.object(h,'cargar_restricciones',return_value=pd.DataFrame()),patch.object(h,'cargar_horarios_apoyo',return_value=pd.DataFrame()),\
    patch.object(h,'_alumnos_de_maestra',return_value=(frame,frame)),patch.object(h,'_avisos_maestra',side_effect=lambda *_:st.info('Aquí aparecen los avisos de tu equipo.')),\
    patch.object(bh,'cargar_borrador',side_effect=lambda *_:deepcopy(st.session_state.get('qa_borrador',{}))),patch.object(bh,'guardar_borrador',side_effect=guardar_borrador):
    if vista=='Padrón':estadisticas.estadisticas_page(frame)
    elif vista=='Horarios':h.horarios_apoyo_page()
    else:
        from ui.pages import expedientes_page
        expedientes_page(frame)

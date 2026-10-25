"""Vista sintética de una EPP cargada: sin binarios ni base institucional."""
from unittest.mock import patch
import streamlit as st
from ui.documento_sintesis import archivado
from services import documentos_sintesis as ds

st.session_state.setdefault('qa_guardados',[])
texto=('ADMINISTRATIVO NO MOSTRAR COMPLETO.\n'*60)+'Necesita fortalecer la lectura funcional mediante apoyos visuales.\nRequiere practicar el conteo de objetos con material concreto.'
row={'ID_Documento':'QA-DOC','Nombre':'EPP-prueba.txt','Tipo':'EPP','Ambito':'individual','ID_Alumnos_JSON':'["QA-1"]'}
def guardadas():
    if not st.session_state.qa_guardados:return {}
    did,v=st.session_state.qa_guardados[-1]
    return {did:{**v,'Revision':'qa-revision','Fecha':'2026-10-23T12:00:00Z'}}
def guardar(did,v,**kw):
    value=ds.validar(v);st.session_state.qa_guardados.append((did,value));return 'qa-revision'
editor_nativo=st.data_editor
def editor(*args,**kwargs):
    result=editor_nativo(*args,**kwargs)
    if st.session_state.get('qa_validar_primera') and not result.empty:
        result=result.copy();result.loc[result.index[0],'estado']='Validada'
    return result
with patch.object(st,'data_editor',side_effect=editor),patch('services.materiales_planeacion.leer_material',return_value={'texto':texto,'avisos':[]}),patch.object(ds,'listar',side_effect=guardadas),patch.object(ds,'guardar',side_effect=guardar):
    archivado('QA-DOC',row,b'archivo-ficticio','qa')

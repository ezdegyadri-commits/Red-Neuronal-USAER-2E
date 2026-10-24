"""Vista sintética de una EPP cargada: sin binarios ni base institucional."""
from unittest.mock import patch
import streamlit as st
from ui.documento_sintesis import archivado
from services import documentos_sintesis as ds

st.session_state.setdefault('qa_guardados',[])
texto=('ADMINISTRATIVO NO MOSTRAR COMPLETO.\n'*60)+'Necesita fortalecer la lectura funcional mediante apoyos visuales.\nRequiere practicar el conteo de objetos con material concreto.'
row={'ID_Documento':'QA-DOC','Nombre':'EPP-prueba.txt','Tipo':'EPP','Ambito':'individual','ID_Alumnos_JSON':'["QA-1"]'}
with patch('services.materiales_planeacion.leer_material',return_value={'texto':texto,'avisos':[]}),patch.object(ds,'guardar',side_effect=lambda did,v:st.session_state.qa_guardados.append((did,v))):
    archivado('QA-DOC',row,b'archivo-ficticio','qa')

import pandas as pd
import streamlit as st
from contextlib import ExitStack
from unittest.mock import patch
from services import tramites as api
from ui.tramites import tramites_page

st.session_state.setdefault("nombre", "Marycruz Caamal Coral")
st.session_state.setdefault("rol", "Maestra de Apoyo")
st.session_state.setdefault("test_db", {api.HOJA: [], api.ARCHIVOS: []})
st.session_state.setdefault("test_oficios", [])

def guardar(datos):
    row = dict(datos, ID_Oficio="TEST-OF", Folio=24)
    st.session_state.test_oficios.append(row)
    return row

with ExitStack() as patches:
    patches.enter_context(patch.object(api, "_leer", side_effect=lambda h: [dict(r) for r in st.session_state.test_db[h]]))
    patches.enter_context(patch.object(api, "_anexar", side_effect=lambda h, cols, rows: st.session_state.test_db[h].extend([dict(r) for r in rows])))
    patches.enter_context(patch.object(api, "alumnos_visibles", side_effect=lambda *args: pd.DataFrame([{"ID_Alumno": "TEST-1", "Nombre_Completo": "Alumno de prueba", "Nombre_Escuela": "Ichcaanziho"}])))
    patches.enter_context(patch.object(api.repo, "oficios_comision", side_effect=lambda: pd.DataFrame(st.session_state.test_oficios)))
    patches.enter_context(patch.object(api.repo, "guardar_oficio_comision", side_effect=guardar))
    tramites_page()

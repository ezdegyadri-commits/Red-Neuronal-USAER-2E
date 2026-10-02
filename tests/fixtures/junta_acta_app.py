from unittest.mock import patch
import pandas as pd
import streamlit as st
from ui.pages import visitas_page
from data import repository as repo

st.session_state.setdefault("nombre", "Abril de María Chable Ríos")
st.session_state.setdefault("rol", "Psicología")
with patch.object(repo, "visitas", return_value=pd.DataFrame()):
    visitas_page(None)

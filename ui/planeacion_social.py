"""Acceso a las barreras documentadas dentro del mismo formato XXV."""
import streamlit as st


def panel(prefix,persist,abrir):
    from services.planeacion_social import proponer
    doc=st.session_state[prefix+'_doc']
    if doc['formato']!='XXV':return
    st.caption('Trabajo Social · Anexo XXV. Las BAP redactadas en los antecedentes y sus apoyos pueden incorporarse a la hoja. Revisa su pertinencia para los alumnos seleccionados; las actividades se organizan en Aula regular, Escuela, Familia y Comunidad.')
    if st.button('Incorporar barreras documentadas a mi formato',key=prefix+'_social_conectar'):
        try:
            nuevo=proponer(doc)
            if nuevo==doc:
                st.info('No hay barreras nuevas redactadas para incorporar. Puedes consultar los antecedentes y escribir la barrera en tu hoja; no se convierten las respuestas de BAPSE en una conclusión.')
            else:
                abrir(prefix,nuevo);persist(prefix);st.rerun()
        except (ValueError,PermissionError,RuntimeError) as exc:st.warning(str(exc))

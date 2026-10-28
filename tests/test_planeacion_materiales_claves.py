import unittest
from streamlit.testing.v1 import AppTest


class MaterialesClavesTests(unittest.TestCase):
    def test_dos_instancias_conservan_identidad_en_rerun(self):
        source='''
import streamlit as st
from ui.planeacion import _materiales
doc={'id':'documento-ficticio','datos':{'Alumnos':[]},'metadatos':{'materiales':[]}}
st.session_state.setdefault('borrador_doc',doc)
st.session_state.setdefault('borrador_material_readings',{'lectura-previa':{'texto':'Lectura ficticia'}})
_materiales('borrador',doc,instancia='herramientas')
_materiales('borrador',doc,instancia='conexiones')
_materiales('borrador',dict(doc,id='otro-documento'),instancia='herramientas')
'''
        app=AppTest.from_string(source).run(timeout=30)
        self.assertFalse(app.exception)
        keys=[x.key for x in app.get('file_uploader')]
        self.assertEqual(len(keys),3)
        self.assertEqual(len(set(keys)),3)
        app.run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(keys,[x.key for x in app.get('file_uploader')])
        self.assertEqual(app.session_state['borrador_material_readings']['lectura-previa']['texto'],'Lectura ficticia')


if __name__=='__main__':unittest.main()

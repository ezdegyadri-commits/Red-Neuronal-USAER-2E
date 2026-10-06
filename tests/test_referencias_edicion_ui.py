import unittest
from streamlit.testing.v1 import AppTest

class ReferenciasUITests(unittest.TestCase):
    def test_editor_disponible_sin_subir_imagen(self):
        code='''
import streamlit as st
import pandas as pd
import ui.horarios_apoyo as u
st.session_state.update(autenticado=True,nombre='Docente ficticia',rol='APOYO')
u.escuelas_asignadas=lambda *args:['Escuela ficticia']
u._avisos_maestra=lambda *args:None
u._cuadricula_horario=lambda *args:None
u.cargar_horarios_apoyo=lambda *args:pd.DataFrame()
u.cargar_restricciones=lambda *args:pd.DataFrame([{'Dia':'Viernes','Inicio':'08:00','Fin':'12:00','Grupo':'','Actividad':'Coros y Cantos','Responsable':'','Archivo':'Maya.jpeg','ID_Version':'v1'}])
def guardar(escuela,archivo,frame,version):
    st.session_state['correccion_prueba']={'escuela':escuela,'archivo':archivo,'version':version,'filas':frame.to_dict('records')}
u.editar_referencia=guardar
u.horarios_apoyo_page()
'''
        at=AppTest.from_string(code,default_timeout=30).run()
        self.assertFalse(at.exception)
        confirmar=next(c for c in at.checkbox if 'confirmo actualizar' in c.label)
        confirmar.check().run()
        next(b for b in at.button if b.label=='Guardar corrección de referencia').click().run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state['correccion_prueba']['archivo'],'Maya.jpeg')
        self.assertEqual(at.session_state['correccion_prueba']['version'],'v1')
        self.assertTrue(any('sin grupos confirmados' in w.value for w in at.warning))

if __name__=='__main__':unittest.main()

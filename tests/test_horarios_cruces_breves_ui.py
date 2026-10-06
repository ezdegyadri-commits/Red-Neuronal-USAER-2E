import unittest
from copy import deepcopy
from unittest.mock import patch
import pandas as pd
from streamlit.testing.v1 import AppTest
from services import borradores_horarios
from ui import horarios_apoyo as u

CODE='''
import pandas as pd
import streamlit as st
from ui.horarios_apoyo import _cuadricula_horario
st.session_state.update(nombre='Marycruz',rol='APOYO',autenticado=True)
referencias=pd.DataFrame([{'Dia':'Jueves','Inicio':'07:50','Fin':'08:40','Grupo':'1B','Actividad':'Educación física','Archivo':'EF','ID_Version':'v1'}])
_cuadricula_horario('Marycruz','Ichcaanziho',referencias,pd.DataFrame())
'''

class CrucesUITests(unittest.TestCase):
    def test_aceptar_acuerdo_habilita_guardado_y_se_recupera(self):
        fila={'Dia':'Jueves','Inicio':'07:00','Fin':'08:00','Grupo':'1B','ID_Alumnos':'A1','Maestra':'Marycruz','Actividad':'Apoyo'}
        saved={'bloques':{'Jueves|07:00|08:00':fila},'widgets':{},'editor_version':0}
        def guardar(_nombre,_escuela,datos):saved.clear();saved.update(deepcopy(datos))
        alumnos=pd.DataFrame([{'ID_Alumno':'A1','Nombre_Completo':'Alumno ficticio','Grado':'1','Grupo':'B'}])
        with patch.object(borradores_horarios,'cargar_borrador',side_effect=lambda *_:deepcopy(saved)),patch.object(borradores_horarios,'guardar_borrador',side_effect=guardar),patch.object(u,'_alumnos_de_maestra',return_value=(alumnos,alumnos)),patch.object(u,'generar_horario_apoyo_cuadricula_pdf',return_value=b'%PDF-muestra'):
            app=AppTest.from_string(CODE,default_timeout=30).run()
            self.assertFalse(app.exception)
            next(c for c in app.checkbox if '10 minutos' in c.label).check().run()
            next(t for t in app.text_input if t.label=='Acuerdo y regreso a clase').set_value('Coordinado con el docente, regresa a las 08:00.').run()
            next(b for b in app.button if b.label=='Confirmar los cruces seleccionados').click().run()
            self.assertFalse(app.exception)
            self.assertIn('Cruces_Aceptados_JSON',saved['bloques']['Jueves|07:00|08:00'])
            next(c for c in app.checkbox if c.label.startswith('Confirmo que revisé')).check().run()
            self.assertFalse(next(b for b in app.button if b.label=='Guardar esta versión en la base central').disabled)
            recovered=AppTest.from_string(CODE,default_timeout=30).run()
            self.assertFalse(recovered.exception)
            self.assertTrue(any('cruces aceptados' in i.value for i in recovered.info))
            self.assertTrue(any('Cruce breve aceptado' in m.value for m in recovered.markdown))

if __name__=='__main__':unittest.main()

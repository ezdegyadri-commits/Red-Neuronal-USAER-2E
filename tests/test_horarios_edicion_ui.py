import unittest
from pathlib import Path
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
import pandas as pd
from services import borradores_horarios
from ui import horarios_apoyo

class HorarioEdicionUITest(unittest.TestCase):
    def test_tiempo_editado_semana_persiste_y_se_recupera(self):
        saved={}
        def guardar(_nombre,_escuela,datos):
            from copy import deepcopy
            saved.clear();saved.update(deepcopy(datos))
        with patch.object(borradores_horarios,'cargar_borrador',side_effect=lambda *_:saved),patch.object(borradores_horarios,'guardar_borrador',side_effect=guardar),patch.object(horarios_apoyo,'_alumnos_de_maestra',return_value=(pd.DataFrame(),pd.DataFrame())):
            app=AppTest.from_file(str(Path(__file__).parent/'fixtures/horario_draft_app.py')).run(timeout=30)
            self.assertFalse(app.exception)
            next(t for t in app.text_area if t.label.startswith('Actividad')).set_value('Preparación de materiales').run()
            next(t for t in app.text_input if t.label=='Fin del bloque · HH:MM').set_value('07:45').run()
            next(t for t in app.checkbox if t.label.startswith('La misma actividad')).check().run()
            next(b for b in app.button if b.label=='Añadir o actualizar este bloque').click().run()
            self.assertFalse(app.exception)
            self.assertEqual(len(saved['bloques']),5)
            self.assertTrue(all(r['Fin']=='07:45' for r in saved['bloques'].values()))
            recovered=AppTest.from_file(str(Path(__file__).parent/'fixtures/horario_draft_app.py')).run(timeout=30)
            self.assertFalse(recovered.exception)
            self.assertTrue(any('07:45' in str(m.value) for m in recovered.markdown))
            self.assertTrue(any('Nuevo bloque con horario libre' in s.options for s in recovered.selectbox))

if __name__=='__main__':unittest.main()

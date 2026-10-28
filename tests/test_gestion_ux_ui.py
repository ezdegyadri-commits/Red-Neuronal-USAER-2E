from unittest import TestCase
from pathlib import Path
from streamlit.testing.v1 import AppTest

class GestionUITests(TestCase):
    def app(self):return AppTest.from_file(str(Path(__file__).parent/'fixtures/gestion_ux_app.py'),default_timeout=30).run()

    def test_padron_editor_baja_y_reactivacion(self):
        app=self.app();self.assertFalse(app.exception)
        # La tabla paginada fue sustituida por el editor directo antes de esta
        # intervención. Mantener el recorrido de baja/reactivación sobre esa UI.
        self.assertTrue(any(w.key and w.key.startswith('padron_directo_editor_') for w in app.dataframe))
        next(w for w in app.radio if w.label=='Acción').set_value('Baja recuperable').run()
        next(w for w in app.text_input if w.label=='Motivo del movimiento').set_value('Baja sintética de prueba').run()
        next(w for w in app.checkbox if w.label.startswith('Revisé el alumno')).check().run()
        next(b for b in app.button if b.label=='Confirmar baja recuperable').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.session_state.qa_padron),31)
        self.assertEqual(app.session_state.qa_padron[0]['Estatus'],'Baja')
        next(w for w in app.radio if w.label=='Acción').set_value('Reactivar').run()
        self.assertTrue(next(b for b in app.button if b.label=='Confirmar reactivar').disabled)
        next(w for w in app.checkbox if w.label.startswith('Revisé el alumno')).check().run()
        next(b for b in app.button if b.label=='Confirmar reactivar').click().run()
        self.assertFalse(app.exception);self.assertEqual(app.session_state.qa_padron[0]['Estatus'],'Activo')

    def test_horarios_abre_semana_sin_montar_uploader_de_referencias(self):
        app=self.app()
        next(w for w in app.radio if w.label=='Módulo').set_value('Horarios').run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.get('file_uploader')),0)
        self.assertTrue(any(w.label=='Día' for w in app.selectbox))
        next(w for w in app.radio if w.label=='¿Qué necesitas hacer?').set_value('Referencias de la escuela').run()
        self.assertFalse(app.exception);self.assertEqual(len(app.get('file_uploader')),1)

    def test_expediente_grupal_y_clasificacion_de_carga(self):
        app=self.app()
        next(w for w in app.radio if w.label=='Módulo').set_value('Expedientes').run()
        self.assertFalse(app.exception)
        next(w for w in app.radio if w.label=='Expedientes').set_value('Grupal').run()
        self.assertFalse(app.exception)
        self.assertTrue(any(w.label=='Tipo de documento' for w in app.selectbox))
        self.assertFalse(any(w.label=='Alumno' for w in app.selectbox))

"""Navegación y trabajo global sin conexiones externas."""
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch
import pandas as pd
from streamlit.testing.v1 import AppTest


class ModuloTests(TestCase):
    def test_ruta_reutiliza_matricula_autorizada_y_permite_volver(self):
        from ui import contenido_modulo as modulo
        import ui.estadisticas as estadistica
        frame=pd.DataFrame([{'ID_Alumno':'FICTICIO','Nombre_Completo':'Alumno de prueba'}])
        script='''
import streamlit as st
from ui.contenido_modulo import mostrar
st.session_state.setdefault('navegacion_principal','Estadística')
if st.session_state.navegacion_principal=='Inicio':
    st.write('Centro de prueba')
else:
    mostrar('Estadística','APOYO','E1',['Inicio','Estadística'])
'''
        with patch.object(modulo,'alumnos_visibles',return_value=frame) as visibles,patch.object(estadistica,'estadisticas_page',side_effect=lambda df:__import__('streamlit').write(str(len(df))+' alumnos ficticios')):
            app=AppTest.from_string(script).run()
            self.assertFalse(app.exception);visibles.assert_called_once_with('APOYO','E1','')
            next(b for b in app.button if b.label=='← Centro de Control').click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state.navegacion_principal,'Inicio')

    def test_treinta_clics_no_regeneran_cifrado_identico(self):
        from ui import sesiones_recuperables as ui
        state={'autenticado':True,'usuario':'cuenta-ficticia','evento_descripcion':'Apunte ficticio'}
        registro=object();render=Mock(return_value={'evento':None});servicio=Mock()
        servicio.proteger_borrador.return_value='cifrado-ficticio'
        with patch.object(ui.st,'session_state',state),patch.object(ui,'servicio',return_value=servicio),patch.object(ui,'_COMPONENTES',{registro:render}),patch.object(ui,'get_bidi_component_manager',return_value=registro):
            for _ in range(30):ui.recuperar()
            self.assertEqual(servicio.proteger_borrador.call_count,1)
            state['evento_descripcion']='Apunte actualizado';ui.recuperar()
            self.assertEqual(servicio.proteger_borrador.call_count,2)
            state['usuario']='otra-cuenta';ui.recuperar()
            self.assertEqual(servicio.proteger_borrador.call_count,3)

    def test_registro_componentes_se_reutiliza(self):
        from ui import interacciones_rapidas as ui
        registro=object();render=Mock()
        with patch.object(ui,'_componentes',{}),patch.object(ui,'get_bidi_component_manager',return_value=registro),patch.object(ui.components,'component',return_value=render) as crear:
            for _ in range(30):ui.activar()
            crear.assert_called_once();self.assertEqual(render.call_count,30)

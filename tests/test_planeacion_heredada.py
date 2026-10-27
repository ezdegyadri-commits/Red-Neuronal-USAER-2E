"""Recuperación de documentos anteriores; todos los datos son ficticios."""
from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch
import pandas as pd
from services import planeacion as s,planeacion_recuperacion as r
from tests.test_planeacion_panel import documento,ALUMNO,ACTOR,PanelTests


def ejemplo():
    d=documento();d['id']='anterior-ficticia';d['revision']='revision-antigua'
    d['metadatos'].pop('modalidad_planeacion',None)
    d['datos']['Alumnos'][0]['Grado']='5o.'
    d['tablas']['aprendizajes']=[{'Necesidades educativas específicas':'Necesidad ficticia '+str(i)} for i in range(3)]
    d['tablas']['dosificacion']=[{'Actividades':'','Contextos':'Aula regular'} for i in range(7)]
    d['tablas']['dosificacion'][4]['Actividades']='Inicio, desarrollo y cierre ficticios. '*100
    return d


class ClasificacionTests(TestCase):
    def test_repositorio_muestra_ambas_y_limpia_filtro_previo_al_reintegrar(self):
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_string('''
import streamlit as st
import pandas as pd
from copy import deepcopy
from services.planeacion_recuperacion import clasificar_heredada
from tests.test_planeacion_heredada import ejemplo,ALUMNO
from ui.planeacion_repositorio import panel
d=clasificar_heredada(ejemplo(),pd.DataFrame([{**ALUMNO,'Tipo_Atencion':'Individual'}]))
otro=deepcopy(d);otro['id']='actual-ficticia';otro['datos']['Alumnos'][0].update({'ID_Alumno':'A2','Nombre del alumno':'Otro alumno ficticio','Grado':'6°'})
st.session_state.setdefault('prueba_repositorio_Individuales_grado','6°')
panel('prueba',[d,otro],lambda base,doc:None)
''').run()
        self.assertFalse(app.exception)
        self.assertEqual(app.tabs[0].label,'Individuales (2)')
        self.assertEqual(app.session_state['prueba_repositorio_Individuales_grado'],'Todos')
        self.assertTrue(any(h.value=='Alumno ficticio' for h in app.subheader))
        self.assertTrue(any(h.value=='Otro alumno ficticio' for h in app.subheader))

    def test_reintegra_en_individuales_con_mismo_id_contenido_y_revision(self):
        d=ejemplo();antes=deepcopy(d);padron=pd.DataFrame([{**ALUMNO,'Tipo_Atencion':'Individual','Grado':'5°'}])
        recuperada=r.clasificar_heredada(d,padron)
        otra=deepcopy(recuperada);otra['id']='otra-ficticia'
        otra['datos']['Alumnos'][0].update(ID_Alumno='A2',**{'Nombre del alumno':'Otro alumno ficticio'})
        self.assertEqual(len(r.repositorios([recuperada,otra])['Individuales']),2)
        self.assertEqual(recuperada['id'],d['id']);self.assertEqual(recuperada['revision'],d['revision'])
        self.assertEqual(recuperada['tablas'],d['tablas']);self.assertEqual(r.actividades_redactadas(recuperada),1)
        self.assertEqual(d,antes);self.assertNotIn('modalidad_planeacion',d['metadatos'])
        self.assertIn('Alumno ficticio',r.titulo_tarjeta(recuperada))

    def test_no_infiere_por_nombre_grupo_ajeno_matricula_incompleta_o_ambigua(self):
        d=ejemplo()
        for cambios in ({'ID_Alumno':'A2'},{'ID_Escuela':'E2'},{'Tipo_Atencion':'Grupal'},{'Tipo_Atencion':''}):
            frame=pd.DataFrame([{**ALUMNO,'Tipo_Atencion':'Individual',**cambios}])
            self.assertEqual(r.clasificar_heredada(d,frame),d)
        row={**ALUMNO,'Tipo_Atencion':'Individual'}
        self.assertEqual(r.clasificar_heredada(d,pd.DataFrame([row,row])),d)

    def test_no_cambia_modalidad_declarada_ni_reclasifica_grupo(self):
        d=ejemplo();d['metadatos']['modalidad_planeacion']='grupal'
        self.assertIs(r.clasificar_heredada(d,pd.DataFrame([{**ALUMNO,'Tipo_Atencion':'Individual'}])),d)


class CatalogoTests(TestCase):
    setUp=PanelTests.setUp
    tearDown=PanelTests.tearDown

    def test_listar_dos_individuales_sin_escribir_y_conservar_historia_original(self):
        frame=pd.DataFrame([{**ALUMNO,'Tipo_Atencion':'Individual'},
                            {**ALUMNO,'ID_Alumno':'A2','Tipo_Atencion':'Individual'}])
        with patch.object(s,'padron_autorizado',return_value=frame):
            vieja=ejemplo();vieja['revision']='';s.guardar(vieja)
            nueva=documento();nueva['id']='actual-ficticia'
            nueva['datos']['Alumnos'][0].update(ID_Alumno='A2',**{'Nombre del alumno':'Segundo alumno ficticio'})
            nueva['metadatos']['modalidad_planeacion']='individual';s.guardar(nueva)
            antes=deepcopy(self.sheet.rows);visibles=s.listar();historico=s.listar(True)
        self.assertEqual(len(r.repositorios(visibles)['Individuales']),2)
        self.assertEqual(self.sheet.rows,antes)
        self.assertNotIn('modalidad_planeacion',next(d for d in historico if d['id']==vieja['id'])['metadatos'])

    def test_documento_no_autorizado_no_reaparece_por_clasificacion(self):
        frame=pd.DataFrame([{**ALUMNO,'Tipo_Atencion':'Individual'}])
        with patch.object(s,'padron_autorizado',return_value=frame):
            d=ejemplo();d['revision']='';s.guardar(d)
        with patch.object(s,'padron_autorizado',return_value=frame.iloc[0:0]),patch.object(s.repo,'alumnos',return_value=frame.iloc[0:0]):
            self.assertEqual(s.listar(),[])

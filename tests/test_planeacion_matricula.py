"""Matrícula y escuelas equivalentes, con alumnos completamente ficticios."""
from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import patch
import pandas as pd
from streamlit.testing.v1 import AppTest
from services import planeacion as s
from services.planeacion_matricula import preparar,clave_escuela
from services.planeacion_modalidad import filtrar
from services.planeacion_modelo import crear_plantilla
from tests import test_planeacion_simple as simple


def matricula():
    rows=[{'ID_Alumno':f'FICTICIO-{i}','Nombre_Completo':f'Estudiante ficticio {i}',
           'ID_Escuela':'MANUEL SARRADO' if i==8 else 'ESC-006',
           'Nombre_Escuela':'MANUEL SARRADO','Grado':'3','Grupo':'A',
           'Tipo_Atencion':'Individual' if i==7 else 'Grupal'} for i in range(13)]
    rows.append({**rows[0],'ID_Alumno':'OTRA-ESCUELA','ID_Escuela':'ESC-003',
                 'Nombre_Escuela':'Gregorio Torres Quintero'})
    return pd.DataFrame(rows)


class MatriculaTests(unittest.TestCase):
    def setUp(self):
        self.frame=matricula()
        self.actor={'cuenta':'cuenta-ficticia','nombre':'Mtra. María del Rosario Pérez Vitorin',
                    'rol':'Apoyo','area':'Aprendizaje','perfil':None,'director':False}

    def padron(self,permiso='ESC-006'):
        with patch.object(s,'identidad',return_value=self.actor),patch.object(s.st,'session_state',{'escuelas_permitidas':permiso}),patch.object(s.repo,'alumnos',return_value=self.frame):
            return s.padron_autorizado()

    def test_codigo_y_nombre_reunen_trece_sin_otras_escuelas(self):
        for permiso in ('ESC-006','Manuel Sarrado'):
            result=self.padron(permiso)
            self.assertEqual(len(result),13)
            self.assertEqual(result['ID_Escuela'].unique().tolist(),['ESC-006'])
            self.assertEqual(result['Nombre_Escuela'].unique().tolist(),['Manuel Sarrado'])
            self.assertEqual(len(filtrar(result,'individual')),1)
            self.assertEqual(len(filtrar(result,'grupal')),12)
        self.assertEqual(self.frame.loc[8,'ID_Escuela'],'MANUEL SARRADO')

    def test_sin_permiso_no_amplia_ambito(self):
        self.assertTrue(self.padron('').empty)
        self.assertEqual(len(self.padron('ESC-003')),1)

    def test_no_modifica_desconocidos_ni_padron_original(self):
        antes=self.frame.copy(deep=True);preparar(self.frame)
        pd.testing.assert_frame_equal(antes,self.frame)
        self.assertEqual(clave_escuela('E-FICTICIA'),'E-FICTICIA')

    def test_documento_historico_con_nombre_se_autoriza_sin_migrarlo(self):
        frame=self.padron()
        legacy=self.frame.iloc[[8]].to_dict('records')
        doc=crear_plantilla('XXIII',[legacy[0]['ID_Alumno']],legacy,autor=self.actor['nombre'],funcion='Aprendizaje')
        doc.update(cuenta=self.actor['cuenta']);antes=deepcopy(doc)
        with patch.object(s,'identidad',return_value=self.actor),patch.object(s,'padron_autorizado',return_value=frame):
            s.autorizar(doc,True)
            otro=deepcopy(doc);otro['datos']['ID_Escuela']='ESC-003'
            with self.assertRaises(PermissionError):s.autorizar(otro)
        self.assertEqual(doc,antes)

    def test_se_puede_crear_grupal_con_ambas_representaciones(self):
        frame=self.padron()
        with patch.object(s,'identidad',return_value=self.actor),patch.object(s,'padron_autorizado',return_value=frame),patch.object(s.repo,'escuelas',return_value=pd.DataFrame()):
            doc=s.nueva('XXIII',['FICTICIO-0','FICTICIO-8'],modalidad='grupal')
        self.assertEqual(doc['datos']['ID_Escuela'],'ESC-006')
        self.assertEqual(len(doc['datos']['Alumnos']),2)

    def test_actualizar_solo_invalida_lectura(self):
        with patch.object(s,'identidad'),patch('data.google.clear_cache') as clear:
            s.refrescar_matricula()
        clear.assert_called_once_with('Alumnos')


class MatriculaUITests(unittest.TestCase):
    setUp=simple.RecorridoTests.setUp
    tearDown=simple.RecorridoTests.tearDown

    def test_selector_unico_con_trece_y_sin_ajenos(self):
        app=AppTest.from_file(str(Path(__file__).with_name('fixture_planeacion_matricula.py')),default_timeout=30).run()
        self.assertFalse(app.exception)
        selector=next(m for m in app.multiselect if m.label=='Alumno o alumnos para planear')
        self.assertEqual(len(selector.options),13)
        self.assertFalse(any(m.label=='Escuela asignada' for m in app.selectbox))
        self.assertTrue(any('13 alumnos disponibles · 1 individuales · 12 grupales' in c.value for c in app.caption))
        selector.set_value(['FICTICIO-0','FICTICIO-8']).run()
        next(b for b in app.button if b.label=='Crear mi borrador').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.session_state.versiones_ficticias[-1]['datos']['Alumnos']),2)

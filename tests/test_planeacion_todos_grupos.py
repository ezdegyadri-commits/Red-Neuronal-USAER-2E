"""Todos los grupos y altas: pruebas exclusivamente con matrícula ficticia."""
from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch
from pathlib import Path
import pandas as pd
from services import planeacion as s, planeacion_grupo_unico as unico
from services.planeacion_ambito import ambito, etiqueta
from services.planeacion_compartida import ampliar_matricula, alumno_padron
from services.planeacion_modalidad import guia_grupal
from services.planeacion_colaboracion import compartible
from tests.test_planeacion_compartida import grupal
from tests.test_planeacion_panel import ALUMNO, ACTOR, PanelTests


def matricula():
    base={**ALUMNO,'Estatus':'Activo','Tipo_Atencion':'Grupal'}
    return pd.DataFrame([
        {**base,'ID_Alumno':'A1','Grado':'1o.','Grupo':'A'},
        {**base,'ID_Alumno':'B1','Grado':'1°','Grupo':'B'},
        {**base,'ID_Alumno':'S1','Grado':'1','Grupo':''},
        {**base,'ID_Alumno':'I1','Grado':'1°','Grupo':'B','Tipo_Atencion':'Individual'},
        {**base,'ID_Alumno':'OTRO-GRADO','Grado':'2°','Grupo':'A'},
        {**base,'ID_Alumno':'OTRA-ESCUELA','ID_Escuela':'E2','Grado':'1°','Grupo':'A'},
        {**base,'ID_Alumno':'BAJA','Grado':'1°','Grupo':'A','Estatus':'Baja'},
    ])


def documento(ids=('A1',),todos=False,incluir=False):
    d=grupal();frame=matricula()
    d['datos']['Alumnos']=[alumno_padron(r) for r in frame.to_dict('records') if r['ID_Alumno'] in ids]
    d['metadatos']['individuales_en_sesion_grupal']=incluir
    if todos:d['metadatos']['alcance_grupal']={'grado':'1°','grupo':'*'}
    return d


class AlcanceTests(TestCase):
    def test_todos_admite_a_b_y_sin_letra_sin_confundir_sus_identidades(self):
        d=documento(('A1','B1','S1'),todos=True);antes=deepcopy(d)
        self.assertEqual(ambito(d),('1°','*'))
        self.assertTrue(compartible(d));self.assertIn('Todos los grupos',etiqueta(d))
        self.assertEqual(unico.clave(d)[-2:],('1°','*'));self.assertEqual(d,antes)
        d['metadatos'].pop('alcance_grupal')
        self.assertIsNone(ambito(d));self.assertFalse(compartible(d))

    def test_sin_letra_no_es_todos_y_a_no_es_b(self):
        for ids,scope,expected in [(('A1',),('1°','A'),['A1']),
                                   (('B1',),('1°','B'),['B1']),
                                   (('S1',),('1°',''),['S1'])]:
            d=documento(ids)
            self.assertEqual(ambito(d),scope)
            nuevo=ampliar_matricula(d,matricula())
            self.assertEqual([a['ID_Alumno'] for a in nuevo['datos']['Alumnos']],expected)

    def test_individuales_excluidos_incluso_con_bandera_historica_y_sin_reescribir(self):
        for incluir,expected in [(False,['A1','B1','S1']),(True,['A1','B1','S1'])]:
            d=documento(todos=True,incluir=incluir)
            d['metadatos']['guia_grupal_manual']={'filas':[{'ID_Alumno':'A1','Aprendizaje':'Texto docente'}]}
            d['metadatos']['aportaciones_equipo']={'Comunicación':{'filas':[{'ID_Alumno':'A1','Texto en formato':'Texto especialista'}]}}
            antes=deepcopy(d);frame=matricula()
            nuevo=ampliar_matricula(d,frame)
            self.assertEqual([a['ID_Alumno'] for a in nuevo['datos']['Alumnos']],expected)
            self.assertEqual(guia_grupal(nuevo)['filas'][0]['Aprendizaje'],'Texto docente')
            self.assertEqual(guia_grupal(nuevo)['filas'][0]['Comunicación'],'Texto especialista')
            self.assertEqual(nuevo['metadatos']['aportaciones_equipo'],d['metadatos']['aportaciones_equipo'])
            self.assertEqual(ampliar_matricula(nuevo,frame),nuevo);self.assertEqual(d,antes)
        # También funciona con una sección concreta, no solo con Todos.
        d=documento(('B1',),incluir=True)
        self.assertEqual([a['ID_Alumno'] for a in ampliar_matricula(d,matricula())['datos']['Alumnos']],['B1'])

    def test_alcance_no_puede_ocultar_dos_grados(self):
        d=documento(('A1','OTRO-GRADO'),todos=True)
        self.assertIsNone(ambito(d));self.assertIsNone(unico.clave(d));self.assertFalse(compartible(d))


class PersistenciaTodosTests(PanelTests):
    def crear(self,ids,todos=True,incluir=False):
        with patch.object(s.repo,'escuelas',return_value=pd.DataFrame()):
            return s.nueva('XXIII',ids,modalidad='grupal',vista_formato='guia',
                           incluir_individuales=incluir,todos_grupos=todos)

    def test_todos_guarda_una_hoja_reabre_desde_b_y_preserva_historia(self):
        frame=matricula()
        with patch.object(s,'padron_autorizado',return_value=frame):
            a=documento();a['id']='origen-a'
            a['metadatos']['guia_grupal_manual']={'filas':[{'ID_Alumno':'A1','Aprendizaje':'Actividad A'}]}
            a=s.guardar(a)
            b=documento(('B1',));b['id']='origen-b'
            b['metadatos']['guia_grupal_manual']={'filas':[{'ID_Alumno':'B1','Aprendizaje':'Actividad B'}]}
            b=s.guardar(b)
            psic={**ACTOR,'area':'Psicología','cuenta':'psic'}
            with patch.object(s,'identidad',return_value=psic):
                s.guardar_aportacion(b,[{'ID_Alumno':'B1','Texto en formato':'Aporte B'}],'')
            unido=self.crear(['A1','B1'],incluir=True)
            self.assertEqual(unido['id'],a['id'])
            self.assertEqual(ambito(unido),('1°','*'))
            self.assertEqual(len(unido['datos']['Alumnos']),3)
            guardado=s.guardar(unido)
            self.assertEqual(len(s.compartidos()),1)
            self.assertEqual(self.crear(['B1'],todos=False)['id'],guardado['id'])
            filas={r['ID_Alumno']:r for r in guia_grupal(guardado)['filas']}
            self.assertEqual(filas['A1']['Aprendizaje'],'Actividad A')
            self.assertEqual(filas['B1']['Aprendizaje'],'Actividad B')
            self.assertEqual(filas['B1']['Psicología'],'Aporte B')
            self.assertEqual({d['id'] for d in s.reconstruir(self.sheet.rows)},{a['id'],b['id']})
            self.assertGreater(len(s.reconstruir(self.sheet.rows)),2)
            with self.assertRaisesRegex(RuntimeError,'único Anexo'):s.guardar(b)

    def test_especialistas_aportan_en_todos_sin_crear_otro_documento(self):
        frame=matricula()
        with patch.object(s,'padron_autorizado',return_value=frame):
            guardado=s.guardar(self.crear(['A1'],incluir=True))
            for area in ('Comunicación','Psicología','Trabajo Social'):
                actor={**ACTOR,'area':area,'cuenta':area}
                with patch.object(s,'identidad',return_value=actor):
                    s.guardar_aportacion(guardado,[{'ID_Alumno':'B1','Texto en formato':area}],'')
            actual=s.compartidos()[0]
            self.assertEqual(actual['id'],guardado['id'])
            fila=next(r for r in guia_grupal(actual)['filas'] if r['ID_Alumno']=='B1')
            for area in ('Comunicación','Psicología','Trabajo Social'):self.assertEqual(fila[area],area)

    def test_no_crea_todos_de_varios_grados_ni_alumnos_ajenos(self):
        with patch.object(s,'padron_autorizado',return_value=matricula()):
            with self.assertRaisesRegex(ValueError,'un grado'):self.crear(['A1','OTRO-GRADO'])
            with self.assertRaises(PermissionError):self.crear(['NO-AUTORIZADO'])

    def test_bandera_historica_no_permite_agregar_individuales_al_xix(self):
        with patch.object(s,'padron_autorizado',return_value=matricula()):
            previo=s.guardar(self.crear(['B1'],todos=False))
            with self.assertRaises(PermissionError):self.crear(['B1','I1'],todos=False,incluir=True)
            self.assertEqual(s.compartidos()[0]['id'],previo['id'])


class CacheMatriculaTests(TestCase):
    def test_sesion_relee_altas_sin_requerir_salir_y_respeta_asignacion(self):
        frame=matricula().iloc[:1]
        state={};now=[10.0]
        with patch.object(s,'identidad',return_value=ACTOR),patch.object(s.st,'session_state',state),\
             patch.object(s.time,'monotonic',side_effect=lambda:now[0]),\
             patch.object(s,'alumnos_visibles',return_value=frame) as leer:
            self.assertEqual(len(s.padron_autorizado()),1)
            leer.return_value=matricula().iloc[:2]
            self.assertEqual(len(s.padron_autorizado()),1)
            now[0]=71
            self.assertEqual(len(s.padron_autorizado()),2)
            self.assertEqual(leer.call_count,2)
            self.assertEqual(leer.call_args.args[2],ACTOR['nombre'])


class RecorridoTodosTests(TestCase):
    # Los fixtures sustituyen servicios durante AppTest; restaurar al terminar.
    from tests.test_planeacion_simple import RecorridoTests
    setUp=RecorridoTests.setUp
    tearDown=RecorridoTests.tearDown

    def test_primero_todos_abre_a_b_y_sin_letra_y_guarda_misma_hoja(self):
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_file(str(Path(__file__).with_name('fixture_planeacion_todos_grupos.py')),default_timeout=30).run()
        self.assertFalse(app.exception)
        next(w for w in app.selectbox if w.label=='Grado').set_value('1°').run()
        next(b for b in app.button if b.label=='Seleccionar todo este grupo').click().run()
        self.assertEqual(len(next(w for w in app.multiselect if w.label=='Alumnos de mi formato').value),3)
        next(b for b in app.button if b.label=='Abrir formato con mis alumnos').click().run()
        self.assertFalse(app.exception)
        docs=app.session_state.versiones_ficticias
        self.assertTrue(docs)
        self.assertEqual(ambito(docs[-1]),('1°','*'))
        self.assertEqual(len(docs[-1]['datos']['Alumnos']),3)
        self.assertFalse(any('Elige un grado y grupo concreto' in w.value for w in app.warning))
        did=docs[-1]['id']
        next(b for b in app.button if b.label=='Guardar borrador').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state.versiones_ficticias[-1]['id'],did)

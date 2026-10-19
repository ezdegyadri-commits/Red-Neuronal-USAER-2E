from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import unittest
import pandas as pd
from streamlit.testing.v1 import AppTest
from services import planeacion_viva as viva
from services.planeacion_modalidad import guia_grupal,GUIA_XIX
from tests.test_planeacion_local import documento
from tests import test_planeacion_simple as simple


class AdaptadorTests(unittest.TestCase):
    def setUp(self):
        self.autorizar=patch.object(viva.s,'autorizar',return_value={'area':'Aprendizaje'});self.autorizar.start()
    def tearDown(self):self.autorizar.stop()

    def test_edita_solo_fila_area_sin_perder_historia(self):
        d=documento();d['metadatos']['modalidad_planeacion']='grupal';antes=deepcopy(d)
        base=guia_grupal(d)['filas']
        nuevo=viva.editar_guia(d,{'edited_rows':{0:{'Aprendizaje':'Actividad docente'}}},base)
        self.assertEqual(guia_grupal(nuevo)['filas'][0]['Aprendizaje'],'Actividad docente')
        self.assertEqual(d,antes);self.assertEqual(nuevo['metadatos']['fuentes'],d['metadatos']['fuentes'])
        self.assertEqual(nuevo['id'],d['id'])
        for campo in ['Nombre alumno','Discapacidad o condición','Psicología']:
            with self.assertRaises(PermissionError):viva.editar_guia(d,{'edited_rows':{0:{campo:'Cambiar'}}},base)

    def test_rechaza_seleccion_ajena_o_modificada_y_guia_compartida(self):
        d=documento();d['metadatos']['modalidad_planeacion']='grupal';base=guia_grupal(d)['filas']
        base[0]['ID_Alumno']='AJENO'
        with self.assertRaises(ValueError):viva.editar_guia(d,{},base)
        d['metadatos']['guia_compartida']='otra'
        self.assertEqual(viva.campos_guia(d),[])
        with self.assertRaises(PermissionError):viva.editar_guia(d,{'edited_rows':{0:{'Aprendizaje':'X'}}},guia_grupal(d)['filas'])

    def test_ficha_solo_antecedentes_propios(self):
        d=documento();d['metadatos']['fuentes'] += [
            {'tipo':'ACTA','alumno':'OTRO','referencia':'AJENA','texto':'No mostrar','vinculo_verificado':True},
            {'tipo':'ACTA','alumno':'A1','referencia':'SIN-VERIFICAR','texto':'No mostrar','vinculo_verificado':False},
            {'tipo':'MATERIAL','alumno':'','referencia':'GENERAL','texto':'Lectura general'}]
        f=viva.ficha(d,'A1')
        self.assertNotIn('AJENA',[r['referencia'] for r in f['antecedentes']])
        self.assertNotIn('SIN-VERIFICAR',[r['referencia'] for r in f['antecedentes']])
        self.assertEqual([r['referencia'] for r in f['materiales_generales']],['GENERAL'])
        with self.assertRaises(PermissionError):viva.ficha(d,'OTRO')

    def test_actividades_locales_se_muestran_por_id_sin_resultados_ni_sobrescritura(self):
        d=documento();d['metadatos']['modalidad_planeacion']='grupal'
        d['tablas']['dosificacion'] += [{'Actividades':'PROPUESTA REVISADA','_actividad_local':'L1','_alumnos_locales':['A1']}, {'Actividades':'OTRA PERSONA','_actividad_local':'L2','_alumnos_locales':['OTRO']}]
        rows=guia_grupal(d)['filas'];self.assertEqual(rows[0]['Aprendizaje'],'PROPUESTA REVISADA')
        self.assertFalse(rows[0]['Situación final']);self.assertFalse(rows[0]['Psicología'])
        d['metadatos']['guia_grupal_manual']={'filas':[{**rows[0],'Aprendizaje':'Mi edición'}]}
        self.assertEqual(guia_grupal(d)['filas'][0]['Aprendizaje'],'Mi edición')

    def test_filtros_respetan_escuela_modalidad_y_no_mutan_padron(self):
        df=pd.DataFrame([{'ID_Alumno':'A','ID_Escuela':'E1','Grado':'4','Grupo':'B','Tipo_Atencion':'Grupal'}, {'ID_Alumno':'I','ID_Escuela':'E1','Grado':'4','Grupo':'B','Tipo_Atencion':'Individual'}, {'ID_Alumno':'X','ID_Escuela':'E2','Grado':'4','Grupo':'B','Tipo_Atencion':'Grupal'}]);antes=df.copy(deep=True)
        self.assertEqual(list(viva.opciones_padron(df,'E1','grupal','4','B')['ID_Alumno']),['A'])
        self.assertEqual(list(viva.opciones_padron(df,'E1','individual')['ID_Alumno']),['I'])
        pd.testing.assert_frame_equal(df,antes)


class HojaTests(unittest.TestCase):
    setUp=simple.RecorridoTests.setUp
    tearDown=simple.RecorridoTests.tearDown

    def abrir(self,area='Aprendizaje',tipo='Grupal',pi=False):
        app=AppTest.from_file(str(Path(__file__).with_name('fixture_planeacion_viva.py')),default_timeout=30).run()
        app.radio[0].set_value(area).run()
        if area!='Aprendizaje':
            next(w for w in app.radio if w.label=='¿Qué vas a continuar?').set_value('Mi formato de especialista').run()
        if tipo=='Individual':
            next(w for w in app.button_group if w.label=='Modalidad de planeación').set_value('Individual').run()
            next(w for w in app.multiselect if w.label=='Alumnos de mi formato').set_value(['I1']).run()
            if pi:next(w for w in app.selectbox if w.label=='Formato').set_value('Plan de intervención anual').run()
        else:
            next(w for w in app.selectbox if w.label=='Grado').set_value('5').run()
            next(w for w in app.selectbox if w.label=='Grupo').set_value('A').run()
            next(w for w in app.multiselect if w.label=='Alumnos de mi formato').set_value(['A1']).run()
        next(b for b in app.button if b.label=='Abrir formato con mis alumnos').click().run()
        self.assertFalse(app.exception)
        return app

    def test_hoja_directa_cuatro_perfiles_sin_ia_y_guardado(self):
        for area in ['Aprendizaje','Psicología','Comunicación','Trabajo Social']:
            with self.subTest(area=area):
                app=self.abrir(area)
                self.assertFalse(any(w.label=='Mi recorrido' for w in app.button_group))
                self.assertEqual(app.session_state.llamadas_ficticias,0)
                self.assertTrue(any(b.label=='Guardar borrador' for b in app.button))
                self.assertFalse(app.get('file_uploader'))
                self.assertFalse(any(c.label.startswith('Revisé el resumen') for c in app.checkbox))
                doc=deepcopy(app.session_state.versiones_ficticias[-1]);did=doc['id']
                campo='Observaciones' if area!='Trabajo Social' else 'Resultados obtenidos en los diferentes contextos'
                next(t for t in app.text_area if t.label==campo).set_value('Texto docente conservado').run()
                next(b for b in app.button if b.label=='Guardar borrador').click().run()
                self.assertEqual(app.session_state.versiones_ficticias[-1]['id'],did)
                self.assertEqual(app.session_state.versiones_ficticias[-1]['textos'][campo],'Texto docente conservado')
                self.assertEqual(app.session_state.llamadas_ficticias,0)

    def test_grupal_misma_matriz_y_edicion_texto_largo(self):
        app=self.abrir();matrices=[d for d in app.dataframe if list(d.value.columns)==GUIA_XIX]
        self.assertEqual(len(matrices),1)
        # El editor de texto largo y la matriz representan la misma celda.
        next(t for t in app.text_area if t.label=='Aprendizaje').set_value('Lectura con imágenes · dos veces por semana').run()
        next(b for b in app.button if b.label=='Guardar borrador').click().run()
        doc=app.session_state.versiones_ficticias[-1]
        self.assertIn('Lectura con imágenes',guia_grupal(doc)['filas'][0]['Aprendizaje'])
        next(b for b in app.button if b.label=='Elegir otro formato o alumnos').click().run()
        next(b for b in app.button if b.label=='Abrir mi formato').click().run()
        self.assertIn('Lectura con imágenes',next(t for t in app.text_area if t.label=='Aprendizaje').value)

    def test_individual_y_pi_conservan_tablas_y_modalidad(self):
        for pi in [False,True]:
            app=self.abrir(tipo='Individual',pi=pi);d=app.session_state.versiones_ficticias[-1]
            self.assertEqual(d['formato'],'XXI' if pi else 'XXIII')
            self.assertEqual(d['metadatos']['modalidad_planeacion'],'individual')
            self.assertEqual([a['ID_Alumno'] for a in d['datos']['Alumnos']],['I1'])
            self.assertFalse(any(list(df.value.columns)==GUIA_XIX for df in app.dataframe))

    def test_preparacion_local_y_vista_anterior_mismo_documento(self):
        app=self.abrir()
        next(b for b in app.button if b.label=='Preparar actividades con mis datos · sin IA').click().run()
        next(c for c in app.checkbox if c.label.startswith('Revisé estas propuestas')).check().run()
        next(b for b in app.button if b.label=='Incorporar actividades locales a mi formato').click().run()
        d=app.session_state.versiones_ficticias[-1];did=d['id']
        self.assertTrue(guia_grupal(d)['filas'][0]['Aprendizaje'])
        next(b for b in app.button if b.label=='Usar el recorrido anterior').click().run()
        self.assertFalse(app.exception);self.assertTrue(any(w.label=='Mi recorrido' for w in app.button_group))
        next(b for b in app.button if b.label=='Volver al formato vivo').click().run()
        self.assertFalse(app.exception);self.assertEqual(app.session_state.versiones_ficticias[-1]['id'],did)
        self.assertEqual(app.session_state.llamadas_ficticias,0)

    def test_director_conserva_revision_y_colaboracion(self):
        app=self.abrir('Aprendizaje')
        app.radio[0].set_value('Dirección').run()
        ruta=next(w for w in app.radio if w.label=='¿Qué vas a continuar?')
        self.assertEqual(ruta.options,['Mi formato','Planeaciones del equipo','Revisión directiva'])
        ruta.set_value('Revisión directiva').run()
        self.assertTrue(any(b.label=='Validar revisión' for b in app.button))

    def test_fallo_guardado_no_oculta_hoja_ni_pierde_texto(self):
        app=self.abrir();app.session_state.fallo_guardado_ficticio=True
        next(t for t in app.text_area if t.label=='Aprendizaje').set_value('Trabajo que debe sobrevivir al fallo').run()
        next(b for b in app.button if b.label=='Guardar borrador').click().run()
        self.assertFalse(app.exception)
        self.assertIn('Trabajo que debe sobrevivir',next(t for t in app.text_area if t.label=='Aprendizaje').value)
        self.assertTrue(any(w.label=='Descargar respaldo editable' for w in app.get('download_button')))
        app.session_state.fallo_guardado_ficticio=False
        next(b for b in app.button if b.label=='Guardar borrador').click().run()
        self.assertIn('Trabajo que debe sobrevivir',guia_grupal(app.session_state.versiones_ficticias[-1])['filas'][0]['Aprendizaje'])

    def test_fallo_ia_permite_continuar_en_matriz_y_preparar_local(self):
        app=self.abrir();app.session_state.fallo_ia_ficticio=True
        next(t for t in app.toggle if t.label=='Solicitar propuesta con IA').set_value(True).run()
        next(c for c in app.checkbox if c.label.startswith('Revisé el resumen')).check().run()
        next(b for b in app.button if b.label=='Generar e integrar actividades al formato').click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any('IA no disponible' in str(i.value) for i in app.warning))
        next(t for t in app.text_area if t.label=='Aprendizaje').set_value('Actividad manual de continuidad').run()
        next(b for b in app.button if b.label=='Preparar actividades con mis datos · sin IA').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state.llamadas_ficticias,1)
        self.assertIn('Actividad manual',next(t for t in app.text_area if t.label=='Aprendizaje').value)

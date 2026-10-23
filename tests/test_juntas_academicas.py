from copy import deepcopy
from datetime import date
from io import BytesIO
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch
import pandas as pd
from pypdf import PdfReader
from streamlit.testing.v1 import AppTest
from services import metas_instrumento as r,metas_personales as metas,juntas_academicas as juntas
from services.juntas_metodologias_catalogo import CATALOGO
from tests.test_metas_personales import GuardadoTests,ACTOR,PADRON


class RubricaTests(TestCase):
    def test_pendiente_no_es_cero_ni_coherencia_parte_del_total(self):
        value=r.vacia();value['Indicadores']['1']=0;value['Coherencia']=3
        result=r.resumen(value)
        self.assertEqual(result['Respondidos'],1);self.assertEqual(result['Pendientes'],13)
        self.assertIsNone(result['Total']);self.assertEqual(result['Subtotal'],0)
        value['Indicadores']={str(i):3 for i in range(1,15)}
        self.assertEqual(r.resumen(value)['Total'],42)

    def test_escala_estricta_y_edicion_sin_cambiar_indicadores(self):
        for score in (True,4,'3',-1):
            value=r.vacia();value['Indicadores']['1']=score
            with self.assertRaises(ValueError):r.validar(value)
        value=r.editar(r.vacia(),{'edited_rows':{0:{'Valoración':'2 · Suficiente'}}})
        self.assertEqual(value['Indicadores']['1'],2)
        self.assertIsNone(value['Indicadores']['2'])
        with self.assertRaises(ValueError):r.editar(value,{'edited_rows':{0:{'Indicador':'Otro'}}})

    def test_pdf_integrado_conserva_autores_y_metas_anteriores(self):
        from documents.metas_personales import generar_consolidado
        docs=[{'Docente':'Autor ficticio Uno','Escuela':'Escuela ficticia','Fecha_Sesion':'2026-10-23','Periodo':'Trimestre 1',
               'Filas':[{'Alumno':'Alumno ficticio','Metas':'Meta antigua','Recursos necesarios':'Recurso antiguo'}]},
              {'Docente':'Autor ficticio Dos','Escuela':'Escuela ficticia','Fecha_Sesion':'2026-10-23','Area':'Psicología',
               'Filas':[{'Alumno':'Alumno ficticio','Metas':'Meta nueva','Recursos necesarios':'Tarjetas','Instrumento':r.vacia()}]}]
        data=generar_consolidado(docs)
        text='\n'.join(p.extract_text() for p in PdfReader(BytesIO(data)).pages)
        for expected in ('Autor ficticio Uno','Autor ficticio Dos','Meta antigua','Meta nueva','Subtotal provisional','Pendiente'):
            self.assertIn(expected,text)


class ConsolidacionTests(GuardadoTests):
    def test_rubrica_se_conserva_al_editar_metas_desde_contrato_anterior(self):
        rows=self.filas();rows[0]['Instrumento']=r.vacia();rows[0]['Instrumento']['Indicadores']['1']=2
        doc=metas.guardar('ESC-001','2026-10-23',rows,periodo='Trimestre 1')
        new=metas.guardar('ESC-001','2026-10-23',self.filas('Meta corregida'),doc['Revision'])
        self.assertEqual(new['Filas'][0]['Instrumento'],rows[0]['Instrumento'])
        self.assertEqual(new['Periodo'],'Trimestre 1')

    def test_director_ve_ultima_version_por_autor_sin_mezclar(self):
        first=metas.guardar('ESC-001','2026-10-23',self.filas())
        metas.guardar('ESC-001','2026-10-23',self.filas('Corrección'),first['Revision'])
        with patch.object(metas.planes,'identidad',return_value={**ACTOR,'cuenta':'especialista-ficticio','area':'Psicología'}):
            metas.guardar('ESC-001','2026-10-23',self.filas('Aporte psicología'))
            self.assertEqual(len(metas.propias()),1)
            with self.assertRaises(PermissionError):metas.consolidar()
        with patch.object(metas.planes,'identidad',return_value={**ACTOR,'director':True}):
            docs=metas.consolidar('2026-10-23')
            self.assertEqual(len(docs),2)
            self.assertEqual({d['Filas'][0]['Metas'] for d in docs},{'Corrección','Aporte psicología'})
            with self.assertRaises(PermissionError):metas.guardar('ESC-001','2026-10-23',self.filas())
        self.assertEqual(len(self.rows),3)

    def test_integridad_escuelas_no_autorizadas_y_sin_escrituras(self):
        metas.guardar('ESC-001','2026-10-23',self.filas())
        with patch.object(metas.planes,'identidad',return_value={**ACTOR,'director':True}):
            with patch.object(metas.planes,'padron_autorizado',return_value=pd.DataFrame([{**PADRON[0],'ID_Escuela':'OTRA'}])):
                self.assertEqual(metas.consolidar(),[])
            self.rows[0]['Contenido']+='alterado'
            with self.assertRaises(RuntimeError):metas.consolidar()


class MetodologiasTests(TestCase):
    def setUp(self):
        self.rows=[];outer=self
        class Sheet:
            def row_values(self,n):return juntas.HEADERS
            def append_rows(self,rows,value_input_option):
                assert value_input_option=='RAW';outer.rows.extend(dict(zip(juntas.HEADERS,row)) for row in rows)
        for p in (patch.object(juntas,'identidad',return_value=ACTOR),patch.object(juntas.repo,'read',side_effect=lambda name:pd.DataFrame(deepcopy(self.rows))),patch.object(juntas,'ensure_headers',return_value=Sheet()),patch.object(juntas,'clear_cache')):
            p.start();self.addCleanup(p.stop)

    def test_catalogo_siglas_y_registro_idempotente_con_historial(self):
        self.assertEqual(len(CATALOGO),25);self.assertEqual(len({x[0] for x in CATALOGO}),25)
        value=juntas.vacia();value['Respuestas']['LC1']={**juntas.registro_vacio(),'A':True,'Aplicación prevista':'=Texto literal'}
        doc=juntas.guardar('2026-10-23',value)
        self.assertEqual(juntas.guardar('2026-10-23',value),doc);self.assertEqual(len(self.rows),1)
        value['Respuestas']['LC1']['C']=True
        juntas.guardar('2026-10-23',value,doc['Revision']);self.assertEqual(len(self.rows),2)
        with self.assertRaises(RuntimeError):juntas.guardar('2026-10-23',juntas.vacia())
        with patch.object(juntas,'identidad',return_value={**ACTOR,'cuenta':'otra'}):self.assertEqual(juntas.listar(),[])

    def test_solo_direccion_integra_y_no_falla_silenciosamente(self):
        juntas.guardar('2026-10-23',juntas.vacia())
        with self.assertRaises(PermissionError):juntas.listar(equipo=True)
        with patch.object(juntas,'identidad',return_value={**ACTOR,'director':True}):self.assertEqual(len(juntas.listar(equipo=True)),1)
        self.rows[0]['Contenido']+='alterado'
        with self.assertRaises(RuntimeError):juntas.listar()

    def test_pdf_mantiene_columnas_literales(self):
        from documents.juntas_academicas import generar_pdf
        value=juntas.vacia();value['Respuestas']['LE6']={**juntas.registro_vacio(),'P':True,'Aplicación prevista':'Aplicación ficticia'}
        data=generar_pdf([{'Docente':'Docente ficticia','Area':'Comunicación','Captura':value}],'2026-10-23')
        text='\n'.join(p.extract_text() for p in PdfReader(BytesIO(data)).pages)
        for expected in ('A, C y P','Aplicación ficticia','POW','TREE'):self.assertIn(expected,text)


class UITests(TestCase):
    def abrir(self,**state):
        app=AppTest.from_file(str(Path(__file__).parent/'fixtures'/'juntas_academicas_app.py'),default_timeout=30)
        for key,value in state.items():app.session_state[key]=value
        return app.run()

    def test_apoyo_desplegable_todos_sus_alumnos_sin_escribir_al_abrir(self):
        app=self.abrir();self.assertFalse(app.exception)
        alumno=next(x for x in app.selectbox if x.label=='Alumno de mi asignación')
        self.assertEqual(len(alumno.options),2);self.assertFalse(any(x.label=='Escuela asignada' for x in app.selectbox))
        self.assertEqual(app.session_state.qa_envios,0)
        alumno.select('A1').run();self.assertFalse(app.exception)
        self.assertEqual(app.session_state.qa_envios,0)

    def test_cambiar_alumno_conserva_metas_y_rubrica(self):
        app=self.abrir();next(x for x in app.selectbox if x.label=='Alumno de mi asignación').select('A1').run()
        next(x for x in app.text_area if x.label=='Metas para este alumno').set_value('Avance ficticio').run()
        next(x for x in app.selectbox if x.label=='Indicador 1').select(3).run()
        next(x for x in app.selectbox if x.label=='Valoración de coherencia').select(2).run()
        next(x for x in app.selectbox if x.label=='Alumno de mi asignación').select('A2').run()
        next(x for x in app.text_area if x.label=='Metas para este alumno').set_value('Segundo avance').run()
        next(x for x in app.selectbox if x.label=='Alumno de mi asignación').select('A1').run()
        self.assertFalse(app.exception)
        self.assertEqual(next(x for x in app.text_area if x.label=='Metas para este alumno').value,'Avance ficticio')
        self.assertEqual(next(x for x in app.selectbox if x.label=='Indicador 1').value,3)
        next(x for x in app.button if x.label=='Guardar instrumento').click().run()
        self.assertFalse(app.exception);self.assertGreater(app.session_state.qa_envios,0)
        import json
        doc=json.loads(app.session_state.qa_rows[metas.HOJA][-1]['Contenido'])
        self.assertEqual(len(doc['Filas']),2);self.assertEqual(doc['Filas'][0]['Instrumento']['Coherencia'],2)

    def test_fallo_no_descarta_la_captura_y_permite_cambiar_alumno(self):
        app=self.abrir(qa_fallo=True)
        next(x for x in app.selectbox if x.label=='Alumno de mi asignación').select('A1').run()
        next(x for x in app.text_area if x.label=='Metas para este alumno').set_value('Avance sin conexión').run()
        next(x for x in app.button if x.label=='Guardar instrumento').click().run()
        self.assertTrue(app.warning);self.assertEqual(app.session_state.qa_envios,0)
        next(x for x in app.selectbox if x.label=='Alumno de mi asignación').select('A2').run()
        self.assertFalse(app.exception)
        next(x for x in app.selectbox if x.label=='Alumno de mi asignación').select('A1').run()
        self.assertEqual(next(x for x in app.text_area if x.label=='Metas para este alumno').value,'Avance sin conexión')

    def test_especialistas_solo_alumnos_de_escuela_elegida(self):
        for area in ('Psicología','Comunicación','Trabajo Social'):
            app=self.abrir(qa_actor={'area':area,'rol':area})
            self.assertEqual(len(next(x for x in app.selectbox if x.label=='Alumno de mi asignación').options),2)
            next(x for x in app.selectbox if x.label=='Escuela asignada').select('ESC-002').run()
            self.assertFalse(app.exception)
            self.assertEqual(len(next(x for x in app.selectbox if x.label=='Alumno de mi asignación').options),1)

    def test_junta_fecha_inicial_y_cuadro_vivo_acp(self):
        app=self.abrir(qa_page='juntas');self.assertFalse(app.exception)
        self.assertEqual(next(x for x in app.selectbox if x.label=='Fecha de la junta').value,'2026-10-23')
        app.segmented_control[0].set_value('Cuadro de metodologías').run()
        self.assertFalse(app.exception)
        next(x for x in app.checkbox if x.label=='A').check().run()
        next(x for x in app.text_area if x.label=='Aplicación prevista').set_value('Aplicación de prueba').run()
        next(x for x in app.button if x.label=='Guardar mi cuadro').click().run()
        self.assertFalse(app.exception);self.assertEqual(app.session_state.qa_envios,1)

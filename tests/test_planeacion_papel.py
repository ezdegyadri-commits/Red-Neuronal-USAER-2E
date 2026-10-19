from copy import deepcopy
from unittest.mock import patch
import unittest
from services import planeacion_papel as papel
from services.planeacion_modalidad import guia_grupal
from tests.test_planeacion_local import documento
from tests import test_planeacion_simple as simple


class PapelTests(unittest.TestCase):
    def setUp(self):self.auth=patch.object(papel.s,'autorizar',return_value={});self.auth.start()
    def tearDown(self):self.auth.stop()
    def evento(self,d,**kwargs):return {'documento':d['id'],'huella':papel.huella(d),'nonce':'n','accion':'guardar','cambios':{},**kwargs}
    def celda(self,spec,target):return next(k for k,c in spec['cells'].items() if c['target']==target)

    def test_formato_ejemplo_conserva_tablas_y_pda_separado(self):
        d=documento();d['metadatos']['modalidad_planeacion']='individual';spec=papel.hoja(d)
        self.assertFalse(spec['grupal']);self.assertEqual([t['id'] for t in spec['tables']],['aprendizajes','dosificacion'])
        self.assertTrue(spec['tables'][0]['headers'][1].startswith('PDA: nacionales'))
        self.assertEqual(spec['tables'][1]['headers'],['Contextos','Actividades','Temporalidad','Recursos'])

    def test_edicion_y_borrado_texto_preservan_referencias_e_identidad(self):
        d=documento();d['tablas']['dosificacion'][0]['_fila_manual']=True;spec=papel.hoja(d);key=self.celda(spec,('tabla','dosificacion',0,'Actividades'))
        antes=deepcopy(d);edited=papel.aplicar(d,self.evento(d,cambios={key:'Actividad redactada'}))
        self.assertEqual(edited['tablas']['dosificacion'][0]['Actividades'],'Actividad redactada')
        blank=papel.aplicar(edited,self.evento(edited,cambios={key:''}))
        self.assertEqual(blank['tablas']['dosificacion'][0]['Actividades'],'')
        self.assertEqual(blank['metadatos'],d['metadatos']);self.assertEqual(d,antes)

    def test_fila_vacia_se_llena_sin_requerir_configuracion(self):
        d=documento();d['tablas']['aprendizajes']=[]
        d=papel.aplicar(d,self.evento(d,accion='agregar',tabla='aprendizajes'))
        spec=papel.hoja(d);key=self.celda(spec,('tabla','aprendizajes',0,'Descriptor de logro'))
        new=papel.aplicar(d,self.evento(d,cambios={key:'El alumno identifica una palabra.'}))
        self.assertEqual(new['tablas']['aprendizajes'][0]['Descriptor de logro'],'El alumno identifica una palabra.')

    def test_agregar_retirar_confirmado_sin_eliminar_version_previa(self):
        d=documento();antes=deepcopy(d);new=papel.aplicar(d,self.evento(d,accion='agregar',tabla='dosificacion'))
        self.assertEqual(len(new['tablas']['dosificacion']),len(d['tablas']['dosificacion'])+1)
        with self.assertRaises(ValueError):papel.aplicar(new,self.evento(new,accion='retirar',tabla='dosificacion',fila=0))
        removed=papel.aplicar(new,self.evento(new,accion='retirar',tabla='dosificacion',fila=0,confirmado=True))
        self.assertEqual(len(removed['tablas']['dosificacion']),len(d['tablas']['dosificacion']))
        self.assertEqual(d,antes)

    def test_guia_grupal_protege_otros_aportes_y_alumnos(self):
        d=documento();d['metadatos']['modalidad_planeacion']='grupal';spec=papel.hoja(d)
        key=self.celda(spec,('guia',0,'Aprendizaje'))
        edited=papel.aplicar(d,self.evento(d,cambios={key:'Actividad propia'}))
        self.assertEqual(guia_grupal(edited)['filas'][0]['Aprendizaje'],'Actividad propia')
        protected=next(k for k,c in spec['cells'].items() if c['label']=='Psicología')
        with self.assertRaises(PermissionError):papel.aplicar(d,self.evento(d,cambios={protected:'Otra área'}))
        with self.assertRaises(ValueError):papel.aplicar(d,self.evento(d,accion='retirar',tabla='guia',fila=0,confirmado=True))

    def test_se_puede_elegir_trimestral_para_subgrupo(self):
        d=documento();d['metadatos'].update(modalidad_planeacion='grupal',vista_formato='trimestral')
        self.assertFalse(papel.hoja(d)['grupal']);self.assertEqual(papel.hoja(d)['tables'][0]['id'],'aprendizajes')

    def test_no_edita_sesiones_ni_aportes_por_copia(self):
        d=documento();d['tablas']['dosificacion'][0].update(_sesion_equipo='S1',Actividades='Actividad vinculada')
        spec=papel.hoja(d)
        self.assertTrue(all(not c['editable'] for c in spec['tables'][1]['rows'][0]))
        with self.assertRaises(ValueError):papel.aplicar(d,self.evento(d,accion='retirar',tabla='dosificacion',fila=0,confirmado=True))

    def test_rechaza_payload_obsoleto_ajeno_y_campos_inventados(self):
        d=documento()
        for overrides in [{'huella':'vieja'},{'documento':'ajeno'},{'accion':'eliminar_padron'}]:
            with self.assertRaises(ValueError):papel.aplicar(d,self.evento(d,**overrides))
        with self.assertRaises(PermissionError):papel.aplicar(d,self.evento(d,cambios={'inventado':'X'}))

    def test_pdf_usa_la_misma_redaccion_de_la_hoja(self):
        from documents.planeacion_papel import generar_pdf
        from pypdf import PdfReader
        from io import BytesIO
        d=documento();d['tablas']['dosificacion'][0]['Actividades']='ACTIVIDAD EDITADA Y VERIFICADA'
        pdf=generar_pdf(d);texto='\n'.join(p.extract_text() for p in PdfReader(BytesIO(pdf)).pages)
        self.assertIn('ACTIVIDAD EDITADA Y VERIFICADA',texto)
        self.assertNotIn('PDA: nacionales',texto)  # Una tabla sin contenido no ocupa espacio en la descarga.

    def test_cache_pdf_no_repite_trabajo_ni_confunde_vistas(self):
        from ui import planeacion as u
        from unittest.mock import Mock
        d=documento();state={};provider=Mock(return_value=b'PDF-PAPEL')
        with patch.object(u.st,'session_state',state),patch.object(u,'generar_pdf',return_value=b'PDF-ANTERIOR') as old:
            self.assertEqual(u._pdf_sesion('p',d),b'PDF-ANTERIOR')
            self.assertEqual(u._pdf_sesion('p',d,provider),b'PDF-PAPEL')
            self.assertEqual(u._pdf_sesion('p',d,provider),b'PDF-PAPEL')
            self.assertEqual(provider.call_count,1);self.assertEqual(old.call_count,1)


class PapelUITests(unittest.TestCase):
    setUp=simple.RecorridoTests.setUp
    tearDown=simple.RecorridoTests.tearDown

    def test_individual_multiple_cuatro_perfiles_conserva_modalidad_y_pdf(self):
        from streamlit.testing.v1 import AppTest
        from pathlib import Path
        from documents.planeacion_papel import generar_pdf
        from pypdf import PdfReader
        from io import BytesIO
        for area in ['Aprendizaje','Psicología','Comunicación','Trabajo Social']:
            with self.subTest(area=area):
                app=AppTest.from_file(str(Path(__file__).with_name('fixture_planeacion_papel.py')),default_timeout=30).run()
                app.radio[0].set_value(area).run()
                if area!='Aprendizaje':
                    next(w for w in app.radio if w.label=='¿Qué vas a continuar?').set_value('Mi formato de especialista').run()
                next(w for w in app.button_group if w.label=='Modalidad de planeación').set_value('Individual').run()
                selector=next(w for w in app.multiselect if w.label=='Alumnos de mi formato')
                self.assertEqual(len(selector.options),2)
                next(b for b in app.button if b.label=='Seleccionar todos los alumnos individuales').click().run()
                self.assertEqual(next(w for w in app.multiselect if w.label=='Alumnos de mi formato').value,['I1','I2'])
                self.assertFalse(any(w.label=='Formato' for w in app.selectbox))
                next(b for b in app.button if b.label=='Abrir formato con mis alumnos').click().run()
                self.assertFalse(app.exception)
                d=app.session_state.versiones_ficticias[-1]
                self.assertEqual([a['ID_Alumno'] for a in d['datos']['Alumnos']],['I1','I2'])
                self.assertEqual(d['metadatos']['modalidad_planeacion'],'individual')
                self.assertFalse(d['metadatos']['individuales_en_sesion_grupal'])
                self.assertEqual(d['formato'],'XXV' if area=='Trabajo Social' else 'XXIII')
                self.assertFalse(papel.hoja(d)['grupal'])
                self.assertEqual(app.session_state.llamadas_ficticias,0)
                texto='\n'.join(p.extract_text() for p in PdfReader(BytesIO(generar_pdf(d))).pages)
                for a in d['datos']['Alumnos']:self.assertIn(a['Nombre del alumno'],texto)
                app.run();self.assertFalse(app.exception)
                self.assertEqual(app.session_state.versiones_ficticias[-1]['id'],d['id'])

    def test_grupal_multiple_conserva_guia_y_destinatarios(self):
        from streamlit.testing.v1 import AppTest
        from pathlib import Path
        app=AppTest.from_file(str(Path(__file__).with_name('fixture_planeacion_papel.py')),default_timeout=30).run()
        next(w for w in app.multiselect if w.label=='Alumnos de mi formato').set_value(['A1','A2']).run()
        next(b for b in app.button if b.label=='Abrir formato con mis alumnos').click().run()
        self.assertFalse(app.exception)
        d=app.session_state.versiones_ficticias[-1]
        self.assertEqual(d['metadatos']['modalidad_planeacion'],'grupal')
        self.assertEqual([r['ID_Alumno'] for r in guia_grupal(d)['filas']],['A1','A2'])

    def test_modalidad_multiple_rechaza_ajenos_grupales_y_duplicados(self):
        import pandas as pd
        from services.planeacion_modalidad import comprobar
        frame=pd.DataFrame([{'ID_Alumno':'I1','Tipo_Atencion':'Individual'},{'ID_Alumno':'I2','Tipo_Atencion':'Individual'},{'ID_Alumno':'G','Tipo_Atencion':'Grupal'}])
        antes=frame.copy(deep=True)
        comprobar(frame,['I1','I2'],'individual')
        self.assertEqual(simple.seleccion(frame,['I1','I2']),'individual')
        for ids in [['I1','G'],['I1','AJENO']]:
            with self.assertRaises(PermissionError):comprobar(frame,ids,'individual')
        for ids in [[],['I1','I1']]:
            with self.assertRaises(ValueError):comprobar(frame,ids,'individual')
        pd.testing.assert_frame_equal(frame,antes)

    def abrir(self,area='Aprendizaje'):
        from streamlit.testing.v1 import AppTest
        from pathlib import Path
        app=AppTest.from_file(str(Path(__file__).with_name('fixture_planeacion_papel.py')),default_timeout=30).run()
        app.radio[0].set_value(area).run()
        if area!='Aprendizaje':
            next(w for w in app.radio if w.label=='¿Qué vas a continuar?').set_value('Mi formato de especialista').run()
        next(m for m in app.multiselect if m.label=='Alumnos de mi formato').set_value(['A1']).run()
        next(b for b in app.button if b.label=='Abrir formato con mis alumnos').click().run()
        self.assertFalse(app.exception)
        return app

    def test_entrada_productiva_y_formato_por_funcion(self):
        for area in ['Aprendizaje','Psicología','Comunicación','Trabajo Social']:
            with self.subTest(area=area):
                app=self.abrir(area)
                self.assertEqual(app.session_state.llamadas_ficticias,0)
                doc=app.session_state.versiones_ficticias[-1]
                self.assertEqual(doc['formato'],'XXV' if area=='Trabajo Social' else 'XXIII')
                spec=papel.hoja(doc)
                headers={'Aprendizaje':['Nombre alumno','Discapacidad o condición','Fecha derivación','Aprendizaje','Psicología','Comunicación','Trabajo Social','Situación inicial','Situación final'],
                         'Trabajo Social':['Nombre del alumno','Grado','Grupo'],
                         'Psicología':['Necesidades educativas específicas','Competencias emocionales','Descriptor de logro'],
                         'Comunicación':['Necesidades educativas específicas','Aprendizaje y/u objetivo','Descriptor de logro']}
                self.assertEqual(spec['tables'][0]['headers'],headers[area])

    def test_evento_de_edicion_escribe_una_sola_version(self):
        import streamlit as st
        from ui import planeacion_papel as ui
        with patch.object(ui,'editor',side_effect=lambda **kw:st.session_state.get('evento_papel_ficticio')):
            app=self.abrir('Trabajo Social');d=app.session_state.versiones_ficticias[-1];antes=len(app.session_state.versiones_ficticias)
            app.session_state.evento_papel_ficticio={'nonce':'agregar-fila','documento':d['id'],'huella':papel.huella(d),'cambios':{},'accion':'agregar','tabla':'dosificacion'}
            app.run();d=app.session_state.versiones_ficticias[-1];antes=len(app.session_state.versiones_ficticias)
            indice=len(d['tablas']['dosificacion'])-1
            spec=papel.hoja(d);key=next(k for k,c in spec['cells'].items() if c['target']==('tabla','dosificacion',indice,'Actividades'))
            app.session_state.evento_papel_ficticio={'nonce':'evento-1','documento':d['id'],'huella':papel.huella(d),'cambios':{key:'Cambio dentro del documento'},'accion':'guardar'}
            app.run();self.assertFalse(app.exception)
            self.assertEqual(len(app.session_state.versiones_ficticias),antes+1)
            self.assertEqual(app.session_state.versiones_ficticias[-1]['tablas']['dosificacion'][indice]['Actividades'],'Cambio dentro del documento')
            app.run();self.assertEqual(len(app.session_state.versiones_ficticias),antes+1)

    def test_por_grado_incluye_individuales_sin_cambiar_su_modalidad(self):
        from streamlit.testing.v1 import AppTest
        from pathlib import Path
        app=AppTest.from_file(str(Path(__file__).with_name('fixture_planeacion_papel.py')),default_timeout=30).run()
        next(w for w in app.button_group if w.label=='Modalidad de planeación').set_value('Por grado').run()
        next(w for w in app.selectbox if w.label=='Grado').set_value('1').run()
        selector=next(w for w in app.multiselect if w.label=='Alumnos de mi formato')
        self.assertEqual(len(selector.options),1)
        selector.set_value(['I1']).run()
        next(b for b in app.button if b.label=='Abrir formato con mis alumnos').click().run()
        self.assertFalse(app.exception)
        doc=app.session_state.versiones_ficticias[-1]
        self.assertEqual([a['ID_Alumno'] for a in doc['datos']['Alumnos']],['I1'])
        self.assertTrue(doc['metadatos']['individuales_en_sesion_grupal'])

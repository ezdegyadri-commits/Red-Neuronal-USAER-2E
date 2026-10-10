from copy import deepcopy
from datetime import date
from pathlib import Path
import unittest
from unittest.mock import patch
import pandas as pd
from streamlit.testing.v1 import AppTest
from ui.planeacion_simple import periodo_actual,seleccion,PASOS


class SeleccionTests(unittest.TestCase):
    def test_cerrar_aportacion_usa_guardado_acotado(self):
        from ui import planeacion as u,planeacion_colaboracion as c
        state={'p_filas':[], 'p_pending':True}
        def guardar(p):state[p+'_pending']=False
        with patch.object(u.st,'session_state',state),patch.object(c,'_guardar',side_effect=guardar) as acotado,patch.object(u,'_persist') as completo:
            self.assertTrue(u._guardar_edicion_pendiente('p'))
        acotado.assert_called_once_with('p');completo.assert_not_called()
    def test_no_reemplaza_edicion_pendiente_entre_modalidades(self):
        from ui import planeacion_simple as simple
        base='planeacion_prueba';anterior={'id':'previo','revision':'r1'}
        state={base+'_individual_doc':deepcopy(anterior),base+'_individual_pending':True}
        with patch.object(simple.st,'session_state',state):
            with self.assertRaises(RuntimeError):simple._abrir(base,base+'_grupal',{'id':'otro','revision':'r2'})
        self.assertEqual(state[base+'_individual_doc'],anterior)
        self.assertNotIn(base+'_grupal_doc',state)

    def test_guardar_y_cerrar_no_sale_si_falla(self):
        from ui import auth,planeacion as u
        import hashlib
        base='planeacion_'+hashlib.sha256(b'prueba').hexdigest()[:12]
        state={'usuario':'prueba','autenticado':True,base+'_individual_pending':True}
        with patch.object(auth.st,'session_state',state),patch.object(auth.st,'warning'),patch.object(auth.st,'checkbox',return_value=False),patch.object(auth.st,'button',return_value=True),patch.object(u,'_persist',return_value=False) as guardar,patch.object(auth.st,'rerun') as rerun:
            auth.logout()
        guardar.assert_called_once_with(base+'_individual');rerun.assert_not_called()
        self.assertTrue(state['autenticado'])

    def test_guardar_y_cerrar_confirma_antes_de_salir(self):
        from ui import auth,planeacion as u
        import hashlib
        base='planeacion_'+hashlib.sha256(b'prueba').hexdigest()[:12]
        state={'usuario':'prueba','autenticado':True,base+'_grupal_pending':True}
        with patch.object(auth.st,'session_state',state),patch.object(auth.st,'warning'),patch.object(auth.st,'checkbox',return_value=False),patch.object(auth.st,'button',return_value=True),patch.object(u,'_persist',return_value=True) as guardar,patch.object(auth.st,'rerun') as rerun:
            auth.logout()
        guardar.assert_called_once_with(base+'_grupal');rerun.assert_called_once()
        self.assertNotIn('autenticado',state)

    def test_periodo_por_fecha_local(self):
        for fecha,esperado in [('2026-10-10',(2026,1)),('2027-02-02',(2026,2)),('2027-05-02',(2026,3)),('2026-08-30',(2026,1))]:
            self.assertEqual(periodo_actual(date.fromisoformat(fecha)),esperado)

    def test_inferencia_sin_cambiar_padron(self):
        df=pd.DataFrame([{'ID_Alumno':'I','Tipo_Atencion':'Individual'},{'ID_Alumno':'G','Tipo_Atencion':'Grupal'},{'ID_Alumno':'X','Tipo_Atencion':''}])
        antes=df.copy(deep=True)
        self.assertEqual(seleccion(df,['I']),'individual')
        self.assertEqual(seleccion(df,['G']),'grupal')
        self.assertEqual(seleccion(df,['I','G'],True),'grupal')
        for ids in (['I','G'],['X'],['ajeno']):
            with self.assertRaises(ValueError):seleccion(df,ids)
        pd.testing.assert_frame_equal(df,antes)


class RecorridoTests(unittest.TestCase):
    def setUp(self):
        from services import planeacion as s
        from ui import planeacion_generacion as g
        self.saved={k:getattr(s,k) for k in ('identidad','padron_autorizado','evidencias','guardar','listar','refrescar','versiones_actuales','guardar_aportacion')}
        self.escuelas=s.repo.escuelas;self.generar=g.generar_completa

    def tearDown(self):
        from services import planeacion as s
        from ui import planeacion_generacion as g
        for k,v in self.saved.items():setattr(s,k,v)
        s.repo.escuelas=self.escuelas;g.generar_completa=self.generar

    def abrir(self,area='Aprendizaje'):
        app=AppTest.from_file(str(Path(__file__).with_name('fixture_planeacion_simple.py')),default_timeout=30).run()
        app.radio[0].set_value(area).run()
        next(m for m in app.multiselect if m.label=='Alumno o alumnos para planear').set_value(['A1']).run()
        next(b for b in app.button if b.label=='Crear mi borrador').click().run()
        self.assertFalse(app.exception,area)
        return app

    def paso(self,app,paso):
        # segmented_control es un button_group en AppTest.
        next(w for w in app.button_group if w.label=='Mi recorrido').set_value(PASOS[paso]).run()
        self.assertFalse(app.exception)

    def test_cuatro_perfiles_generan_editan_y_recuperan(self):
        for area in ['Aprendizaje','Psicología','Comunicación','Trabajo Social']:
            with self.subTest(area=area):
                app=self.abrir(area)
                self.assertEqual({t.label for t in app.tabs},{'Mi planeación','Trabajo colaborativo'})
                self.assertFalse(any(r.label=='Cómo quieres trabajar' for r in app.radio))
                self.assertFalse(any(s.label in ['Documento','Escuela asignada'] for s in app.selectbox))
                self.assertFalse(any(n.label=='Duración de cada sesión (minutos)' for n in app.number_input))
                consent=[c for c in app.checkbox if c.label.startswith('Revisé el resumen')]
                self.assertEqual(len(consent),1)
                self.assertTrue(next(b for b in app.button if b.label=='Preparar mi planeación').disabled)
                self.assertEqual(app.session_state.llamadas_ficticias,0)
                consent[0].check().run()
                next(b for b in app.button if b.label=='Preparar mi planeación').click().run()
                self.assertFalse(app.exception,area)
                self.assertEqual(app.session_state.llamadas_ficticias,1)
                doc=app.session_state.versiones_ficticias[-1];did=doc['id']
                if area!='Aprendizaje':self.assertEqual(doc['metadatos']['equipo']['subgrupos'][0]['nombre'],'Subgrupo 1')
                self.assertIn('generacion_completa',doc['metadatos'])
                self.assertTrue(any(b.label=='Ver PDF' for b in app.button))
                campo='Observaciones' if area!='Trabajo Social' else 'Seguimiento'
                # Editar un campo existente sin cambiar identidad ni volver a IA.
                if any(t.label==campo for t in app.text_area):
                    next(t for t in app.text_area if t.label==campo).set_value('Redacción docente conservada.').run()
                next(b for b in app.button if b.label=='Guardar borrador').click().run()
                self.paso(app,0)
                next(b for b in app.button if b.label=='Continuar').click().run()
                self.assertFalse(app.exception,area)
                self.assertEqual(app.session_state.versiones_ficticias[-1]['id'],did)
                self.assertEqual(app.session_state.llamadas_ficticias,1)

    def test_pdf_solo_bajo_demanda_y_no_ia_al_editar(self):
        from ui import planeacion as u
        with patch.object(u,'generar_pdf',wraps=u.generar_pdf) as pdf:
            app=self.abrir();self.assertEqual(pdf.call_count,0)
            self.paso(app,2);self.assertEqual(pdf.call_count,0)
            next(b for b in app.button if b.label=='Ver PDF').click().run()
            self.assertFalse(app.exception);self.assertEqual(pdf.call_count,1)
            next(b for b in app.button if b.label=='Volver a editar').click().run()
            self.assertEqual(pdf.call_count,1)
            self.assertEqual(app.session_state.llamadas_ficticias,0)

    def test_configuracion_opcional_y_materiales_conservados(self):
        app=self.abrir()
        next(t for t in app.toggle if t.label=='Cambiar sesiones, apoyos o referencia').set_value(True).run()
        next(n for n in app.number_input if n.label=='Duración de cada sesión (minutos)').set_value(60).run()
        next(b for b in app.button if b.label=='Guardar borrador').click().run()
        self.paso(app,0);next(b for b in app.button if b.label=='Continuar').click().run()
        next(t for t in app.toggle if t.label=='Cambiar sesiones, apoyos o referencia').set_value(True).run()
        self.assertEqual(next(n for n in app.number_input if n.label=='Duración de cada sesión (minutos)').value,60)
        next(t for t in app.toggle if t.label=='Más herramientas').set_value(True).run()
        next(s for s in app.selectbox if s.label=='Herramienta que necesito').set_value('Materiales y escaneos').run()
        self.assertFalse(app.exception)
        self.assertTrue(any(w.label=='Materiales de apoyo' for w in app.get('file_uploader')))
        self.assertEqual(app.session_state.llamadas_ficticias,0)

    def test_instrumentos_y_referencias_no_se_cargan_al_abrir_editor(self):
        app=self.abrir()
        self.assertFalse(app.get('file_uploader') and any(w.label=='Materiales de apoyo' for w in app.get('file_uploader')))
        self.assertFalse(any(s.label=='Campo formativo' for s in app.selectbox))
        self.assertFalse(any(b.label=='Actualizar conexiones del expediente' for b in app.button))
        self.assertEqual(app.session_state.llamadas_ficticias,0)

    def test_historia_y_documentos_previos_siguen_visibles(self):
        app=self.abrir();count=len(app.session_state.versiones_ficticias)
        self.paso(app,0);next(b for b in app.button if b.label=='Continuar').click().run()
        self.assertEqual(len(app.session_state.versiones_ficticias),count)
        next(t for t in app.toggle if t.label=='Más herramientas').set_value(True).run()
        next(s for s in app.selectbox if s.label=='Herramienta que necesito').set_value('Respaldo y versiones').run()
        next(t for t in app.toggle if t.label=='Consultar versiones anteriores').set_value(True).run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.session_state.versiones_ficticias),count)

    def test_director_conserva_revision_y_colaboracion(self):
        app=self.abrir('Dirección')
        self.assertFalse(app.exception)
        self.assertEqual({t.label for t in app.tabs},{'Mi planeación','Trabajo colaborativo','Revisión directiva'})
        self.assertTrue(any(b.label=='Validar revisión' for b in app.button))
        self.assertTrue(any(b.label=='Devolver con observaciones' for b in app.button))

    def test_cache_y_prioridades_no_repiten_generacion(self):
        for area in ['Psicología','Trabajo Social']:
            app=self.abrir(area)
            if area=='Psicología':next(c for c in app.checkbox if c.label=='Regulación emocional').check().run()
            else:next(m for m in app.multiselect if m.label=='¿Con quién trabajarás? (opcional)').set_value(['Familia']).run()
            next(c for c in app.checkbox if c.label.startswith('Revisé el resumen')).check().run()
            next(b for b in app.button if b.label=='Preparar mi planeación').click().run()
            self.assertFalse(app.exception,area)
            self.assertEqual(app.session_state.llamadas_ficticias,1)
            self.paso(app,1)
            self.assertTrue(any(b.label=='Recuperar la generación guardada' for b in app.button),area)
            next(c for c in app.checkbox if c.label.startswith('Revisé el resumen')).check().run()
            next(b for b in app.button if b.label=='Recuperar la generación guardada').click().run()
            self.assertFalse(app.exception,area)
            self.assertEqual(app.session_state.llamadas_ficticias,1)
    def test_intervencion_individual_no_confirma_nee_automaticamente(self):
        source=Path(__file__).with_name('fixture_planeacion_panel.py').read_text(encoding='utf-8').replace('from ui.planeacion import _planeacion_page_clasica as planeacion_page','from ui.planeacion import planeacion_page')
        app=AppTest.from_string(source,default_timeout=30).run()
        next(m for m in app.multiselect if m.label=='Alumno o alumnos para planear').set_value(['A1']).run()
        next(w for w in app.button_group if w.label=='¿Qué documento necesitas?').set_value('Plan de intervención').run()
        next(b for b in app.button if b.label=='Crear mi borrador').click().run()
        self.assertFalse(app.exception)
        doc=app.session_state.fixture_versions[-1]
        self.assertEqual(doc['formato'],'XXI')
        self.assertEqual(doc['metadatos']['modalidad_planeacion'],'individual')
        self.assertFalse(doc['metadatos'].get('NEE confirmadas desde IEPP'))
        self.assertEqual(sum(c.label.startswith('Revisé') for c in app.checkbox),1)

    def test_competencias_y_contextos_son_prioridades_no_hallazgos(self):
        app=self.abrir('Psicología')
        next(c for c in app.checkbox if c.label=='Regulación emocional').check().run()
        self.assertFalse(app.exception)
        next(b for b in app.button if b.label=='Guardar borrador').click().run()
        doc=app.session_state.versiones_ficticias[-1]
        self.assertEqual(doc['metadatos']['configuracion_generacion']['competencias_priorizadas'],['Regulación emocional'])
        self.assertTrue(all(not c['Necesidad documentada'] for c in doc['metadatos']['equipo']['competencias']))
        app=self.abrir('Trabajo Social')
        next(m for m in app.multiselect if m.label=='¿Con quién trabajarás? (opcional)').set_value(['Familia']).run()
        self.assertFalse(app.exception)
        next(b for b in app.button if b.label=='Guardar borrador').click().run()
        self.assertEqual(app.session_state.versiones_ficticias[-1]['metadatos']['configuracion_generacion']['contextos_priorizados'],['Familia'])
        self.assertEqual(app.session_state.llamadas_ficticias,0)


if __name__=='__main__':unittest.main()

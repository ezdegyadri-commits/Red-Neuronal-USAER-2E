"""Hoja tradicional, propuestas aditivas y compatibilidad sin datos reales."""
from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch
from services import planeacion as s
from services.planeacion_papel import huella
from services.planeacion_propuesta import conservar_redaccion,aplicar
from tests.test_planeacion_cero_friccion import individual,ACTOR


class DocumentoTests(TestCase):
    def test_propuesta_nunca_borra_redaccion_ni_sesiones(self):
        doc=individual();doc['textos']['Evaluación']='Instrumento docente'
        doc['metadatos']['equipo']={'sesiones':[{'id':'s1','actividad':'Texto docente'}]}
        candidate=deepcopy(doc);candidate['tablas']['aprendizajes']=[]
        candidate['tablas']['dosificacion']=[{'Actividades':'Propuesta nueva'}]
        candidate['textos']['Evaluación']='Otro instrumento'
        candidate['metadatos']['equipo']['sesiones']=[{'id':'s1','actividad':'No sustituir'},{'id':'s2','actividad':'Nueva sesión'}]
        antes=deepcopy(doc);result=conservar_redaccion(doc,candidate)
        self.assertEqual(result['tablas']['aprendizajes'],doc['tablas']['aprendizajes'])
        self.assertEqual(result['textos']['Evaluación'],'Instrumento docente')
        self.assertEqual(result['metadatos']['equipo']['sesiones'][0]['actividad'],'Texto docente')
        self.assertEqual(len(result['metadatos']['equipo']['sesiones']),2)
        self.assertEqual(doc,antes)

    def test_aceptar_solo_sobre_la_misma_edicion_y_mismos_alumnos(self):
        doc=individual();pack={'base':huella(doc),'documento':deepcopy(doc)}
        with patch.object(s,'autorizar',return_value=ACTOR):
            self.assertEqual(aplicar(doc,pack),doc)
            changed=deepcopy(doc);changed['textos']['Evaluación']='Edición posterior'
            with self.assertRaises(ValueError):aplicar(changed,pack)
            pack['documento']['datos']['Alumnos']=[]
            with self.assertRaises(ValueError):aplicar(doc,pack)

    def test_ruta_nueva_directa_y_formulario_abierto_protegido(self):
        from ui import planeacion_papel as ui,planeacion_cero_friccion as vieja
        d=individual();state={'p_doc':d}
        with patch.object(ui.st,'session_state',state),patch.object(ui,'hoja') as hoja,patch.object(vieja,'hoja') as antigua:
            ui.presentar('p');hoja.assert_called_once();antigua.assert_not_called()
            state['p_'+d['id']+'_captura_0_celda']='Texto no enviado'
            ui.presentar('p');antigua.assert_called_once()
            state['p_editor_directo']=True;ui.presentar('p')
            self.assertEqual(hoja.call_count,2)

    def test_hoja_sin_ayuda_no_consulta_ia_ni_versiones_ocultas(self):
        from pathlib import Path
        import ast
        source=(Path(__file__).parents[1]/'ui'/'planeacion_papel.py').read_text(encoding='utf-8')
        tree=ast.parse(source)
        gated=next(n for n in ast.walk(tree) if isinstance(n,ast.If) and "action == 'opciones'" in ast.unparse(n.test))
        self.assertIn('_acciones(',ast.unparse(gated))
        self.assertIn('[data-stale="true"]{opacity:1!important}',source)
        ayuda=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='conexiones')
        self.assertIn('st.dialog(',ast.unparse(ayuda))
        self.assertNotIn('run_every',ast.unparse(ayuda))


HELP_APP='''
import streamlit as st
from unittest.mock import patch
from tests.test_planeacion_cero_friccion import individual,ACTOR
from services import planeacion as s,planeacion_generacion as g
from ui import planeacion_asistente as ui,planeacion as u
if 'p_doc' not in st.session_state:st.session_state['p_doc']=individual()
def guardar(*a,**k):
    st.session_state['guardados']=st.session_state.get('guardados',0)+1
    st.session_state['p_pending']=False
    return True
with patch('ui.planeacion_memoria.actualizar',return_value=True),patch.object(s,'autorizar',return_value=ACTOR),patch.object(g,'configuracion',return_value={}),patch.object(u,'_persist',side_effect=guardar):
    ui.panel('p')
'''


class AsistenteTests(TestCase):
    def test_ayuda_aparece_en_dialogo_y_cerrar_no_guarda(self):
        from streamlit.testing.v1 import AppTest
        source=HELP_APP.replace("    ui.panel('p')", "    from ui.planeacion_papel import conexiones\n    conexiones('p')")
        app=AppTest.from_string(source,default_timeout=30)
        app.session_state['p_papel_panel']='ia';app.run()
        self.assertFalse(app.exception)
        self.assertTrue(any(h.value=='Actividades para esta planeación' for h in app.subheader))
        next(b for b in app.button if b.label=='Cerrar conexión y seguir en mi hoja').click().run()
        self.assertFalse(app.exception)
        self.assertNotIn('p_papel_panel',app.session_state)
        self.assertNotIn('guardados',app.session_state)

    def test_local_se_revisa_antes_de_anadir_y_descartar_no_escribe(self):
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_string(HELP_APP,default_timeout=30).run()
        self.assertFalse(app.exception);before=deepcopy(app.session_state['p_doc'])
        next(r for r in app.radio if r.label=='Preparar actividades').set_value('Con mis datos, sin IA').run()
        next(b for b in app.button if b.label=='Preparar propuesta').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['p_doc'],before)
        self.assertNotIn('guardados',app.session_state)
        next(b for b in app.button if b.label=='Descartar propuesta').click().run()
        self.assertFalse(app.exception);self.assertEqual(app.session_state['p_doc'],before)
        next(b for b in app.button if b.label=='Preparar propuesta').click().run()
        next(b for b in app.button if b.label=='Añadir propuesta a mi formato').click().run()
        self.assertFalse(app.exception);self.assertEqual(app.session_state['guardados'],1)
        self.assertGreater(len(app.session_state['p_doc']['tablas']['dosificacion']),len(before['tablas']['dosificacion']))

    def test_ia_no_se_llama_al_abrir_ni_al_preparar_resumen(self):
        from streamlit.testing.v1 import AppTest
        from services import planeacion_generacion as g
        sol={'huella':'ficticia','resumen':'Resumen educativo sin identificación'}
        with patch.object(g,'preparar_solicitud',return_value=sol),patch('ai.planeacion_completa.generar_completa') as ia:
            app=AppTest.from_string(HELP_APP,default_timeout=30).run()
            next(r for r in app.radio if r.label=='Preparar actividades').set_value('Con IA')
            next(b for b in app.button if b.label=='Preparar propuesta').click().run()
            self.assertFalse(app.exception);ia.assert_not_called()
            boton=next(b for b in app.button if b.label=='Generar actividades con este resumen')
            self.assertTrue(boton.disabled)

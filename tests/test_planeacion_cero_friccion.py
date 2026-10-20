"""Captura sin escrituras intermedias, con datos exclusivamente ficticios."""
import ast
from copy import deepcopy
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch
import pandas as pd
from streamlit.testing.v1 import AppTest
from services import planeacion_cero_friccion as flujo,planeacion_papel as papel
from services import planeacion as s
from tests.test_planeacion_panel import documento,ACTOR


def individual(area='Aprendizaje'):
    d=documento('XXV' if area=='Trabajo Social' else 'XXIII')
    d['datos']['Función']=area;d['metadatos']['modalidad_planeacion']='individual'
    key='barreras' if area=='Trabajo Social' else 'aprendizajes'
    from services.planeacion_modelo import FORMATOS
    d['tablas'][key]=[{h:'Texto de prueba '+h for h in FORMATOS[d['formato']]['tablas'][key]}]
    d['tablas'][key][0]['_alumnos_apartados']=['A1']
    d['tablas'][key][0]['_origenes']=[{'registro':'FICTICIO'}]
    return d


class CapturaTests(TestCase):
    def test_edita_toda_celda_conservando_origen_y_entrada(self):
        for area in ('Aprendizaje','Psicología','Comunicación','Trabajo Social'):
            doc=individual(area);before=deepcopy(doc)
            with patch.object(s,'autorizar',return_value={**ACTOR,'area':area}):
                spec=papel.hoja(doc)
                cambios={c['id']:'Nueva redacción' for c in spec['cells'].values() if c['editable'] and c['target'][0]=='tabla'}
                actual=flujo.capturar(doc,spec,cambios)
            tabla='barreras' if area=='Trabajo Social' else 'aprendizajes'
            self.assertEqual(actual['tablas'][tabla][0]['_origenes'],[{'registro':'FICTICIO'}])
            self.assertEqual(actual['tablas'][tabla][0]['_alumnos_apartados'],['A1'])
            self.assertEqual(doc,before)
            self.assertTrue(all(actual['tablas'][tabla][0][h]=='Nueva redacción' for h in before['tablas'][tabla][0] if not h.startswith('_')))

    def test_no_filas_de_relleno_y_retiro_es_version_local(self):
        doc=individual();before=deepcopy(doc)
        with patch.object(s,'autorizar',return_value=ACTOR):
            spec=papel.hoja(doc)
            result=flujo.capturar(doc,spec,{},nuevas={'aprendizajes':{'Descriptor de logro':'  '}})
            self.assertEqual(len(result['tablas']['aprendizajes']),1)
            result=flujo.capturar(doc,spec,{},retirar={'aprendizajes':[0]})
            self.assertEqual(result['tablas']['aprendizajes'],[])
        self.assertEqual(doc,before)

    def test_fuentes_padron_y_aportes_protegidos(self):
        doc=individual();doc['tablas']['aprendizajes'][0]['_aporte']='otra-area'
        with patch.object(s,'autorizar',return_value=ACTOR):
            spec=papel.hoja(doc)
            with self.assertRaises(PermissionError):flujo.capturar(doc,spec,{},retirar={'aprendizajes':[0]})
            with self.assertRaises(PermissionError):flujo.capturar(doc,spec,{'celda-inventada':'Cambiar'})

    def test_escuelas_por_id_y_roles_sin_opciones_ajenas(self):
        frame=pd.DataFrame([{'ID_Escuela':'E1','Nombre':'Igual'},{'ID_Escuela':'E10','Nombre':'Igual'}])
        self.assertEqual(list(flujo.seleccionar_escuela(frame,'E1')['ID_Escuela']),['E1'])
        self.assertTrue(flujo.seleccionar_escuela(frame,'E').empty)
        self.assertNotIn('Planeación del Equipo de Paradocentes',flujo.campos_del_rol(ACTOR))
        self.assertNotIn('Planeación del Docente de Apoyo',flujo.campos_del_rol({**ACTOR,'area':'Psicología'}))

    def test_anexo_xix_no_pasa_por_formulario_ni_tick(self):
        from tests.test_planeacion_compartida import grupal
        self.assertFalse(flujo.aplica(grupal()))
        tree=ast.parse((Path(__file__).parents[1]/'ui'/'planeacion_papel.py').read_text(encoding='utf-8'))
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='presentar')
        self.assertFalse(fn.decorator_list)

    def test_ia_no_envia_sin_previa_consentida_o_si_cambio_resumen(self):
        from ui.planeacion_cero_friccion import _asistencia
        from services import planeacion_generacion as g
        doc=individual();sol={'huella':'nueva','resumen':'Resumen educativo'}
        with patch.object(g,'preparar_solicitud',return_value=sol),patch('ai.planeacion_completa.generar_completa') as ia:
            for preview,consent in [(None,False),({'huella':'vieja'},True),({'huella':'nueva'},False)]:
                actual,pendiente,_=_asistencia(doc,'Proponer actividades con IA',{},preview,consent)
                self.assertEqual(actual,doc);self.assertEqual(pendiente,sol)
            ia.assert_not_called()


APP='''
import streamlit as st
from unittest.mock import patch
from tests.test_planeacion_cero_friccion import individual,ACTOR
from services import planeacion as s
from ui import planeacion as u
from ui.planeacion_cero_friccion import hoja
area=st.session_state.get('test_area','Aprendizaje')
if 'p_doc' not in st.session_state:st.session_state.p_doc=individual(area)
def guardar(prefix,estado='BORRADOR'):
    st.session_state['guardados']=st.session_state.get('guardados',0)+1
    ok=st.session_state.get('test_exito',True)
    st.session_state[prefix+'_pending']=not ok
    if ok:st.session_state[prefix+'_doc']['guardado_en']='2026-10-19T20:00:00-06:00'
    return ok
with patch.object(s,'autorizar',return_value={**ACTOR,'area':area}),patch.object(u,'_persist',side_effect=guardar),patch.object(u,'_pdf_sesion',return_value=b'%PDF'),patch('ui.archivo_expediente.boton'):
    hoja('p')
'''


class FormularioTests(TestCase):
    def test_cuatro_roles_un_solo_envio_y_todo_editable(self):
        for area in ('Aprendizaje','Psicología','Comunicación','Trabajo Social'):
            app=AppTest.from_string(APP,default_timeout=30)
            app.session_state['test_area']=area;app.run()
            self.assertFalse(app.exception,area)
            self.assertNotIn('guardados',app.session_state)
            maestros=[b for b in app.button if b.label=='Guardar Planeación']
            self.assertEqual(len(maestros),1)
            label='Apoyos y/o ajustes razonables' if area=='Trabajo Social' else 'Descriptor de logro'
            next(t for t in app.text_area if t.label==label).set_value('Cambio docente')
            maestros[0].click().run()
            self.assertFalse(app.exception,area)
            self.assertEqual(app.session_state['guardados'],1)
            tabla='barreras' if area=='Trabajo Social' else 'aprendizajes'
            self.assertEqual(app.session_state['p_doc']['tablas'][tabla][0][label],'Cambio docente')

    def test_fallo_no_borra_captura_enviada(self):
        app=AppTest.from_string(APP,default_timeout=30);app.session_state['test_exito']=False;app.run()
        next(t for t in app.text_area if t.label=='Descriptor de logro').set_value('Conservar este texto')
        next(b for b in app.button if b.label=='Guardar Planeación').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['p_doc']['tablas']['aprendizajes'][0]['Descriptor de logro'],'Conservar este texto')
        self.assertTrue(app.session_state['p_pending'])

    def test_propuesta_local_se_revisa_y_se_integra_sin_otra_botonera(self):
        app=AppTest.from_string(APP,default_timeout=30).run()
        next(w for w in app.selectbox if w.label=='Al guardar quiero').set_value('Proponer actividades sin IA')
        next(b for b in app.button if b.label=='Guardar Planeación').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['p_captura_preview']['tipo'],'local')
        next(c for c in app.checkbox if c.label.startswith('Revisé las propuestas locales')).check()
        next(b for b in app.button if b.label=='Guardar Planeación').click().run()
        self.assertFalse(app.exception)
        self.assertTrue(app.session_state['p_doc']['tablas']['dosificacion'])
        self.assertTrue(any('Inicio:' in r.get('Actividades','') for r in app.session_state['p_doc']['tablas']['dosificacion']))

    def test_ia_solo_tras_revisar_resumen_y_un_nuevo_envio(self):
        from services import planeacion_generacion as g
        solicitud={'huella':'verificada','resumen':'Alumno 1 necesita apoyos de lectura.',
            'evidencias':{'DOCENTE':['Alumno 1']},'contexto':{},'ajustes':{},'aliases':{'Alumno 1':'A1'}}
        def ensamblar(doc,*args):
            result=deepcopy(doc);result['metadatos']['generacion_completa']={}
            result['tablas']['dosificacion'].append({'Actividades':'Actividad propuesta y editable','Contextos':'Aula regular'})
            return result
        with patch.object(g,'preparar_solicitud',return_value=solicitud),patch.object(g,'ensamblar',side_effect=ensamblar),patch('ai.planeacion_completa.generar_completa',return_value={'unidades':[{}]}) as ia,patch('ai.planeacion.modelo_configurado',return_value='motor-ficticio'):
            app=AppTest.from_string(APP,default_timeout=30).run()
            next(w for w in app.selectbox if w.label=='Al guardar quiero').set_value('Proponer actividades con IA')
            next(b for b in app.button if b.label=='Guardar Planeación').click().run()
            self.assertFalse(app.exception);ia.assert_not_called()
            next(c for c in app.checkbox if c.label.startswith('Revisé este resumen')).check()
            next(b for b in app.button if b.label=='Guardar Planeación').click().run()
            self.assertFalse(app.exception);ia.assert_called_once()
            self.assertEqual(app.session_state['p_doc']['tablas']['dosificacion'][-1]['Actividades'],'Actividad propuesta y editable')

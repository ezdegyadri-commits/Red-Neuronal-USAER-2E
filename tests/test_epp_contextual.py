"""Datos ficticios: permisos, fuentes, concurrencia y una solicitud por acción."""
from copy import deepcopy
from concurrent.futures import Future
from pathlib import Path
import json
import unittest
from unittest.mock import patch,MagicMock
from tests.test_epp import EPPTests,ACTOR
from services import epp as s,epp_contextual as servicio
from services.epp_modelo import AREAS,campos,vacia,NEE,BAP


def respuesta(solicitud):
    ref=solicitud['datos']['fuentes'][0]['id']
    return {'apartados':[dict(d,redaccion='Hallazgo documentado para '+d['campo'],fuentes=[ref]) for d in solicitud['datos']['destinos']],
        'nee':[],'bap':[],'faltantes':[]}


class ContextualTests(unittest.TestCase):
    setUp=EPPTests.setUp
    tearDown=EPPTests.tearDown
    def doc(self):
        d=s.crear('FICTICIO-A1','2026-2027')
        for area in AREAS:
            v=vacia(area);v['evaluaciones']=[{'id':'prueba-'+area,'nombre':'Observación '+area,'texto':'Alumno de prueba realiza una tarea con modelado visual.','fecha':'2026-10-27'}]
            d['partes'][area]={'contenido':v,'revision':'rev-'+area}
        return d

    def test_global_reune_todas_las_areas_anonimizadas_una_vez(self):
        p=servicio.preparar(self.doc())
        self.assertEqual(len(p['datos']['fuentes']),4)
        self.assertEqual({f['area'] for f in p['datos']['fuentes']},set(AREAS))
        self.assertNotIn('Alumno de prueba',json.dumps(p['datos']))
        self.assertEqual({x['area'] for x in p['datos']['destinos']},{'Aprendizaje','Conclusión'})
        self.assertNotIn('alumno',p['datos']);self.assertNotIn('Nombre_Completo',p['datos']['contexto'])

    def test_global_no_pisa_texto_humano_ni_no_requerido(self):
        d=self.doc();field=campos('Aprendizaje')[0];omit=campos('Aprendizaje')[1]
        d['partes']['Aprendizaje']['contenido']['campos'][field]='Texto humano conservado'
        d['partes']['Aprendizaje']['contenido']['no_requeridos']={omit:True}
        p=servicio.preparar(d);r=respuesta(p);nuevo,areas,conflictos=servicio.aplicar(d,p,r)
        self.assertEqual(nuevo['partes']['Aprendizaje']['contenido']['campos'][field],'Texto humano conservado')
        self.assertTrue(nuevo['partes']['Aprendizaje']['contenido']['no_requeridos'][omit])
        self.assertFalse(conflictos);self.assertEqual(d['partes']['Aprendizaje']['contenido']['campos'][campos('Aprendizaje')[2]],'')

    def test_inline_y_edicion_durante_ia_conserva_aporte_nuevo(self):
        d=self.doc();field=campos('Aprendizaje')[0];p=servicio.preparar(d,('Aprendizaje',field));r=respuesta(p)
        self.assertEqual(len(p['datos']['destinos']),1)
        now=deepcopy(d);now['partes']['Aprendizaje']['contenido']['campos'][field]='Edición durante la espera'
        nuevo,areas,conflictos=servicio.aplicar(now,p,r)
        self.assertFalse(areas);self.assertTrue(conflictos)
        self.assertEqual(nuevo['partes']['Aprendizaje']['contenido']['campos'][field],'Edición durante la espera')

    def test_fuentes_inexistentes_apartados_ajenos_y_duplicados_rechazados(self):
        p=servicio.preparar(self.doc());r=respuesta(p)
        for change in ('fuente','ajeno','duplicado'):
            bad=deepcopy(r)
            if change=='fuente':bad['apartados'][0]['fuentes']=['EV999']
            elif change=='ajeno':bad['apartados'][0]['campo']='3.5. Cociente intelectual'
            else:bad['apartados'].append(bad['apartados'][0])
            with self.assertRaises(ValueError):servicio.validar(bad,p)

    def test_comunicacion_solo_propios_y_compartidos(self):
        d=self.doc()
        with patch.object(s,'actor',return_value={**ACTOR,'area':'Comunicación','rol':'COMUNICACION','cuenta':'com-ficticia'}):
            p=servicio.preparar(d)
            self.assertFalse(p['coordinadora'])
            self.assertIn({'area':'Psicología','campo':'4.3. Coordinación motriz fina'},p['datos']['destinos'])
            with self.assertRaises(PermissionError):servicio.preparar(d,('Psicología','3.5. Cociente intelectual'))
            nuevo,areas,_=servicio.aplicar(d,p,respuesta(p))
            self.assertEqual(areas,{'Comunicación','Psicología','Aprendizaje'})
            self.assertEqual(nuevo['partes']['Psicología']['contenido']['campos']['3.5. Cociente intelectual'],'')

    def test_tablas_no_sobrescriben_captura_humana_ni_duplican(self):
        d=self.doc();v=vacia('Conclusión');human=dict.fromkeys(NEE,'');human['NEE']='Necesita usar apoyos visuales'
        v['nee']=[human];d['partes']['Conclusión']={'contenido':v,'revision':'c1'}
        p=servicio.preparar(d);r=respuesta(p)
        r['nee']=[{**human,'fuentes':['EV1']}]
        n,_,_=servicio.aplicar(d,p,r)
        rows=n['partes']['Conclusión']['contenido']['nee']
        self.assertEqual(len(rows),1)
        self.assertEqual({k:rows[0][k] for k in NEE},human)
        self.assertFalse(n['partes']['Conclusión']['contenido']['validada'])

    def test_sin_evidencia_no_se_llama_motor(self):
        d=self.doc()
        for area in AREAS:d['partes'][area]['contenido']['evaluaciones']=[]
        with self.assertRaises(ValueError):servicio.preparar(d)

    def test_motor_una_llamada_y_json_validado(self):
        from ai import epp_contextual as motor
        p=servicio.preparar(self.doc());client=MagicMock();client.models.generate_content.return_value.text=json.dumps(respuesta(p))
        with patch('google.genai.Client',return_value=client):
            result=motor.generar(p,{'gemini':'ficticia','modelos':['modelo-configurado','respaldo'],'openai':''})
        self.assertEqual(len(result['apartados']),len(p['datos']['destinos']))
        self.assertEqual(client.models.generate_content.call_count,1)

    def test_motor_respaldo_solo_ante_fallo(self):
        from ai import epp_contextual as motor
        p=servicio.preparar(self.doc());client=MagicMock()
        exc=RuntimeError('Servicio ocupado');exc.code=503
        result=MagicMock();result.text=json.dumps(respuesta(p))
        client.models.generate_content.side_effect=[exc,result]
        with patch('google.genai.Client',return_value=client):motor.generar(p,{'gemini':'ficticia','modelos':['uno','dos'],'openai':''})
        self.assertEqual(client.models.generate_content.call_count,2)

    def test_lectura_visual_rechaza_archivo_antes_de_enviar(self):
        from ai import epp_contextual as motor
        with patch.object(motor._pool,'submit') as submit:
            with self.assertRaises(ValueError):motor.enviar_lectura(b'foto','text/html',{})
            with self.assertRaises(ValueError):motor.enviar_lectura(b'x'*(5*1024*1024+1),'image/png',{})
            submit.assert_not_called()

    def test_lectura_visual_sintesis_sin_calificar_prueba(self):
        from ai import epp_contextual as motor
        client=MagicMock();client.models.generate_content.return_value.text=json.dumps({'sintesis':'Resultado registrado: requiere modelado visual.'})
        with patch('google.genai.Client',return_value=client):
            result=motor.leer_visual(b'foto-ficticia','image/png',{'gemini':'ficticia','modelos':['configurado']})
        self.assertIn('modelado visual',result['texto'])
        self.assertEqual(client.models.generate_content.call_count,1)

    def test_diario_confirma_por_area_y_conserva_fallo_para_reintento(self):
        from ui import epp_contextual as ui
        d=self.doc();captures={a:(d,{},vacia(a),'r') for a in ('Aprendizaje','Conclusión')}
        def write(doc,area,*args):
            if area=='Conclusión':raise RuntimeError('fallo ficticio')
            return {'contenido':vacia(area),'revision':'confirmada','fecha':'2026-10-27'}
        with patch.object(s,'guardar_cambios',side_effect=write):results=ui._escribir(captures)
        self.assertEqual(results['Aprendizaje']['saved']['revision'],'confirmada')
        self.assertTrue(results['Conclusión']['error'])


class ContextualUITests(unittest.TestCase):
    def app(self):
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_file(str(Path(__file__).parent/'fixtures/epp_viva_app.py'),default_timeout=40)
        app.query_params['principal']='1';return app.run()

    def test_hub_documento_completo_sin_modal_ni_motor(self):
        app=self.app();self.assertFalse(app.exception)
        self.assertTrue(any(b.label=='✨ Redactar EPP Automáticamente' for b in app.button))
        self.assertTrue(any(b.label=='✨ Autocompletar' for b in app.button))
        self.assertFalse(any(x.label in ('Motor de IA','Apartado a redactar / enriquecer:') for x in app.selectbox))
        self.assertFalse(app.get('dialog'))
        self.assertTrue(any('3. Funcionamiento intelectual' in x.label for x in app.expander))
        self.assertTrue(any('7. Conclusión' in x.label for x in app.expander))

    def test_una_accion_llena_widgets_y_no_exige_seleccionar_apartado(self):
        from ui import epp_contextual as ui
        def enqueue(p,config):
            future=Future();future.set_result(respuesta(p));return future
        with patch('ai.epp_contextual.enviar',side_effect=enqueue),patch('ai.epp_contextual.configuracion',return_value={}),patch.object(ui,'guardados'):
            app=self.app()
            next(t for t in app.text_area if t.label=='5.1. Competencia curricular').set_value('Observación de lectura documentada').run()
            next(c for c in app.checkbox if c.label.startswith('Autorizo usar los hallazgos')).check().run()
            next(b for b in app.button if b.label=='✨ Redactar EPP Automáticamente').click().run()
            self.assertFalse(app.exception)
            self.assertEqual(next(t for t in app.text_area if t.label=='5.1. Competencia curricular').value,'Observación de lectura documentada')
            self.assertIn('Hallazgo documentado',next(t for t in app.text_area if t.label=='5.2. Estilo de aprendizaje').value)

    def test_generacion_pendiente_permite_escribir_sin_segundo_envio(self):
        pending=Future()
        with patch('ai.epp_contextual.enviar',return_value=pending) as send,patch('ai.epp_contextual.configuracion',return_value={}):
            app=self.app()
            next(t for t in app.text_area if t.label=='5.1. Competencia curricular').set_value('Observación documentada').run()
            next(c for c in app.checkbox if c.label.startswith('Autorizo usar los hallazgos')).check().run()
            next(b for b in app.button if b.label=='✨ Redactar EPP Automáticamente').click().run()
            self.assertTrue(next(b for b in app.button if b.label=='✨ Redactar EPP Automáticamente').disabled)
            next(t for t in app.text_area if t.label=='5.1. Competencia curricular').set_value('Edición durante generación').run()
            self.assertEqual(send.call_count,1)
            self.assertFalse(app.exception)
            self.assertEqual(next(t for t in app.text_area if t.label=='5.1. Competencia curricular').value,'Edición durante generación')


if __name__=='__main__':unittest.main()

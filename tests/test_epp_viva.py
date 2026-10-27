"""EPP viva: alumnos ficticios, sin escrituras reales ni solicitudes de IA."""
from copy import deepcopy
from pathlib import Path
import json
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from services import epp as s,epp_papel as papel
from services.epp_modelo import vacia
from tests.test_epp import EPPTests,ACTOR,ALUMNO


class ContratoTests(EPPTests):
    def event(self,doc,field,text='Hallazgo documentado.',action='guardar'):
        spec=papel.hoja(doc)
        c=next(c for c in spec['cells'].values() if c['editable'] and c['label']==field)
        return {'nonce':'prueba','documento':doc['id'],'huella':spec['huella'],'cambios':{c['id']:text},'accion':action}

    def test_hoja_tiene_todas_las_areas_y_solo_funcion_editable(self):
        d=self.doc()
        for area in ('Aprendizaje','Psicología','Comunicación','Trabajo Social','Dirección'):
            with patch.object(s,'actor',return_value={**ACTOR,'area':area,'rol':'MAESTRO DE APOYO' if area=='Aprendizaje' else area,'director':area=='Dirección'}):
                spec=papel.hoja(d)
                import re
                self.assertTrue(all(re.fullmatch(r'[a-zA-Z0-9_-]+',key) for key in spec['cells']))
                owners={c['target'][0] for c in spec['cells'].values() if c['editable']}
                expected={'Aprendizaje':{'Aprendizaje','Conclusión'},'Comunicación':{'Comunicación','Aprendizaje','Psicología'},'Trabajo Social':{'Trabajo Social','Aprendizaje'},'Psicología':{'Psicología'},'Dirección':set()}
                self.assertEqual(owners,expected[area])
                for section in ('2. Información inicial y salud','3. Funcionamiento intelectual','4. Conducta adaptativa','5. Funcionamiento académico','6. Contextos'):
                    self.assertTrue(any(t['title']==section for t in spec['tables']))

    def test_celda_ajena_rechazada_en_servidor(self):
        d=self.doc();spec=papel.hoja(d)
        c=next(c for c in spec['cells'].values() if c['label']=='3.1. Atención' and c['target'] is not None)
        e={'documento':d['id'],'huella':spec['huella'],'cambios':{c['id']:'No autorizado'},'accion':'guardar'}
        with self.assertRaises(PermissionError):papel.aplicar(d,e)

    def test_aplicar_no_modifica_otra_area_y_no_duplica_informe(self):
        d=self.doc();e=self.event(d,'5.1. Competencia curricular')
        n,areas=papel.aplicar(d,e)
        self.assertEqual(areas,{'Aprendizaje'});self.assertNotIn('Psicología',n['partes'])
        saved=s.guardar_cambios(d,'Aprendizaje',vacia('Aprendizaje'),n['partes']['Aprendizaje']['contenido'],'')
        again=s.guardar_cambios(d,'Aprendizaje',vacia('Aprendizaje'),n['partes']['Aprendizaje']['contenido'],'')
        self.assertEqual(saved['revision'],again['revision']);self.assertEqual(len(self.sheet.rows),2)

    def test_tres_vias_combina_celdas_independientes_de_misma_area(self):
        d=self.doc();base=vacia('Aprendizaje');uno=deepcopy(base);dos=deepcopy(base)
        uno['campos']['5.1. Competencia curricular']='Primer hallazgo'
        dos['campos']['5.2. Estilo de aprendizaje']='Segundo hallazgo'
        s.guardar_cambios(d,'Aprendizaje',base,uno,'')
        result=s.guardar_cambios(d,'Aprendizaje',base,dos,'')['contenido']
        self.assertEqual(result['campos']['5.1. Competencia curricular'],'Primer hallazgo')
        self.assertEqual(result['campos']['5.2. Estilo de aprendizaje'],'Segundo hallazgo')

    def test_tres_vias_no_sobrescribe_conflicto_en_mismo_dato(self):
        d=self.doc();b=vacia('Aprendizaje');uno=deepcopy(b);dos=deepcopy(b)
        uno['campos']['5.1. Competencia curricular']='Remoto'
        dos['campos']['5.1. Competencia curricular']='Local'
        s.guardar_cambios(d,'Aprendizaje',b,uno,'')
        with self.assertRaises(RuntimeError):s.guardar_cambios(d,'Aprendizaje',b,dos,'')
        self.assertEqual(len(self.sheet.rows),2)

    def test_acuse_perdido_reintento_recupera_sin_duplicar(self):
        d=self.doc();v=vacia('Aprendizaje');original=self.sheet.append_rows
        def append(*args,**kwargs):
            original(*args,**kwargs)
            raise ConnectionError('Confirmación interrumpida después del append')
        with patch.object(self.sheet,'append_rows',side_effect=append):
            with self.assertRaises(ConnectionError):s.guardar(d,'Aprendizaje',v,'')
        self.assertEqual(len(self.sheet.rows),2)
        s.guardar(d,'Aprendizaje',v,'');self.assertEqual(len(self.sheet.rows),2)

    def test_pendiente_conservado_al_sincronizar_otro_especialista(self):
        from ui import epp_viva as ui
        d=self.doc();v=vacia('Aprendizaje');v['campos']['5.1. Competencia curricular']='Texto local'
        local=deepcopy(d);local['partes']['Aprendizaje']={'contenido':v,'revision':''}
        remote=deepcopy(d);remote['partes']['Psicología']={'contenido':vacia('Psicología'),'revision':'psico'}
        state={'p_doc':local,'p_cola':{'Aprendizaje':{'base':vacia('Aprendizaje'),'revision':''}}}
        with patch.object(ui.st,'session_state',state),patch.object(s,'listar',return_value=[remote]):ui.sincronizar('p')
        self.assertEqual(state['p_doc']['partes']['Aprendizaje']['contenido'],v)
        self.assertEqual(state['p_doc']['partes']['Psicología']['revision'],'psico')

    def test_respaldo_cliente_recupera_solo_mismo_alumno_y_area(self):
        d=self.doc();spec=papel.hoja(d)
        c=next(c for c in spec['cells'].values() if c['editable'] and c['label']=='5.1. Competencia curricular')
        backup={'tipo':'usaer-texto-pendiente-v2','documento':d['id'],'celdas':[{'target':c['target'],'base':'','valor':'Texto recuperable'}]}
        result=papel.recuperar(d,backup,'Aprendizaje')
        self.assertEqual(result['campos']['5.1. Competencia curricular'],'Texto recuperable')
        with self.assertRaises(ValueError):papel.recuperar(d,{**backup,'documento':'otro'},'Aprendizaje')
        with self.assertRaises(PermissionError):papel.recuperar(d,backup,'Psicología')

    def test_envio_fallido_no_descarta_ni_bloquea_otro_informe(self):
        from ui import epp_viva as ui
        d=self.doc();e=self.event(d,'5.1. Competencia curricular','Avance protegido')
        nuevo,areas=papel.aplicar(d,e);state={'p_doc':d}
        with patch.object(ui.st,'session_state',state):
            ui.preparar_cambios('p',nuevo,areas)
            with patch.object(s,'guardar_cambios',side_effect=ConnectionError()):self.assertFalse(ui.guardar('p',True))
            self.assertTrue(state['p_pending'])
            self.assertEqual(state['p_doc']['partes']['Aprendizaje']['contenido']['campos']['5.1. Competencia curricular'],'Avance protegido')
            self.assertTrue(ui.guardar('otro'))
            self.assertTrue(ui.guardar('p',True));self.assertFalse(state['p_pending'])


class PantallaTests(unittest.TestCase):
    def open(self,area='Aprendizaje'):
        app=AppTest.from_file(str(Path(__file__).with_name('fixtures')/'epp_viva_app.py'),default_timeout=30)
        app.session_state['qa_area']=area
        return app.run()

    def test_apoyo_ve_matricula_completa_individual_grupal_y_grupos(self):
        app=self.open();self.assertFalse(app.exception)
        self.assertEqual(app.selectbox[0].options,['Escuela ficticia'])
        self.assertEqual(len(next(c for c in app.selectbox if c.label=='Alumno').options),3)
        next(b for b in app.button if b.label=='Abrir EPP del alumno').click().run()
        self.assertFalse(app.exception);self.assertEqual(app.session_state['qa_spec']['tipo_documento'],'epp')

    def test_especialistas_continuan_mismo_informe_no_crean(self):
        for area in ('Psicología','Comunicación','Trabajo Social'):
            app=self.open(area);self.assertFalse(app.exception)
            self.assertEqual(len(next(c for c in app.selectbox if c.label=='Alumno').options),1)
            next(b for b in app.button if b.label=='Abrir EPP del alumno').click().run()
            self.assertFalse(app.exception)
            self.assertEqual(sum(r[2]=='META' for r in app.session_state['qa_rows']),1)
            spec=app.session_state['qa_spec']
            expected={'Psicología':{'Psicología'},'Comunicación':{'Comunicación','Aprendizaje','Psicología'},'Trabajo Social':{'Trabajo Social','Aprendizaje'}}
            self.assertEqual({c['target'][0] for c in spec['cells'].values() if c['editable']},expected[area])

    def test_abrir_redactor_desde_hoja_nativa_conserva_el_apartado(self):
        app=self.open();next(b for b in app.button if b.label=='Abrir EPP del alumno').click().run()
        spec=app.session_state['qa_spec'];cell=next(c for c in spec['cells'].values() if c.get('apartado_epp'))
        app.session_state['qa_event']={'nonce':'abrir-redactor-qa','documento':spec['documento'],'huella':spec['huella'],'cambios':{},'accion':'redaccion','celda':cell['id']}
        app.run();self.assertFalse(app.exception)
        next(t for t in app.text_area if t.label.startswith('Tus ideas')).set_value('Necesita modelado visual.').run()
        next(b for b in app.button if b.label=='Preparar texto para revisión').click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any('modelado visual' in t.value for t in app.text_area if t.label.startswith('Resumen que se enviará')))


if __name__=='__main__':unittest.main()

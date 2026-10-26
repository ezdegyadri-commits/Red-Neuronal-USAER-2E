"""Regresiones con alumnos ficticios y persistencia simulada."""
from copy import deepcopy
import unittest
from unittest.mock import patch
from tests import test_epp as fixture
from services import epp as s,epp_papel as papel
from services.epp_modelo import vacia
from services.epp_colaborativa import no_requiere

class CompartidosTests(unittest.TestCase):
    setUp=fixture.EPPTests.setUp
    tearDown=fixture.EPPTests.tearDown
    doc=fixture.EPPTests.doc

    def test_comunicacion_edita_solo_tres_campos_compartidos(self):
        d=self.doc();base=vacia('Psicología');nuevo=deepcopy(base)
        nuevo['campos']['4.3. Coordinación motriz fina']='Manipula objetos con apoyo observado.'
        with patch.object(s,'actor',return_value={**fixture.ACTOR,'area':'Comunicación','rol':'COMUNICACION','cuenta':'comunicacion-ficticia'}):
            result=s.guardar_cambios(d,'Psicología',base,nuevo,'')
            self.assertEqual(result['contenido']['campos']['4.3. Coordinación motriz fina'],nuevo['campos']['4.3. Coordinación motriz fina'])
            malicious=deepcopy(result['contenido']);malicious['campos']['3.1. Atención']='Fuera del permiso'
            with self.assertRaises(PermissionError):s.guardar(d,'Psicología',malicious,result['revision'])
            malicious=deepcopy(result['contenido']);malicious['validada']=True
            with self.assertRaises(PermissionError):s.guardar(d,'Psicología',malicious,result['revision'])
            spec=papel.hoja(s.listar()[0])
            cross={tuple(c['target']) for c in spec['cells'].values() if c['editable'] and c['target'][0]!='Comunicación'}
            self.assertEqual(cross,{('Psicología','campos','4.3. Coordinación motriz fina'),('Psicología','campos','4.3. Coordinación motriz gruesa'),('Aprendizaje','campos','4.1. Orientación temporal')})

    def test_ts_general_permitido_otros_campos_no(self):
        d=self.doc();base=vacia('Aprendizaje');v=deepcopy(base);v['generales']['Domicilio']='Dato ficticio'
        with patch.object(s,'actor',return_value={**fixture.ACTOR,'area':'Trabajo Social'}):
            result=s.guardar_cambios(d,'Aprendizaje',base,v,'')
            wrong=deepcopy(result['contenido']);wrong['campos']['5.1. Competencia curricular']='No'
            with self.assertRaises(PermissionError):s.guardar(d,'Aprendizaje',wrong,result['revision'])

    def test_exclusion_reversible_y_pdf_sin_apartado(self):
        from documents.epp import generar_pdf
        import fitz
        d=self.doc();v=vacia('Psicología');campo='3.7. Creatividad (AS)';v['campos'][campo]='TEXTO-QA-CONSERVADO'
        d['partes']['Psicología']={'contenido':no_requiere(v,campo,True),'fecha':'2026-10-26'}
        pdf=fitz.open(stream=generar_pdf(d,fixture.ALUMNO),filetype='pdf');text=''.join(p.get_text() for p in pdf)
        self.assertNotIn(campo,text);self.assertNotIn('TEXTO-QA-CONSERVADO',text)
        restored=no_requiere(d['partes']['Psicología']['contenido'],campo,False)
        self.assertEqual(restored['campos'][campo],'TEXTO-QA-CONSERVADO');self.assertEqual(v['campos'][campo],'TEXTO-QA-CONSERVADO')

    def test_exclusion_compartida_y_conflicto_no_pierden_texto(self):
        d=self.doc();base=vacia('Aprendizaje');a=no_requiere(base,'4.1. Orientación temporal',True)
        b=no_requiere(base,'5.1. Competencia curricular',True)
        s.guardar_cambios(d,'Aprendizaje',base,b,'')
        with patch.object(s,'actor',return_value={**fixture.ACTOR,'area':'Comunicación'}):
            merged=s.guardar_cambios(d,'Aprendizaje',base,a,'')['contenido']
        self.assertEqual(len(merged['no_requeridos']),2)
        c=deepcopy(base);c['campos']['5.1. Competencia curricular']='Otra edición'
        with self.assertRaises(RuntimeError):s.guardar_cambios(d,'Aprendizaje',base,c,'')

    def test_entrevista_precarga_sin_sobrescribir_correccion(self):
        from services.epp_entrada import precargar
        d=self.doc();ts=vacia('Trabajo Social');ts['evaluaciones']=[{'nombre':'Entrevista a padres','texto':'Domicilio: Calle ficticia\nNombre de la madre: Persona ficticia'}]
        d['partes']['Trabajo Social']={'contenido':ts}
        v=precargar(vacia('Aprendizaje'),{'Domicilio':'Dato del padrón'},d)
        self.assertEqual(v['generales']['Domicilio'],'Calle ficticia')
        v['generales_editados']=['Domicilio'];v['generales']['Domicilio']='Corrección revisada'
        self.assertEqual(precargar(v,{},d)['generales']['Domicilio'],'Corrección revisada')

    def test_redactor_minimiza_y_no_llama_ia_al_preparar(self):
        from services.epp_redaccion import preparar,generar
        d=self.doc()
        with patch('ai.planeacion.proponer') as motor:
            text=preparar(d,'Aprendizaje','5.1. Competencia curricular','Alumno de prueba requiere apoyos visuales.')
            self.assertNotIn('Alumno de prueba',text);motor.assert_not_called()
            motor.return_value={'redaccion':'Requiere apoyos visuales.'}
            self.assertEqual(generar(text,'5.1. Competencia curricular'),'Requiere apoyos visuales.')
        with self.assertRaises(ValueError):preparar(d,'Aprendizaje','5.1. Competencia curricular')

    def test_evento_exclusion_no_admite_apartados_ajenos(self):
        d=self.doc();spec=papel.hoja(d)
        c=next(c for c in spec['cells'].values() if c.get('target')==['Aprendizaje','campos','5.1. Competencia curricular'])
        event={'documento':d['id'],'huella':spec['huella'],'cambios':{},'accion':'no_requiere','celda':c['id'],'activar':True}
        result,areas=papel.aplicar(d,event)
        self.assertEqual(areas,{'Aprendizaje'});self.assertTrue(result['partes']['Aprendizaje']['contenido']['no_requeridos'])
        other=next(c for c in spec['cells'].values() if c.get('target')==['Psicología','campos','3.1. Atención'])
        with self.assertRaises(PermissionError):papel.aplicar(d,{**event,'celda':other['id']})

if __name__=='__main__':unittest.main()

import unittest
from unittest.mock import patch
from copy import deepcopy
import json
import pandas as pd
import fitz
from services import epp as s
from services.epp_modelo import AREAS, campos, vacia, clave, reconstruir, pendientes, conclusion_vigente, validar_parte
from services.planeacion_modalidad import filtrar, comprobar, modalidad_documento
from documents.epp import generar_pdf
from ai import epp as ai

ALUMNO={'ID_Alumno':'FICTICIO-A1','Nombre_Completo':'Alumno de prueba','ID_Escuela':'E1','Nombre_Escuela':'Escuela ficticia','CCT_Escuela':'TEST','Grado':'3','Grupo':'A','Tipo_Atencion':'Individual'}
ACTOR={'cuenta':'docente-ficticia','nombre':'Docente de prueba','area':'Aprendizaje','director':False,'rol':'MAESTRO DE APOYO','perfil':None}

class Sheet:
    def __init__(self):self.rows=[]
    def append_rows(self,rows,value_input_option):
        assert value_input_option=='RAW'
        self.rows.extend(deepcopy(rows))
    def frame(self,*args):return pd.DataFrame(self.rows,columns=s.HEADERS)

class EPPTests(unittest.TestCase):
    def setUp(self):
        self.sheet=Sheet()
        s.recientes().clear()
        self.mocks=[patch.object(s,'actor',return_value=ACTOR),
            patch.object(s.planes,'padron_autorizado',return_value=pd.DataFrame([ALUMNO])),
            patch.object(s,'df_sheet',side_effect=self.sheet.frame),patch.object(s,'clear_cache'),
            patch.object(s,'hoja',return_value=self.sheet),patch.object(s,'retry_google',side_effect=lambda f:f())]
        for m in self.mocks:m.start()
    def tearDown(self):
        for m in reversed(self.mocks):m.stop()
        s.recientes().clear()
    def doc(self):return s.crear(ALUMNO['ID_Alumno'],'2026-2027')
    def test_una_epp_por_alumno_ciclo(self):
        d=self.doc()
        self.assertEqual(len(s.listar()),1)
        with self.assertRaises(ValueError):self.doc()
        self.assertEqual(d['id'],clave(ALUMNO['ID_Alumno'],'2026-2027'))
    def test_especialista_no_crea(self):
        for area in ('Psicología','Comunicación','Trabajo Social'):
            with patch.object(s,'actor',return_value={**ACTOR,'area':area,'rol':area}):
                with self.assertRaises(PermissionError):self.doc()
        self.assertEqual(self.sheet.rows,[])
    def test_director_no_crea(self):
        with patch.object(s,'actor',return_value={**ACTOR,'director':True}):
            with self.assertRaises(PermissionError):self.doc()
    def test_rechaza_alumno_fuera_de_asignacion(self):
        with self.assertRaises(PermissionError):s.crear('AJENO','2026-2027')
    def test_edita_solo_area_propia(self):
        d=self.doc()
        with self.assertRaises(PermissionError):s.guardar(d,'Psicología',vacia('Psicología'),'')
        with self.assertRaises(PermissionError):s.guardar(d,'Trabajo Social',vacia('Trabajo Social'),'')
    def test_colaboracion_no_sobrescribe_otra_area(self):
        d=self.doc();a=vacia('Aprendizaje');a['campos']['5.1. Competencia curricular']='Reconoce números con apoyo documentado.'
        s.guardar(d,'Aprendizaje',a,'')
        with patch.object(s,'actor',return_value={**ACTOR,'cuenta':'psicologa-ficticia','area':'Psicología','rol':'PSICOLOGO'}):
            p=vacia('Psicología');p['campos']['3.1. Atención']='Observación registrada.'
            s.guardar(d,'Psicología',p,'')
        result=s.listar()[0]
        self.assertEqual(result['partes']['Aprendizaje']['contenido'],a)
        self.assertEqual(result['partes']['Psicología']['contenido'],p)
    def test_version_obsoleta_no_se_guarda(self):
        d=self.doc();v=vacia('Aprendizaje');s.guardar(d,'Aprendizaje',v,'')
        with self.assertRaises(RuntimeError):s.guardar(d,'Aprendizaje',v,'')
        self.assertEqual(len(self.sheet.rows),2)
    def test_falsificar_coordinadora_no_da_permiso(self):
        d=self.doc();d['partes']['META']['cuenta']='otra'
        with patch.object(s,'actor',return_value={**ACTOR,'cuenta':'otra'}):
            with self.assertRaises(PermissionError):s.guardar(d,'Conclusión',vacia('Conclusión'),'')
    def test_retirar_y_recuperar_conserva_historial(self):
        d=self.doc();s.retirar(d)
        self.assertEqual(s.listar(),[])
        archived=s.listar(True)[0];s.retirar(archived,True)
        self.assertEqual(len(s.listar()),1)
        self.assertEqual(len(self.sheet.rows),3)
    def test_reintento_duplicado_no_duplica_informe(self):
        self.doc();self.sheet.rows.extend(deepcopy(self.sheet.rows))
        self.assertEqual(len(s.listar()),1)
    def test_reintento_antiguo_no_revive_texto_reemplazado(self):
        d=self.doc();v=vacia('Aprendizaje')
        first=s.guardar(d,'Aprendizaje',v,'');old=deepcopy(self.sheet.rows[-1])
        v['campos']['5.1. Competencia curricular']='Hallazgo actualizado.'
        s.guardar(d,'Aprendizaje',v,first['revision'])
        self.sheet.rows.append(old)
        self.assertEqual(s.listar()[0]['partes']['Aprendizaje']['contenido']['campos']['5.1. Competencia curricular'],'Hallazgo actualizado.')
    def test_identidad_del_informe_no_se_puede_cambiar(self):
        d=self.doc();d['id']='otro-informe'
        with self.assertRaises(PermissionError):s.guardar(d,'Aprendizaje',vacia('Aprendizaje'),'')
    def test_informe_corrupto_se_ignora_sin_borrar(self):
        self.doc();self.sheet.rows.append(['AJENO','2026-2027','META','x','','2026','a','a','BORRADOR','no json'])
        self.assertEqual(len(s.listar()),1)
        self.assertEqual(len(self.sheet.rows),2)
    def test_validacion_vacia_requiere_justificacion(self):
        v=vacia('Psicología');v['validada']=True
        with self.assertRaises(ValueError):validar_parte('Psicología',v)
        v['sintesis']='Área no evaluada en este momento; acuerdo del equipo registrado.'
        self.assertTrue(validar_parte('Psicología',v)['validada'])
    def test_necesidades_y_barreras_no_se_generan_desde_condicion(self):
        d=self.doc()
        self.assertGreater(len(pendientes(d)),0)
        self.assertFalse(conclusion_vigente(d))
    def test_cambio_de_area_invalida_conclusion_anterior(self):
        d=self.doc()
        for area in AREAS:d['partes'][area]={'revision':area,'contenido':{'validada':True}}
        d['partes']['Conclusión']={'contenido':{'validada':True,'revisiones_areas':{a:a for a in AREAS}}}
        self.assertTrue(conclusion_vigente(d))
        d['partes']['Psicología']['revision']='nueva'
        self.assertFalse(conclusion_vigente(d))
    def test_pdf_conserva_estructura_y_texto_extenso(self):
        d=self.doc();v=vacia('Aprendizaje');v['campos']['5.1. Competencia curricular']='MARCADOR INICIO. '+('Hallazgo educativo documentado. '*500)+' MARCADOR FINAL.'
        d['partes']['Aprendizaje']={'contenido':v,'fecha':'2026-10-07','autor':'Docente ficticia'}
        pdf=fitz.open(stream=generar_pdf(d,ALUMNO),filetype='pdf')
        text=''.join(p.get_text() for p in pdf)
        for t in ['Información inicial','Funcionamiento intelectual','Conducta adaptativa','Funcionamiento académico','Contextos','Conclusión','Necesidades','Firmas','MARCADOR FINAL']:
            self.assertIn(t.lower(),text.lower())
        self.assertGreater(len(pdf),2)
    def test_pdf_precarga_fecha_y_registro_directo(self):
        d=self.doc();v=vacia('Aprendizaje')
        v['evaluaciones']=[{'id':'ficticio','nombre':'Observación directa ficticia','texto':'Hallazgo','fecha':'2026-10-07','entrada':'DIRECTO'}]
        d['partes']['Aprendizaje']={'contenido':v,'fecha':'2026-10-07','autor':'Docente ficticia'}
        pdf=fitz.open(stream=generar_pdf(d,{**ALUMNO,'Fecha_Nacimiento':'2017-01-01'}),filetype='pdf')
        text=''.join(p.get_text() for p in pdf)
        self.assertIn('2017-01-01',text);self.assertIn('Observación directa ficticia',text)
    def test_ia_rechaza_determinar_nee_en_area(self):
        def call(*args,**kwargs):
            response={'campos':{f:'' for f in campos('Comunicación')},'faltantes':[],'nee':[{}],'bap':[]}
            return kwargs['_validador'](response)
        with patch.object(ai,'proponer',side_effect=call):
            with self.assertRaises(ValueError):ai.generar('EV1: Hallazgos revisados.','Comunicación')
    def test_prompt_incluye_limites_y_manual(self):
        with patch.object(ai,'proponer',return_value={}) as mock:
            ai.generar('EV1: Observación ficticia.','Psicología')
        prompt=mock.call_args.kwargs['_prompt']
        self.assertIn('No interpretes ni califiques pruebas psicométricas',prompt)
        self.assertIn('Anexos XVII y XVIII',prompt)
        self.assertNotIn(ALUMNO['Nombre_Completo'],prompt)
    def test_ia_rechaza_apartado_sin_instrumento_citado(self):
        def call(*args,**kwargs):
            r={'campos':{f:'Resultado sin fuente.' for f in campos('Psicología')},'faltantes':[],'nee':[],'bap':[]}
            return kwargs['_validador'](r)
        with patch.object(ai,'proponer',side_effect=call):
            with self.assertRaises(ValueError):ai.generar('EV1: Hallazgo.','Psicología')
    def test_ia_rechaza_codigo_de_instrumento_ajeno(self):
        def call(*args,**kwargs):
            r={'campos':{f:'EV99: Resultado.' for f in campos('Psicología')},'faltantes':[],'nee':[],'bap':[]}
            return kwargs['_validador'](r)
        with patch.object(ai,'proponer',side_effect=call):
            with self.assertRaises(ValueError):ai.generar('EV1: Hallazgo.','Psicología')

class ModalidadTests(unittest.TestCase):
    def setUp(self):self.frame=pd.DataFrame([ALUMNO,{**ALUMNO,'ID_Alumno':'FICTICIO-A2','Tipo_Atencion':'GRUPAL'},{**ALUMNO,'ID_Alumno':'FICTICIO-A3','Tipo_Atencion':''}])
    def test_particion_exclusiva_y_completa(self):
        i=filtrar(self.frame,'individual');g=filtrar(self.frame,'grupal')
        self.assertEqual(list(i['ID_Alumno']),['FICTICIO-A1'])
        self.assertEqual(len(g),2)
        self.assertEqual(len(i)+len(g),len(self.frame))
    def test_no_permite_individual_en_grupal(self):
        with self.assertRaises(PermissionError):comprobar(self.frame,['FICTICIO-A1'],'grupal')
    def test_no_altera_padron(self):
        previous=self.frame.copy(deep=True);filtrar(self.frame,'grupal')
        pd.testing.assert_frame_equal(previous,self.frame)
    def test_documentos_anteriores_se_clasifican_sin_borrar(self):
        d={'datos':{'Alumnos':[{'ID_Alumno':'FICTICIO-A1'}]},'metadatos':{}}
        self.assertEqual(modalidad_documento(d,self.frame),'individual')
        d['datos']['Alumnos'].append({'ID_Alumno':'FICTICIO-A2'})
        self.assertEqual(modalidad_documento(d,self.frame),'grupal')

if __name__=='__main__':unittest.main()

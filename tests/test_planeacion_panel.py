import unittest
from unittest.mock import patch
from copy import deepcopy
import json
import hashlib
import pandas as pd
from services import planeacion as s
from services.planeacion_modelo import crear_plantilla
from documents.planeacion import generar_pdf


ALUMNO={'ID_Alumno':'A1','Nombre_Completo':'Alumno ficticio','ID_Escuela':'E1','Nombre_Escuela':'Escuela de prueba','CCT_Escuela':'TEST','Grado':'1','Grupo':'B'}
ACTOR={'cuenta':'prueba','nombre':'Autor ficticio','director':False,'area':'Aprendizaje','rol':'APOYO','perfil':None}


def documento(formato='XXIII'):
    d=crear_plantilla(formato,['A1'],[ALUMNO],autor='Autor ficticio',funcion='Aprendizaje')
    d.update(id='test',revision='',cuenta='prueba',observaciones_director='')
    return d


class Sheet:
    def __init__(self):self.rows=[s.HEADERS];self.options=[]
    def get_all_values(self):return self.rows
    def append_rows(self,rows,value_input_option):self.rows.extend(rows);self.options.append(value_input_option)


class PanelTests(unittest.TestCase):
    def setUp(self):
        self.sheet=Sheet();self.heads={}
        import threading
        self.patches=[patch.object(s,'identidad',return_value=ACTOR),patch.object(s,'padron_autorizado',return_value=pd.DataFrame([ALUMNO])),patch.object(s,'_hoja',return_value=self.sheet),patch.object(s,'_control',return_value=(threading.RLock(),self.heads)),patch.object(s,'retry_google',side_effect=lambda f:f()),patch.object(s,'reservar_escritura')]
        for p in self.patches:p.start()
        s._versiones.clear()
        s._recientes().clear()
    def tearDown(self):
        for p in self.patches:p.stop()
        s._versiones.clear()
        s._recientes().clear()
    def test_guardar_recuperar_sin_reescribir(self):
        a=s.guardar(documento());b=deepcopy(a);b['textos']['Evaluación']='Texto';b=s.guardar(b)
        self.assertEqual(len(s.listar(True)),2)
        self.assertEqual(s.listar()[0]['revision'],b['revision'])
        self.assertEqual(self.sheet.options,['RAW','RAW'])
    def test_edicion_obsoleta_no_borra(self):
        a=s.guardar(documento());b=deepcopy(a);b['textos']['Evaluación']='Cambio de otra sesión';s.guardar(b)
        with self.assertRaises(RuntimeError):s.guardar(a)
        self.assertEqual(len(s.listar(True)),2)
    def test_fragmentos_incompletos_no_se_muestran(self):
        d=documento();d['textos']['Evaluación']='x'*50000
        s.guardar(d)
        self.assertEqual(len(s.reconstruir(self.sheet.rows)),1)
        self.assertEqual(s.reconstruir(self.sheet.rows[:-1]),[])
    def test_reintento_duplicado_idempotente(self):
        s.guardar(documento());rows=self.sheet.rows+deepcopy(self.sheet.rows[1:])
        self.assertEqual(len(s.reconstruir(rows)),1)
    def test_alumnos_ajenos_denegados(self):
        d=documento();d['datos']['Alumnos'][0]['ID_Alumno']='A2'
        with self.assertRaises(PermissionError):s.guardar(d)
        self.assertEqual(len(self.sheet.rows),1)
    def test_otro_autor_no_edita(self):
        d=documento();d['cuenta']='otra'
        with self.assertRaises(PermissionError):s.guardar(d)
    def test_trabajo_social_no_se_ofrece_a_apoyo(self):
        with self.assertRaises(PermissionError):s.guardar(documento('XXV'))
    def test_incompleto_no_se_envia(self):
        with self.assertRaises(ValueError):s.guardar(documento(),'ENVIADO')
    def test_no_firma_automatica_en_borrador(self):
        d=documento();d['metadatos']['firma_aprobada_por']='Firma anterior'
        saved=s.guardar(d)
        self.assertEqual(saved['metadatos']['firma_aprobada_por'],'')
    def test_director_devuelve_sin_cambiar_autor(self):
        saved=s.guardar(documento())
        with patch.object(s,'identidad',return_value={**ACTOR,'cuenta':'director','nombre':'Director ficticio','director':True}):
            reviewed=s.guardar(saved,'CON_OBSERVACIONES','Precisar evidencia observable')
        self.assertEqual(reviewed['cuenta'],'prueba')
        self.assertEqual(reviewed['observaciones_director'],'Precisar evidencia observable')
        self.assertEqual(len(s.listar(True)),2)
    def test_resumen_retira_identificadores_conocidos(self):
        d=documento()
        result=s.resumen_previo(d,[{'referencia':'E1','alcance':'individual','texto':'Alumno ficticio A1 TEST correo@ejemplo.com identifica letras.'}])
        self.assertNotIn('Alumno ficticio',result)
        self.assertNotIn('correo@ejemplo.com',result)
        self.assertIn('identifica letras',result)
    def test_pdf_tres_anexos_y_texto_extenso(self):
        import fitz
        for fmt in ('XXI','XXIII','XXV'):
            d=documento(fmt);d['textos']['Observaciones']='Texto final de control. '+('Contenido amplio. '*1600)
            data=generar_pdf(d)
            pdf=fitz.open(stream=data,filetype='pdf');texto=''.join(p.get_text() for p in pdf)
            self.assertIn('Texto final de control',texto);self.assertIn('Escuela de prueba',texto)
            self.assertGreater(len(pdf),1)


if __name__=='__main__':unittest.main()

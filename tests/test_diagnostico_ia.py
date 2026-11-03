import unittest
from unittest.mock import patch
from services import diagnostico_ia as q
class PruebaSeguraIATests(unittest.TestCase):
 def test_solo_caso_ficticio_y_rol_institucional(self):
  value={k:'Contenido educativo ficticio suficiente para verificar la estructura.' for k in q.CAMPOS}
  def transport(prompt,schema,validate,config,**kw):
   self.assertIn('Especialista Técnico-Pedagógico',prompt)
   self.assertIn('COMPLETAMENTE FICTICIOS',prompt)
   self.assertNotIn('abril.chable',prompt)
   return validate(value)
  with patch('ai.documento_json.generar',side_effect=transport):self.assertEqual(q.generar({'gemini':'clave-ficticia'}),value)
 def test_rechaza_respuesta_incompleta(self):
  with self.assertRaises(ValueError):q.validar({'objetivo':'Sin desarrollo'})
 def test_no_ofrece_sonda_a_especialistas(self):
  from ui import diagnostico_ia as u
  with patch('services.planeacion.identidad',return_value={'director':False}),patch.object(u.st,'error') as error,patch.object(u.st,'button') as button:
   u.pagina();error.assert_called_once();button.assert_not_called()

class ConfiguracionCompartidaIATests(unittest.TestCase):
 def test_lee_claves_de_entorno_sin_ocultarlas_por_recursion(self):
  import os,streamlit as st
  from ai import epp_contextual,planeacion
  with patch.dict(os.environ,{'GEMINI_API_KEY':'clave-google-ficticia','OPENAI_API_KEY':'clave-openai-ficticia'}),patch.object(st,'session_state',{}),patch.object(planeacion,'modelo_configurado',return_value='modelo-ficticio'):
   for cfg in (epp_contextual.configuracion(),planeacion.configuracion_trabajo()):
    self.assertEqual(cfg['gemini'],'clave-google-ficticia')
    self.assertEqual(cfg['openai'],'clave-openai-ficticia')
    self.assertEqual(cfg['modelos'],['modelo-ficticio'])
 def test_conserva_alternativa_de_sesion_sin_claves_de_entorno(self):
  import streamlit as st
  from ai import epp_contextual,planeacion
  with patch.object(epp_contextual,'secreto',return_value=''),patch.object(st,'session_state',{'relatoria_openai_key':'clave-de-sesion-ficticia'}),patch.object(planeacion,'modelo_configurado',return_value='modelo-ficticio'):
   self.assertEqual(epp_contextual.configuracion()['openai'],'clave-de-sesion-ficticia')

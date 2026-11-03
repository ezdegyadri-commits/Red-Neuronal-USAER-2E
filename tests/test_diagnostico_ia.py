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

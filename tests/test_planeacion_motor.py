import json
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch, Mock
from ai import planeacion as motor

class MotorTests(unittest.TestCase):
    def llamada(self,respuesta=None,error=None):
        client=Mock()
        client.models.generate_content.return_value=SimpleNamespace(text=respuesta)
        if error:client.models.generate_content.side_effect=error
        types=SimpleNamespace(HttpOptions=lambda **kw:kw,HttpRetryOptions=lambda **kw:kw)
        genai=SimpleNamespace(Client=Mock(return_value=client),types=types)
        google=SimpleNamespace(genai=genai)
        state={}
        with patch.dict(sys.modules,{'google':google,'google.genai':genai,'google.genai.types':types}),patch.object(motor.st,'secrets',{'GEMINI_API_KEY':'clave-ficticia'}),patch.object(motor.st,'session_state',state):
            try:result=motor.proponer('Resumen educativo ficticio','XXIII','Aprendizaje')
            except RuntimeError as exc:result=exc
        return result,state,client
    def test_acepta_json_con_delimitadores_sin_reintentos(self):
        result,state,client=self.llamada('```json\n'+json.dumps({'observaciones':'Falta evidencia','faltantes':['Confirmar apoyos'],'propuestas':[]})+'\n```')
        self.assertIsInstance(result,dict)
        self.assertEqual(client.models.generate_content.call_count,1)
        self.assertEqual(client.models.generate_content.call_args.kwargs['config']['max_output_tokens'],4000)
    def test_429_diagnostico_sin_texto_privado(self):
        class ErrorCuota(Exception):code=429
        result,state,_=self.llamada(error=ErrorCuota('MENSAJE PRIVADO DEL PROVEEDOR'))
        self.assertIsInstance(result,RuntimeError)
        self.assertEqual(state['planeacion_ia_diagnostico']['codigo'],429)
        self.assertNotIn('PRIVADO',str(result)+str(state))
    def test_respuesta_no_utilizable_preserva_error_breve(self):
        result,state,_=self.llamada('no es JSON')
        self.assertIsInstance(result,RuntimeError)
        self.assertIn('borrador se conserva',str(result))

if __name__=='__main__':unittest.main()

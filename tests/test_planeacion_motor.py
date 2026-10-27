import json
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch, Mock
from ai import planeacion as motor

class MotorTests(unittest.TestCase):
    def test_migra_configuracion_heredada_sin_cambiar_clave(self):
        secretos={'GEMINI_API_KEY':'clave-ficticia','PLANEACION_GEMINI_MODEL':'models/gemini-2.5-flash'}
        with patch.object(motor.st,'secrets',secretos):
            self.assertEqual(motor.modelo_configurado(),'gemini-3.5-flash-lite')
            self.assertTrue(motor.configuracion_modelo()['migrado'])
        self.assertEqual(secretos['GEMINI_API_KEY'],'clave-ficticia')
    def test_default_vigente_y_modelo_explicito_preservado(self):
        with patch.object(motor.st,'secrets',{}),patch.object(motor,'MODEL','gemini-3.5-flash-lite'):
            self.assertEqual(motor.modelo_configurado(),'gemini-3.5-flash-lite')
        with patch.object(motor.st,'secrets',{'PLANEACION_GEMINI_MODEL':'gemini-3.6-flash'}):
            self.assertEqual(motor.modelo_configurado(),'gemini-3.6-flash')
            self.assertFalse(motor.configuracion_modelo()['migrado'])
    def llamada(self,respuesta=None,error=None):
        client=Mock()
        client.models.generate_content.return_value=SimpleNamespace(text=respuesta)
        if error:client.models.generate_content.side_effect=error
        types=SimpleNamespace(HttpOptions=lambda **kw:kw,HttpRetryOptions=lambda **kw:kw)
        genai=SimpleNamespace(Client=Mock(return_value=client),types=types)
        google=SimpleNamespace(genai=genai)
        state={}
        with patch.dict(sys.modules,{'google':google,'google.genai':genai,'google.genai.types':types}),patch.object(motor.st,'secrets',{'GEMINI_API_KEY':'clave-ficticia'}),patch.object(motor.st,'session_state',state),patch.object(motor.time,'sleep'):
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
        self.assertEqual(state['planeacion_ia_diagnostico']['tipo'],'RespuestaNoVerificable')
    def test_recupera_503_con_un_solo_reintento(self):
        class Saturado(Exception):code=503
        respuesta=SimpleNamespace(text=json.dumps({'observaciones':'Confirmar evidencia','faltantes':['¿Qué apoyo funciona?'],'propuestas':[]}))
        result,state,client=self.llamada(error=[Saturado(),respuesta])
        self.assertIsInstance(result,dict)
        self.assertEqual(client.models.generate_content.call_count,2)
        self.assertNotIn('planeacion_ia_diagnostico',state)
        self.assertIn('response_schema',client.models.generate_content.call_args.kwargs['config'])
    def test_no_reintenta_permisos_o_saldo(self):
        for codigo in (400,401,402,403,404):
            with self.subTest(codigo=codigo):
                error=Exception('PRIVADO');error.code=codigo
                result,state,client=self.llamada(error=error)
                self.assertIsInstance(result,RuntimeError)
                self.assertEqual(client.models.generate_content.call_count,1)
    def test_agotar_429_limita_intentos_y_activa_pausa(self):
        error=Exception();error.code=429
        _,state,client=self.llamada(error=error)
        self.assertEqual(client.models.generate_content.call_count,2)
        self.assertGreater(state['planeacion_ia_reintentar_desde'],motor.time.monotonic())
        with patch.object(motor.st,'session_state',state):
            with self.assertRaisesRegex(RuntimeError,'30 segundos'):
                motor.proponer('Resumen educativo ficticio','XXIII','Aprendizaje')
    def test_modelo_secrets_tiene_prioridad(self):
        with patch.object(motor.st,'secrets',{'PLANEACION_GEMINI_MODEL':'gemini-3.1-flash-lite'}):
            self.assertEqual(motor.modelo_configurado(),'gemini-3.1-flash-lite')

    def test_chatgpt_openai_directo(self):
        json_resp = json.dumps({'observaciones':'Propuesta con OpenAI','faltantes':[],'propuestas':[]})
        state = {'planeacion_motor': 'ChatGPT (OpenAI)'}
        with patch.object(motor.st, 'session_state', state), \
             patch.object(motor, '_proponer_openai', return_value=json_resp) as mock_oa:
            res = motor.proponer('Resumen educativo', 'XXIII', 'Aprendizaje')
            self.assertIsInstance(res, dict)
            self.assertEqual(res['observaciones'], 'Propuesta con OpenAI')
            mock_oa.assert_called_once()

    def test_gemini_pro_preferido(self):
        respuesta = json.dumps({'observaciones':'Propuesta Gemini Pro','faltantes':[],'propuestas':[]})
        client = Mock()
        client.models.generate_content.return_value = SimpleNamespace(text=respuesta)
        types = SimpleNamespace(HttpOptions=lambda **kw:kw, HttpRetryOptions=lambda **kw:kw)
        genai = SimpleNamespace(Client=Mock(return_value=client), types=types)
        google = SimpleNamespace(genai=genai)
        state = {'planeacion_modelo_preferido': 'gemini-2.5-pro'}
        with patch.dict(sys.modules, {'google': google, 'google.genai': genai, 'google.genai.types': types}), \
             patch.object(motor.st, 'secrets', {'GEMINI_API_KEY': 'clave-test'}), \
             patch.object(motor.st, 'session_state', state):
            res = motor.proponer('Resumen ficticio', 'XXIII', 'Aprendizaje')
            self.assertIsInstance(res, dict)
            self.assertEqual(client.models.generate_content.call_args.kwargs['model'], 'gemini-2.5-pro')

    def test_blindaje_pedagogico_prompt(self):
        from ai.planeacion_prompt import INSTRUCCIONES
        self.assertIn("ORIGEN DUAL OBLIGATORIO DE LAS NEE", INSTRUCCIONES)
        self.assertIn("<evaluacion_psicopedagogica>", INSTRUCCIONES)
        self.assertIn("<contexto_documentado>", INSTRUCCIONES)
        self.assertIn("<ediciones_manuales_docente>", INSTRUCCIONES)
        self.assertIn("FILTRO DE NIVEL REAL DE DESARROLLO", INSTRUCCIONES)
        self.assertIn("TRAZABILIDAD Y SUSTENTO DOCUMENTAL", INSTRUCCIONES)
        self.assertIn("SUBORDINACIÓN ESTRICTA A EDICIONES MANUALES DEL DOCENTE", INSTRUCCIONES)
        self.assertIn("MARCO DUA Y ACTIVIDADES DIVERSIFICADAS", INSTRUCCIONES)

    def test_payload_xml_estructurado_y_subordinacion(self):
        from services.planeacion_generacion import construir_payload_estructurado_xml
        doc = {
            'datos': {
                'Alumnos': [
                    {'ID_Alumno': 'ALU-100', 'Grado': '3°', 'Condicion': 'Discapacidad Intelectual'}
                ]
            },
            'metadatos': {
                'fuentes': [
                    {'tipo': 'EPP', 'referencia': 'E1', 'alumno': 'ALU-100', 'fecha': '2026-09-15', 'texto': 'Nivel presilábico, conteo hasta 5 con material concreto.'},
                    {'tipo': 'SEGUIMIENTO', 'referencia': 'E2', 'alumno': 'ALU-100', 'fecha': '2026-10-02', 'texto': 'NEE detectada: Requiere andamiaje uno a uno en conteo.'}
                ],
                'intervenciones_nee': [
                    {'alumno': 'ALU-100', 'campos': {'NEE': 'Consolidar correspondencia grafofonética', 'Apoyos': 'Tarjetas ARASAAC'}}
                ],
                'curriculo': {'adaptaciones': {}}
            },
            'tablas': {
                'aprendizajes': [
                    {'Necesidades educativas específicas': 'Conciencia fonológica', 'Aprendizaje y/u objetivo': 'Identificar sonido inicial', 'Descriptor de logro': 'Señala tarjeta con sonido /m/'}
                ],
                'barreras': [],
                'necesidades': []
            }
        }
        aliases = {'Alumno 1': 'ALU-100'}
        reversa = {'ALU-100': 'Alumno 1'}
        xml = construir_payload_estructurado_xml(doc, aliases, reversa)
        
        self.assertIn('<evaluacion_psicopedagogica>', xml)
        self.assertIn('Nivel presilábico, conteo hasta 5', xml)
        self.assertIn('<contexto_documentado>', xml)
        self.assertIn('NEE detectada: Requiere andamiaje', xml)
        self.assertIn('<ediciones_manuales_docente>', xml)
        self.assertIn('VERDAD ABSOLUTA Y PRIORIDAD TOTAL', xml)
        self.assertIn('Conciencia fonológica', xml)
        self.assertIn('Tarjetas ARASAAC', xml)

if __name__=='__main__':unittest.main()


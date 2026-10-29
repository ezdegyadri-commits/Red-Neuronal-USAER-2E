import json,unittest
from types import SimpleNamespace as NS
from unittest.mock import Mock,patch
from ai import modelos_gemini as motor


class Retirado(Exception):code=404


class ModelosTests(unittest.TestCase):
    def setUp(self):
        motor._catalogos.clear();motor._resueltos.clear()
        self.cli=Mock();self.cli.models.list.return_value=[NS(name='models/gemini-3.5-flash',supported_actions=['generateContent']),
            NS(name='models/gemini-3.5-pro',supported_actions=['generateContent']),
            NS(name='models/gemini-3.5-pro-image',supported_actions=['generateContent']),
            NS(name='models/gemini-embedding-001',supported_actions=['embedContent'])]

    def llamar(self,**kw):return motor.generar(self.cli,model='gemini-2.5-pro',api_key='ficticia',contents='contexto ficticio',**kw)

    def test_modelo_actual_no_consulta_catalogo(self):
        self.cli.models.generate_content.return_value='ok'
        self.assertEqual(self.llamar(),'ok');self.cli.models.list.assert_not_called()

    def test_404_recupera_modelo_pro_real_y_cachea_sin_guardar_clave(self):
        self.cli.models.generate_content.side_effect=[Retirado(),'ok','ok2']
        self.assertEqual(self.llamar(),'ok');self.assertEqual(self.llamar(),'ok2')
        models=[c.kwargs['model'] for c in self.cli.models.generate_content.call_args_list]
        self.assertEqual(models,['gemini-2.5-pro','gemini-3.5-pro','gemini-3.5-pro'])
        self.assertNotIn('ficticia',str(motor._catalogos)+str(motor._resueltos))
        self.cli.models.list.assert_called_once_with(config={'page_size':100})

    def test_todos_los_perfiles_recuperan_igual_con_una_consulta(self):
        for area in ('Aprendizaje','Comunicación','Psicología','Trabajo Social'):
            self.cli.models.generate_content.side_effect=[Retirado(),'ok'] if area=='Aprendizaje' else ['ok']
            self.assertEqual(motor.generar(self.cli,model='gemini-2.5-pro',api_key='ficticia',contents=area),'ok')
        self.cli.models.list.assert_called_once()

    def test_catalogo_aislado_por_conexion(self):
        self.cli.models.generate_content.side_effect=[Retirado(),'ok',Retirado(),'ok']
        self.llamar();motor.generar(self.cli,model='gemini-2.5-pro',api_key='otra-ficticia',contents='qa')
        self.assertEqual(self.cli.models.list.call_count,2)

    def test_no_reintenta_permisos_cuota_saldo_o_peticion_invalida(self):
        for code in (400,401,402,403,429,503):
            with self.subTest(code=code):
                error=Exception();error.code=code;self.cli.reset_mock();self.cli.models.generate_content.side_effect=error
                with self.assertRaises(Exception):self.llamar()
                self.cli.models.list.assert_not_called();self.assertEqual(self.cli.models.generate_content.call_count,1)

    def test_catalogo_sin_generacion_no_inventa_modelo(self):
        self.cli.models.generate_content.side_effect=Retirado();self.cli.models.list.return_value=[]
        with self.assertRaises(Retirado):self.llamar()
        self.assertEqual(self.cli.models.generate_content.call_count,1)

    def test_listado_falla_no_muestra_detalle_privado(self):
        self.cli.models.generate_content.side_effect=Retirado('modelo retirado');self.cli.models.list.side_effect=RuntimeError('secreto')
        with self.assertRaises(Retirado):self.llamar()
        self.assertEqual(self.cli.models.generate_content.call_count,1)

    def test_cache_modelo_retirado_de_nuevo_actualiza_catalogo(self):
        self.cli.models.generate_content.side_effect=[Retirado(),'ok',Retirado(),'ok2']
        self.llamar()
        self.cli.models.list.return_value=[NS(name='gemini-3.6-pro',supported_actions=['generateContent'])]
        self.assertEqual(self.llamar(),'ok2');self.assertEqual(self.cli.models.list.call_count,2)

    def test_alternativa_no_hereda_parametros_exclusivos_del_modelo_retirado(self):
        self.cli.models.generate_content.side_effect=[Retirado(),'ok','ok2']
        config={'response_mime_type':'application/json','thinking_config':{'thinking_budget':0}}
        self.llamar(config=config);self.llamar(config=config)
        self.assertNotIn('thinking_config',self.cli.models.generate_content.call_args.kwargs['config'])
        self.assertIn('thinking_config',config)

    def test_recarga_real_conserva_pool_slots_y_contexto(self):
        import importlib
        from ai import documento_json,epp_contextual,planeacion
        for module,attrs in ((documento_json,('_pool','_slots')),(epp_contextual,('_pool','_slots')),(planeacion,('_conexion','_progreso'))):
            previous={k:getattr(module,k) for k in attrs}
            importlib.reload(module)
            for k,v in previous.items():self.assertIs(getattr(module,k),v)

    def test_transporte_json_recupera_y_valida_salida(self):
        from ai import documento_json
        self.cli.models.generate_content.side_effect=[Retirado(),NS(text='{"actividades": ["actividad ficticia"]}')]
        with patch('google.genai.Client',return_value=self.cli):
            result=documento_json.generar('qa',{'type':'object'},lambda d:d,{'gemini':'ficticia','modelos':['gemini-2.5-pro']})
        self.assertEqual(result['actividades'],['actividad ficticia'])


if __name__=='__main__':unittest.main()

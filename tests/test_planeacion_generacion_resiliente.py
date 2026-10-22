from unittest import TestCase
from unittest.mock import patch,Mock
from copy import deepcopy
from ai import planeacion as motor,planeacion_completa as completa
from ui import planeacion_progreso as ui


class ResilienciaTests(TestCase):
    def test_error_desconocido_no_expone_texto_del_proveedor(self):
        self.assertNotIn('PRIVADO',ui.mensaje_error(RuntimeError('TOKEN PRIVADO')))
        self.assertIn('límite de IA',ui.mensaje_error(RuntimeError('Se alcanzó el límite de IA. Conservamos tu borrador; vuelve a intentar más tarde.')))

    def llamada(self,errores,motivo='SalidaCortada',tipo='RespuestaNoVerificable'):
        state={};calls=[]
        def proponer(*a,**kw):
            calls.append(kw)
            state['planeacion_ia_diagnostico']={'tipo':tipo,'motivo':motivo}
            valor=errores[min(len(calls)-1,len(errores)-1)]
            if isinstance(valor,Exception):raise valor
            return valor
        with patch.object(motor.st,'session_state',state),patch.object(motor,'proponer',side_effect=proponer):
            resultado=completa.generar_completa('Resumen revisado','XXIII','Aprendizaje',{'fuentes':[]},{'sesiones':12},['Alumno 1'],{'E1':['Alumno 1']})
        return resultado,calls

    def test_corrige_una_vez_sin_enviar_salida_o_error_privado(self):
        antes=deepcopy(completa.SCHEMA)
        resultado,calls=self.llamada([RuntimeError('RESPUESTA PRIVADA'),{'unidades':[]}])
        self.assertEqual(len(calls),2);self.assertEqual(resultado,{'unidades':[]})
        self.assertEqual(calls[1]['_schema']['properties']['unidades']['maxItems'],3)
        self.assertNotIn('RESPUESTA PRIVADA',calls[1]['_prompt'])
        self.assertEqual(completa.SCHEMA,antes)
        self.assertIs(calls[0]['_validador'],calls[1]['_validador'])

    def test_no_bucle_ni_reintento_de_credenciales_cuota_o_saldo(self):
        for tipo in ('ErrorCuota','ClaveNoConfigurada','PermissionError'):
            with self.assertRaises(RuntimeError):self.llamada([RuntimeError('Fallo')],tipo=tipo)
        with patch.object(motor,'proponer',side_effect=RuntimeError('Fallo')) as m,patch.object(motor.st,'session_state',{'planeacion_ia_diagnostico':{'tipo':'RespuestaNoVerificable','motivo':'CamposIncompletos'}}):
            with self.assertRaises(RuntimeError):completa.generar_completa('Resumen','XXIII','Aprendizaje',{}, {'sesiones':12},['Alumno 1'],{})
            self.assertEqual(m.call_count,2)

    def test_barra_solo_hitos_monotona_y_no_anuncia_exito_ante_error(self):
        solicitud={'resumen':'Revisado','contexto':{},'ajustes':{},'aliases':{},'evidencias':{}}
        doc={'formato':'XXIII','datos':{'Función':'Aprendizaje'}}
        barra=Mock()
        def generar(*a):
            for etapa in ('solicitando','validando','corrigiendo','solicitando','validando'):motor.notificar_progreso(etapa)
            return {'unidades':[]}
        with patch.object(ui.st,'progress',return_value=barra),patch.object(ui.st,'caption'),patch.object(completa,'generar_completa',side_effect=generar):ui.generar(solicitud,doc)
        valores=[c.args[0] for c in barra.progress.call_args_list]
        self.assertEqual(valores,sorted(valores));self.assertEqual(valores[-1],100)
        barra.reset_mock()
        with patch.object(ui.st,'progress',return_value=barra),patch.object(ui.st,'caption'),patch.object(completa,'generar_completa',side_effect=RuntimeError('Fallo')):
            with self.assertRaises(RuntimeError):ui.generar(solicitud,doc)
        barra.empty.assert_called_once();self.assertFalse(any(c.args[0]==100 for c in barra.progress.call_args_list))

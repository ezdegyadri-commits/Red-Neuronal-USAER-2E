"""Activación sin reemplazar ejecutores, bloqueos o datos de sesiones."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from ui import memoria_actualizacion as ui


class ActualizacionTests(unittest.TestCase):
    def test_actualiza_solo_una_vez_y_conserva_contextvars_y_pool(self):
        old=ui._aplicada
        self.addCleanup(setattr,ui,'_aplicada',old)
        ui._aplicada=None
        pool=object();conexion=object();outbox=object()
        prompt=SimpleNamespace(INSTRUCCIONES='nuevo',solicitud=lambda:None,validar_respuesta=lambda:None)
        cliente=SimpleNamespace(INSTRUCCIONES='viejo',_conexion=conexion,proponer=lambda:None)
        modules={n:SimpleNamespace() for n in ui._MODULOS}
        modules.update({'ai.planeacion_prompt':prompt,'ai.planeacion':cliente,
            'ai.documento_json':SimpleNamespace(_pool=pool),
            'services.planeacion_estabilidad':SimpleNamespace(intentos=outbox),
            'ui.planeacion':SimpleNamespace(proponer='viejo'), 'ai.epp':SimpleNamespace(proponer='viejo')})
        with patch.dict(ui.sys.modules,modules),patch.object(ui.importlib,'reload',side_effect=lambda m:m) as reload:
            ui.preparar_entrada('qa-v1');cantidad=reload.call_count
            self.assertEqual(cantidad,len(ui._MODULOS))
            ui.preparar_entrada('qa-v1');self.assertEqual(reload.call_count,cantidad)
            self.assertEqual(cliente.INSTRUCCIONES,'nuevo')
            self.assertIs(modules['ui.planeacion'].proponer,cliente.proponer)
            self.assertIs(modules['ai.epp'].proponer,cliente.proponer)
            self.assertIs(cliente._conexion,conexion)
            self.assertIs(modules['ai.documento_json']._pool,pool)
            self.assertIs(modules['services.planeacion_estabilidad'].intentos,outbox)
            self.assertNotIn('services.planeacion_estabilidad',ui._MODULOS)

    def test_fallo_no_marca_actualizacion_completa(self):
        old=ui._aplicada;self.addCleanup(setattr,ui,'_aplicada',old);ui._aplicada=None
        with patch.dict(ui.sys.modules,{'services.planeacion':SimpleNamespace()}),patch.object(ui.importlib,'reload',side_effect=RuntimeError('qa')):
            with self.assertRaises(RuntimeError):ui.preparar_entrada('qa-v1')
        self.assertIsNone(ui._aplicada)


if __name__=='__main__':unittest.main()

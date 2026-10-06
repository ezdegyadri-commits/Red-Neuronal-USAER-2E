from copy import deepcopy
from unittest.mock import patch,Mock
import unittest
from services import novedades_supervision as s

def documento(ident='demo',version='2026-10-06T10:00:00Z',sync='2026-10-06T11:00:00Z'):
    return {'ID_Documento':ident,'Nombre':'Plan de zona ficticio','Seccion':'Documentos de zona','Modificado_En':version,'Sincronizado_En':sync,'Enlace':'https://drive.google.com/file/d/demo/view','Extracto':'Orientación ficticia','Estado':'VIGENTE'}

class NovedadesTests(unittest.TestCase):
    def test_autorizacion_antes_de_lectura(self):
        with patch.object(s,'identidad',return_value={'director':False}),patch.object(s,'_leer') as leer:
            with self.assertRaises(PermissionError):s.cargar()
            leer.assert_not_called()
    def test_actualizado_sin_duplicados(self):
        old=documento();nuevo={**documento(sync='2026-10-06T12:00:00Z'),'Nombre':'Versión actualizada'}
        docs,_=s.vigentes([nuevo,old]);self.assertEqual(len(docs),1);self.assertEqual(docs[0]['Nombre'],'Versión actualizada')
    def test_fuente_no_es_documento_y_retirado_no_aparece(self):
        docs,fuente=s.vigentes([documento('__SOURCE__'),{**documento(),'Estado':'RETIRADO'}]);self.assertFalse(docs);self.assertTrue(fuente)
    def test_urls_no_transmiten_fuera_de_google(self):
        for url in ['javascript:alert(1)','http://drive.google.com/a','https://docs.google.com.evil.test/a','https://user:pass@drive.google.com/a']:
            self.assertFalse(s.enlace_seguro(url))
    def test_marcas_por_cuenta_y_version(self):
        data=[documento()];revisiones=[{'Cuenta':'otro','Documento':'demo','Modificado_En':data[0]['Modificado_En']}]
        with patch.object(s,'identidad',return_value={'director':True,'cuenta':'director-ficticio'}),patch.object(s,'_leer',side_effect=[data,revisiones]):
            docs,_=s.cargar();self.assertTrue(docs[0]['Nuevo'])
    def test_filtros_no_inventan_eventos(self):
        d={**documento(),'Nuevo':True};self.assertEqual(s.filtrar([d],actividades=True),[d]);self.assertFalse(s.filtrar([d],'alumno ajeno'))
    def test_version_ajena_no_se_marca(self):
        with patch.object(s,'autorizar',return_value={'cuenta':'ficticio'}),patch.object(s,'cargar',return_value=([documento()],{})),patch.object(s,'ensure_headers') as escribir:
            with self.assertRaises(ValueError):s.marcar_revisado('demo','otra-version')
            escribir.assert_not_called()
    def test_fecha_mexico_y_error(self):
        self.assertEqual(s.fecha_local('2026-10-06T17:00:00Z'),'06/10/2026 11:00');self.assertEqual(s.fecha_local('desconocida'),'Sin fecha informada')

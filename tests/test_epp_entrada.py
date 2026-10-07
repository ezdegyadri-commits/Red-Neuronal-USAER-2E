import unittest
from datetime import date
from services.epp_modelo import vacia, validar_parte
from services.epp_entrada import datos_registrados, precargar, entrada_directa, huella_instrumentos

class EntradasTests(unittest.TestCase):
    def test_precarga_solo_registros_no_domicilio_escolar(self):
        result=precargar(vacia('Aprendizaje'),{'Edad_1_Septiembre':9,'Direccion_Escuela':'Dirección escolar'})
        self.assertIn('referencia del padrón',result['generales']['Edad'])
        self.assertEqual(result['generales']['Domicilio'],'')
        self.assertEqual(result['generales']['Nombre de la madre'],'')
    def test_no_infiere_fecha_desde_curp(self):
        self.assertNotIn('Fecha de nacimiento',datos_registrados({'CURP':'XXXX170101HYNNNN01'}))
    def test_fecha_registrada_edad_calculada(self):
        result=datos_registrados({'Fecha_Nacimiento':'2017-01-01'})
        self.assertIn(str(date.today().year-2017)+' años',result['Edad'])
    def test_fecha_invalida_no_edad_inventada(self):
        self.assertNotIn('Edad',datos_registrados({'Fecha_Nacimiento':'2017-02-31'}))
    def test_no_sobrescribe_correccion(self):
        v=vacia('Aprendizaje');v['generales']['Domicilio']='Corrección'
        self.assertEqual(precargar(v,{'Domicilio':'Otro'})['generales']['Domicilio'],'Corrección')
    def test_vacio_manual_se_conserva(self):
        v=vacia('Aprendizaje');v['generales_editados']=['Edad']
        self.assertEqual(precargar(v,{'Edad_1_Septiembre':9})['generales']['Edad'],'')
    def test_no_mutacion_y_no_datos_nan(self):
        v=vacia('Aprendizaje');precargar(v,{'Nombre_Madre':'Persona'})
        self.assertEqual(v['generales']['Nombre de la madre'],'')
        self.assertEqual(datos_registrados({'Domicilio':float('nan')}),{})
    def test_entrada_directa_identidad_y_deduplicacion(self):
        d={'Instrumento o técnica aplicada':'Observación','Fecha de aplicación (AAAA-MM-DD)':'2026-10-07',
           'Resultados y observaciones documentadas':'Reconoce letras con apoyo.'}
        e=entrada_directa(d);self.assertEqual(e,entrada_directa(d));self.assertEqual(e['entrada'],'DIRECTO')
        v=vacia('Aprendizaje');v['evaluaciones']=[e];self.assertEqual(validar_parte('Aprendizaje',v),v)
    def test_directo_requiere_resultados_y_fecha(self):
        for d in ({},{'Instrumento o técnica aplicada':'Prueba','Resultados y observaciones documentadas':'Resultado','Fecha de aplicación (AAAA-MM-DD)':'2026-02-30'}):
            with self.assertRaises(ValueError):entrada_directa(d)
    def test_cambio_de_resultados_invalida_resumen(self):
        v=vacia('Psicología');v['evaluaciones']=[{'id':'1','nombre':'Observación','texto':'Resultado'}]
        h=huella_instrumentos({},'Psicología',v);v['evaluaciones'][0]['texto']='Otro resultado'
        self.assertNotEqual(h,huella_instrumentos({},'Psicología',v))
    def test_cambio_equipo_invalida_conclusion(self):
        doc={'partes':{'Psicología':{'revision':'1'}}}
        h=huella_instrumentos(doc,'Conclusión',{});doc['partes']['Psicología']['revision']='2'
        self.assertNotEqual(h,huella_instrumentos(doc,'Conclusión',{}))

if __name__=='__main__':unittest.main()

import unittest
from copy import deepcopy
from services.horarios import actualizar_bloques_borrador, DIAS, detectar_choques
import pandas as pd

class EdicionHorarioTests(unittest.TestCase):
    def setUp(self):
        self.bloque={'Dia':'Lunes','Inicio':'07:00','Fin':'08:00','Actividad':'Lectura','Grupo':'5 A','Maestra':'Docente ficticia'}
        self.clave='Lunes|07:00|08:00'
        self.borrador={self.clave:deepcopy(self.bloque)}
    def actualizar(self,candidato,dias=None,**kw):
        return actualizar_bloques_borrador(self.borrador,self.clave,candidato,dias or ['Lunes'],'07:00','13:00',**kw)
    def test_editar_horas_y_repetir_cinco_dias(self):
        result=self.actualizar({**self.bloque,'Fin':'07:45'},DIAS)
        self.assertEqual(len(result),5)
        self.assertTrue(all(r['Fin']=='07:45' for r in result.values()))
        self.assertEqual(self.borrador[self.clave]['Fin'],'08:00')
    def test_repeticion_no_sobrescribe_otras_actividades(self):
        self.borrador['Martes|07:00|08:00']={**self.bloque,'Dia':'Martes','Actividad':'Otra actividad'}
        with self.assertRaises(ValueError):self.actualizar(self.bloque,DIAS)
        self.assertEqual(self.borrador['Martes|07:00|08:00']['Actividad'],'Otra actividad')
        result=self.actualizar(self.bloque,DIAS,reemplazar=True)
        self.assertEqual(result['Martes|07:00|08:00']['Actividad'],'Lectura')
    def test_tiempos_invalidos_descanso_y_solapes_sin_cambios_parciales(self):
        for change in ({'Inicio':'06:50'},{'Fin':'07:00'},{'Fin':'14:00'},{'Fin':'xx'}):
            with self.assertRaises(ValueError):self.actualizar({**self.bloque,**change})
        with self.assertRaises(ValueError):self.actualizar(self.bloque,descanso_inicio='07:30',descanso_fin='08:00')
        self.borrador['Jueves|07:30|08:30']={**self.bloque,'Dia':'Jueves','Inicio':'07:30','Fin':'08:30','Actividad':'Matemáticas'}
        before=deepcopy(self.borrador)
        with self.assertRaises(ValueError):self.actualizar(self.bloque,DIAS,reemplazar=True)
        self.assertEqual(before,self.borrador)
    def test_editar_copias_identicas_no_deja_bloques_obsoletos(self):
        repetido=self.actualizar(self.bloque,DIAS)
        result=actualizar_bloques_borrador(repetido,self.clave,{**self.bloque,'Fin':'07:30'},DIAS,'07:00','13:00')
        self.assertEqual(len(result),5)
        self.assertNotIn('Martes|07:00|08:00',result)
    def test_choques_se_verifican_para_todos_los_dias(self):
        result=self.actualizar(self.bloque,DIAS)
        restriction=pd.DataFrame([{'Dia':'Miércoles','Inicio':'07:15','Fin':'07:50','Grupo':'5 A','Actividad':'Inglés'}])
        choques=detectar_choques(list(result.values()),restriction)
        self.assertEqual(choques.iloc[0]['Día'],'Miércoles')

if __name__=='__main__':unittest.main()

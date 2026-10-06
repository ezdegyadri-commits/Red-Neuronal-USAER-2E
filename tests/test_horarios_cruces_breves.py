import json
import unittest
from copy import deepcopy
from unittest.mock import patch,Mock
import pandas as pd
from services import horarios as h

def caso():
    fila={'Dia':'Jueves','Inicio':'07:00','Fin':'08:00','Grupo':'1B','ID_Alumnos':'A1','Maestra':'Docente','Actividad':'Apoyo'}
    referencia=pd.DataFrame([{'Dia':'Jueves','Inicio':'07:50','Fin':'08:40','Grupo':'1B','Actividad':'Artes','Archivo':'Artes','ID_Version':'v1'}])
    return fila,referencia

class CrucesTests(unittest.TestCase):
    def aceptar(self):
        fila,ref=caso();original={'Jueves|07:00|08:00':fila}
        cruces=h.detectar_choques([fila],ref)
        nuevo=h.aceptar_cruces(original,cruces,[cruces.iloc[0]['Clave']],'Coordinado con el docente: regresa al aula a las 08:00.','Docente')
        return original,nuevo,ref
    def test_diez_minutos_requieren_acuerdo_y_conservan_original(self):
        original,nuevo,ref=self.aceptar()
        self.assertTrue(h.detectar_choques(list(nuevo.values()),ref).iloc[0]['Aceptado'])
        self.assertFalse(h.detectar_choques(list(original.values()),ref).iloc[0]['Aceptado'])
        self.assertNotIn('Cruces_Aceptados_JSON',next(iter(original.values())))
        self.assertEqual(h.detectar_choques(list(nuevo.values()),ref).iloc[0]['Minutos de cruce'],10)
    def test_mas_de_diez_no_admite_acuerdo(self):
        fila,ref=caso();fila['Fin']='08:01'
        cruce=h.detectar_choques([fila],ref)
        self.assertFalse(cruce.iloc[0]['Permite acuerdo'])
        with self.assertRaises(ValueError):h.aceptar_cruces({'Jueves|07:00|08:01':fila},cruce,[cruce.iloc[0]['Clave']],'Acuerdo por confirmar','Docente')
    def test_todas_las_materias_admiten_acuerdo_breve(self):
        for actividad in ('Educación física','Ed. Física','E.F.','EF','Educación Fis.','Maya','Inglés','Artes','Matemáticas'):
            fila,ref=caso();ref.loc[0,'Actividad']=actividad;ref.loc[0,'Inicio']='07:59'
            cruce=h.detectar_choques([fila],ref)
            self.assertTrue(cruce.iloc[0]['Permite acuerdo'],actividad)
    def test_no_permite_solapes_propios_o_con_otra_maestra(self):
        fila,_=caso();otra={**fila,'Inicio':'07:59','Fin':'08:30'}
        self.assertFalse(h.detectar_choques([fila,otra]).iloc[0]['Permite acuerdo'])
        otra['Maestra']='Colega'
        self.assertFalse(h.detectar_choques([fila],horarios_apoyo=pd.DataFrame([otra])).iloc[0]['Permite acuerdo'])
    def test_cambio_de_alumno_hora_o_referencia_invalida_acuerdo(self):
        _,nuevo,ref=self.aceptar();base=next(iter(nuevo.values()))
        for campo,valor in [('ID_Alumnos','A2'),('Fin','07:59'),('Grupo','1A')]:
            fila={**base,campo:valor};cruces=h.detectar_choques([fila],ref)
            self.assertTrue(cruces.empty or not cruces['Aceptado'].any())
        ref.loc[0,'ID_Version']='v2'
        self.assertFalse(h.detectar_choques([base],ref).iloc[0]['Aceptado'])
    def test_suma_de_cruces_superior_a_diez_no_se_acepta(self):
        fila,ref=caso();segunda={**ref.iloc[0].to_dict(),'Inicio':'07:40','Fin':'07:50','Actividad':'Maya','Archivo':'Maya'}
        cruces=h.detectar_choques([fila],pd.concat([ref,pd.DataFrame([segunda])]))
        self.assertFalse(cruces['Permite acuerdo'].any())
    def test_referencias_duplicadas_no_duplican_minutos(self):
        fila,ref=caso();ref=pd.concat([ref,ref])
        self.assertTrue(h.detectar_choques([fila],ref)['Permite acuerdo'].all())
    def test_motivo_vacio_no_se_guarda(self):
        fila,ref=caso();cruces=h.detectar_choques([fila],ref)
        with self.assertRaises(ValueError):h.aceptar_cruces({'Jueves|07:00|08:00':fila},cruces,[cruces.iloc[0]['Clave']],'','Docente')
    def test_guardado_central_conserva_acuerdo_y_revalida(self):
        _,nuevo,ref=self.aceptar();ws=Mock();rows=list(nuevo.values())
        with patch.object(h.st,'session_state',{'autenticado':True,'nombre':'Docente','rol':'APOYO'}),patch.object(h,'escuelas_asignadas',return_value=['Escuela']),patch.object(h,'cargar_restricciones',return_value=ref),patch.object(h,'cargar_horarios_apoyo',return_value=pd.DataFrame()),patch.object(h,'_leer',return_value=(ws,h.HORARIOS_APOYO_HEADERS,[])),patch.object(h,'_id_escuela',return_value='E1'),patch.object(h,'clear_cache'):
            h.guardar_horario_apoyo('Docente','Escuela',rows)
        valor=ws.append_rows.call_args.args[0][0][h.HORARIOS_APOYO_HEADERS.index('Cruces_Aceptados_JSON')]
        self.assertTrue(json.loads(valor))
    def test_guardado_central_exige_nuevo_acuerdo_si_cambia_la_materia(self):
        _,nuevo,ref=self.aceptar();ref.loc[0,'Actividad']='Educación física'
        with patch.object(h.st,'session_state',{'autenticado':True,'nombre':'Docente','rol':'APOYO'}),patch.object(h,'escuelas_asignadas',return_value=['Escuela']),patch.object(h,'cargar_restricciones',return_value=ref),patch.object(h,'cargar_horarios_apoyo',return_value=pd.DataFrame()):
            with self.assertRaises(ValueError):h.guardar_horario_apoyo('Docente','Escuela',list(nuevo.values()))

if __name__=='__main__':unittest.main()

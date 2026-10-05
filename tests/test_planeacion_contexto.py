import unittest
from unittest.mock import patch
from copy import deepcopy
import pandas as pd
from services import planeacion as s
from services.planeacion_modelo import crear_plantilla

ALUMNO={'ID_Alumno':'A1','Nombre_Completo':'Alumno ficticio','ID_Escuela':'E1','Nombre_Escuela':'Escuela ficticia','CCT_Escuela':'TEST','Grado':'3','Grupo':'A'}

def documento():
    d=crear_plantilla('XXIII',['A1'],[ALUMNO],autor='Docente ficticia',funcion='Aprendizaje')
    d.update(id='actual',cuenta='prueba',revision='')
    return d

class ContextoTests(unittest.TestCase):
    def test_grupal_no_se_duplica_ni_atribuye_individual(self):
        a2={**ALUMNO,'ID_Alumno':'A2','Nombre_Completo':'Otro alumno ficticio'}
        d=crear_plantilla('XXIII',['A1','A2'],[ALUMNO,a2],autor='Docente ficticia',funcion='Aprendizaje');d.update(id='actual',cuenta='prueba')
        bap=pd.DataFrame([{'ID_Alumno':'GRUPO-E1-3-A','ID_Anexo3':'B1','Fecha':'2026-10-01','BAP_Pedagogicas':'Apoyo visual registrado'}])
        with patch.object(s,'autorizar'),patch.object(s,'padron_autorizado',return_value=pd.DataFrame([ALUMNO,a2])),patch.object(s.repo,'alumnos',return_value=pd.DataFrame([ALUMNO,a2])),patch.object(s.repo,'anexo3',return_value=bap),patch.object(s.repo,'anexo4',return_value=pd.DataFrame()),patch.object(s.repo,'anexo5',return_value=pd.DataFrame()),patch.object(s.repo,'visitas',return_value=pd.DataFrame()),patch.object(s.repo,'eventos_alumno',return_value=pd.DataFrame()),patch.object(s,'df_sheet',return_value=pd.DataFrame()),patch.object(s,'versiones_actuales',return_value=[]):
            sources,failed=s.evidencias(d)
        self.assertEqual(len(sources),1)
        self.assertEqual(sources[0]['alcance'],'grupo vinculado')
        self.assertEqual(sources[0]['alumno'],'A1,A2')
        self.assertEqual(failed,[])
    def test_fuente_desconectada_conserva_contexto_previo(self):
        d=documento();source={'tipo':'III','registro':'B1','fecha':'2026-10-01','alumno':'A1','texto':'BAP documentada','alcance':'individual','referencia':'E1'}
        d['metadatos']['fuentes']=[source]
        with patch.object(s,'evidencias',return_value=([],['III'])),patch.object(s,'autorizar'):
            result=s.preparar_contexto(d)
        self.assertEqual(result['metadatos']['fuentes'][0]['texto'],'BAP documentada')
        self.assertEqual(d['metadatos']['fuentes'],[source])
    def test_planeacion_anterior_solo_alumnos_seleccionados(self):
        d=documento();previous=deepcopy(d);previous.update(id='anterior',estado='ENVIADO',revision='r1',guardado_en='2026-09-30');previous['textos']['Evaluación']='Apoyo registrado para seguimiento'
        other=deepcopy(previous);other['id']='ajeno';other['datos']['Alumnos'][0]['ID_Alumno']='A2'
        with patch.object(s,'autorizar'),patch.object(s,'padron_autorizado',return_value=pd.DataFrame([ALUMNO])),patch.object(s.repo,'alumnos',return_value=pd.DataFrame([ALUMNO])),patch.object(s.repo,'anexo3',return_value=pd.DataFrame()),patch.object(s.repo,'anexo4',return_value=pd.DataFrame()),patch.object(s.repo,'anexo5',return_value=pd.DataFrame()),patch.object(s.repo,'visitas',return_value=pd.DataFrame()),patch.object(s.repo,'eventos_alumno',return_value=pd.DataFrame()),patch.object(s,'df_sheet',return_value=pd.DataFrame()),patch.object(s,'versiones_actuales',return_value=[previous,other]):
            sources,_=s.evidencias(d)
        self.assertEqual([f['registro'] for f in sources],['anterior'])
        self.assertIn('no equivale a resultado',sources[0]['alcance'])

if __name__=='__main__':unittest.main()

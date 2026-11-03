import unittest
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier,Lock
import pandas as pd
from data import repository as r
class LecturaIndiceTests(unittest.TestCase):
 def test_copia_por_llamador_y_una_consulta_por_indice(self):
  with patch.object(r,'_leer_alumnos',return_value=pd.DataFrame([{'ID':'A'}])) as read:
   with r.captura_padron():
    a=r.alumnos();a.loc[0,'ID']='CAMBIO LOCAL'
    self.assertEqual(r.alumnos().loc[0,'ID'],'A')
   self.assertEqual(read.call_count,1)
   r.alumnos();self.assertEqual(read.call_count,2)
 def test_peticiones_concurrentes_no_comparten_instantaneas(self):
  lock=Lock();count=[0];barrier=Barrier(2)
  def read():
   with lock:count[0]+=1;n=count[0]
   return pd.DataFrame([{'ID':n}])
  def one(_):
   with r.captura_padron():
    a=r.alumnos().loc[0,'ID'];barrier.wait()
    self.assertEqual(a,r.alumnos().loc[0,'ID']);return a
  with patch.object(r,'_leer_alumnos',side_effect=read),ThreadPoolExecutor(max_workers=2) as pool:
   self.assertEqual(len(set(pool.map(one,range(2)))),2)
  self.assertEqual(count[0],2)
 def test_invalidacion_no_conserva_lectura_antigua(self):
  with patch.object(r,'_leer_alumnos',side_effect=[pd.DataFrame([{'ID':'A'}]),pd.DataFrame([{'ID':'B'}])]):
   with r.captura_padron():
    self.assertEqual(r.alumnos().loc[0,'ID'],'A');r.clear_alumnos_cache()
    self.assertEqual(r.alumnos().loc[0,'ID'],'B')

 def test_grupo_sin_alumnos_vigentes_no_bloquea_el_repositorio(self):
  from services import planeacion as s,planeacion_compartida as compartida,planeacion_grupo_unico as grupos
  from tests.test_planeacion_compartida import grupal
  from copy import deepcopy
  d=grupal();empty=deepcopy(d);empty['datos']['Alumnos']=[]
  with patch.object(s,'versiones_actuales',return_value=[d]),patch.object(s,'padron_autorizado',return_value=pd.DataFrame()),patch.object(grupos,'documentos',return_value=[d]),patch.object(compartida,'ampliar_matricula',return_value=empty),patch.object(s,'autorizar') as authorize:
   self.assertEqual(s.compartidos(),[]);authorize.assert_not_called()
  self.assertTrue(d['datos']['Alumnos'])

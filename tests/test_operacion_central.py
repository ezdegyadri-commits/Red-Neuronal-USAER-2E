"""Enrutamiento de Streamlit: fuente única, sin datos de producción."""
import os,unittest
from unittest.mock import patch
from concurrent.futures import Future
import pandas as pd
from data import repository as repo,origen_operativo as policy,sql_repository as sql
from ui import operacion_actualizacion as activation
class OperacionTests(unittest.TestCase):
 def test_database_url_does_not_activate_sql(self):
  with patch.dict(os.environ,{'DATABASE_URL':'postgresql://fake:fake@localhost/fake','DISABLE_SQL':''}),patch('streamlit.secrets',{}):
   self.assertFalse(policy.usar_sql())
 def test_sql_is_explicit_and_disable_wins(self):
  with patch.dict(os.environ,{'USAER_STREAMLIT_DATA_SOURCE':'postgresql','DISABLE_SQL':''}):self.assertTrue(policy.usar_sql())
  with patch.dict(os.environ,{'USAER_STREAMLIT_DATA_SOURCE':'postgresql','DISABLE_SQL':'1'}):self.assertFalse(policy.usar_sql())
 def test_unknown_source_does_not_silently_write_elsewhere(self):
  with patch.dict(os.environ,{'USAER_STREAMLIT_DATA_SOURCE':'otra','DISABLE_SQL':''}):
   with self.assertRaises(ValueError):policy.usar_sql()
 def test_reads_use_central_with_sql_url_present(self):
  frame=pd.DataFrame([{'ID_Alumno':'F1','Nombre_Completo':'Alumno ficticio','CURP':'FICTICIO','Grado':'1','ID_Escuela':'E1','Estatus':'ACTIVO'}])
  cases=[('personal','Personal'),('asignaciones','Asignaciones'),('anexo3','Anexo3_Deteccion'),('anexo4','Anexo4_Sugerencias'),('anexo5','Anexo5_Eventos'),('anexo7','Anexo7_Derivacion'),('visitas','Registro_Visitas'),('oficios_comision','Oficios_Comision')]
  with patch.dict(os.environ,{'DATABASE_URL':'postgresql://fake:fake@localhost/fake','USAER_STREAMLIT_DATA_SOURCE':'central','DISABLE_SQL':''}),patch.object(repo,'read',return_value=frame) as read,patch.object(sql,'alumnos_sql',side_effect=AssertionError('SQL no debe consultarse')):
   repo._alumnos_operativos.clear();self.assertEqual(list(repo.alumnos()['ID_Alumno']),['F1'])
   for fn,table in cases:
    getattr(repo,fn)();self.assertEqual(read.call_args.args[0],table)
  repo._alumnos_operativos.clear()
 def test_write_goes_to_same_central_source(self):
  with patch.dict(os.environ,{'USAER_STREAMLIT_DATA_SOURCE':'central','DISABLE_SQL':''}),patch.object(repo,'ensure_headers'),patch.object(repo,'next_numeric_id',return_value='VIS-FICTICIA'),patch.object(repo,'append_dict') as append,patch.object(sql,'save_visita_sql') as sqlwrite:
   self.assertEqual(repo.save_visita({'Motivo':'Reunión ficticia'}),'VIS-FICTICIA');self.assertEqual(append.call_args.args[0],'Registro_Visitas');sqlwrite.assert_not_called()
 def test_explicit_sql_does_not_fallback_on_error(self):
  with patch.dict(os.environ,{'USAER_STREAMLIT_DATA_SOURCE':'postgresql','DISABLE_SQL':''}),patch.object(sql,'alumnos_sql',side_effect=ConnectionError('simulada')),patch.object(repo,'read') as central:
   with self.assertRaises(ConnectionError):repo.alumnos()
   central.assert_not_called()
 def test_activation_replaces_old_selector_without_losing_draft(self):
  future=Future();doc={'id':'ficticia','texto':'captura pendiente'}
  state={'autenticado':True,'usuario':'ficticia','p_doc':doc,'p_pending':True,'p_cola':{'A':'sin confirmar'},'p_trabajo_io':future,'evento_descripcion':'conservar evento','_padron_autorizado_identidad_v3_ficticia':pd.DataFrame(),'_padron_autorizado_identidad_v3_ficticia_leido_en':123}
  with patch.object(activation,'_aplicada',False),patch.object(repo,'usar_sql',return_value=True),patch.object(repo,'clear_alumnos_cache') as clear,patch.object(activation.st,'session_state',state):
   activation.preparar();self.assertIs(repo.usar_sql,policy.usar_sql);clear.assert_called_once();self.assertIs(state['p_doc'],doc);self.assertIs(state['p_trabajo_io'],future);self.assertTrue(state['p_pending']);self.assertEqual(state['p_cola'],{'A':'sin confirmar'});self.assertEqual(state['evento_descripcion'],'conservar evento');self.assertFalse(any(k.startswith('_padron_autorizado_') for k in state))

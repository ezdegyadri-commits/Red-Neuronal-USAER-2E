"""Regresión de Streamlit y SQL aislado. Sin datos ni escrituras de producción."""
import unittest,inspect
from unittest.mock import patch
from copy import deepcopy
from concurrent.futures import Future
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from data import repository as repo,database as db,sql_repository as sql
from services.autenticacion import buscar_usuario
from data import acceso_usuarios as source
from ui import guardado_seguro,guardado_asincrono as plan,epp_guardado_asincrono as eppui
from tests.test_planeacion_panel import ACTOR,documento
from services.epp_modelo import vacia
FIELDS=['ID_Usuario','Nombre','Usuario','Password','Rol','Escuelas_Permitidas']
ROW=dict(ID_Usuario='F1',Nombre='Persona Ficticia',Usuario='maestra_ñ',Password=' clave ñ ',Rol='APOYO',Escuelas_Permitidas='E1')
class AccessTests(unittest.TestCase):
 def test_postgresql_is_the_only_authentication_source(self):
  with patch.object(source,'_sql',return_value=pd.DataFrame([ROW])) as sqlread,patch.object(source,'df_sheet') as read:
   self.assertEqual(repo.usuarios().iloc[0]['Usuario'],ROW['Usuario']);sqlread.assert_called_once();read.assert_not_called()
 def test_empty_sql_catalog_is_service_error_not_bad_password(self):
  with patch.object(source,'_sql',return_value=pd.DataFrame(columns=FIELDS)):
   with self.assertRaises(RuntimeError):repo.usuarios()
 def test_explicit_sql_remains_sole_source(self):
  with patch.object(source,'fuente',return_value='postgresql'),patch.object(source,'_sql',return_value=pd.DataFrame([ROW])),patch.object(source,'df_sheet') as fallback:
   self.assertEqual(repo.usuarios().to_dict('records'),[ROW]);fallback.assert_not_called()
 def test_sql_failure_does_not_resurrect_central_account(self):
  with patch.object(source,'fuente',return_value='postgresql'),patch.object(source,'_sql',side_effect=ConnectionError()),patch.object(source,'df_sheet') as fallback:
   with self.assertRaises(ConnectionError):repo.usuarios()
   fallback.assert_not_called()
 def test_activation_replaces_old_imports_without_touching_session(self):
  from ui import auth,acceso_actualizacion as activation
  before={'autenticado':True,'borrador_ficticio':'NO BORRAR'}
  with patch.object(activation,'_aplicada',False),patch.object(auth,'usuarios',return_value=pd.DataFrame()),patch.object(repo,'usuarios',return_value=pd.DataFrame()),patch('data.google.clear_cache') as clear,patch.object(auth.st,'session_state',before):
   activation.preparar();self.assertIs(auth.usuarios,source.usuarios);self.assertIs(repo.usuarios,source.usuarios)
   clear.assert_called_once_with('Usuarios');self.assertEqual(before,{'autenticado':True,'borrador_ficticio':'NO BORRAR'})
 def test_activation_reloads_cached_old_auth_module(self):
  from ui import auth,acceso_actualizacion as activation
  with patch.object(activation,'_aplicada',False),patch.object(auth,'VERSION_ACCESO','anterior'),patch.object(auth,'usuarios',return_value=pd.DataFrame()),patch.object(repo,'usuarios',return_value=pd.DataFrame()),patch('data.google.clear_cache'):
   activation.preparar();self.assertEqual(auth.VERSION_ACCESO,'A3');self.assertIs(auth.usuarios,source.usuarios)
 def test_exact_utf8_credentials_and_ambiguous_account_rejected(self):
  frame=pd.DataFrame([ROW]);self.assertIsNotNone(buscar_usuario(frame,ROW['Usuario'],ROW['Password']))
  for user,password in [(ROW['Usuario'].upper(),ROW['Password']),(ROW['Usuario'],ROW['Password'].strip())]:self.assertIsNone(buscar_usuario(frame,user,password))
  self.assertIsNone(buscar_usuario(pd.concat([frame,frame]),ROW['Usuario'],ROW['Password']))
 def test_sql_users_read_does_not_create_unmigrated_table(self):
  engine=create_engine('sqlite://')
  with patch.object(sql,'get_engine',return_value=engine) as get,patch.object(sql,'get_session') as session:
   self.assertTrue(sql.usuarios_sql().empty);get.assert_called_once_with(initialize_schema=False);session.assert_not_called()
  self.assertFalse(inspect_sql(engine,'usuarios'));engine.dispose()
 def test_sql_contract_matches_legacy_credentials(self):
  engine=create_engine('sqlite://');db.Usuario.__table__.create(engine)
  with db.SafeSession(engine) as s:
   s.add(db.Usuario(id='F1',nombre=ROW['Nombre'],usuario=ROW['Usuario'],password=ROW['Password'],rol=ROW['Rol'],escuelas_permitidas='E1'));s.commit()
  with patch.object(sql,'get_engine',return_value=engine),patch.object(sql,'get_session',side_effect=lambda **kw:db.SafeSession(engine)):
   self.assertIsNotNone(buscar_usuario(sql.usuarios_sql(),ROW['Usuario'],ROW['Password']))
  engine.dispose()
 def test_streamlit_form_login_uses_sql_with_existing_password(self):
  from streamlit.testing.v1 import AppTest
  from ui import auth
  script="""import streamlit as st
from ui.auth import login
if st.session_state.get('autenticado'):st.success('Acceso correcto')
else:login()
"""
  with patch.object(source,'_sql',return_value=pd.DataFrame([ROW])),patch.object(auth,'login_passkey'),patch.object(auth,'installation_help'):
   app=AppTest.from_string(script).run(timeout=15)
   app.text_input[0].set_value(ROW['Usuario']);app.text_input[1].set_value(ROW['Password']);app.button[0].click().run(timeout=15)
   self.assertFalse(app.exception);self.assertTrue(app.session_state['autenticado']);self.assertEqual(app.success[0].value,'Acceso correcto')
def inspect_sql(engine,name):
 from sqlalchemy import inspect as insp
 return insp(engine).has_table(name)
class RetentionTests(unittest.TestCase):
 def test_plan_failure_preserves_full_capture_and_shows_red_error(self):
  doc=documento();doc['textos']['Evaluación']='Captura que se debe conservar';state={'p_doc':deepcopy(doc),'p_papel_nonce':'envio-ficticio'}
  f=Future();f.set_exception(ConnectionError('simulada'));state['p_trabajo_io']={'future':f,'cuenta':ACTOR['cuenta'],'documento':doc['id']}
  with patch.object(plan.st,'session_state',state),patch.object(plan.s,'identidad',return_value=ACTOR),patch.object(plan.st,'error') as error,patch.object(plan.st,'toast'),patch.object(plan.st,'rerun') as rerun:
   self.assertFalse(plan.persistir('p'));error.assert_called_with(guardado_seguro.ERROR_CONEXION);rerun.assert_not_called()
  self.assertEqual(state['p_doc'],doc);self.assertTrue(state['p_pending']);self.assertNotIn('p_papel_aceptado',state)
 def test_epp_failure_preserves_full_capture_and_queue(self):
  doc={'id':'ficticia','partes':{'Aprendizaje':{'contenido':vacia('Aprendizaje'),'revision':''}}};doc['partes']['Aprendizaje']['contenido']['campos']['5.1. Competencia curricular']='Hallazgo ficticio'
  cola={'Aprendizaje':{'base':vacia('Aprendizaje'),'revision':''}};f=Future();f.set_result(({},TimeoutError('simulado')))
  state={'p_doc':deepcopy(doc),'p_cola':deepcopy(cola),'p_trabajo_io':{'future':f,'cuenta':ACTOR['cuenta'],'documento':doc['id'],'enviado':deepcopy(doc),'nonce':'n'}}
  with patch.object(eppui.st,'session_state',state),patch.object(eppui.s,'actor',return_value=ACTOR),patch.object(eppui.st,'error') as error,patch.object(eppui.st,'toast'),patch.object(eppui.st,'rerun') as rerun:
   self.assertFalse(eppui.guardar('p'));error.assert_called_with(guardado_seguro.ERROR_CONEXION);rerun.assert_not_called()
  self.assertEqual(state['p_doc'],doc);self.assertEqual(state['p_cola'],cola);self.assertTrue(state['p_pending']);self.assertNotIn('p_aceptado',state)
 def test_failed_ack_does_not_rerun_either_document(self):
  for module,func in [(plan,'persistir'),(eppui,'guardar')]:
   state={'p_trabajo_io':{'future':Future()},'p_doc':{'texto':'conservar'}}
   def failed(*args,**kwargs):state.pop('p_trabajo_io');return False
   with patch.object(module.st,'session_state',state),patch.object(module,func,side_effect=failed),patch.object(module.st,'rerun') as rerun:
    inspect.unwrap(module.acuses)('p');rerun.assert_not_called()
 def test_sql_transaction_failure_rolls_back_and_closes(self):
  engine=create_engine('sqlite://');db.Usuario.__table__.create(engine)
  s=db.SafeSession(engine)
  with patch.object(s,'rollback',wraps=s.rollback) as rollback:
   with self.assertRaises(ConnectionError):
    with s:
     s.add(db.Usuario(id='ficticia',usuario='ficticia'));s.flush();raise ConnectionError('simulada')
   rollback.assert_called_once()
  with Session(engine) as check:self.assertEqual(check.query(db.Usuario).count(),0)
  engine.dispose()
 def test_sql_commit_error_rolls_back_without_ack(self):
  engine=create_engine('sqlite://');db.Usuario.__table__.create(engine);s=db.SafeSession(engine)
  with patch.object(s,'commit',side_effect=TimeoutError('commit simulado')),patch.object(s,'rollback',wraps=s.rollback) as rollback:
   with self.assertRaises(TimeoutError):
    with s:s.add(db.Usuario(id='ficticia',usuario='ficticia'));s.flush();s.commit()
   rollback.assert_called_once()
  with Session(engine) as check:self.assertEqual(check.query(db.Usuario).count(),0)
  engine.dispose()

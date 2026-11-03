"""La contingencia no abre SQL, incluso con variables de migración presentes."""
import ast,os,unittest
from pathlib import Path
from unittest.mock import patch,Mock
from data import acceso_usuarios as acceso,origen_operativo,google
from services import planeacion_estabilidad as estabilidad
class ContingenciaTests(unittest.TestCase):
 def test_flags_never_enable_postgres(self):
  with patch.dict(os.environ,{'DATABASE_URL':'postgresql://ficticio','USAER_AUTH_SOURCE':'postgresql','USAER_STREAMLIT_DATA_SOURCE':'postgresql'}):
   self.assertFalse(origen_operativo.usar_sql());self.assertEqual(acceso.fuente(),'central')
 def test_connects_to_google_service_account(self):
  fake=Mock();fake.open_by_url.return_value=Mock()
  with patch.object(google,'_secret_dict',return_value={'type':'service_account'}),patch.object(google.gspread,'service_account_from_dict',return_value=fake) as factory:
   google.connections.clear();result=google.connections();self.assertIs(result[0],fake.open_by_url.return_value);factory.assert_called_once();fake.set_timeout.assert_called_once();google.connections.clear()
 def test_core_has_no_postgres_imports(self):
  for name in ['services/planeacion.py','services/epp.py','services/planeacion_estabilidad.py','services/cronogramas.py','services/archivo_expediente.py','data/google.py']:
   with self.subTest(name=name):
    tree=ast.parse(Path(name).read_text(encoding='utf-8'))
    self.assertFalse(any(isinstance(n,ast.ImportFrom) and n.module=='data.pg_documental' for n in ast.walk(tree)))
 def test_reads_are_cached(self):
  tree=ast.parse(Path('data/google.py').read_text(encoding='utf-8'))
  for name in ['read_sheet','read_personal_responses']:
   fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
   self.assertTrue(any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='cache_data' and any(k.arg=='ttl' and isinstance(k.value,ast.Constant) and k.value.value>=60 for k in n.keywords) for n in fn.decorator_list))
 def test_write_budget_is_active(self):
  budget=Mock()
  with patch.object(estabilidad,'presupuesto',return_value=budget):estabilidad.reservar_escritura();budget.reservar.assert_called_once()

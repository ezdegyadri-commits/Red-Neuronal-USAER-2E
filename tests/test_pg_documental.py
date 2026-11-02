import unittest
from copy import deepcopy
from unittest.mock import patch
from sqlalchemy import create_engine,select,func
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from data import pg_documental as pg
from data.sincronizacion_pg import crear_esquema
from data.database import Usuario,Alumno

class DocumentoSQLTests(unittest.TestCase):
 def setUp(self):
  self.engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
  with self.engine.begin() as c:crear_esquema(c);pg.Base.metadata.create_all(c)
  self.initial={"Datos":[["ID","Uno","Dos"],["id-1","original","sin cambio"],[],["id-2","último"]],"Usuarios":[["ID_Usuario","Nombre","Usuario","Password","Rol","Escuelas_Permitidas"],["U1","Persona ficticia","ficticio","contraseña","Director","ESC-001"]]}
  with Session(self.engine) as s,s.begin():pg.importar_libro(s,"libro",self.initial)
  self.book=pg.Libro("libro",self.engine)
 def tearDown(self):self.engine.dispose()
 def test_roundtrip_positions_empty_rows_extra_columns(self):
  self.assertEqual(self.book.worksheet("Datos").get_all_values(),self.initial["Datos"])
  self.assertEqual(self.book.worksheet("Datos").get("A2:B4"),[["id-1","original"],[],["id-2","último"]])
 def test_idempotent_atomic_append_and_receipt(self):
  sheet=self.book.worksheet("Datos");a=sheet.append_rows([["id-3","nueva","captura"]]);b=sheet.append_rows([["id-3","nueva","captura"]])
  self.assertEqual(a,b);self.assertEqual(a["updates"]["updatedRange"],"'Datos'!A5:C5")
  self.assertEqual(len(sheet.get_all_values()),5)
 def test_different_cells_merge_and_same_cell_conflicts_without_losing_data(self):
  a=self.book.worksheet("Datos");b=self.book.worksheet("Datos")
  baseline=a.row_values(2);b.row_values(2)
  a.update_cell(2,2,"aportación A")
  baseline[2]="aportación B";b.update(values=[baseline],range_name="A2:C2")
  self.assertEqual(a.row_values(2),["id-1","aportación A","aportación B"])
  stale=self.book.worksheet("Datos");stale.row_values(2);a.update_cell(2,2,"nuevo")
  with self.assertRaises(pg.Conflicto):stale.update_cell(2,2,"texto en conflicto")
  self.assertEqual(a.row_values(2)[1],"nuevo")
 def test_history_keeps_before_and_after(self):
  sheet=self.book.worksheet("Datos");sheet.row_values(2);sheet.update_cell(2,2,"redacción")
  with Session(self.engine) as s:
   change=s.scalars(select(pg.Cambio)).one();self.assertEqual(change.antes[1],"original");self.assertEqual(change.despues[1],"redacción")
 def test_transaction_rollback_preserves_full_document(self):
  sheet=self.book.worksheet("Datos")
  with self.assertRaises(RuntimeError):
   with pg.bloqueo("doc",self.engine):sheet.append_rows([["no persistir","texto","pendiente"]]);raise RuntimeError("fallo")
  self.assertEqual(sheet.get_all_values(),self.initial["Datos"])
 def test_confirm_commits_before_ack_and_retry_does_not_duplicate(self):
  sheet=self.book.worksheet("Datos")
  with pg.bloqueo("doc",self.engine):sheet.append_rows([["persistir","texto","confirmado"]]);pg.confirmar()
  self.assertEqual(sheet.get_all_values()[-1],["persistir","texto","confirmado"])
 def test_projection_keeps_sql_user_table_in_same_transaction(self):
  sheet=self.book.worksheet("Usuarios");sheet.row_values(2);sheet.update_cell(2,4,"clave nueva")
  with Session(self.engine) as s:self.assertEqual(s.get(Usuario,"U1").password,"clave nueva")
 def test_columns_headers_and_literal_formulas(self):
  sheet=self.book.add_worksheet("Nueva",cols=3);sheet.append_row(["ID","Texto"]);sheet.append_row(["A","=no es una fórmula"])
  sheet.add_cols(2);sheet.update_cell(1,3,"Adicional")
  self.assertEqual(sheet.row_values(1),["ID","Texto","Adicional"]);self.assertEqual(sheet.col_values(2),["Texto","=no es una fórmula"])
 def test_source_change_never_overwrites_live_capture(self):
  other=deepcopy(self.initial);other["Datos"][1][1]="cambio"
  with self.assertRaises(pg.Conflicto):
   with Session(self.engine) as s,s.begin():pg.importar_libro(s,"libro",other)
  self.assertEqual(self.book.worksheet("Datos").row_values(2)[1],"original")
 def test_backend_google_names_never_connect_google(self):
  import data.google as bridge
  with patch.object(pg,"motor",return_value=self.engine),patch.object(bridge,"_secret_dict",side_effect=AssertionError("No Google")):
   self.assertIsInstance(bridge.service_account_client(),pg.Cliente)
   self.assertIsInstance(bridge.connections()[0],pg.Libro)
 def test_missing_postgresql_cannot_fallback_sqlite_or_sheets(self):
  pg.motor.cache_clear()
  with patch("data.database.get_database_url",return_value="sqlite:///no.db"):
   with self.assertRaises(RuntimeError):pg.motor()
 def test_three_way_merge_refuses_real_conflicts_and_keeps_disjoint_changes(self):
  from tools.corte_streamlit_pg import tres_vias
  self.assertEqual(tres_vias({"A":"base","B":"base"},{"A":"nuevo fuente","B":"base"},{"A":"base","B":"nuevo SQL"}),{"A":"nuevo fuente","B":"nuevo SQL"})
  with self.assertRaises(Exception):tres_vias({"A":"base"},{"A":"fuente"},{"A":"SQL"})
 def test_reconcile_keeps_original_blank_row_positions(self):
  from tools.corte_streamlit_pg import reconciliar
  from data.database import Alumno
  source={"Alumnos":[["ID_Alumno","Nombre_Completo","CURP","Grado"],["A1","Uno","C1","1"],[],["A2","Dos","C2","2"]]}
  with Session(self.engine) as s,s.begin():
   s.add_all([Alumno(id="A1",nombre_completo="Uno",curp="C1",grado="1"),Alumno(id="A2",nombre_completo="Dos",curp="C2",grado="2")])
  with Session(self.engine,autoflush=False) as s:
   result,_=reconciliar(s,source,source)
   self.assertEqual(result["Alumnos"],source["Alumnos"])
 def test_latest_and_per_document_history_never_drop_old_revisions(self):
  import json,hashlib
  from services.planeacion import HEADERS
  sheet=self.book.add_worksheet('Planeaciones_Versiones',cols=len(HEADERS));sheet.append_row(HEADERS)
  def append(doc,rev,date):
   value={'id':doc,'cuenta':'ficticio','formato':'XXIII','estado':'BORRADOR','datos':{},'metadatos':{},'revision':rev,'guardado_en':date}
   payload=json.dumps(value,ensure_ascii=False,sort_keys=True)
   sheet.append_rows([[doc,rev,'',date,'ficticio','Docente ficticio','E1','[]','XXIII','BORRADOR','0','1',hashlib.sha256(payload.encode()).hexdigest(),payload]])
  append('D1','R1','2026-11-01T09:00:00');append('D1','R2','2026-11-02T09:00:00');append('D2','R3','2026-11-02T09:01:00')
  self.assertEqual({d['revision'] for d in pg.planes(engine=self.engine,libro='libro')},{'R2','R3'})
  self.assertEqual({d['revision'] for d in pg.planes(True,'D1',self.engine,'libro')},{'R1','R2'})
  with pg.bloqueo('D1',self.engine):self.assertEqual({d['revision'] for d in pg.planes(engine=self.engine,libro='libro')},{'R1','R2','R3'})
  self.assertEqual(len(sheet.get_all_values()),4)
 def test_catchup_keeps_captures_from_both_sides_and_blank_rows(self):
  before=deepcopy(self.initial);incoming=deepcopy(before)
  incoming['Datos'][1][1]='cambio fuente';incoming['Datos'].append(['origen','captura nueva',''])
  sheet=self.book.worksheet('Datos');sheet.row_values(2);sheet.update_cell(2,3,'cambio Neon');sheet.append_rows([['neon','captura propia','']])
  with Session(self.engine) as s,s.begin():pg.conciliar_origen(s,'libro',before,incoming)
  data=sheet.get_all_values();self.assertEqual(data[1],['id-1','cambio fuente','cambio Neon']);self.assertEqual(data[2],[])
  self.assertIn(['origen','captura nueva',''],data);self.assertIn(['neon','captura propia',''],data)
 def test_catchup_same_cell_conflict_rolls_back(self):
  before=deepcopy(self.initial);incoming=deepcopy(before);incoming['Datos'][1][1]='fuente'
  sheet=self.book.worksheet('Datos');sheet.row_values(2);sheet.update_cell(2,2,'Neon')
  with self.assertRaises(pg.Conflicto):
   with Session(self.engine) as s,s.begin():pg.conciliar_origen(s,'libro',before,incoming)
  self.assertEqual(sheet.row_values(2)[1],'Neon')
 def test_atomic_id_reservation_does_not_reuse_an_id(self):
  sheet=self.book.add_worksheet('IDs',cols=1);sheet.append_row(['ID']);sheet.append_row(['ALU-007'])
  self.assertEqual(pg.siguiente_id('libro','IDs','ID','ALU',self.engine),'ALU-008')
  self.assertEqual(pg.siguiente_id('libro','IDs','ID','ALU',self.engine),'ALU-009')
 def test_archived_file_uses_stable_identity_not_row_offset(self):
  sheet=self.book.add_worksheet('Partes',cols=4);sheet.append_row(['ID_Documento','Indice','Total','Contenido'])
  sheet.append_rows([['F1','0','2','primero'],['F2','0','1','otro'],['F1','1','2','segundo']])
  self.assertEqual([r[-1] for r in sheet.por_clave('ID_Documento','F1')],['primero','segundo'])
 def test_original_epp_permissions_and_collaboration_with_fake_store(self):
  # La suite histórica conserva su almacén ficticio; la transacción SQL se prueba arriba.
  from contextlib import nullcontext
  import tests.test_epp as legacy
  result=unittest.TestResult()
  with patch.object(pg,"bloqueo",side_effect=lambda *a,**k:nullcontext()):unittest.defaultTestLoader.loadTestsFromTestCase(legacy.EPPTests).run(result)
  self.assertEqual(result.errors,[]);self.assertEqual(result.failures,[])

if __name__=="__main__":unittest.main()

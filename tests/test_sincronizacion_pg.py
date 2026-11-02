import unittest
from copy import deepcopy
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session
from data.sincronizacion_pg import crear_esquema, importar, preparar, manifiesto, Pestana, Copia, Integridad, registros
from data.database import Usuario, Alumno

class SincronizacionTests(unittest.TestCase):
    def setUp(self):
        self.engine=create_engine("sqlite://")
        with self.engine.begin() as c: crear_esquema(c)
        self.source={
          "Usuarios":[["ID_Usuario","Nombre","Usuario","Password","Rol","Escuelas_Permitidas"],["USR-1","Persona ficticia","docente","clave-ficticia","Comunicación","ESC-001"]],
          "Alumnos":[["ID_Alumno","Nombre_Completo","CURP","ID_Escuela","Maestra de Apoyo","Campo_Adicional"],["ALU-001","Alumno ficticio","FICTICIO","ESC-001","Persona ficticia","no perder"]],
          "Planeaciones_Versiones":[["Documento","Revision","Contenido"],["DOC-1","REV-1","{texto íntegro}"],[],["DOC-1","REV-1","{texto íntegro}"]],
          "EPP_Versiones":[["Alumno","Contenido"],["ALU-001","texto EPP"]],
          "Otra_Pestana":[["Encabezado","Encabezado",""],["primero","segundo","tercero"]]}
    def apply(self,source=None,**kw):
        with Session(self.engine) as s,s.begin(): return importar(s,source or self.source,"fuente-ficticia",**kw)
    def test_full_content_order_duplicates_extra_columns_and_idempotency(self):
        first=self.apply(); second=self.apply()
        self.assertEqual(first["copia"],second["copia"])
        self.assertEqual(second["pestanas"]["Usuarios"]["insertados"],0)
        with Session(self.engine) as s:
            self.assertEqual(s.scalar(select(func.count()).select_from(Copia)),1)
            for name,values in self.source.items(): self.assertEqual(s.get(Pestana,(first["copia"],name)).valores,values)
            self.assertEqual(s.get(Usuario,"USR-1").password,"clave-ficticia")
            self.assertEqual(s.get(Alumno,"ALU-001").maestra_apoyo,"Persona ficticia")
    def test_failure_rolls_back_everything(self):
        with self.assertRaises(Integridad): self.apply(test_fail=True)
        with Session(self.engine) as s:
            self.assertEqual(s.scalar(select(func.count()).select_from(Copia)),0)
            self.assertIsNone(s.get(Usuario,"USR-1"))
    def test_existing_different_capture_blocks_entire_import(self):
        self.apply(); other=deepcopy(self.source); other["Usuarios"][1][3]="otra-clave"
        with self.assertRaises(Integridad): self.apply(other)
        with Session(self.engine) as s:
            self.assertEqual(s.get(Usuario,"USR-1").password,"clave-ficticia")
            self.assertEqual(s.scalar(select(func.count()).select_from(Copia)),1)
    def test_empty_authorized_row_only_excluded_if_still_empty(self):
        source=deepcopy(self.source); source["Alumnos"].append(["ALU-276","","","","",""])
        rows,excluded=preparar(source);self.assertEqual(excluded,1);self.assertEqual(len(rows["Alumnos"]),1)
        source["Alumnos"][-1][1]="Ahora tiene información"
        with self.assertRaises(Integridad): preparar(source)
    def test_unknown_columns_retained_and_unnamed_headers_supported(self):
        records=registros(self.source["Otra_Pestana"])
        self.assertEqual(records,[{"Encabezado":"primero","Encabezado_2":"segundo","Columna_3":"tercero"}])
    def test_nonempty_cells_beyond_header_rejected_not_truncated(self):
        with self.assertRaises(Integridad): registros([["A"],["x","no perder"]])
    def test_content_comparison_detects_changes_with_same_counts(self):
        other=deepcopy(self.source);other["EPP_Versiones"][1][1]="otra redacción"
        self.assertNotEqual(manifiesto(other),manifiesto(self.source))
    def test_source_not_mutated(self):
        original=deepcopy(self.source);self.apply();self.assertEqual(self.source,original)
    def test_duplicate_identity_with_different_data_rejected(self):
        source=deepcopy(self.source);source["Usuarios"].append(["USR-1","Otra persona","otro","x","Apoyo","ESC-2"])
        with self.assertRaises(Integridad): preparar(source)
    def test_duplicate_id_different_unknown_column_is_not_silently_merged(self):
        source=deepcopy(self.source);extra=deepcopy(source["Alumnos"][1]);extra[-1]="otro antecedente";source["Alumnos"].append(extra)
        with self.assertRaises(Integridad):preparar(source)
    def test_empty_schools_uses_real_catalog_not_sample_schools(self):
        source=deepcopy(self.source);source["Escuelas"]=[["ID_Escuela","Nombre_Escuela"]]
        rows,_=preparar(source)
        self.assertEqual(len(rows["Escuelas"]),8)
        self.assertEqual({r["id"] for r in rows["Escuelas"]},{f"ESC-{i:03d}" for i in range(1,9)})
    def test_empty_sql_school_read_never_creates_examples(self):
        from unittest.mock import patch
        from data import sql_repository
        from data.database import Escuela
        with patch.object(sql_repository,"get_session",side_effect=lambda: Session(self.engine)):
            self.assertTrue(sql_repository.escuelas_sql().empty)
        with Session(self.engine) as s:self.assertEqual(s.scalar(select(func.count()).select_from(Escuela)),0)
    def test_no_network_writes_in_reader(self):
        import ast
        from pathlib import Path
        tree=ast.parse(Path("tools/sync_central_pg.py").read_text(encoding="utf-8"))
        forbidden={"append_row","append_rows","update","update_cell","batch_update","delete_rows","clear","add_worksheet","del_worksheet"}
        self.assertFalse([n.attr for n in ast.walk(tree) if isinstance(n,ast.Attribute) and n.attr in forbidden])

if __name__=="__main__":unittest.main()

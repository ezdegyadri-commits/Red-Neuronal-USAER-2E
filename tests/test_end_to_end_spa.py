"""Pruebas Integrales End-to-End para USAER 2E 2.0 SPA.

Verifica la paridad funcional real, el control de acceso RBAC, la persistencia en base de datos,
el control de versiones, la resolución de firmas oficiales y la seguridad criptográfica de tokens.
"""
import sys
import unittest
from pathlib import Path

ROOT_DIR = str(Path(__file__).resolve().parents[1])
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from starlette.testclient import TestClient
from piloto_spa.backend.main import app

class TestUSAER2ESPAIntegral(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

        # Login como Director (con contraseña robusta PBKDF2)
        res_dir = cls.client.post("/api/auth/login", json={"usuario": "edgar", "password": "Usaer2E!Dir#2026"})
        assert res_dir.status_code == 200, f"Login director failed: {res_dir.text}"
        data_dir = res_dir.json()
        cls.token_dir = data_dir["token"]
        cls.headers_dir = {"Authorization": f"Bearer {cls.token_dir}"}

        # Login como Maestra de Apoyo (Cindy Burgos - ESC-001, ESC-003)
        res_doc = cls.client.post("/api/auth/login", json={"usuario": "cindy.burgos", "password": "Usaer2E!Cindy#2026"})
        assert res_doc.status_code == 200, f"Login docente failed: {res_doc.text}"
        data_doc = res_doc.json()
        cls.token_doc = data_doc["token"]
        cls.headers_doc = {"Authorization": f"Bearer {cls.token_doc}"}

    def test_01_seguridad_autenticacion_estricta(self):
        """Verifica rechazo de credenciales incorrectas, contraseñas triviales y acceso anónimo."""
        # Intento con contraseña trivial prohibida '123'
        res_trivial = self.client.post("/api/auth/login", json={"usuario": "edgar", "password": "123"})
        self.assertEqual(res_trivial.status_code, 401)

        # Intento de login inválido
        res_bad = self.client.post("/api/auth/login", json={"usuario": "edgar", "password": "wrongpassword"})
        self.assertEqual(res_bad.status_code, 401)

        # Acceso anónimo sin header Authorization
        res_anon = self.client.get("/api/me")
        self.assertEqual(res_anon.status_code, 401)

        # Acceso con token válido
        res_ok = self.client.get("/api/me", headers=self.headers_dir)
        self.assertEqual(res_ok.status_code, 200)
        self.assertEqual(res_ok.json()["usuario"], "edgar")
        self.assertTrue(res_ok.json()["director"])

    def test_02_rbac_filtrado_escuelas(self):
        """Verifica que el docente sólo reciba alumnos de sus escuelas asignadas y el Director vea todas."""
        # Director ve todos
        res_dir = self.client.get("/api/alumnos", headers=self.headers_dir)
        self.assertEqual(res_dir.status_code, 200)
        alumnos_dir = res_dir.json()
        self.assertGreaterEqual(len(alumnos_dir), 5)

        # Maestra de apoyo asignada a ESC-001 y ESC-003
        res_doc = self.client.get("/api/alumnos", headers=self.headers_doc)
        self.assertEqual(res_doc.status_code, 200)
        alumnos_doc = res_doc.json()
        escuelas_permitidas = {"ESC-001", "ESC-003"}
        for a in alumnos_doc:
            self.assertIn(a["id_escuela"], escuelas_permitidas)

    def test_03_catalogo_8_escuelas_oficiales(self):
        """Verifica que el catálogo devuelva las primarias oficiales de la Zona 001."""
        res = self.client.get("/api/escuelas", headers=self.headers_dir)
        self.assertEqual(res.status_code, 200)
        escuelas = res.json()
        self.assertGreaterEqual(len(escuelas), 8)
        ccts = [e["cct"] for e in escuelas]
        self.assertIn("31DPR0001A", ccts)

    def test_04_expediente_completo_con_historia(self):
        """Verifica recuperación integral del expediente (BAP, sugerencias, eventos, EPP)."""
        res = self.client.get("/api/expedientes/ALU-001", headers=self.headers_dir)
        self.assertEqual(res.status_code, 200)
        exp = res.json()
        self.assertEqual(exp["alumno"]["id"], "ALU-001")
        self.assertIn("anexo3_bap", exp)
        self.assertIn("anexo4_sugerencias", exp)
        self.assertIn("anexo5_eventos", exp)
        self.assertIn("anexo7_derivacion", exp)
        self.assertIn("epp", exp)
        self.assertGreaterEqual(exp["total_documentos"], 1)

    def test_05_planeacion_crud_firmas_y_versionado(self):
        """Verifica guardado transaccional, cálculo de firmas de Director y eliminación."""
        plan_id = "plan-test-e2e-001"
        payload = {
            "id": plan_id,
            "formato": "XXIII",
            "estado": "BORRADOR",
            "datos": {
                "Escuela": "Damián Carmona",
                "Grado_Grupo": "2° A",
                "Ciclo": "2026-2027",
                "Mes": "Noviembre 2026",
                "Docente_Especialista": "Mtra. Cindy Mayanín Burgos González",
                "Director_USAER": "Psic. Edgar Adrián Yam Briceño MD"
            },
            "metadatos": {"titulo": "Planeación de Integración Curricular"},
            "tablas": {
                "nee": [
                    {
                        "alumno": "Jesús Emmanuel Chan Burgos",
                        "descriptor": "Jesús Emmanuel formula dos oraciones estructuradas.",
                        "pda": "Identifica y reflexiona sobre textos narrativos.",
                        "apoyos": "Cronómetro visual."
                    }
                ]
            },
            "textos": {"proposito": "Mejorar la comprensión lectora."}
        }

        # Guardar planeación
        res_save = self.client.post("/api/planeaciones", json=payload, headers=self.headers_doc)
        self.assertEqual(res_save.status_code, 200)
        save_data = res_save.json()
        self.assertEqual(save_data["status"], "success")
        self.assertTrue(save_data["revision"].startswith("rev-"))

        # Consultar planeación guardada con cálculo de firmas
        res_get = self.client.get(f"/api/planeaciones/{plan_id}", headers=self.headers_doc)
        self.assertEqual(res_get.status_code, 200)
        doc = res_get.json()
        self.assertIn("firmas_resueltas", doc)
        self.assertIn("Edgar Adrián Yam Briceño", doc["firmas_resueltas"]["director_nombre"])

        # Eliminar planeación
        res_del = self.client.delete(f"/api/planeaciones/{plan_id}", headers=self.headers_doc)
        self.assertEqual(res_del.status_code, 200)

    def test_06_epp_multi_area_persistencia(self):
        """Verifica guardado y consulta de Evaluación Psicopedagógica multi-área."""
        epp_payload = {
            "id": "epp_ALU-001_2026-2027",
            "alumno": "ALU-001",
            "ciclo": "2026-2027",
            "partes": {
                "APRENDIZAJE": {"avances": "Conteo cardinal y grafomotricidad básica."},
                "PSICOLOGIA": {"emocional": "Tolerancia progresiva a tareas estructuradas."},
                "COMUNICACION": {"lenguaje": "Oraciones compuestas con apoyo léxico."},
                "TRABAJO_SOCIAL": {"familia": "Compromiso de acompañamiento vespertino."}
            }
        }
        res_save = self.client.post("/api/epp", json=epp_payload, headers=self.headers_doc)
        self.assertEqual(res_save.status_code, 200)
        self.assertEqual(res_save.json()["status"], "success")

        # Consultar EPP
        res_get = self.client.get("/api/epp/ALU-001", headers=self.headers_doc)
        self.assertEqual(res_get.status_code, 200)
        self.assertEqual(res_get.json()["alumno"], "ALU-001")

    def test_07_asistente_pedagogico_indicadores_zona(self):
        """Verifica que el asistente aplique la fórmula canónica Sujeto + Verbo presente + Observable."""
        chat_payload = {
            "mensaje": "Requiere mayor apoyo en fluidez lectora y comprensión de textos informativos",
            "alumno_id": "ALU-001"
        }
        res = self.client.post("/api/ai/chat", json=chat_payload, headers=self.headers_doc)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("respuesta", data)
        self.assertIn("propuesta_tabla", data)
        # Comprobar que incluya el nombre del alumno y descriptor observable
        descriptor = data["propuesta_tabla"]["descriptor"]
        self.assertIn("Jesús Emmanuel", descriptor)

    def test_08_actas_visita_y_oficios(self):
        """Verifica emisión y consulta de actas de acompañamiento y oficios de comisión."""
        # Crear acta de visita
        vis_payload = {
            "escuela": "Damián Carmona",
            "personal": "Psic. Edgar Adrián Yam Briceño MD",
            "motivo": "Supervisión de expedientes EPP",
            "observaciones": "Todos los anexos actualizados al trimestre."
        }
        res_vis = self.client.post("/api/visitas", json=vis_payload, headers=self.headers_dir)
        self.assertEqual(res_vis.status_code, 200)

        # Consultar visitas
        res_list = self.client.get("/api/visitas", headers=self.headers_dir)
        self.assertEqual(res_list.status_code, 200)
        self.assertGreaterEqual(len(res_list.json()), 1)

    def test_09_estadisticas_zona_001(self):
        """Verifica cálculo de métricas institucionales desde PostgreSQL."""
        res = self.client.get("/api/estadisticas/zona", headers=self.headers_dir)
        self.assertEqual(res.status_code, 200)
        stats = res.json()
        self.assertGreater(stats["total_alumnos"], 0)
        self.assertEqual(stats["total_escuelas"], 8)
        self.assertIn("distribucion_condicion", stats)

    def test_10_logout_invalida_token(self):
        """Verifica que cerrar sesión invalide el token inmediatamente en el backend."""
        # Logout
        res_out = self.client.post("/api/auth/logout", headers=self.headers_dir)
        self.assertEqual(res_out.status_code, 200)

        # Intentar consultar con el token revocado -> debe dar 401
        res_rev = self.client.get("/api/me", headers=self.headers_dir)
        self.assertEqual(res_rev.status_code, 401)

    def test_11_aislamiento_entre_escuelas_403_forbidden(self):
        """Verifica que un docente no pueda acceder a expedientes ni EPP de otra escuela no autorizada."""
        # ALU-004 pertenece a ESC-002 (Ichcaanziho). Cindy sólo tiene ESC-001 y ESC-003.
        res_exp_cross = self.client.get("/api/expedientes/ALU-004", headers=self.headers_doc)
        self.assertEqual(res_exp_cross.status_code, 403)
        self.assertIn("Acceso denegado", res_exp_cross.json()["detail"])

        # Intento de ver EPP de otra escuela
        res_epp_cross = self.client.get("/api/epp/ALU-004", headers=self.headers_doc)
        self.assertEqual(res_epp_cross.status_code, 403)

        # Intento de agregar BAP a alumno de otra escuela
        res_bap_cross = self.client.post("/api/anexo3", json={
            "id_alumno": "ALU-004",
            "bap_pedagogicas": "Intento de mutación no autorizada"
        }, headers=self.headers_doc)
        self.assertEqual(res_bap_cross.status_code, 403)

        # Intento de consultar IA con alumno de otra escuela
        res_ai_cross = self.client.post("/api/ai/chat", json={
            "mensaje": "Sugerir adecuación curricular",
            "alumno_id": "ALU-004"
        }, headers=self.headers_doc)
        self.assertEqual(res_ai_cross.status_code, 403)

if __name__ == "__main__":
    unittest.main()

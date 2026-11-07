import sys
import unittest
from pathlib import Path

ROOT_DIR = str(Path(__file__).resolve().parents[1])
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from fastapi.testclient import TestClient
from piloto_spa.backend.main import app

class TestSeguridadConcurrenciaPlaneacion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        # Login Cindy (ESC-001)
        r_cindy = cls.client.post("/api/auth/login", json={"usuario": "cindy.burgos", "password": "Usaer2E*Carmona"})
        cls.cindy_token = r_cindy.json()["token"]
        cls.cindy_headers = {"Authorization": f"Bearer {cls.cindy_token}"}

        # Login Dolores (ESC-003)
        r_dolo = cls.client.post("/api/auth/login", json={"usuario": "dolores.cortazar", "password": "Usaer2E*Torres"})
        cls.dolo_token = r_dolo.json()["token"]
        cls.dolo_headers = {"Authorization": f"Bearer {cls.dolo_token}"}

        # Login Abril (Psicología - ESC-003, 004, 006, 007)
        r_abril = cls.client.post("/api/auth/login", json={"usuario": "abril.chable", "password": "Usaer2E*Psico2"})
        cls.abril_token = r_abril.json()["token"]
        cls.abril_headers = {"Authorization": f"Bearer {cls.abril_token}"}

        # Login Edgar (Director)
        r_edgar = cls.client.post("/api/auth/login", json={"usuario": "edgar", "password": "DirUsaer2E*2026"})
        cls.edgar_token = r_edgar.json()["token"]
        cls.edgar_headers = {"Authorization": f"Bearer {cls.edgar_token}"}

    def test_01_atajo_autenticacion_bloqueado(self):
        """Verifica que un token que contenga 'edgar' arbitrario ya NO conceda acceso de Dirección."""
        fake_tokens = [
            "edgar",
            "edgar-fake-token",
            "bearer edgar",
            "token_edgar_test",
            "malicious_edgar_token",
        ]
        for ft in fake_tokens:
            res = self.client.get("/api/planeaciones", headers={"Authorization": f"Bearer {ft}"})
            self.assertEqual(res.status_code, 401, f"El token {ft} no fue rechazado.")

    def test_02_rbac_planeaciones_alcance_estricto(self):
        """Cindy (ESC-001) NO debe poder abrir la planeación de Dolores (ESC-003)."""
        # Crear planeación para Dolores en ESC-003
        plan_dolo = {
            "id": "plan-privada-dolores-003",
            "cuenta": "dolores.cortazar",
            "formato": "XXIII",
            "datos": {
                "Escuela": "Gregorio Torres Quintero",
                "ID_Escuela": "ESC-003",
                "Docente_Especialista": "Mtra. Dolores Eugenia Cortázar Navarrete"
            },
            "metadatos": {"titulo": "Planeación Privada Dolores"},
            "tablas": {"nee": []},
            "textos": {}
        }
        res_crear = self.client.post("/api/planeaciones", json=plan_dolo, headers=self.dolo_headers)
        self.assertEqual(res_crear.status_code, 200)

        # Cindy intenta abrirla -> Debe ser 403 Forbidden
        res_cindy = self.client.get("/api/planeaciones/plan-privada-dolores-003", headers=self.cindy_headers)
        self.assertEqual(res_cindy.status_code, 403, "Cindy no debería tener acceso a la planeación de Dolores.")

        # Dolores puede abrirla -> 200 OK
        res_dolo_get = self.client.get("/api/planeaciones/plan-privada-dolores-003", headers=self.dolo_headers)
        self.assertEqual(res_dolo_get.status_code, 200)

        # Director puede abrirla -> 200 OK
        res_edgar_get = self.client.get("/api/planeaciones/plan-privada-dolores-003", headers=self.edgar_headers)
        self.assertEqual(res_edgar_get.status_code, 200)

    def test_03_control_concurrencia_optimista_revision(self):
        """Si un cliente envía una revisión desfasada, debe rechazarse con 409 Conflict."""
        # Abrir documento inicial de Dolores
        doc_ini = self.client.get("/api/planeaciones/plan-privada-dolores-003", headers=self.dolo_headers).json()
        rev_original = doc_ini["revision"]

        # Sesión 1 guarda y avanza la revisión
        doc_mod1 = dict(doc_ini)
        doc_mod1["metadatos"]["titulo"] = "Título Modificado por Sesión 1"
        res1 = self.client.post("/api/planeaciones", json=doc_mod1, headers=self.dolo_headers)
        self.assertEqual(res1.status_code, 200)
        nueva_rev = res1.json()["revision"]
        self.assertNotEqual(rev_original, nueva_rev)

        # Sesión 2 intenta guardar con la revisión desfasada (rev_original)
        doc_mod2 = dict(doc_ini)
        doc_mod2["revision"] = rev_original
        doc_mod2["metadatos"]["titulo"] = "Sobreescritura conflictiva por Sesión 2"
        res2 = self.client.post("/api/planeaciones", json=doc_mod2, headers=self.dolo_headers)
        self.assertEqual(res2.status_code, 409, "Debe rechazar guardado con revisión desfasada.")

    def test_04_aportacion_colaborativa_por_area(self):
        """Un especialista clínico (Abril - Psicología) puede aportar a su área sin conflicto."""
        # Abril aporta en Psicología a la planeación de ESC-003 (su escuela asignada)
        payload_aporte = {
            "id": "plan-privada-dolores-003",
            "aporte_area": {
                "area": "Psicología",
                "observaciones": "Se sugiere seguimiento en habilidades socioemocionales y autorregulación grupal.",
                "filas": [
                    {
                        "ID_Alumno": "ALU-001",
                        "Objetivo / qué trabajar": "Autorregulación emocional",
                        "Actividad / cómo trabajar": "Semáforo emocional en aula de apoyo",
                    }
                ]
            }
        }
        res_aporte = self.client.post("/api/planeaciones", json=payload_aporte, headers=self.abril_headers)
        self.assertEqual(res_aporte.status_code, 200)
        data = res_aporte.json()
        self.assertIn("Psicología", data["metadatos"]["aportaciones_equipo"])
        aporte_psic = data["metadatos"]["aportaciones_equipo"]["Psicología"]
        self.assertIn("socioemocionales", aporte_psic["observaciones"])
        self.assertEqual(aporte_psic["cuenta"], "abril.chable")

if __name__ == "__main__":
    unittest.main()

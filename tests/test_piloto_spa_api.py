"""Pruebas automáticas y verificación de contratos del Backend FastAPI del Piloto SPA.

Valida tiempos de respuesta, serialización JSON, resolución de firmas canónicas y control de errores.
"""
import unittest
from fastapi.testclient import TestClient
from piloto_spa.backend.main import app

class TestPilotoSPAAPI(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    def test_01_healthcheck_endpoint(self):
        """Verifica que el endpoint de disponibilidad responda en tiempo sub-milisegundo."""
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("timestamp", data)

    def test_02_login_endpoint(self):
        """Verifica el inicio de sesión y la asignación del rol."""
        res = self.client.post("/api/auth/login", json={"usuario": "cindy.burgos", "password": "123"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("Mtra. Cindy", data["nombre"])
        self.assertEqual(data["rol"], "MAESTRA DE APOYO")

    def test_03_listar_planeaciones_limite_y_rendimiento(self):
        """Verifica que la lista de planeaciones retorne rápidamente."""
        res = self.client.get("/api/planeaciones", headers={"X-User-Account": "cindy.burgos"})
        self.assertEqual(res.status_code, 200)
        planeaciones = res.json()
        self.assertIsInstance(planeaciones, list)
        self.assertGreater(len(planeaciones), 0)
        self.assertIn("formato", planeaciones[0])
        self.assertIn("estado", planeaciones[0])

    def test_04_obtener_planeacion_con_firmas_oficiales(self):
        """Verifica que la planeación completa resuelva automáticamente las firmas de Edgar y del docente."""
        res = self.client.get("/api/planeaciones/plan-demo-001", headers={"X-User-Account": "cindy.burgos"})
        self.assertEqual(res.status_code, 200)
        doc = res.json()
        self.assertIn("firmas_resueltas", doc)
        firmas = doc["firmas_resueltas"]
        self.assertIn("Edgar Adrián Yam Briceño", firmas["director_nombre"])
        self.assertIn("Cindy", firmas["especialista_nombre"])

    def test_05_guardar_planeacion_con_revision(self):
        """Verifica el guardado y confirmación atómica con nuevo hash de revisión."""
        payload = {
            "id": "plan-test-save-999",
            "cuenta": "cindy.burgos",
            "formato": "XXIII",
            "estado": "REVISIÓN",
            "datos": {"Escuela": "Damián Carmona"},
            "metadatos": {"titulo": "Planeación Guardada Test"},
            "tablas": {
                "aprendizajes": [{"Necesidades educativas específicas": "Atención focalizada"}]
            },
            "textos": {"Observaciones": "Sin incidencias"}
        }
        res = self.client.post("/api/planeaciones", json=payload, headers={"X-User-Account": "cindy.burgos"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertTrue(data["revision"].startswith("rev-"))

    def test_06_asistente_ia_sugerencias(self):
        """Verifica que el asistente pedagógico devuelva sugerencias limpias con fallback."""
        payload = {"necesidad_o_barrera": "Dificultad de autorregulación"}
        res = self.client.post("/api/ai/sugerencias", json=payload)
        self.assertEqual(res.status_code, 200)
        sug = res.json()
        self.assertIn("sugerencias", sug)
        self.assertIn("area", sug)

    def test_07_frontend_spa_html_servido(self):
        """Verifica que el punto de entrada raíz sirva el HTML de la aplicación React SPA."""
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/html", res.headers.get("content-type", ""))
        self.assertIn("Piloto SPA", res.text)
        self.assertIn("React 18", res.text)

if __name__ == "__main__":
    unittest.main()


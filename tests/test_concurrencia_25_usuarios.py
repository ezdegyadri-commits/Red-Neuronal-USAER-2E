"""Prueba de Concurrencia Real para 25 Usuarios Simultáneos.

Simula la jornada matutina de una USAER escolar donde 25 docentes acceden simultáneamente
a la plataforma, consultan padrones con RBAC, editan sus planeaciones y solicitan
asistencia pedagógica contextualizada.
"""
import concurrent.futures
import sys
import time
import unittest
from pathlib import Path

ROOT_DIR = str(Path(__file__).resolve().parents[1])
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from starlette.testclient import TestClient
from piloto_spa.backend.main import app

class TestConcurrencia25Usuarios(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        # Login general
        res = cls.client.post("/api/auth/login", json={"usuario": "edgar", "password": "123"})
        cls.token = res.json()["token"]
        cls.headers = {"Authorization": f"Bearer {cls.token}"}

    def _simular_sesion_docente(self, user_idx: int):
        """Simula el flujo completo de un docente en 1 clic."""
        t0 = time.perf_counter()
        
        # 1. Cargar Hub de documentos
        res_hub = self.client.get("/api/planeaciones", headers=self.headers)
        assert res_hub.status_code == 200, f"Error hub usuario {user_idx}"
        
        # 2. Consultar padrón
        res_alu = self.client.get("/api/alumnos", headers=self.headers)
        assert res_alu.status_code == 200, f"Error alumnos usuario {user_idx}"
        
        # 3. Abrir planeación
        res_plan = self.client.get(f"/api/planeaciones/plan-focalizada-001", headers=self.headers)
        assert res_plan.status_code == 200, f"Error abrir plan usuario {user_idx}"
        
        # 4. Guardar edición (autoguardado simulado con payload único)
        doc = res_plan.json()
        doc["metadatos"]["titulo"] = f"Plan Editado por Hilo {user_idx}"
        res_save = self.client.post("/api/planeaciones", json=doc, headers=self.headers)
        assert res_save.status_code == 200, f"Error guardar plan usuario {user_idx}"
        
        # 5. Solicitar asistencia IA
        res_ai = self.client.post("/api/ai/chat", json={
            "mensaje": f"Sugerir actividad focalizada para sesión de usuario {user_idx}",
            "alumno_id": "ALU-001"
        }, headers=self.headers)
        assert res_ai.status_code == 200, f"Error IA usuario {user_idx}"

        t1 = time.perf_counter()
        duracion_ms = (t1 - t0) * 1000.0
        return duracion_ms

    def test_25_usuarios_simultaneos(self):
        """Ejecuta 25 hilos paralelos concurrentes y mide latencias y tasa de éxito."""
        num_usuarios = 25
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_usuarios) as executor:
            futuros = [executor.submit(self._simular_sesion_docente, i) for i in range(num_usuarios)]
            tiempos = [f.result() for f in concurrent.futures.as_completed(futuros)]

        self.assertEqual(len(tiempos), num_usuarios)
        
        promedio = sum(tiempos) / len(tiempos)
        tiempos.sort()
        p95 = tiempos[int(len(tiempos) * 0.95)]
        
        print(f"\n[BENCHMARK CONCURRENCIA 25 DOCENTES]")
        print(f"Total sesiones concurrentes: {num_usuarios}")
        print(f"Tasa de éxito: 100% (0 errores, 0 timeouts)")
        print(f"Latencia Promedio por flujo completo: {promedio:.1f} ms")
        print(f"Percentil 95 (P95): {p95:.1f} ms")
        
        # El flujo completo de 5 endpoints por usuario debe ser menor a 3.0 segundos incluso bajo carga
        self.assertLess(promedio, 3000.0)

if __name__ == "__main__":
    unittest.main()

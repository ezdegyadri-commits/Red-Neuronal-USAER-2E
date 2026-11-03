"""Prueba de rendimiento y verificación de tiempos de respuesta (QA Performance Test).

Verifica que el tiempo para cargar el padrón de alumnos, catálogos estáticos,
'Mis Planeaciones' y el informe EPP sea estrictamente menor a 2.0 segundos.
"""
import time
import unittest
from unittest.mock import patch
import pandas as pd

from tests.test_planeacion_panel import ACTOR, ALUMNO
from data.google import ensure_headers, append_dict, df_sheet


class TestPerformanceQA(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Garantizar que las hojas maestras existan en el backend local (SQLite/PG)
        try:
            ensure_headers('Alumnos', list(ALUMNO.keys()))
            if df_sheet('Alumnos').empty:
                append_dict('Alumnos', ALUMNO)
            
            ensure_headers('Escuelas', ['CCT', 'Nombre_Escuela', 'Turno'])
            if df_sheet('Escuelas').empty:
                append_dict('Escuelas', {'CCT': '14DPR1234A', 'Nombre_Escuela': 'Escuela Primaria', 'Turno': 'Matutino'})
            
            ensure_headers('Personal', ['ID', 'Nombre', 'Funcion', 'Correo'])
            if df_sheet('Personal').empty:
                append_dict('Personal', {'ID': '1', 'Nombre': 'Docente Test', 'Funcion': 'Maestra de Apoyo', 'Correo': 'test@usaer.edu.mx'})
        except Exception:
            pass

    def setUp(self):
        import data.repository as repo
        self.repo = repo
        self.padron_mock = pd.DataFrame([ALUMNO])

    def test_01_padron_y_catalogos_cache_performance(self):
        """Verifica que la consulta del padrón y catálogos con caché ttl=3600 responda en < 0.5s."""
        # Warmup inicial
        _ = self.repo.escuelas()
        _ = self.repo.alumnos()
        _ = self.repo.personal()

        inicio = time.perf_counter()
        escuelas = self.repo.escuelas()
        alumnos = self.repo.alumnos()
        personal = self.repo.personal()
        duracion = time.perf_counter() - inicio

        print(f"\n[QA PERF] Padrón y catálogos estáticos cargados en: {duracion*1000:.2f} ms")
        self.assertLess(duracion, 0.5, f"La carga del padrón y catálogos tardó {duracion:.2f}s, superando el límite de 0.5s")
        self.assertIsInstance(escuelas, pd.DataFrame)
        self.assertIsInstance(alumnos, pd.DataFrame)

    def test_02_mis_planeaciones_performance(self):
        """Verifica que la carga resumida de 'Mis Planeaciones' responda en < 2.0 segundos."""
        from services import planeacion as s

        with patch.object(s, 'identidad', return_value=ACTOR), \
             patch.object(s, 'padron_autorizado', return_value=self.padron_mock):
            inicio = time.perf_counter()
            planeaciones = s.listar()
            duracion = time.perf_counter() - inicio

        print(f"[QA PERF] 'Mis Planeaciones' cargadas en: {duracion*1000:.2f} ms")
        self.assertLess(duracion, 2.0, f"La carga de Mis Planeaciones tardó {duracion:.2f}s, superando el límite de 2.0s")
        self.assertIsInstance(planeaciones, list)

    def test_03_epp_listar_performance(self):
        """Verifica que la consulta de informes EPP responda en < 2.0 segundos."""
        from services import epp, planeacion as planes

        with patch.object(epp, 'actor', return_value=ACTOR), \
             patch.object(planes, 'identidad', return_value=ACTOR), \
             patch.object(planes, 'padron_autorizado', return_value=self.padron_mock):
            inicio = time.perf_counter()
            informes = epp.listar()
            duracion = time.perf_counter() - inicio

        print(f"[QA PERF] Informes EPP cargados en: {duracion*1000:.2f} ms")
        self.assertLess(duracion, 2.0, f"La carga de EPP tardó {duracion:.2f}s, superando el límite de 2.0s")
        self.assertIsInstance(informes, list)

    def test_04_benchmark_completo_inferior_a_dos_segundos(self):
        """Benchmark integral: Carga conjunta de padrón + Mis Planeaciones + EPP < 2.0s."""
        from services import planeacion as s, epp

        with patch.object(s, 'identidad', return_value=ACTOR), \
             patch.object(epp, 'actor', return_value=ACTOR), \
             patch.object(s, 'padron_autorizado', return_value=self.padron_mock):
            inicio = time.perf_counter()
            _ = self.repo.alumnos()
            _ = self.repo.escuelas()
            planeaciones = s.listar()
            informes = epp.listar()
            duracion = time.perf_counter() - inicio

        print(f"[QA PERF] Flujo completo (Catálogos + Planeaciones + EPP) ejecutado en: {duracion*1000:.2f} ms")
        self.assertLess(duracion, 2.0, f"El flujo completo tardó {duracion:.2f}s (debe ser < 2.0s)")


if __name__ == '__main__':
    unittest.main()

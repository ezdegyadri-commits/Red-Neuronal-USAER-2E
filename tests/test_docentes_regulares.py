"""Pruebas unitarias para el registro de docentes regulares de las 7 escuelas primarias."""
import tempfile
import os
from unittest import TestCase
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from services import docentes_regulares
from services.docentes_regulares import (
    ESCUELAS_PRIMARIAS,
    GRADOS,
    GRUPOS,
    registrar_docente_regular,
    registrar_lote_docentes,
    listar_docentes_regulares,
    resumen_cobertura_escuelas,
)


class DocentesRegularesTests(TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        self.tmp.write(b"[]")
        self.tmp.close()
        self.patcher = patch.object(docentes_regulares, "_LOCAL_BACKUP_PATH", self.tmp.name)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        if os.path.exists(self.tmp.name):
            os.remove(self.tmp.name)

    def test_las_siete_escuelas_primarias_exactas(self):
        self.assertEqual(len(ESCUELAS_PRIMARIAS), 7)
        esperadas = {
            "Damián Carmona",
            "Ichcaanziho",
            "Gregorio Torres Quintero",
            "Remigio Aguilar Sosa",
            "Elvira Parra Ávila",
            "Manuel Sarrado",
            "Domingo Solís Rodríguez",
        }
        self.assertEqual(set(ESCUELAS_PRIMARIAS), esperadas)

    def test_valida_campos_obligatorios(self):
        with self.assertRaises(ValueError):
            registrar_docente_regular("", "1°", "A", "Juan Pérez")
        with self.assertRaises(ValueError):
            registrar_docente_regular("Damián Carmona", "", "A", "Juan Pérez")
        with self.assertRaises(ValueError):
            registrar_docente_regular("Damián Carmona", "1°", "", "Juan Pérez")
        with self.assertRaises(ValueError):
            registrar_docente_regular("Damián Carmona", "1°", "A", "")

    def test_guarda_y_recupera_docente(self):
        doc = registrar_docente_regular(
            escuela="Damián Carmona",
            grado="3°",
            grupo="B",
            nombre_docente="Mtra. Carmen Rodríguez",
            turno="Matutino",
            telefono="9991234567",
        )
        self.assertTrue(doc["ID_Registro"].startswith("DOC-"))
        self.assertEqual(doc["Nombre_Escuela"], "Damián Carmona")
        self.assertEqual(doc["Grado"], "3°")
        self.assertEqual(doc["Grupo"], "B")

        todos = listar_docentes_regulares(escuela="Damián Carmona")
        encontrado = next(
            (d for d in todos if d.get("Nombre_Docente") == "Mtra. Carmen Rodríguez" and d.get("Grado") == "3°" and d.get("Grupo") == "B"),
            None,
        )
        self.assertIsNotNone(encontrado)

    def test_lote_plantilla_y_cobertura(self):
        plantilla = [
            {"Grado": "1°", "Grupo": "A", "Nombre_Docente": "Mtra. Ana María"},
            {"Grado": "2°", "Grupo": "A", "Nombre_Docente": "Mtro. Roberto Carlos"},
        ]
        guardados = registrar_lote_docentes("Manuel Sarrado", "Matutino", plantilla)
        self.assertEqual(len(guardados), 2)

        cobertura = resumen_cobertura_escuelas()
        self.assertEqual(len(cobertura), 7)
        res_sarrado = next(c for c in cobertura if c["Escuela"] == "Manuel Sarrado")
        self.assertGreaterEqual(res_sarrado["Docentes_Registrados"], 2)


class AppPublicaTests(TestCase):
    def test_formulario_publico_sin_login(self):
        from pathlib import Path
        app_path = str(Path(__file__).parents[1] / "app.py")
        app = AppTest.from_file(app_path, default_timeout=30)
        app.query_params["p"] = "docentes"
        app.run()
        self.assertFalse(app.exception)
        self.assertTrue(any("Maestros de Grupo de Primaria" in str(m.value) for m in app.markdown))
        botones = [b for b in app.button if "Guardar" in b.label]
        self.assertTrue(len(botones) >= 1)

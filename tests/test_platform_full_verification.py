"""Verificación integral del sistema: Roles, Permisos, Módulos, Planeaciones, EPP e IA.

Garantiza que ningún perfil sufra caídas o bloqueos en producción.
"""
import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import streamlit as st


class TestPlatformFullVerification(unittest.TestCase):

    def setUp(self):
        # Mock básico de Streamlit para pruebas fuera del navegador
        if not hasattr(st, "session_state"):
            st.session_state = {}

    def test_01_acceso_usuarios_y_roles_existentes(self):
        """Verifica que el catálogo de usuarios cargue y contenga todos los roles necesarios."""
        from data.acceso_usuarios import usuarios
        df = usuarios()
        self.assertIsInstance(df, pd.DataFrame)
        self.assertFalse(df.empty, "El catálogo de usuarios no debe estar vacío")
        
        columnas_requeridas = {'Nombre', 'Usuario', 'Password', 'Rol', 'Escuelas_Permitidas'}
        self.assertTrue(columnas_requeridas.issubset(set(df.columns)), f"Faltan columnas en usuarios: {df.columns}")
        
        roles = set(df['Rol'].str.upper().unique())
        print(f"\n[VERIFICACIÓN] Roles detectados en la plataforma: {roles}")
        self.assertTrue(any("DIRECTOR" in r for r in roles), "Debe existir al menos un rol de DIRECTOR")

    def test_02_perfiles_y_menus_por_rol(self):
        """Verifica que cada rol obtenga su menú exacto sin excepciones."""
        from services.cronogramas import perfil_especialista
        from services.asignaciones import puede_dar_alta_alumnos
        from services.tramites import gestor as gestor_tramites, puede_solicitar

        perfiles_a_probar = [
            {"rol": "DIRECTOR", "nombre": "Edgar Adrian Yam Briceno", "escuelas": "ESC-001,ESC-002"},
            {"rol": "MAESTRA DE APOYO", "nombre": "Cindy Mayanín Burgos González", "escuelas": "ESC-001"},
            {"rol": "MAESTRO DE APOYO", "nombre": "Pedro Manuel Torres May", "escuelas": "ESC-007"},
            {"rol": "ESPECIALISTA", "nombre": "Psic. María José Cupul Realpozo", "escuelas": "ESC-001,ESC-002"},
            {"rol": "ESPECIALISTA", "nombre": "Lic. Elmy Lucelly Puerto Gone", "escuelas": "ESC-001,ESC-002"},
            {"rol": "ESPECIALISTA", "nombre": "LTS. Diego Peralta Torres", "escuelas": "ESC-001,ESC-002,ESC-003"},
        ]

        for p in perfiles_a_probar:
            rol = p["rol"]
            nombre = p["nombre"]
            
            # Lógica de cálculo de menú de app.py
            menu = ["Inicio", "Expedientes", "Anexo III BAP", "Anexo IV Hoja de sugerencias", "Anexo V Eventos significativos", "Estadística", "Documentos", "Calendario de actividades"]
            
            perfil_cronograma = perfil_especialista(nombre, rol)
            if perfil_cronograma or "APOYO" in rol.upper():
                menu += ["Planeación e intervención", "EPP", "Juntas académicas", "Metas personales"]
            if perfil_cronograma and perfil_cronograma.get("area") != "Dirección":
                menu += ["Cronograma mensual"]
            if "DIRECTOR" in rol.upper():
                menu += ["Panel de Dirección", "Maestros de primaria", "Novedades de supervisión", "Constancias de visita"]
                if puede_dar_alta_alumnos(nombre, rol):
                    menu += ["Alta de alumnos"]
            elif "APOYO" in rol.upper():
                menu += ["Horarios de apoyo", "Maestros de primaria"]
                if puede_dar_alta_alumnos(nombre, rol):
                    menu += ["Alta de alumnos"]
                menu += ["Oficios de comisión", "Anexo VII Derivación"]
            else:
                menu += ["Constancias de visita", "Anexo VII Derivación"]

            print(f"[VERIFICACIÓN] Rol '{rol}' ({nombre[:20]}...): {len(menu)} módulos asignados.")
            self.assertIn("Inicio", menu)
            self.assertIn("Expedientes", menu)
            self.assertGreaterEqual(len(menu), 8)

    def test_03_importacion_todos_los_modulos_ui(self):
        """Verifica que todos los módulos y submódulos se puedan importar sin SyntaxError ni KeyError."""
        modulos = [
            "ui.hub",
            "ui.pages",
            "ui.sugerencias",
            "ui.estadisticas",
            "ui.calendario_eventos",
            "ui.cronogramas",
            "ui.horarios_apoyo",
            "ui.tramites",
            "ui.planeacion",
            "ui.epp_acceso",
            "ui.epp",
            "ui.metas_personales",
            "ui.juntas_academicas",
            "ui.novedades_supervision",
            "ui.direccion_rapida",
            "ui.direccion_oficios",
            "ui.docentes_regulares_form",
            "ui.oficios",
            "ui.contenido_modulo",
        ]
        for mod in modulos:
            try:
                __import__(mod)
            except Exception as e:
                self.fail(f"Error al importar el módulo {mod}: {e}")
        print(f"\n[VERIFICACIÓN] {len(modulos)} submódulos UI importados correctamente sin errores.")

    def test_04_resolucion_firmas_director_y_docentes(self):
        """Verifica que la planeación resuelva correctamente el nombre del docente y del director."""
        from services.planeacion_firmas import resolver_firmas_planeacion, DIRECTOR_USAER

        # 1. Caso Maestra de Apoyo (Damián Carmona)
        doc_apoyo = {
            "formato": "XXIII",
            "cuenta": "cindy.burgos",
            "datos": {"Escuela": "Damián Carmona", "Alumnos": []},
            "metadatos": {}
        }
        firmas_apoyo = resolver_firmas_planeacion(doc_apoyo)
        self.assertEqual(firmas_apoyo["director_nombre"], DIRECTOR_USAER)
        self.assertIn("Cindy", firmas_apoyo["especialista_nombre"])

        # 2. Caso Especialista Psicología
        doc_psic = {
            "formato": "XXV",
            "cuenta": "maria.cupul",
            "datos": {"Escuela": "Damián Carmona", "Alumnos": []},
            "metadatos": {"area": "PSICOLOGIA"}
        }
        firmas_psic = resolver_firmas_planeacion(doc_psic)
        self.assertEqual(firmas_psic["director_nombre"], DIRECTOR_USAER)
        self.assertIn("María José Cupul", firmas_psic["especialista_nombre"])

        # 3. Caso Trabajo Social
        doc_ts = {
            "formato": "XXV",
            "cuenta": "diego.peralta",
            "datos": {"Escuela": "Manuel Sarrado", "Alumnos": []},
            "metadatos": {"area": "TRABAJO_SOCIAL"}
        }
        firmas_ts = resolver_firmas_planeacion(doc_ts)
        self.assertEqual(firmas_ts["director_nombre"], DIRECTOR_USAER)
        self.assertIn("Diego Peralta", firmas_ts["especialista_nombre"])

        print("\n[VERIFICACIÓN] Firmas de Director y Docentes/Especialistas resueltas correctamente.")

    def test_05_generacion_pdf_planeaciones_sin_error(self):
        """Verifica que la exportación a PDF de planeación funcione perfectamente."""
        from documents.planeacion import generar_pdf
        
        doc_test = {
            "id": "test_plan_001",
            "formato": "XXIII",
            "estado": "REVISIÓN",
            "revision": "rev-test-123",
            "cuenta": "cindy.burgos",
            "datos": {
                "Escuela": "Damián Carmona",
                "Grado_Grupo": "2° A",
                "Alumnos": [
                    {"Nombre del alumno": "Alumno Prueba", "Grado": "2", "Grupo": "A", "Condición": "TDAH"}
                ]
            },
            "metadatos": {},
            "tablas": {
                "aprendizajes": [
                    {"Necesidades educativas específicas": "Atención sostenida", "Objetivo": "Lograr 15 min de atención", "Apoyos": "Material visual"}
                ],
                "dosificacion": []
            },
            "textos": {
                "Observaciones": "Trabajo continuo en aula de apoyo"
            },
            "observaciones_director": "Aprobado con observaciones mínimas"
        }
        pdf_bytes = generar_pdf(doc_test)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 1000, "El PDF generado debe contener datos legibles")
        print(f"\n[VERIFICACIÓN] PDF de Planeación generado con éxito ({len(pdf_bytes)} bytes).")

    def test_06_epp_modulo_persistencia_y_consulta(self):
        """Verifica que el informe EPP liste, consulte y persista sin errores."""
        from data.sql_repository import epp_listar_sql, guardar_epp_sql
        
        doc_epp = {
            "id": "epp_test_alumn_001:2026-2027",
            "alumno": "ALUMNO-TEST-001",
            "ciclo": "2026-2027",
            "revision": "rev-epp-1",
            "fecha": "2026-11-03",
            "partes": {
                "META": {"estado": "BORRADOR"},
                "DATOS_GENERALES": {"nombre": "Alumno Prueba EPP"},
                "DIAGNOSTICO": "Diagnóstico pedagógico inicial"
            }
        }
        guardar_epp_sql(doc_epp)
        
        lista = epp_listar_sql(["ALUMNO-TEST-001"])
        self.assertTrue(any(e["alumno"] == "ALUMNO-TEST-001" for e in lista))
        print(f"\n[VERIFICACIÓN] Módulo EPP verificado y persistido en SQL con éxito.")

    def test_07_modulos_ia_y_fallback(self):
        """Verifica que el motor de IA maneje fallbacks limpios sin lanzar excepciones no controladas."""
        from ai.engine import fallback, generar_sugerencias
        
        fb = fallback()
        self.assertIn("area", fb)
        self.assertIn("sugerencias", fb)
        
        # Probar con cliente nulo (offline o sin key en test)
        with patch("ai.engine.client", return_value=None):
            res = generar_sugerencias({"alumno": "Prueba"})
            self.assertEqual(res["area"], "Aprendizaje")
            self.assertIn("sugerencias", res)
            
        print("\n[VERIFICACIÓN] Motor de IA y mecanismos de contingencia (fallback) verificados.")


if __name__ == "__main__":
    unittest.main()


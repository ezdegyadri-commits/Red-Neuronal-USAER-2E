import unittest
from unittest.mock import patch

from services import planeacion_firmas as pf
from services import planeacion_papel as papel
from documents import planeacion_papel as pdf_papel
from documents import planeacion as pdf_clasico


def doc_prueba(formato="XXIII", escuela="Damián Carmona", funcion="Aprendizaje", autor=""):
    return {
        "id": f"plan-test-{formato}-{escuela}",
        "formato": formato,
        "estado": "BORRADOR",
        "datos": {
            "Servicio de apoyo": "USAER 02E",
            "Zona": "01",
            "ID_Escuela": escuela,
            "Escuela regular": escuela,
            "CCT": "31EPR0001A",
            "Curso escolar": "2026-2027",
            "Fecha de elaboración": "2026-10-28",
            "Nombre del especialista": autor,
            "Función": funcion,
            "Trimestre": 1,
            "Periodo": "2026-10-01 / 2026-12-31",
            "Alumnos": [
                {
                    "ID_Alumno": "ALU-100",
                    "Nombre del alumno": "Alumno Prueba",
                    "Grado": "3",
                    "Grupo": "A",
                    "Condición": "Discapacidad intelectual",
                }
            ],
        },
        "tablas": {"aprendizajes": [], "dosificacion": [], "barreras": []},
        "textos": {},
        "metadatos": {},
    }


class TestPlaneacionFirmas(unittest.TestCase):
    def test_firmas_director_siempre_presente(self):
        doc = doc_prueba("XXIII", "Damián Carmona", "Aprendizaje")
        firmas = pf.resolver_firmas_planeacion(doc)
        self.assertEqual(firmas["director_nombre"], "Psic. Edgar Adrián Yam Briceño MD")
        self.assertEqual(firmas["director_cargo"], "Vo. Bo. Director del Servicio de Apoyo")
        self.assertIn("Psic. Edgar Adrián Yam Briceño MD", firmas["vobo"])
        self.assertIn("Vo. Bo. Director del Servicio de Apoyo", firmas["vobo"])

    def test_firmas_trabajo_social_formato_xxv(self):
        doc = doc_prueba("XXV", "Remigio Aguilar Sosa", "Trabajo Social")
        firmas = pf.resolver_firmas_planeacion(doc)
        self.assertEqual(firmas["especialista_nombre"], "LTS. Diego Peralta Torres")
        self.assertEqual(firmas["especialista_cargo"], "Trabajo Social")
        self.assertIn("LTS. Diego Peralta Torres", firmas["firma"])

    def test_firmas_psicologia_segun_zona_escolar(self):
        # Zona 1: Damián Carmona -> María José Cupul
        doc1 = doc_prueba("XXIII", "Damián Carmona", "Psicología")
        firmas1 = pf.resolver_firmas_planeacion(doc1)
        self.assertEqual(firmas1["especialista_nombre"], "Psic. María José Cupul Realpozo")
        self.assertEqual(firmas1["especialista_cargo"], "Área de Psicología")

        # Zona 2: Remigio Aguilar Sosa -> Abril de María Chable
        doc2 = doc_prueba("XXIII", "Remigio Aguilar Sosa", "Psicología")
        firmas2 = pf.resolver_firmas_planeacion(doc2)
        self.assertEqual(firmas2["especialista_nombre"], "Psic. Abril de María Chable Ríos")
        self.assertEqual(firmas2["especialista_cargo"], "Área de Psicología")

    def test_firmas_comunicacion_segun_zona_escolar(self):
        # Zona 1: Elvira Parra Ávila -> Elmy Lucelly Puerto
        doc1 = doc_prueba("XXIII", "Elvira Parra Ávila", "Comunicación")
        firmas1 = pf.resolver_firmas_planeacion(doc1)
        self.assertEqual(firmas1["especialista_nombre"], "Lic. Elmy Lucelly Puerto Gone")
        self.assertEqual(firmas1["especialista_cargo"], "Área de Comunicación")

        # Zona 2: Gregorio Torres Quintero -> Marilyn Pérez Lizama
        doc2 = doc_prueba("XXIII", "Gregorio Torres Quintero", "Comunicación")
        firmas2 = pf.resolver_firmas_planeacion(doc2)
        self.assertEqual(firmas2["especialista_nombre"], "Lic. Marilyn Pérez Lizama")
        self.assertEqual(firmas2["especialista_cargo"], "Área de Comunicación")

    def test_firmas_maestras_de_apoyo_por_escuela(self):
        maestras_esperadas = {
            "Damián Carmona": "Mtra. Cindy Mayanín Burgos González",
            "Ichcaanziho": "Mtra. Marycruz Caamal Coral",
            "Gregorio Torres Quintero": "Mtra. Dolores Eugenia Cortázar Navarrete",
            "Remigio Aguilar Sosa": "Mtra. Dianely de Sugeidy Caamal Tamay",
            "Elvira Parra Ávila": "Mtro. Luis Jorge García Herrera",
            "Manuel Sarrado": "Mtra. María del Rosario Pérez Vitorin",
            "Domingo Solís Rodríguez": "Mtra. Zuemmy del Carmen Pérez Basto",
            "Quintana Roo": "Mtro. Pedro Manuel Torres May",
        }
        for escuela, maestra in maestras_esperadas.items():
            doc = doc_prueba("XXIII", escuela, "Aprendizaje")
            firmas = pf.resolver_firmas_planeacion(doc)
            self.assertEqual(firmas["especialista_nombre"], maestra, f"Fallo en escuela {escuela}")
            self.assertIn(firmas["especialista_cargo"], ("Maestra de Apoyo", "Maestro de Apoyo"))

    def test_autor_especifico_reconocido_y_director_no_se_duplica(self):
        # Si la docente es Cecilia Solís en Ichcaanziho
        doc_cecy = doc_prueba("XXIII", "Ichcaanziho", "Aprendizaje", autor="Cecilia Solís")
        firmas_cecy = pf.resolver_firmas_planeacion(doc_cecy)
        self.assertEqual(firmas_cecy["especialista_nombre"], "Mtra. María Cecilia Solís Vázquez")

        # Si el director inició sesión o guardó la planeación en Remigio Aguilar Sosa,
        # la firma de especialista no debe ser el director duplicado, sino la maestra asignada.
        doc_dir = doc_prueba("XXIII", "Remigio Aguilar Sosa", "Aprendizaje", autor="Psic. Edgar Adrián Yam Briceño MD")
        firmas_dir = pf.resolver_firmas_planeacion(doc_dir)
        self.assertEqual(firmas_dir["especialista_nombre"], "Mtra. Dianely de Sugeidy Caamal Tamay")
        self.assertEqual(firmas_dir["director_nombre"], "Psic. Edgar Adrián Yam Briceño MD")

    def test_integracion_hoja_papel_y_pdf(self):
        doc = doc_prueba("XXIII", "Remigio Aguilar Sosa", "Aprendizaje")
        with patch("services.planeacion.autorizar", return_value={"cuenta": "test", "area": "Aprendizaje", "escuelas": ["Remigio Aguilar Sosa"], "es_director": False, "es_colaborador": False}):
            spec = papel.hoja(doc)
            self.assertIn("Mtra. Dianely de Sugeidy Caamal Tamay", spec["firma"])
            self.assertIn("Maestra de Apoyo", spec["firma"])
            self.assertIn("Psic. Edgar Adrián Yam Briceño MD", spec["vobo"])
            self.assertIn("Vo. Bo. Director del Servicio de Apoyo", spec["vobo"])

            # Generación de PDF papel
            pdf_bytes = pdf_papel.generar_pdf(doc)
            self.assertIsInstance(pdf_bytes, (bytes, bytearray))
            self.assertGreater(len(pdf_bytes), 1000)

            # Generación de PDF clásico
            pdf_clasico_bytes = pdf_clasico.generar_pdf(doc)
            self.assertIsInstance(pdf_clasico_bytes, (bytes, bytearray))
            self.assertGreater(len(pdf_clasico_bytes), 1000)


if __name__ == "__main__":
    unittest.main()

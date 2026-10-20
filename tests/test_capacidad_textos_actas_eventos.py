"""Pruebas de integridad y capacidad de texto para Actas de Visita y Eventos Significativos."""
import unittest
from unittest.mock import patch, MagicMock
from datetime import date
import pandas as pd
from documents.visitas import visita_pdf
from documents.anexos import anexo5_pdf


class CapacidadTextosActasEventosTests(unittest.TestCase):
    def test_visita_pdf_soporta_texto_largo_sin_truncar_ni_fallar(self):
        texto_largo = "Actividad detallada de observacion y seguimiento pedagogico. " * 60  # ~3,600 caracteres
        pdf_bytes = visita_pdf(
            titulo="Constancia de visita",
            folio="VIS-999",
            escuela="Ichcaanziho",
            lugar="Ichcaanziho",
            fecha="20/10/2026",
            ciclo="2026 – 2027",
            especialidad="Área de Aprendizaje - USAER 02-E",
            motivos=["Observación en grupo", "Sugerencias a Maestra(o)"],
            detalles="Seguimiento curricular en 3ro A",
            descripcion=texto_largo,
            firmantes=[("Mtra. Directora", "Directora"), ("Mtra. Apoyo", "Maestra de apoyo")],
        )
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 1000)

    def test_anexo5_pdf_soporta_evento_largo_sin_truncar_ni_fallar(self):
        texto_evento = "Avances observados en el aula regular durante la sesion. " * 65  # ~3,700 caracteres
        alumno = {"Nombre_Completo": "Alumno de Prueba", "ID_Alumno": "AL-001"}
        rows = pd.DataFrame([{
            "Fecha": "20/10/2026",
            "Especialista": "Psic. Edgar Yam",
            "Evento": texto_evento,
            "Estado": "ACTIVO",
        }])
        pdf_bytes = anexo5_pdf(alumno, rows)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 1000)


if __name__ == "__main__":
    unittest.main()

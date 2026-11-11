import base64
from io import BytesIO
import os
import secrets
import unittest

from fastapi.testclient import TestClient

from data.database import Alumno, Base, Escuela, Usuario, get_engine, get_session
from data.sql_repository import guardar_planeacion_sql
from piloto_spa.backend.auth_service import hash_password
from piloto_spa.backend.main import app


class EppYPlaneacion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.environ.get("DATABASE_URL") != (
            "postgresql+psycopg2://usaer_qa@127.0.0.1:55491/usaer_epp_noviembre_qa"
        ):
            raise RuntimeError("La prueba solo admite la base local desechable usaer_epp_noviembre_qa.")
        engine = get_engine(initialize_schema=False)
        Base.metadata.create_all(engine)
        with get_session() as db:
            if db.query(Alumno).count() or db.query(Usuario).count():
                raise RuntimeError("Usa una base desechable vacía.")
            for i in (1, 2):
                db.add(Escuela(id=f"ESC-QA{i}", nombre_escuela=f"Escuela ficticia {i}"))
                db.add(Alumno(id=f"ALU-QA{i}", nombre_completo=f"Estudiante ficticio {i}",
                              id_escuela=f"ESC-QA{i}", nombre_escuela=f"Escuela ficticia {i}",
                              grado="2", grupo="B", tipo_atencion="Grupal"))
            cls.password = secrets.token_urlsafe(24)
            for i, rol in enumerate(("APRENDIZAJE", "PSICOLOGIA", "APRENDIZAJE")):
                db.add(Usuario(id=f"QA-{i}", usuario=f"qa.{i}", nombre=f"Profesional ficticio {i}",
                               password=hash_password(cls.password), rol=rol,
                               escuelas_permitidas="ESC-QA2" if i == 2 else "ESC-QA1"))
            db.commit()
        for clave, modalidad in (("historica-ind", "individual"), ("historica-grupo", "grupal")):
            guardar_planeacion_sql({"id": clave, "cuenta": "qa.0", "formato": "XXIII",
                "estado": "BORRADOR", "revision": "importada", "datos": {
                    "ID_Escuela": "ESC-QA1", "Escuela regular": "Escuela ficticia 1",
                    "Curso escolar": "2026-2027", "Función": "Aprendizaje",
                    "Nombre del especialista": "Profesional ficticio 0",
                    "Alumnos": [{"ID_Alumno": "ALU-QA1", "Grado": "2", "Grupo": "B", "Condición": "",
                                 "Nombre del alumno": "Estudiante ficticio 1", "Tipo_Atencion": "Grupal"}]},
                "metadatos": {"modalidad_planeacion": modalidad, "guia_grupal_manual": {"filas": [
                    {"ID_Alumno": "ALU-QA1", "Psicología": "Aporte histórico ficticio"}
                ]} if modalidad == "grupal" else {}},
                "tablas": {"aprendizajes": [{"Descriptor de logro": "Identifica dos cantidades"}],
                           "dosificacion": [{"Fecha": "Semana 1", "Actividades": "Actividad histórica"}]},
                "textos": {"Evaluación": "Evidencia ficticia"}})

    def setUp(self):
        self.client = TestClient(app)
        self.headers = []
        for i in range(3):
            r = self.client.post("/api/auth/login", json={"usuario": f"qa.{i}", "password": self.password})
            self.assertEqual(r.status_code, 200, r.text)
            self.headers.append({"Authorization": "Bearer " + r.json()["token"]})

    def test_formato_vivo_y_colaboracion(self):
        c = self.client
        apoyo, psicologia, otra = self.headers
        ruta = "/api/epp/ALU-QA1"
        self.assertEqual(c.get(ruta, headers=otra).status_code, 404)
        self.assertEqual(c.get(ruta).status_code, 401)
        d = c.get(ruta, headers=apoyo).json()
        self.assertIsNone(d["revision"])
        guardar = {"area": "Aprendizaje", "ciclo": d["ciclo"], "revision": d["revision"],
                   "campos": {"4.1. Orientación temporal": "Ordena tres tarjetas con ayuda."},
                   "sintesis": "NEE: Necesita ordenar las secuencias de la rutina."}
        self.assertEqual(c.put(ruta+"/apartado", headers=psicologia, json=guardar).status_code, 403)
        r = c.put(ruta+"/apartado", headers=apoyo, json=guardar)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(c.put(ruta+"/apartado", headers=apoyo, json=guardar).status_code, 409)
        psi = {"area": "Psicología", "ciclo": d["ciclo"], "revision": r.json()["revision"],
               "campos": {"3.1. Atención": "Atiende a una consigna breve."}}
        r = c.put(ruta+"/apartado", headers=psicologia, json=psi)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertIn("Ordena tres tarjetas", r.json()["partes"]["Aprendizaje"]["contenido"]["campos"]["4.1. Orientación temporal"])
        propuesta = {"area": "Conclusión", "ciclo": d["ciclo"]}
        p = c.post(ruta+"/propuesta", headers=apoyo, json=propuesta).json()
        self.assertIn("Psicología", p["campos"]["7.1. Conclusión"])
        self.assertTrue(any("secuencias" in row["NEE"] for row in p["nee"]))
        self.assertFalse(any(row["Tipo de barrera"] for row in p["bap"]))
        self.assertTrue(c.get(ruta+"/pdf", headers=apoyo).content.startswith(b"%PDF"))

    def test_lectura_de_archivos_y_permiso(self):
        from docx import Document
        from reportlab.pdfgen.canvas import Canvas

        ruta = "/api/epp/ALU-QA2/propuesta"
        apoyo, _, otra = self.headers
        docx = Document()
        docx.add_paragraph("En lectura identifica dos palabras con tarjetas.")
        buf_docx = BytesIO()
        docx.save(buf_docx)
        buf_pdf = BytesIO()
        pdf = Canvas(buf_pdf)
        pdf.drawString(72, 720, "En lectura identifica dos palabras con tarjetas.")
        pdf.save()
        for nombre, data in (("evidencia.txt", b"En lectura identifica dos palabras con tarjetas."),
                             ("evidencia.docx", buf_docx.getvalue()), ("evidencia.pdf", buf_pdf.getvalue())):
            payload = {"area": "Aprendizaje", "ciclo": "2026-2027", "campo": "4.1. Lectura y escritura funcional",
                       "archivo_nombre": nombre, "archivo_base64": base64.b64encode(data).decode()}
            self.assertEqual(self.client.post(ruta, headers=apoyo, json=payload).status_code, 404)
            r = self.client.post(ruta, headers=otra, json=payload)
            self.assertEqual(r.status_code, 200, r.text)
            self.assertIn("dos palabras", r.json()["texto"])
            self.assertEqual(len(r.json()["archivo_sha256"]), 64)

    def test_recuperacion_individual_grupal_y_aislamiento(self):
        apoyo, _, otra = self.headers
        docs = self.client.get("/api/planeaciones", headers=apoyo).json()
        self.assertEqual({d["modalidad"] for d in docs}, {"individual", "grupal"})
        self.assertEqual(self.client.get("/api/planeaciones", headers=otra).json(), [])
        r = self.client.get("/api/planeaciones/historica-grupo", headers=apoyo)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["guia_grupal"]["filas"][0]["Psicología"], "Aporte histórico ficticio")
        self.assertEqual(r.json()["tablas"]["dosificacion"][0]["Temporalidad"], "Semana 1")
        self.assertEqual(self.client.get("/api/planeaciones/historica-grupo", headers=otra).status_code, 403)
        self.assertEqual(self.client.get("/api/planeaciones/no-existe", headers=apoyo).status_code, 404)

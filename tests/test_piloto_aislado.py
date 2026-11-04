"""Regresión del piloto con HTTP real, dos arranques y SQLite temporal."""

import os
import secrets
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import contextmanager

import httpx
import ssl

ROOT = Path(__file__).resolve().parents[1]

PASSWORD = secrets.token_urlsafe(24)
SEED = """
import sys
from data.database import Alumno, Usuario, get_session
from piloto_spa.backend.auth_service import hash_password
with get_session() as db:
    for suffix in ("A", "B"):
        db.add(Alumno(id="alu-" + suffix, nombre_completo="Alumno ficticio " + suffix,
                      id_escuela="esc-" + suffix, grado="2", grupo="A"))
        db.add(Usuario(id=suffix, usuario=suffix.lower(), rol="MAESTRA DE APOYO",
                       escuelas_permitidas="esc-" + suffix, password=hash_password(sys.argv[1])))
    db.add(Usuario(id="legacy", usuario="legacy", rol="DIRECTOR", password=sys.argv[1]))
    db.commit()
"""


@contextmanager
def servidor(env, carpeta):
    log_path = carpeta / "servidor.log"
    with log_path.open("wb") as log:
        process = subprocess.Popen(
            [sys.executable, "iniciar_piloto.py"], cwd=ROOT, env=env, stdout=log, stderr=log
        )
        try:
            deadline = time.monotonic() + 25
            tls = env.get("USAER_SPA_TLS_CERT")
            protocolo = "https" if tls else "http"
            verificador = ssl.create_default_context(cafile=tls) if tls else True
            with httpx.Client(base_url=f"{protocolo}://127.0.0.1:{env['USAER_SPA_PORT']}",
                              trust_env=False, verify=verificador) as client:
                client.usaer_pid = process.pid
                while time.monotonic() < deadline:
                    if process.poll() is not None:
                        break
                    try:
                        if client.get("/api/health", timeout=1).status_code == 200:
                            # Evitar escribir si hay otro proceso escuchando en el mismo puerto.
                            if "Uvicorn running on" in log_path.read_text(encoding="utf-8", errors="replace") and process.poll() is None:
                                break
                    except httpx.TransportError:
                        pass
                    time.sleep(0.15)
                else:
                    raise AssertionError(log_path.read_text(encoding="utf-8", errors="replace"))
                if process.poll() is not None:
                    raise AssertionError(log_path.read_text(encoding="utf-8", errors="replace"))
                yield client
        finally:
            if process.poll() is None:
                process.terminate()
            process.wait(timeout=10)


class PilotoAislado(unittest.TestCase):
    def login(self, client, usuario="a", password=PASSWORD):
        return client.post("/api/auth/login", json={"usuario": usuario, "password": password})

    def ok(self, response):
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_persistencia_permisos_y_reinicio(self):
        with tempfile.TemporaryDirectory(prefix="usaer-auditoria-") as tmp:
            carpeta = Path(tmp)
            env = dict(os.environ, DATABASE_URL=f"sqlite:///{(carpeta / 'ficticia.db').as_posix()}")
            env["USAER_SPA_SQLITE_URL"] = env["DATABASE_URL"]
            with socket.socket() as probe:
                probe.bind(("127.0.0.1", 0))
                env["USAER_SPA_PORT"] = str(probe.getsockname()[1])
            subprocess.run([sys.executable, "-c", SEED, PASSWORD], cwd=ROOT, env=env, check=True)
            with servidor(env, carpeta) as client:
                self.assertIn("/assets/app.js", client.get("/").text)
                self.assertEqual(self.login(client, password=secrets.token_urlsafe(24)).status_code, 401)
                self.assertEqual(self.login(client, "legacy").status_code, 401)
                token = self.ok(self.login(client))["token"]
                a = {"Authorization": f"Bearer {token}"}
                b_token = self.ok(self.login(client, "b"))["token"]
                b = {"Authorization": f"Bearer {b_token}"}
                self.assertEqual(client.get("/api/me").status_code, 401)
                pid = "plan-nuevo-auditoria"
                plan = self.ok(client.get(f"/api/planeaciones/{pid}", headers=a))
                plan["metadatos"]["titulo"] = "Planeación ficticia, primer guardado"
                acuse = self.ok(client.post("/api/planeaciones", json=plan, headers=a))
                plan = self.ok(client.get(f"/api/planeaciones/{pid}", headers=a))
                self.assertEqual(plan["revision"], acuse["revision"])
                plan["metadatos"]["titulo"] = "Planeación ficticia persistente"
                self.ok(client.post("/api/planeaciones", json=plan, headers=a))
                self.assertEqual(client.post("/api/planeaciones", json=plan, headers=a).status_code, 409)
                self.assertEqual(client.get(f"/api/planeaciones/{pid}", headers=b).status_code, 404)
                self.assertEqual(client.post("/api/planeaciones", json=plan, headers=b).status_code, 404)
                self.assertEqual(client.get(f"/api/planeaciones/{pid}/pdf", headers=b).status_code, 404)
                pdf = client.get(f"/api/planeaciones/{pid}/pdf", headers=a)
                self.assertEqual(pdf.status_code, 200, pdf.text if pdf.status_code != 200 else "")
                self.assertTrue(pdf.content.startswith(b"%PDF"))
                exp = self.ok(client.get("/api/expedientes/alu-A", headers=a))
                self.assertEqual(exp["anexo5_eventos"], [])
                evento = {"id_alumno": "alu-A", "evento": "Evento ficticio persistente"}
                self.ok(client.post("/api/anexo5", json=evento, headers=a))
                self.assertEqual(client.post("/api/anexo5", json=evento, headers=b).status_code, 404)
                self.assertEqual(client.get("/api/expedientes/alu-A", headers=b).status_code, 404)
                epp = self.ok(client.get("/api/epp/alu-A", headers=a))
                epp["partes"]["APRENDIZAJE"]["avances_observables"] = "Evidencia ficticia persistente"
                self.ok(client.post("/api/epp", json=epp, headers=a))
                self.assertEqual(client.post("/api/epp", json=epp, headers=a).status_code, 409)
                self.assertEqual(client.post("/api/epp", json=epp, headers=b).status_code, 404)
                self.assertEqual(client.get("/api/epp/alu-A", headers=b).status_code, 404)
                self.assertEqual(client.get("/api/estadisticas/zona", headers=b).status_code, 403)
                self.assertEqual(client.get("/api/visitas", headers=b).status_code, 403)
                self.assertEqual(client.post("/api/ai/chat", json={"mensaje":"Prueba", "alumno_id":"alu-A"},
                                             headers=b).status_code, 404)
                self.assertEqual(client.put("/api/alumnos/alu-A", json={"ID_Escuela":"esc-B"},
                                            headers=a).status_code, 403)
                self.ok(client.post("/api/auth/logout", headers=b))
                self.assertEqual(client.get("/api/me", headers=b).status_code, 401)
            with servidor(env, carpeta) as client:
                self.assertEqual(client.get("/api/me", headers=a).status_code, 200)
                a = {"Authorization": f"Bearer {self.ok(self.login(client))['token']}"}
                plan = self.ok(client.get(f"/api/planeaciones/{pid}", headers=a))
                self.assertEqual(plan["metadatos"]["titulo"], "Planeación ficticia persistente")
                exp = self.ok(client.get("/api/expedientes/alu-A", headers=a))
                self.assertEqual(exp["anexo5_eventos"][0]["evento"], evento["evento"])
                epp = self.ok(client.get("/api/epp/alu-A", headers=a))
                self.assertEqual(epp["partes"]["APRENDIZAJE"]["avances_observables"],
                                 "Evidencia ficticia persistente")


if __name__ == "__main__":
    unittest.main()

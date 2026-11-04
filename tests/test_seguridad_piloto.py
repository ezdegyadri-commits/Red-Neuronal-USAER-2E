"""HTTPS local con confianza explícita y regresión de acceso y cuentas."""
from datetime import datetime, timedelta, timezone
import ipaddress
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import unittest

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from test_piloto_aislado import ROOT, SEED, servidor


def certificado_local(carpeta):
    clave = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    sujeto = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "USAER piloto sintético")])
    ahora = datetime.now(timezone.utc)
    certificado = (x509.CertificateBuilder().subject_name(sujeto).issuer_name(sujeto)
                   .public_key(clave.public_key()).serial_number(x509.random_serial_number())
                   .not_valid_before(ahora - timedelta(minutes=5)).not_valid_after(ahora + timedelta(hours=1))
                   .add_extension(x509.SubjectAlternativeName([
                       x509.IPAddress(ipaddress.ip_address("127.0.0.1")), x509.DNSName("usaer-prueba.invalid"),
                   ]), critical=False).sign(clave, hashes.SHA256()))
    ruta_cert, ruta_clave = carpeta / "test.pem", carpeta / "test.key"
    ruta_cert.write_bytes(certificado.public_bytes(serialization.Encoding.PEM))
    ruta_clave.write_bytes(clave.private_bytes(serialization.Encoding.PEM,
                          serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    return {"USAER_SPA_TLS_CERT": str(ruta_cert), "USAER_SPA_TLS_KEY": str(ruta_clave),
            "USAER_SPA_TLS_HOST": "usaer-prueba.invalid"}


class SeguridadPiloto(unittest.TestCase):
    def test_tls_limite_y_revocacion(self):
        with tempfile.TemporaryDirectory(prefix="usaer-tls-") as tmp:
            carpeta = Path(tmp)
            tls = certificado_local(carpeta)
            subprocess.run([sys.executable, "tools/verificar_tls_privado.py"], cwd=ROOT, check=True,
                           env=dict(os.environ, **tls))
            with socket.socket() as probe:
                probe.bind(("127.0.0.1", 0))
                puerto = probe.getsockname()[1]
            password = secrets.token_urlsafe(24)
            sqlite = f"sqlite:///{(carpeta / 'fixture.db').as_posix()}"
            env = dict(os.environ, **tls, DATABASE_URL=sqlite, USAER_SPA_SQLITE_URL=sqlite, USAER_SPA_PORT=str(puerto))
            env.pop("USAER_SPA_POSTGRES_TEST_URL", None)
            subprocess.run([sys.executable, "-c", SEED, password], cwd=ROOT, env=env, check=True)
            semilla = """
import sys
from data.database import Escuela, Usuario, get_session
from piloto_spa.backend.auth_service import hash_password
with get_session() as db:
    db.add(Escuela(id='esc-A', nombre_escuela='Escuela sintética'))
    db.add(Usuario(id='dir-prueba', usuario='dir-prueba', nombre='Dirección sintética', rol='DIRECTOR',
                   escuelas_permitidas='TODAS', password=hash_password(sys.argv[1])))
    db.commit()
"""
            subprocess.run([sys.executable, "-c", semilla, password], cwd=ROOT, env=env, check=True)
            with servidor(env, carpeta) as client:
                browser = {"X-USAER-Client": "browser"}
                login = client.post("/api/auth/login", json={"usuario": "a", "password": password}, headers=browser)
                self.assertEqual(login.status_code, 200, login.text)
                cookie = login.headers["set-cookie"]
                self.assertIn("Secure", cookie)
                self.assertIn("HttpOnly", cookie)
                self.assertIn("SameSite=strict", cookie)
                self.assertEqual(login.headers["strict-transport-security"], "max-age=86400")
                self.assertEqual(client.get("/api/health", headers={"Host": "host-no-autorizado.invalid"}).status_code, 400)
                self.assertEqual(client.get("/api/health", headers={"Host": "usaer-prueba.invalid"}).status_code, 200)
                self.assertEqual(client.get("/api/me").status_code, 200)
                import pymupdf
                with pymupdf.open() as pdf:
                    pdf.new_page().insert_text((72, 72), "Documento sintético")
                    contenido = pdf.tobytes()
                adjuntos = "/api/expedientes/alu-A/adjuntos"
                pdf_headers = {**browser, "Content-Type": "application/pdf"}
                subida = client.post(adjuntos + "?nombre=Prueba.pdf", headers=pdf_headers, content=contenido)
                self.assertEqual(subida.status_code, 200, subida.text)
                id_pdf = subida.json()["id"]
                self.assertEqual(client.post(adjuntos + "?nombre=Duplicado.pdf", headers=pdf_headers,
                                             content=contenido).json()["id"], id_pdf)
                self.assertEqual(client.post(adjuntos + "?nombre=Falso.pdf", headers=pdf_headers,
                                             content=b"contenido falso").status_code, 422)
                self.assertEqual(client.post(adjuntos + "?nombre=Grande.pdf", headers=pdf_headers,
                                             content=b"x" * (5 * 1024**2 + 1)).status_code, 413)
                otro = client.post("/api/auth/login", json={"usuario": "b", "password": password}).json()["token"]
                self.assertEqual(client.get(adjuntos + "/" + id_pdf,
                                             headers={"Authorization": f"Bearer {otro}"}).status_code, 404)
                descarga = client.get(adjuntos + "/" + id_pdf)
                self.assertEqual(descarga.content, contenido)
                self.assertIn("attachment", descarga.headers["content-disposition"])
                client.get("/api/health?dato=marcador_privado_de_prueba")
                log = (carpeta / "servidor.log").read_text(encoding="utf-8", errors="replace")
                self.assertIn("ruta=/api/expedientes/{alumno_id}/adjuntos/{adjunto_id}", log)
                self.assertNotIn(id_pdf, log)
                self.assertNotIn("marcador_privado_de_prueba", log)
                contrasena_alta = secrets.token_urlsafe(22) + "9A"
                alta = {"usuario": "docente-nuevo", "nombre": "Docente sintético",
                        "rol": "PSICOLOGIA", "escuelas": ["esc-A"], "password": contrasena_alta, "actual": password}
                self.assertEqual(client.post("/api/auth/cuentas", headers=browser, json=alta).status_code, 403)
                login_dir = client.post("/api/auth/login", json={"usuario": "dir-prueba", "password": password})
                self.assertEqual(login_dir.status_code, 200, login_dir.text)
                admin = {"Authorization": f"Bearer {login_dir.json()['token']}"}
                acta = {"tipo_acta": "Acta de reunión", "escuela": "Escuela sintética",
                        "fecha": "2026-11-03", "acuerdos": "Revisar los apoyos",
                        "seguimiento": "Segunda visita", "responsable": "Dirección sintética"}
                self.assertEqual(client.post("/api/visitas", json=acta, headers=browser).status_code, 403)
                alta_acta = client.post("/api/visitas", json=acta, headers=admin)
                self.assertEqual(alta_acta.status_code, 200, alta_acta.text)
                ruta_acta = "/api/visitas/" + alta_acta.json()["id"]
                doc = client.get(ruta_acta, headers=admin).json()
                self.assertEqual(doc["acuerdos"], acta["acuerdos"])
                self.assertEqual(client.put(ruta_acta, json={**doc, "seguimiento": "Acuerdo revisado"},
                                            headers=admin).status_code, 200)
                self.assertEqual(client.put(ruta_acta, json=doc, headers=admin).status_code, 409)
                self.assertEqual(len(client.get(ruta_acta + "/historial", headers=admin).json()), 2)
                self.assertEqual(client.get(ruta_acta, headers=admin).json()["seguimiento"], "Acuerdo revisado")
                pdf = client.get(ruta_acta + "/pdf", headers=admin)
                self.assertEqual(pdf.status_code, 200)
                self.assertTrue(pdf.content.startswith(b"%PDF-"))
                self.assertEqual(client.post("/api/auth/cuentas", headers=admin,
                                             json={**alta, "escuelas": ["externa"]}).status_code, 422)
                alta_res = client.post("/api/auth/cuentas", headers=admin, json=alta)
                self.assertEqual(alta_res.status_code, 201, alta_res.text)
                cuenta_url = "/api/auth/cuentas/" + alta_res.json()["id"]
                usuario = client.post("/api/auth/login", json={"usuario": alta["usuario"], "password": contrasena_alta})
                self.assertEqual(usuario.status_code, 200, usuario.text)
                sesion = {"Authorization": f"Bearer {usuario.json()['token']}"}
                self.assertEqual(client.post(cuenta_url + "/baja", headers=admin, json={"actual": password}).status_code, 200)
                self.assertEqual(client.get("/api/me", headers=sesion).status_code, 401)
                self.assertEqual(client.post("/api/auth/login",
                    json={"usuario": alta["usuario"], "password": contrasena_alta}).status_code, 401)
                nueva_clave = secrets.token_urlsafe(22) + "9A"
                self.assertEqual(client.put(cuenta_url + "/password", headers=admin,
                    json={"actual": password, "nueva": nueva_clave}).status_code, 200)
                self.assertEqual(client.post("/api/auth/login",
                    json={"usuario": alta["usuario"], "password": nueva_clave}).status_code, 200)
                nueva = secrets.token_urlsafe(22) + "9A"
                payload = {"actual": password, "nueva": nueva}
                self.assertEqual(client.put("/api/auth/cuentas/B/password", json=payload, headers=browser).status_code, 403)
                self.assertEqual(client.put("/api/auth/cuentas/A/password", json=payload, headers=browser).status_code, 200)
                self.assertEqual(client.get("/api/me").status_code, 401)
                self.assertEqual(client.post("/api/auth/login", json={"usuario": "a", "password": nueva}).status_code, 200)
                respuestas = [client.post("/api/auth/login", json={"usuario": "noexiste", "password": nueva})
                              for _ in range(16)]
                self.assertIn(429, [r.status_code for r in respuestas])
                self.assertTrue(all("retry-after" in r.headers for r in respuestas if r.status_code == 429))
                entrada = client.get("/")
                self.assertIn("script-src 'self'", entrada.headers["content-security-policy"])
                self.assertIn('/assets/app.js', entrada.text)
                self.assertNotIn('unpkg.com', entrada.text)
                self.assertNotIn('cdn.tailwindcss.com', entrada.text)
                self.assertEqual(client.get('/assets/app.js').status_code, 200)
                self.assertEqual(client.get('/assets/app.css').status_code, 200)


if __name__ == "__main__":
    unittest.main()

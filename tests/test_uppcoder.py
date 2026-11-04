"""Prueba el contrato de Uppcoder sin abrir la base del alojamiento."""
import os
import secrets
import unittest
from unittest.mock import patch

from sqlalchemy.engine import make_url

from deploy import uppcoder


class ConfiguracionUppcoder(unittest.TestCase):
    def test_url_cerrada_secreto_codificado_y_proxy_acotado(self):
        clave = secrets.token_urlsafe(20) + "@:/"
        with patch.dict(os.environ, {"USAER_UPPCODER_PUBLIC_HOST": "piloto.example.invalid",
                                     "USAER_UPPCODER_SYNTHETIC": "1", "USAER_UPPCODER_DB_PASSWORD": clave}):
            uppcoder.configurar()
            self.assertEqual(make_url(os.environ["DATABASE_URL"]).password, clave)
            uppcoder.verificar_url()
            os.environ["DATABASE_URL"] = "postgresql+psycopg2://usaer_app@otro:5432/usaer_2e_2_0"
            with self.assertRaises(RuntimeError):
                uppcoder.verificar_url()
            with patch.dict(os.environ, {"USAER_UPPCODER_PROXY_IPS": "0.0.0.0/0"}):
                with self.assertRaises(ValueError):
                    uppcoder.proxies_confiables()


@unittest.skipUnless(os.getenv("USAER_UPPCODER_TEST_LOCAL_URL"), "Requiere clúster PostgreSQL 17 temporal.")
class UppcoderPostgres(unittest.TestCase):
    def test_migracion_repetible_y_inicio_https(self):
        from fastapi.testclient import TestClient
        from data.database import get_engine

        url_local = os.environ["USAER_UPPCODER_TEST_LOCAL_URL"]
        clave = secrets.token_urlsafe(24)
        host = "piloto.example.invalid"
        with patch.dict(os.environ, {
            "USAER_UPPCODER_PUBLIC_HOST": host, "USAER_UPPCODER_SYNTHETIC": "1",
            "USAER_UPPCODER_DB_PASSWORD": secrets.token_urlsafe(24),
            "USAER_UPPCODER_DIRECTOR_PASSWORD": clave,
        }):
            uppcoder.configurar()
            url_esperada = os.environ["DATABASE_URL"]
            # Solo el test cambia el transporte. La identidad y las tablas se
            # comprueban en un PostgreSQL 17 real y recién creado.
            os.environ["DATABASE_URL"] = url_local
            engine = get_engine(initialize_schema=False)
            os.environ["DATABASE_URL"] = url_esperada
            with engine.connect() as db, self.assertRaisesRegex(RuntimeError, "migración"):
                uppcoder.verificar_instalacion(db)
            uppcoder.migrar()
            del os.environ["USAER_UPPCODER_DIRECTOR_PASSWORD"]
            uppcoder.migrar()
            from piloto_spa.backend.main import app

            with TestClient(app, base_url=f"https://{host}") as cliente:
                self.assertEqual(cliente.get("/api/health").status_code, 200)
                self.assertIn("/assets/app.js", cliente.get("/").text)
                self.assertEqual(cliente.get("/assets/app.js").status_code, 200)
                self.assertEqual(cliente.get("/api/health", headers={"Host": "otro.invalid"}).status_code, 400)
                self.assertEqual(cliente.get("/api/alumnos").status_code, 401)
                login = cliente.post("/api/auth/login", headers={"X-USAER-Client": "browser"},
                                     json={"usuario": "direccion.piloto", "password": clave})
                self.assertEqual(login.status_code, 200, login.text)
                self.assertIn("Secure", login.headers["set-cookie"])
                self.assertEqual(len(cliente.get("/api/alumnos").json()), 2)


if __name__ == "__main__":
    unittest.main()

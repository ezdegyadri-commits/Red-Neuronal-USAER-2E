"""Prueba el contrato de Uppcoder sin abrir la base del alojamiento."""
import os
import secrets
import sys
from importlib.abc import MetaPathFinder
import unittest
from unittest.mock import patch

from sqlalchemy import text
from sqlalchemy.engine import make_url

from deploy import uppcoder


class ConfiguracionUppcoder(unittest.TestCase):
    def test_destino_spark_y_secreto_del_servicio_enlazado(self):
        clave = secrets.token_urlsafe(20) + "@:/"
        datos = {"host": "piloto.example.invalid", "db_host": "pila-postgresql-17",
                 "db_name": "piloto_dedicado", "db_user": "rol_piloto"}
        with patch.dict(os.environ, {"POSTGRES_HOST": "otra-pila", "POSTGRES_DB": datos["db_name"],
                                     "POSTGRES_USER": datos["db_user"], "POSTGRES_PASSWORD": clave}, clear=True):
            uppcoder.configurar_spark(datos)
            self.assertIsNone(uppcoder.password_conexion())
            os.environ["POSTGRES_HOST"] = datos["db_host"]
            uppcoder.configurar()
            url = make_url(os.environ["DATABASE_URL"])
            self.assertEqual((url.host, url.database, url.username), tuple(datos[k] for k in ("db_host", "db_name", "db_user")))
            self.assertEqual(url.password, clave)
            uppcoder.verificar_url()
            os.environ["USAER_UPPCODER_DB_NAME"] = "otra_base"
            with self.assertRaises(RuntimeError):
                uppcoder.verificar_url()
            os.environ["USAER_UPPCODER_DB_HOST"] = "https://otro:5432"
            with self.assertRaises(RuntimeError):
                uppcoder.destino_postgres()

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
        class SinLegado(MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if fullname.split(".")[0] in {"streamlit", "gspread", "googleapiclient", "pytesseract", "openai"}:
                    raise ImportError(f"Dependencia no incluida en Spark: {fullname}")

        guardia = SinLegado()
        sys.meta_path.insert(0, guardia)
        self.addCleanup(sys.meta_path.remove, guardia)
        from fastapi.testclient import TestClient
        from data import database
        from data.database import get_engine

        url_local = os.environ["USAER_UPPCODER_TEST_LOCAL_URL"]
        clave = secrets.token_urlsafe(24)
        host = "piloto.example.invalid"
        with patch.dict(os.environ, {
            "USAER_UPPCODER_PUBLIC_HOST": host, "USAER_UPPCODER_SYNTHETIC": "1",
            "USAER_UPPCODER_DB_PASSWORD": secrets.token_urlsafe(24),
            "USAER_UPPCODER_DIRECTOR_PASSWORD": clave,
            "USAER_UPPCODER_SPARK": "1",
        }):
            uppcoder.configurar()
            url_esperada = os.environ["DATABASE_URL"]
            # Solo el test cambia el transporte. La identidad y las tablas se
            # comprueban en un PostgreSQL 17 real y recién creado.
            driver = make_url(url_esperada).drivername
            os.environ["DATABASE_URL"] = make_url(url_local).set(drivername=driver).render_as_string(hide_password=False)
            engine = get_engine(initialize_schema=False)
            os.environ["DATABASE_URL"] = url_esperada
            with engine.connect() as db:
                with self.assertRaisesRegex(RuntimeError, "CREATEROLE"):
                    uppcoder.verificar_instalacion(db)
                with self.assertRaisesRegex(RuntimeError, "migración"):
                    uppcoder.verificar_instalacion(db, migracion=True)
            uppcoder.migrar(cuenta_migracion=True)
            del os.environ["USAER_UPPCODER_DIRECTOR_PASSWORD"]
            uppcoder.migrar(cuenta_migracion=True)
            runtime = uppcoder.USUARIO_RUNTIME
            clave_runtime = secrets.token_urlsafe(32)
            with engine.begin() as db:
                self.assertTrue(uppcoder.preparar_runtime(db, runtime, clave_runtime))
                self.assertFalse(uppcoder.preparar_runtime(db, runtime, None))
            engine.dispose()
            database._ENGINE = database._SESSION_FACTORY = None
            uppcoder.configurar_spark({"host": host, "db_host": uppcoder.HOST_DB,
                                      "db_name": uppcoder.BASE_DB, "db_user": runtime,
                                      "password": clave_runtime, "separado": True})
            uppcoder.configurar()
            url_esperada = os.environ["DATABASE_URL"]
            os.environ["DATABASE_URL"] = make_url(url_local).set(
                drivername=driver, username=runtime, password=clave_runtime,
            ).render_as_string(hide_password=False)
            engine = get_engine(initialize_schema=False)
            os.environ["DATABASE_URL"] = url_esperada
            with engine.connect() as db:
                uppcoder.verificar_instalacion(db)
                self.assertFalse(db.scalar(text("SELECT has_schema_privilege('public', 'CREATE')")))
                self.assertFalse(db.scalar(text(
                    "SELECT has_table_privilege('public.usaer_uppcoder_piloto', 'UPDATE')"
                )))
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
                headers = {"X-USAER-Client": "browser"}
                alumno = "alu-uppcoder-a"
                self.assertEqual(cliente.get(f"/api/expedientes/{alumno}").status_code, 200)
                self.assertEqual(cliente.get(f"/api/epp/{alumno}/pdf").status_code, 200)
                alta = cliente.post("/api/planeaciones/nueva", headers=headers, json={
                    "modalidad": "individual", "alumnos": [alumno], "formato": "XXIII",
                })
                self.assertEqual(alta.status_code, 200, alta.text)
                ruta = "/api/planeaciones/" + alta.json()["id"]
                plan = cliente.get(ruta).json()
                plan["metadatos"]["titulo"] = "Plan ficticio Spark"
                guardado = cliente.post("/api/planeaciones", headers=headers, json=plan)
                self.assertEqual(guardado.status_code, 200, guardado.text)
                propuesta = cliente.post(ruta + "/propuesta", headers=headers, json={"enfoque": "lectura"})
                self.assertEqual(propuesta.status_code, 200, propuesta.text)
                self.assertTrue(cliente.get(ruta + "/pdf").content.startswith(b"%PDF"))
            with TestClient(app, base_url=f"https://{host}") as cliente:
                cliente.post("/api/auth/login", headers=headers, json={"usuario": "direccion.piloto", "password": clave})
                self.assertEqual(cliente.get(ruta).json()["metadatos"]["titulo"], "Plan ficticio Spark")
            if os.getenv("USAER_SPARK_CARGA_LOCAL") == "1":
                from time import monotonic, process_time
                from data.database import Usuario, get_session
                from piloto_spa.backend.auth_service import hash_password
                from carga_piloto import memoria_mib

                cuentas = [(f"docente-spark-{i}", secrets.token_urlsafe(24)) for i in range(15)]
                inicio_cpu = process_time()
                inicio = monotonic()
                with get_session() as db:
                    db.add_all(Usuario(id=u, usuario=u, nombre=f"Docente ficticio {i}",
                                       rol="MAESTRA DE APOYO", escuelas_permitidas="esc-uppcoder-a",
                                       password=hash_password(p)) for i, (u, p) in enumerate(cuentas))
                    db.commit()
                with TestClient(app, base_url=f"https://{host}") as cliente:
                    for usuario, password in cuentas:
                        cliente.cookies.clear()
                        acceso = cliente.post("/api/auth/login", headers=headers,
                                              json={"usuario": usuario, "password": password})
                        self.assertEqual(acceso.status_code, 200, acceso.text)
                        self.assertEqual(cliente.get("/api/alumnos").json()[0]["id"], alumno)
                        self.assertEqual(cliente.get("/api/expedientes/alu-uppcoder-b").status_code, 404)
                        cliente.post("/api/auth/logout", headers=headers)
                print(f"Spark local, 15 cuentas secuenciales: {monotonic()-inicio:.2f} s, "
                      f"CPU Python {process_time()-inicio_cpu:.2f} s, RSS {memoria_mib(os.getpid())} MiB.")


if __name__ == "__main__":
    unittest.main()

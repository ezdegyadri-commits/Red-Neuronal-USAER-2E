"""Prueba el contrato de Uppcoder sin abrir la base del alojamiento."""
import os
import secrets
import sys
from importlib.abc import MetaPathFinder
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from time import monotonic, process_time
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
                from deploy.cuentas_docentes_spark import CUENTAS, crear_cuentas
                claves = {usuario: secrets.token_urlsafe(24) + "1a" for usuario, *_ in CUENTAS}
                self.assertEqual(crear_cuentas(engine, claves.__getitem__), list(claves))
                self.assertEqual(crear_cuentas(engine, lambda _: self.fail("Cuenta ya creada")), [])
                accesos = [(usuario, claves[usuario], escuela[-1]) for usuario, _, _, escuela in CUENTAS]
                with engine.begin() as db:
                    db.execute(text("UPDATE alumnos SET tipo_atencion = 'Grupal' WHERE id = :id"), {"id": alumno})
            with TestClient(app, base_url=f"https://{host}") as cliente:
                cliente.post("/api/auth/login", headers=headers, json={"usuario": "direccion.piloto", "password": clave})
                self.assertEqual(cliente.get(ruta).json()["metadatos"]["titulo"], "Plan ficticio Spark")

                def comprobar_acceso(acceso):
                    usuario, password, escuela = acceso
                    propio = f"alu-uppcoder-{escuela}"
                    ajeno = "alu-uppcoder-b" if escuela == "a" else alumno
                    with TestClient(app, base_url=f"https://{host}") as docente:
                        login = docente.post("/api/auth/login", headers=headers, json={"usuario": usuario, "password": password})
                        self.assertEqual(login.status_code, 200, login.text)
                        self.assertEqual([a["id"] for a in docente.get("/api/alumnos").json()], [propio])
                        self.assertEqual(docente.get(f"/api/epp/{propio}/anexo").status_code, 200)
                        self.assertEqual(docente.get(f"/api/epp/{ajeno}/anexo").status_code, 404)
                        self.assertEqual(docente.get("/api/auth/cuentas").status_code, 403)
                        if usuario == "docente.a.piloto":
                            individual = docente.post("/api/planeaciones/nueva", headers=headers, json={
                                "modalidad": "individual", "alumnos": [propio],
                            })
                            self.assertEqual(individual.status_code, 200, individual.text)
                            grupal = docente.post("/api/planeaciones/nueva", headers=headers, json={
                                "modalidad": "grupal", "alumnos": [propio],
                            })
                            self.assertEqual(grupal.status_code, 200, grupal.text)
                            ruta_grupo = "/api/planeaciones/" + grupal.json()["id"]
                            guia = docente.get(ruta_grupo).json()
                            campo = "Aprendizaje"
                            self.assertIn(campo, guia["editor"]["columnas_editables"])
                            revision = guia["metadatos"]["revisiones_celda"]["filas"][propio][campo]
                            celda = docente.patch(ruta_grupo + "/celda", headers=headers, json={
                                "tabla": "filas", "alumno": propio, "campo": campo,
                                "revision": revision, "texto": "Aportación ficticia guardada",
                            })
                            self.assertEqual(celda.status_code, 200, celda.text)
                            informe = docente.post("/api/informes", headers=headers, json={
                                "alumno_id": propio, "ciclo": "2026-2027", "titulo": "Informe ficticio docente",
                            })
                            self.assertEqual(informe.status_code, 201, informe.text)
                            documento = (informe.json()["id"], ruta_grupo, campo)
                        else:
                            documento = None
                        cookie = docente.cookies.get("usaer_spa_session")
                        docente.post("/api/auth/logout", headers=headers)
                        self.assertEqual(docente.get("/api/alumnos").status_code, 401)
                        self.assertEqual(docente.get("/api/alumnos", headers={
                            "Cookie": f"usaer_spa_session={cookie}",
                        }).status_code, 401)
                        return documento

                inicio, cpu = monotonic(), process_time()
                with ThreadPoolExecutor(max_workers=3) as pool:
                    documentos, _, _ = list(pool.map(comprobar_acceso, accesos))
                informe_id, ruta_grupo, campo = documentos
                print(f"Tres cuentas concurrentes locales: {monotonic()-inicio:.2f} s, CPU Python {process_time()-cpu:.2f} s.")

                for usuario, password, _ in accesos:
                    with TestClient(app, base_url=f"https://{host}") as docente:
                        docente.post("/api/auth/login", headers=headers, json={"usuario": usuario, "password": password})
                        informe = docente.get(f"/api/informes/{informe_id}")
                        self.assertEqual(informe.status_code, 200 if usuario == "docente.a.piloto" else 404)
                        guia = docente.get(ruta_grupo)
                        if usuario == "docente.b.piloto":
                            self.assertEqual(guia.status_code, 404)
                        else:
                            self.assertEqual(guia.json()["metadatos"]["guia_grupal_manual"]["filas"][0][campo],
                                             "Aportación ficticia guardada")
                            if usuario == "psicologia.a.piloto":
                                intento = docente.patch(ruta_grupo + "/celda", headers=headers, json={
                                    "tabla": "filas", "alumno": alumno, "campo": campo,
                                    "revision": "", "texto": "Cambio ajeno",
                                })
                                self.assertEqual(intento.status_code, 403)
            if destino := os.getenv("USAER_UPPCODER_TEST_DUMP"):
                from deploy.respaldo_spark import respaldar

                respaldar(make_url(url_local).set(username=runtime, password=clave_runtime), Path(destino),
                          pg_dump=os.getenv("USAER_UPPCODER_TEST_PG_DUMP", "pg_dump"))
            if os.getenv("USAER_SPARK_CARGA_LOCAL") == "1":
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

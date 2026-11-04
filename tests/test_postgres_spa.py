"""Prueba integral con un clúster PostgreSQL nuevo y dos servicios sintéticos."""
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
import os
from io import BytesIO
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import unittest

import psycopg2
from openpyxl import Workbook, load_workbook
from psycopg2 import sql
from sqlalchemy.engine import URL

from test_piloto_aislado import ROOT, SEED, PASSWORD, servidor


def puerto():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def excel_padron(nombre, escuela="esc-A"):
    libro = Workbook()
    hoja = libro.active
    hoja.title = "ALUMNOS USAER"
    hoja.append(["Nombre completo", "CURP", "Grado", "Grupo", "Sexo", "Tipo de atención", "ID Escuela"])
    hoja.append([nombre, "ZZZZ160101HNEZZZ01", "6", "Z", "H", "Individual", escuela])
    archivo = BytesIO()
    libro.save(archivo)
    return archivo.getvalue()


@unittest.skipUnless(os.getenv("USAER_PG_BIN"), "Requiere los binarios locales de PostgreSQL.")
class PostgreSQLAislado(unittest.TestCase):
    def test_servicios_respaldo_y_reinicio(self):
        binarios = Path(os.environ["USAER_PG_BIN"]).resolve()
        with tempfile.TemporaryDirectory(prefix="usaer-pg-") as temporal:
            carpeta = Path(temporal)
            datos = carpeta / "cluster"
            pwd_file = carpeta / "bootstrap.txt"
            bootstrap = secrets.token_urlsafe(30)
            pwd_file.write_text(bootstrap + "\n", encoding="ascii")
            pg_port = puerto()
            if pg_port == 5432:
                pg_port = puerto()
            base_env = {k: v for k, v in os.environ.items()
                        if not k.startswith("PG") and k != "USAER_SPA_POSTGRES_TEST_URL"}

            def pg(programa, *args, env=base_env):
                exe = binarios / (programa + (".exe" if os.name == "nt" else ""))
                registro = carpeta / (programa + ".log")
                with registro.open("ab") as log:
                    result = subprocess.run([str(exe), *map(str, args)], cwd=carpeta,
                                            env=env, stdout=log, stderr=log, timeout=60)
                self.assertEqual(result.returncode, 0, registro.read_text(encoding="utf-8", errors="replace"))

            try:
                pg("initdb", "-D", datos, "-U", "spa_bootstrap", "--pwfile", pwd_file,
                   "--auth=scram-sha-256", "--encoding=UTF8", "--locale=C")
            finally:
                pwd_file.unlink(missing_ok=True)
            pg("pg_ctl", "-D", datos, "-l", carpeta / "postgres.log", "-w", "start",
               "-o", f"-h 127.0.0.1 -p {pg_port}")
            try:
                def db_config(sufijo):
                    return URL.create("postgresql", username="spa_fixture_" + sufijo, password=secrets.token_urlsafe(30),
                                      host="127.0.0.1", port=pg_port, database="usaer_spa_test_" + sufijo)

                nombres = ["a", "b", "recuperada"]
                if os.getenv("USAER_MIGRACION_PRUEBA"):
                    nombres.extend(("migracion_fixture", "migracion_restaurada", "preparacion", "proyeccion_fixture"))
                urls = {nombre: db_config(nombre) for nombre in nombres}
                with closing(psycopg2.connect(host="127.0.0.1", port=pg_port, dbname="postgres",
                                              user="spa_bootstrap", password=bootstrap, connect_timeout=5)) as db:
                    db.autocommit = True
                    with db.cursor() as cur:
                        for url in urls.values():
                            rol, base = sql.Identifier(url.username), sql.Identifier(url.database)
                            cur.execute(sql.SQL("CREATE ROLE {} LOGIN PASSWORD %s").format(rol), (url.password,))
                            cur.execute(sql.SQL("CREATE DATABASE {} OWNER {}").format(base, rol))
                            cur.execute(sql.SQL("REVOKE CONNECT ON DATABASE {} FROM PUBLIC").format(base))
                            cur.execute(sql.SQL("COMMENT ON DATABASE {} IS %s").format(sql.Identifier(url.database)),
                                        ("USAER SPA synthetic only",))

                def app_env(nombre):
                    url = urls[nombre].render_as_string(hide_password=False)
                    return dict(base_env, DATABASE_URL=url, USAER_SPA_POSTGRES_TEST_URL=url, USAER_SPA_PORT=str(puerto()))

                if os.getenv("USAER_UPPCODER_PRUEBA") == "solo":
                    clave = secrets.token_urlsafe(24)
                    with closing(psycopg2.connect(host="127.0.0.1", port=pg_port, dbname="postgres",
                                                  user="spa_bootstrap", password=bootstrap)) as db:
                        db.autocommit = True
                        with db.cursor() as cur:
                            cur.execute("CREATE ROLE usaer_app LOGIN PASSWORD %s", (clave,))
                            cur.execute("CREATE DATABASE usaer_2e_2_0 OWNER usaer_app")
                    prueba = URL.create("postgresql+psycopg2", username="usaer_app", password=clave,
                                        host="127.0.0.1", port=pg_port, database="usaer_2e_2_0")
                    subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests",
                                    "-p", "test_uppcoder.py", "-v"], cwd=ROOT,
                                   env=dict(base_env, USAER_UPPCODER_TEST_LOCAL_URL=prueba.render_as_string(hide_password=False)),
                                   check=True)
                    return

                if os.getenv("USAER_MIGRACION_PRUEBA"):
                    script_proyeccion = """
from data.database import Alumno, get_engine
from sqlalchemy import select, update
from tools.proyectar_copia_sintetica import proyectar
from tools.migracion_paralela import MARCA
engine = get_engine()
copia = {"marca": MARCA, "origen": "fixture", "pestanas": {
    "Escuelas": [["ID_Escuela", "Nombre_Escuela"], ["esc-sint", "Escuela ficticia"]],
    "Alumnos": [["ID_Alumno", "ID_Escuela", "Nombre_Completo"], ["alu-sint", "esc-sint", "Estudiante ficticio"]],
    "Anexo5_Eventos": [["ID_Evento", "ID_Alumno", "Evento"], ["evento-1", "alu-sint", "Observación ficticia"]],
}}
assert proyectar(engine, copia)["tablas"]["Alumnos"]["nuevas"] == 1
assert proyectar(engine, copia, aplicar=True)["tablas"]["Anexo5_Eventos"]["nuevas"] == 1
assert proyectar(engine, copia, aplicar=True)["tablas"]["Alumnos"]["iguales"] == 1
with engine.begin() as db:
    db.execute(update(Alumno).values(nombre_completo="Edición de prueba"))
copia["pestanas"]["Anexo5_Eventos"].append(["evento-2", "alu-sint", "Evento posterior"])
result = proyectar(engine, copia, aplicar=True)["tablas"]
assert result["Alumnos"]["conflictos_preservados"] == 1
assert result["Anexo5_Eventos"]["nuevas"] == 0
with engine.connect() as db:
    assert db.execute(select(Alumno.nombre_completo)).scalar_one() == "Edición de prueba"
print("Proyección operativa: altas, repetición y ediciones locales preservadas.")
"""
                    subprocess.run([sys.executable, "-c", script_proyeccion], cwd=ROOT,
                                   env=app_env("proyeccion_fixture"), check=True)
                    script_semilla = """
import secrets
import sys
from tools.preparar_piloto_postgres import preparar
from data.database import Alumno, Usuario, get_session
from piloto_spa.backend.auth_service import verificar_password
password = sys.stdin.read()
preparar(password)
with get_session() as db:
    assert db.query(Alumno).count() == 2
    usuario = db.query(Usuario).one()
    assert usuario.usuario == "direccion.piloto" and verificar_password(password, usuario.password)
try:
    preparar(secrets.token_urlsafe(24))
except ValueError:
    pass
else:
    raise AssertionError("La preparación no debe cambiar cuentas existentes.")
"""
                    clave_direccion = secrets.token_urlsafe(24)
                    env_preparacion = app_env("preparacion")
                    subprocess.run([sys.executable, "-c", script_semilla], cwd=ROOT, text=True,
                                   input=clave_direccion, env=env_preparacion, check=True)
                    operativa = urls["preparacion"].set(username="spa_runtime_preparacion",
                                                        password=secrets.token_urlsafe(24))
                    with closing(psycopg2.connect(host="127.0.0.1", port=pg_port, dbname=operativa.database,
                                                  user="spa_bootstrap", password=bootstrap)) as db:
                        db.autocommit = True
                        with db.cursor() as cur:
                            cur.execute("CREATE ROLE spa_runtime_preparacion LOGIN PASSWORD %s", (operativa.password,))
                            cur.execute("GRANT CONNECT ON DATABASE usaer_spa_test_preparacion TO spa_runtime_preparacion")
                            cur.execute("GRANT USAGE ON SCHEMA public TO spa_runtime_preparacion")
                            cur.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO spa_runtime_preparacion")
                    from test_seguridad_piloto import certificado_local
                    env_tls = dict(env_preparacion, **certificado_local(carpeta), USAER_SPA_ROLE="runtime",
                                   USAER_SPA_POSTGRES_TEST_URL=operativa.render_as_string(hide_password=False))
                    with servidor(env_tls, carpeta) as cliente_tls:
                        login_tls = cliente_tls.post("/api/auth/login", headers={"X-USAER-Client": "browser"},
                                                     json={"usuario": "direccion.piloto", "password": clave_direccion})
                        self.assertEqual(login_tls.status_code, 200, login_tls.text)
                        self.assertIn("Secure", login_tls.headers["set-cookie"])
                        self.assertEqual(len(cliente_tls.get("/api/alumnos").json()), 2)
                        self.assertEqual(cliente_tls.get("/", headers={"Host": "host-ajeno.invalid"}).status_code, 400)
                    print("HTTPS local: certificado verificado y rol operativo PostgreSQL confirmados.")
                    url_migracion = urls["migracion_fixture"]
                    subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests",
                                    "-p", "test_migracion_paralela.py", "-v"], cwd=ROOT,
                                   env=dict(base_env, USAER_MIGRACION_TEST_URL=url_migracion.render_as_string(hide_password=False)),
                                   check=True)
                    respaldo = carpeta / "copia_migracion.dump"
                    conexion = ("-h", "127.0.0.1", "-p", pg_port)
                    pg("pg_dump", *conexion, "-U", url_migracion.username, "-Fc", "-n", "copia_usaer",
                       "-f", respaldo, url_migracion.database, env=dict(base_env, PGPASSWORD=url_migracion.password))
                    nueva = urls["migracion_restaurada"]
                    pg("pg_restore", *conexion, "-U", nueva.username, "--no-owner", "--exit-on-error",
                       "-d", nueva.database, respaldo, env=dict(base_env, PGPASSWORD=nueva.password))
                    with closing(psycopg2.connect(nueva.render_as_string(hide_password=False))) as db:
                        with db.cursor() as cur:
                            cur.execute("SELECT count(*) FROM copia_usaer.lote WHERE NOT revertido")
                            self.assertEqual(cur.fetchone()[0], 1)
                            cur.execute("SELECT count(*) FROM copia_usaer.orden")
                            self.assertGreater(cur.fetchone()[0], 20)
                            cur.execute("SELECT to_regclass('public.edicion_piloto')")
                            self.assertIsNone(cur.fetchone()[0])
                    print("Migración paralela: respaldo y restauración sintéticos verificados.")
                    if os.environ["USAER_MIGRACION_PRUEBA"] == "solo":
                        return

                with self.assertRaises(psycopg2.OperationalError):
                    psycopg2.connect(host="127.0.0.1", port=pg_port, dbname=urls["b"].database,
                                     user=urls["a"].username, password=urls["a"].password, connect_timeout=3)

                env_a, env_b = app_env("a"), app_env("b")
                for env in (env_a, env_b):
                    subprocess.run([sys.executable, "-c", SEED, PASSWORD], cwd=ROOT, env=env, check=True)
                extra = """
import sys
from data.database import Alumno, Escuela, Usuario, get_session
from piloto_spa.backend.auth_service import hash_password
with get_session() as db:
    db.add_all([Escuela(id="esc-A", nombre_escuela="Escuela ficticia A", cct="00DPR0001A"),
                Escuela(id="esc-B", nombre_escuela="Escuela ficticia B", cct="00DPR0002A")])
    db.add(Usuario(id="psi", usuario="psi", rol="PSICOLOGIA", escuelas_permitidas="esc-A",
                   password=hash_password(sys.argv[1])))
    db.add(Usuario(id="dir", usuario="dir", rol="DIRECTOR", escuelas_permitidas="TODAS",
                   password=hash_password(sys.argv[1])))
    db.add(Alumno(id="alu-as", nombre_completo="Alumno sintético AS", id_escuela="esc-A",
                  grado="2", grupo="A", tipo_atencion="Grupal", condicion_discapacidad="Aptitudes sobresalientes"))
    db.commit()
"""
                subprocess.run([sys.executable, "-c", extra, PASSWORD], cwd=ROOT, env=env_a, check=True)
                # Reproduce an existing pilot schema and apply only the new table.
                with closing(psycopg2.connect(env_a["DATABASE_URL"])) as db, db:
                    with db.cursor() as cur:
                        cur.execute("DROP TABLE informes_educativos_spa")
                subprocess.run([sys.executable, "tools/migrar_informes_spa.py"], cwd=ROOT,
                               env=dict(env_a, USAER_SPA_MODE="postgres-synthetic", USAER_SPA_ROLE="owner"),
                               check=True)

                def navegador_informes(cliente, fase):
                    if os.getenv("USAER_PLAYWRIGHT"):
                        subprocess.run(["node", str(ROOT / "tests/navegador_informes_spa.cjs"),
                                        str(cliente.base_url), fase], cwd=ROOT,
                                       env=dict(os.environ, USAER_TEST_PASSWORD=PASSWORD),
                                       check=True, timeout=90)

                def navegador_padron(cliente, fase):
                    if os.getenv("USAER_PLAYWRIGHT"):
                        subprocess.run(["node", str(ROOT / "tests/navegador_padron_spa.cjs"),
                                        str(cliente.base_url), fase], cwd=ROOT,
                                       env=dict(os.environ, USAER_TEST_PASSWORD=PASSWORD),
                                       check=True, timeout=90)

                def navegador_oficios(cliente, fase):
                    if os.getenv("USAER_PLAYWRIGHT"):
                        subprocess.run(["node", str(ROOT / "tests/navegador_oficios_spa.cjs"),
                                        str(cliente.base_url), fase], cwd=ROOT,
                                       env=dict(os.environ, USAER_TEST_PASSWORD=PASSWORD),
                                       check=True, timeout=90)

                with servidor(env_a, carpeta) as a:
                    login = a.post("/api/auth/login", json={"usuario": "a", "password": PASSWORD},
                                   headers={"X-USAER-Client": "browser"})
                    self.assertEqual(login.status_code, 200, login.text)
                    self.assertNotIn("token", login.json())
                    self.assertIn("HttpOnly", login.headers["set-cookie"])
                    token = a.cookies["usaer_spa_session"]
                    headers = {"X-USAER-Client": "browser"}
                    importacion = "/api/alumnos/importar-excel"
                    archivo = excel_padron("Padrón sintético importado")
                    vista = a.post(importacion, content=archivo, headers=headers)
                    self.assertEqual(vista.status_code, 200, vista.text)
                    self.assertEqual(vista.json()["errores"], [])
                    self.assertEqual(vista.json()["filas"][0]["accion"], "Alta")
                    self.assertFalse(any(r["nombre_completo"] == "Padrón sintético importado" for r in a.get("/api/alumnos").json()))
                    confirmar = {**headers, "X-USAER-Revision": vista.json()["revision"]}
                    self.assertEqual(a.post(importacion, content=excel_padron("Otro contenido"), headers=confirmar).status_code, 409)
                    self.assertEqual(a.post(importacion, content=archivo, headers=confirmar).json(), {"altas": 1, "actualizados": 0})
                    self.assertEqual(a.post(importacion, content=archivo, headers=confirmar).json(), {"altas": 0, "actualizados": 0})
                    archivo = excel_padron("Padrón sintético actualizado")
                    cambio_excel = a.post(importacion, content=archivo, headers=headers).json()
                    self.assertEqual(cambio_excel["filas"][0]["accion"], "Actualizar")
                    self.assertEqual(a.post(importacion, content=archivo, headers={
                        **headers, "X-USAER-Revision": cambio_excel["revision"],
                    }).json(), {"altas": 0, "actualizados": 1})
                    padron_id = next(r["id"] for r in a.get("/api/alumnos").json() if r["nombre_completo"] == "Padrón sintético actualizado")
                    ajeno_excel = a.post(importacion, content=excel_padron("Escuela ajena", "esc-B"), headers=headers)
                    self.assertTrue(ajeno_excel.json()["errores"])
                    self.assertEqual(ajeno_excel.json()["filas"], [])
                    exportacion = a.get("/api/alumnos/exportar.xlsx")
                    self.assertEqual(exportacion.status_code, 200, exportacion.text if exportacion.status_code != 200 else "")
                    with closing(load_workbook(BytesIO(exportacion.content), read_only=True)) as libro:
                        nombres = {celda for fila in libro["ALUMNOS USAER"].values for celda in fila}
                    self.assertIn("Padrón sintético actualizado", nombres)
                    self.assertNotIn("Alumno ficticio B", nombres)
                    estadisticas = a.get("/api/estadisticas/padron?escuela=esc-A")
                    self.assertEqual(estadisticas.status_code, 200, estadisticas.text)
                    self.assertEqual(estadisticas.json()["total_alumnos"], 3)
                    self.assertEqual(estadisticas.json()["sexo"]["hombres"], 1)
                    self.assertEqual(a.get("/api/estadisticas/padron?escuela=esc-B").status_code, 404)
                    alta_mov = a.post("/api/alumnos", headers=headers, json={
                        "nombre_completo": "Alumno sintético de movimientos", "id_escuela": "esc-A",
                        "curp": "ZZZZ160101HNEZZZ02", "grado": "6", "grupo": "Y", "edad_1_septiembre": "10",
                    })
                    self.assertEqual(alta_mov.status_code, 200, alta_mov.text)
                    alumno_mov = alta_mov.json()["id"]
                    informe_mov = a.post("/api/informes", headers=headers, json={
                        "alumno_id": alumno_mov, "ciclo": "2026-2027", "titulo": "Informe previo al traslado",
                    })
                    self.assertEqual(informe_mov.status_code, 201, informe_mov.text)
                    url_informe_mov = "/api/informes/" + informe_mov.json()["id"]
                    planes_mov = []
                    for modalidad in ("individual", "grupal"):
                        plan_mov = a.post("/api/planeaciones/nueva", headers=headers, json={
                            "modalidad": modalidad, "alumnos": [alumno_mov], "formato": "XXIII",
                        })
                        self.assertEqual(plan_mov.status_code, 200, plan_mov.text)
                        planes_mov.append(plan_mov.json()["id"])
                    url_ficha = f"/api/alumnos/{alumno_mov}/ficha"
                    url_mov = f"/api/alumnos/{alumno_mov}/movimientos"
                    ficha = a.get(url_ficha).json()
                    edicion = {"revision": ficha["revision"], "campos": {"Grupo": "X"}}
                    self.assertEqual(a.put(url_ficha, json=edicion, headers=headers).status_code, 200)
                    self.assertEqual(a.put(url_ficha, json=edicion, headers=headers).status_code, 409)
                    self.assertEqual(a.put(f"/api/alumnos/{alumno_mov}", json={"Estatus": "Baja"}, headers=headers).status_code, 422)
                    registro = a.post(f"/api/expedientes/{alumno_mov}/anexos/5",
                                      json={"campos": {"evento": "Evento previo al traslado"}}, headers=headers)
                    self.assertEqual(registro.status_code, 200, registro.text)
                    from reportlab.pdfgen import canvas
                    original = BytesIO()
                    documento = canvas.Canvas(original)
                    documento.drawString(40, 750, "Resultado de evaluación externa ficticia")
                    documento.save()
                    ruta_adjunto = f"/api/expedientes/{alumno_mov}/adjuntos"
                    adjunto_externo = a.post(ruta_adjunto, params={"nombre": "evaluacion-sintetica.pdf"},
                                             content=original.getvalue(),
                                             headers={**headers, "Content-Type": "application/pdf"})
                    self.assertEqual(adjunto_externo.status_code, 200, adjunto_externo.text)
                    ciclo_anterior = f"/api/epp/{alumno_mov}/anexo"
                    anterior = a.get(ciclo_anterior, params={"ciclo": "2025-2026"}).json()
                    valor_anterior = anterior["partes"]["Aprendizaje"]["contenido"]
                    valor_anterior["sintesis"] = "Antecedente sintético del ciclo anterior."
                    self.assertEqual(a.put(ciclo_anterior + "/Aprendizaje", params={"ciclo": "2025-2026"},
                                           headers=headers, json={"revision": anterior["revision"],
                                                                   "valor": valor_anterior}).status_code, 200)
                    instrumentos = f"/api/epp/{alumno_mov}/instrumentos"
                    self.assertIn("XIV", a.get(instrumentos).json())
                    self.assertNotIn("XVI", a.get(instrumentos).json())
                    self.assertEqual(a.put(instrumentos + "/XVI", headers=headers,
                                           json={"revision": "anterior", "captura": {}}).status_code, 404)
                    navegador_padron(a, "origen")
                    for accion in ("baja", "reactivacion", "traslado"):
                        ficha = a.get(url_ficha).json()
                        movimiento = a.post(url_mov, headers=headers, json={
                            "revision": ficha["revision"], "accion": accion, "motivo": "Movimiento sintético confirmado",
                            "escuela": "esc-B", "cuenta_destino": "B", "grado": "6", "grupo": "W",
                        })
                        self.assertEqual(movimiento.status_code, 200, movimiento.text)
                    self.assertEqual(a.get(url_ficha).status_code, 404)
                    self.assertEqual(a.get(f"/api/expedientes/{alumno_mov}").status_code, 404)
                    self.assertEqual(a.get(ruta_adjunto + "/" + adjunto_externo.json()["id"]).status_code, 404)
                    self.assertEqual(a.get(url_informe_mov).status_code, 404)
                    for doc_id in planes_mov:
                        for sufijo in ("", "/pdf", "/historial"):
                            self.assertEqual(a.get(f"/api/planeaciones/{doc_id}{sufijo}").status_code, 404)
                    celda_trasladada = {"tabla": "filas", "alumno": alumno_mov, "campo": "Aprendizaje",
                                         "revision": "", "texto": "Intento fuera de escuela"}
                    self.assertEqual(a.patch(f"/api/planeaciones/{planes_mov[1]}/celda", headers=headers,
                                             json=celda_trasladada).status_code, 404)
                    self.assertTrue(set(planes_mov).isdisjoint(p["id"] for p in a.get("/api/planeaciones").json()))
                    navegador_oficios(a, "crear")
                    informe = {"alumno_id": "alu-A", "ciclo": "2026-2027", "tipo": "seguimiento",
                               "titulo": "Informe de integración API", "avances": "Primer avance sintético"}
                    creado = a.post("/api/informes", json=informe, headers=headers)
                    self.assertEqual(creado.status_code, 201, creado.text)
                    informe_url = "/api/informes/" + creado.json()["id"]
                    recuperado = a.get(informe_url).json()
                    self.assertEqual(recuperado["avances"], informe["avances"])
                    cambio = {**informe, "revision": recuperado["revision"], "avances": "Avance editado"}
                    with ThreadPoolExecutor(max_workers=2) as pool:
                        ediciones = list(pool.map(
                            lambda _: a.put(informe_url, json=cambio, headers=headers), range(2)))
                    self.assertEqual(sorted(r.status_code for r in ediciones), [200, 409])
                    self.assertEqual(len(a.get(informe_url + "/historial").json()), 2)
                    self.assertTrue(a.get(informe_url + "/pdf").content.startswith(b"%PDF"))
                    docente_b = a.post("/api/auth/login", json={"usuario": "b", "password": PASSWORD}).json()["token"]
                    fuera = {"Authorization": f"Bearer {docente_b}"}
                    for url in (informe_url, informe_url + "/pdf", informe_url + "/historial",
                                "/api/informes?alumno_id=alu-A"):
                        self.assertEqual(a.get(url, headers=fuera).status_code, 404)
                    self.assertEqual(a.put(informe_url, json=cambio, headers=fuera).status_code, 404)
                    self.assertEqual(a.post("/api/informes", json=informe, headers=fuera).status_code, 404)
                    navegador_informes(a, "crear")
                    anexos = {}
                    for numero, campos in ((3, {"bap_pedagogicas": "Barrera sintética de lectura"}),
                                          (4, {"sugerencias": "Apoyo sintético para consignas"}),
                                          (5, {"evento": "Observación sintética de clase"})):
                        ruta_anexo = f"/api/expedientes/alu-A/anexos/{numero}"
                        alta_anexo = a.post(ruta_anexo, json={"campos": campos}, headers=headers)
                        self.assertEqual(alta_anexo.status_code, 200, alta_anexo.text)
                        datos_anexo = alta_anexo.json()
                        clave_anexo = next(iter(campos))
                        cambios_anexo = {"revision": datos_anexo["revision"],
                                        "campos": {clave_anexo: f"Seguimiento sintético del anexo {numero}"}}
                        ruta_registro = ruta_anexo + "/" + datos_anexo["id"]
                        cambio_anexo = a.put(ruta_registro, json=cambios_anexo, headers=headers)
                        self.assertEqual(cambio_anexo.status_code, 200, cambio_anexo.text)
                        self.assertEqual(a.put(ruta_registro, json=cambios_anexo, headers=headers).status_code, 409)
                        self.assertEqual(len(a.get(ruta_registro + "/historial").json()), 2)
                        pdf_anexo = a.get(ruta_anexo + "/pdf")
                        self.assertEqual(pdf_anexo.status_code, 200, pdf_anexo.text if pdf_anexo.status_code != 200 else "")
                        self.assertTrue(pdf_anexo.content.startswith(b"%PDF"))
                        anexos[numero] = (datos_anexo["id"], ruta_anexo, clave_anexo)
                    epp = a.get("/api/epp/alu-A").json()
                    epp["partes"]["PSICOLOGIA"]["desarrollo_emocional"] = "Edición fuera de área"
                    self.assertEqual(a.post("/api/epp", json=epp, headers=headers).status_code, 403)
                    epp = a.get("/api/epp/alu-A").json()
                    epp["partes"]["APRENDIZAJE"]["avances_observables"] = "Avance sintético PostgreSQL"
                    self.assertEqual(a.post("/api/epp", json=epp, headers=headers).status_code, 200)
                    alta = {"modalidad": "grupal", "alumnos": ["alu-A"], "formato": "XXIII"}
                    self.assertEqual(a.post("/api/planeaciones/nueva", json=alta).status_code, 403)
                    indebida = a.post("/api/planeaciones/nueva", json={**alta, "alumnos": ["alu-B"]}, headers=headers)
                    self.assertEqual(indebida.status_code, 404)
                    with ThreadPoolExecutor(max_workers=2) as pool:
                        respuestas = list(pool.map(lambda _: a.post("/api/planeaciones/nueva", json=alta, headers=headers), range(2)))
                    for respuesta in respuestas:
                        self.assertEqual(respuesta.status_code, 200, respuesta.text)
                    self.assertEqual(len({r.json()["id"] for r in respuestas}), 1)
                    respuesta = respuestas[0]
                    ruta = f"/api/planeaciones/{respuesta.json()['id']}"
                    plan = a.get(ruta).json()
                    self.assertEqual(plan["datos"]["Vigencia"], "2026-2027")
                    self.assertEqual(plan["metadatos"]["vinculos_documentales"][0]["alumno"], "alu-A")
                    plan["metadatos"]["titulo"] = "Revisión persistente A"
                    self.assertEqual(a.post("/api/planeaciones", json=plan, headers=headers).status_code, 200)
                    self.assertEqual(a.post("/api/planeaciones", json=plan, headers=headers).status_code, 409)
                    historial = a.get(ruta + "/historial").json()
                    self.assertEqual(len(historial), 2)
                    self.assertEqual(historial[0]["autor"], "a")
                    pdf = a.get(ruta + "/pdf")
                    self.assertEqual(pdf.status_code, 200, pdf.text if pdf.status_code != 200 else "")
                    self.assertTrue(pdf.content.startswith(b"%PDF"))
                    otro = a.post("/api/auth/login", json={"usuario": "b", "password": PASSWORD}).json()["token"]
                    self.assertEqual(a.get(ruta, headers={"Authorization": f"Bearer {otro}"}).status_code, 404)
                    referentes = a.get(ruta + "/referentes").json()
                    self.assertTrue(referentes)
                    self.assertEqual(a.post(ruta + "/propuesta", json={"pda_id": "inventado"}, headers=headers).status_code, 422)
                    propuesta = a.post(ruta + "/propuesta", json={"pda_id": referentes[0]["id"], "enfoque": "Lectura"},
                                      headers=headers)
                    self.assertEqual(propuesta.status_code, 200, propuesta.text)
                    respuesta = propuesta.json()
                    self.assertEqual(len(respuesta["indicadores"]), 14)
                    self.assertIn(referentes[0]["id"], respuesta["propuestas"][0]["referentes"])
                    self.assertTrue(any("EPP" in fuente for fuente in respuesta["propuestas"][0]["evidencias"]))
                    self.assertEqual(len(a.get(ruta + "/historial").json()), 2)
                    print(f"PostgreSQL local: {propuesta.elapsed.total_seconds():.3f} s para consulta de propuesta")
                    psi = a.post("/api/auth/login", json={"usuario": "psi", "password": PASSWORD}).json()["token"]
                    auth_psi = {"Authorization": f"Bearer {psi}"}
                    self.assertEqual(a.get("/api/planeaciones", headers=auth_psi).json()[0]["id"], ruta.rsplit("/", 1)[-1])
                    self.assertEqual(a.post("/api/planeaciones/nueva", json={**alta, "formato": "XXV"}, headers=auth_psi).json()["id"], ruta.rsplit("/", 1)[-1])
                    base_psi = a.get(ruta, headers=auth_psi).json()
                    doc = a.get(ruta).json()
                    doc["metadatos"]["guia_grupal_manual"]["filas"][0]["Aprendizaje"] = "Aporte pedagógico de apoyo"
                    self.assertEqual(a.post("/api/planeaciones", json=doc, headers=headers).status_code, 200)
                    base_psi["metadatos"]["guia_grupal_manual"]["filas"][0]["Psicología"] = "Aporte psicológico sintético"
                    self.assertEqual(a.post("/api/planeaciones", json=base_psi, headers=auth_psi).status_code, 409)
                    doc_psi = a.get(ruta, headers=auth_psi).json()
                    fila = doc_psi["metadatos"]["guia_grupal_manual"]["filas"][0]
                    fila["Aprendizaje"] = "No autorizado"
                    self.assertEqual(a.post("/api/planeaciones", json=doc_psi, headers=auth_psi).status_code, 403)
                    fila["Aprendizaje"] = "Aporte pedagógico de apoyo"
                    fila["Psicología"] = "Aporte psicológico sintético"
                    self.assertEqual(a.post("/api/planeaciones", json=doc_psi, headers=auth_psi).status_code, 200)
                    doc = a.get(ruta).json()
                    matricula = a.post(ruta + "/matricula", json={"revision": doc["revision"]}, headers=headers)
                    self.assertEqual(matricula.status_code, 200, matricula.text)
                    doc = a.get(ruta).json()
                    self.assertEqual(doc["metadatos"]["guia_grupal_manual"]["as"][0]["ID_Alumno"], "alu-as")
                    doc["metadatos"]["guia_grupal_manual"]["as"][0]["Aptitud intelectual"] = "Enriquecimiento sintético"
                    self.assertEqual(a.post("/api/planeaciones", json=doc, headers=headers).status_code, 200)
                    pdf = a.get(ruta + "/pdf")
                    self.assertEqual(pdf.status_code, 200)
                    import fitz
                    with fitz.open(stream=BytesIO(pdf.content), filetype="pdf") as impreso:
                        texto = " ".join(p.get_text() for p in impreso)
                    self.assertIn("Anexo XIX", texto)
                    self.assertIn("Anexo XX.", texto)
                    self.assertIn("Aporte psicológico", texto)
                    historial = a.get(ruta + "/historial").json()
                    self.assertIn("psi", {r["autor"] for r in historial})
                    director = a.post("/api/auth/login", json={"usuario": "dir", "password": PASSWORD}).json()["token"]
                    auth_dir = {"Authorization": f"Bearer {director}"}
                    acta_payload = {"alumno_id": "alu-A", "tipo_acta": "Acta de reunión",
                                    "fecha": "2026-10-12", "acuerdos": "Acuerdo ficticio inicial"}
                    self.assertEqual(a.post("/api/visitas", json=acta_payload, headers=headers).status_code, 403)
                    self.assertEqual(a.post("/api/visitas", json={**acta_payload, "alumno_id": "inexistente"},
                                            headers=auth_dir).status_code, 404)
                    acta = a.post("/api/visitas", json=acta_payload, headers=auth_dir)
                    self.assertEqual(acta.status_code, 200, acta.text)
                    url_acta = "/api/visitas/" + acta.json()["id"]
                    acta_editada = {**acta_payload, "revision": acta.json()["revision"],
                                    "acuerdos": "Acuerdo ficticio actualizado"}
                    self.assertEqual(a.put(url_acta, json=acta_editada, headers=auth_dir).status_code, 200)
                    self.assertEqual(a.put(url_acta, json=acta_editada, headers=auth_dir).status_code, 409)
                    self.assertEqual(len(a.get(url_acta + "/historial", headers=auth_dir).json()), 2)
                    self.assertTrue(a.get(url_acta + "/pdf", headers=auth_dir).content.startswith(b"%PDF"))
                    self.assertEqual(a.get(url_acta).status_code, 403)
                    anexo_url = "/api/epp/alu-A/anexo"
                    anexo = a.get(anexo_url, headers=auth_dir).json()
                    parte = anexo["partes"]["Aprendizaje"]["contenido"]
                    self.assertEqual(a.put(anexo_url + "/Aprendizaje", headers=auth_psi,
                                           json={"revision": anexo["revision"], "valor": parte}).status_code, 403)
                    self.assertEqual(a.get(anexo_url, headers={"Authorization": f"Bearer {otro}"}).status_code, 404)
                    for area in ("Aprendizaje", "Psicología", "Comunicación", "Trabajo Social"):
                        anexo = a.get(anexo_url, headers=auth_dir).json()
                        parte = anexo["partes"][area]["contenido"]
                        parte.update(validada=True, sintesis=f"Hallazgo sintético de {area}")
                        if area == "Aprendizaje":
                            parte["evaluaciones"] = [{"id": "instrumento-1", "nombre": "Observación estructurada",
                                                       "fecha": "2026-10-01", "texto": "Resultado sintético"}]
                        guardado = a.put(anexo_url + "/" + area, headers=auth_dir,
                                         json={"revision": anexo["revision"], "valor": parte})
                        self.assertEqual(guardado.status_code, 200, guardado.text)
                    anexo = a.get(anexo_url, headers=auth_dir).json()
                    conclusion = anexo["partes"]["Conclusión"]["contenido"]
                    conclusion["validada"] = True
                    conclusion["campos"]["7.1. Conclusión"] = "Conclusión interdisciplinaria sintética"
                    conclusion["bap"][0]["Tipo de barrera"] = "Consignas extensas sin apoyos visuales"
                    necesidad = "Necesita identificar ideas principales en textos breves"
                    conclusion["nee"][0]["NEE"] = necesidad
                    payload = {"revision": anexo["revision"], "valor": conclusion}
                    self.assertEqual(a.put(anexo_url + "/Conclusión", headers=auth_dir, json=payload).status_code, 422)
                    payload["nee"] = [{"texto": necesidad, "fundamento": "Observación estructurada 2026-10-01",
                                       "desde": "2026-01-01", "hasta": "2027-12-31"}]
                    guardado = a.put(anexo_url + "/Conclusión", headers=auth_dir, json=payload)
                    self.assertEqual(guardado.status_code, 200, guardado.text)
                    self.assertEqual(a.put(anexo_url + "/Conclusión", headers=auth_dir, json=payload).status_code, 409)
                    anexo = a.get(anexo_url).json()
                    self.assertTrue(anexo["conclusion_vigente"])
                    self.assertEqual(anexo["nee_vigentes"][0]["texto"], necesidad)
                    pdf_epp = a.get("/api/epp/alu-A/pdf")
                    self.assertEqual(pdf_epp.status_code, 200, pdf_epp.text if pdf_epp.status_code != 200 else "")
                    with fitz.open(stream=pdf_epp.content, filetype="pdf") as impreso:
                        texto = " ".join(p.get_text() for p in impreso)
                    self.assertIn("Anexo XVII", texto)
                    self.assertIn("Conclusión interdisciplinaria sintética", texto)
                    self.assertIn("Resultado sintético", texto)
                    self.assertIn("Trazabilidad de las NEE confirmadas", texto)
                    individual = a.post("/api/planeaciones/nueva", headers=headers,
                                        json={**alta, "modalidad": "individual"}).json()
                    ruta_ind = "/api/planeaciones/" + individual["id"]
                    doc_ind = a.get(ruta_ind).json()
                    nee_id = doc_ind["editor"]["nee_confirmadas"][0]["id"]
                    previo = a.post("/api/planeaciones/nueva", headers=headers,
                                    json={**alta, "modalidad": "individual", "formato": "XXI"})
                    self.assertEqual(previo.status_code, 200, previo.text)
                    previo_id = previo.json()["id"]
                    previo_doc = a.get("/api/planeaciones/" + previo_id).json()
                    previo_doc["metadatos"]["titulo"] = "Intervención previa sintética"
                    previo_doc["textos"]["Seguimiento"] = "Avance previo documentado"
                    self.assertEqual(a.post("/api/planeaciones", json=previo_doc, headers=headers).status_code, 200)
                    propuesta = a.post(ruta_ind + "/propuesta", headers=headers,
                                       json={"nee_id": nee_id, "pda_id": referentes[0]["id"]})
                    self.assertEqual(propuesta.status_code, 200, propuesta.text)
                    cadena = propuesta.json()["propuestas"][0]
                    self.assertTrue(cadena["descriptor"].startswith("Alumno ficticio A"))
                    self.assertEqual(cadena["nee"], necesidad)
                    self.assertTrue(any(previo_id in fuente for fuente in cadena["evidencias"]))
                    self.assertTrue(all(cadena[k] for k in ("pda", "apoyos", "temporalidad", "recursos", "evaluacion")))
                    self.assertEqual(a.post(ruta_ind + "/propuesta", headers=headers,
                                            json={"nee_id": "ajena", "pda_id": referentes[0]["id"]}).status_code, 422)


                bearer = {"Authorization": f"Bearer {token}"}
                with servidor(env_a, carpeta) as a:
                    navegador_oficios(a, "recuperar")
                    navegador_informes(a, "recuperar")
                    navegador_padron(a, "destino")
                    destino = a.post("/api/auth/login", json={"usuario": "b", "password": PASSWORD}).json()["token"]
                    cabecera_destino = {"Authorization": f"Bearer {destino}"}
                    self.assertEqual(a.get(url_informe_mov, headers=cabecera_destino).status_code, 404)
                    self.assertEqual(a.get(f"/api/informes?alumno_id={alumno_mov}", headers=cabecera_destino).json(), [])
                    for doc_id in planes_mov:
                        self.assertEqual(a.get(f"/api/planeaciones/{doc_id}", headers=cabecera_destino).status_code, 404)
                    self.assertEqual(a.get(url_ficha, headers=cabecera_destino).json()["escuela"], "esc-B")
                    historia = a.get(url_mov, headers=cabecera_destino).json()
                    self.assertEqual([r["documento"]["accion"] for r in historia[:3]], ["traslado", "reactivacion", "baja"])
                    exp_mov = a.get(f"/api/expedientes/{alumno_mov}", headers=cabecera_destino).json()
                    self.assertEqual(exp_mov["alumno"]["id"], alumno_mov)
                    self.assertIn("Evento previo al traslado", {r["evento"] for r in exp_mov["anexo5_eventos"]})
                    if os.getenv("USAER_PLAYWRIGHT"):
                        self.assertEqual([r["ciclo"] for r in exp_mov["comparativo_epp"]], ["2026-2027", "2025-2026"])
                    if os.getenv("USAER_PLAYWRIGHT"):
                        epp_mov = a.get(f"/api/epp/{alumno_mov}/anexo", headers=cabecera_destino).json()
                        aplicados = epp_mov["partes"]["Aprendizaje"]["contenido"]["evaluaciones"]
                        self.assertEqual(aplicados[0]["codigo"], "XIV")
                        externas = [r for r in aplicados if r.get("entrada") == "EXTERNA_REVISADA"]
                        self.assertEqual(len(externas), 1)
                        self.assertEqual(externas[0]["archivo_sha256"], adjunto_externo.json()["sha256"])
                        self.assertEqual(externas[0]["resultados"], "Hallazgo sintético actualizado.")
                    informe_token = a.post("/api/auth/login", json={"usuario": "a", "password": PASSWORD}).json()["token"]
                    vigente = a.get(informe_url, headers={"Authorization": f"Bearer {informe_token}"})
                    self.assertEqual(vigente.status_code, 200, vigente.text)
                    self.assertEqual(vigente.json()["avances"], "Avance editado")
                    expediente_padron = a.get(f"/api/expedientes/{padron_id}",
                                              headers={"Authorization": f"Bearer {informe_token}"})
                    self.assertEqual(expediente_padron.json()["alumno"]["nombre_completo"], "Padrón sintético actualizado")
                    expediente_seguimiento = a.get("/api/expedientes/alu-A",
                                                   headers={"Authorization": f"Bearer {informe_token}"})
                    self.assertEqual(expediente_seguimiento.status_code, 200, expediente_seguimiento.text)
                    seguimiento = expediente_seguimiento.json()["seguimiento"]
                    self.assertTrue({"Informe", "EPP", "BAP", "Sugerencia", "Evento significativo",
                                     "Plan individual"}.issubset({fila["tipo"] for fila in seguimiento}))
                    self.assertNotIn("Acta", {fila["tipo"] for fila in seguimiento})
                    dir_reinicio = a.post("/api/auth/login", json={"usuario": "dir", "password": PASSWORD}).json()["token"]
                    dir_headers = {"Authorization": f"Bearer {dir_reinicio}"}
                    self.assertEqual(a.get(url_informe_mov, headers=dir_headers).status_code, 200)
                    if os.getenv("USAER_PLAYWRIGHT"):
                        oficio = a.get("/api/oficios", headers=dir_headers).json()[0]
                        ruta_oficio = "/api/oficios/" + oficio["ID_Oficio"]
                        self.assertEqual(len(a.get(ruta_oficio + "/historial", headers=dir_headers).json()), 2)
                        self.assertEqual(a.get(ruta_oficio + "/pdf", headers=cabecera_destino).status_code, 403)
                        visual = os.environ.get("USAER_QA_OFICIO_DIR")
                        if visual:
                            from documents.oficios import generar_oficio_comision
                            destino_visual = Path(visual)
                            destino_visual.mkdir(parents=True, exist_ok=True)
                            (destino_visual / "spa.pdf").write_bytes(a.get(ruta_oficio + "/pdf", headers=dir_headers).content)
                            (destino_visual / "referencia.pdf").write_bytes(generar_oficio_comision({
                                "Folio": oficio["Folio"], "Fecha_Emision": "2026-10-01",
                                "Fecha_Comision": "2026-10-02", "Escuela": "Escuela ficticia",
                                "Director_Escuela": "Dirección ficticia", "Maestra_Apoyo": "Docente ficticio",
                                "Asunto": "Comisión sintética", "Destino": "Taller pedagógico sintético",
                                "Horario": "09:00 a 11:00",
                            }, incluir_firmas=False))
                    self.assertEqual(a.get(url_acta, headers=dir_headers).json()["alumno_id"], "alu-A")
                    seguimiento_dir = a.get("/api/expedientes/alu-A", headers=dir_headers).json()["seguimiento"]
                    self.assertIn("Acuerdo ficticio actualizado", {fila["detalle"] for fila in seguimiento_dir})
                    self.assertEqual(a.get("/api/me", headers=bearer).status_code, 200)
                    self.assertEqual(a.get(ruta, headers=bearer).json()["metadatos"]["titulo"], "Revisión persistente A")
                    for numero, (id_anexo, ruta_anexo, clave_anexo) in anexos.items():
                        registros = a.get(ruta_anexo, headers=bearer).json()
                        self.assertEqual(registros[0]["campos"][clave_anexo], f"Seguimiento sintético del anexo {numero}")
                        self.assertEqual(a.get(ruta_anexo + "/pdf", headers={"Authorization": f"Bearer {otro}"}).status_code, 404)
                    self.assertEqual(a.post("/api/auth/logout", headers=bearer).status_code, 200)
                    self.assertEqual(a.get("/api/me", headers=bearer).status_code, 401)
                with servidor(env_b, carpeta) as b:
                    self.assertEqual(b.get("/api/me", headers=bearer).status_code, 401)
                    respuesta = b.post("/api/auth/login", json={"usuario": "a", "password": PASSWORD})
                    auth_b = {"Authorization": f"Bearer {respuesta.json()['token']}"}
                    self.assertEqual(b.get("/api/planeaciones", headers=auth_b).json(), [])
                dump = carpeta / "synthetic.dump"
                conexion = ("-h", "127.0.0.1", "-p", pg_port)
                pg("pg_dump", *conexion, "-U", urls["a"].username, "-Fc", "--exclude-table-data=public.spa_sesiones", "-f", dump, urls["a"].database,
                   env=dict(base_env, PGPASSWORD=urls["a"].password))
                pg("pg_restore", *conexion, "-U", urls["recuperada"].username, "--no-owner", "--exit-on-error", "-d", urls["recuperada"].database, dump,
                   env=dict(base_env, PGPASSWORD=urls["recuperada"].password))
                with servidor(app_env("recuperada"), carpeta) as recuperada:
                    self.assertEqual(recuperada.get("/api/me", headers={"Authorization": f"Bearer {otro}"}).status_code, 401)
                    respuesta = recuperada.post("/api/auth/login", json={"usuario": "a", "password": PASSWORD})
                    auth = {"Authorization": f"Bearer {respuesta.json()['token']}"}
                    doc = recuperada.get(ruta, headers=auth)
                    self.assertEqual(doc.json()["metadatos"]["titulo"], "Revisión persistente A")
                    self.assertEqual(len(recuperada.get(ruta + "/historial", headers=auth).json()), 6)
                    guia = doc.json()["metadatos"]["guia_grupal_manual"]
                    self.assertEqual(guia["filas"][0]["Aprendizaje"], "Aporte pedagógico de apoyo")
                    self.assertEqual(guia["filas"][0]["Psicología"], "Aporte psicológico sintético")
                    anexo = recuperada.get("/api/epp/alu-A/anexo", headers=auth).json()
                    self.assertTrue(anexo["conclusion_vigente"])
                    self.assertEqual(anexo["nee_vigentes"][0]["texto"], necesidad)
                    epp = recuperada.get("/api/epp/alu-A", headers=auth).json()
                    self.assertEqual(epp["partes"]["APRENDIZAJE"]["avances_observables"], "Avance sintético PostgreSQL")
                if os.environ.get("USAER_PLAYWRIGHT"):
                    env_browser = app_env("recuperada")
                    for modo in ("editar", "verificar"):
                        with servidor(env_browser, carpeta) as navegador:
                            subprocess.run(["node", str(ROOT / "tests" / "navegador_flujos_spa.cjs"),
                                            str(navegador.base_url), PASSWORD, ruta.rsplit("/", 1)[-1],
                                            individual["id"], modo], cwd=ROOT, check=True, timeout=100)
                if os.environ.get("USAER_ETL"):
                    archivo = carpeta / "eventos-sinteticos.xlsx"
                    libro = Workbook()
                    hoja = libro.active
                    hoja.title = "EventosVersiones"
                    hoja.append(["ID_Evento", "ID_Alumno", "Revision", "Revision_Anterior", "Autor",
                                 "Fecha", "Fecha_Modificacion", "Evento"])
                    hoja.append(["evt-importado", "alu-A", "v1", "", "a", "2026-10-01",
                                 "2026-10-01T12:00:00-06:00", "Versión inicial"])
                    libro.save(archivo)
                    env_etl = dict(app_env("recuperada"), USAER_SPA_MODE="postgres-synthetic")
                    programa = """
from pathlib import Path
import sys
from tools.importar_eventos_sinteticos import conciliar
from data.database import Anexo5Evento, get_session
archivo = Path(sys.argv[1])
aplicar = sys.argv[2] == 'incremental'
if not aplicar:
    assert conciliar(archivo)['nuevas'] == 1
    with get_session(initialize_schema=False) as db:
        assert db.get(Anexo5Evento, 'evt-importado') is None
r = conciliar(archivo, aplicar=True)
assert r['nuevas'] == 1 and r['repetidas'] == int(aplicar), r
assert conciliar(archivo, aplicar=True)['nuevas'] == 0
"""
                    subprocess.run([sys.executable, "-c", programa, str(archivo), "inicial"],
                                   cwd=ROOT, env=env_etl, check=True)
                    hoja.append(["evt-importado", "alu-A", "v2", "v1", "a", "2026-10-01",
                                 "2026-10-02T12:00:00-06:00", "Versión incremental"])
                    libro.save(archivo)
                    subprocess.run([sys.executable, "-c", programa, str(archivo), "incremental"],
                                   cwd=ROOT, env=env_etl, check=True)
                    with servidor(app_env("recuperada"), carpeta) as etl:
                        token_etl = etl.post("/api/auth/login", json={"usuario": "a", "password": PASSWORD}).json()["token"]
                        res = etl.get("/api/expedientes/alu-A/anexos/5/evt-importado/historial",
                                      headers={"Authorization": f"Bearer {token_etl}"})
                        self.assertEqual([r["revision"] for r in res.json()], ["v2", "v1"])
                        self.assertEqual(res.json()[0]["documento"]["campos"]["evento"], "Versión incremental")
                if os.environ.get("USAER_CARGA_EVIDENCIA"):
                    from carga_piloto import ejecutar_carga, evidencia, memoria_mib
                    credenciales = [(f"carga{i:02}", secrets.token_urlsafe(22), f"alu-carga{i:02}",
                                     "Psicología" if i % 2 else "Aprendizaje") for i in range(25)]
                    seed_carga = """
import json, sys
from data.database import Alumno, Usuario, get_session
from piloto_spa.backend.auth_service import hash_password
with get_session() as db:
    for usuario, password, alumno, area in json.load(sys.stdin):
        rol = "PSICOLOGIA" if area == "Psicología" else "MAESTRA DE APOYO"
        db.add(Usuario(id=usuario, usuario=usuario, nombre=f"Cuenta ficticia {usuario}",
                       rol=rol, escuelas_permitidas="esc-A", password=hash_password(password)))
        db.add(Alumno(id=alumno, nombre_completo=f"Alumno ficticio {usuario}",
                      id_escuela="esc-A", grado="2", grupo="A", tipo_atencion="Grupal"))
    db.commit()
"""
                    env_carga = app_env("recuperada")
                    import json
                    subprocess.run([sys.executable, "-c", seed_carga], cwd=ROOT, env=env_carga,
                                   input=json.dumps(credenciales, ensure_ascii=True), text=True, check=True)
                    propietario = urls["recuperada"]
                    operativa = propietario.set(username="spa_runtime_recuperada", password=secrets.token_urlsafe(30))
                    with closing(psycopg2.connect(host="127.0.0.1", port=pg_port, dbname=propietario.database,
                                                  user="spa_bootstrap", password=bootstrap)) as permisos:
                        permisos.autocommit = True
                        with permisos.cursor() as cur:
                            rol = sql.Identifier(operativa.username)
                            cur.execute(sql.SQL("CREATE ROLE {} LOGIN PASSWORD %s").format(rol), (operativa.password,))
                            cur.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(sql.Identifier(propietario.database), rol))
                            cur.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(rol))
                            cur.execute(sql.SQL("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {}").format(rol))
                    with closing(psycopg2.connect(host="127.0.0.1", port=pg_port, dbname=operativa.database,
                                                  user=operativa.username, password=operativa.password)) as db:
                        with db.cursor() as cur:
                            with self.assertRaises(psycopg2.errors.InsufficientPrivilege):
                                cur.execute("CREATE TABLE public.no_debe_crearse (id integer)")
                    env_carga.update(USAER_SPA_POSTGRES_TEST_URL=operativa.render_as_string(hide_password=False),
                                     USAER_SPA_ROLE="runtime")
                    with servidor(env_carga, carpeta) as cliente_carga, closing(psycopg2.connect(
                        host="127.0.0.1", port=pg_port, user="spa_bootstrap", password=bootstrap,
                        dbname="postgres", connect_timeout=5
                    )) as metrica_db:
                        metrica_db.autocommit = True

                        def medir():
                            with metrica_db.cursor() as cur:
                                cur.execute("SELECT count(*) FROM pg_stat_activity WHERE datname=%s AND backend_type='client backend'",
                                            (urls["recuperada"].database,))
                                conexiones = cur.fetchone()[0]
                            return conexiones, memoria_mib(cliente_carga.usaer_pid)

                        login = cliente_carga.post("/api/auth/login", json={"usuario": "a", "password": PASSWORD})
                        self.assertEqual(login.status_code, 200, login.text)
                        auth = {"Authorization": f"Bearer {login.json()['token']}"}
                        doc = cliente_carga.get(ruta, headers=auth).json()
                        matricula = cliente_carga.post(ruta + "/matricula", headers=auth, json={"revision": doc["revision"]})
                        self.assertEqual(matricula.status_code, 200, matricula.text)
                        doc = cliente_carga.get(ruta, headers=auth).json()
                        revision = doc["metadatos"]["revisiones_celda"]["filas"]["alu-A"]["Aprendizaje"]
                        cambio = {"tabla": "filas", "alumno": "alu-A", "campo": "Aprendizaje", "revision": revision}
                        primero = cliente_carga.patch(ruta + "/celda", headers=auth, json={**cambio, "texto": "Primer aporte"})
                        self.assertEqual(primero.status_code, 200, primero.text)
                        segundo = cliente_carga.patch(ruta + "/celda", headers=auth, json={**cambio, "texto": "Segundo aporte"})
                        self.assertEqual(segundo.status_code, 409, segundo.text)
                        actual = segundo.json()["detail"]
                        self.assertEqual(actual["texto"], "Primer aporte")
                        resuelto = cliente_carga.patch(ruta + "/celda", headers=auth,
                            json={**cambio, "revision": actual["revision"], "texto": "Aportes conciliados"})
                        self.assertEqual(resuelto.status_code, 200, resuelto.text)

                        for latencia in (0, 180):
                            resultado = ejecutar_carga(cliente_carga.base_url, credenciales, ruta, medir, latencia_ms=latencia)
                            archivo = os.environ["USAER_CARGA_EVIDENCIA"]
                            evidencia(archivo if not latencia else str(Path(archivo).with_stem(Path(archivo).stem + "-180ms")), resultado)
                            print(json.dumps(resultado, ensure_ascii=True))
                            self.assertEqual(resultado["sesiones_distintas"], 25)
                            self.assertEqual(resultado["errores"], [])
                            self.assertEqual(resultado["aportes_confirmados"], 25)
                            doc = cliente_carga.get(ruta, headers=auth).json()
                            filas = {f["ID_Alumno"]: f for f in doc["metadatos"]["guia_grupal_manual"]["filas"]}
                            for cuenta, _, alumno, campo in credenciales:
                                self.assertEqual(filas[alumno][campo], f"Aporte sintético de {cuenta} ({latencia} ms)")
            finally:
                pg("pg_ctl", "-D", datos, "-w", "-m", "fast", "stop")


if __name__ == "__main__":
    unittest.main()

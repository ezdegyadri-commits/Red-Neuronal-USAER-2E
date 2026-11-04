from copy import deepcopy
import os
import unittest

import httpx
from sqlalchemy import text
from sqlalchemy.engine import make_url

from tools.migracion_paralela import MARCA, PESTANAS, destino, guardar, leer_sheets, recuperar, revertir, verificar_destino_local


def copia_sintetica():
    hojas = {n: [list(claves), ["fixture-" + k for k in claves]] for n, claves in PESTANAS.items()}
    hojas["Alumnos"] = [["ID_Alumno", "ID_Escuela", "Nombre_Completo"],
                        ["fixture-ID_Alumno", "fixture-ID_Escuela", "Estudiante ficticio"]]
    hojas["EPP_Versiones"] = [["Alumno", "Ciclo", "Parte", "Revision", "Autor", "Contenido"],
                             ["fixture-ID_Alumno", "2026-2027", "Aprendizaje", "v1", "Docente ficticio", "{}"]]
    hojas["Planeaciones_Versiones"][0].append("Alumnos_JSON")
    hojas["Planeaciones_Versiones"][1].append('["fixture-ID_Alumno"]')
    hojas["Relaciones_Documentos"] = [
        ["ID_Relacion", "Origen_Tipo", "Origen_ID", "Destino_Tipo", "Destino_ID"],
        ["fixture-relacion", "Planeaciones_Versiones", "fixture-Documento", "EPP_Versiones", "fixture-ID_Alumno"],
    ]
    return {"marca": MARCA, "origen": "fixture-paralela", "pestanas": hojas}


class CopiaSheets(unittest.TestCase):
    def test_destino_remoto_o_override_se_rechaza_antes_de_conectar(self):
        url = make_url("postgresql://spa_fixture_migracion_ensayo@127.0.0.1/usaer_spa_test_migracion_ensayo")
        verificar_destino_local(url, "migracion")
        for destino_invalido in (url.set(host="postgres.example.invalid"),
                                 url.update_query_dict({"host": "postgres.example.invalid"}),
                                 url.set(username="cuenta-no-aislada")):
            with self.assertRaises(ValueError):
                verificar_destino_local(destino_invalido, "migracion")

    def test_solo_get_copia_marcada_y_exclusion_de_cuentas(self):
        identificador = "copia_ficticia_de_prueba_001"
        peticiones = []

        def responder(request):
            self.assertEqual(request.method, "GET")
            self.assertEqual(request.url.host, "sheets.googleapis.com")
            peticiones.append(request)
            if request.url.path.endswith("values:batchGet"):
                self.assertEqual(request.url.params.get_list("ranges"), ["'Escuelas'", "'Alumnos'"])
                return httpx.Response(200, json={"spreadsheetId": identificador, "valueRanges": [
                    {"range": "Escuelas!A1:A2", "values": [["ID_Escuela"], ["ESC-FICTICIA"]]},
                    {"range": "Alumnos!A1:B2", "values": [["ID_Alumno", "ID_Escuela"], ["FICTICIO", "ESC-FICTICIA"]]},
                ]})
            return httpx.Response(200, json={"properties": {"title": MARCA}, "sheets": [
                {"properties": {"title": nombre}} for nombre in ("Escuelas", "Alumnos", "Usuarios")
            ]})

        with httpx.Client(transport=httpx.MockTransport(responder)) as cliente:
            copia = leer_sheets(identificador, "token-simulado", cliente=cliente)
        self.assertEqual(len(peticiones), 2)
        self.assertEqual(set(copia["pestanas"]), {"Escuelas", "Alumnos"})

    def test_titulo_incorrecto_detiene_antes_de_leer_celdas(self):
        peticiones = []
        def responder(request):
            peticiones.append(request)
            return httpx.Response(200, json={"properties": {"title": "otra copia"}})
        with httpx.Client(transport=httpx.MockTransport(responder)) as cliente:
            with self.assertRaises(ValueError):
                leer_sheets("copia_ficticia_de_prueba_001", "token-simulado", cliente=cliente)
        self.assertEqual(len(peticiones), 1)
        self.assertNotIn("values", peticiones[0].url.path)

    def test_conciliacion_no_imprime_valores_y_rechaza_credenciales(self):
        copia = copia_sintetica()
        copia["pestanas"]["Alumnos"][1][1] = "escuela-no-conciliada"
        informe = guardar(None, copia)
        self.assertEqual(informe["pestanas"]["Alumnos"]["errores"]["escuela_no_encontrada"], 1)
        self.assertEqual(informe["pestanas"]["Relaciones_Documentos"]["errores"]["extremos_no_conciliados"], 0)
        self.assertNotIn("Estudiante ficticio", str(informe))
        copia["pestanas"]["Alumnos"][0].append("Contraseña")
        with self.assertRaises(ValueError):
            guardar(None, copia)


@unittest.skipUnless(os.getenv("USAER_MIGRACION_TEST_URL"), "Requiere PostgreSQL sintético independiente.")
class CopiaPostgres(unittest.TestCase):
    def test_incremental_reversion_y_preservacion_de_ediciones(self):
        engine = destino()
        copia = copia_sintetica()
        vista = guardar(None, copia)
        with engine.begin() as db:
            db.execute(text("CREATE TABLE public.edicion_piloto (contenido text)"))
            db.execute(text("INSERT INTO public.edicion_piloto VALUES ('Edición docente independiente')"))
            self.assertIsNone(db.execute(text("SELECT to_regclass('copia_usaer.lote')")).scalar())
        alta = guardar(engine, copia, aplicar=True)
        self.assertEqual(alta["lote"], vista["lote"])
        self.assertEqual(alta["huellas_verificadas"], len(PESTANAS))
        self.assertEqual(recuperar(engine, alta["lote"]), copia)
        repetida = guardar(engine, copia, aplicar=True)
        self.assertTrue(repetida["repetido"])
        self.assertEqual(repetida["filas_nuevas_en_archivo"], 0)
        siguiente = deepcopy(copia)
        siguiente["pestanas"]["EPP_Versiones"].append(
            ["fixture-ID_Alumno", "2026-2027", "Aprendizaje", "v2", "Docente ficticio", '{"sintesis":"avance"}'])
        incremental = guardar(engine, siguiente, aplicar=True)
        self.assertEqual(incremental["filas_nuevas_en_archivo"], 1)
        revertir(engine, incremental["lote"])
        with self.assertRaises(ValueError):
            recuperar(engine, incremental["lote"])
        with self.assertRaises(ValueError):
            guardar(engine, siguiente, aplicar=True)
        self.assertTrue(guardar(engine, copia, aplicar=True)["repetido"])
        with engine.connect() as db:
            self.assertEqual(db.execute(text("SELECT contenido FROM public.edicion_piloto")).scalar_one(),
                             "Edición docente independiente")
            self.assertEqual(db.execute(text("SELECT count(*) FROM copia_usaer.lote WHERE NOT revertido")).scalar_one(), 1)


if __name__ == "__main__":
    unittest.main()

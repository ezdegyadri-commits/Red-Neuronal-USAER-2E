from copy import deepcopy
import unittest
from unittest.mock import patch

import httpx
from sqlalchemy.engine import make_url

from tools.copia_controlada import (MARCA_REAL, empaquetar, leer_captura_paginada, leer_lote_sheets,
                                   permiso_real, verificar_destino, verificar_paquete)
from tools.migracion_paralela import MARCA


class CopiaControlada(unittest.TestCase):
    def test_paginas_conservan_mas_de_veinte_alumnos(self):
        from unittest.mock import Mock

        hojas = {"Escuelas": [["ID_Escuela", "Nombre_Escuela"], ["esc-f", "Ficticia"]],
                 "Alumnos": [["ID_Alumno", "ID_Escuela"], *[[f"fic-{i}", "esc-f"] for i in range(37)]]}
        rangos = []

        def pagina(cliente, libro, solicitado, encabezados):
            import re

            nombre, rango = next(iter(solicitado.items()))
            rangos.append(rango)
            inicio, fin = map(int, re.findall(r"\d+", rango))
            return {nombre: hojas[nombre][inicio-1:fin]}

        with patch("tools.copia_controlada.leer_lote_sheets", side_effect=pagina):
            resultado = leer_captura_paginada(Mock(), "copia", {
                n: {"ultima_fila": len(filas), "ultima_columna": "B"} for n, filas in hojas.items()
            }, {}, tamano=10)
        self.assertEqual(resultado, hojas)
        self.assertEqual(rangos, ["A1:B2", "A1:B10", "A11:B20", "A21:B30", "A31:B38"])
        paquete = empaquetar({"marca": MARCA, "origen": "ficticio", "pestanas": resultado},
                             "esc-f", "2026-01-01T00:00:00Z", clase="ensayo")
        self.assertEqual(paquete["manifiesto"]["pestanas"]["Alumnos"]["filas"], 37)

    def test_get_acotado_y_sin_pestanas_de_acceso(self):
        llamadas = []
        libro = "copia_ficticia_de_ensayo"

        def responder(request):
            llamadas.append(request)
            self.assertEqual(request.method, "GET")
            self.assertEqual(request.url.host, "sheets.googleapis.com")
            self.assertEqual(request.url.params.get_list("ranges"), ["'Escuelas'!A1:B2"])
            return httpx.Response(200, json={"spreadsheetId": libro, "valueRanges": [
                {"range": "Escuelas!A1:B2", "values": [["ID_Escuela", "Nombre_Escuela"], ["f", "Ficticia"]]},
            ]})

        with httpx.Client(transport=httpx.MockTransport(responder)) as cliente:
            self.assertIn("Escuelas", leer_lote_sheets(cliente, libro, {"Escuelas": "A1:B2"}, {}))
            with self.assertRaises(ValueError):
                leer_lote_sheets(cliente, libro, {"Usuarios": "A1:B2"}, {})
        self.assertEqual(len(llamadas), 1)

    def test_perfiles_y_escuelas_separados(self):
        copia = {"marca": MARCA, "origen": "ficticio", "pestanas": {
            "Escuelas": [["ID_Escuela"], ["esc-f"]],
            "Alumnos": [["ID_Alumno", "ID_Escuela"], ["alu-f", "esc-f"]],
        }}
        fecha = "2026-01-01T10:00:00+00:00"
        paquete = empaquetar(copia, "esc-f", fecha, clase="ensayo")
        self.assertEqual(verificar_paquete(paquete, clase="ensayo")["capturada"], fecha)
        alterado = deepcopy(paquete)
        alterado["copia"]["pestanas"]["Alumnos"][1][0] = "otro-id"
        with self.assertRaises(ValueError):
            verificar_paquete(alterado)
        self.assertEqual(paquete["manifiesto"]["pestanas"]["Alumnos"]["filas"], 1)
        ajena = deepcopy(copia)
        ajena["pestanas"]["Alumnos"][1][1] = "otra"
        with self.assertRaises(ValueError):
            empaquetar(ajena, "esc-f", fecha, clase="ensayo")
        with self.assertRaises(ValueError):
            empaquetar({**copia, "marca": MARCA_REAL}, "esc-f", fecha, clase="ensayo")
        with patch.dict("os.environ", {"USAER_COPIA_PRIVADA_AUTORIZADA": "0"}):
            with self.assertRaises(ValueError):
                permiso_real("ACTA-0001")
        url = make_url("postgresql+psycopg://copia_ensayo_fixture@127.0.0.1:15432/usaer_copia_ensayo_fixture")
        verificar_destino(url, "ensayo")
        with self.assertRaises(ValueError):
            verificar_destino(url, "real")
        with self.assertRaises(ValueError):
            verificar_destino(url.set(host="servidor.example.invalid"), "ensayo")

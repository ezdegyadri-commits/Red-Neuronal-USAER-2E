import copy
import unittest
from io import BytesIO
from unittest.mock import patch
from pathlib import Path

import pandas as pd
from PIL import Image
from services import tramites as api
from documents.tramites import generar_respuesta, _texto
from ui.pages import _visitas_visibles, _es_acta_reunion


class TramitesTest(unittest.TestCase):
    def setUp(self):
        self.state = {"nombre": "Marycruz Caamal Coral", "rol": "Maestra de Apoyo"}
        self.db = {api.HOJA: [], api.ARCHIVOS: []}
        self.oficios = []
        self.alumnos = pd.DataFrame([{"ID_Alumno": "ALU-224", "Nombre_Completo": "Alumno de prueba", "Nombre_Escuela": "Ichcaanziho"}])
        for p in [patch.object(api.st, "session_state", self.state),
                  patch.object(api, "_leer", side_effect=lambda h: copy.deepcopy(self.db[h])),
                  patch.object(api, "_anexar", side_effect=lambda h, cols, rows: self.db[h].extend(copy.deepcopy(rows))),
                  patch.object(api, "alumnos_visibles", return_value=self.alumnos),
                  patch.object(api.repo, "oficios_comision", side_effect=lambda: pd.DataFrame(self.oficios)),
                  patch.object(api.repo, "guardar_oficio_comision", side_effect=self.guardar_oficio)]:
            p.start()
            self.addCleanup(p.stop)

    def guardar_oficio(self, datos):
        row = dict(datos, ID_Oficio="OF-024", Folio=24)
        self.oficios.append(row)
        return row

    def diego(self):
        self.state.update(nombre="Diego Peralta Torres", rol="Trabajo Social")

    def interna(self):
        return api.crear_solicitud("Interna", "Solicito revisión del expediente", "REQ-1", ["ALU-224"])

    def test_roles(self):
        self.assertTrue(api.puede_solicitar())
        self.assertFalse(api.gestor())
        self.diego()
        self.assertTrue(api.gestor())
        self.assertFalse(api.puede_solicitar())
        self.state.update(nombre="María José Cupul Realpozo", rol="Psicología")
        self.assertFalse(api.gestor())
        with self.assertRaises(PermissionError):
            api.solicitudes()
        self.state.update(nombre="Psic. Edgar Adrián Yam Briceño MD", rol="Director")
        self.assertTrue(api.gestor())

    def test_internal_revalidates_student_assignment(self):
        with self.assertRaises(PermissionError):
            api.crear_solicitud("Interna", "Expediente", "REQ-2", ["OTRO"])
        self.assertEqual(self.db[api.HOJA], [])
        r = self.interna()
        self.assertEqual(r["Escuela"], "Ichcaanziho")
        self.assertEqual(r["Alumnos"], "Alumno de prueba")

    def test_same_request_not_duplicated(self):
        first = self.interna()
        self.assertEqual(first, self.interna())
        self.assertEqual(len(self.db[api.HOJA]), 1)

    def test_teacher_only_own_requests(self):
        self.interna()
        self.state["nombre"] = "María Cecilia Solís Vázquez"
        self.assertEqual(api.solicitudes(), [])
        with self.assertRaises(PermissionError):
            api.consultar("REQ-1")

    def test_external_only_manager_no_roster_mutations(self):
        with self.assertRaises(PermissionError):
            api.crear_solicitud("Externa", "Expediente", "EXT", origen="CAM", alumnos="Alumno")
        self.diego()
        r = api.crear_solicitud("Externa", "Expediente", "EXT", origen="CAM de prueba", alumnos="Alumno externo")
        self.assertEqual(r["ID_Alumnos"], "[]")
        self.assertEqual(r["Tipo"], "Externa")
        self.assertEqual(len(self.alumnos), 1)

    def test_followup_append_preserves_previous_and_rejects_stale(self):
        old = self.interna()
        self.diego()
        new = api.actualizar("REQ-1", old["Revision"], "En revisión", "En seguimiento")
        self.assertEqual(self.db[api.HOJA][0], old)
        self.assertEqual(len(self.db[api.HOJA]), 2)
        self.assertEqual(api.consultar("REQ-1"), new)
        with self.assertRaises(ValueError):
            api.actualizar("REQ-1", old["Revision"], "Entregada", "")

    def test_teacher_cannot_change_status(self):
        r = self.interna()
        with self.assertRaises(PermissionError):
            api.actualizar("REQ-1", r["Revision"], "Entregada", "")

    def test_reply_reuses_folio_and_original_body(self):
        self.interna()
        self.diego()
        first = api.emitir_respuesta("REQ-1", "Dirección solicitante", "En respuesta a su solicitud, se informa el seguimiento acordado.")
        second = api.emitir_respuesta("REQ-1", "Otro", "No se debe sustituir")
        self.assertEqual(first, second)
        self.assertEqual(len(self.oficios), 1)
        self.assertEqual(api.consultar("REQ-1")["Estado"], "En preparación")
        self.assertEqual(api.oficio_guardado("REQ-1")["Folio"], 24)

    def test_link_retry_does_not_consume_another_folio(self):
        self.interna()
        self.diego()
        with patch.object(api, "actualizar", side_effect=RuntimeError("Interrupción")):
            with self.assertRaises(RuntimeError):
                api.emitir_respuesta("REQ-1", "Dirección", "Respuesta original")
        api.emitir_respuesta("REQ-1", "Dirección", "Respuesta repetida")
        self.assertEqual(len(self.oficios), 1)
        self.assertEqual(api.consultar("REQ-1")["ID_Oficio"], "OF-024")

    def imagen(self):
        stream = BytesIO()
        Image.new("RGB", (64, 64), "blue").save(stream, format="PNG")
        return stream.getvalue()

    def test_attachment_roundtrip_deduplicated_private(self):
        self.interna()
        self.diego()
        data = self.imagen()
        key = api.guardar_imagen("REQ-1", "Acuse de recibido", "acuse.png", data)
        count = len(self.db[api.ARCHIVOS])
        self.assertEqual(key, api.guardar_imagen("REQ-1", "Acuse de recibido", "acuse.png", data))
        self.assertEqual(len(self.db[api.ARCHIVOS]), count)
        self.assertEqual(api.descargar_imagen("REQ-1", key), data)
        self.state.update(nombre="María Cecilia Solís Vázquez", rol="Maestra de Apoyo")
        with self.assertRaises(PermissionError):
            api.descargar_imagen("REQ-1", key)

    def test_invalid_attachment_rejected(self):
        self.interna()
        self.diego()
        with self.assertRaises((ValueError, OSError)):
            api.guardar_imagen("REQ-1", "Oficio recibido", "mal.png", b"No es imagen")
        self.assertEqual(self.db[api.ARCHIVOS], [])

    def test_incomplete_attachment_not_exposed(self):
        self.interna()
        self.db[api.ARCHIVOS].append({"ID_Tramite": "REQ-1", "ID_Adjunto": "parcial", "Total": "2", "Indice": "0"})
        self.assertEqual(api.adjuntos("REQ-1"), [])

    def test_junta_visible_at_any_school_only_for_its_author(self):
        records = pd.DataFrame([
            {"ID_Visita": "J1", "Personal": "Abril de María Chable Ríos", "Escuela": "Ichcaanziho", "Tipo_Acta": "Junta de USAER"},
            {"ID_Visita": "V1", "Personal": "Abril de María Chable Ríos", "Escuela": "Ichcaanziho", "Tipo_Acta": "Constancia de visita"},
            {"ID_Visita": "J2", "Personal": "Marilyn Pérez Lizama", "Escuela": "Ichcaanziho", "Tipo_Acta": "Junta de USAER"},
        ])
        visible = _visitas_visibles(records, "Abril de María Chable Ríos", "Psicología", ["Domingo Solís Rodríguez"])
        self.assertEqual(visible.ID_Visita.tolist(), ["J1"])
        self.assertTrue(_es_acta_reunion(records.iloc[0]))

    def test_pdf_signature_kept_with_body_and_original_accents(self):
        from pypdf import PdfReader
        row = dict(Fecha_Emision="2026-10-02", Folio=24, Director_Escuela="Dirección de la USAER solicitante", Destino="Se informa el seguimiento a la solicitud de expedientes. " * 65)
        data = generar_respuesta(row)
        reader = PdfReader(BytesIO(data))
        text = reader.pages[-1].extract_text()
        self.assertIn("Edgar Adrián Yam Briceño", text)
        self.assertIn("seguimiento", text)
        self.assertIn("Director de la USAER", text)
        self.assertEqual(_texto("María José"), "María José")
        with self.assertRaises(ValueError):
            _texto("Texto con 😀")


if __name__ == "__main__":
    unittest.main()


class TramitesUITest(unittest.TestCase):
    def test_junta_location_lists_all_eight_without_associated_school(self):
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_file(str(Path(__file__).parent / "fixtures" / "junta_acta_app.py"), default_timeout=30).run()
        self.assertEqual(len(at.exception), 0)
        next(r for r in at.radio if r.label == "Tipo de acta").set_value("Junta de USAER").run()
        self.assertEqual(len(at.exception), 0)
        escuela = next(s for s in at.selectbox if s.label == "Escuela donde se realizó la junta")
        self.assertEqual(len(escuela.options), 8)
        self.assertIn("Ichcaanziho", escuela.options)
        self.assertFalse(any(s.label == "Escuela relacionada" for s in at.selectbox))
        next(r for r in at.radio if r.label == "Tipo de acta").set_value("Constancia de visita").run()
        self.assertEqual(len(next(s for s in at.selectbox if s.label == "Escuela visitada").options), 4)

    def test_teacher_request_manager_response_and_download(self):
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_file(str(Path(__file__).parent / "fixtures" / "tramites_app.py"), default_timeout=30).run()
        self.assertEqual(len(at.exception), 0)
        at.multiselect[0].select("TEST-1")
        at.text_area[0].set_value("Solicito el expediente para seguimiento educativo.")
        next(b for b in at.button if b.label == "Enviar solicitud a Trabajo Social").click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(len(at.session_state["test_db"][api.HOJA]), 1)
        at.session_state["nombre"] = "Diego Peralta Torres"
        at.session_state["rol"] = "Trabajo Social"
        at.run()
        self.assertEqual(len(at.exception), 0)
        next(t for t in at.text_input if t.label == "Destinatario y cargo").set_value("Dirección de la escuela")
        next(t for t in at.text_area if t.label == "Respuesta").set_value("Se da seguimiento a su solicitud de expedientes.")
        next(b for b in at.button if b.label == "Preparar oficio y asignar folio").click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(len(at.session_state["test_oficios"]), 1)
        self.assertEqual(len(at.get("download_button")), 1)
        at.run()
        self.assertEqual(len(at.get("download_button")), 1)
        at.session_state["nombre"] = "María Cecilia Solís Vázquez"
        at.session_state["rol"] = "Maestra de Apoyo"
        at.run()
        self.assertEqual(len(at.dataframe), 0)
        self.assertEqual(len(at.get("download_button")), 0)

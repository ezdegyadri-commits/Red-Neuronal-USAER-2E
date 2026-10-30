"""Regresiones sin red ni información real: recibos y carga bajo demanda."""
from contextlib import ExitStack
from copy import deepcopy
from unittest import TestCase
from unittest.mock import MagicMock, patch
import pandas as pd


class ExpedienteTests(TestCase):
    def renderizar(self, preview=False):
        from ui import pages
        student={"ID_Alumno":"FICTICIO","Nombre_Completo":"Alumno ficticio"}
        frame=pd.DataFrame([{"ID_Alumno":"FICTICIO","Fecha":"2026-10-30"}])
        exp=dict(alumno=student,id_expediente="EXP-FICTICIO",anexo3=frame,
                 anexo4=frame,anexo5=frame,timeline=pd.DataFrame())
        ui=MagicMock();ui.session_state={};ui.columns.return_value=[MagicMock() for _ in range(4)]
        ui.tabs.return_value=[MagicMock() for _ in range(5)]
        ui.toggle.return_value=preview
        names=("anexo3_pdf","anexo4_pdf","anexo5_pdf","anexo3_html","anexo4_html","anexo5_html")
        with ExitStack() as stack:
            stack.enter_context(patch.object(pages,"st",ui))
            stack.enter_context(patch.object(pages,"hero"))
            stack.enter_context(patch.object(pages,"card"))
            stack.enter_context(patch.object(pages,"_panel_analisis_atencion"))
            stack.enter_context(patch.object(pages,"_seleccionar_alumno",return_value=("FICTICIO",student)))
            stack.enter_context(patch.object(pages,"expediente",return_value=exp))
            generators={n:stack.enter_context(patch.object(pages,n,return_value=b"contenido ficticio")) for n in names}
            pages._expediente_individual(pd.DataFrame([student]))
            calls={n:m.call_count for n,m in generators.items()}
            downloads=[c.args[1] for c in ui.download_button.call_args_list]
            return calls,downloads,generators

    def test_ningun_pdf_ni_html_se_genera_antes_de_pedirlo(self):
        calls,downloads,generators=self.renderizar()
        self.assertTrue(all(n==0 for n in calls.values()))
        self.assertEqual(len(downloads),5)
        self.assertTrue(all(callable(x) for x in downloads))
        self.assertEqual(downloads[0](),b"contenido ficticio")
        self.assertEqual(generators["anexo3_pdf"].call_count,1)

    def test_vista_previa_solo_cuando_se_abre(self):
        calls,_,_=self.renderizar(preview=True)
        for n,count in calls.items():
            self.assertEqual(count,1 if n.endswith("_html") else 0)


class ReciboTests(TestCase):
    def test_recibo_epp_no_afirma_guardado_central(self):
        from ui import epp_viva as ui
        nuevo={"id":"FICTICIO"}
        state={"p_doc":{"id":"FICTICIO"}}
        def preparar(p,doc,areas):
            state[p+"_doc"]=doc
            state[p+"_pending"]=True
        with patch.object(ui.st,"session_state",state),patch.object(ui.papel,"aplicar",return_value=(nuevo,["Aprendizaje"])),patch.object(ui,"preparar_cambios",side_effect=preparar),patch.object(ui,"guardar",return_value=False):
            ui.recibir("p",{"nonce":"recibo-epp","accion":"guardar","huella":"base"})
        self.assertEqual(state["p_recibido"],"recibo-epp")
        self.assertTrue(state["p_pending"])
        self.assertNotIn("p_aceptado",state)

    def test_recibo_local_no_afirma_guardado_central(self):
        from ui import planeacion_papel as ui,planeacion as u
        doc={"id":"FICTICIO","texto":"antes"}
        nuevo={"id":"FICTICIO","texto":"recibido"}
        state={"p_doc":doc}
        def abrir(prefix,data):
            state[prefix+"_doc"]=deepcopy(data)
        def persistir(*a,**kw):
            state["p_pending"]=True
            return False
        with patch.object(ui.st,"session_state",state),patch.object(ui.papel,"aplicar",return_value=nuevo),patch.object(u,"_open",side_effect=abrir),patch.object(u,"_persist",side_effect=persistir):
            ui.recibir_edicion("p",{"nonce":"n-ficticio","accion":"guardar"})
        self.assertEqual(state["p_papel_recibido"],"n-ficticio")
        self.assertTrue(state["p_pending"])
        self.assertNotIn("p_papel_aceptado",state)
        self.assertEqual(state["p_doc"],nuevo)

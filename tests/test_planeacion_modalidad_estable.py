import unittest
from unittest.mock import patch
from ui import planeacion_viva as ui


class ModalidadEstableTests(unittest.TestCase):
    def test_desmarcar_no_convierte_grupal_a_individual(self):
        estado={}
        with patch.object(ui.st,'session_state',estado):
            ui._conservar_modalidad('modo',['Individual','Grupal'],'Grupal')
            self.assertEqual(estado['modo'],'Grupal')
            estado['modo']=None
            ui._conservar_modalidad('modo',['Individual','Grupal'],'Grupal')
            self.assertEqual(estado['modo'],'Grupal')
            estado['modo']='Individual'
            ui._conservar_modalidad('modo',['Individual','Grupal'],'Grupal')
            estado['modo']=None
            ui._conservar_modalidad('modo',['Individual','Grupal'],'Grupal')
            self.assertEqual(estado['modo'],'Individual')

    def test_selector_invalido_no_cambia_borrador_pendiente(self):
        doc={'id':'ficticio','texto':'Pendiente de guardar'}
        estado={'modo':'No válido','borrador_doc':doc,'borrador_pending':True}
        with patch.object(ui.st,'session_state',estado):
            ui._conservar_modalidad('modo',['Individual','Mi intervención'],'Mi intervención')
        self.assertEqual(estado['modo'],'Mi intervención')
        self.assertIs(estado['borrador_doc'],doc)
        self.assertTrue(estado['borrador_pending'])

from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from data.google import retry_google
from data import google as g
from requests.exceptions import ReadTimeout


class FakeAPIError(Exception):
    def __init__(self, status):
        super().__init__("Google API request failed")
        self.response = SimpleNamespace(status_code=status)


class GoogleRetryTest(unittest.TestCase):
    def setUp(self):
        self.patch=patch.object(g,'_cuota_hasta',0.0);self.patch.start();self.addCleanup(self.patch.stop)
    def test_retry_google_retries_temporary_server_errors(self):
        operation = Mock(side_effect=[FakeAPIError(503), "ok"])
        with patch("data.google.time.sleep"), patch("data.google.random.uniform", return_value=0):
            result = retry_google(operation)
        self.assertEqual(result, "ok")
        self.assertEqual(operation.call_count, 2)

    def test_retry_google_does_not_retry_permission_errors(self):
        operation = Mock(side_effect=FakeAPIError(403))
        with patch("data.google.time.sleep") as sleep:
            with self.assertRaises(FakeAPIError):
                retry_google(operation)
        self.assertEqual(operation.call_count, 1)
        sleep.assert_not_called()

    def test_cuota_falla_rapido_y_no_insiste_desde_otras_sesiones(self):
        first=Mock(side_effect=FakeAPIError(429));second=Mock(return_value='ok')
        with patch.object(g.time,'monotonic',return_value=100),patch.object(g.time,'sleep') as sleep:
            with self.assertRaises(g.GoogleTemporal):retry_google(first)
            with self.assertRaises(g.GoogleTemporal):retry_google(second)
            self.assertEqual(first.call_count,1);second.assert_not_called();sleep.assert_not_called()
        with patch.object(g.time,'monotonic',return_value=161):self.assertEqual(retry_google(second),'ok')

    def test_timeout_no_repite_escrituras_ambiguas(self):
        operation=Mock(side_effect=ReadTimeout('simulado'))
        with patch.object(g.time,'sleep') as sleep:
            with self.assertRaises(g.GoogleTemporal):retry_google(operation)
        self.assertEqual(operation.call_count,1);sleep.assert_not_called()

    def test_cliente_con_timeout_antes_de_abrir_el_libro(self):
        g.connections.clear();self.addCleanup(g.connections.clear)
        client=Mock();events=[]
        client.set_timeout.side_effect=lambda value:events.append(('timeout',value))
        client.open_by_url.side_effect=lambda url:events.append(('open',None)) or 'libro'
        with patch.object(g,'_secret_dict',return_value={}),patch.object(g.gspread,'service_account_from_dict',return_value=client):
            self.assertEqual(g.connections(),('libro',None))
        self.assertEqual(events[0],('timeout',(5,12)));self.assertEqual(events[1][0],'open')

    def test_metadata_compartida_valores_confirmados_siguen_frescos(self):
        g._worksheet_cached.clear();g.read_sheet.clear()
        self.addCleanup(g._worksheet_cached.clear);self.addCleanup(g.read_sheet.clear)
        ws=Mock();ws.get_all_values.side_effect=[[['ID'],['primera']],[['ID'],['segunda']]]
        book=Mock();book.worksheet.return_value=ws
        with patch.object(g,'connections',return_value=(book,None)):
            self.assertEqual(g.read_sheet('QA')[0]['ID'],'primera')
            g.clear_cache('QA')
            self.assertEqual(g.read_sheet('QA')[0]['ID'],'segunda')
        self.assertEqual(book.worksheet.call_count,1);self.assertEqual(ws.get_all_values.call_count,2)

    def test_encabezados_verificados_sin_segunda_lectura_y_contrato_compatible(self):
        ws=Mock();ws.row_values.return_value=['Documento','Revision']
        with patch.object(g,'ensure_sheet',return_value=ws):
            self.assertEqual(g.ensure_headers('QA',['Documento'],return_columns=True),(ws,['Documento','Revision']))
            self.assertEqual(ws.row_values.call_count,1)
            self.assertIs(g.ensure_headers('QA',['Documento']),ws)


if __name__ == "__main__":
    unittest.main()

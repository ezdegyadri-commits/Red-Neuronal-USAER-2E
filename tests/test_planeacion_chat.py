import unittest
from unittest.mock import patch, Mock
from types import SimpleNamespace
from ai import planeacion_chat as chat


class PlaneacionChatTests(unittest.TestCase):
    def test_responder_chat_sin_cliente_retorna_aviso(self):
        with patch.object(chat, 'get_client', return_value=None):
            resp = chat.responder_chat([{'rol': 'user', 'texto': 'Hola'}], 'Alumno 1 (3°)', 'Aprendizaje')
            self.assertIn('no está configurado', resp)

    def test_responder_chat_genera_respuesta_pedagogica(self):
        mock_cli = Mock()
        mock_cli.models.generate_content.return_value = SimpleNamespace(text='¿Qué materiales visuales le ayudan?')
        with patch.object(chat, 'get_client', return_value=mock_cli):
            mensajes = [
                {'rol': 'assistant', 'texto': 'Hola maestra'},
                {'rol': 'user', 'texto': 'El alumno se distrae rápido'}
            ]
            resp = chat.responder_chat(mensajes, 'Alumno 1 (3°)', 'Aprendizaje')
            self.assertEqual(resp, '¿Qué materiales visuales le ayudan?')
            self.assertTrue(mock_cli.models.generate_content.called)
            call_kwargs = mock_cli.models.generate_content.call_args.kwargs
            self.assertIn('HISTORIAL DE DIÁLOGO', call_kwargs['contents'])
            self.assertIn('Docente: El alumno se distrae rápido', call_kwargs['contents'])

    def test_sintetizar_necesidades_genera_parrafo_estructurado(self):
        mock_cli = Mock()
        mock_cli.models.generate_content.return_value = SimpleNamespace(
            text='Alumno de 3° con desempeño presilábico que requiere apoyos visuales y bloques concretos.'
        )
        with patch.object(chat, 'get_client', return_value=mock_cli):
            mensajes = [
                {'rol': 'user', 'texto': 'No lee letras, solo vocales'},
                {'rol': 'user', 'texto': 'Le gustan los dinosaurios y fichas de conteo'}
            ]
            sintesis = chat.sintetizar_necesidades(mensajes, 'Alumno 1', 'Aprendizaje')
            self.assertIn('presilábico', sintesis)
            self.assertIn('apoyos visuales', sintesis)

    def test_sintetizar_sin_cliente_recupera_textos_usuario(self):
        with patch.object(chat, 'get_client', return_value=None):
            mensajes = [
                {'rol': 'assistant', 'texto': 'Hola'},
                {'rol': 'user', 'texto': 'Necesidad expresada por maestra'}
            ]
            sintesis = chat.sintetizar_necesidades(mensajes, 'Alumno 1', 'Aprendizaje')
            self.assertEqual(sintesis, 'Necesidad expresada por maestra')


if __name__ == '__main__':
    unittest.main()

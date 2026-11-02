import asyncio,gzip,unittest
import main

class GatewayAssetsTests(unittest.TestCase):
    def request(self,path,method='GET',headers=()):
        output=[]
        async def send(message):output.append(message)
        asyncio.run(main.servir_estatico({'path':path,'method':method,'headers':headers},send))
        return output[0],output[1]['body']
    def test_javascript_directo_comprimido(self):
        file=next((main.STATIC/'js').glob('index.*.js'))
        path='/static/'+file.relative_to(main.STATIC).as_posix()
        status,body=self.request(path,headers=[(b'accept-encoding',b'gzip')])
        self.assertEqual(status['status'],200)
        self.assertEqual(dict(status['headers'])[b'content-type'],b'application/javascript')
        self.assertEqual(gzip.decompress(body),file.read_bytes())
    def test_recorrido_fuera_del_paquete(self):
        self.assertEqual(self.request('/static/../../main.py')[0]['status'],404)
    def test_no_encontrado(self):
        self.assertEqual(self.request('/static/inexistente.zzz')[0]['status'],404)
    def test_head_y_etag(self):
        file=next((main.STATIC/'js').glob('index.*.js'))
        path='/static/'+file.relative_to(main.STATIC).as_posix()
        status,body=self.request(path)
        self.assertEqual(status['status'],200)
        etag=dict(status['headers'])[b'etag']
        self.assertEqual(self.request(path,'HEAD')[1],b'')
        cached,body=self.request(path,headers=[(b'if-none-match',etag)])
        self.assertEqual((cached['status'],body),(304,b''))

class DatabaseDriverTests(unittest.TestCase):
    def test_auth_normaliza_controlador_disponible(self):
        from unittest.mock import patch
        from data import acceso_usuarios
        acceso_usuarios._engine.cache_clear()
        with patch.object(acceso_usuarios,'create_engine') as create:
            acceso_usuarios._engine('postgresql+psycopg://fake:fake@localhost/fake')
            self.assertEqual(create.call_args.args[0].drivername,'postgresql+psycopg2')
        acceso_usuarios._engine.cache_clear()

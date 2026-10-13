"""Adaptador y persistencia offline; SQL real se comprueba en el script PGlite."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import threading
import unittest
from unittest.mock import patch,Mock
from data.coordinacion import Coordinador,SupabaseRest,coordinador
from services.planeacion_estabilidad import GuardadoPendiente
from services import planeacion as s
from tests import test_planeacion_panel as fixtures
documento=fixtures.documento


class ServidorFake:
    def __init__(self):self.lock=threading.RLock();self.rows={};self.cupos={};self.ahora=100


class BackendFake:
    def __init__(self,server):self.server=server
    def operar(self,namespace,accion,**p):
        server=self.server;key=(namespace,p.get('clave',''))
        with server.lock:
            row=server.rows.get(key)
            if accion=='PRESUPUESTO':
                key=(namespace,p['tipo']);eventos=[e for e in server.cupos.get(key,[]) if e>server.ahora-60]
                if len(eventos)>=45:return {'ok':True,'espera':int(eventos[0]+60-server.ahora)}
                server.cupos[key]=eventos+[server.ahora];return {'ok':True,'espera':0}
            if accion=='ADQUIRIR':
                if row and row['fase']=='RESERVADO' and row['creado']<server.ahora-120:row=None
                if not row:
                    server.rows[key]={'token':p['token'],'fase':'RESERVADO','creado':server.ahora}
                    return {'ok':True}
                return {'ok':False,'meta':deepcopy(row)}
            if not row or row['token']!=p['token']:return {'ok':False}
            if accion=='INICIAR':
                if row['fase']!='RESERVADO':return {'ok':False}
                row.update(fase='INCIERTO',**{k:p[k] for k in ('revision','digest','firma')});return {'ok':True}
            if accion=='RECUPERAR' and (row['fase']!='INCIERTO' or row['revision']!=p['revision'] or row['digest']!=p['digest']):return {'ok':False}
            if accion in ('LIBERAR','RECUPERAR'):del server.rows[key];return {'ok':True}
            raise AssertionError('Acción de prueba desconocida')


def cliente(server=None):return Coordinador(BackendFake(server or ServidorFake()),'prueba')


class AdaptadorTests(unittest.TestCase):
    def test_20_clientes_solo_un_propietario(self):
        server=ServidorFake();clients=[cliente(server) for _ in range(20)];barrera=threading.Barrier(20)
        def adquirir(c):barrera.wait();return c.solicitar('ficticio')[0]
        with ThreadPoolExecutor(max_workers=20) as pool:permisos=list(pool.map(adquirir,clients))
        self.assertEqual(sum(p is not None for p in permisos),1)
        for p in permisos:
            if p:p.__exit__(None,None,None)
        self.assertIsNotNone(clients[0].solicitar('ficticio')[0])

    def test_20_documentos_y_presupuesto_compartido(self):
        server=ServidorFake();clients=[cliente(server) for _ in range(20)]
        with ThreadPoolExecutor(max_workers=20) as pool:
            permisos=list(pool.map(lambda i:clients[i].solicitar(str(i))[0],range(20)))
        self.assertTrue(all(permisos))
        def consumir(i):
            try:clients[i%20].reservar('escritura');return 1
            except GuardadoPendiente:return 0
        with ThreadPoolExecutor(max_workers=20) as pool:self.assertEqual(sum(pool.map(consumir,range(80))),45)

    def test_propietario_antiguo_no_inicia_ni_libera_otro(self):
        c=cliente();p,_=c.solicitar('d');c.backend.server.ahora+=121
        nuevo,_=c.solicitar('d');self.assertIsNotNone(nuevo)
        p.__exit__(None,None,None)
        with self.assertRaises(GuardadoPendiente):p.iniciar('a'*32,'b'*64,'c'*64)
        self.assertEqual(c.backend.server.rows[('prueba',p.key)]['token'],nuevo.token)

    def test_incierto_no_caduca_por_reloj(self):
        c=cliente();p,_=c.solicitar('d');p.iniciar('a'*32,'b'*64,'c'*64)
        c.backend.server.ahora+=10000;p.__exit__(None,None,None)
        otro,meta=c.solicitar('d');self.assertIsNone(otro);self.assertEqual(meta['fase'],'INCIERTO')

    def test_solo_metadatos_no_contenido_educativo(self):
        c=cliente();p,_=c.solicitar('ID alumno ficticio');p.iniciar('a'*32,'b'*64,'c'*64)
        self.assertNotIn('alumno',p.key)
        self.assertEqual(set(c.backend.server.rows[('prueba',p.key)]),{'token','fase','creado','revision','digest','firma'})
        with self.assertRaises(ValueError):SupabaseRest('https://prueba.supabase.co','ficticio').operar('prueba','ADQUIRIR',contenido='No transmitir')

    def test_error_no_revela_token(self):
        backend=SupabaseRest('https://prueba.supabase.co','TOKEN-PRIVADO')
        with patch('data.coordinacion.requests.post',side_effect=RuntimeError('TOKEN-PRIVADO')):
            with self.assertRaises(GuardadoPendiente) as error:backend.operar('prueba','PRESUPUESTO',tipo='lectura')
        self.assertNotIn('TOKEN-PRIVADO',str(error.exception))

    def test_ruta_header_y_redireccion_seguras(self):
        b=SupabaseRest('https://prueba.supabase.co','sb_secret_ficticio')
        with patch('data.coordinacion.requests.post',return_value=Mock(status_code=200,json=lambda:{'ok':True,'espera':0})) as post:
            self.assertEqual(b.operar('prueba','PRESUPUESTO',tipo='lectura')['espera'],0)
        self.assertEqual(post.call_args.args[0],'https://prueba.supabase.co/rest/v1/rpc/usaer_coord_operar')
        self.assertFalse(post.call_args.kwargs['allow_redirects'])
        self.assertEqual(post.call_args.kwargs['headers']['apikey'],'sb_secret_ficticio')
        self.assertNotIn('Authorization',post.call_args.kwargs['headers'])

    def test_rechaza_url_insegura_y_configuracion_parcial(self):
        for url in ['http://prueba.supabase.co','https://google.com','https://prueba.supabase.co?token=x','https://usuario:clave@prueba.supabase.co','https://prueba.supabase.co/ruta']:
            with self.assertRaises(ValueError):SupabaseRest(url,'ficticio')
        coordinador.clear()
        try:
            with patch('data.coordinacion.st.secrets',{'coordinacion_planeacion':{'habilitada':False}}),patch('data.coordinacion.requests.post') as post:
                self.assertIsNone(coordinador());post.assert_not_called()
            coordinador.clear()
            with patch('data.coordinacion.st.secrets',{'coordinacion_planeacion':{'habilitada':True}}):
                with self.assertRaises(ValueError):coordinador()
        finally:coordinador.clear()

    def test_cupo_google_se_reserva_antes_de_la_solicitud(self):
        from data import google
        c=cliente();http=object.__new__(google.CuotasCompartidasHTTPClient)
        with patch.object(google,'coordinador',return_value=c),patch('gspread.HTTPClient.request',return_value='ficticio') as original:
            self.assertEqual(http.request('get','https://sheets.googleapis.com/'),'ficticio')
            for _ in range(45):c.reservar('escritura')
            with self.assertRaises(GuardadoPendiente):http.request('post','https://sheets.googleapis.com/')
        self.assertEqual(original.call_count,1)


class PersistenciaTests(unittest.TestCase):
    def setUp(self):
        fixtures.PanelTests.setUp(self);self.cliente=cliente()
        self.coordinado=patch('data.coordinacion.coordinador',return_value=self.cliente);self.coordinado.start()
    def tearDown(self):
        self.coordinado.stop();fixtures.PanelTests.tearDown(self);s.intentos().clear()

    def test_20_guardados_conservan_registros_y_formatos(self):
        def guardar(i):
            d=documento();d['id']='ficticio-'+str(i);return s.guardar(d)
        with ThreadPoolExecutor(max_workers=20) as pool:docs=list(pool.map(guardar,range(20)))
        self.assertEqual(len(s.reconstruir(self.sheet.rows)),20)
        self.assertEqual(len({d['revision'] for d in docs}),20)
        self.assertTrue(all(d['formato']=='XXIII' for d in docs))

    def test_cache_obsoleto_no_autoriza_guardado(self):
        a=s.guardar(documento());b=deepcopy(a);b['textos']['Evaluación']='Otra instancia';b=s.guardar(b)
        with patch.object(s,'versiones_actuales',return_value=[a]):
            with self.assertRaises(RuntimeError):s.guardar(a)
        self.assertEqual(s.reconstruir(self.sheet.rows)[-1]['revision'],b['revision'])

    def test_relojes_distintos_no_ocultan_version_reciente(self):
        a=s.guardar(documento());b=deepcopy(a);b['textos']['Evaluación']='Versión posterior con reloj atrasado'
        with patch.object(s,'datetime') as reloj:
            reloj.now.return_value.isoformat.return_value='2026-01-01T08:00:00'
            b=s.guardar(b)
        self.assertEqual(s.listar()[0]['revision'],b['revision'])

    def test_respuesta_perdida_se_recupera_sin_memoria_local(self):
        original=self.sheet.append_rows
        def ambiguo(rows,value_input_option):original(rows,value_input_option);raise TimeoutError()
        d=documento()
        with patch.object(self.sheet,'append_rows',side_effect=ambiguo):
            with self.assertRaises(TimeoutError):s.guardar(d)
        count=len(self.sheet.rows);s.intentos().clear();s._recientes().clear();s._versiones.clear()
        saved=s.guardar(d)
        self.assertEqual(len(self.sheet.rows),count);self.assertEqual(saved['revision'],self.sheet.rows[1][1])

    def test_operacion_no_confirmada_no_repite_append(self):
        d=documento()
        with patch.object(self.sheet,'append_rows',side_effect=TimeoutError) as append:
            with self.assertRaises(TimeoutError):s.guardar(d)
            s.intentos().clear()
            with self.assertRaises(GuardadoPendiente):s.guardar(d)
        self.assertEqual(append.call_count,1);self.assertEqual(self.sheet.rows,[s.HEADERS])

    def test_cuota_antes_de_transmitir_permite_reintento(self):
        d=documento()
        with patch.object(self.sheet,'append_rows',side_effect=GuardadoPendiente(15)):
            with self.assertRaises(GuardadoPendiente):s.guardar(d)
        self.assertEqual(self.sheet.rows,[s.HEADERS]);self.assertEqual(s.guardar(d)['id'],d['id'])

    def test_sha_incompleto_no_libera_incierto(self):
        d=documento();d['textos']['Evaluación']='x'*50000;original=self.sheet.append_rows
        def parcial(rows,value_input_option):original(rows[:1],value_input_option);raise TimeoutError()
        with patch.object(self.sheet,'append_rows',side_effect=parcial):
            with self.assertRaises(TimeoutError):s.guardar(d)
        with self.assertRaises(GuardadoPendiente):s.guardar(d)
        self.assertEqual(len(self.sheet.options),1)

    def test_usuario_no_autorizado_no_consulta_coordinador(self):
        d=documento();d['datos']['Alumnos'][0]['ID_Alumno']='otro'
        with patch('data.coordinacion.coordinador') as coord:
            with self.assertRaises(PermissionError):s.guardar(d)
        coord.assert_not_called()

    def test_conserva_xxi_xxiii_xxv_por_perfil(self):
        for area,fmt in [('Aprendizaje','XXI'),('Aprendizaje','XXIII'),('Psicología','XXIII'),('Comunicación','XXIII'),('Trabajo Social','XXV')]:
            d=documento(fmt);d['id']=area+fmt;d['datos']['Función']=area
            with patch.object(s,'identidad',return_value={**fixtures.ACTOR,'area':area}):saved=s.guardar(d)
            self.assertEqual(saved['formato'],fmt);self.assertEqual(saved['datos']['Alumnos'],d['datos']['Alumnos'])


if __name__=='__main__':unittest.main()

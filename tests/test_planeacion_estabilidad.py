"""Sin datos, credenciales ni conexiones reales: límites y concurrencia sintéticos."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import threading
import unittest
from unittest.mock import patch
import pandas as pd
from services import planeacion as s
from services.planeacion_estabilidad import Presupuesto, GuardadoPendiente
from tests import test_planeacion_panel as fixtures
documento=fixtures.documento


class EstabilidadTests(unittest.TestCase):
    setUp=fixtures.PanelTests.setUp
    tearDown=fixtures.PanelTests.tearDown

    def test_guardar_sin_cambios_no_crea_version(self):
        a=s.guardar(documento());b=s.guardar(a)
        self.assertEqual(a['revision'],b['revision'])
        self.assertEqual(len(self.sheet.options),1)

    def test_respuesta_perdida_no_repite_append(self):
        original=self.sheet.append_rows
        def ambiguo(rows,value_input_option):
            original(rows,value_input_option)
            raise TimeoutError('Respuesta perdida ficticia')
        d=documento()
        with patch.object(self.sheet,'append_rows',side_effect=ambiguo):
            with self.assertRaises(TimeoutError):s.guardar(d)
        cantidad=len(self.sheet.rows)
        guardado=s.guardar(d)
        self.assertEqual(len(self.sheet.rows),cantidad)
        self.assertEqual(len(s.listar(True)),1)
        self.assertEqual(guardado['revision'],self.sheet.rows[1][1])

    def test_fallo_antes_de_escribir_reusa_revision(self):
        d=documento()
        with patch.object(self.sheet,'append_rows',side_effect=TimeoutError):
            with self.assertRaises(TimeoutError):s.guardar(d)
        pendiente=next(v for k,v in s.intentos().items() if k[0]==d['id'])
        revision=pendiente['saved']['revision']
        guardado=s.guardar(d)
        self.assertEqual(guardado['revision'],revision)
        self.assertEqual(len(s.listar(True)),1)

    def test_cambios_nuevos_no_se_pisan_al_conciliar(self):
        d=documento();original=self.sheet.append_rows
        def ambiguo(rows,value_input_option):
            original(rows,value_input_option);raise TimeoutError()
        with patch.object(self.sheet,'append_rows',side_effect=ambiguo):
            with self.assertRaises(TimeoutError):s.guardar(d)
        d['textos']['Evaluación']='Edición nueva que debe conservarse'
        with self.assertRaisesRegex(RuntimeError,'cambios nuevos'):s.guardar(d)
        self.assertEqual(d['textos']['Evaluación'],'Edición nueva que debe conservarse')
        self.assertEqual(len(self.sheet.options),1)

    def test_cuota_difiere_sin_crear_intento_ambiguo(self):
        d=documento()
        with patch.object(s,'reservar_escritura',side_effect=GuardadoPendiente(20)):
            with self.assertRaises(GuardadoPendiente):s.guardar(d)
        self.assertEqual(self.sheet.rows,[s.HEADERS])
        self.assertFalse(any(k[0]==d['id'] for k in s.intentos()))

    def test_dos_editores_una_revision_solo_uno_guarda(self):
        inicial=s.guardar(documento());barrera=threading.Barrier(2)
        def editar(n):
            d=deepcopy(inicial);d['textos']['Evaluación']=str(n);barrera.wait()
            try:s.guardar(d);return 'ok'
            except RuntimeError:return 'conflicto'
        with ThreadPoolExecutor(max_workers=2) as pool:
            resultados=list(pool.map(editar,[1,2]))
        self.assertEqual(sorted(resultados),['conflicto','ok'])

    def test_documento_lento_no_bloquea_otro(self):
        inicio=threading.Event();liberar=threading.Event();original=self.sheet.append_rows
        def lento(rows,value_input_option):
            if rows[0][0]=='lento':inicio.set();liberar.wait(5)
            return original(rows,value_input_option)
        with patch.object(self.sheet,'append_rows',side_effect=lento):
            with ThreadPoolExecutor(max_workers=2) as pool:
                d=documento();d['id']='lento';f=pool.submit(s.guardar,d)
                self.assertTrue(inicio.wait(2))
                otro=documento();otro['id']='rapido'
                try:self.assertEqual(pool.submit(s.guardar,otro).result(timeout=2)['id'],'rapido')
                finally:liberar.set()
                f.result(timeout=2)

    def test_15_20_25_30_documentos_con_diferimiento_y_recuperacion(self):
        for n in (15,20,25,30):
            ahora=[100.0];p=Presupuesto(reloj=lambda:ahora[0]);s._versiones.clear();s._recientes().clear()
            self.sheet.rows=[s.HEADERS];self.sheet.options=[]
            with patch.object(s,'reservar_escritura',side_effect=p.reservar):
                def crear(i):
                    d=documento();d['id']=f'carga-{n}-{i}';return s.guardar(d)
                with ThreadPoolExecutor(max_workers=n) as pool:docs=list(pool.map(crear,range(n)))
                def editar(d):
                    d=deepcopy(d);d['textos']['Evaluación']='Cambio ficticio recuperable'
                    try:return s.guardar(d),False
                    except GuardadoPendiente:return d,True
                with ThreadPoolExecutor(max_workers=n) as pool:resultados=list(pool.map(editar,docs))
                diferidos=[d for d,pendiente in resultados if pendiente]
                ahora[0]+=60
                for d in diferidos:s.guardar(d)
                versiones=s.reconstruir(self.sheet.rows)
                self.assertEqual(len(versiones),2*n)
                finales={d['id']:d for d in versiones}
                self.assertEqual(len(finales),n)
                self.assertTrue(all(d['textos']['Evaluación']=='Cambio ficticio recuperable' for d in finales.values()))
                print('Persistencia sintética:',n,'documentos;',len(versiones),'versiones;',len(diferidos),'diferidas y recuperadas')


class PresupuestoTests(unittest.TestCase):
    def test_limite_ventana_y_recuperacion(self):
        ahora=[100.0];p=Presupuesto(limite=2,reloj=lambda:ahora[0])
        p.reservar();p.reservar()
        with self.assertRaises(GuardadoPendiente):p.reservar()
        ahora[0]+=60;p.reservar();self.assertEqual(len(p.eventos),1)

    def test_15_20_25_30_usuarios_presupuesto_no_se_supera(self):
        for n in (15,20,25,30):
            ahora=[100.0];p=Presupuesto(reloj=lambda:ahora[0]);ok=0;deferred=0
            # Simula el ritmo anterior de cuatro escrituras por persona/minuto.
            for _ in range(4):
                with ThreadPoolExecutor(max_workers=n) as pool:
                    def reservar(_):
                        try:p.reservar();return True
                        except GuardadoPendiente:return False
                    result=list(pool.map(reservar,range(n)))
                ok+=sum(result);deferred+=len(result)-sum(result)
                ahora[0]+=15
            self.assertEqual(ok,45)
            self.assertEqual(deferred,4*n-45)
            print('Simulación de presupuesto:',n,'usuarios;',ok,'reservas;',deferred,'diferidas; sin red')


class InterfazEstabilidadTests(unittest.TestCase):
    def test_abrir_otro_no_reemplaza_edicion_pendiente(self):
        from ui import planeacion as u
        d=documento();state={'p_doc':deepcopy(d),'p_pending':True}
        otro=deepcopy(d);otro['id']='otro'
        with patch.object(u.st,'session_state',state):
            with self.assertRaises(RuntimeError):u._open('p',otro)
        self.assertEqual(state['p_doc'],d);self.assertTrue(state['p_pending'])

    def test_pdf_solo_se_reconstruye_con_cambios(self):
        from ui import planeacion as u
        d=documento()
        with patch.object(u.st,'session_state',{}),patch.object(u,'generar_pdf',return_value=b'PDF') as pdf:
            u._pdf_sesion('p',d);u._pdf_sesion('p',d)
            self.assertEqual(pdf.call_count,1)
            d['textos']['Evaluación']='Cambio';u._pdf_sesion('p',d)
            self.assertEqual(pdf.call_count,2)

    def test_contexto_directivo_minimizado_lista_no_texto(self):
        from ui import planeacion as u
        d=documento()
        with patch.object(s,'autorizar'),patch.object(u,'contexto_ia',return_value={'contextualizacion_docente':'Alumno ficticio identifica palabras.'}):
            result=u._contexto_revision(d)
        self.assertNotIn('Alumno ficticio',result['contextualizacion_docente'])
        self.assertIn('identifica palabras',result['contextualizacion_docente'])

    def test_cache_selectivo_no_limpia_otra_hoja(self):
        from data import google
        with patch.object(google,'read_sheet') as read:
            google.clear_cache('Alumnos');read.clear.assert_called_once_with('Alumnos')

    def test_cupo_material_no_pierde_archivo_y_se_libera(self):
        from services import materiales_planeacion as m
        cupo=threading.BoundedSemaphore(1);cupo.acquire()
        with patch('services.planeacion_estabilidad.lecturas_materiales',return_value=cupo):
            with self.assertRaisesRegex(ValueError,'transcripciones'):m.leer_material('texto.txt',b'Archivo ficticio')
            cupo.release()
            self.assertIn('Archivo ficticio',m.leer_material('texto.txt',b'Archivo ficticio')['texto'])
            with self.assertRaises(ValueError):m.leer_material('invalido.bin',b'No admitido')
            self.assertTrue(cupo.acquire(blocking=False));cupo.release()

    def test_logout_advierte_pendientes_y_no_cierra_sin_confirmar(self):
        from ui import auth
        import hashlib
        base='planeacion_'+hashlib.sha256(b'prueba').hexdigest()[:12]
        state={'autenticado':True,'usuario':'prueba',base+'_individual_pending':True}
        with patch.object(auth.st,'session_state',state),patch.object(auth.st,'warning'),patch.object(auth.st,'checkbox',return_value=False),patch.object(auth.st,'button',return_value=False) as boton:
            auth.logout()
        self.assertTrue(boton.call_args.kwargs['disabled']);self.assertTrue(state['autenticado'])

    def test_conciliar_resguarda_edicion_antes_de_abrir_reciente(self):
        from ui import planeacion as u
        d=documento();state={'p_doc':deepcopy(d),'p_pending':True}
        nuevo=deepcopy(d);nuevo['revision']='servidor'
        with patch.object(u.st,'session_state',state):
            u._resguardar_pendiente('p')
            with patch('services.planeacion_generacion.prellenar',side_effect=lambda d:d):u._open('p',nuevo)
        self.assertEqual(state['p_doc']['revision'],'servidor')
        self.assertEqual(next(iter(state['p_resguardos'].values())),d)


if __name__=='__main__':unittest.main()

"""Navegación sin bloqueos ni pérdidas. Datos exclusivamente ficticios."""
from copy import deepcopy
import unittest
from unittest.mock import patch
from contextlib import nullcontext
from ui import planeacion as u,planeacion_simple as simple,planeacion_pendientes as cola


def doc(identidad):
    from tests.test_planeacion_panel import documento
    d=documento();d['id']=identidad
    d['textos']['Evaluación']='Edición propia '+identidad
    return d


class ColaTests(unittest.TestCase):
    def test_cola_conserva_aportes_de_filas_excluidas_al_cambiar_de_documento(self):
        p='planeacion_qa_grupal';base='planeacion_qa'
        filas=[{'ID_Alumno':'I1','Texto en formato':'Texto pendiente anterior a la exclusión'}]
        state={p+'_doc':doc('a'),p+'_pending':True,p+'_filas_retiradas':deepcopy(filas)}
        with patch.object(cola.st,'session_state',state):
            reserva=cola.conservar(p,base)
        self.assertEqual(state[reserva+'_filas_retiradas'],filas)
        self.assertTrue(state[reserva+'_pending'])

    def test_otro_grupo_abre_y_retiene_edicion_completa_que_no_se_guardo(self):
        base='planeacion_qa';p=base+'_grupal';anterior=doc('grupo-a');nuevo=doc('grupo-b')
        state={p+'_doc':deepcopy(anterior),p+'_pending':True,p+'_error':'Sin conexión'}
        def abrir(prefix,d):state[prefix+'_doc']=deepcopy(d);state[prefix+'_pending']=False
        with patch.object(u.st,'session_state',state),patch.object(u,'_open',side_effect=abrir):
            simple._abrir(base,p,nuevo)
            guardados=cola.pendientes(base)
        self.assertEqual(state[p+'_doc'],nuevo)
        self.assertEqual(len(guardados),1)
        reserva=guardados[0]
        self.assertEqual(state[reserva+'_doc'],anterior)
        self.assertTrue(state[reserva+'_pending'])
        state[p+'_doc']['textos']['Evaluación']='Otra redacción'
        self.assertEqual(state[reserva+'_doc'],anterior)

    def test_abrir_mismo_documento_no_recupera_version_obsoleta(self):
        p='planeacion_qa_grupal';actual=doc('grupo-a');viejo=deepcopy(actual)
        viejo['textos']['Evaluación']='Texto anterior del servidor'
        state={p+'_doc':actual,p+'_pending':True}
        with patch.object(u.st,'session_state',state),patch.object(u,'_open') as abrir:
            simple._abrir('planeacion_qa',p,viejo)
        abrir.assert_not_called();self.assertEqual(state[p+'_doc'],actual)
        self.assertTrue(state[p+'_pending'])

    def test_crear_nuevo_grupo_no_exige_que_se_guarde_el_anterior(self):
        base='planeacion_qa';p=base+'_grupal';viejo=doc('a');nuevo=doc('b')
        state={p+'_doc':viejo,p+'_pending':True}
        def abrir(prefix,d):state[prefix+'_doc']=deepcopy(d);state[prefix+'_pending']=False
        with patch.object(u.st,'session_state',state),patch.object(simple.st,'spinner',return_value=nullcontext()),patch.object(simple.s,'identidad',return_value={'area':'Aprendizaje'}),patch.object(simple.s,'nueva',return_value=nuevo),patch.object(simple.s,'preparar_contexto',side_effect=lambda d:d),patch.object(simple.equipo,'aplica',return_value=False),patch.object(u,'_open',side_effect=abrir),patch.object(u,'_persist',return_value=False),patch.object(u,'_guardar_edicion_pendiente') as guardar_anterior:
            resultado=simple.crear_borrador(base,'XXIII',['A1'],2026,1,'grupal')
            reservas=cola.pendientes(base)
        self.assertEqual(resultado,p);guardar_anterior.assert_not_called()
        self.assertEqual(state[p+'_doc']['id'],'b')
        self.assertTrue(any(state[r+'_doc']==viejo for r in reservas))

    def test_reintenta_otro_documento_aunque_falle_el_primero(self):
        base='planeacion_qa';a=base+'_envio_a';b=base+'_envio_b';activo=base+'_grupal'
        state={a+'_doc':doc('a'),a+'_pending':True,b+'_doc':doc('b'),b+'_pending':True,
               activo+'_doc':doc('activo'),activo+'_pending':True,base+'_activa':activo}
        def guardar(p,automatic=False):
            if p==b:state[p+'_pending']=False
            return p==b
        with patch.object(u.st,'session_state',state),patch.object(u,'_guardar_edicion_pendiente',side_effect=guardar) as guardar_mock:
            quedan=cola.reintentar(base)
        self.assertEqual([c.args[0] for c in guardar_mock.call_args_list],[a,b])
        self.assertEqual(quedan,[a]);self.assertTrue(state[activo+'_pending'])

    def test_cola_no_incluye_edicion_de_otra_cuenta(self):
        state={'planeacion_qa_grupal_doc':doc('a'),'planeacion_qa_grupal_pending':True,
               'planeacion_otra_grupal_doc':doc('b'),'planeacion_otra_grupal_pending':True}
        with patch.object(u.st,'session_state',state):self.assertEqual(cola.pendientes('planeacion_qa'),['planeacion_qa_grupal'])

    def test_aportes_y_observaciones_se_conservan_por_separado(self):
        state={'p_doc':doc('a'),'p_pending':True,'p_filas':[{'Texto en formato':'Aporte propio'}],'p_obs':'Observación propia'}
        with patch.object(u.st,'session_state',state):r=cola.conservar('p','planeacion_qa')
        self.assertEqual(state[r+'_filas'],state['p_filas']);self.assertEqual(state[r+'_obs'],'Observación propia')
        state['p_filas'][0]['Texto en formato']='Otro texto'
        self.assertEqual(state[r+'_filas'][0]['Texto en formato'],'Aporte propio')

    def test_abrir_otra_vez_el_grupo_recupera_la_edicion_pendiente_no_el_servidor(self):
        base='planeacion_qa';p=base+'_grupal';a=doc('a');b=doc('b')
        state={p+'_doc':a,p+'_pending':True}
        def abrir(prefix,d):state[prefix+'_doc']=deepcopy(d);state[prefix+'_pending']=False
        with patch.object(u.st,'session_state',state),patch.object(u,'_open',side_effect=abrir):
            simple._abrir(base,p,b)
            viejo=doc('a');viejo['textos']['Evaluación']='Versión anterior'
            destino=simple._abrir(base,p,viejo)
            self.assertEqual(cola.raiz(destino),base)
        self.assertNotEqual(destino,p)
        self.assertEqual(state[destino+'_doc'],a)
        self.assertTrue(state[destino+'_pending']);self.assertEqual(state[p+'_doc'],b)

    def test_nuevo_documento_no_hereda_envio_acuses_ni_columnas_anteriores(self):
        base='planeacion_qa';p=base+'_grupal';a=doc('a');b=doc('b')
        state={p+'_doc':a,p+'_pending':True,p+'_estado_pendiente':'ENVIADO',
               p+'_filas':[{'Texto en formato':'Aporte anterior'}],p+'_papel_nonce':'acuse-antiguo',p+'_retry_at':12345}
        with patch.object(u.st,'session_state',state):
            simple._abrir(base,p,b)
            reserva=cola.pendientes(base)[0]
        self.assertEqual(state[reserva+'_estado_pendiente'],'ENVIADO')
        self.assertNotIn(p+'_estado_pendiente',state)
        self.assertNotIn(p+'_filas',state);self.assertNotIn(p+'_papel_nonce',state)
        self.assertNotIn(p+'_retry_at',state)

    def test_fallo_temporal_en_un_envio_no_retrasa_otro_listo(self):
        base='planeacion_qa';a=base+'_envio_a';b=base+'_envio_b'
        state={a+'_doc':doc('a'),a+'_pending':True,a+'_retry_at':float('inf'),
               b+'_doc':doc('b'),b+'_pending':True}
        with patch.object(u.st,'session_state',state),patch.object(u,'_guardar_edicion_pendiente',return_value=False) as guardar:
            cola.reintentar(base)
        guardar.assert_called_once_with(b,automatic=True)

    def test_interfaz_permite_otro_grupo_y_confirmacion_posterior_sin_perdida(self):
        from streamlit.testing.v1 import AppTest
        codigo='''
import streamlit as st
from unittest.mock import patch
from copy import deepcopy
from ui import planeacion as u,planeacion_simple as simple,planeacion_pendientes as cola
from tests.test_planeacion_cola_pendientes import doc
base='planeacion_qa';p=base+'_grupal'
if p+'_doc' not in st.session_state:
    st.session_state[p+'_doc']=doc('a');st.session_state[p+'_pending']=True
    st.session_state[base+'_activa']=p
conectado=st.checkbox('Conexión restablecida')
def guardar(d,estado):
    if d['id']=='a' and not conectado:raise TimeoutError('Fallo ficticio')
    return {**deepcopy(d),'revision':'confirmada-'+d['id'],'guardado_en':'2026-10-21T10:00:00-06:00'}
with patch.object(u.servicio,'guardar',side_effect=guardar):
    if st.button('Abrir otro grupo'):
        simple._abrir(base,p,doc('b'));u._persist(p)
    cola.panel(base)
st.metric('Documento abierto',st.session_state[p+'_doc']['id'])
st.metric('Ediciones pendientes',len(cola.pendientes(base)))
st.session_state['cola_ids_prueba']=cola.pendientes(base)
'''
        app=AppTest.from_string(codigo,default_timeout=30).run()
        next(b for b in app.button if b.label=='Abrir otro grupo').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(next(m.value for m in app.metric if m.label=='Documento abierto'),'b')
        self.assertEqual(next(m.value for m in app.metric if m.label=='Ediciones pendientes'),'1')
        reserva=app.session_state['cola_ids_prueba'][0]
        self.assertTrue(app.session_state[reserva+'_pending'])
        app.session_state[reserva+'_retry_at']=0;app.session_state[reserva+'_last_attempt']=0
        next(c for c in app.checkbox if c.label=='Conexión restablecida').check().run()
        self.assertFalse(app.exception)
        self.assertEqual(next(m.value for m in app.metric if m.label=='Ediciones pendientes'),'0')
        self.assertEqual(app.session_state[reserva+'_doc']['revision'],'confirmada-a')
        self.assertEqual(app.session_state[reserva+'_doc']['textos']['Evaluación'],'Edición propia a')

    def test_reintento_preserva_estado_de_envio(self):
        d=doc('a');state={'p_doc':d}
        with patch.object(u.st,'session_state',state),patch.object(u.servicio,'guardar',side_effect=[TimeoutError(),deepcopy(d)]) as guardar:
            self.assertFalse(u._persist('p','ENVIADO'))
            self.assertTrue(state['p_pending']);self.assertIn('p_retry_at',state)
            self.assertTrue(u._persist('p'))
        self.assertEqual(guardar.call_args.args[1],'ENVIADO')
        self.assertFalse(state['p_pending']);self.assertNotIn('p_estado_pendiente',state)

    def test_cierre_intenta_todos_y_no_sale_si_uno_falla(self):
        from ui import auth
        import hashlib
        base='planeacion_'+hashlib.sha256(b'qa').hexdigest()[:12]
        state={'usuario':'qa',base+'_a_pending':True,base+'_b_pending':True,base+'_a_doc':doc('a'),base+'_b_doc':doc('b')}
        with patch.object(u.st,'session_state',state),patch.object(auth.st,'info'),patch.object(auth.st,'warning'),patch.object(auth.st,'checkbox',return_value=False),patch.object(auth.st,'button',side_effect=lambda label,**k:label=='Guardar cambios y cerrar sesión'),patch.object(u,'_guardar_edicion_pendiente',side_effect=[False,True]) as guardar,patch.object(auth,'_cerrar') as cerrar:
            auth.logout()
        self.assertEqual(guardar.call_count,2);cerrar.assert_not_called()

"""Actividades distintas: no multiplicar secuencias al dosificar. Datos ficticios."""
from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch
from services import planeacion as s, planeacion_generacion as g
from tests.test_planeacion_completa import documento, resultado
from ai.planeacion_completa import validar_completa, solicitud_completa


class ActividadesDistintasTests(TestCase):
    def preparar(self,area='Aprendizaje',cantidad=None):
        d=g.prellenar(documento(area));config={**g.configuracion(d),'inicio':'2026-10-07'}
        if cantidad:config.update(sesiones=cantidad,actividades_solicitadas=cantidad,contextos_solicitados=['Aula de apoyo'])
        return d,g.preparar_solicitud(d,config)

    def setUp(self):
        p=patch.object(s,'autorizar',return_value={'cuenta':'cuenta-ficticia','director':False});p.start();self.addCleanup(p.stop)

    def test_dos_unidades_no_se_replican_hasta_doce_fechas(self):
        d,sol=self.preparar();r=resultado(sol,'Aprendizaje');nuevo=g.ensamblar(d,r,sol)
        actividades=[row['Actividades'] for row in nuevo['tablas']['dosificacion'] if row.get('Actividades')]
        self.assertEqual(len(actividades),2);self.assertEqual(len(set(actividades)),2)
        antes=deepcopy(nuevo);sol2=g.preparar_solicitud(nuevo,sol['configuracion_original'])
        self.assertEqual(g.ensamblar(nuevo,r,sol2),antes)
        self.assertTrue(sol2['contexto']['actividades_previas'])

    def test_cantidad_y_contexto_elegidos_se_validan(self):
        d,sol=self.preparar(cantidad=2);r=resultado(sol,'Aprendizaje')
        self.assertEqual(len(validar_completa(r,d['formato'],'Aprendizaje',sol['contexto'],sol['aliases'],sol['evidencias'])['unidades']),2)
        r['unidades'][0]['contexto']='Familia'
        with self.assertRaises(ValueError):validar_completa(r,d['formato'],'Aprendizaje',sol['contexto'],sol['aliases'],sol['evidencias'])
        _,sol3=self.preparar(cantidad=3)
        with self.assertRaises(ValueError):validar_completa(resultado(sol3,'Aprendizaje'),d['formato'],'Aprendizaje',sol3['contexto'],sol3['aliases'],sol3['evidencias'])
        prompt=solicitud_completa(sol3['resumen'],d['formato'],'Aprendizaje',sol3['contexto'],sol3['ajustes'],sol3['aliases'],sol3['evidencias'])
        self.assertIn('exactamente 3',prompt)

    def test_nee_elegida_se_incluye_con_su_destinatario(self):
        from tests.test_planeacion_intervenciones_nee import ejemplo
        from services import planeacion_intervenciones_nee as nee
        d=ejemplo();d=nee.incorporar(d,[r['id'] for r in nee.catalogo(d)])
        config={**g.configuracion(d),'inicio':'2026-10-07','sesiones':2,'actividades_solicitadas':2}
        sol=g.preparar_solicitud(d,config)
        self.assertIn('NEE-SELECCIONADA-1',sol['resumen'])
        self.assertEqual(sol['evidencias']['NEE-SELECCIONADA-1'],['Alumno 1'])

    def test_ensamblar_aisla_tabla_superior_y_escribe_solo_en_dosificacion(self):
        d,sol=self.preparar();r=resultado(sol,'Aprendizaje')
        # Guardar estado de tabla superior antes
        tabla1_antes=deepcopy(d['tablas'].get('aprendizajes',[]))
        nuevo=g.ensamblar(d,r,sol)
        # La tabla superior permanece intacta (aislamiento estricto, read-only)
        self.assertEqual(nuevo['tablas'].get('aprendizajes',[]), tabla1_antes)
        # La dosificación contiene las actividades generadas (unidireccional a Tabla 2)
        actividades=[row['Actividades'] for row in nuevo['tablas']['dosificacion'] if row.get('Actividades')]
        self.assertEqual(len(actividades), 2)

    def test_admite_bateria_amplia_actividades(self):
        d,sol=self.preparar(cantidad=2);r=resultado(sol,'Aprendizaje')
        # Crear 15 unidades válidas para probar que el validador acepta batería extendida
        base_u=deepcopy(r['unidades'][0])
        unidades_15=[]
        for i in range(15):
            u=deepcopy(base_u)
            u['actividad']=f'Inicio {i}: ver material. Desarrollo: andamiaje de actividad {i}. Cierre: registro observable {i}.'
            unidades_15.append(u)
        r_15={'observaciones':'OK','faltantes':[],'unidades':unidades_15,'sugerencia_familia':''}
        # Validar que 15 unidades no causan error de límite en validar_completa
        contexto_15={**sol['contexto'], 'actividades_solicitadas': 15}
        validados=validar_completa(r_15,d['formato'],'Aprendizaje',contexto_15,sol['aliases'],sol['evidencias'])
        self.assertEqual(len(validados['unidades']), 15)

    def test_seleccion_y_cantidad_visibles_antes_de_preparar(self):
        from streamlit.testing.v1 import AppTest
        from tests.test_planeacion_documento_directo import HELP_APP
        app=AppTest.from_string(HELP_APP,default_timeout=30).run()
        self.assertFalse(app.exception)
        self.assertEqual(next(w for w in app.selectbox if w.label=='Cantidad de actividades').value,3)
        self.assertTrue(any(w.label=='Minutos por actividad' for w in app.selectbox))
        self.assertTrue(any(w.label=='Contextos de intervención' for w in app.multiselect))
        next(w for w in app.selectbox if w.label=='Cantidad de actividades').set_value(2).run()
        with patch.object(g,'preparar_solicitud',return_value={'resumen':'Resumen ficticio revisable','huella':'qa'}) as preparar:
            next(w for w in app.button if w.label=='Preparar propuesta').click().run()
            self.assertEqual(preparar.call_args.args[1]['actividades_solicitadas'],2)
        self.assertFalse(app.exception)
        self.assertNotIn('guardados',app.session_state)

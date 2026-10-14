"""Continuidad local y diagnóstico preciso, sin servicios externos."""
from copy import deepcopy
import json
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch,Mock
from services import planeacion as s,planeacion_local as local
from services.planeacion_modelo import crear_plantilla
from services.curriculo import vincular,opciones
from ai import planeacion as motor
from ai.planeacion_completa import RespuestaInvalida
from tests.test_planeacion_completa import documento
from tests import test_planeacion_simple as simple


class LocalTests(unittest.TestCase):
    def setUp(self):
        self.p=patch.object(s,'autorizar',return_value={'cuenta':'cuenta-ficticia','director':False})
        self.p.start();self.addCleanup(self.p.stop)

    def test_cuatro_perfiles_y_datos_manuales_intactos(self):
        for area in ('Aprendizaje','Psicología','Comunicación','Trabajo Social'):
            d=documento(area);d['textos'][next(iter(d['textos']))]='Redacción docente conservada'
            antes=deepcopy(d)
            with patch('ai.planeacion.proponer') as ia:
                req=local.preparar(d);new=local.aplicar(d,req,[r['id'] for r in req['propuestas']])
            ia.assert_not_called();self.assertEqual(d,antes)
            self.assertEqual(new['datos'],d['datos']);self.assertEqual(new['textos'],d['textos'])
            self.assertEqual(new['tablas']['aprendizajes' if area!='Trabajo Social' else 'barreras'],d['tablas']['aprendizajes' if area!='Trabajo Social' else 'barreras'])
            self.assertEqual(len(new['tablas']['dosificacion']),len(d['tablas']['dosificacion'])+1)
            self.assertNotIn('generacion_completa',new['metadatos'])

    def test_no_mezcla_antecedentes_de_otros_alumnos(self):
        d=documento(dos=True);d['metadatos']['fuentes'][0]['texto']='Apoyo en lectura documentado'
        d['metadatos']['fuentes'][1]['texto']='Apoyo en números y conteo documentado'
        d['metadatos']['fuentes'].append({**d['metadatos']['fuentes'][0],'alumno':'AJENO','referencia':'AJENA','texto':'Información ajena'})
        rows=local.preparar(d)['propuestas']
        a1=next(r for r in rows if r['alumno']=='A1');a2=next(r for r in rows if r['alumno']=='A2')
        self.assertEqual(a1['evidencias'],['E1']);self.assertEqual(a2['evidencias'],['E2'])
        self.assertNotIn('AJENA',str(rows));self.assertIn('Leer o escuchar',a1['actividad']);self.assertIn('Agrupar, contar',a2['actividad'])

    def test_sin_evidencia_individual_se_declara_general(self):
        d=documento(dos=True);d['metadatos']['fuentes']=d['metadatos']['fuentes'][:1]
        req=local.preparar(d);row=next(r for r in req['propuestas'] if r['alumno']=='A2')
        self.assertFalse(row['evidencias'])
        self.assertIn('sin antecedente individual',row['actividad'])

    def test_material_general_no_se_convierte_en_evidencia_individual(self):
        d=documento();d['metadatos']['fuentes']=[{'tipo':'MATERIAL','alumno':'','referencia':'M1','texto':'Actividades de lectura con imágenes'}]
        row=local.preparar(d)['propuestas'][0]
        self.assertFalse(row['evidencias']);self.assertIn('Materiales generales',row['actividad'])
        self.assertIn('Leer o escuchar',row['actividad'])

    def test_respetar_campos_y_no_cambiar_grados(self):
        d=documento();campos=['Lenguajes','De lo Humano y lo Comunitario']
        refs=[opciones(d,c,[2])[0]['id'] for c in campos]
        d=vincular(d,campos,['Inclusión'],refs)
        req=local.preparar(d)
        self.assertEqual({r['campo'] for r in req['propuestas']},set(campos))
        new=local.aplicar(d,req,[r['id'] for r in req['propuestas']])
        self.assertEqual(new['metadatos']['curriculo'],d['metadatos']['curriculo'])
        self.assertEqual(new['datos']['Alumnos'][0]['Grado'],'5')

    def test_no_duplica_ni_repone_actividades_retiradas(self):
        d=documento();req=local.preparar(d);ids=[r['id'] for r in req['propuestas']]
        new=local.aplicar(d,req,ids);new['tablas']['dosificacion'].pop()
        req2=local.preparar(new);repetido=local.aplicar(new,req2,ids)
        self.assertEqual(repetido,new)

    def test_cambio_de_edicion_no_se_sobrescribe(self):
        d=documento();req=local.preparar(d)
        d['textos']['Observaciones']='Nueva edición'
        with self.assertRaises(ValueError):local.aplicar(d,req,[req['propuestas'][0]['id']])

    def test_pi_sin_nee_ni_resultados_inventados(self):
        a={'ID_Alumno':'A1','Nombre_Completo':'Alumno ficticio','ID_Escuela':'E1','Nombre_Escuela':'Escuela ficticia'}
        d=crear_plantilla('XXI',['A1'],[a],autor='Autor ficticio',funcion='Aprendizaje')
        d.update(id='pi-ficticio',cuenta='cuenta-ficticia');d['metadatos']['necesidades_confirmadas']='Orientación de lectura documentada'
        req=local.preparar(d,'Lectura con imágenes');new=local.aplicar(d,req,[req['propuestas'][0]['id']])
        self.assertFalse(new['tablas']['necesidades']);self.assertFalse(new['tablas']['evaluacion_final'])
        self.assertEqual(new['tablas']['barreras'][0]['BAP'],'')
        self.assertFalse(new['metadatos']['NEE confirmadas desde IEPP'])

    def test_sin_datos_no_inventa_y_respeta_autorizacion(self):
        d=documento();d['metadatos']['fuentes']=[]
        with self.assertRaises(ValueError):local.preparar(d)
        with patch.object(s,'autorizar',side_effect=PermissionError):
            with self.assertRaises(PermissionError):local.preparar(documento())


class DiagnosticoTests(unittest.TestCase):
    def test_solicitud_restringe_ids_y_contextos_a_opciones_validas(self):
        from ai.planeacion_completa import generar_completa,SCHEMA
        contexto={'fuentes':[{'id':'SEGEY-USAER'}],'referentes_por_grado':[]}
        anterior=deepcopy(SCHEMA)
        with patch.object(motor,'proponer',return_value={}) as llamada:
            generar_completa('Resumen ficticio','XXIII','Aprendizaje',contexto,{'sesiones':12},['Alumno 1'],{'E1':['Alumno 1']})
        props=llamada.call_args.kwargs['_schema']['properties']['unidades']['items']['properties']
        self.assertEqual(props['evidencias']['items']['enum'],['E1'])
        self.assertEqual(props['destinatarios']['items']['enum'],['Alumno 1'])
        self.assertEqual(props['referentes']['maxItems'],0)
        self.assertEqual(props['competencias']['maxItems'],0)
        self.assertIn('Aula regular',props['contexto']['enum'])
        self.assertEqual(SCHEMA,anterior)

    def llamada(self,texto,finish=None,validador=None):
        client=Mock();client.models.generate_content.return_value=SimpleNamespace(text=texto,candidates=[SimpleNamespace(finish_reason=finish)] if finish else [])
        types=SimpleNamespace(HttpOptions=lambda **k:k,HttpRetryOptions=lambda **k:k)
        genai=SimpleNamespace(Client=Mock(return_value=client),types=types);state={}
        with patch.dict(sys.modules,{'google':SimpleNamespace(genai=genai),'google.genai':genai,'google.genai.types':types}),patch.object(motor.st,'secrets',{'GEMINI_API_KEY':'ficticia'}),patch.object(motor.st,'session_state',state):
            with self.assertRaises(RuntimeError) as error:
                motor.proponer('Resumen ficticio','XXIII','Aprendizaje',_validador=validador)
        return state,str(error.exception),client

    def test_distingue_json_y_no_reintenta(self):
        state,msg,client=self.llamada('respuesta no estructurada')
        self.assertEqual(state['planeacion_ia_diagnostico']['motivo'],'JSONInvalido')
        self.assertEqual(client.models.generate_content.call_count,1)

    def test_distingue_salida_cortada_sin_guardar_texto(self):
        state,msg,_=self.llamada('PRIVADO incompleto','MAX_TOKENS')
        self.assertEqual(state['planeacion_ia_diagnostico']['motivo'],'SalidaCortada')
        self.assertNotIn('PRIVADO',str(state)+msg)

    def test_distingue_vinculo_invalido_sin_exponer_excepcion(self):
        def validador(data):raise RespuestaInvalida('DETALLE PRIVADO','Vinculo_evidencias')
        state,msg,_=self.llamada('{}',validador=validador)
        self.assertEqual(state['planeacion_ia_diagnostico']['motivo'],'Vinculo_evidencias')
        self.assertNotIn('PRIVADO',str(state)+msg)


class LocalUITests(unittest.TestCase):
    setUp=simple.RecorridoTests.setUp
    tearDown=simple.RecorridoTests.tearDown
    abrir=simple.RecorridoTests.abrir
    paso=simple.RecorridoTests.paso

    def test_cuatro_perfiles_preparan_revisan_editan_y_guardan_sin_ia(self):
        for area in ('Aprendizaje','Psicología','Comunicación','Trabajo Social'):
            with self.subTest(area=area):
                app=self.abrir(area);antes=deepcopy(app.session_state.versiones_ficticias[-1])
                next(b for b in app.button if b.label=='Preparar actividades con mis datos · sin IA').click().run()
                self.assertEqual(app.session_state.versiones_ficticias[-1],antes)
                next(c for c in app.checkbox if c.label.startswith('Revisé estas propuestas')).check().run()
                next(b for b in app.button if b.label=='Incorporar actividades locales a mi formato').click().run()
                self.assertFalse(app.exception)
                new=app.session_state.versiones_ficticias[-1]
                self.assertIn('preparacion_local',new['metadatos'])
                self.assertTrue(any(b.label=='Guardar borrador' for b in app.button))
                self.assertEqual(app.session_state.llamadas_ficticias,0)
                campo='Resultados obtenidos en los diferentes contextos' if area=='Trabajo Social' else 'Observaciones'
                next(t for t in app.text_area if t.label==campo).set_value('Edición manual después de preparación local').run()
                next(b for b in app.button if b.label=='Guardar borrador').click().run()
                self.assertEqual(app.session_state.versiones_ficticias[-1]['textos'][campo],'Edición manual después de preparación local')

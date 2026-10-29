"""Escenarios A–I con datos ficticios; sin Sheets ni servicios de IA reales."""
from copy import deepcopy
from datetime import date
import json,unittest
from unittest.mock import patch
from services import planeacion as s,memoria_pedagogica as m,planeacion_chat_contextual as c
from tests.test_planeacion_panel import documento,ACTOR


def fuente(tipo,texto,fecha='2026-10-25',alumno='A1',registro='registro-qa'):
    return {'tipo':tipo,'texto':texto,'fecha':fecha,'alumno':alumno,'registro':registro,'referencia':registro,
            'alcance':'individual','vinculo_verificado':True}


def ejemplo():
    d=documento();d['id']='plan-qa';d['revision']='r1';d['metadatos']['modalidad_planeacion']='individual'
    d['metadatos']['fuentes']=[fuente('EPP','No logra formar sílabas. Requiere instrucciones cortas y apoyos visuales.'),
        fuente('ACTA','Mayor participación al usar fichas y materiales manipulativos.',registro='visita-qa'),
        fuente('V','Sigue instrucciones cortas con apoyo visual.',registro='evento-qa')]
    d['tablas']['dosificacion']=[{'Actividades':'Clasificar fichas por sonido inicial.','Contextos':'Aula de apoyo','Recursos':'Fichas','Temporalidad':'30 minutos'}]
    d['textos']['Evaluación']='Lista de cotejo inicial'
    return d


class MemoriaChatTests(unittest.TestCase):
    def setUp(self):
        self.d=ejemplo()
        self.auth=patch.object(s,'autorizar',return_value=ACTOR);self.auth.start();self.addCleanup(self.auth.stop)
        self.ident=patch.object(s,'identidad',return_value=ACTOR);self.ident.start();self.addCleanup(self.ident.stop)
        self.cur=patch('services.curriculo.contexto_ia',return_value={'referentes_por_grado':[{'id':'R1','pda':'Reconoce sonidos iniciales.','contenido':'Lenguaje','fuente':'SEP','pagina_pdf':20}]})
        self.cur.start();self.addCleanup(self.cur.stop)

    def request(self,text='Quiero actividades más cortas y prácticas',tipo=c.TIPOS[0]):
        d,turn=c.registrar(self.d,'A1',text,tipo)
        return d,c.preparar(d,'A1',turn['id'])

    def respuesta(self,req,campo='Actividades',texto='Separar tres fichas por su sonido inicial con apoyo visual.'):
        target=next(k for k,v in req['destinos'].items() if v['ruta'][-1]==campo)
        return {'respuesta':'Propongo acortar esta actividad conservando su objetivo.','faltantes':[],
            'cambios':[{'destino':target,'texto':texto,'evidencias':[req['memoria']['hechos'][0]['id']],'referentes':['R1']}]}

    def test_A_recupera_epp_acta_eventos_con_fuentes_sin_expediente_integro(self):
        mem=m.construir(self.d,hoy=date(2026,10,28))
        self.assertEqual({r['tipo'] for r in mem['hechos']},{'EPP','ACTA','V'})
        payload=m.para_ia(self.d,mem,{'Alumno 1':'A1'})
        serial=json.dumps(payload)
        self.assertNotIn('plan-qa',serial);self.assertNotIn('registro-qa',serial)
        self.assertTrue(all(r['destinatarios']==['Alumno 1'] for r in payload['hechos']))

    def test_B_avance_reciente_primero_sin_presentar_historia_como_actual(self):
        self.d['metadatos']['fuentes']=[fuente('EPP','No reconoce vocales.','2025-09-01',registro='anterior'),
            fuente('V','Ya reconoce vocales con apoyo visual.','2026-10-26',registro='actual')]
        mem=m.construir(self.d,hoy=date(2026,10,28))
        self.assertEqual(mem['hechos'][0]['fecha'],'2026-10-26')
        self.assertEqual(mem['hechos'][-1]['temporalidad'],'historico')
        self.assertFalse(mem['conflictos'])

    def test_C_aceptar_solo_modifica_el_apartado_propuesto(self):
        d,req=self.request();res=c.validar(self.respuesta(req),req)
        pending=c.adjuntar_respuesta(d,req,res);before=deepcopy(pending)
        result=c.aplicar(pending,'A1')
        self.assertNotEqual(result['tablas']['dosificacion'][0]['Actividades'],before['tablas']['dosificacion'][0]['Actividades'])
        self.assertEqual(result['textos'],before['textos'])
        for campo in ('Recursos','Temporalidad','Contextos'):self.assertEqual(result['tablas']['dosificacion'][0][campo],before['tablas']['dosificacion'][0][campo])
        self.assertTrue(result['metadatos']['chat_contextual']['A1']['aprobaciones'])
        self.assertEqual(d['tablas'],self.d['tablas'])

    def test_D_contradiccion_actual_bloquea_ia_hasta_confirmacion(self):
        self.d['metadatos']['fuentes']=[fuente('ACTA','No reconoce vocales.','2026-10-23',registro='a'),fuente('V','Reconoce vocales.','2026-10-24',registro='b')]
        mem=m.construir(self.d,hoy=date(2026,10,28));self.assertEqual(len(mem['conflictos']),1)
        with self.assertRaises(ValueError):self.request()
        conflict=mem['conflictos'][0]
        resolved=m.resolver(self.d,conflict['id'],conflict['fuentes'][0])
        self.assertTrue(m.construir(resolved)['conflictos'][0]['resuelta'])
        self.assertNotIn('memoria_decisiones',self.d['metadatos'])

    def test_D_decision_conservada_si_cambia_la_relevancia_de_la_busqueda(self):
        self.d['metadatos']['fuentes']=[fuente('ACTA','No reconoce vocales. Requiere fichas.',registro='a'),fuente('V','Reconoce vocales. Usa dibujos.',registro='b')]
        cf=m.construir(self.d)['conflictos'][0]
        d=m.resolver(self.d,cf['id'],cf['fuentes'][0])
        updated=m.construir(d,necesidades=['dibujos'])
        self.assertTrue(updated['conflictos'][0]['resuelta'])


    def test_D_cambiar_documento_invalida_decision_anterior(self):
        self.d['metadatos']['fuentes']=[fuente('ACTA','No reconoce vocales.',registro='a'),fuente('V','Reconoce vocales.',registro='b')]
        mem=m.construir(self.d);cf=mem['conflictos'][0];d=m.resolver(self.d,cf['id'],cf['fuentes'][0])
        d['metadatos']['fuentes'][0]['texto']='No reconoce las vocales.'
        self.assertFalse(m.construir(d)['conflictos'][0]['resuelta'])

    def test_E_revision_siempre_muestra_14_pendientes_sin_certificar(self):
        from services.planeacion_calidad import revisar
        rows=revisar(self.d);self.assertEqual(len(rows),14)
        self.assertTrue(all(r['Valoración docente'] is None for r in rows))
        self.assertTrue(any(r['Comprobación estructural']!='Datos presentes; revisar pertinencia' for r in rows))

    def test_F_conversacion_y_propuesta_sobreviven_serializacion_reapertura(self):
        d,req=self.request();pending=c.adjuntar_respuesta(d,req,c.validar(self.respuesta(req),req))
        reopened=json.loads(json.dumps(pending))
        self.assertEqual(c.conversacion(reopened,'A1')['mensajes'][0]['texto'],req['entrada']['indicacion'])
        self.assertTrue(c.aplicar(reopened,'A1')['metadatos']['chat_contextual']['A1']['aprobaciones'])

    def test_G_rechaza_otro_alumno_antes_de_llamar_ia(self):
        with patch('ai.documento_json.generar') as ia:
            with self.assertRaises(PermissionError):c.registrar(self.d,'A2','Consulta otro expediente')
            with self.assertRaises(PermissionError):m.construir(self.d,'A2')
        ia.assert_not_called()

    def test_G_no_incluye_fuentes_ajenas_o_no_verificadas(self):
        self.d['metadatos']['fuentes'] += [fuente('EPP','SECRETO DE OTRO ALUMNO',alumno='A2'),{**fuente('V','NO VERIFICADO'),'vinculo_verificado':False},fuente('MATERIAL','GENERAL NO INDIVIDUAL')]
        text=json.dumps(m.construir(self.d),ensure_ascii=False)
        for value in ('SECRETO DE OTRO','NO VERIFICADO','GENERAL NO INDIVIDUAL'):self.assertNotIn(value,text)

    def test_G_permisos_se_revalidan_al_aceptar(self):
        d,req=self.request();d=c.adjuntar_respuesta(d,req,c.validar(self.respuesta(req),req))
        with patch.object(s,'autorizar',side_effect=PermissionError('Retirada asignación')):
            with self.assertRaises(PermissionError):c.aplicar(d,'A1')

    def test_I_datos_insuficientes_no_inventan_hallazgos(self):
        self.d['metadatos']['fuentes']=[]
        d,req=self.request('Necesito una propuesta')
        self.assertTrue(req['memoria']['provisional']);self.assertFalse(req['memoria']['hechos'])
        self.assertTrue(req['memoria']['faltantes'])
        self.assertNotIn('necesidades_confirmadas',d['metadatos'])

    def test_no_confirma_como_hecho_una_instruccion_o_respuesta_ia(self):
        d,req=self.request(tipo='Observación pendiente')
        self.assertFalse(d['metadatos']['chat_contextual']['A1']['mensajes'][0]['confirmada'])
        d=c.adjuntar_respuesta(d,req,c.validar(self.respuesta(req),req))
        self.assertNotIn('necesidades_confirmadas',d['metadatos'])
        self.assertNotIn('fuente_DOCENTE',d['metadatos'])

    def test_observacion_solo_se_incorpora_con_confirmacion_explicita_idempotente(self):
        d,turn=c.registrar(self.d,'A1','Participa durante cinco minutos con fichas.','Observación pendiente')
        with patch.object(s.repo,'timeline',return_value='TL-QA') as timeline,patch.object(s.repo,'clear_cache'):
            result=c.confirmar_observacion(d,'A1',turn['id']);otra=c.confirmar_observacion(result,'A1',turn['id'])
        timeline.assert_called_once()
        self.assertTrue(c.conversacion(otra,'A1')['mensajes'][0]['confirmada'])
        self.assertFalse(c.conversacion(d,'A1')['mensajes'][0]['confirmada'])

    def test_instruccion_temporal_no_se_puede_guardar_como_observacion(self):
        d,t=c.registrar(self.d,'A1','Hazlo más corto')
        with self.assertRaises(ValueError):c.confirmar_observacion(d,'A1',t['id'])

    def test_revision_concurrente_no_sobrescribe_redaccion(self):
        d,req=self.request();d=c.adjuntar_respuesta(d,req,c.validar(self.respuesta(req),req))
        d['tablas']['dosificacion'][0]['Recursos']='Cartulina corregida por docente'
        before=deepcopy(d)
        with self.assertRaises(ValueError):c.aplicar(d,'A1')
        self.assertEqual(d,before)

    def test_rechaza_destino_y_referencias_inventadas(self):
        d,req=self.request();response=self.respuesta(req);response['cambios'][0]['destino']='ID_Escuela'
        with self.assertRaises(PermissionError):c.validar(response,req)
        response=self.respuesta(req);response['cambios'][0]['evidencias']=['EPP inexistente']
        with self.assertRaises(ValueError):c.validar(response,req)

    def test_propuesta_guardada_no_puede_manipular_su_ruta(self):
        d,req=self.request();d=c.adjuntar_respuesta(d,req,c.validar(self.respuesta(req),req))
        pending=d['metadatos']['chat_contextual']['A1']['pendiente'];key=next(iter(pending['peticion']['destinos']))
        pending['peticion']['destinos'][key]['ruta']=['texto','Evaluación']
        with self.assertRaises(PermissionError):c.aplicar(d,'A1')

    def test_descartar_conserva_documento_y_conversacion(self):
        d,req=self.request();d=c.adjuntar_respuesta(d,req,c.validar(self.respuesta(req),req));r=c.descartar(d,'A1')
        self.assertEqual(r['tablas'],d['tablas']);self.assertEqual(r['textos'],d['textos'])
        self.assertFalse(c.conversacion(r,'A1').get('pendiente'));self.assertEqual(len(c.conversacion(r,'A1')['mensajes']),2)

    def test_editar_propuesta_solo_permite_destinos_propuestos(self):
        d,req=self.request();response=c.validar(self.respuesta(req),req);d=c.adjuntar_respuesta(d,req,response)
        key=response['cambios'][0]['destino'];r=c.aplicar(d,'A1',{key:'Actividad revisada por la docente con tres fichas.'})
        self.assertEqual(r['tablas']['dosificacion'][0]['Actividades'],'Actividad revisada por la docente con tres fichas.')
        with self.assertRaises(PermissionError):c.aplicar(d,'A1',{'otra-celda':'Texto'})

    def test_anonimizacion_y_fragmentos_pedagogicos_sin_familia_nominal(self):
        self.d['metadatos']['fuentes']=[fuente('EPP',json.dumps({'Nombre del padre':'PERSONA PRIVADA','Atención':'Requiere instrucciones cortas.'}))]
        mem=m.construir(self.d);self.assertNotIn('PERSONA PRIVADA',json.dumps(mem))
        self.assertIn('instrucciones',json.dumps(mem))

    def test_demanda_incompatible_con_nivel_se_rechaza(self):
        _,req=self.request();response=self.respuesta(req,texto='Lectura autónoma de textos extensos y redactar un ensayo.')
        with self.assertRaises(ValueError):c.validar(response,req)

    def test_memoria_acotada(self):
        self.d['metadatos']['fuentes']=[fuente('V','Avance observable con materiales visuales '+str(i),registro=str(i)) for i in range(200)]
        mem=m.construir(self.d);self.assertLessEqual(len(mem['hechos']),32)
        self.assertLessEqual(sum(len(r['texto']) for r in mem['hechos']),14000)

    def test_motor_de_generacion_utiliza_memoria_sin_transcribir_epp(self):
        from services import planeacion_generacion as g
        cfg={**g.configuracion(self.d),'inicio':'2026-10-28','sesiones':2,'actividades_solicitadas':2}
        with patch.object(g,'contexto_ia',return_value={'fuentes':[],'referentes_por_grado':[]}),patch.object(g,'sugerir_curriculo',side_effect=deepcopy):
            req=g.preparar_solicitud(self.d,cfg)
        self.assertIn('memoria_pedagogica',req['contexto'])
        self.assertNotIn('<evaluacion_psicopedagogica>',req['resumen'])
        self.assertTrue(any(k.startswith('M') for k in req['evidencias']))
        self.assertNotIn('Alumno ficticio',req['resumen'])

    def test_resumen_editado_no_reenvia_fragmentos_retirados_por_otra_via(self):
        from services import planeacion_generacion as g
        from ai.planeacion_completa import solicitud_completa
        self.d['metadatos']['fuentes']=[fuente('V','PEDAGOGIA ESPECIFICA A RETIRAR DEL ENVIO')]
        self.d['metadatos']['resumen_ia_completo']='Resumen mínimo revisado por la docente.'
        cfg={**g.configuracion(self.d),'inicio':'2026-10-28','sesiones':2}
        req=g.preparar_solicitud(self.d,cfg)
        prompt=solicitud_completa(req['resumen'],self.d['formato'],'Aprendizaje',req['contexto'],req['ajustes'],req['aliases'],req['evidencias'])
        self.assertNotIn('PEDAGOGIA ESPECIFICA A RETIRAR',prompt)
        self.assertIn('Resumen mínimo revisado',prompt)

    def test_cambio_de_antecedentes_no_aplica_propuesta_antigua(self):
        d,req=self.request();d=c.adjuntar_respuesta(d,req,c.validar(self.respuesta(req),req))
        d['metadatos']['fuentes'][0]['texto']='Ahora requiere otro apoyo documentado.'
        with self.assertRaises(ValueError):c.aplicar(d,'A1')

    def test_sin_pda_es_provisional_y_pide_vinculacion_sin_cambiar_curriculo(self):
        with patch('services.curriculo.contexto_ia',return_value={'referentes_por_grado':[]}):
            d,req=self.request()
        self.assertTrue(req['memoria']['provisional'])
        respuesta=self.respuesta(req);respuesta['cambios'][0]['referentes']=[]
        validated=c.validar(respuesta,req)
        self.assertTrue(any('PDA oficial' in f for f in validated['faltantes']))
        self.assertEqual(d['metadatos'].get('curriculo'),self.d['metadatos'].get('curriculo'))


    def test_boton_chat_del_formato_valida_y_conserva_ediciones_pendientes(self):
        from services import planeacion_papel as papel
        spec=papel.hoja(self.d)
        self.assertTrue(spec['chat_contextual'])
        cell=next(k for k,v in spec['cells'].items() if v['target']==('tabla','dosificacion',0,'Actividades'))
        evento={'documento':self.d['id'],'huella':papel.huella(self.d),'nonce':'qa-chat','accion':'chat','cambios':{cell:'Edición antes de abrir chat'}}
        result=papel.aplicar(self.d,evento)
        self.assertEqual(result['tablas']['dosificacion'][0]['Actividades'],'Edición antes de abrir chat')
        grupal=deepcopy(self.d);grupal['metadatos']['modalidad_planeacion']='grupal'
        evento.update(huella=papel.huella(grupal),cambios={})
        with self.assertRaises(PermissionError):papel.aplicar(grupal,evento)


    def test_chat_es_inline_y_no_abre_modal(self):
        from ui import planeacion_papel as ui
        with patch.object(ui.st,'session_state',{'p_papel_panel':'chat'}),patch.object(ui.st,'button',return_value=False),patch.object(ui.st,'dialog') as dialog,patch('ui.planeacion_chat.render_asistente_dialogo') as render:
            ui.conexiones('p');render.assert_called_once();dialog.assert_not_called()


class ChatUITests(unittest.TestCase):
    def test_H_chat_compacto_propone_acepta_y_mantiene_contexto_por_documento(self):
        from pathlib import Path
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_file(str(Path(__file__).parent/'fixtures/chat_contextual_app.py'),default_timeout=30).run()
        self.assertFalse(app.exception)
        consent=next(w for w in app.checkbox if w.label.startswith('Permitir propuestas'))
        consent.check().run()
        app.chat_input[0].set_value('Haz la actividad más corta y con fichas').run()
        self.assertFalse(app.exception)
        self.assertTrue(any(b.label=='Aceptar cambios' for b in app.button))
        self.assertEqual(app.session_state['qa_chat_Uno_doc']['tablas']['dosificacion'][0]['Actividades'],'Clasificar fichas por sonido inicial.')
        next(b for b in app.button if b.label=='Aceptar cambios').click().run()
        self.assertFalse(app.exception)
        self.assertIn('Agrupar tres fichas',app.session_state['qa_chat_Uno_doc']['tablas']['dosificacion'][0]['Actividades'])
        next(r for r in app.radio if r.label=='Documento ficticio').set_value('Dos').run()
        self.assertFalse(app.exception);self.assertFalse(app.chat_message)
        next(r for r in app.radio if r.label=='Documento ficticio').set_value('Uno').run()
        self.assertFalse(app.exception);self.assertGreaterEqual(len(app.chat_message),2)


if __name__=='__main__':unittest.main()

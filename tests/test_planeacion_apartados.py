from copy import deepcopy
import unittest
from unittest.mock import patch
from services import planeacion_apartados as p,planeacion_papel as papel
from tests.test_planeacion_completa import documento
from tests import test_planeacion_papel as papeltests


class ApartadosTests(unittest.TestCase):
    def setUp(self):
        self.auth=patch.object(p.s,'autorizar',return_value={});self.auth.start();self.addCleanup(self.auth.stop)
        import pandas as pd
        self.padron=patch.object(p.s,'padron_autorizado',return_value=pd.DataFrame());self.padron.start();self.addCleanup(self.padron.stop)

    def doc(self,area='Aprendizaje',dos=False):
        d=documento(area,dos=dos)
        d['tablas']['barreras' if area=='Trabajo Social' else 'aprendizajes']=[]
        return d

    def test_propone_tres_celdas_con_antecedentes_sin_motor(self):
        d=self.doc();antes=deepcopy(d)
        with patch('ai.planeacion.proponer') as ia:
            new=p.proponer(d)
        row=new['tablas']['aprendizajes'][0]
        self.assertTrue(all(row[k] for k in ['Necesidades educativas específicas','Aprendizaje y/u objetivo','Descriptor de logro']))
        self.assertTrue(row['Necesidades educativas específicas'].startswith('Necesita '))
        self.assertTrue(row['_nee_origen']['propuesta'])
        ia.assert_not_called();self.assertEqual(d,antes)
        self.assertEqual(new['datos'],d['datos']);self.assertEqual(new['textos'],d['textos'])

    def test_no_mezcla_alumnos_ni_fuentes_ajenas(self):
        d=self.doc(dos=True)
        d['metadatos']['fuentes'][0]['texto']='LECTURA PROPIA UNO'
        d['metadatos']['fuentes'][1]['texto']='CONTEO PROPIO DOS'
        d['metadatos']['fuentes'].append({**d['metadatos']['fuentes'][0],'alumno':'AJENO','texto':'DATO AJENO'})
        d['metadatos']['fuentes'].append({**d['metadatos']['fuentes'][0],'alumno':'A1,A2','texto':'ANTECEDENTE COMPARTIDO, NO INDIVIDUAL'})
        rows=p.proponer(d)['tablas']['aprendizajes']
        self.assertEqual(len(rows),2)
        self.assertIn('comprensión de textos',rows[0]['Necesidades educativas específicas'])
        self.assertNotIn('CONTEO PROPIO DOS',str(rows[0]))
        self.assertNotIn('LECTURA PROPIA UNO',str(rows[1]))
        self.assertNotIn('DATO AJENO',str(rows))
        self.assertNotIn('ANTECEDENTE COMPARTIDO',str(rows))

    def test_idempotente_y_respeta_ediciones_y_aportes(self):
        d=p.proponer(self.doc());self.assertEqual(p.proponer(d),d)
        d['tablas']['aprendizajes'][0]['Descriptor de logro']='DECISIÓN DOCENTE'
        self.assertEqual(p.proponer(d)['tablas']['aprendizajes'][0]['Descriptor de logro'],'DECISIÓN DOCENTE')
        d=self.doc();d['tablas']['aprendizajes']=[{'Necesidades educativas específicas':'','Aprendizaje y/u objetivo':'','Descriptor de logro':'','_aporte':'PSIC'}]
        self.assertEqual(p.proponer(d),d)

    def test_completa_vacios_de_una_fila_manual_sin_sustituir_la_redaccion(self):
        d=self.doc();d['tablas']['aprendizajes']=[{'Necesidades educativas específicas':'DECISIÓN DOCENTE','Aprendizaje y/u objetivo':'','Descriptor de logro':''}]
        new=p.proponer(d)
        self.assertEqual(len(new['tablas']['aprendizajes']),1)
        self.assertEqual(new['tablas']['aprendizajes'][0]['Necesidades educativas específicas'],'DECISIÓN DOCENTE')
        self.assertTrue(new['tablas']['aprendizajes'][0]['Descriptor de logro'])

    def test_sin_evidencia_propone_hipotesis_sin_confirmarla(self):
        d=self.doc();d['metadatos']['fuentes']=[];d['metadatos'].pop('curriculo',None)
        with patch.object(p,'contexto_ia',return_value={'referentes_por_grado':[]}):
            inicial=p.proponer(d)
        self.assertIn('sin hallazgos suficientes',inicial['tablas']['aprendizajes'][0]['_nee_origen']['origen'])
        self.assertTrue(inicial['tablas']['aprendizajes'][0]['_nee_origen']['propuesta'])
        r={'id':'OFICIAL','grado':5,'contenido':'Lectura compartida','pda':'PDA verificado','fuente':'SEP','pagina_pdf':3}
        with patch.object(p,'contexto_ia',return_value={'referentes_por_grado':[r]}):new=p.proponer(d)
        self.assertTrue(new['tablas']['aprendizajes'][0]['_nee_origen']['propuesta'])
        self.assertIn('Lectura compartida',new['tablas']['aprendizajes'][0]['Aprendizaje y/u objetivo'])
        self.assertEqual(new['tablas']['aprendizajes'][0]['_referentes_apartados'],['OFICIAL'])

    def test_cuatro_areas_sin_resultados_ni_nee_por_condicion(self):
        for area in ['Aprendizaje','Psicología','Comunicación','Trabajo Social']:
            d=self.doc(area);new=p.proponer(d)
            self.assertEqual(new['textos'],d['textos'])
            tabla='barreras' if area=='Trabajo Social' else 'aprendizajes'
            if area=='Trabajo Social':self.assertFalse(new['tablas'][tabla])  # El antecedente de lectura no establece una BAP.
            else:self.assertTrue(new['tablas'][tabla])
            self.assertNotIn('diagnóstico',str(new['tablas'][tabla]).lower())

    def test_hoja_edita_borra_y_retira_sin_regenerar_automaticamente(self):
        d=p.proponer(self.doc());spec=papel.hoja(d)
        key=next(k for k,c in spec['cells'].items() if c['target']==('tabla','aprendizajes',0,'Descriptor de logro'))
        def ev(doc,**kw):return {'documento':doc['id'],'huella':papel.huella(doc),'cambios':{},**kw}
        blank=papel.aplicar(d,ev(d,cambios={key:''}))
        self.assertEqual(blank['tablas']['aprendizajes'][0]['Descriptor de logro'],'')
        self.assertEqual(papel.hoja(blank)['tables'][0]['rows'][0][2]['value'],'')
        retirado=papel.aplicar(blank,ev(blank,accion='retirar',tabla='aprendizajes',fila=0,confirmado=True))
        self.assertFalse(retirado['tablas']['aprendizajes'])
        self.assertFalse(papel.hoja(retirado)['tables'][0]['rows'][0][2]['value'])
        solicitado=papel.aplicar(retirado,ev(retirado,accion='apartados'))
        self.assertTrue(solicitado['tablas']['aprendizajes'])

    def test_pi_y_documento_no_autorizado_no_se_rellenan(self):
        d=self.doc();d['formato']='XXI';self.assertEqual(p.proponer(d),d)
        with patch.object(p.s,'autorizar',side_effect=PermissionError):
            with self.assertRaises(PermissionError):p.proponer(self.doc())


class ApartadosUITests(unittest.TestCase):
    setUp=papeltests.PapelUITests.setUp
    tearDown=papeltests.PapelUITests.tearDown
    abrir=papeltests.PapelUITests.abrir

    def test_nuevo_formato_ya_propone_celdas_sin_solicitar_ia(self):
        app=self.abrir();doc=app.session_state.versiones_ficticias[-1]
        self.assertTrue(doc['tablas']['aprendizajes'][0]['Descriptor de logro'])
        self.assertEqual(app.session_state.llamadas_ficticias,0)
        app.run();self.assertFalse(app.exception)
        self.assertEqual(app.session_state.versiones_ficticias[-1]['id'],doc['id'])

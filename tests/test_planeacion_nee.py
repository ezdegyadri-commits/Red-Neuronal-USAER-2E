from copy import deepcopy
import json
import unittest
from unittest.mock import patch
import pandas as pd
from services import planeacion_nee as nee,planeacion_apartados as apartados
from services.planeacion_modelo import crear_plantilla
from tests import test_planeacion_apartados as base


class NeeTests(unittest.TestCase):
    setUp=base.ApartadosTests.setUp
    doc=base.ApartadosTests.doc

    def test_bapse_no_se_copia_ni_se_usa_para_inferir_lectura(self):
        d=self.doc();d['metadatos']['fuentes'][0].update(tipo='III',texto='BAP_Fisicas: {"Item_1":{"pregunta":"LECTURA ESCRITURA ATENCION","frecuencia":"Siempre"}}')
        new=apartados.proponer(d);r=new['tablas']['aprendizajes'][0]
        self.assertNotIn('BAP_Fisicas',str(r));self.assertNotIn('Item_1',str(r));self.assertNotIn('comprensión de textos',r['Necesidades educativas específicas'])
        self.assertEqual(r['_nee_origen']['referencias'],[])

    def test_padron_prioritario_por_id_no_por_condicion(self):
        d=self.doc(dos=True)
        frame=pd.DataFrame([{'ID_Alumno':'A1','NEE':'Necesita consolidar la escritura de mensajes.'},{'ID_Alumno':'A2','NEE':'Necesita desarrollar el concepto de número.'}])
        with patch.object(apartados.s,'padron_autorizado',return_value=frame):new=apartados.proponer(d)
        self.assertEqual(new['tablas']['aprendizajes'][0]['Necesidades educativas específicas'],frame.iloc[0]['NEE'])
        self.assertEqual(new['tablas']['aprendizajes'][1]['Necesidades educativas específicas'],frame.iloc[1]['NEE'])
        self.assertFalse(new['tablas']['aprendizajes'][0]['_nee_origen']['propuesta'])

    def test_captura_unica_de_columna_nee_opcional(self):
        a={'ID_Alumno':'A1','Nombre_Completo':'Ficticio','ID_Escuela':'E1','Nombre_Escuela':'Escuela ficticia','Grado':'3','NEE_Propuesta':'Desarrollar la comunicación funcional'}
        d=crear_plantilla('XXIII',['A1'],[a],autor='Autor ficticio',funcion='Aprendizaje')
        self.assertEqual(d['datos']['Alumnos'][0]['NEE registrada'],a['NEE_Propuesta'])
        self.assertEqual(nee.redactar_nee(a['NEE_Propuesta']),'Necesita desarrollar la comunicación funcional')

    def test_epp_conclusion_revisada_precede_hipotesis(self):
        d=self.doc();d['metadatos']['fuentes'][0].update(tipo='EPP',parte='Conclusión',texto=json.dumps({'NEE':[{'NEE':'Necesita ampliar su vocabulario funcional.'}]}))
        r=apartados.proponer(d)['tablas']['aprendizajes'][0]
        self.assertEqual(r['Necesidades educativas específicas'],'Necesita ampliar su vocabulario funcional.')
        self.assertEqual(r['_nee_origen']['origen'],'EPP revisada')

    def test_repara_copia_legacy_exacta_y_respeta_edicion_docente(self):
        d=self.doc();f=d['metadatos']['fuentes'][0]
        legacy=d['datos']['Alumnos'][0]['Nombre del alumno']+' · Antecedentes para revisar la necesidad educativa (no confirma NEE):\n['+f['referencia']+'] '+f['texto'][:900]
        d['tablas']['aprendizajes']=[{'Necesidades educativas específicas':legacy,'Aprendizaje y/u objetivo':'Objetivo docente','Descriptor de logro':'Descriptor docente','_alumnos_apartados':['A1']}]
        before=deepcopy(d);new=apartados.proponer(d)
        self.assertNotEqual(new['tablas']['aprendizajes'][0]['Necesidades educativas específicas'],legacy)
        self.assertEqual(new['tablas']['aprendizajes'][0]['Descriptor de logro'],'Descriptor docente');self.assertEqual(d,before)
        d['tablas']['aprendizajes'][0]['Necesidades educativas específicas']=legacy+'\nEDITADO POR DOCENTE'
        self.assertEqual(apartados.proponer(d)['tablas']['aprendizajes'][0]['Necesidades educativas específicas'],d['tablas']['aprendizajes'][0]['Necesidades educativas específicas'])

    def test_bapse_no_puede_copiarse_con_usar_evidencia(self):
        from services.planeacion_formato import usar_evidencia
        with self.assertRaisesRegex(ValueError,'BAPSE'):usar_evidencia(self.doc(),{'tipo':'III','texto':'BAP_Fisicas: {}'})

    def test_pdf_distingue_la_nee_propuesta_de_una_determinacion(self):
        from documents.planeacion_papel import generar_pdf
        from pypdf import PdfReader
        from io import BytesIO
        d=apartados.proponer(self.doc());texto='\n'.join(p.extract_text() for p in PdfReader(BytesIO(generar_pdf(d))).pages)
        self.assertIn('NEE propuesta para valoración',texto)


class FormatoUITests(unittest.TestCase):
    from tests import test_planeacion_papel as papeltests
    setUp=papeltests.PapelUITests.setUp
    tearDown=papeltests.PapelUITests.tearDown

    def test_boton_individual_o_grupal_abre_su_formato(self):
        from pathlib import Path
        from streamlit.testing.v1 import AppTest
        from services.planeacion_papel import hoja
        for area,modo,ids in [('Aprendizaje','Individual',['I1','I2']),('Aprendizaje','Grupal',['A1','A2']),('Psicología','Individual',['I1']),('Trabajo Social','Mi intervención',['A1'])]:
            app=AppTest.from_file(str(Path(__file__).with_name('fixture_planeacion_papel.py')),default_timeout=30).run()
            app.radio[0].set_value(area).run()
            next(w for w in app.button_group if w.label=='Modalidad de planeación').set_value(modo).run()
            next(w for w in app.multiselect if w.label=='Alumnos de mi formato').set_value(ids).run()
            next(b for b in app.button if b.label=='Abrir formato con mis alumnos').click().run()
            self.assertFalse(app.exception)
            d=app.session_state.versiones_ficticias[-1];spec=hoja(d)
            self.assertEqual(d['metadatos']['modalidad_planeacion'],'especialista' if modo=='Mi intervención' else modo.lower())
            self.assertEqual(spec['grupal'],area=='Aprendizaje' and modo=='Grupal')
            self.assertEqual(spec['tables'][0]['id'],'guia' if spec['grupal'] else 'alumnos_ts' if area=='Trabajo Social' else 'competencias' if area=='Psicología' else 'aprendizajes')

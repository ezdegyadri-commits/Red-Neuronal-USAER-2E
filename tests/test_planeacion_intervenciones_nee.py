"""Una intervención por necesidad. Exclusivamente datos ficticios, sin red."""
from copy import deepcopy
import json
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch
from tests.test_planeacion_completa import documento
from services import planeacion_intervenciones_nee as s, planeacion_papel as papel

LECTURA='Necesita fortalecer la lectura de palabras con apoyos visuales.'
CONTEO='Necesita practicar el conteo de objetos con material concreto.'


def ejemplo(area='Aprendizaje',formato=None):
    d=documento(area);d['metadatos']['modalidad_planeacion']='individual'
    if formato:
        from services.planeacion_modelo import FORMATOS
        d['formato']=formato;d['tablas']={k:[] for k in FORMATOS[formato]['tablas']}
    d['metadatos']['fuentes']=[{'tipo':'EPP','parte':'Conclusión','alumno':'A1','vinculo_verificado':True,
        'registro':'EPP-QA-Conclusión','documento_origen':'EPP-QA','revision':'REV-QA','referencia':'E1',
        'texto':json.dumps({'NEE':[{'NEE':LECTURA},{'NEE':CONTEO}]}),'alcance':'individual'}]
    return d


class IntervencionesNEETests(TestCase):
    def agregar(self,doc):return s.incorporar(doc,[r['id'] for r in s.catalogo(doc)])

    def test_dos_necesidades_crean_apartados_independientes_por_perfil(self):
        for area in ('Aprendizaje','Psicología','Comunicación','Trabajo Social'):
            with self.subTest(area=area):
                doc=ejemplo(area);antes=deepcopy(doc);nuevo=self.agregar(doc)
                bs=s.bloques(nuevo);self.assertEqual(len(bs),2)
                self.assertEqual(doc,antes);self.assertEqual(nuevo['tablas'],antes['tablas'])
                self.assertEqual(set(bs[0]['campos']),set(s.CAMPOS))
                nuevo=s.editar(nuevo,bs[0]['id'],'Actividades','Actividad exclusiva de lectura.')
                nuevo=s.editar(nuevo,bs[1]['id'],'Actividades','Actividad exclusiva de conteo.')
                self.assertNotEqual(s.bloques(nuevo)[0]['campos']['Actividades'],s.bloques(nuevo)[1]['campos']['Actividades'])
                self.assertEqual(len(s.bloques(self.agregar(nuevo))),2)

    def test_plan_anual_individual_admite_varias_necesidades(self):
        self.assertEqual(len(s.bloques(self.agregar(ejemplo(formato='XXI')))),2)

    def test_misma_nee_de_dos_alumnos_no_se_mezcla(self):
        doc=ejemplo();segundo=deepcopy(doc['datos']['Alumnos'][0]);segundo['ID_Alumno']='A2'
        doc['datos']['Alumnos'].append(segundo)
        doc['metadatos']['fuentes'].append({**doc['metadatos']['fuentes'][0],'alumno':'A2','registro':'EPP-QA-2','documento_origen':'EPP-QA-2'})
        bs=s.bloques(self.agregar(doc))
        self.assertEqual(len(bs),4);self.assertEqual({b['alumno'] for b in bs},{'A1','A2'})

    def test_nee_descartada_o_detectada_no_entra_por_fuente_historica(self):
        doc=ejemplo();source=doc['metadatos']['fuentes'][0]
        source['texto']=json.dumps({'NEE':[{'NEE':LECTURA,'Estado':'Validada'},{'NEE':CONTEO,'Estado':'Descartada'}]})
        self.assertEqual(len(s.catalogo(doc)),1)
        self.assertEqual(len(s.bloques(self.agregar(doc))),1)

    def test_revision_por_nee_no_exige_duplicar_aprendizajes_o_dosificacion(self):
        from services.planeacion import revisar
        doc=self.agregar(ejemplo())
        self.assertTrue(s.revisar(doc))
        for b in s.bloques(doc):
            for c in s.CAMPOS:doc=s.editar(doc,b['id'],c,'Contenido docente de prueba')
        self.assertEqual(s.revisar(doc),[])
        faltas=revisar(doc)
        self.assertFalse(any('aprendizajes' in f or 'actividades, tiempos' in f or 'evaluación formativa' in f for f in faltas),faltas)
        b=s.bloques(doc)[1];doc=s.editar(doc,b['id'],'Actividades','')
        self.assertTrue(any('NEE 2' in f and 'Actividades' in f for f in revisar(doc)))
        from services.planeacion_revision import pendientes
        self.assertTrue(any(p['target']==('intervencion_nee',b['id'],'Actividades') for p in pendientes(doc)[1]))

    def test_especialistas_no_duplican_sesiones_grupales_en_individual_por_nee(self):
        from services.planeacion_equipo import preparar, revisar
        for area in ('Psicología','Comunicación','Trabajo Social'):
            doc=self.agregar(preparar(ejemplo(area)))
            self.assertEqual(revisar(doc),[])

    def test_sin_epp_conserva_propuesta_y_tablas_anteriores(self):
        doc=documento();doc['metadatos']['modalidad_planeacion']='individual';antes=deepcopy(doc)
        self.assertEqual(s.catalogo(doc),[]);self.assertEqual(s.incorporar(doc,[]),antes)
        self.assertEqual(doc,antes)

    def test_necesidad_ajena_sin_validar_o_grupal_no_se_incorpora(self):
        doc=ejemplo()
        with self.assertRaises(PermissionError):s.incorporar(doc,['NEE-AJENA'])
        doc['metadatos']['fuentes'][0]['vinculo_verificado']=False
        self.assertEqual(s.catalogo(doc),[])
        doc['metadatos']['modalidad_planeacion']='grupal'
        with self.assertRaises(ValueError):s.incorporar(doc,[])

    def test_otra_revision_de_epp_no_modifica_intervencion_guardada(self):
        doc=self.agregar(ejemplo());before=deepcopy(doc['metadatos']['intervenciones_nee'])
        doc['metadatos']['fuentes'][0].update(revision='OTRA',texto=json.dumps({'NEE':[{'NEE':'Necesita fortalecer otra habilidad documentada en la evaluación.'}]}))
        self.assertEqual(s.bloques(doc),before)
        recuperado=json.loads(json.dumps(doc));self.assertEqual(s.bloques(recuperado),before)

    def test_hoja_y_evento_editan_solo_bloque_elegido(self):
        doc=self.agregar(ejemplo());antes=deepcopy(doc)
        with patch.object(papel.s,'autorizar',return_value={'area':'Aprendizaje','cuenta':'qa','director':False}):
            spec=papel.hoja(doc)
            campos=[c for c in spec['cells'].values() if c['target'] and c['target'][0]=='intervencion_nee' and c['label']=='Actividades']
            self.assertEqual(len(campos),2)
            nuevo=papel.aplicar(doc,{'documento':doc['id'],'huella':spec['huella'],'accion':'guardar','cambios':{campos[1]['id']:'CONTEO-QA'}})
        self.assertEqual(s.bloques(nuevo)[0],s.bloques(antes)[0]);self.assertEqual(s.bloques(nuevo)[1]['campos']['Actividades'],'CONTEO-QA')

    def test_evento_de_seleccion_multiple_valida_y_conserva_texto_previo(self):
        doc=ejemplo();antes=deepcopy(doc)
        with patch.object(papel.s,'autorizar',return_value={'area':'Aprendizaje','cuenta':'qa','director':False}):
            spec=papel.hoja(doc)
            nuevo=papel.aplicar(doc,{'documento':doc['id'],'huella':spec['huella'],'accion':'incorporar_nee',
                'cambios':{},'nee_ids':[r['id'] for r in spec['nee_intervenciones']]})
        self.assertEqual(nuevo['tablas'],antes['tablas']);self.assertEqual(len(s.bloques(nuevo)),2)

    def test_pdf_incluye_cada_intervencion_y_sus_actividades(self):
        import pymupdf
        from documents.planeacion import generar_pdf
        for area in ('Aprendizaje','Psicología','Comunicación','Trabajo Social'):
            doc=self.agregar(ejemplo(area));bs=s.bloques(doc)
            doc=s.editar(doc,bs[0]['id'],'Actividades','LECTURA-QA-UNICA')
            doc=s.editar(doc,bs[1]['id'],'Actividades','CONTEO-QA-UNICO')
            with patch.object(papel.s,'autorizar',return_value={'area':area,'cuenta':'qa','director':False}):pdf=generar_pdf(doc)
            with pymupdf.open(stream=pdf,filetype='pdf') as pages:text='\n'.join(p.get_text() for p in pages)
            self.assertIn('LECTURA-QA-UNICA',text);self.assertIn('CONTEO-QA-UNICO',text)

    def test_trabajo_social_no_convierte_nee_en_bap(self):
        doc=ejemplo('Trabajo Social');antes=deepcopy(doc['tablas']['barreras'])
        nuevo=self.agregar(doc);self.assertEqual(nuevo['tablas']['barreras'],antes)

    def test_formulario_seleccion_multiple_y_guardado_independiente(self):
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_file(str(Path(__file__).parent/'fixtures/planeacion_nee_bloques_app.py'),default_timeout=30).run()
        self.assertFalse(app.exception)
        app.multiselect[0].set_value([r['id'] for r in s.catalogo(app.session_state.qa_doc)]).run()
        next(b for b in app.button if b.label=='Agregar NEE y sus apartados').click().run()
        self.assertFalse(app.exception);self.assertEqual(len(s.bloques(app.session_state.qa_doc)),2)
        actividades=[t for t in app.text_area if t.label=='Actividades']
        actividades[0].set_value('LECTURA-UI-QA').run()
        self.assertFalse(app.exception)
        bs=s.bloques(app.session_state.qa_doc)
        self.assertEqual(bs[0]['campos']['Actividades'],'LECTURA-UI-QA');self.assertEqual(bs[1]['campos']['Actividades'],'')

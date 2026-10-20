"""Visibilidad y síntesis sin migraciones: solo documentos ficticios."""
from copy import deepcopy
from io import BytesIO
from unittest import TestCase
from unittest.mock import patch
from pypdf import PdfReader
from services import planeacion_papel as papel,planeacion_equipo as equipo
from services.planeacion_compartida import situacion_inicial
from services.planeacion_modalidad import guia_grupal
from documents.planeacion_papel import generar_pdf,preparar_descarga
from tests.test_planeacion_panel import ACTOR
from tests.test_planeacion_compartida import grupal
from tests.test_planeacion_cero_friccion import individual


class VisibilidadTests(TestCase):
    def setUp(self):
        self.auth=patch.object(papel.s,'autorizar',return_value=ACTOR)
        self.auth.start();self.addCleanup(self.auth.stop)

    def texto_pdf(self,doc):
        return '\n'.join(p.extract_text() for p in PdfReader(BytesIO(generar_pdf(doc))).pages)

    def test_actividad_psicologia_visible_editable_y_eliminable_sin_copias(self):
        d=equipo.preparar(individual('Psicología'))
        d['metadatos']['equipo']['competencias'][0]['Actividad prevista']='ACTIVIDAD_ORIGINAL_FICTICIA'
        before=deepcopy(d);spec=papel.hoja(d)
        c=next(c for c in spec['cells'].values() if c['target']==('competencia',0,'Actividad prevista'))
        self.assertEqual(c['value'],'ACTIVIDAD_ORIGINAL_FICTICIA');self.assertTrue(c['editable'])
        self.assertIn(c['value'],self.texto_pdf(d))
        evento={'documento':d['id'],'huella':spec['huella'],'accion':'guardar','cambios':{c['id']:''}}
        edited=papel.aplicar(d,evento)
        self.assertEqual(edited['metadatos']['equipo']['competencias'][0]['Actividad prevista'],'')
        self.assertEqual(edited['tablas'],d['tablas']);self.assertEqual(d,before)

    def test_detalle_grupal_y_observaciones_en_hoja_pdf_sin_rellenar_ni_duplicar(self):
        d=grupal();d['tablas']['dosificacion'][0]['Actividades']='DETALLE_FICTICIO_UNICO'
        d['textos']['Evaluación']='OBSERVACION_FICTICIA_UNICA'
        before=deepcopy(d);spec=papel.hoja(d)
        table=next(t for t in spec['tables'] if t['id']=='dosificacion')
        self.assertEqual(len(table['rows']),1);self.assertFalse(table['add']);self.assertFalse(table['delete'])
        cell=next(c for c in spec['cells'].values() if c['value']=='DETALLE_FICTICIO_UNICO')
        self.assertTrue(cell['editable'])
        pdf=self.texto_pdf(d)
        self.assertEqual(pdf.count('DETALLE_FICTICIO_UNICO'),1)
        self.assertEqual(pdf.count('OBSERVACION_FICTICIA_UNICA'),1)
        self.assertEqual(d,before)

    def test_colaborador_lee_detalle_sin_poder_editar_otra_area(self):
        d=grupal();d['tablas']['dosificacion'][0]['Actividades']='Detalle de apoyo'
        with patch.object(papel.s,'autorizar',return_value={**ACTOR,'area':'Comunicación'}):
            spec=papel.hoja(d,colaborativa=True)
        cell=next(c for c in spec['cells'].values() if c['value']=='Detalle de apoyo')
        self.assertFalse(cell['editable']);self.assertIsNone(cell['target'])
        self.assertTrue(any(c['editable'] and c['label']=='Comunicación' for c in spec['cells'].values()))

    def test_copia_bapse_se_resume_sin_modificar_registro_ni_redaccion_docente(self):
        d=grupal();raw='E1 · 2026-09-10 · BAP_Fisicas: {"Item_1":{"pregunta":"¿Áreas delimitadas?","frecuencia":"Siempre"}}'
        d['metadatos']['grupal_zona']=[{'ID_Alumno':'A1','Situación inicial':raw}]
        d['metadatos']['contexto_padron_grupo']={'A1':{'NEE':'Necesita consolidar la lectura de palabras.'}}
        before=deepcopy(d);resumen=guia_grupal(d)['filas'][0]['Situación inicial']
        self.assertEqual(resumen,'RI · Necesita consolidar la lectura de palabras.')
        self.assertNotIn('BAP_Fisicas',self.texto_pdf(d));self.assertEqual(d,before)
        d['metadatos']['guia_grupal_manual']={'filas':[{'ID_Alumno':'A1','Situación inicial':'RI · Lee palabras con apoyo visual.'}]}
        self.assertEqual(guia_grupal(d)['filas'][0]['Situación inicial'],'RI · Lee palabras con apoyo visual.')

    def test_sintesis_breve_solo_nee_verificada_no_inventa_ni_cruza_alumnos(self):
        a={'ID_Alumno':'A1','Situacion_Alumno':'NI','NEE':'Necesita '+('fortalecer la lectura ' * 50)}
        self.assertLessEqual(len(situacion_inicial(a,[])),240)
        fuente={'tipo':'EPP','parte':'Conclusión','vinculo_verificado':True,'alumno':'A1','texto':'{"NEE":[{"NEE":"Necesita comunicar sus necesidades."}]}'}
        a.pop('NEE')
        self.assertIn('comunicar',situacion_inicial(a,[fuente]))
        self.assertNotIn('comunicar',situacion_inicial(a,[{**fuente,'alumno':'A2'}]))
        self.assertNotIn('comunicar',situacion_inicial(a,[{**fuente,'vinculo_verificado':False}]))

    def test_cache_pdf_anterior_no_oculta_columnas_nuevas(self):
        import streamlit as st
        d=individual();d['revision']='revision-ficticia'
        estado={'_pdf_spec_cache':{(d['id'],d['revision']):{'spec_antiguo':True}}}
        with patch.object(st,'session_state',estado),patch('documents.planeacion_papel.hoja',wraps=papel.hoja) as hoja:
            preparar_descarga(d);preparar_descarga(d)
            self.assertEqual(hoja.call_count,1)

    def test_generacion_ensambla_resumen_no_fragmentos_del_expediente(self):
        from services import planeacion_generacion as g
        from tests.test_planeacion_completa import documento,resultado
        d=documento();d['datos']['Alumnos'][0]['Situacion_Alumno']='RI'
        d['metadatos']['contexto_padron_grupo']={'A1':{'NEE':'Necesita apoyos para leer palabras.'}}
        d=g.prellenar(d);req=g.preparar_solicitud(d,{**g.configuracion(d),'inicio':'2026-10-07','grado_referencia':3})
        before=deepcopy(d);nuevo=g.ensamblar(d,resultado(req,'Aprendizaje'),req)
        self.assertEqual(nuevo['metadatos']['grupal_zona'][0]['Situación inicial'],'RI · Necesita apoyos para leer palabras.')
        self.assertEqual(d,before)

    def test_copia_antigua_de_fragmentos_se_sintetiza_tambien_en_pdf(self):
        d=grupal();raw='E1 · 2026-09-10: Fragmento antiguo muy largo del expediente.'
        d['metadatos']['grupal_zona']=[{'ID_Alumno':'A1','Situación inicial':raw}]
        self.assertNotIn(raw,guia_grupal(d)['filas'][0]['Situación inicial'])
        self.assertNotIn('Fragmento antiguo',self.texto_pdf(d))
        self.assertEqual(d['metadatos']['grupal_zona'][0]['Situación inicial'],raw)

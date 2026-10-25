"""Matriz de aceptación EPP→NEE→planeación. Solo alumnos y documentos ficticios."""
from contextlib import ExitStack
from copy import deepcopy
import json
from unittest import TestCase
from unittest.mock import Mock, patch
from services import nee_documentales as n, documentos_sintesis as ds
from services import planeacion_necesidades as pn

TEXTO='Necesita fortalecer la lectura de palabras con apoyos visuales.'


class NEEIntegracionTests(TestCase):
    def setUp(self):
        self.rows=[];self.ws=Mock()
        self.doc={'ID_Documento':'DOC-QA','SHA256':'hash-qa','Tipo':'EPP','Ambito':'individual',
            'ID_Alumnos_JSON':'["QA-1"]','Ciclo':'2026-2027','Fecha':'2026-10-25'}
        self.ws.append_rows.side_effect=lambda rows,**kw:self.rows.extend(dict(zip(ds.HEADERS,r)) for r in rows)
        stack=ExitStack();self.addCleanup(stack.close)
        for obj,name,kwargs in ((ds.archivo,'listar',{'return_value':[self.doc]}),
            (ds,'_rows',{'side_effect':lambda:deepcopy(self.rows)}),
            (ds,'ensure_headers',{'return_value':(self.ws,ds.HEADERS)}),
            (ds,'retry_google',{'side_effect':lambda f:f()}),(ds,'clear_cache',{}),
            (ds.st,'session_state',{'new':{'usuario':'profesional-ficticia'}})):
            stack.enter_context(patch.object(obj,name,**kwargs))

    def propuesta(self,estado='Detectada'):
        r=n.detectar('Página 2\n'+TEXTO,'DOC-QA','hash-qa')[0];r['estado']=estado;return r

    def guardar(self,rows,rev=''):
        return ds.guardar('DOC-QA',{'resumen':'Síntesis pedagógica ficticia.','nee_registros':rows},revision_esperada=rev)

    def plan(self,aid='QA-1'):
        return {'datos':{'Alumnos':[{'ID_Alumno':aid,'Nombre del alumno':'Nombre homónimo ficticio'}],
            'Curso escolar':'2026-2027'},'metadatos':{'fuentes':[]},'tablas':{'aprendizajes':[{'NEE':'Redacción previa'}]}}

    def fuente(self):
        return [{**f,'vinculo_verificado':True,'referencia':'E1'} for f in ds.fuentes_epp({'QA-1'},'2026-2027')]

    def test_01_extraccion_explicita_con_pagina_y_procedencia(self):
        r=self.propuesta();self.assertEqual(r['pagina'],'2');self.assertEqual(r['estado'],'Detectada')
        self.assertEqual(r['fundamento'],TEXTO)
        q=n.detectar('Necesidades educativas específicas\nFortalecer la lectura de palabras mediante apoyos visuales.','D','H')
        self.assertEqual(len(q),1);self.assertEqual(q[0]['origen'],'Sección de NEE')

    def test_02_pdf_escaneado_usa_ocr_existente(self):
        import pymupdf
        from services.materiales_planeacion import leer_material
        with pymupdf.open() as pdf:
            pdf.new_page();data=pdf.tobytes()
        with patch('services.materiales_planeacion._ocr',return_value=TEXTO) as ocr:
            read=leer_material('epp-ficticia.pdf',data)
        ocr.assert_called_once();self.assertEqual(n.detectar(read['texto'],'D','H')[0]['pagina'],'1')

    def test_03_ilegible_no_se_confirma_y_conserva_lo_legible(self):
        rows=n.detectar('Necesita [ilegible] para leer palabras.\n'+TEXTO,'D','H')
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['estado'],'Detectada')
        r=self.propuesta('Validada');r['fundamento']='Necesita [ilegible] en esta evaluación.'
        with self.assertRaises(ValueError):self.guardar([r])

    def test_04_detectadas_y_descartadas_no_llegan_al_selector(self):
        self.guardar([self.propuesta()]);self.assertEqual(json.loads(self.fuente()[0]['texto'])['NEE'],[])
        self.assertEqual(ds.listar()['DOC-QA']['nee_registros'][0]['estado'],'Detectada')

    def test_05_varias_validadas_con_identidad_y_autoria_servidor(self):
        a=self.propuesta('Validada');b={**a,'id':'','texto':'Necesita practicar el conteo de objetos con material concreto.'}
        a['alumno']='AJENO';a['validada_por']='autor-inyectado'
        self.guardar([a,b]);r=ds.listar()['DOC-QA']['nee_registros']
        self.assertEqual(len({v['id'] for v in r}),2)
        self.assertTrue(all(v['alumno']=='QA-1' and v['validada_por']=='profesional-ficticia' and v['validada_en'] for v in r))
        doc=self.plan();doc['metadatos']['fuentes']=self.fuente();self.assertEqual(len(pn.opciones(doc)),2)

    def test_06_homonimos_no_comparten_necesidades(self):
        self.guardar([self.propuesta('Validada')]);doc=self.plan('QA-2');doc['metadatos']['fuentes']=self.fuente()
        self.assertEqual(pn.opciones(doc),[])

    def test_07_cambio_alumno_descarta_catalogo_ajeno(self):
        d=self.plan('QA-2');d['metadatos']['catalogo_nee_actual']=[{'alumno':'QA-1','texto':TEXTO}]
        self.assertEqual(pn.opciones(d),[])

    def test_08_nueva_revision_preserva_historia_y_el_identificador(self):
        rev=self.guardar([self.propuesta('Validada')]);before=deepcopy(self.rows)
        r=deepcopy(ds.listar()['DOC-QA']['nee_registros'][0]);r['texto']='Necesita fortalecer la lectura de oraciones con apoyos visuales.'
        self.guardar([r],rev);self.assertEqual(self.rows[:1],before)
        self.assertEqual(ds.listar()['DOC-QA']['nee_registros'][0]['id'],r['id'])

    def test_09_actualiza_catalogo_sin_cambiar_selecciones_historicas(self):
        self.guardar([self.propuesta('Validada')]);doc=self.plan();before=deepcopy(doc)
        with patch('services.planeacion.autorizar'),patch.object(ds.archivo,'descargar') as download:
            result=pn.actualizar_catalogo(doc)
        self.assertEqual(doc,before);self.assertEqual(result['tablas'],before['tablas'])
        self.assertEqual(pn.opciones(result)[0]['texto'],TEXTO);download.assert_not_called()

    def test_10_sin_epp_no_bloquea_redaccion_manual(self):
        doc=self.plan();before=deepcopy(doc)
        with patch('services.planeacion.autorizar'):result=pn.actualizar_catalogo(doc)
        self.assertEqual(pn.opciones(result),[]);self.assertEqual(result['tablas'],before['tablas'])

    def test_11_dos_sesiones_no_sobrescriben_revision_reciente(self):
        rev=self.guardar([self.propuesta()]);original=deepcopy(ds.listar()['DOC-QA']['nee_registros'])
        a=deepcopy(original);a[0]['estado']='Validada';self.guardar(a,rev)
        b=deepcopy(original);b[0]['estado']='Descartada'
        with self.assertRaisesRegex(RuntimeError,'Otra profesional'):self.guardar(b,rev)
        self.assertEqual(len(self.rows),2);self.assertEqual(ds.listar()['DOC-QA']['nee_registros'][0]['estado'],'Validada')

    def test_12_deduplica_variantes_y_permite_descartar_equivalentes(self):
        a=self.propuesta('Validada');b={**a,'id':'','texto':TEXTO.replace('Necesita','Requiere')}
        with self.assertRaisesRegex(ValueError,'repetidas'):self.guardar([a,b])
        b['estado']='Descartada';self.guardar([a,b]);self.assertEqual(len(json.loads(self.fuente()[0]['texto'])['NEE']),1)

    def test_13_sin_permisos_y_documento_colectivo_rechazan_guardado(self):
        with patch.object(ds.archivo,'listar',return_value=[]):
            with self.assertRaises(PermissionError):self.guardar([self.propuesta('Validada')])
        self.doc['ID_Alumnos_JSON']='["QA-1","QA-2"]'
        with self.assertRaises(ValueError):self.guardar([self.propuesta()])
        self.ws.append_rows.assert_not_called()

    def test_14_fallo_de_red_preserva_fuente_y_reintento_no_duplica(self):
        r=self.propuesta('Validada');rev=self.guardar([r])
        self.assertEqual(self.guardar([r],rev),rev);self.assertEqual(len(self.rows),1)
        self.ws.append_rows.side_effect=RuntimeError('Fallo ficticio')
        r['estado']='Descartada'
        with self.assertRaises(RuntimeError):self.guardar([r],rev)
        self.assertEqual(ds.listar()['DOC-QA']['nee_registros'][0]['estado'],'Validada')

    def test_15_diagnosticos_y_ejemplos_no_se_convierten_en_necesidades(self):
        self.assertEqual(n.detectar('Diagnóstico: TEA.\nEjemplo: Necesita fortalecer la lectura de palabras.','D','H'),[])
        self.assertEqual(n.detectar('Dificultades en matemáticas. Requiere apoyo general.','D','H'),[])

    def test_16_legado_revisado_se_conserva_sin_inventar_pagina(self):
        from ui.documento_sintesis import _registros_guardados
        r=_registros_guardados({'necesidades':[TEXTO]},'DOC-QA','H')
        self.assertEqual(r[0]['estado'],'Validada');self.assertEqual(r[0]['pagina'],'')
        self.assertEqual(r[0]['fundamento'],TEXTO)

    def test_17_propuesta_docente_requiere_fundamento_y_no_toma_autoria_de_cliente(self):
        r={**self.propuesta('Validada'),'id':'','origen':'Propuesta docente','fundamento':''}
        with self.assertRaises(ValueError):self.guardar([r])
        r['fundamento']='Página 2: omite letras al escribir palabras documentadas.'
        rev=self.guardar([r]);self.assertTrue(ds.listar()['DOC-QA']['nee_registros'][0]['id'])
        self.assertEqual(self.guardar([r],rev),rev)
        self.assertEqual(len(self.rows),1)

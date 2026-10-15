from copy import deepcopy
from io import BytesIO
import unittest
from unittest.mock import patch
from pypdf import PdfReader
from services import planeacion as s,planeacion_papel as papel
from services.planeacion_limpieza import normalizar
from services.planeacion_revision import pendientes
from tests.test_planeacion_completa import documento
from tests import test_planeacion_panel as panel


class ClaridadTests(unittest.TestCase):
    def setUp(self):
        self.auth=patch.object(s,'autorizar',return_value={});self.auth.start();self.addCleanup(self.auth.stop)

    def test_repara_instrumento_legacy_y_conserva_necesidad_docente(self):
        d=documento();d['datos']['Alumnos'][0]['NEE registrada']='Necesita fortalecer la atención sostenida.'
        f=d['metadatos']['fuentes'][0];f.update(tipo='III',texto='BAP_Fisicas: {"Item_1":{"pregunta":"El salón tiene áreas delimitadas", "frecuencia":"Pocas veces"}}')
        raw='[III · E1] '+f['texto'];d['tablas']['aprendizajes']=[{'Necesidades educativas específicas':raw,'Aprendizaje y/u objetivo':'Objetivo docente','Descriptor de logro':'Descriptor docente'}]
        before=deepcopy(d);limpio=normalizar(d)
        row=limpio['tablas']['aprendizajes'][0]
        self.assertEqual(row['Necesidades educativas específicas'],'Necesita fortalecer la atención sostenida.')
        self.assertEqual(row['_nee_reparada']['anterior'],raw);self.assertEqual(row['Descriptor de logro'],'Descriptor docente');self.assertEqual(d,before)
        spec=papel.hoja(d);self.assertNotIn('Item_1',' '.join(c['value'] for c in spec['cells'].values()))
        self.assertTrue(next(c for c in spec['cells'].values() if c['target']==('tabla','aprendizajes',0,'Necesidades educativas específicas'))['editable'])
        from documents.planeacion_papel import generar_pdf
        text=' '.join(p.extract_text() for p in PdfReader(BytesIO(generar_pdf(d))).pages)
        self.assertNotIn('BAP_Fisicas',text);self.assertIn('atención sostenida',text)
        limpio['tablas']['aprendizajes'][0]['Necesidades educativas específicas']='Redacción elegida por la maestra.'
        self.assertEqual(normalizar(limpio),limpio)
        d['tablas']['aprendizajes'][0]['Aprendizaje y/u objetivo']=''
        d['tablas']['aprendizajes'][0]['Descriptor de logro']=''
        propuesta=normalizar(d)
        self.assertTrue(propuesta['tablas']['aprendizajes'][0]['Descriptor de logro'].startswith('El alumno'))
        self.assertTrue(propuesta['tablas']['aprendizajes'][0]['Aprendizaje y/u objetivo'])
        propuesta['tablas']['aprendizajes'][0]['Descriptor de logro']=''
        self.assertEqual(normalizar(propuesta)['tablas']['aprendizajes'][0]['Descriptor de logro'],'')

    def test_sin_filas_de_relleno_y_edicion_con_indices_reales(self):
        d=documento();before=deepcopy(d);spec=papel.hoja(d)
        self.assertEqual(next(t for t in spec['tables'] if t['id']=='dosificacion')['rows'],[])
        def ev(doc,**kwargs):return {'documento':doc['id'],'huella':papel.huella(doc),'cambios':{},**kwargs}
        new=papel.aplicar(d,ev(d,accion='agregar',tabla='dosificacion'))
        tabla=next(t for t in papel.hoja(new)['tables'] if t['id']=='dosificacion')
        self.assertEqual(tabla['indices'],[4]);self.assertEqual(len(tabla['rows']),1)
        key=next(k for k,c in papel.hoja(new)['cells'].items() if c['target']==('tabla','dosificacion',4,'Actividades'))
        new=papel.aplicar(new,ev(new,accion='guardar',cambios={key:'Actividad nueva'}))
        self.assertEqual(new['tablas']['dosificacion'][4]['Actividades'],'Actividad nueva')
        removed=papel.aplicar(new,ev(new,accion='retirar',tabla='dosificacion',fila=4,confirmado=True))
        self.assertEqual(removed['tablas']['dosificacion'],before['tablas']['dosificacion']);self.assertEqual(d,before)

    def test_pendientes_llevan_a_la_celda_y_no_cuentan_metadatos(self):
        d=documento();d['tablas']['aprendizajes']=[{'Necesidades educativas específicas':'Necesita comprender textos.','Aprendizaje y/u objetivo':'Identifica una idea.','Descriptor de logro':''},
            {'_alumnos_apartados':['A1'],'Necesidades educativas específicas':'','Aprendizaje y/u objetivo':'','Descriptor de logro':''}]
        _,items=pendientes(d)
        self.assertEqual(len([i for i in items if 'descriptor' in i['mensaje']]),1)
        spec=papel.hoja(d);item=next(i for i in spec['pendientes'] if 'descriptor' in i['mensaje'])
        self.assertEqual(spec['cells'][item['celda']]['target'],('tabla','aprendizajes',0,'Descriptor de logro'))
        self.assertFalse(any('fila 2' in i['mensaje'] for i in items))

    def test_descarga_diferida_autoriza_antes_del_hilo_y_no_genera_al_abrir(self):
        from documents import planeacion_papel as pdf
        d=documento()
        with patch.object(pdf,'_generar_pdf',return_value=b'PDF') as generar:
            descargar=pdf.preparar_descarga(d);generar.assert_not_called()
            with patch.object(s,'autorizar',side_effect=RuntimeError('No session_state en el hilo')):
                self.assertEqual(descargar(),b'PDF')
            generar.assert_called_once()

    def test_ensamble_ia_prioriza_nee_docente_y_separa_fundamentos(self):
        from services import planeacion_generacion as g
        from tests.test_planeacion_completa import resultado
        d=documento();d['datos']['Alumnos'][0]['NEE registrada']='Necesita fortalecer la atención sostenida.'
        req=g.preparar_solicitud(d,{**g.configuracion(d),'inicio':'2026-10-15'})
        respuesta=resultado(req,'Aprendizaje')
        for unidad in respuesta['unidades']:unidad['necesidad']='BAP_Fisicas: {"pregunta":"Una pregunta del instrumento"}'
        nuevo=g.ensamblar(d,respuesta,req)
        for row in nuevo['tablas']['aprendizajes']:
            self.assertEqual(row['Necesidades educativas específicas'],'Necesita fortalecer la atención sostenida.')
        self.assertFalse(any('Fundamento:' in r.get('Actividades','') for r in nuevo['tablas']['dosificacion']))
        self.assertIn('resultado',nuevo['metadatos']['generacion_completa'])


class BorradoresTests(unittest.TestCase):
    setUp=panel.PanelTests.setUp
    tearDown=panel.PanelTests.tearDown

    def test_eliminacion_versionada_conserva_historia_y_bloquea_sesion_obsoleta(self):
        saved=s.guardar(panel.documento());before=deepcopy(saved)
        eliminado=s.eliminar_borrador(saved)
        self.assertTrue(eliminado['metadatos']['borrador_eliminado']);self.assertEqual(s.listar(),[])
        self.assertEqual(len(s.listar(True)),2);self.assertEqual(s.listar(True)[0]['revision'],before['revision'])
        self.assertEqual(saved,before)
        with self.assertRaises(RuntimeError):s.guardar(saved)
        restaurado=s.restaurar_borrador(eliminado)
        self.assertFalse(restaurado['metadatos'].get('borrador_eliminado'))
        self.assertEqual(len(s.listar()),1);self.assertEqual(len(s.listar(True)),3)

    def test_no_elimina_documento_enviado_ni_de_otro_autor(self):
        d=panel.documento();d['estado']='ENVIADO'
        with self.assertRaises(PermissionError):s.eliminar_borrador(d)
        d['estado']='BORRADOR';d['cuenta']='otra-cuenta'
        with self.assertRaises(PermissionError):s.eliminar_borrador(d)
        self.assertEqual(len(self.sheet.rows),1)
        saved=s.guardar(panel.documento())
        with patch.object(s,'versiones_actuales',return_value=[{**saved,'estado':'ENVIADO'}]):
            with self.assertRaises(PermissionError):s.eliminar_borrador(saved)

"""Casos exclusivamente ficticios: resumen, procedencia de NEE y cambio interno."""
from copy import deepcopy
import json
from unittest import TestCase
from unittest.mock import Mock, patch
import pandas as pd
from services.documento_sintesis import sintetizar, necesidades_explicitas
from services.planeacion_necesidades import opciones
from services import documentos_sintesis as ds, padron_movimientos as mv, alumnos

NEED='Necesita fortalecer la lectura funcional mediante apoyos visuales.'


def fuente(aid='QA-1', **extras):
    return {'tipo':'EPP','parte':'Conclusión','alumno':aid,'vinculo_verificado':True,
            'texto':json.dumps({'NEE':[{'NEE':NEED}]}),'referencia':'E1','revision':'r1',**extras}


class SintesisTests(TestCase):
    def test_resumen_breve_no_transcripcion_completa_ni_datos_de_contacto(self):
        text='CURP: CLAVE FICTICIA\nDomicilio: NO REAL\n'+('Texto administrativo repetido del formato.\n'*50)+NEED
        r=sintetizar(text)
        self.assertLessEqual(len(r['resumen']),800)
        self.assertIn('lectura funcional',r['resumen'])
        self.assertNotIn('CURP',r['resumen']);self.assertNotIn('Domicilio',r['resumen'])
        self.assertNotEqual(r['resumen'],text)

    def test_no_infiere_necesidades_de_diagnostico_o_palabras_aisladas(self):
        self.assertEqual(necesidades_explicitas('Condición: TEA. Atención y lectura.'),[])
        self.assertEqual(necesidades_explicitas('Ejemplo: '+NEED),[])
        self.assertEqual(necesidades_explicitas('Necesita [ilegible] para leer palabras.'),[])
        self.assertEqual(necesidades_explicitas(NEED+'\n• '+NEED),[NEED])

    def test_selector_solo_conclusion_o_escaneo_revisado_de_mismo_id(self):
        d={'datos':{'Alumnos':[{'ID_Alumno':'QA-1'}]},'metadatos':{'fuentes':[
            fuente(),fuente(),fuente('AJENO'),fuente(parte='Psicología'),fuente(vinculo_verificado=False),
            fuente(tipo='III'),fuente('QA-1,AJENO'),fuente(tipo='EPP_ESCANEADA',revision='r2')]}}
        self.assertEqual(len(opciones(d)),1)
        self.assertEqual(opciones(d)[0]['revision'],'r1')
        d['metadatos']['fuentes']=[fuente(tipo='EPP_ESCANEADA')]
        self.assertEqual(opciones(d)[0]['tipo'],'EPP_ESCANEADA')

    def test_hoja_viva_ofrece_lista_sin_reemplazar_celda_ni_modificar_impresion(self):
        from tests.test_planeacion_local import documento
        from services import planeacion_papel as papel
        d=documento();d['metadatos'].update(modalidad_planeacion='individual',fuentes=[fuente('A1')])
        d['datos']['Alumnos'][0]['ID_Alumno']='A1'
        d['tablas']['aprendizajes']=[{'Necesidades educativas específicas':'Texto previo docente',
                                    'Aprendizaje y/u objetivo':'','Descriptor de logro':'','_fila_manual':True}]
        before=deepcopy(d)
        with patch.object(papel.s,'autorizar',return_value={}):
            spec=papel.hoja(d)
            cells=[c for c in spec['cells'].values() if c['label']=='Necesidades educativas específicas']
            self.assertTrue(cells)
            self.assertEqual(cells[0]['sugerencias_nee'][0]['texto'],NEED)
            imp=papel.hoja(d,para_impresion=True)
            self.assertFalse(any(c.get('sugerencias_nee') for c in imp['cells'].values()))
        self.assertEqual(d,before)


class IndiceTests(TestCase):
    def setUp(self):
        self.doc={'ID_Documento':'DOC-QA','SHA256':'hash-original','Tipo':'EPP','Ambito':'individual',
                  'ID_Alumnos_JSON':'["QA-1"]','Ciclo':'2026-2027','Fecha':'2026-10-23'}
        self.value={'resumen':'Síntesis breve de resultados ficticios.','necesidades':[NEED]}

    def test_indice_verifica_escritura_y_reintento_idempotente(self):
        rows=[];ws=Mock()
        ws.append_rows.side_effect=lambda values,**kw:rows.extend(dict(zip(ds.HEADERS,r)) for r in values)
        with patch.object(ds.archivo,'listar',return_value=[self.doc]),patch.object(ds,'_rows',side_effect=lambda:deepcopy(rows)),patch.object(ds,'ensure_headers',return_value=(ws,ds.HEADERS)),patch.object(ds,'retry_google',side_effect=lambda f:f()),patch.object(ds,'clear_cache'),patch.object(ds.st,'session_state',{'usuario':'cuenta-ficticia'}):
            a=ds.guardar('DOC-QA',self.value);b=ds.guardar('DOC-QA',self.value)
            self.assertEqual(a,b);self.assertEqual(ws.append_rows.call_count,1)
            self.assertEqual(ws.append_rows.call_args.kwargs['value_input_option'],'RAW')
            self.assertEqual(ds.fuentes_epp({'QA-1'},'2026-2027')[0]['tipo'],'EPP_ESCANEADA')
            self.assertEqual(ds.fuentes_epp({'AJENO'},'2026-2027'),[])
            self.assertEqual(ds.fuentes_epp({'QA-1'},'2025-2026'),[])

    def test_sin_permiso_o_documento_multialumno_no_se_escribe(self):
        with patch.object(ds.archivo,'listar',return_value=[]),patch.object(ds,'ensure_headers') as write:
            with self.assertRaises(PermissionError):ds.guardar('DOC-QA',self.value)
            write.assert_not_called()
        with patch.object(ds.archivo,'listar',return_value=[{**self.doc,'ID_Alumnos_JSON':'["QA-1","QA-2"]'}]),patch.object(ds,'ensure_headers') as write:
            with self.assertRaises(ValueError):ds.guardar('DOC-QA',self.value)
            write.assert_not_called()

    def test_hash_distinto_no_reutiliza_sintesis_y_no_lee_binarios_para_listar(self):
        row={'ID_Documento':'DOC-QA','SHA256':'otro-hash','Sintesis_JSON':json.dumps(self.value),'Revision':'r1'}
        with patch.object(ds.archivo,'listar',return_value=[self.doc]),patch.object(ds,'_rows',return_value=[row]),patch.object(ds.archivo,'descargar') as download:
            self.assertEqual(ds.listar(),{});download.assert_not_called()

    def test_no_publica_nee_no_revisadas(self):
        row={'ID_Documento':'DOC-QA','SHA256':'hash-original','Sintesis_JSON':json.dumps({**self.value,'revisada':False}),'Revision':'r1'}
        with patch.object(ds.archivo,'listar',return_value=[self.doc]),patch.object(ds,'_rows',return_value=[row]):
            self.assertEqual(ds.listar(),{})


class MatriculaInternaTests(TestCase):
    def alumno(self,**kw):
        return {'ID_Alumno':'QA-IN','ID_Escuela':'ESC-002','Nombre_Escuela':'Ichcaanziho',
                'Maestra de Apoyo':'Mtra. María Cecilia Solís Vázquez','Grado':'6o.','Grupo':'B',
                'CURP':'','Estatus':'Activo',**kw}

    def test_cambio_interno_solo_responsable_sin_borrar_ubicacion(self):
        actual=self.alumno();before=deepcopy(actual)
        cambios=mv.preparar(actual,'Cambiar maestra en la misma escuela',docente='MARYCRUZ CAAMAL CORAL')
        self.assertEqual(cambios,{'Maestra de Apoyo':'MARYCRUZ CAAMAL CORAL'})
        self.assertEqual(actual,before)
        for nombre in ('DIANELY DE SUGEIDY CAAMAL TAMAY','Caamal','MARIA CECILIA SOLIS VAZQUEZ'):
            with self.assertRaises(ValueError):mv.preparar(actual,'Cambiar maestra en la misma escuela',docente=nombre)
        with self.assertRaises(ValueError):mv.preparar(self.alumno(ID_Escuela='ESC-004'),'Cambiar maestra en la misma escuela',docente='MARYCRUZ CAAMAL CORAL')

    def test_nueve_de_sexto_sin_confundir_dianely_ni_modalidad(self):
        from services.expedientes import alumnos_visibles
        from services.planeacion_matricula import preparar
        from services.planeacion_viva import opciones_padron
        rows=[self.alumno(ID_Alumno=f'QA-{i}',**{'Maestra de Apoyo':'Mtra. Marycruz Caamal Coral','Tipo_Atencion':'Individual' if i<2 else 'Grupal'}) for i in range(9)]
        rows += [self.alumno(ID_Alumno='QA-CECI'),self.alumno(ID_Alumno='QA-DIANELY',ID_Escuela='ESC-004',**{'Maestra de Apoyo':'Mtra. Dianely de Sugeidy Caamal Tamay'})]
        with patch('services.expedientes.repo.alumnos',return_value=pd.DataFrame(rows)):
            frame=preparar(alumnos_visibles('APOYO','ESC-002','Mtra. Marycruz Caamal Coral'))
        self.assertEqual(len(frame),9);self.assertTrue(frame['Grado'].eq('6°').all())
        self.assertEqual(len(opciones_padron(frame,'ESC-002','grupal','6°')),7)
        self.assertEqual(len(opciones_padron(frame,'ESC-002','individual','6°')),2)

    def test_cero_asignados_no_muestra_los_de_la_otra_maestra(self):
        frame=pd.DataFrame([self.alumno()])
        self.assertTrue(alumnos.filtrar_alumnos_por_docente_compartido(frame,'Marycruz Caamal Coral').empty)

    def test_ejecutar_audita_cambio_interno_y_rechaza_especialista(self):
        current=self.alumno();log=[]
        state={'autenticado':True,'usuario':'qa-ceci','nombre':'María Cecilia Solís Vázquez','rol':'APOYO'}
        with patch.object(mv.st,'session_state',state),patch.object(mv,'visibles',return_value=pd.DataFrame([current])),patch.object(mv.repo,'read',return_value=pd.DataFrame([current])),patch.object(mv,'ensure_sheet',return_value=Mock(row_values=lambda _:mv.HEADERS)),patch.object(mv,'_anexar',side_effect=lambda r:log.append(deepcopy(r))),patch.object(mv.repo,'actualizar_ubicacion_alumno') as write:
            mv.ejecutar('QA-IN','Cambiar maestra en la misma escuela','Cambio de responsable ficticio',docente='MARYCRUZ CAAMAL CORAL')
            self.assertEqual(write.call_args.args[1],{'Maestra de Apoyo':'MARYCRUZ CAAMAL CORAL'})
        self.assertEqual([r['Estado'] for r in log],['PREPARADO','CONFIRMADO'])
        with patch.object(mv.st,'session_state',{**state,'rol':'Comunicación'}),patch.object(mv.repo,'actualizar_ubicacion_alumno') as write:
            with self.assertRaises(PermissionError):mv.ejecutar('QA-IN','Cambiar maestra en la misma escuela','No autorizado ficticio',docente='MARYCRUZ CAAMAL CORAL')
            write.assert_not_called()

    def test_epp_continua_con_nueva_responsable_solo_tras_movimiento_confirmado(self):
        from services import epp
        original=self.alumno();actual=self.alumno(**{'Maestra de Apoyo':'Marycruz Caamal Coral'})
        doc={'alumno':'QA-IN','partes':{'META':{'cuenta':'qa-ceci','contenido':{'coordinadora':'María Cecilia Solís Vázquez'}}}}
        actor={'cuenta':'qa-mary','nombre':'Marycruz Caamal Coral','rol':'APOYO','director':False,'area':'Aprendizaje'}
        row={'ID_Alumno':'QA-IN','Accion':'Cambiar maestra en la misma escuela','Estado':'PREPARADO','ID_Movimiento':'mov-qa',
             'Antes_JSON':json.dumps({'Maestra de Apoyo':original['Maestra de Apoyo']}),'Despues_JSON':json.dumps({'Maestra de Apoyo':actual['Maestra de Apoyo']})}
        before=deepcopy(doc)
        with patch.object(epp,'actor',return_value=actor),patch.object(epp,'alumno_autorizado',return_value=actual),patch.object(mv.repo,'read',return_value=pd.DataFrame([row])):
            self.assertFalse(epp.es_coordinadora(doc))
        with patch.object(epp,'actor',return_value=actor),patch.object(epp,'alumno_autorizado',return_value=actual),patch.object(mv.repo,'read',return_value=pd.DataFrame([{**row,'Estado':'CONFIRMADO'}])):
            self.assertTrue(epp.es_coordinadora(doc))
        self.assertEqual(doc,before)

"""Datos sintéticos: movimientos, archivo privado y paginación."""
from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch,Mock
import json
import pandas as pd
from services import archivo_expediente as ar,padron_movimientos as mv
from config.settings import ESCUELAS_USAER

ALUMNO={'ID_Alumno':'QA1','Nombre_Completo':'Alumno ficticio','ID_Escuela':str(ESCUELAS_USAER['Damián Carmona']),
    'Nombre_Escuela':'Damián Carmona','Tipo_Atencion':'Grupal','Grado':'2o.','Grupo':'A','Estatus':'Activo','CURP':'FICTICIA-NO-OFICIAL','Maestra de Apoyo':'CINDY MAYANIN BURGOS GONZALEZ'}
STATE={'autenticado':True,'usuario':'cuenta-prueba','nombre':'Cindy','rol':'APOYO'}


class PresentacionSeguraTests(TestCase):
    def test_matricula_grupal_retiros_auditados_sin_perder_filas(self):
        from tests.test_planeacion_compartida import grupal
        from tests.test_planeacion_panel import ALUMNO as R
        from services.planeacion_compartida import proyectar_retiros
        from services import planeacion as p,planeacion_papel as papel
        d=grupal();d['datos']['Alumnos'].append({**d['datos']['Alumnos'][0],'ID_Alumno':'A2'})
        d['metadatos']['guia_grupal_manual']={'filas':[{'ID_Alumno':'A1','Aprendizaje':'Actividad histórica'}]}
        d['metadatos']['aportaciones_equipo']={'Comunicación':{'filas':[{'ID_Alumno':'A1','Texto en formato':'Aporte histórico'}]}}
        antes=deepcopy(d);frame=pd.DataFrame([{**R,'ID_Alumno':'A2'}])
        with patch.object(p.repo,'alumnos',return_value=pd.DataFrame([{**R,'Estatus':'Baja'},{**R,'ID_Alumno':'A2'}])):
            nuevo=proyectar_retiros(d,frame)
        self.assertEqual([a['ID_Alumno'] for a in nuevo['datos']['Alumnos']],['A2'])
        hist=nuevo['metadatos']['alumnos_retirados_del_grupo']['A1']
        self.assertEqual(hist['fila']['Aprendizaje'],'Actividad histórica')
        self.assertEqual(hist['aportaciones']['Comunicación'][0]['Texto en formato'],'Aporte histórico')
        self.assertEqual(d,antes)
        with patch.object(p.repo,'alumnos',return_value=pd.DataFrame([{**R,'ID_Escuela':'OTRA'}])),patch.object(mv,'traslado_confirmado',return_value=False):
            self.assertEqual(proyectar_retiros(d,frame),d)
        from tests.test_planeacion_panel import ACTOR
        with patch.object(p,'autorizar',return_value=ACTOR):
            spec=papel.hoja(nuevo)
        self.assertEqual({c['destinatario'] for c in spec['cells'].values() if c.get('destinatario')},{'A2'})

    def test_historial_grupal_solo_origen_y_solo_con_traslado_probado(self):
        from tests.test_planeacion_compartida import grupal
        from tests.test_planeacion_panel import ALUMNO as R,ACTOR
        from services import planeacion as p,asignaciones
        d=grupal();vacio=pd.DataFrame(columns=['ID_Alumno','ID_Escuela'])
        with patch.object(p,'identidad',return_value=ACTOR),patch.object(mv,'visibles',return_value=vacio),patch.object(p.repo,'alumnos',return_value=pd.DataFrame([{**R,'ID_Escuela':'OTRA'}])),patch.object(asignaciones,'escuelas_asignadas',return_value=[d['datos']['Escuela regular']]),patch.object(mv,'traslado_confirmado',return_value=True):
            p.autorizar(d,incluir_bajas=True)
            with self.assertRaises(PermissionError):p.autorizar(d,True,incluir_bajas=True)
        with patch.object(p,'identidad',return_value=ACTOR),patch.object(mv,'visibles',return_value=vacio),patch.object(asignaciones,'escuelas_asignadas',return_value=['Destino']):
            with self.assertRaises(PermissionError):p.autorizar(d,incluir_bajas=True)

    def test_tabla_escapa_html_y_csv_no_interpreta_formulas(self):
        from ui import tablas
        c1=Mock();c1.selectbox.return_value=25
        c2=Mock();c2.number_input.return_value=1
        with patch.object(tablas,'st') as ui:
            ui.session_state={};ui.text_input.return_value='';ui.columns.return_value=[c1,c2]
            tablas.tabla_paginada(pd.DataFrame({'Texto':['<script>no ejecutar</script>','=SUM(A1)']}),'qa')
            markup=ui.html.call_args.args[0]
            self.assertNotIn('<script>',markup);self.assertIn('&lt;script&gt;',markup)
            csv=ui.download_button.call_args.args[1].decode('utf-8-sig')
            self.assertIn("'=SUM(A1)",csv)

    def test_contraste_de_colores_principales(self):
        def luminancia(color):
            partes=[int(color[i:i+2],16)/255 for i in (0,2,4)]
            lineal=[c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4 for c in partes]
            return sum(c*w for c,w in zip(lineal,(.2126,.7152,.0722)))
        def contraste(a,b):
            x,y=sorted([luminancia(a),luminancia(b)],reverse=True)
            return (x+.05)/(y+.05)
        for fondo in ('1b4958','12333e','245a6d','9f2330','801b26'):
            self.assertGreaterEqual(contraste('ffffff',fondo),4.5)
        self.assertGreaterEqual(contraste('1e333c','f4f8fa'),4.5)


class ArchivoTests(TestCase):
    def setUp(self):
        self.rows=[];self.parts=[];self.calls=[]
        self.enter=patch.object(ar.st,'session_state',deepcopy(STATE));self.enter.start()
        self.padron=patch.object(ar,'visibles',return_value=pd.DataFrame([ALUMNO]));self.padron_mock=self.padron.start()
        self.read=patch.object(ar,'_rows',side_effect=lambda:deepcopy(self.rows));self.read.start()
        self.ensure=patch.object(ar,'ensure_sheet',side_effect=lambda n,h:Mock(row_values=lambda _:h));self.ensure.start()
        self.cache=patch.object(ar,'clear_cache');self.cache.start()
        self.retry=patch.object(ar,'retry_google',side_effect=lambda f:f());self.retry.start()
        test=self
        class Sheet:
            def __init__(self,name):self.name=name
            def append_rows(self,rows,**kw):
                test.calls.append(kw)
                if self.name==ar.PARTES:
                    start=len(test.parts)+2;test.parts.extend(rows)
                    return {'updates':{'updatedRange':f'{ar.PARTES}!A{start}:D{start+len(rows)-1}'}}
                test.rows.extend(dict(zip(ar.HEADERS,r)) for r in rows)
                return {}
            def get(self,rango):
                import re
                a,b=map(int,re.findall(r'\d+',rango));return test.parts[a-2:b-1]
        self.ws=patch.object(ar,'worksheet',side_effect=Sheet);self.ws.start()
        import pymupdf
        doc=pymupdf.open();doc.new_page();self.pdf=doc.tobytes();doc.close()

    def tearDown(self):
        for p in [self.enter,self.padron,self.read,self.ensure,self.cache,self.retry,self.ws]:p.stop()

    def test_clasificacion_manual_y_ciclo_normalizado(self):
        self.assertEqual(ar.contexto(['QA1'],'Planeación grupal','2026 – 2027')['Ambito'],'grupal')
        self.assertEqual(ar.contexto(['QA1'],'Informe médico','2026-2027')['Ambito'],'individual')
        self.assertEqual(ar.contexto(['QA1'],'Derivación','2026-2027','EPP iniciada')['Ambito'],'individual')
        with self.assertRaises(ValueError):ar.contexto(['QA1'],'Informe médico','2026-2030')
        self.assertEqual(ar.sugerir_tipo('CURP_alumno_prueba.pdf'),'CURP')
        self.assertIsNone(ar.sugerir_tipo('escaner_0001.pdf'))

    def test_guardado_verificado_raw_idempotente_y_descarga(self):
        key=ar.guardar(['QA1'],'Planeación grupal','2026 – 2027','=no-es-formula.pdf',self.pdf)
        n=len(self.parts)
        self.assertEqual(ar.guardar(['QA1'],'Planeación grupal','2026-2027','otra-etiqueta.pdf',self.pdf),key)
        self.assertEqual(len(self.parts),n);self.assertEqual(len(self.rows),1)
        self.assertTrue(all(c['value_input_option']=='RAW' for c in self.calls))
        self.assertEqual(ar.descargar(key)[1],self.pdf)

    def test_rechaza_ajenos_escuelas_mezcladas_y_grados_mezclados(self):
        with self.assertRaises(PermissionError):ar.contexto(['NO'],'EPP','2026-2027')
        self.padron_mock.return_value=pd.DataFrame([ALUMNO,{**ALUMNO,'ID_Alumno':'QA2','Grado':'3°'}])
        with self.assertRaises(ValueError):ar.contexto(['QA1','QA2'],'Planeación grupal','2026-2027')
        self.assertEqual(ar.contexto(['QA1','QA2'],'EPP','2026-2027')['Ambito'],'individual')

    def test_no_muestra_archivo_incompleto_ni_descarga_corrupta(self):
        with patch.object(ar,'_contenido',side_effect=ValueError('partes incompletas')):
            with self.assertRaises(ValueError):ar.guardar(['QA1'],'EPP','2026-2027','QA.pdf',self.pdf)
        self.assertEqual(self.rows,[])
        key=ar.guardar(['QA1'],'EPP','2026-2027','QA.pdf',self.pdf)
        self.parts[-1][3]='AAAA'
        with self.assertRaises(ValueError):ar.descargar(key)

    def test_individual_sigue_a_id_sin_revelar_colectivo_en_destino(self):
        individual=ar.guardar(['QA1'],'EPP','2026-2027','QA.pdf',self.pdf)
        ar.guardar(['QA1'],'Planeación grupal','2026-2027','grupo.pdf',self.pdf)
        self.padron_mock.return_value=pd.DataFrame([{**ALUMNO,'ID_Escuela':'DESTINO','Nombre_Escuela':'Destino'}])
        ar.st.session_state['usuario']='cuenta-destino';ar.st.session_state['nombre']='Profesional destino ficticio'
        self.assertEqual([r['ID_Documento'] for r in ar.listar()],[individual])

    def test_limites_y_binario_real_no_extension(self):
        with self.assertRaises(Exception):ar.validar_binario(b'no-soy-pdf')
        with self.assertRaises(ValueError):ar.validar_binario(b'x'*(5*1024*1024+1))
        self.assertEqual(ar.validar_binario(self.pdf),'application/pdf')


class MovimientoTests(TestCase):
    def test_todas_en_sesion_no_amplia_asignacion_de_apoyo(self):
        frame=pd.DataFrame([ALUMNO,{**ALUMNO,'ID_Alumno':'OTRO','ID_Escuela':str(ESCUELAS_USAER['Manuel Sarrado']),'Nombre_Escuela':'Manuel Sarrado'}])
        with patch.object(mv.st,'session_state',{**STATE,'escuelas_permitidas':'TODAS'}),patch.object(mv,'alumnos_visibles',return_value=frame):
            self.assertEqual(mv.visibles()['ID_Alumno'].tolist(),['QA1'])

    def test_curp_duplicada_activa_impide_movimiento_sin_reescribir(self):
        raw=pd.DataFrame([ALUMNO,{**ALUMNO,'ID_Alumno':'QA2'}])
        with patch.object(mv.st,'session_state',STATE),patch.object(mv,'visibles',return_value=pd.DataFrame([ALUMNO])),patch.object(mv.repo,'read',return_value=raw),patch.object(mv.repo,'actualizar_ubicacion_alumno') as write:
            with self.assertRaises(ValueError):mv.ejecutar('QA1','Baja recuperable','Identidad duplicada')
            write.assert_not_called()

    def test_cadena_de_traslados_confirmados_no_sigue_preparados(self):
        def fila(op,antes,despues,estado,fecha):
            return dict(ID_Movimiento=op,ID_Alumno='QA1',Accion='Trasladar',Estado=estado,Fecha=fecha,Antes_JSON=json.dumps({'ID_Escuela':antes}),Despues_JSON=json.dumps({'ID_Escuela':despues}))
        rows=[fila('uno','A','B','CONFIRMADO','1'),fila('dos','B','C','CONFIRMADO','2'),fila('tres','C','D','PREPARADO','3')]
        with patch.object(mv.repo,'read',return_value=pd.DataFrame(rows)):
            self.assertTrue(mv.traslado_confirmado('QA1','A','C'))
            self.assertFalse(mv.traslado_confirmado('QA1','A','D'))
            self.assertFalse(mv.traslado_confirmado('OTRO','A','C'))

    def test_baja_no_toca_identidad_y_reactivar(self):
        antes=deepcopy(ALUMNO)
        self.assertEqual(mv.preparar(ALUMNO,'Baja recuperable'),{'Estatus':'Baja'})
        self.assertEqual(mv.preparar(ALUMNO,'Reactivar'),{'Estatus':'Activo'})
        self.assertEqual(ALUMNO,antes)

    def test_traslado_confirmado_actualiza_solo_ubicacion_con_auditoria(self):
        destino='Manuel Sarrado';docente=mv.docentes_destino(destino)[0];log=[]
        catalogo=pd.DataFrame([{'ID_Escuela':str(ESCUELAS_USAER[destino]),'CCT':'CCT-FICTICIO'}])
        with patch.object(mv.st,'session_state',STATE),patch.object(mv,'visibles',return_value=pd.DataFrame([ALUMNO])),patch.object(mv.repo,'read',return_value=pd.DataFrame([ALUMNO])),patch.object(mv.repo,'escuelas',return_value=catalogo),patch.object(mv,'ensure_sheet',return_value=Mock(row_values=lambda _:mv.HEADERS)),patch.object(mv,'_anexar',side_effect=lambda r:log.append(deepcopy(r))),patch.object(mv.repo,'actualizar_ubicacion_alumno') as write:
            mv.ejecutar('QA1','Trasladar','Cambio de escuela de prueba',escuela=destino,docente=docente,grado='3o',grupo='b')
        self.assertEqual([r['Estado'] for r in log],['PREPARADO','CONFIRMADO'])
        aid,cambios,antes=write.call_args.args
        self.assertEqual(aid,'QA1');self.assertEqual(cambios['Grado'],'3°')
        self.assertEqual(antes['ID_Escuela'],ALUMNO['ID_Escuela'])
        self.assertFalse({'ID_Alumno','CURP','Nombre_Completo'} & set(cambios))

    def test_antecedente_individual_sigue_id_solo_si_traslado_auditado(self):
        from services import planeacion as p
        origen={'ID_Alumno':'QA1','ID_Escuela':'ORIGEN'}
        with patch.object(mv,'traslado_confirmado',return_value=True):
            self.assertTrue(p._vinculo_individual(origen,ALUMNO,[]))
            self.assertFalse(p._vinculo_individual({**origen,'ID_Alumno':'OTRO'},ALUMNO,[]))
        with patch.object(mv,'traslado_confirmado',return_value=False):
            self.assertFalse(p._vinculo_individual(origen,ALUMNO,[]))

    def test_traslado_limpia_contexto_origen_y_conserva_id(self):
        destino='Manuel Sarrado';docente=mv.docentes_destino(destino)[0]
        catalogo=pd.DataFrame([{'ID_Escuela':str(ESCUELAS_USAER[destino]),'CCT':'CCT-PRUEBA'}])
        with patch.object(mv.repo,'escuelas',return_value=catalogo):
            cambios=mv.preparar(ALUMNO,'Trasladar',destino,docente,'3o','b')
        self.assertEqual(cambios['Grado'],'3°');self.assertEqual(cambios['Grupo'],'B')
        self.assertEqual(cambios['ID_Maestro_Regular'],'');self.assertEqual(cambios['Direccion_Escuela'],'')
        self.assertNotIn('ID_Alumno',cambios);self.assertNotIn('CURP',cambios)
        with self.assertRaises(ValueError):mv.preparar(ALUMNO,'Trasladar','Escuela ajena',docente,'3°')

    def test_permiso_en_servidor_no_confia_en_selector(self):
        for rol in ('COMUNICACIÓN','PSICOLOGÍA','TRABAJO SOCIAL'):
            with self.subTest(rol=rol),patch.object(mv.st,'session_state',{**STATE,'rol':rol}),patch.object(mv.repo,'actualizar_ubicacion_alumno') as write:
                with self.assertRaises(PermissionError):mv.ejecutar('QA1','Baja recuperable','Prueba de permiso')
                write.assert_not_called()

    def test_error_de_escritura_conserva_preparado_sin_confirmar(self):
        log=[]
        with patch.object(mv.st,'session_state',STATE),patch.object(mv,'visibles',return_value=pd.DataFrame([ALUMNO])),patch.object(mv.repo,'read',return_value=pd.DataFrame()),patch.object(mv,'ensure_sheet',return_value=Mock(row_values=lambda _:mv.HEADERS)),patch.object(mv,'_anexar',side_effect=lambda r:log.append(deepcopy(r))),patch.object(mv.repo,'actualizar_ubicacion_alumno',side_effect=RuntimeError('Fallo ficticio')):
            with self.assertRaises(RuntimeError):mv.ejecutar('QA1','Baja recuperable','Fallo de prueba')
        self.assertEqual([r['Estado'] for r in log],['PREPARADO'])

    def test_reintento_confirmado_no_vuelve_a_escribir_padron(self):
        previo={'ID_Movimiento':'op','ID_Alumno':'QA1','Cuenta':'cuenta-prueba','Accion':'Baja recuperable','Estado':'CONFIRMADO'}
        with patch.object(mv.st,'session_state',STATE),patch.object(mv.repo,'read',return_value=pd.DataFrame([previo])),patch.object(mv.repo,'actualizar_ubicacion_alumno') as write:
            self.assertEqual(mv.ejecutar('QA1','Baja recuperable','Prueba de reintento',operacion='op'),'op')
            write.assert_not_called()

    def test_recupera_confirmacion_perdida_despues_del_traslado_sin_acceso_a_origen(self):
        despues={'ID_Escuela':'DESTINO','Maestra de Apoyo':'Docente destino'}
        previo={'ID_Movimiento':'op','ID_Alumno':'QA1','Cuenta':'cuenta-prueba','Accion':'Trasladar','Estado':'PREPARADO','Despues_JSON':json.dumps(despues)}
        with patch.object(mv.st,'session_state',STATE),patch.object(mv.repo,'read',return_value=pd.DataFrame([previo])),patch.object(mv.repo,'alumnos',return_value=pd.DataFrame([{**ALUMNO,**despues}])),patch.object(mv,'_anexar') as anexar,patch.object(mv.repo,'actualizar_ubicacion_alumno') as write,patch.object(mv,'visibles') as visible:
            self.assertEqual(mv.ejecutar('QA1','Trasladar','Reintento de prueba',operacion='op'),'op')
            anexar.assert_called_once();self.assertEqual(anexar.call_args.args[0]['Estado'],'CONFIRMADO')
            visible.assert_not_called();write.assert_not_called()

    def test_documento_historico_solo_lectura_tras_cadena_auditada(self):
        from services import planeacion as p
        from tests.test_planeacion_panel import documento,ACTOR
        d=documento();d['metadatos']['modalidad_planeacion']='individual'
        actual=pd.DataFrame([{**d['datos']['Alumnos'][0],'ID_Escuela':'DESTINO'}])
        with patch.object(p,'identidad',return_value=ACTOR),patch.object(p,'padron_autorizado',return_value=actual),patch.object(mv,'traslado_confirmado',return_value=True):
            p.autorizar(d)
            with self.assertRaises(PermissionError):p.autorizar(d,True)
        with patch.object(p,'identidad',return_value=ACTOR),patch.object(p,'padron_autorizado',return_value=actual),patch.object(mv,'traslado_confirmado',return_value=False):
            with self.assertRaises(PermissionError):p.autorizar(d)

    def test_repositorio_rechaza_cambio_obsoleto_y_no_permite_modificar_id(self):
        from data import repository as r
        ws=Mock();ws.row_values.side_effect=[['ID_Alumno','Estatus'],['QA1','Baja']];ws.col_values.return_value=['ID_Alumno','QA1']
        with patch.object(r,'worksheet',return_value=ws),patch.object(r,'retry_google',side_effect=lambda f:f()):
            with self.assertRaises(RuntimeError):r.actualizar_ubicacion_alumno('QA1',{'Estatus':'Activo'},{'Estatus':'Otro'})
            ws.batch_update.assert_not_called()
        with self.assertRaises(ValueError):r.actualizar_ubicacion_alumno('QA1',{'ID_Alumno':'OTRO'},{'ID_Alumno':'QA1'})

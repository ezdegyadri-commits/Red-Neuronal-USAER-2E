from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from io import BytesIO
import unittest
from unittest.mock import patch
from openpyxl import Workbook
from services import padron_importacion as motor
from data import repository as repo
from utils.escolar import separar_grado_grupo

SCHOOL={'ID_Escuela':'ESC-FICTICIA','Nombre_Escuela':'Escuela Ficticia','CCT_Escuela':'CCTFICTICIO'}
CURP='AAAA160101HYNLNNA1'
REG={'CURP':CURP,'Nombre_Completo':'Alumno ficticio','Grado':'2°','Grupo':'A','Sexo':'H','Tipo_Atencion':'Grupal',**SCHOOL}


class LibroTests(unittest.TestCase):
    def archivo(self,header,rows):
        w=Workbook();s=w.active;s.title='ALUMNOS USAER';s.append(header)
        for row in rows:s.append(row)
        out=BytesIO();w.save(out);return out.getvalue()

    def test_excel_flat_y_grupos_compuestos(self):
        for grupo in ('2°a','2A','2° A','2º A'):
            data=self.archivo(['Nombre completo','CURP','Grado','Grupo','Sexo','Tipo de atención'],[['Alumno ficticio',CURP,'2',grupo,'Hombre','Grupal']])
            read=motor.leer(data,[SCHOOL]);self.assertFalse(read['errores'])
            row=read['registros'][0];self.assertEqual((row['Grado'],row['Grupo']),('2°','A'))
            self.assertEqual(row['Sexo'],'H')

    def test_plantilla_dos_filas_usa_columna_primaria_y_grupo_final(self):
        h=['11.- APELLIDO PATERNO, MATERNO Y NOMBRE(S) COMPLETO DEL ALUMNO','12.- CURP (18 DIGITOS)','16- NIVEL Y GRADO AL QUE ESTA INSCRITO',None,'Grupo']
        data=self.archivo(h,[[None,None,'PRIMARIA','Grupo',None],['Alumno ficticio',CURP,'2o.',None,'B']])
        read=motor.leer(data,[SCHOOL]);row=read['registros'][0]
        self.assertEqual((row['Grado'],row['Grupo'],row['Nivel_Educativo']),('2°','B','Primaria'))

    def test_grado_contradictorio_y_cct_ajena_no_se_importan(self):
        with self.assertRaises(ValueError):separar_grado_grupo('3','2A')
        data=self.archivo(['Nombre completo','CURP','CCT'],[['Alumno ficticio',CURP,'OTRA-CCT']])
        read=motor.leer(data,[SCHOOL]);self.assertTrue(read['errores']);self.assertFalse(read['registros'])

    def test_vacios_y_ausentes_no_se_borran(self):
        old={**REG,'ID_Alumno':'ALU-001','Fecha_Derivacion':'2026-09-01'}
        other={**REG,'CURP':'BBBB160101HYNLNNA2','ID_Alumno':'ALU-002'}
        plan=motor.comparar([{**REG,'Grupo':''}],[old,other],[SCHOOL])
        self.assertNotIn('Grupo',plan['filas'][0]['cambios'])
        self.assertEqual(len(plan['filas']),1)
        self.assertEqual(old['Fecha_Derivacion'],'2026-09-01')

    def test_duplicados_y_traslado_se_detienen(self):
        self.assertTrue(motor.comparar([REG,REG],[],[SCHOOL])['conflictos'])
        other={**REG,'ID_Alumno':'ALU-001','ID_Escuela':'OTRA'}
        self.assertTrue(motor.comparar([REG],[other],[SCHOOL])['conflictos'])


class Memoria:
    def __init__(self):
        self.headers=repo.BASE_HEADERS['Alumnos'];self.rows=[self.headers.copy()];self.calls=[];self.history=[];self.fallar=False
    def sheet(self,name):
        data=self
        class Sheet:
            id=1 if name=='Alumnos' else 2
            spreadsheet=data
            def get_all_values(self):return deepcopy(data.rows)
        return Sheet()
    def batch_update(self,body):
        self.calls.append(body)
        for r in body['requests']:
            if 'appendCells' in r:
                a=r['appendCells'];dest=self.rows if a['sheetId']==1 else self.history
                dest.extend([[v['userEnteredValue']['stringValue'] for v in row['values']] for row in a['rows']])
            if 'updateCells' in r:
                a=r['updateCells'];s=a['start'];self.rows[s['rowIndex']][s['columnIndex']]=a['rows'][0]['values'][0]['userEnteredValue']['stringValue']
        if self.fallar:self.fallar=False;raise TimeoutError('Acuse perdido ficticio')


class ConfirmacionUITests(unittest.TestCase):
    def comprobar(self,error=False):
        from concurrent.futures import Future
        from ui import padron_importacion as ui
        future=Future()
        if error:future.set_exception(TimeoutError('Fallo ficticio'))
        else:future.set_result({'altas':1,'actualizados':2})
        state={'nombre':'Docente ficticio','rol':'Apoyo','qa_trabajo':future}
        estado=getattr(ui._estado,'__wrapped__',ui._estado)
        with patch.object(ui.st,'session_state',state),patch.object(ui.st,'success') as success,patch.object(ui.st,'warning') as warning:
            estado('qa','Docente ficticio','Apoyo')
            self.assertNotIn('qa_trabajo',state)
            success.reset_mock();warning.reset_mock()
            estado('qa','Docente ficticio','Apoyo')
            self.assertTrue(warning.called if error else success.called)
        return state
    def test_confirmacion_permanece_al_volver_a_la_pantalla(self):
        self.assertEqual(self.comprobar()['qa_resultado']['actualizados'],2)
    def test_error_permanece_sin_descartar_vista_previa(self):
        self.assertIn('vista previa se conservan',self.comprobar(True)['qa_error'])


class PersistenciaTests(unittest.TestCase):
    def setUp(self):
        self.db=Memoria();self.ps=[patch.object(repo,'worksheet',side_effect=self.db.sheet),patch.object(repo,'retry_google',side_effect=lambda f:f()),patch.object(repo,'clear_cache'),patch.object(repo,'clear_alumnos_cache'),patch('services.asignaciones.puede_dar_alta_alumnos',return_value=True),patch('services.asignaciones.escuelas_asignadas',return_value=['Escuela Ficticia'])]
        for p in self.ps:p.start()
    def tearDown(self):
        for p in reversed(self.ps):p.stop()
    def confirmar(self,plan):return motor.confirmar(plan,[SCHOOL],'Docente ficticio','Apoyo','ficticio.xlsx')
    def test_quince_reintentos_concurrentes_generan_una_alta_y_un_historial(self):
        plan=motor.comparar([REG],[],[SCHOOL])
        with ThreadPoolExecutor(max_workers=15) as pool:results=list(pool.map(lambda _:self.confirmar(plan),range(15)))
        self.assertEqual(sum(r['altas'] for r in results),1)
        self.assertEqual(len(self.db.rows),2);self.assertEqual(len(self.db.history),1)
        self.assertEqual(len(self.db.calls),1)
    def test_acuse_perdido_no_duplica(self):
        plan=motor.comparar([REG],[],[SCHOOL]);self.db.fallar=True
        with self.assertRaises(TimeoutError):self.confirmar(plan)
        self.assertEqual(self.confirmar(plan),{'altas':0,'actualizados':0})
        self.assertEqual(len(self.db.rows),2)
    def test_cambio_posterior_requiere_nueva_revision(self):
        plan=motor.comparar([REG],[],[SCHOOL]);self.confirmar(plan)
        headers=self.db.headers;old=dict(zip(headers,self.db.rows[1]));plan=motor.comparar([{**REG,'Grupo':'B'}],[old],[SCHOOL])
        self.db.rows[1][headers.index('Grupo')]='C'
        with self.assertRaises(ValueError):self.confirmar(plan)
        self.assertEqual(self.db.rows[1][headers.index('Grupo')],'C')
    def test_copia_conservada_no_recibe_cambios_del_registro_activo(self):
        self.confirmar(motor.comparar([REG],[],[SCHOOL]));headers=self.db.headers
        duplicado=self.db.rows[1].copy();duplicado[headers.index('ID_Alumno')]='ALU-099';duplicado[headers.index('Estatus')]='Duplicado - conservado'
        self.db.rows.append(duplicado);antes=duplicado.copy()
        actuales=[dict(zip(headers,r)) for r in self.db.rows[1:]]
        self.confirmar(motor.comparar([{**REG,'Grupo':'B'}],actuales,[SCHOOL]))
        self.assertEqual(self.db.rows[1][headers.index('Grupo')],'B');self.assertEqual(self.db.rows[2],antes)

"""No confundir a docentes por apellidos. Datos de alumnos exclusivamente ficticios."""
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch
import pandas as pd
from services import alumnos,expedientes,padron_movimientos as movimientos,planeacion

NOMBRE='Mtra. Dianely de Sugeidy Caamal Tamay'


def padron_ficticio():
    rows=[{'ID_Alumno':f'QA-{i:03d}','Nombre_Completo':f'Alumno ficticio {i:03d}',
        'CURP':f'NO-OFICIAL-{i}','ID_Escuela':'ESC-004','Nombre_Escuela':'Remigio Aguilar Sosa',
        'Maestra de Apoyo':'' if i<39 else NOMBRE,'Estatus':'Activo','Grado':'3°','Grupo':'A',
        'Tipo_Atencion':'Grupal','Edad_1_Septiembre':8,'Sexo':'H','Condicion_Discapacidad':'Dato ficticio'} for i in range(50)]
    rows.append({**rows[0],'ID_Alumno':'QA-OTRA','CURP':'NO-OFICIAL-OTRA','Nombre_Completo':'Alumno ficticio de otra escuela',
                 'ID_Escuela':'ESC-002','Nombre_Escuela':'Ichcaanziho','Maestra de Apoyo':'Marycruz Caamal Coral'})
    return pd.DataFrame(rows)


class RemigioTests(TestCase):
    def test_apellido_caamal_no_convierte_dianely_en_marycruz(self):
        self.assertEqual(alumnos._canonizar_docente_apoyo(NOMBRE),'DIANELY DE SUGEIDY CAAMAL TAMAY')
        for otro in ('Otra Cecilia Pérez','Otra maestra Caamal','Caamal','Cecilia'):
            self.assertNotIn(alumnos._canonizar_docente_apoyo(otro),alumnos.DOCENTES_ICHC_AANZIHO)

    def test_conserva_alias_conocidos_sin_coincidencias_parciales(self):
        for v in ('Cecilia Solís','Mtra. María Cecilia Solís','Cecilia Solís Vázquez','María Cecilia Solís Vázquez'):
            self.assertEqual(alumnos._canonizar_docente_apoyo(v),'MARIA CECILIA SOLIS VAZQUEZ')
        for v in ('Marycruz Caamal','Mtra. Marycruz Caamal Coral'):
            self.assertEqual(alumnos._canonizar_docente_apoyo(v),'MARYCRUZ CAAMAL CORAL')

    def test_cuenta_apoyo_recupera_historia_y_altas_sin_mostrar_otra_escuela(self):
        original=padron_ficticio();before=original.copy(deep=True)
        with patch.object(expedientes.repo,'read',return_value=original):
            result=expedientes.alumnos_visibles('APOYO','Remigio Aguilar Sosa',NOMBRE)
        self.assertEqual(len(result),50)
        self.assertIn('QA-000',result['ID_Alumno'].tolist());self.assertIn('QA-049',result['ID_Alumno'].tolist())
        self.assertNotIn('QA-OTRA',result['ID_Alumno'].tolist())
        pd.testing.assert_frame_equal(original,before)

    def test_filtro_de_movimientos_no_vuelve_a_ocultar_alumnos(self):
        state={'autenticado':True,'usuario':'qa','rol':'APOYO','nombre':NOMBRE,'escuelas_permitidas':'Remigio Aguilar Sosa'}
        with patch.object(movimientos.st,'session_state',state),patch.object(expedientes.repo,'read',return_value=padron_ficticio()):
            result=movimientos.visibles()
        self.assertEqual(len(result),50);self.assertTrue(result['ID_Escuela'].eq('ESC-004').all())

    def test_planeacion_no_reutiliza_cache_antigua_de_once_alumnos(self):
        original=padron_ficticio();parcial=original.iloc[39:50].copy()
        actor={'cuenta':'qa','nombre':NOMBRE,'rol':'APOYO','area':'Aprendizaje','perfil':None,'director':False}
        state={'autenticado':True,'escuelas_permitidas':'Remigio Aguilar Sosa',
               '_padron_autorizado_grados_v2_qa_Remigio Aguilar Sosa':parcial}
        with patch.object(planeacion,'identidad',return_value=actor),patch.object(planeacion.st,'session_state',state),patch.object(expedientes.repo,'read',return_value=original):
            actual=planeacion.padron_autorizado()
        self.assertEqual(len(actual),50)
        self.assertEqual(len(state['_padron_autorizado_grados_v2_qa_Remigio Aguilar Sosa']),11)

    def test_interfaz_estadistica_muestra_total_completo(self):
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_file(str(Path(__file__).parent/'fixtures/estadistica_remigio_app.py'),default_timeout=30).run()
        self.assertFalse(app.exception)
        self.assertEqual(next(m.value for m in app.metric if m.label=='Alumnos'),'50')
        self.assertTrue(any('50 resultados' in c.value for c in app.caption))
        next(r for r in app.radio if r.label=='¿Qué deseas consultar?').set_value('Estadísticas').run()
        self.assertFalse(app.exception)
        self.assertEqual(next(m.value for m in app.metric if m.label=='Alumnos'),'50')

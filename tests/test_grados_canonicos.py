"""Misma clave de grado en padrón y planeación; sin datos reales ni migraciones."""
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch,MagicMock
import pandas as pd
from data import repository as repo
from services import planeacion_viva as viva,planeacion as s
from services.planeacion_grupo_unico import clave
from utils.escolar import grado_canonico
from tests.test_planeacion_compartida import grupal


class GradosTests(TestCase):
    from tests.test_planeacion_simple import RecorridoTests
    setUp=RecorridoTests.setUp
    tearDown=RecorridoTests.tearDown

    def test_variantes_de_los_seis_grados_e_idempotencia(self):
        nombres=['primero','segundo','tercero','cuarto','quinto','sexto']
        for n,nombre in enumerate(nombres,1):
            for v in (n,float(n),f'{n}',f'{n}°',f'{n}º',f'{n}o.',f'{n}.',f'0{n}',f'{n}.0',nombre,f'{nombre} grado',f'{n}° de primaria',f'grado {n}'):
                with self.subTest(v=v):
                    self.assertEqual(grado_canonico(v),f'{n}°')
                    self.assertEqual(grado_canonico(grado_canonico(v)),f'{n}°')
        for v in ('1er','1ero','1ro','primer grado'):self.assertEqual(grado_canonico(v),'1°')

    def test_no_deduce_grados_de_datos_ambiguos_ni_grupos(self):
        for v in ('1 y 2','2026-2027','1A','7','13','Primaria','Pendiente'):
            self.assertEqual(grado_canonico(v),v)
        for v in (None,float('nan'),''):self.assertEqual(grado_canonico(v),'')

    def test_padron_operativo_normaliza_sin_mutar_hoja_ni_modalidad(self):
        original=pd.DataFrame([{'ID_Alumno':str(n),'Nombre_Completo':f'Ficticio {n}','CURP':f'FICTICIO{n}','Grado':f'{n}o.','Grupo':'','Tipo_Atencion':'Individual'} for n in range(1,7)])
        before=original.copy(deep=True)
        with patch.object(repo,'read',return_value=original),patch.object(repo,'worksheet') as sheet:
            result=repo.alumnos();sheet.assert_not_called()
        self.assertEqual(result['Grado'].tolist(),[f'{n}°' for n in range(1,7)])
        self.assertEqual(result['Tipo_Atencion'].tolist(),['Individual']*6)
        pd.testing.assert_frame_equal(original,before)

    def test_filtro_equivalente_sin_ampliar_escuela_ni_cambiar_atencion(self):
        original=pd.DataFrame([{'ID_Alumno':'I','ID_Escuela':'E1','Grado':'1ero','Grupo':'a','Tipo_Atencion':'Individual'},
            {'ID_Alumno':'G','ID_Escuela':'E1','Grado':'2o.','Grupo':'A','Tipo_Atencion':'Grupal'},
            {'ID_Alumno':'X','ID_Escuela':'E2','Grado':'1°','Grupo':'A','Tipo_Atencion':'Grupal'}])
        before=original.copy(deep=True)
        self.assertTrue(viva.opciones_padron(original,'E1','grupal','1°','A').empty)
        result=viva.opciones_padron(original,'E1','grupal','primero','a',incluir=True)
        self.assertEqual(result['ID_Alumno'].tolist(),['I'])
        self.assertEqual(result['Grado'].tolist(),['1°'])
        self.assertEqual(result['Tipo_Atencion'].tolist(),['Individual'])
        pd.testing.assert_frame_equal(original,before)

    def test_edicion_nueva_guarda_grado_canonico_solo_en_celda_solicitada(self):
        sheet=MagicMock();sheet.row_values.return_value=['ID_Alumno','Grado'];sheet.col_values.return_value=['ID_Alumno','A1']
        with patch.object(repo,'worksheet',return_value=sheet),patch.object(repo,'retry_google',side_effect=lambda f:f()),patch.object(repo,'clear_cache'):
            repo.update_alumno('A1',{'Grado':'primer grado'},{'A1'})
        self.assertEqual(sheet.batch_update.call_args.args[0],[{'range':'B2','values':[['1°']]}])

    def test_variantes_no_crean_otro_documento_grupal(self):
        d=grupal();d['datos']['Alumnos'][0]['Grado']='1°';base=clave(d)
        for v in ('1ero','1o.','primer grado','1º'):
            d['datos']['Alumnos'][0]['Grado']=v
            self.assertEqual(clave(d),base)

    def test_primer_grado_individual_aparece_por_defecto_en_entrada_grupal(self):
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_file(str(Path(__file__).with_name('fixture_planeacion_papel.py')),default_timeout=30).run()
        self.assertFalse(app.exception)
        grado=next(w for w in app.selectbox if w.label=='Grado')
        self.assertIn('1°',grado.options)
        grado.set_value('1°').run()
        self.assertFalse(app.exception)
        self.assertIn('Alumno ficticio Individual',next(w for w in app.multiselect if w.label=='Alumnos de mi formato').options)

    def test_padron_cacheado_tambien_se_normaliza_sin_cambiar_entrada(self):
        from tests.test_planeacion_panel import ACTOR
        original=pd.DataFrame([{'ID_Alumno':'A1','ID_Escuela':'E1','Grado':'1ero','Grupo':'a'}])
        before=original.copy(deep=True)
        estado={'_padron_autorizado_identidad_v3_prueba_':original}
        with patch.object(s,'identidad',return_value=ACTOR),patch.object(s.st,'session_state',estado),patch.object(s,'alumnos_visibles') as leer:
            result=s.padron_autorizado();leer.assert_not_called()
        self.assertEqual(result['Grado'].tolist(),['1°']);pd.testing.assert_frame_equal(original,before)

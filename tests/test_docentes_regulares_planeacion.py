"""Asignación, correcciones y precarga: sólo registros ficticios y repositorio simulado."""
from copy import deepcopy
from pathlib import Path
import tempfile
from unittest import TestCase
from unittest.mock import patch
import pandas as pd
from streamlit.testing.v1 import AppTest
from services import docentes_regulares as catalogo
from services.planeacion_docentes import aplicar
from tests.test_planeacion_todos_grupos import documento


ACTOR={'autenticado':True,'cuenta':'cuenta-apoyo','nombre':'Mtra. Cindy Mayanín Burgos González','rol':'APOYO','escuelas_permitidas':'Todas'}


def registro(nombre='Docente simulado',grupo='A',**kw):
    return {'ID_Registro':'DOC-A','Fecha_Registro':'2026-10-01T08:00:00-06:00',
            'Ciclo_Escolar':'2026 – 2027','ID_Escuela':'ESC-001','Nombre_Escuela':'Damián Carmona',
            'Turno':'Matutino','Grado':'1o.','Grupo':grupo,'Nombre_Docente':nombre,
            'Telefono':'dato conservado','Email':'','Observaciones':'Nota original',**kw}


class CatalogoTests(TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.rows=[registro()]
        self.patches=[patch.object(catalogo,'_LOCAL_BACKUP_PATH',str(Path(self.tmp.name)/'directorio.json')),
            patch('data.google.df_sheet',side_effect=lambda name:pd.DataFrame(deepcopy(self.rows))),
            patch('data.google.ensure_headers'),patch('data.google.clear_cache'),
            patch('data.google.append_dict',side_effect=lambda name,row:self.rows.append(deepcopy(row)))]
        for p in self.patches:p.start()
    def tearDown(self):
        for p in reversed(self.patches):p.stop()
        self.tmp.cleanup()

    def test_apoyo_solo_su_escuela_incluso_con_todas_en_sesion(self):
        self.assertEqual(catalogo.escuelas_del_actor(ACTOR),['Damián Carmona'])
        with self.assertRaises(PermissionError):
            catalogo.guardar_docente_asignado(ACTOR,'Manuel Sarrado',grado='1°',grupo='A',nombre_docente='Nombre')
        with self.assertRaises(PermissionError):catalogo.escuelas_del_actor({**ACTOR,'autenticado':False})
        with self.assertRaises(PermissionError):catalogo.escuelas_del_actor({**ACTOR,'rol':'Comunicación'})
        self.assertEqual(len(catalogo.escuelas_del_actor({**ACTOR,'rol':'DIRECTOR'})),7)

    def test_corregir_nombre_y_grupo_append_sin_borrar_historia(self):
        antes=deepcopy(self.rows[0])
        actualizado=catalogo.editar_docente_regular('DOC-A',{'Nombre_Docente':'Nombre corregido','Grado':'1ero','Grupo':'b'},ACTOR)
        self.assertTrue(actualizado['_guardado_central'])
        self.assertEqual(len(self.rows),2);self.assertEqual(self.rows[0],antes)
        self.assertEqual(actualizado['ID_Registro'],'DOC-A');self.assertEqual(actualizado['Actualizado_Por'],ACTOR['cuenta'])
        vigente=catalogo.listar_docentes_regulares('ESC-001')
        self.assertEqual(len(vigente),1)
        self.assertEqual(vigente[0]['Grupo'],'B');self.assertEqual(vigente[0]['Nombre_Docente'],'Nombre corregido')
        self.assertEqual(vigente[0]['Telefono'],'dato conservado')
        self.assertEqual(vigente[0]['Observaciones'],'Nota original')

    def test_cada_maestra_solo_su_primaria_incluyendo_marycruz_y_cecilia(self):
        from services.asignaciones import ASIGNACIONES_ESPECIALISTAS
        nombres=['CINDY MAYANIN BURGOS GONZALEZ','MARYCRUZ CAAMAL CORAL','MARIA CECILIA SOLIS VAZQUEZ',
                 'DOLORES EUGENIA CORTAZAR NAVARRETE','DIANELY DE SUGEIDY CAAMAL TAMAY',
                 'LUIS JORGE GARCIA HERRERA','MARIA DEL ROSARIO PEREZ VITORIN','ZUEMMY DEL CARMEN PEREZ BASTO']
        for nombre in nombres:
            with self.subTest(maestra=nombre):
                self.assertEqual(catalogo.escuelas_del_actor({**ACTOR,'nombre':nombre}),ASIGNACIONES_ESPECIALISTAS[nombre])

    def test_correccion_no_oculta_otro_maestro_del_mismo_grupo(self):
        self.rows.append(registro('Docente B',grupo='B',ID_Registro='DOC-B'))
        with self.assertRaisesRegex(ValueError,'otro maestro'):catalogo.editar_docente_regular('DOC-A',{'Grupo':'B'},ACTOR)
        self.assertEqual(len(self.rows),2)

    def test_local_antiguo_no_oculta_correccion_central_y_separacion_ciclos(self):
        catalogo._guardar_local(registro())
        self.rows.append(registro('Corrección central',Fecha_Registro='2026-10-22T08:00:00-06:00'))
        self.rows.append(registro('Ciclo anterior',ID_Registro='DOC-ANTERIOR',Ciclo_Escolar='2025-2026'))
        actual=catalogo.listar_docentes_regulares('Damián Carmona')
        self.assertEqual(len(actual),2)
        self.assertEqual(next(r for r in actual if r['Ciclo_Escolar']=='2026-2027')['Nombre_Docente'],'Corrección central')

    def test_escuela_ciclo_id_no_editables_y_docentes_ajenos_denegados(self):
        for cambios in [{'ID_Escuela':'ESC-006'},{'Nombre_Escuela':'Manuel Sarrado'},{'Ciclo_Escolar':'2027-2028'},{'ID_Registro':'OTRO'}]:
            with self.assertRaises(ValueError):catalogo.editar_docente_regular('DOC-A',cambios,ACTOR)
        self.rows.append(registro(ID_Registro='DOC-AJENO',ID_Escuela='ESC-006',Nombre_Escuela='Manuel Sarrado'))
        with self.assertRaises(PermissionError):catalogo.editar_docente_regular('DOC-AJENO',{'Nombre_Docente':'Otro'},ACTOR)
        self.assertEqual(len(self.rows),2)

    def test_fallo_central_no_informa_guardado_y_conserva_contingencia(self):
        with patch('data.google.append_dict',side_effect=RuntimeError('sin conexión')):
            result=catalogo.editar_docente_regular('DOC-A',{'Nombre_Docente':'Corrección pendiente'},ACTOR)
        self.assertFalse(result['_guardado_central'])
        self.assertEqual(catalogo._leer_local()[0]['Nombre_Docente'],'Corrección pendiente')
        self.assertEqual(len(self.rows),1)


class PrecargaTests(TestCase):
    def doc(self,ids=('A1',),todos=False):
        d=documento(ids,todos=todos);d['datos']['ID_Escuela']='ESC-001'
        return d

    def test_precarga_antigua_completa_mas_abreviatura_usa_catalogo_exacto(self):
        d=self.doc(('A1','B1'),todos=True)
        for a,n in zip(d['datos']['Alumnos'],['Ana Beatriz Pérez López','Beatriz']):
            a.update(Grupo='A',ID_Maestro_Regular=n)
        d['metadatos']['guia_grupal_manual']={'maestro_grupo':'Ana Beatriz Pérez López, Beatriz','filas':[]}
        antes=deepcopy(d)
        nuevo=aplicar(d,[registro('Ana Beatriz Pérez López')])
        self.assertEqual(nuevo['metadatos']['guia_grupal_manual']['maestro_grupo'],'Ana Beatriz Pérez López')
        self.assertEqual(d,antes)
        d['metadatos']['maestro_regular_edicion_manual']=True
        self.assertEqual(aplicar(d,[registro('Ana Beatriz Pérez López')])['metadatos']['guia_grupal_manual']['maestro_grupo'],antes['metadatos']['guia_grupal_manual']['maestro_grupo'])

    def test_sin_catalogo_no_equipara_personas_por_nombre_parcial(self):
        d=self.doc();d['metadatos']['guia_grupal_manual']={'maestro_grupo':'Ana, Ana López'}
        self.assertEqual(aplicar(d,[]),d)

    def test_match_escuela_ciclo_grado_grupo_y_turno_sin_sobrescribir_doc(self):
        d=self.doc();antes=deepcopy(d)
        regs=[registro(),registro('Otra escuela',ID_Escuela='ESC-006'),registro('Otro ciclo',Ciclo_Escolar='2025-2026'),
              registro('Otro grado',Grado='2°'),registro('Otra sección',grupo='B'),registro('Otro turno',Turno='Vespertino')]
        nuevo=aplicar(d,regs)
        self.assertEqual(nuevo['metadatos']['guia_grupal_manual']['maestro_grupo'],'Docente simulado')
        self.assertEqual(d,antes)

    def test_todos_muestra_docentes_de_a_y_b_y_actualiza_correccion_no_manual(self):
        d=self.doc(('A1','B1'),todos=True)
        nuevo=aplicar(d,[registro('Docente A'),registro('Docente B',grupo='B',ID_Registro='DOC-B')])
        texto=nuevo['metadatos']['guia_grupal_manual']['maestro_grupo']
        self.assertIn('1° A · Docente A',texto);self.assertIn('1° B · Docente B',texto)
        corregido=aplicar(nuevo,[registro('Docente A corregido'),registro('Docente B',grupo='B')])
        self.assertIn('Docente A corregido',corregido['metadatos']['guia_grupal_manual']['maestro_grupo'])

    def test_respeta_nombre_escrito_por_maestra_y_no_adivina_grupo_sin_letra(self):
        d=self.doc();d['metadatos']['guia_grupal_manual']={'maestro_grupo':'Redacción manual'}
        nuevo=aplicar(d,[registro()])
        self.assertEqual(nuevo['metadatos']['guia_grupal_manual']['maestro_grupo'],'Redacción manual')
        self.assertEqual(nuevo['metadatos']['docentes_regulares_sugeridos'],'Docente simulado')
        sinletra=self.doc(('S1',))
        self.assertEqual(aplicar(sinletra,[registro(),registro('Docente B',grupo='B')]),sinletra)
        self.assertEqual(aplicar(sinletra,[registro()])['metadatos']['guia_grupal_manual']['maestro_grupo'],'Docente simulado')


class FormularioAsignadoTests(TestCase):
    def test_solo_escuela_asignada_y_edicion_disponible(self):
        from ui import docentes_regulares_form as ui
        codigo="""
import streamlit as st
st.session_state.update(autenticado=True,usuario='cuenta-apoyo',nombre='Mtra. Cindy Mayanín Burgos González',rol='APOYO',escuelas_permitidas='Todas')
from ui.docentes_regulares_form import formulario_publico_docentes
formulario_publico_docentes()
"""
        with patch.object(ui,'listar_docentes_regulares',return_value=[registro(Grado='1°')]):
            app=AppTest.from_string(codigo,default_timeout=30).run()
        self.assertFalse(app.exception)
        self.assertFalse(any(s.label=='Escuela Primaria' for s in app.selectbox))
        self.assertTrue(any('Damián Carmona' in i.value for i in app.info))
        self.assertTrue(any(b.label=='Guardar corrección' for b in app.button))
        self.assertFalse(any('Manuel Sarrado' in str(w.value) for w in app.info))

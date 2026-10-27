"""Reproduce el grupo B, dos copias y el alta explícita sin datos reales."""
from copy import deepcopy
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch
import pandas as pd
from streamlit.testing.v1 import AppTest
from services import planeacion as s, planeacion_alumnos as alumnos, planeacion_grupo_unico as unico
from services.planeacion_compartida import alumno_padron, ampliar_matricula
from services.planeacion_modalidad import guia_grupal
from services.planeacion_recuperacion import titulo_tarjeta
from tests.test_planeacion_compartida import grupal
from tests.test_planeacion_panel import ALUMNO, ACTOR, PanelTests


def padron():
    return pd.DataFrame([
        {**ALUMNO,'ID_Alumno':'A1','Nombre_Completo':'Alumno grupal B','Grado':'5°','Grupo':'B','Tipo_Atencion':'Grupal','Estatus':'Activo'},
        {**ALUMNO,'ID_Alumno':'A2','Nombre_Completo':'Alumno sin grupo','Grado':'5o.','Grupo':'','Tipo_Atencion':'Grupal','Estatus':'Activo'},
        {**ALUMNO,'ID_Alumno':'I1','Nombre_Completo':'Alumno individual B','Grado':'5°','Grupo':'B','Tipo_Atencion':'Individual','Estatus':'Activo'},
        {**ALUMNO,'ID_Alumno':'OTRA','Nombre_Completo':'Alumno de otro grupo','Grado':'5°','Grupo':'A','Tipo_Atencion':'Grupal','Estatus':'Activo'}])


def raiz():
    d=grupal();d.update(id='raiz-b',revision='revision-raiz',guardado_en='2026-10-01T10:00:00')
    d['datos']['Alumnos']=[alumno_padron(padron().iloc[0].to_dict())]
    d['metadatos']['guia_grupal_manual']={'filas':[{'ID_Alumno':'A1','Aprendizaje':'Actividad original de apoyo','Comunicación':'Aporte previo de comunicación'}]}
    return d


class IncorporacionTests(TestCase):
    def setUp(self):
        self.auth=patch.object(s,'autorizar',return_value=ACTOR);self.auth.start();self.addCleanup(self.auth.stop)

    def test_sin_grupo_se_anade_a_misma_hoja_sin_cambiar_padron(self):
        d=raiz();frame=padron();antes=frame.copy(deep=True)
        n=alumnos.incorporar(d,['A2'],frame)
        self.assertEqual(n['id'],d['id']);self.assertEqual(n['revision'],d['revision'])
        self.assertEqual(unico.clave(n),unico.clave(d))
        self.assertEqual([r['ID_Alumno'] for r in guia_grupal(n)['filas']],['A1','A2'])
        self.assertEqual(guia_grupal(n)['filas'][0]['Comunicación'],'Aporte previo de comunicación')
        pd.testing.assert_frame_equal(frame,antes)

    def test_individual_necesita_confirmacion_y_excepcion_no_se_hereda(self):
        d=raiz();frame=padron()
        with self.assertRaises(PermissionError):alumnos.incorporar(d,['I1'],frame)
        n=alumnos.incorporar(d,['I1'],frame,autorizar_individuales=True)
        alumnos.validar_incorporaciones(n,frame)
        self.assertIn('I1',[r['ID_Alumno'] for r in guia_grupal(ampliar_matricula(n,frame))['filas']])
        self.assertEqual(next(a for a in n['datos']['Alumnos'] if a['ID_Alumno']=='I1')['Tipo_Atencion'],'Individual')
        otra=deepcopy(n);otra['id']='otro-documento'
        self.assertNotIn('I1',[r['ID_Alumno'] for r in guia_grupal(ampliar_matricula(otra,frame))['filas']])
        with self.assertRaises(PermissionError):alumnos.validar_incorporaciones(otra,frame)

    def test_otro_grupo_o_escuela_y_baja_no_se_incorporan(self):
        d=raiz();frame=padron()
        for aid in ('OTRA','FUERA'):
            with self.assertRaises(PermissionError):alumnos.incorporar(d,[aid],frame)
        for campo,valor in [('Estatus','Baja'),('ID_Escuela','E2'),('Grado','4°')]:
            mod=frame.copy();mod.loc[mod.ID_Alumno.eq('A2'),campo]=valor
            with self.assertRaises(PermissionError):alumnos.incorporar(d,['A2'],mod)

    def test_grupal_de_un_alumno_se_identifica_por_grado_y_grupo(self):
        self.assertEqual(titulo_tarjeta(raiz()),'5° B')

    def test_mismo_periodo_no_crea_copia_adaptada_para_anadir(self):
        from services.planeacion_edicion import copiar
        d=raiz()
        with patch.object(s,'padron_autorizado',return_value=padron()),patch.object(s,'nueva') as nueva:
            with self.assertRaisesRegex(ValueError,'Añadir alumno'):
                copiar(d,['A1','A2'],2026,1,grupal=True)
            nueva.assert_not_called()


def copias():
    r=raiz();result=[r]
    for i in (1,2):
        d=deepcopy(r);d.update(id='copia-'+str(i),revision='rev-'+str(i),guardado_en=f'2026-10-0{i+1}T10:00:00')
        d['metadatos']['vista_formato']='trimestral'
        d['metadatos']['copia_de']={'documento':r['id'],'revision':r['revision']}
        d['datos']['Alumnos'].append(alumno_padron(padron().iloc[1].to_dict()))
        d['tablas']['dosificacion'].append({'Contextos':'Aula regular','Actividades':'Actividad conservada de copia '+str(i),'Temporalidad':'','Recursos':''})
        result.append(d)
    return result


class CopiasTests(TestCase):
    def test_planeacion_individual_existente_no_se_absorbe(self):
        entrada=copias();individual=deepcopy(entrada[0])
        individual.update(id='individual-intacto',revision='individual-rev')
        individual['metadatos']['modalidad_planeacion']='individual'
        individual['metadatos']['vista_formato']='trimestral'
        individual['datos']['Alumnos']=[alumno_padron(padron().iloc[2].to_dict())]
        individual['tablas']['dosificacion']=[{'Actividades':'Actividad individual que se conserva'}]
        antes=deepcopy(individual)
        salida=unico.documentos([*entrada,individual])
        self.assertEqual(len(salida),2)
        self.assertEqual(next(d for d in salida if d['id']==individual['id']),antes)

    def test_dos_copias_del_mismo_grupo_se_reintegran_sin_perder_texto(self):
        entrada=copias();antes=deepcopy(entrada);docs=unico.documentos(entrada)
        self.assertEqual(len(docs),1);d=docs[0]
        self.assertEqual(d['id'],'raiz-b');self.assertEqual(unico.clave(d),unico.clave(entrada[0]))
        self.assertEqual(len(d['datos']['Alumnos']),2)
        self.assertIn('copia-1',d['metadatos']['unificacion_grupal']['fuentes'])
        self.assertIn('copia-2',d['metadatos']['unificacion_grupal']['fuentes'])
        self.assertTrue(all(any('copia '+str(i) in r.get('Actividades','') for r in d['tablas']['dosificacion']) for i in (1,2)))
        self.assertEqual(entrada,antes)
        d.update(revision='consolidada',guardado_en='2026-10-20T10:00:00')
        self.assertEqual(len(unico.documentos([*entrada,d])),1)

    def test_subgrupo_independiente_otro_periodo_o_autor_no_se_absorben(self):
        r,c,_=copias()
        for cambiar in ('independiente','periodo','autor','grupo'):
            otro=deepcopy(c)
            if cambiar=='independiente':otro['metadatos'].pop('copia_de')
            elif cambiar=='periodo':otro['datos']['Trimestre']=2
            elif cambiar=='autor':otro['cuenta']='otra-cuenta'
            else:otro['datos']['Alumnos'][0]['Grupo']='A'
            self.assertEqual(len(unico.documentos([r,otro])),2,cambiar)


class GuardadoTests(TestCase):
    setUp=PanelTests.setUp
    tearDown=PanelTests.tearDown

    def test_guardar_y_reabrir_preserva_alumno_sin_grupo_e_individual_confirmado(self):
        frame=padron();d=raiz();d['revision']=''
        with patch.object(s,'padron_autorizado',return_value=frame):
            saved=s.guardar(d)
            n=alumnos.incorporar(saved,['A2','I1'],frame,autorizar_individuales=True)
            saved=s.guardar(n)
            abierta=s.listar()[0]
        self.assertEqual(abierta['id'],d['id'])
        self.assertEqual({r['ID_Alumno'] for r in guia_grupal(abierta)['filas']},{'A1','A2','I1'})
        self.assertEqual(len({v['id'] for v in s.reconstruir(self.sheet.rows)}),1)


    def test_guardar_raiz_abierta_reune_copias_y_preserva_redaccion_local(self):
        frame=padron();d=raiz();d['revision']=''
        with patch.object(s,'padron_autorizado',return_value=frame):
            original=s.guardar(d)
            for copia in copias()[1:]:
                copia['revision']='';copia['metadatos']['copia_de']['documento']=original['id']
                s.guardar(copia)
            local=deepcopy(original);local['textos']['Evaluación']='Texto escrito mientras se creaban copias'
            saved=s.guardar(local)
            abiertas=[x for x in s.listar() if x['metadatos'].get('modalidad_planeacion')=='grupal']
        self.assertEqual(len(abiertas),1);self.assertEqual(saved['id'],original['id'])
        self.assertIn('Texto escrito mientras',saved['textos']['Evaluación'])
        self.assertTrue(all(any('copia '+str(i) in r.get('Actividades','') for r in saved['tablas']['dosificacion']) for i in (1,2)))
        self.assertEqual(len(s.reconstruir(self.sheet.rows)),4)


class InterfazTests(TestCase):
    def test_selector_y_confirmacion_actualizan_la_misma_hoja(self):
        app=AppTest.from_file(str(Path(__file__).parent/'fixtures/planeacion_alumnos_app.py'),default_timeout=30).run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.multiselect[0].options),1)
        self.assertIn('Sin grupo registrado',app.multiselect[0].options[0])
        app.checkbox[0].check().run();self.assertFalse(app.exception)
        self.assertTrue(any('Atención individual' in v for v in app.multiselect[0].options))
        app.multiselect[0].set_value(['I1']).run()
        next(b for b in app.button if b.label=='Añadir a esta planeación').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state.qa_envios,1)
        self.assertEqual(app.session_state.qa_doc_id,'raiz-b')
        self.assertIn('I1',[r['ID_Alumno'] for r in guia_grupal(app.session_state.qa_doc)['filas']])

"""Preparación sin doble captura; todos los nombres y antecedentes son ficticios."""
from copy import deepcopy
import json
from unittest import TestCase
from unittest.mock import patch
from services import planeacion as s,planeacion_rapida as r,planeacion_evaluacion as ev
from tests.test_planeacion_cero_friccion import individual,ACTOR


def fuente(tipo='EPP',alumno='A1',**extra):
    return {'tipo':tipo,'alumno':alumno,'vinculo_verificado':True,'registro':'F1','revision':'V1',
        'parte':'Conclusión','referencia':'Fuente ficticia','texto':json.dumps({'NEE':[{'NEE':'Necesita fortalecer la escritura.'}],
        'BAP':[{'Tipo de barrera':'Material sin alternativas accesibles','Contextos':'Aula','Acciones generales':'Ofrecer alternativas'}]}),**extra}


class RapidaTests(TestCase):
    def setUp(self):
        self.auth=patch.object(s,'autorizar',return_value=ACTOR);self.auth.start();self.addCleanup(self.auth.stop)

    def test_precarga_epp_sin_confundir_bap_ni_escribir(self):
        doc=individual();doc['tablas']['aprendizajes']=[];doc['metadatos']['fuentes']=[fuente()];before=deepcopy(doc)
        estado=r.estado(doc)
        self.assertEqual(estado['nee'],['Necesita fortalecer la escritura.'])
        self.assertIn('Material sin alternativas',estado['bap'][0][r.BARRERA])
        self.assertEqual(estado['defaults']['prioridades'],['escritura']);self.assertEqual(doc,before)

    def test_solo_destinatarios_exactos_e_instrumento_no_es_nee(self):
        doc=individual();doc['tablas']['aprendizajes']=[]
        doc['metadatos']['fuentes']=[fuente(alumno='A10'),fuente(tipo='BAPSE',texto='BAP_Fisicas: contenido')]
        estado=r.estado(doc);self.assertFalse(estado['nee']);self.assertFalse(estado['bap']);self.assertTrue(estado['avisos'])

    def test_cte_explicito_verificado_no_inventa_acuerdos(self):
        doc=individual();cte=fuente('CTE',texto=json.dumps({'acuerdos':['Probar materiales accesibles.']}))
        doc['metadatos']['fuentes']=[cte,fuente('ACTA',texto=cte['texto']),fuente('CTE',vinculo_verificado=False)]
        opciones=r.acuerdos(doc);self.assertEqual(len(opciones),1)
        elecciones=r.estado(doc)['defaults'];elecciones['acuerdos']=list(opciones)
        nuevo=r.ensamblar(doc,elecciones)
        self.assertIn('Probar materiales accesibles.',nuevo['tablas']['dosificacion'][-1]['Actividades'])
        elecciones['acuerdos']=['inventado'];self.assertTrue(r.validar(doc,elecciones))

    def test_cada_area_solo_prioridades_propias_y_formato_correcto(self):
        for area in r.POR_AREA:
            doc=individual(area);estado=r.estado(doc)
            self.assertEqual(estado['permitidas'],r.POR_AREA[area]);nuevo=r.ensamblar(doc,estado['defaults'])
            self.assertEqual(nuevo['formato'],'XXV' if area=='Trabajo Social' else 'XXIII')
            self.assertTrue(nuevo['tablas']['dosificacion'])

    def test_ensamble_aditivo_idempotente_sin_modificar_entrada(self):
        doc=individual();doc['textos']['Evaluación']='Decisión docente';antes=deepcopy(doc)
        elecciones=r.estado(doc)['defaults'];nuevo=r.ensamblar(doc,elecciones)
        self.assertEqual(doc,antes);self.assertEqual(nuevo['textos']['Evaluación'],'Decisión docente')
        self.assertEqual(nuevo['tablas']['aprendizajes'],doc['tablas']['aprendizajes'])
        elecciones['apoyos'].reverse()
        self.assertEqual(r.ensamblar(nuevo,elecciones)['tablas'],nuevo['tablas'])
        self.assertIn('Inicio:',nuevo['tablas']['dosificacion'][-1]['Actividades'])
        self.assertTrue(nuevo['metadatos']['preparacion_rapida']['requiere_revision'])

    def test_validacion_inmediata_y_rechazo_de_opciones_ajenas(self):
        doc=individual();base=r.estado(doc)['defaults']
        for key,value in [('prioridades',[]),('contextos',[]),('duracion',True),('metodo','otro'),('prioridades',['familia']),('apoyos',['inventado'])]:
            elecciones={**base,key:value};self.assertTrue(r.validar(doc,elecciones))
            with self.assertRaises(ValueError):r.ensamblar(doc,elecciones)
        self.assertTrue(r.validar(doc,None))

    def test_escala_individual_vinculada_sin_resultados_inventados(self):
        doc=individual();nuevo=r.ensamblar(doc,r.estado(doc)['defaults'])
        indicador=nuevo['tablas']['dosificacion'][-1]['_indicador_propuesto']
        rows=ev.filas(nuevo);fila=next(x for x in rows if x['Indicador de logro']==indicador)
        self.assertEqual(fila['Valoración'],'Sin valorar');self.assertIn('Inicio:',fila['Actividad vinculada'])
        indice=rows.index(fila);retirado=ev.cambiar_fila(nuevo,indice)
        self.assertNotIn(indicador,[x['Indicador de logro'] for x in ev.filas(retirado)])

    def test_dos_alumnos_con_fuentes_separadas(self):
        doc=individual();doc['datos']['Alumnos'].append({**doc['datos']['Alumnos'][0],'ID_Alumno':'A2','Nombre del alumno':'Otro ficticio'})
        doc['metadatos']['fuentes']=[fuente(),fuente(alumno='A2',registro='F2')]
        nuevo=r.ensamblar(doc,r.estado(doc)['defaults'])
        for row in nuevo['tablas']['dosificacion']:
            if not row.get('_actividad_rapida'):continue
            self.assertEqual(len(row['_alumnos_planeacion']),1)
            self.assertTrue(all(f['alumno']==row['_alumnos_planeacion'][0] for f in row['_origenes']))

    def test_ui_sin_campos_masivos_valida_antes_de_preparar(self):
        from streamlit.testing.v1 import AppTest
        from tests.test_planeacion_documento_directo import HELP_APP
        app=AppTest.from_string(HELP_APP).run(timeout=20)
        self.assertFalse(app.exception);self.assertEqual(len(app.text_area),0)
        next(x for x in app.multiselect if x.label=='Qué vamos a trabajar').set_value([]).run()
        self.assertTrue(next(x for x in app.button if x.label=='Preparar propuesta').disabled)
        self.assertNotIn('p_asistente_propuesta',app.session_state)

    def test_completar_vacio_no_duplica_la_fila_y_exporta_pdf(self):
        from services.planeacion_propuesta import conservar_redaccion,aplicar
        from services.planeacion_papel import huella
        from documents.planeacion import generar_pdf
        doc=individual();doc['tablas']['aprendizajes'][0]['Descriptor de logro']=''
        def rellenar(d):
            nuevo=deepcopy(d);nuevo['tablas']['aprendizajes'][0]['Descriptor de logro']='Indicador revisable';return nuevo
        elecciones=r.estado(doc)['defaults'];elecciones['completar']=True
        with patch('services.planeacion_apartados.proponer',side_effect=rellenar):nuevo=r.ensamblar(doc,elecciones)
        nuevo=conservar_redaccion(doc,nuevo);nuevo=aplicar(doc,{'base':huella(doc),'documento':nuevo})
        self.assertEqual(len(nuevo['tablas']['aprendizajes']),1)
        self.assertEqual(nuevo['tablas']['aprendizajes'][0]['Descriptor de logro'],'Indicador revisable')
        self.assertTrue(generar_pdf(nuevo).startswith(b'%PDF'))

    def test_autollenado_con_dos_filas_originales_identicas_no_pierde_ninguna(self):
        from services.planeacion_propuesta import conservar_redaccion
        doc=individual();doc['tablas']['aprendizajes']=[{},{}]
        def rellenar(d):
            nuevo=deepcopy(d)
            nuevo['tablas']['aprendizajes']=[{'Descriptor de logro':'Uno'},{'Descriptor de logro':'Dos'}]
            return nuevo
        elecciones=r.estado(doc)['defaults'];elecciones['completar']=True
        with patch('services.planeacion_apartados.proponer',side_effect=rellenar):nuevo=r.ensamblar(doc,elecciones)
        nuevo=conservar_redaccion(doc,nuevo)
        self.assertEqual([x['Descriptor de logro'] for x in nuevo['tablas']['aprendizajes']],['Uno','Dos'])

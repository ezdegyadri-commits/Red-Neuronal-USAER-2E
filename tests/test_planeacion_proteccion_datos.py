"""Reproducciones de pérdida de texto, conflicto y exclusión no destructiva."""
from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch
from services import planeacion as s,planeacion_papel as papel
from services.planeacion_guardado_estado import diagnostico
from services.planeacion_texto_local import recuperar
from services.planeacion_compartida import ampliar_matricula,proyectar_individuales
from services.planeacion_modalidad import guia_grupal
from services.planeacion_estabilidad import GuardadoPendiente
from tests.test_planeacion_todos_grupos import documento,matricula
from tests.test_planeacion_panel import ACTOR,PanelTests


class RestauracionPendienteTests(TestCase):
    def test_archivado_ofrece_restauracion_y_no_rebasa_revision_local(self):
        from ui import planeacion_pendientes as ui,planeacion as editor
        doc=documento(('A1',),todos=True);doc['revision']='base_local'
        ultimo=deepcopy(doc);ultimo['revision']='archivado';ultimo['metadatos']['borrador_eliminado']=True
        detalle=diagnostico(RuntimeError('Este borrador fue eliminado en otra sesión.'))
        self.assertEqual(detalle['tipo'],'archivado')
        state={'p_doc':doc,'p_pending':True,'p_guardado_diagnostico':detalle}
        with patch.object(ui.st,'session_state',state),patch.object(ui.st,'warning'),patch.object(ui.st,'caption'),patch.object(ui.st,'success'),patch.object(ui.st,'download_button'),patch.object(ui.st,'button',side_effect=lambda label,**kw:label=='Restaurar este borrador y reintentar'),patch.object(s,'versiones_actuales',return_value=[ultimo]),patch.object(s,'restaurar_borrador') as restaurar,patch.object(editor,'_guardar_edicion_pendiente',return_value=True) as guardar:
            ui.controles_guardado('p','k')
        restaurar.assert_called_once_with(ultimo);guardar.assert_called_once_with('p')
        self.assertEqual(state['p_doc']['revision'],'base_local')
        self.assertTrue(state['p_pending'])


class ExclusionesTests(TestCase):
    def test_individual_ya_redactado_no_se_imprime_pero_conserva_todo_su_aporte(self):
        d=documento(('A1','I1'),todos=True,incluir=True)
        d['metadatos']['guia_grupal_manual']={'filas':[{'ID_Alumno':'I1','Aprendizaje':'Trabajo previo individual','Situación inicial':'Antecedente'}]}
        d['metadatos']['aportaciones_equipo']={'Comunicación':{'filas':[{'ID_Alumno':'I1','Texto en formato':'Aporte previo'}]}}
        antes=deepcopy(d)
        nuevo=ampliar_matricula(d,matricula())
        self.assertEqual([a['ID_Alumno'] for a in nuevo['datos']['Alumnos']],['A1','B1','S1'])
        self.assertNotIn('I1',[r['ID_Alumno'] for r in guia_grupal(nuevo)['filas']])
        historia=nuevo['metadatos']['alumnos_atencion_individual_archivados']['I1']
        self.assertEqual(historia['fila']['Aprendizaje'],'Trabajo previo individual')
        self.assertEqual(historia['aportaciones']['Comunicación'][0]['Texto en formato'],'Aporte previo')
        self.assertEqual(nuevo['metadatos']['aportaciones_equipo'],antes['metadatos']['aportaciones_equipo'])
        self.assertEqual(d,antes);self.assertEqual(ampliar_matricula(nuevo,matricula()),nuevo)

    def test_documento_individual_nunca_es_filtrado_como_xix(self):
        d=documento(('I1',));d['metadatos']['modalidad_planeacion']='individual'
        self.assertEqual(proyectar_individuales(d,matricula()),d)


class RecuperacionTextoTests(TestCase):
    def setUp(self):
        self.p=patch.object(s,'autorizar',return_value=ACTOR);self.p.start()
    def tearDown(self):self.p.stop()
    def respaldo(self,d,valor='Texto recuperado'):
        spec=papel.hoja(d)
        c=next(c for c in spec['cells'].values() if c['editable'] and c['label']=='Aprendizaje')
        return {'tipo':'usaer-texto-pendiente-v2','documento':d['id'],'cache_id':spec['cache_id'],
                'celdas':[{'destinatario':c['destinatario'],'label':c['label'],'target':list(c['target']),'base':c['value'],'valor':valor}]}
    def test_recupera_por_id_aunque_hayan_cambiado_indices(self):
        d=documento(('B1',),todos=True);respaldo=self.respaldo(d)
        nuevo=ampliar_matricula(d,matricula());antes=deepcopy(nuevo)
        recuperado=recuperar(nuevo,respaldo)
        fila=next(r for r in guia_grupal(recuperado)['filas'] if r['ID_Alumno']=='B1')
        self.assertEqual(fila['Aprendizaje'],'Texto recuperado');self.assertEqual(nuevo,antes)

    def test_no_sobrescribe_otra_edicion_ni_otra_cuenta(self):
        d=documento();respaldo=self.respaldo(d)
        d['metadatos']['guia_grupal_manual']={'filas':[{'ID_Alumno':'A1','Aprendizaje':'Edición remota'}]}
        with self.assertRaisesRegex(RuntimeError,'también cambió'):recuperar(d,respaldo)
        self.assertEqual(guia_grupal(d)['filas'][0]['Aprendizaje'],'Edición remota')
        respaldo['cache_id']='otra-cuenta'
        with self.assertRaises(PermissionError):recuperar(d,respaldo)


class DiagnosticoTests(TestCase):
    def test_causa_y_solucion_distinguen_red_limite_y_conflicto(self):
        self.assertEqual(diagnostico(TimeoutError())['tipo'],'conexion')
        self.assertEqual(diagnostico(GuardadoPendiente(15))['tipo'],'espera')
        self.assertEqual(diagnostico(RuntimeError('Otra sesión guardó cambios'))['tipo'],'revision')
        self.assertEqual(diagnostico(PermissionError())['tipo'],'acceso')
        self.assertTrue(diagnostico(ValueError('Falta el dato'))['accion'])

    def test_error_no_marca_confirmado_y_explicacion_queda_disponible(self):
        from ui import planeacion as u
        state={'p_doc':documento(),'p_pending':False}
        with patch.object(u.st,'session_state',state),patch.object(s,'guardar',side_effect=TimeoutError()):
            self.assertFalse(u._persist('p'))
        self.assertTrue(state['p_pending'])
        self.assertEqual(state['p_guardado_diagnostico']['tipo'],'conexion')
        self.assertNotIn('p_papel_aceptado',state)


class PersistenciaExclusionTests(PanelTests):
    def test_exclusion_se_guarda_sin_borrar_la_version_anterior(self):
        frame=matricula()
        d=documento(('A1','I1'),todos=True,incluir=True)
        # Sembrar una versión histórica, anterior a la regla de exclusión.
        with patch.object(s,'padron_autorizado',return_value=frame):
            anterior=s.guardar(d)
            projected=ampliar_matricula(anterior,frame)
            nuevo=s.guardar(projected)
            self.assertEqual(nuevo['id'],anterior['id'])
            versiones=s.reconstruir(self.sheet.rows)
            self.assertIn('I1',[a['ID_Alumno'] for a in versiones[0]['datos']['Alumnos']])
            self.assertNotIn('I1',[a['ID_Alumno'] for a in versiones[-1]['datos']['Alumnos']])

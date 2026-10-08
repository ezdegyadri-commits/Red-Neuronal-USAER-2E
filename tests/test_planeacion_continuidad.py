from copy import deepcopy
from datetime import date
import json
import unittest
from unittest.mock import patch
import pandas as pd
from services import planeacion as s,planeacion_generacion as g
from services import planeacion_continuidad as c
from services import planeacion_colaboracion as col
from services.planeacion_modalidad import modalidad,filtrar,comprobar
from tests.test_planeacion_completa import documento,resultado
from tests.test_planeacion_panel import PanelTests,ACTOR,ALUMNO,documento as doc_panel


class ContinuidadTests(unittest.TestCase):
    def test_contexto_local_visible_minimizado_y_cambia_huella(self):
        with patch.object(s,'autorizar'):
            d=documento();d['metadatos']['curriculo']={'contexto_local':'Escuela ficticia: huerto escolar, intereses en plantas, recursos de cartón.'}
            a=g.preparar_solicitud(d,g.configuracion(d))
            self.assertIn('huerto escolar',a['resumen']);self.assertNotIn('Escuela ficticia',a['contexto']['contextualizacion_docente'])
            d['metadatos']['curriculo']['contexto_local']='Proyecto comunitario de lectura.'
            b=g.preparar_solicitud(d,g.configuracion(d));self.assertNotEqual(a['huella'],b['huella'])
    def test_sesiones_editadas_y_eliminadas_no_reaparecen_al_regenerar(self):
        with patch.object(s,'autorizar'):
            d=documento('Comunicación');req=g.preparar_solicitud(d,g.configuracion(d));res=resultado(req,'Comunicación')
            nuevo=g.ensamblar(d,res,req);e=nuevo['metadatos']['equipo']
            e['sesiones'][0]['actividad']='Edición profesional conservada';borrada=e['sesiones'][1]['id'];e['sesiones'].pop(1)
            req2=g.preparar_solicitud(nuevo,req['configuracion_original']);otra=g.ensamblar(nuevo,res,req2)
            self.assertTrue(any(t['actividad']=='Edición profesional conservada' for t in otra['metadatos']['equipo']['sesiones']))
            self.assertNotIn(borrada,[t['id'] for t in otra['metadatos']['equipo']['sesiones']])
            self.assertEqual(len(otra['metadatos']['equipo']['sesiones']),len(e['sesiones']))
            req3=g.preparar_solicitud(otra,req['configuracion_original']);otra2=g.ensamblar(otra,res,req3)
            self.assertEqual(len(otra2['metadatos']['equipo']['sesiones']),len(e['sesiones']))
    def test_modalidad_pendiente_y_flexibilidad_explicita(self):
        frame=pd.DataFrame([{**ALUMNO,'Tipo_Atencion':'Individual'},{**ALUMNO,'ID_Alumno':'A2','Tipo_Atencion':''}])
        self.assertEqual(modalidad(frame.iloc[1]),'por confirmar');self.assertTrue(filtrar(frame,'grupal').empty)
        comprobar(frame,['A1'],'grupal',True)
        with self.assertRaises(PermissionError):comprobar(frame,['A2'],'grupal',True)
    def fuente(self,rev='r1'):
        return {'tipo':'EPP','parte':'Conclusión','documento_origen':'epp-ficticia','registro':'epp-ficticia-Conclusión',
            'revision':rev,'alumno':'A1','referencia':'E1','vinculo_verificado':True,
            'texto':json.dumps({'NEE':[{'NEE':'Necesita expresar necesidades','Apoyos':'Tablero','Responsables':'Equipo'}],
                'BAP':[{'Tipo de barrera':'Instrucciones solo orales','Acciones generales':'Apoyo visual','Responsables':'Docente'}]})}
    def test_epp_pi_precarga_sin_pisar_ni_validar(self):
        d=doc_panel('XXI');d['metadatos']['fuentes']=[self.fuente()]
        d=c.actualizar_vinculos(d);nuevo=c.trasladar_epp(d)
        self.assertEqual(nuevo['tablas']['necesidades'][0]['NEE'],'Necesita expresar necesidades')
        self.assertEqual(nuevo['tablas']['barreras'][0]['BAP'],'Instrucciones solo orales')
        self.assertFalse(nuevo['metadatos']['NEE confirmadas desde IEPP'])
        nuevo['tablas']['necesidades'][0]['NEE']='Necesidad priorizada por equipo'
        self.assertEqual(c.trasladar_epp(nuevo)['tablas']['necesidades'][0]['NEE'],'Necesidad priorizada por equipo')
    def test_cambio_origen_advierte_y_conserva_redaccion(self):
        d=documento();d['metadatos']['fuentes']=[self.fuente()];d=c.actualizar_vinculos(d)
        d['textos']['Evaluación']='Decisión profesional';d['metadatos']['fuentes']=[self.fuente('r2')]
        actualizado=c.actualizar_vinculos(d)
        self.assertTrue(actualizado['metadatos']['avisos_continuidad']);self.assertEqual(actualizado['textos']['Evaluación'],'Decisión profesional')
    def test_no_vincula_otro_alumno_ni_elige_pi_ambiguo(self):
        d=documento();f=self.fuente();f['alumno']='A2';d['metadatos']['fuentes']=[f]
        self.assertFalse(c.actualizar_vinculos(d)['metadatos']['vinculos_documentales'])
        pi={**f,'alumno':'A1','tipo':'PLAN','formato':'XXI','documento_origen':'pi1'}
        d['metadatos']['fuentes']=[pi,{**pi,'documento_origen':'pi2'}]
        out=c.actualizar_vinculos(d);self.assertFalse(out['metadatos']['vinculos_documentales']);self.assertTrue(out['metadatos']['avisos_continuidad'])
    def test_pi_hasta_tres_cursos(self):
        p=doc_panel('XXI');p['datos']['Vigencia en cursos escolares']='3';p['datos']['Curso escolar']='2026-2027'
        self.assertTrue(c.vigente_pi(p,'2028-2029'));self.assertFalse(c.vigente_pi(p,'2029-2030'))
    def test_seguimiento_exige_evidencia_real_y_no_futuro(self):
        d=documento();nuevo=c.seguimiento(d,'2026-10-01','Participó con tarjetas según el acta.','Continuar',['E1'])
        self.assertEqual(len(c.seguimiento(nuevo,'2026-10-01','Participó con tarjetas según el acta.','Continuar',['E1'])['metadatos']['seguimiento_formativo']),1)
        self.assertEqual(nuevo['metadatos']['seguimiento_formativo'][0]['origenes'][0]['tipo'],'ACTA')
        with self.assertRaises(ValueError):c.seguimiento(d,'2040-01-01','Futuro','Continuar',['E1'])
        d['metadatos']['fuentes'][0]['tipo']='PLAN'
        with self.assertRaises(ValueError):c.seguimiento(d,'2026-10-01','Actividad prevista','Continuar',['E1'])


class ColaboracionTests(unittest.TestCase):
    setUp=PanelTests.setUp
    tearDown=PanelTests.tearDown
    def fila(self):
        return {**dict.fromkeys(col.COLUMNAS,''),'ID_Alumno':'A1','Objetivo / qué trabajar':'El alumno expresa una necesidad.',
                'Necesidad o barrera documentada':'Necesita expresar necesidades','Actividad / cómo trabajar':'Elegir un apoyo visual.'}
    def test_aporte_acotado_no_altera_tablas_ni_otras_areas(self):
        d=s.guardar(doc_panel('XXI'))
        with patch.object(s,'identidad',return_value={**ACTOR,'cuenta':'psic','nombre':'Profesional ficticio','area':'Psicología'}):
            entrada=deepcopy(d);entrada['tablas']['necesidades']=[{'NEE':'Dato manipulado'}]
            d=s.guardar_aportacion(entrada,[self.fila()],'Observación del área')
            self.assertEqual(d['tablas']['necesidades'],[])
            with self.assertRaises(PermissionError):s.guardar(d)
        with patch.object(s,'identidad',return_value={**ACTOR,'cuenta':'com','nombre':'Otro profesional','area':'Comunicación'}):
            d=s.guardar_aportacion(d,[self.fila()],'Otra aportación')
        self.assertEqual(set(d['metadatos']['aportaciones_equipo']),{'Psicología','Comunicación'})
        self.assertEqual(d['cuenta'],'prueba');self.assertEqual(d['estado'],'BORRADOR')
    def test_aporte_ajeno_director_y_version_obsoleta_denegados(self):
        d=s.guardar(doc_panel('XXI'));row=self.fila();row['ID_Alumno']='A2'
        with self.assertRaises(PermissionError):s.guardar_aportacion(d,[row],'')
        with patch.object(s,'identidad',return_value={**ACTOR,'director':True}):
            with self.assertRaises(PermissionError):s.guardar_aportacion(d,[self.fila()],'')
        actualizado=s.guardar_aportacion(d,[self.fila()],'')
        with self.assertRaises(RuntimeError):s.guardar_aportacion(d,[self.fila()],'')
        self.assertNotEqual(d['revision'],actualizado['revision'])
    def test_integracion_idempotente_no_firma(self):
        d=s.guardar(doc_panel('XXI'));d=s.guardar_aportacion(d,[self.fila()],'')
        integrado=col.integrar(d);integrado=s.guardar(integrado)
        self.assertEqual(len(col.integrar(integrado)['tablas']['necesidades']),1)
        self.assertEqual(integrado['metadatos']['firma_aprobada_por'],'')
    def test_no_cambia_aportes_desde_editor_general(self):
        d=s.guardar(doc_panel('XXI'));d=s.guardar_aportacion(d,[self.fila()],'')
        d['metadatos']['aportaciones_equipo']['Aprendizaje']['observaciones']='Cambio fuera del módulo'
        with self.assertRaises(PermissionError):s.guardar(d)
    def test_guia_de_un_grupo_y_aporte_en_columna_propia(self):
        d=doc_panel();d['metadatos']['modalidad_planeacion']='grupal'
        self.assertTrue(col.compartible(d));d=col.aportar(d,{**ACTOR,'area':'Comunicación'},[self.fila()],'')
        out=col.integrar(d);r=out['metadatos']['guia_grupal_manual']['filas'][0]
        self.assertIn('Elegir',r['Comunicación']);self.assertFalse(r['Psicología'])
        d['datos']['Alumnos'].append({**d['datos']['Alumnos'][0],'ID_Alumno':'A2','Grupo':'Otro'})
        self.assertFalse(col.compartible(d))

    def test_guia_actualiza_aporte_sin_pisar_celda_humana(self):
        d=doc_panel();d['metadatos']['modalidad_planeacion']='grupal';actor={**ACTOR,'area':'Comunicación'}
        d=col.integrar(col.aportar(d,actor,[self.fila()],''))
        fila=self.fila();fila['Actividad / cómo trabajar']='Nueva propuesta'
        d=col.integrar(col.aportar(d,actor,[fila],''))
        self.assertIn('Nueva propuesta',d['metadatos']['guia_grupal_manual']['filas'][0]['Comunicación'])
        d['metadatos']['guia_grupal_manual']['filas'][0]['Comunicación']='Edición humana'
        fila['Actividad / cómo trabajar']='Otra propuesta';d=col.integrar(col.aportar(d,actor,[fila],''))
        self.assertEqual(d['metadatos']['guia_grupal_manual']['filas'][0]['Comunicación'],'Edición humana')
        self.assertTrue(d['metadatos']['avisos_integracion'])
        self.assertNotEqual(d['metadatos']['aportaciones_integradas']['Comunicación'],d['metadatos']['aportaciones_equipo']['Comunicación']['revision'])


if __name__=='__main__':unittest.main()

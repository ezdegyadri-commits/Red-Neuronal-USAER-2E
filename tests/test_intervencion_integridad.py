from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import unittest
from unittest.mock import patch
from services import nee_documentales as nee,padron_integridad as integridad,planeacion_calidad as calidad


class NecesidadesTests(unittest.TestCase):
    def test_hallazgos_son_propuestas_no_diagnosticos_ni_validaciones(self):
        text='Dificultades para mantener la atención durante tareas escolares.\nEscaso desarrollo de conciencia fonológica.\nDificultad para reconocer y combinar sílabas.\nNecesidad de apoyos visuales para comprender instrucciones.\nDiagnóstico TEA\nNo presenta dificultad para comprender instrucciones.'
        rows=nee.detectar(text,'FICTICIO','hash')
        self.assertEqual(len(rows),4)
        self.assertTrue(all(r['estado']=='Detectada' and 'revisar' in r['origen'] and r['fundamento'] in text for r in rows))
    def test_fusion_conserva_fuentes_y_exige_revision(self):
        rows=nee.detectar('Necesita reconocer letras mediante tarjetas ilustradas.\nNecesita formar sílabas con letras móviles.','D','H')
        before=deepcopy(rows);rows[0]['prioridad']='Alta'
        merged=nee.fusionar(rows,[r['id'] for r in rows],'Necesita reconocer letras y formar sílabas con apoyos visuales.','D','H')
        self.assertEqual(len(merged),3);self.assertEqual([r['estado'] for r in merged],['Descartada','Descartada','Detectada'])
        self.assertEqual(merged[-1]['prioridad'],'Alta')
        self.assertTrue(all(r['fundamento'] in merged[-1]['fundamento'] for r in before))
        self.assertEqual(rows[0]['estado'],'Detectada')
        with self.assertRaises(ValueError):nee.validar_registros([{**before[0],'prioridad':'Urgente'}])


class IntegridadTests(unittest.TestCase):
    def test_variantes_reversibles_no_fusionan_identidades(self):
        rows=[{'ID_Alumno':str(i),'ID_Escuela':'E','CURP':'FICTICIA'+str(i),'Grado':v,'Grupo':''} for i,v in enumerate(('2°a','2A','2° A','2º A'))]
        before=deepcopy(rows);esc=[{'ID_Escuela':'E','CCT':'TEST'}]
        plan=integridad.diagnosticar(rows,esc);normal=integridad.simular(rows,plan)
        self.assertTrue(all(r['Grado']=='2°' and r['Grupo']=='A' for r in normal))
        self.assertEqual(integridad.simular(normal,plan,True),before);self.assertEqual(rows,before)
        changed=deepcopy(rows);changed[0]['Grupo']='B'
        with self.assertRaises(ValueError):integridad.simular(changed,plan)
    def test_duplicados_referencias_y_cct_se_reportan_sin_tocar_datos(self):
        rows=[{'ID_Alumno':'A','ID_Escuela':'NO','CURP':'MISMA','Grado':'2A','Grupo':'B'},{'ID_Alumno':'B','ID_Escuela':'E','CURP':'MISMA','Grado':'2','Grupo':'A','CCT_Escuela':'OTRA'}]
        before=deepcopy(rows)
        docs=[{'id':'DOC','datos':{'Alumnos':[{'ID_Alumno':'HISTORICO'}],'Curso escolar':'2026-2029'}}]
        r=integridad.diagnosticar(rows,[{'ID_Escuela':'E','CCT':'TEST'}],docs)
        self.assertGreaterEqual(len(r['avisos']),6);self.assertEqual(rows,before)


class CoherenciaTests(unittest.TestCase):
    def test_dos_nee_conservan_pda_descriptor_y_actividades_independientes(self):
        from tests.test_planeacion_intervenciones_nee import ejemplo
        from tests.test_planeacion_completa import resultado
        from services import planeacion_intervenciones_nee as n,planeacion_generacion as g,planeacion as s
        d=ejemplo()
        with patch.object(s,'autorizar',return_value={'cuenta':d['cuenta'],'director':False}):
            d=n.incorporar(d,[r['id'] for r in n.catalogo(d)])
            ajustes={**g.configuracion(d),'inicio':'2026-10-07','grado_referencia':1}
            d=g.sugerir_curriculo(d,ajustes)
            referente=d['metadatos']['curriculo']['registros'][0]
            for i,b in enumerate(n.bloques(d),1):
                d=n.editar(d,b['id'],'Aprendizaje y/u objetivo',referente['pda'])
                d=n.editar(d,b['id'],'Descriptor de logro',calidad.descriptor(d['datos']['Alumnos'][0]['Nombre del alumno'],'identifica',f'{i+1} tarjetas entre tres opciones con apoyo visual'))
            antes=deepcopy(d);req=g.preparar_solicitud(d,ajustes);res=resultado(req,'Aprendizaje')
            for i,u in enumerate(res['unidades'],1):u['evidencias']=['NEE-SELECCIONADA-'+str(i),'E1']
            nuevo=g.ensamblar(d,res,req)
        bs=n.bloques(nuevo)
        self.assertEqual(bs[0]['campos']['Actividades'],res['unidades'][0]['actividad'])
        self.assertEqual(bs[1]['campos']['Actividades'],res['unidades'][1]['actividad'])
        for a,b in zip(n.bloques(antes),bs):
            self.assertEqual(a['campos']['Descriptor de logro'],b['campos']['Descriptor de logro'])
            self.assertEqual(a['campos']['Aprendizaje y/u objetivo'],b['campos']['Aprendizaje y/u objetivo'])
            self.assertTrue(b['campos']['Evaluación y seguimiento'])
        self.assertEqual(d,antes)
        self.assertEqual(nuevo['tablas']['dosificacion'],antes['tablas']['dosificacion'])

    def test_alerta_especifica_sin_calificacion(self):
        d={'metadatos':{'intervenciones_nee':[{'campos':{'NEE':'Necesita reconocer letras y sílabas.','Actividades':'Resolver sumas contando fichas.'}}]}}
        alerta=calidad.alertas_coherencia(d)
        self.assertEqual(len(alerta),1);self.assertIn('descriptor y evaluación',alerta[0]);self.assertIn('no una conclusión',alerta[0])
    def test_ia_valida_indicadores_y_no_escribe_documentos(self):
        def generar(prompt,schema,validar,config,*args):
            self.assertIn('no certifiques',prompt)
            self.assertNotIn('Valoración docente',schema['properties'])
            with self.assertRaises(ValueError):validar({'observaciones':[{'indicador':99,'apartado':'x','hallazgo':'x','sugerencia':'x'}]})
            return validar({'observaciones':[{'indicador':8,'apartado':'NEE 1','hallazgo':'El descriptor refiere lectura y la actividad conteo.','sugerencia':'Precisar una tarea de lectura que permita observar el descriptor.'}]})
        with patch('ai.documento_json.generar',side_effect=generar):
            self.assertEqual(calidad.analizar_ia({'resumen':'Datos ficticios'},{} )['observaciones'][0]['indicador'],8)


class ColaTests(unittest.TestCase):
    def test_20_solicitudes_acotadas_sin_bloquear_y_aisladas(self):
        from ai import documento_json as motor
        salida=Event();bloqueadas=[];futures=[]
        def ejecutar(datos):salida.wait(5);return datos
        try:
            with ThreadPoolExecutor(max_workers=20) as pool:
                pendientes=[pool.submit(motor.enviar,ejecutar,{'sesion':i}) for i in range(20)]
                for p in pendientes:
                    try:futures.append(p.result(2))
                    except RuntimeError:bloqueadas.append(True)
            self.assertEqual(len(futures),8);self.assertEqual(len(bloqueadas),12)
        finally:salida.set()
        results=[f.result(5)['sesion'] for f in futures]
        self.assertEqual(len(set(results)),8)
        self.assertEqual(motor.enviar(lambda x:x,{'sesion':99}).result(2),{'sesion':99})

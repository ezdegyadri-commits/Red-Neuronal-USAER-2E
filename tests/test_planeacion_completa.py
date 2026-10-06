from copy import deepcopy
from datetime import date
from unittest.mock import patch
import unittest
import pandas as pd
from services import planeacion as s,planeacion_generacion as g
from services.planeacion_modelo import crear_plantilla
from services.planeacion_equipo import COMPETENCIAS
from ai.planeacion_completa import validar_completa,solicitud_completa

def documento(area='Aprendizaje',dos=False):
    alumnos=[{'ID_Alumno':'A1','Nombre_Completo':'Alumno ficticio Uno','ID_Escuela':'E1','Nombre_Escuela':'Escuela ficticia','CCT_Escuela':'TEST','Grado':'5','Grupo':'A'}]
    if dos:alumnos.append({**alumnos[0],'ID_Alumno':'A2','Nombre_Completo':'Alumno ficticio Dos','Grupo':'B'})
    doc=crear_plantilla('XXV' if area=='Trabajo Social' else 'XXIII',[a['ID_Alumno'] for a in alumnos],alumnos,autor='Autor ficticio',funcion=area,fecha=date(2026,10,6))
    doc.update(id='documento-ficticio',cuenta='cuenta-ficticia',revision='',observaciones_director='')
    doc['metadatos']['fuentes']=[{'tipo':'ACTA','alumno':a['ID_Alumno'],'referencia':'E'+str(i+1),'fecha':'2026-10-02','registro':'Registro ficticio '+str(i),
        'texto':a['Nombre_Completo']+' participa en lectura con tarjetas. Necesita apoyos para expresar emociones y tomar turnos.','vinculo_verificado':True,'alcance':'individual'} for i,a in enumerate(alumnos)]
    doc['metadatos'].update(resumen_educativo='Lectura y participación con apoyos documentados.',necesidades_confirmadas='',referente_curricular='')
    return doc

def resultado(req,area):
    unidades=[];n=6 if area=='Psicología' else 2
    for i in range(n):
        unidades.append({'necesidad':'Necesidad educativa documentada para participar.','objetivo':'El alumno identifica apoyos para participar.','descriptor':'El alumno elige un apoyo y explica su elección.',
            'actividad':'Inicio: observar tarjetas. Desarrollo: elegir y explicar. Cierre: compartir una respuesta.','contexto':'Aula regular' if area=='Psicología' and i==5 else 'Familia' if area=='Trabajo Social' else 'Aula de apoyo',
            'apoyos':'Tarjetas y tiempo de respuesta.','recursos':'Tarjetas disponibles','evaluacion':'Lista de cotejo: observar la elección durante la actividad; revisar al cierre.','fundamento':'La propuesta responde al registro y al referente seleccionado.',
            'evidencias':list(req['evidencias']),'fuentes':['SEGEY-USAER'],'referentes':[r['id'] for r in req['contexto'].get('referentes_por_grado',[])][:1],
            'destinatarios':list(req['aliases']),'competencias':[COMPETENCIAS[i]] if area=='Psicología' and i<5 else []})
    return {'observaciones':'Revisar la propuesta antes de aplicarla.','faltantes':[],'unidades':unidades,'sugerencia_familia':'Prever una hoja de sugerencias con un apoyo cotidiano; no se presume entregada.'}

class GeneracionCompletaTests(unittest.TestCase):
    def test_edicion_grupal_conserva_identidad_y_borrador(self):
        from ui import planeacion as ui
        d=documento();base=[{'ID_Alumno':'A1','Actividades':'Propuesta inicial','Situación inicial':'Registro documentado','Situación final':''}]
        d['metadatos']['grupal_zona']=deepcopy(base)
        state={'demo_doc':d,'editor':{'edited_rows':{0:{'Actividades':'Cambio docente','ID_Alumno':'A3','Alumno':'Otro'}}}}
        with patch.object(ui.st,'session_state',state),patch.object(ui,'_persist') as guardar:
            ui._grupal_zona('demo','editor',base)
            guardar.assert_called_once_with('demo',automatic=True)
        self.assertEqual(state['demo_doc']['metadatos']['grupal_zona'][0]['ID_Alumno'],'A1')
        self.assertEqual(state['demo_doc']['metadatos']['grupal_zona'][0]['Actividades'],'Cambio docente')
        self.assertEqual(base[0]['Actividades'],'Propuesta inicial')
    def test_material_individual_no_se_asigna_a_otro_alumno(self):
        from services.materiales_planeacion import incorporar,fuentes_materiales
        d=documento();material={'id':'ficticio','nombre':'informe.txt','alumnos':['A3']}
        with self.assertRaises(PermissionError):incorporar(d,material,'Informe educativo revisado')
        material['alumnos']=['A1'];d=incorporar(d,material,'Informe educativo revisado')
        self.assertEqual(fuentes_materiales(d)[0]['alumno'],'A1')
    def test_grupal_zona_rechaza_otro_alumno_y_duplicados(self):
        from services.planeacion_equipo import validar
        d=documento();d['metadatos']['grupal_zona']=[{'ID_Alumno':'A3'}]
        with self.assertRaises(PermissionError):validar(d)
        d['metadatos']['grupal_zona']=[{'ID_Alumno':'A1'},{'ID_Alumno':'A1'}]
        with self.assertRaises(ValueError):validar(d)
        d['metadatos']['grupal_zona']=[{'ID_Alumno':'A1','Actividades':'Redacción docente'}]
        validar(d)
    def setUp(self):
        self.a=patch.object(s,'autorizar',return_value={'cuenta':'cuenta-ficticia','director':False});self.a.start();self.addCleanup(self.a.stop)
    def preparar(self,area='Aprendizaje',dos=False):
        d=g.prellenar(documento(area,dos));ajustes={**g.configuracion(d),'inicio':'2026-10-07','grado_referencia':3}
        return d,g.preparar_solicitud(d,ajustes)
    def test_prellenado_no_inventa_y_no_pisa_redaccion(self):
        d=documento();nuevo=g.prellenar(d)
        self.assertIn('E1',nuevo['metadatos']['necesidades_confirmadas']);self.assertEqual(d['metadatos']['necesidades_confirmadas'],'')
        nuevo['metadatos']['necesidades_confirmadas']='Redacción revisada por docente'
        self.assertEqual(g.prellenar(nuevo)['metadatos']['necesidades_confirmadas'],'Redacción revisada por docente')
    def test_otro_alumno_excluido_y_no_justifica_actividad(self):
        d=documento(dos=True);d['metadatos']['fuentes'].append({**d['metadatos']['fuentes'][0],'alumno':'A3','referencia':'OTRO','texto':'Información ajena'})
        d=g.prellenar(d);req=g.preparar_solicitud(d,{**g.configuracion(d),'inicio':'2026-10-07'})
        self.assertNotIn('OTRO',req['evidencias']);self.assertNotIn('Información ajena',d['metadatos']['necesidades_confirmadas'])
        res=resultado(req,'Aprendizaje');res['unidades'][0].update(evidencias=['E1'],destinatarios=['Alumno 2'])
        with self.assertRaises(ValueError):validar_completa(res,d['formato'],'Aprendizaje',req['contexto'],req['aliases'],req['evidencias'])
    def test_resumen_y_prompt_sin_nombre_real_ni_id(self):
        d,req=self.preparar();prompt=solicitud_completa(req['resumen'],d['formato'],d['datos']['Función'],req['contexto'],req['ajustes'],req['aliases'],req['evidencias'])
        self.assertNotIn('Alumno ficticio Uno',prompt);self.assertNotIn('Escuela ficticia',prompt);self.assertNotIn('"A1"',prompt)
        self.assertIn('Alumno 1',prompt);self.assertIn('ZONA-GRUPAL',prompt)
    def test_grado_anterior_oficial_no_cambia_padron(self):
        d,req=self.preparar();refs=req['contexto'].get('referentes_por_grado',[])
        self.assertTrue(refs);self.assertTrue(all(r['grado']==3 for r in refs));self.assertEqual(d['datos']['Alumnos'][0]['Grado'],'5')
    def test_referente_y_destinatario_inventados_rechazados(self):
        d,req=self.preparar();res=resultado(req,'Aprendizaje')
        for campo,valor in [('fuentes',['FUENTE-INVENTADA']),('destinatarios',['Alumno 99']),('referentes',['PDA-INVENTADO'])]:
            copia=deepcopy(res);copia['unidades'][0][campo]=valor
            with self.assertRaises(ValueError):validar_completa(copia,d['formato'],'Aprendizaje',req['contexto'],req['aliases'],req['evidencias'])
    def test_ensamble_cuatro_areas_y_resultados_pendientes(self):
        for area in ['Aprendizaje','Psicología','Comunicación','Trabajo Social']:
            d,req=self.preparar(area);nuevo=g.ensamblar(d,resultado(req,area),req)
            self.assertTrue(nuevo['tablas']['barreras' if area=='Trabajo Social' else 'aprendizajes'])
            self.assertTrue(nuevo['tablas']['dosificacion'])
            if area=='Trabajo Social':self.assertEqual(nuevo['textos']['Resultados obtenidos en los diferentes contextos'],'')
            else:self.assertTrue(nuevo['textos']['Evaluación'])
            grupal=nuevo['metadatos'].get('equipo',{}).get('grupal',nuevo['metadatos'].get('grupal_zona',[]))
            self.assertTrue(grupal);self.assertEqual(grupal[0]['Situación final'],'')
            if area=='Psicología':
                self.assertEqual(len(nuevo['metadatos']['equipo']['sesiones']),6)
                self.assertTrue(all(c['Actividad prevista'] for c in nuevo['metadatos']['equipo']['competencias']))
    def test_regenerar_sin_duplicar_ni_borrar_ajustes(self):
        d,req=self.preparar();res=resultado(req,'Aprendizaje');nuevo=g.ensamblar(d,res,req)
        req2=g.preparar_solicitud(nuevo,req['configuracion_original']);nuevo2=g.ensamblar(nuevo,res,req2)
        self.assertEqual(len(nuevo2['tablas']['dosificacion']),len(nuevo['tablas']['dosificacion']))
        nuevo['tablas']['aprendizajes'][0]['Descriptor de logro']='Cambio docente'
        nuevo['textos']['Evaluación']='Evaluación docente revisada'
        req3=g.preparar_solicitud(nuevo,req['configuracion_original']);editado=g.ensamblar(nuevo,res,req3)
        self.assertTrue(any(r['Descriptor de logro']=='Cambio docente' for r in editado['tablas']['aprendizajes']))
        self.assertEqual(editado['textos']['Evaluación'],'Evaluación docente revisada')
    def test_cambio_de_evidencia_invalida_ensamble(self):
        d,req=self.preparar();res=resultado(req,'Aprendizaje')
        d['metadatos']['resumen_educativo']='Se actualizó la evidencia educativa.'
        with self.assertRaises(ValueError):g.ensamblar(d,res,req)
    def test_calendario_no_propone_cte_ni_fines_de_semana(self):
        d,req=self.preparar();ajustes={**req['configuracion_original'],'inicio':'2026-10-29','dias':['Viernes'],'sesiones':4}
        fechas=g.fechas_sesiones(d,ajustes)
        self.assertNotIn('2026-10-30',fechas);self.assertNotIn('2026-11-27',fechas)
        self.assertTrue(all(date.fromisoformat(f).weekday()==4 for f in fechas))
    def test_no_hay_datos_suficientes_no_inventa(self):
        d=documento();d['metadatos']['fuentes']=[];d['metadatos']['resumen_educativo']=''
        with self.assertRaises(ValueError):g.preparar_solicitud(d,g.configuracion(d))

if __name__=='__main__':unittest.main()

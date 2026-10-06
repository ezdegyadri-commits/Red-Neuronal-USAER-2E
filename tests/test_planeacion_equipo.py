import unittest
from copy import deepcopy
from datetime import date
from services.planeacion_modelo import crear_plantilla
from services import planeacion_equipo as e
from services.curriculo import contexto_ia
from ai.planeacion_prompt import solicitud

def documento(area='Psicología'):
    a={'ID_Alumno':'A1','Nombre_Completo':'Alumno ficticio','ID_Escuela':'E1','Nombre_Escuela':'Escuela ficticia','CCT_Escuela':'TEST','Grado':'3','Grupo':'A'}
    return e.preparar(crear_plantilla('XXV' if area=='Trabajo Social' else 'XXIII',['A1'],[a],autor='Autor ficticio',funcion=area,fecha=date(2026,10,6)))

def sesion(fecha='2026-10-07',contexto='Aula de apoyo'):
    return {'fecha':fecha,'subgrupo':'Subgrupo 1','contexto':contexto,'competencias':list(e.COMPETENCIAS),
            'objetivo':'Los alumnos nombran emociones con apoyo visual.','actividad':'Observan tarjetas, eligen una emoción y explican su elección.',
            'apoyos':'Tarjetas y tiempo de respuesta.','recursos':'Tarjetas disponibles','seguimiento':'Registrar la respuesta durante la sesión.'}

class EquipoTests(unittest.TestCase):
    def test_perfiles_reales_y_ocho_escuelas_de_diego(self):
        from services.cronogramas import perfil_especialista
        casos=[('Psic. María José Cupul Realpozo','PSICOLOGIA','Psicología'),
               ('Abril de María Chable Ríos','PSICOLOGIA','Psicología'),
               ('Com. Elmy Lucelly Puerto Gone','COMUNICACION','Comunicación'),
               ('Marilyn Pérez Lizama','COMUNICACION','Comunicación'),
               ('T.S. Diego Peralta Torres','TRABAJO SOCIAL','Trabajo Social')]
        for nombre,rol,area in casos:
            perfil=perfil_especialista(nombre,rol)
            self.assertIsNotNone(perfil,nombre)
            self.assertEqual(perfil['area'],area)
            self.assertEqual(len(perfil['escuelas']),8 if area=='Trabajo Social' else 4)
        self.assertIsNone(perfil_especialista('Persona ajena','PSICOLOGIA'))
    def test_no_modifica_apoyo_ni_plan_individual(self):
        d=documento('Aprendizaje');self.assertNotIn('equipo',d['metadatos'])
        d=documento();d['formato']='XXI';d['metadatos'].pop('equipo');self.assertEqual(e.preparar(d),d)
    def test_area_correcta_y_sin_trasladar_minimos(self):
        for area in e.AREAS:
            d=documento(area);self.assertEqual(len(d['metadatos']['equipo']['competencias']),5 if area=='Psicología' else 0)
            self.assertEqual(d['formato'],'XXV' if area=='Trabajo Social' else 'XXIII')
            self.assertEqual(d['metadatos']['equipo']['grupal'][0]['Situación final'],'')
    def test_no_admite_alumnos_ajenos(self):
        with self.assertRaises(PermissionError):e.guardar_subgrupo(documento(),'Grupo',['A2'])
    def test_edicion_sin_duplicados_ni_perder_manual(self):
        d=e.guardar_subgrupo(documento(),'Subgrupo 1',['A1']);original=deepcopy(d)
        d['tablas']['dosificacion'].append({'Contextos':'Escuela','Actividades':'Actividad manual','Recursos':'Libro','Temporalidad':'Octubre'})
        d=e.guardar_sesion(d,sesion());sid=d['metadatos']['equipo']['sesiones'][0]['id']
        d=e.guardar_sesion(d,{**sesion(),'actividad':'Actividad corregida'},sid)
        self.assertEqual(len(d['metadatos']['equipo']['sesiones']),1)
        self.assertEqual(len([r for r in d['tablas']['dosificacion'] if r.get('_sesion_equipo')]),1)
        self.assertTrue(any(r['Actividades']=='Actividad manual' for r in d['tablas']['dosificacion']))
        self.assertEqual(original['metadatos']['equipo']['sesiones'],[])
        d=e.quitar_sesion(d,sid);self.assertFalse(any(r.get('_sesion_equipo') for r in d['tablas']['dosificacion']))
    def test_fecha_fuera_del_trimestre_y_contexto(self):
        d=e.guardar_subgrupo(documento(),'Subgrupo 1',['A1'])
        with self.assertRaises(ValueError):e.guardar_sesion(d,sesion('2027-01-01'))
        with self.assertRaises(ValueError):e.guardar_sesion(d,sesion(contexto='Consulta clínica'))
    def test_requisitos_psicologia_cubiertos_sin_resultados_ficticios(self):
        d=e.guardar_subgrupo(documento(),'Subgrupo 1',['A1'])
        for i in range(5):d=e.guardar_sesion(d,sesion('2026-10-'+str(7+i).zfill(2)))
        d=e.guardar_sesion(d,sesion('2026-10-14','Aula regular'))
        eq=d['metadatos']['equipo']
        for r in eq['competencias']:r.update({'Necesidad documentada':'Necesidad confirmada, E1','Descriptor de logro':'El alumno expresa su emoción.','Actividad prevista':'Sesión con tarjetas.'})
        eq['sugerencia_familia']='Preparar hoja de sugerencias para reconocer emociones en casa.'
        self.assertEqual(e.revisar(d),[])
        self.assertEqual(eq['grupal'][0]['Situación final'],'')
    def test_social_no_necesita_competencias_ni_cinco_sesiones(self):
        d=e.guardar_subgrupo(documento('Trabajo Social'),'Subgrupo 1',['A1'])
        d=e.guardar_sesion(d,{**sesion(contexto='Familia'),'competencias':[]})
        self.assertEqual(e.revisar(d),[])
        self.assertIn('Fecha',d['tablas']['dosificacion'][-1])
    def test_fuentes_de_zona_llegan_al_prompt_sin_identificadores(self):
        d=documento();contexto=contexto_ia(d);prompt=solicitud('Necesidad documentada, sin identificadores.','XXIII','Psicología',curriculo=contexto)
        self.assertIn('ZONA-PSICOLOGIA-2026',prompt);self.assertIn('cinco sesiones',prompt)
        self.assertNotIn('Alumno ficticio',prompt);self.assertNotIn('Escuela ficticia',prompt)
        c=contexto_ia(documento('Trabajo Social'));self.assertNotIn('ZONA-PSICOLOGIA-2026',{r['id'] for r in c['fuentes']})
    def test_salida_zona_conserva_nombre_y_no_exporta_id(self):
        tablas=e.tablas_salida(documento());titulo,headers,filas=tablas[-1]
        self.assertNotIn('ID_Alumno',headers);self.assertEqual(filas[0]['Nombre del alumno'],'Alumno ficticio')
    def test_recuperar_no_reemplaza_complementos(self):
        d=e.guardar_subgrupo(documento(),'Subgrupo 1',['A1']);self.assertEqual(e.preparar(d),d)
    def test_no_expone_enlaces_privados_de_drive(self):
        import json
        self.assertNotIn('drive.google.com',json.dumps(e.FUENTES))

if __name__=='__main__':unittest.main()

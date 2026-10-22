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
    def test_formato_oficial_psicologia_modelo_exacto(self):
        from unittest.mock import patch
        from services import planeacion_papel as papel, planeacion as s
        from documents.planeacion_papel import generar_pdf
        from io import BytesIO
        try:
            from pypdf import PdfReader
        except ImportError:
            import pymupdf
            class PdfReader:
                def __init__(self, stream):
                    doc = pymupdf.open(stream=stream.getvalue() if hasattr(stream, 'getvalue') else stream, filetype="pdf")
                    class _P:
                        def __init__(self, p): self.p = p
                        def extract_text(self): return self.p.get_text()
                    self.pages = [_P(p) for p in doc]

        d = documento('Psicología')
        d['id'] = 'doc-test-psicologia'
        with patch.object(s, 'autorizar', return_value={'cuenta':'psicologia@usaer.com','area':'Psicología','director':False}):
            spec = papel.hoja(d)
            
            # Verificar encabezado institucional de 4 filas
            self.assertEqual(len(spec['header']), 4)
            self.assertEqual(len(spec['header'][0]), 2)  # Zona, Servicio de Apoyo
            self.assertEqual(len(spec['header'][1]), 5)  # Escuela Regular, Fase, Grado, Grupo, Trimestre
            self.assertEqual(len(spec['header'][2]), 1)  # Nombre de los alumnos individuales
            self.assertEqual(len(spec['header'][3]), 2)  # Especialista, Función
            
            # Verificar Tabla 1: Competencias (3 columnas)
            t_comp = next(t for t in spec['tables'] if t['id'] == 'competencias')
            self.assertEqual(t_comp['headers'], ['Necesidades Educativas Específicas', 'Competencias emocionales', 'Descriptor de logro'])
            self.assertEqual(len(t_comp['rows']), 5)
            for row in t_comp['rows']:
                self.assertEqual(len(row), 3)
                
            # Verificar Tabla 2: Dosificación con los 5 contextos oficiales
            t_dosi = next(t for t in spec['tables'] if t['id'] == 'dosificacion')
            self.assertEqual(t_dosi['headers'], ['Contextos', 'Actividades', 'Temporalidad', 'Recursos'])
            ctxs = [row[0]['value'] for row in t_dosi['rows']]
            self.assertEqual(ctxs, ['Aula de Apoyo', 'Aula Regular', 'Escuela', 'Familia', 'Evaluación'])
            
            # Generar PDF y comprobar que son exactamente 2 páginas
            pdf_bytes = generar_pdf(d)
            reader = PdfReader(BytesIO(pdf_bytes))
            self.assertEqual(len(reader.pages), 2)
            p1_text = reader.pages[0].extract_text()
            p2_text = reader.pages[1].extract_text()
            self.assertIn('Planeación del Servicio de Apoyo de Educación Especial', p1_text)
            self.assertIn('Organización de las actividades de aprendizaje', p1_text)
            self.assertIn('Observaciones', p2_text)
            self.assertIn('Nombre y firma del Especialista', p2_text)
            self.assertIn('Director del Servicio de Apoyo', p2_text)

if __name__=='__main__':unittest.main()

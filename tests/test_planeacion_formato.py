from copy import deepcopy
from pathlib import Path
import unittest
from services import planeacion_formato as f
from tests.test_planeacion_panel import documento

class FormatoTests(unittest.TestCase):
    def test_edicion_conserva_identidad_y_trazas(self):
        d=documento();d=f.nueva_fila(d,'aprendizajes');d['tablas']['aprendizajes'][0]['_origenes']=[{'revision':'r1'}]
        antes=deepcopy(d);out=f.editar_celda(d,'aprendizajes',0,'Descriptor de logro','Describe dos objetos.')
        self.assertEqual(out['datos'],d['datos']);self.assertEqual(d,antes)
        self.assertEqual(out['tablas']['aprendizajes'][0]['_origenes'],[{'revision':'r1'}])
    def test_columnas_y_sesiones_protegidas(self):
        d=f.nueva_fila(documento(),'dosificacion');d['tablas']['dosificacion'][0]['_sesion_equipo']='s1'
        with self.assertRaises(ValueError):f.editar_celda(d,'dosificacion',0,'Actividades','Cambiar')
        with self.assertRaises(ValueError):f.quitar_fila(d,'dosificacion',0)
        with self.assertRaises(ValueError):f.editar_celda(d,'dosificacion',0,'ID_Alumno','A2')
    def test_guia_no_cambia_alumnos_ni_otras_secciones(self):
        d=documento();d['metadatos']['modalidad_planeacion']='grupal'
        base=[{'ID_Alumno':'A1','Nombre alumno':'Ficticio','Discapacidad o condición':'Registro','Aprendizaje':''}]
        out=f.editar_guia(d,{'edited_rows':{0:{'Nombre alumno':'Otro','ID_Alumno':'A2','Aprendizaje':'Leer con tarjetas'}}},base)
        row=out['metadatos']['guia_grupal_manual']['filas'][0]
        self.assertEqual(row['ID_Alumno'],'A1');self.assertEqual(row['Nombre alumno'],'Ficticio');self.assertEqual(out['tablas'],d['tablas'])
        d['metadatos']['guia_compartida']={'documento':'otro'}
        with self.assertRaises(PermissionError):f.editar_guia(d,{},base)
    def test_formatos_xxi_xxiii_xxv(self):
        from services.planeacion_modelo import FORMATOS
        for fmt in FORMATOS:
            d=documento(fmt)
            for tabla,cols in FORMATOS[fmt]['tablas'].items():
                out=f.nueva_fila(d,tabla);self.assertEqual(set(out['tablas'][tabla][-1]),set(cols))
                self.assertEqual(f.quitar_fila(out,tabla,len(out['tablas'][tabla])-1)['tablas'][tabla],d['tablas'][tabla])

class FormatoUITests(unittest.TestCase):
    def setUp(self):
        from services import planeacion as s
        from ui import planeacion_generacion as generador
        self.originales={k:getattr(s,k) for k in ('identidad','padron_autorizado','evidencias','guardar','listar','refrescar','versiones_actuales','guardar_aportacion')}
        self.escuelas=s.repo.escuelas;self.generar=generador.generar_completa
    def tearDown(self):
        from services import planeacion as s
        from ui import planeacion_generacion as generador
        for k,v in self.originales.items():setattr(s,k,v)
        s.repo.escuelas=self.escuelas;generador.generar_completa=self.generar
    def test_cuatro_perfiles_editan_mismo_documento_y_recuperan(self):
        from streamlit.testing.v1 import AppTest
        for area in ['Aprendizaje','Psicología','Comunicación','Trabajo Social']:
            app=AppTest.from_file(str(Path(__file__).with_name('fixture_planeacion_completa.py')),default_timeout=30).run()
            app.radio[0].set_value(area).run()
            next(m for m in app.multiselect if m.label=='Alumnos de atención grupal de la misma escuela').set_value(['A1']).run()
            next(b for b in app.button if b.label=='Crear y guardar borrador').click().run()
            self.assertFalse(app.exception,area)
            self.assertEqual(next(r for r in app.radio if r.label=='Cómo quieres trabajar').value,'Mi formato')
            titulo='Guía de planeación para maestras de apoyo' if area=='Aprendizaje' else 'Guía de planeación para el equipo paradocente'
            self.assertTrue(any(titulo in m.value and 'Mi formato' in m.value for m in app.markdown))
            tabla='barreras' if area=='Trabajo Social' else 'aprendizajes'
            next(b for b in app.button if b.label=='Añadir fila · '+f.TITULOS[tabla]).click().run()
            self.assertFalse(app.exception,area)
            campo='Apoyos y/o ajustes razonables' if area=='Trabajo Social' else 'Descriptor de logro'
            next(t for t in app.text_area if t.label==campo).set_value('Texto revisado en el formato.').run()
            next(b for b in app.button if b.label=='Guardar borrador').click().run()
            doc=app.session_state.versiones_ficticias[-1];did=doc['id']
            self.assertEqual(doc['tablas'][tabla][-1][campo],'Texto revisado en el formato.')
            next(r for r in app.radio if r.label=='Cómo quieres trabajar').set_value('Edición guiada').run()
            next(r for r in app.radio if r.label=='Cómo quieres trabajar').set_value('Mi formato').run()
            self.assertFalse(app.exception,area);self.assertEqual(app.session_state.versiones_ficticias[-1]['id'],did)
            next(b for b in app.button if b.label=='Abrir documento').click().run()
            self.assertFalse(app.exception,area)
            self.assertEqual(next(t for t in app.text_area if t.label==campo).value,'Texto revisado en el formato.')
            self.assertEqual(app.session_state.llamadas_ficticias,0)
            next(t for t in app.text_area if t.label=='Fecha derivación').set_value('Fecha documentada de ejemplo').run()
            self.assertFalse(app.exception,area)
            self.assertEqual(app.session_state.versiones_ficticias[-1]['metadatos']['guia_grupal_manual']['filas'][0]['Fecha derivación'],'Fecha documentada de ejemplo')

if __name__=='__main__':unittest.main()

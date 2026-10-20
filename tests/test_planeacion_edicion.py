"""Edición, copias y propuestas selectivas sin red ni alumnos reales."""
from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import patch
import pandas as pd
from services import planeacion as s,planeacion_edicion as e
from services.planeacion_modelo import crear_plantilla
from tests.test_planeacion_completa import documento
from tests import test_planeacion_simple as simple


class EdicionTests(unittest.TestCase):
    def setUp(self):
        self.actor={'cuenta':'cuenta-ficticia','nombre':'Autor ficticio','area':'Aprendizaje','rol':'APOYO','perfil':None,'director':False}
        self.auth=patch.object(s,'autorizar',return_value=self.actor);self.auth.start();self.addCleanup(self.auth.stop)

    def doc(self,area='Aprendizaje',formato=None):
        d=documento(area);d.update(estado='VALIDADO',revision='r1')
        if formato=='XXI':
            a={'ID_Alumno':'A1','Nombre_Completo':'Alumno ficticio Uno','ID_Escuela':'E1','Nombre_Escuela':'Escuela ficticia','Grado':'5','Tipo_Atencion':'Individual'}
            d=crear_plantilla('XXI',['A1'],[a],autor='Autor ficticio',funcion='Aprendizaje');d.update(id='doc-pi',cuenta='cuenta-ficticia',revision='r1',estado='VALIDADO')
            d['tablas']['barreras']=[{'BAP':'Barrera privada','Acciones para minimizarla o eliminarla':'Actividad prevista con tarjetas'}]
        else:d['tablas']['dosificacion']=[{'Contextos':'Aula regular','Actividades':'Actividad primera','Recursos':'Tarjetas'},{'Contextos':'Aula regular','Actividades':'Actividad segunda','Recursos':'Fichas'}]
        d['metadatos']['firma_aprobada_por']='Dirección'
        return d

    def test_borrador_preserva_identidad_e_historia(self):
        for area in ('Aprendizaje','Psicología','Comunicación','Trabajo Social'):
            d=self.doc(area);prev=deepcopy(d);new=e.borrador(d)
            self.assertEqual(new['estado'],'BORRADOR');self.assertEqual(d,prev)
            self.assertEqual(new['datos'],d['datos']);self.assertEqual(new['revision'],'r1')
            self.assertEqual(new['metadatos']['firma_aprobada_por'],'')

    def test_reordenar_solo_filas_sin_cambiar_contenido(self):
        d=self.doc();new=e.reordenar(d,'dosificacion',0,1)
        self.assertEqual(new['tablas']['dosificacion'],list(reversed(d['tablas']['dosificacion'])))
        self.assertEqual(new['datos'],d['datos'])
        d['tablas']['dosificacion'][1]['_sesion_equipo']='s1'
        with self.assertRaises(ValueError):e.reordenar(d,'dosificacion',0,1)

    def test_copia_cuatro_perfiles_y_pi_sin_arrastrar_hallazgos(self):
        for area,fmt in [('Aprendizaje',None),('Psicología',None),('Comunicación',None),('Trabajo Social',None),('Aprendizaje','XXI')]:
            d=self.doc(area,fmt);prev=deepcopy(d)
            filas=[{'ID_Alumno':'A1','Nombre_Completo':'Alumno ficticio Uno','ID_Escuela':'E1','Nombre_Escuela':'Escuela ficticia','Grado':'5','Tipo_Atencion':'Individual' if fmt else 'Grupal'},
                   {'ID_Alumno':'A2','Nombre_Completo':'Alumno ficticio Dos','ID_Escuela':'E1','Nombre_Escuela':'Escuela ficticia','Grado':'3','Tipo_Atencion':'Grupal'}]
            self.actor['area']=area
            with patch.object(s,'identidad',return_value=self.actor),patch.object(s,'padron_autorizado',return_value=pd.DataFrame(filas)),patch.object(s.repo,'escuelas',return_value=pd.DataFrame()),patch.object(s,'preparar_contexto',side_effect=lambda x:x):
                nuevo=e.copiar(d,['A1','A2'],2026,2,grupal=True,incluir_individuales=True)
            self.assertNotEqual(nuevo['id'],d['id']);self.assertEqual(nuevo['revision'],'')
            self.assertEqual(nuevo['formato'],'XXV' if area=='Trabajo Social' else 'XXIII')
            self.assertEqual(len(nuevo['datos']['Alumnos']),2)
            self.assertFalse(nuevo['metadatos']['fuentes'])
            self.assertNotIn('aportaciones_equipo',nuevo['metadatos'])
            self.assertEqual(nuevo['metadatos']['copia_de']['documento'],d['id'])
            self.assertEqual(d,prev)

    def test_copia_rechaza_otra_escuela_y_multiples_en_pi(self):
        d=self.doc();frame=pd.DataFrame([{'ID_Alumno':'A2','ID_Escuela':'E2'},{'ID_Alumno':'A1','ID_Escuela':'E1'}])
        with patch.object(s,'padron_autorizado',return_value=frame):
            with self.assertRaises(PermissionError):e.copiar(d,['A2'],2026,1)
            with self.assertRaises(PermissionError):e.copiar(d,['FUERA'],2026,1)
        frame.loc[0,'ID_Escuela']='E1'
        with patch.object(s,'padron_autorizado',return_value=frame):
            with self.assertRaises(ValueError):e.copiar(self.doc(formato='XXI'),['A1','A2'],2026,1)

    def test_copia_individual_trimestral_multiple_preserva_original(self):
        d=self.doc();prev=deepcopy(d)
        frame=pd.DataFrame([{'ID_Alumno':i,'Nombre_Completo':'Alumno ficticio '+i,'ID_Escuela':'E1','Nombre_Escuela':'Escuela ficticia','Grado':'3','Tipo_Atencion':'Individual'} for i in ['A1','A2']])
        with patch.object(s,'identidad',return_value=self.actor),patch.object(s,'padron_autorizado',return_value=frame),patch.object(s.repo,'escuelas',return_value=pd.DataFrame()),patch.object(s,'preparar_contexto',side_effect=lambda x:x):
            nuevo=e.copiar(d,['A1','A2'],2026,2)
        self.assertEqual(nuevo['metadatos']['modalidad_planeacion'],'individual')
        self.assertEqual(len(nuevo['datos']['Alumnos']),2)
        self.assertNotEqual(nuevo['id'],d['id']);self.assertEqual(d,prev)

    def test_recuperacion_mantiene_revision_actual_y_aportes(self):
        actual=self.doc();actual['revision']='r2';actual['metadatos']['aportaciones_equipo']={'psic':'Actual'}
        anterior=deepcopy(actual);anterior['revision']='r1';anterior['metadatos']['aportaciones_equipo']={'psic':'Anterior'}
        anterior['tablas']['dosificacion'][0]['Actividades']='Redacción anterior'
        new=e.recuperar(actual,anterior)
        self.assertEqual(new['revision'],'r2');self.assertEqual(new['estado'],'BORRADOR')
        self.assertEqual(new['metadatos']['aportaciones_equipo'],actual['metadatos']['aportaciones_equipo'])
        anterior['id']='otro'
        with self.assertRaises(PermissionError):e.recuperar(actual,anterior)

    def test_ia_solo_sustituye_celdas_elegidas_y_rechaza_version_obsoleta(self):
        for fmt in (None,'XXI'):
            d=self.doc(formato=fmt);ref=next(iter(e.actividades(d)))
            propuesta={'huella':e.huella(d),'cambios':[{'referencia':ref,'actividad':'Nueva propuesta revisada'}]}
            new=e.aplicar_revision(d,propuesta)
            target=e.actividades(new)[ref]
            self.assertEqual(target['texto'],'Nueva propuesta revisada')
            self.assertEqual(new['datos'],d['datos']);self.assertEqual(new['textos'],d['textos'])
            d['textos']['Edición posterior']='conservar'
            with self.assertRaises(ValueError):e.aplicar_revision(d,propuesta)

    def test_ia_vinculada_actualiza_sesion_sin_duplicar(self):
        from services.planeacion_equipo import preparar,guardar_subgrupo,guardar_sesion
        d=guardar_subgrupo(preparar(documento('Comunicación')),'Subgrupo',['A1'])
        d=guardar_sesion(d,{'fecha':'2026-10-15','subgrupo':'Subgrupo','contexto':'Aula regular','objetivo':'Objetivo','actividad':'Original','apoyos':'Tarjetas','recursos':'Fichas','seguimiento':'Observación','competencias':[]})
        ref=next(k for k in e.actividades(d) if k.startswith('sesion:'))
        new=e.aplicar_revision(d,{'huella':e.huella(d),'cambios':[{'referencia':ref,'actividad':'Reformulación'}]})
        self.assertEqual(len(new['metadatos']['equipo']['sesiones']),1)
        vinculadas=[r for r in new['tablas']['dosificacion'] if r.get('_sesion_equipo')]
        self.assertEqual(len(vinculadas),1)
        self.assertIn('Reformulación',vinculadas[0]['Actividades'])

    def test_preparacion_minimiza_y_no_llama_motor(self):
        d=self.doc();ref=next(iter(e.actividades(d)))
        d['tablas']['dosificacion'][0]['Actividades']='Alumno ficticio Uno participa con tarjetas'
        with patch('ai.planeacion.proponer') as motor:
            req=e.preparar_revision(d,[ref])
        self.assertNotIn('Alumno ficticio Uno',req['resumen']);motor.assert_not_called()

    def test_generacion_valida_referencias_y_no_envia_campos_libres_ocultos(self):
        d=self.doc();ref=next(iter(e.actividades(d)));req=e.preparar_revision(d,[ref])
        def motor(*args,**kwargs):
            self.assertNotIn('NO ENVIAR',kwargs['_prompt'])
            validar=kwargs['_validador']
            with self.assertRaises(ValueError):validar({'cambios':[{'referencia':'AJENO','actividad':'Texto'}]})
            return validar({'cambios':[{'referencia':ref,'actividad':'Texto válido'}]})
        with patch('services.curriculo.contexto_ia',return_value={'fuentes':[],'contextualizacion_docente':'NO ENVIAR','adaptaciones_docentes':{'a':'NO ENVIAR'}}),patch('ai.planeacion.proponer',side_effect=motor) as m:
            result=e.generar_revision(d,req,'Resumen anónimo revisado')
        self.assertEqual(len(result['cambios']),1);self.assertEqual(m.call_count,1)

    def test_copia_pi_no_sobrescribe_el_pi_existente(self):
        d=self.doc(formato='XXI')
        frame=pd.DataFrame([{'ID_Alumno':'A1','Nombre_Completo':'Alumno ficticio Uno','ID_Escuela':'E1','Nombre_Escuela':'Escuela ficticia','Grado':'5','Tipo_Atencion':'Individual'}])
        with patch.object(s,'identidad',return_value=self.actor),patch.object(s,'padron_autorizado',return_value=frame),patch.object(s,'compartidos',return_value=[d]):
            with self.assertRaisesRegex(ValueError,'Ya existe'):e.copiar(d,['A1'],2026,1)

    def test_sin_autorizacion_no_hay_edicion_ni_copia(self):
        d=self.doc()
        with patch.object(s,'autorizar',side_effect=PermissionError):
            with self.assertRaises(PermissionError):e.borrador(d)
            with self.assertRaises(PermissionError):e.copiar(d,['A1'],2026,1)

    def test_no_reformula_ni_restaura_aportes_ajenos(self):
        d=self.doc(formato='XXI')
        d['tablas']['barreras'].append({'Acciones para minimizarla o eliminarla':'Aporte actual','_aporte':'actual'})
        anterior=deepcopy(d);anterior['tablas']['barreras'][-1]['Acciones para minimizarla o eliminarla']='Aporte anterior'
        self.assertEqual(len(e.actividades(d)),1)
        restaurado=e.recuperar(d,anterior)
        self.assertEqual(restaurado['tablas']['barreras'][-1]['Acciones para minimizarla o eliminarla'],'Aporte actual')

    def test_abrir_edicion_no_descarta_cambios_pendientes(self):
        from ui import planeacion_edicion as ui,planeacion as u
        from ui import planeacion_simple as simple_ui
        doc=self.doc();editado=deepcopy(doc);editado['textos']['Observaciones']='Pendiente que debe conservarse'
        state={'base_grupal_doc':editado,'base_grupal_pending':True}
        def guardar(prefix):
            state[prefix+'_pending']=False;return True
        with patch.object(ui.st,'session_state',state),patch.object(u,'_persist',side_effect=guardar),patch.object(s,'padron_autorizado',return_value=pd.DataFrame()),patch.object(simple_ui,'_abrir') as abrir:
            ui.abrir_guardada('base',doc)
        self.assertEqual(abrir.call_args.args[2]['textos']['Observaciones'],'Pendiente que debe conservarse')


class EdicionUITests(unittest.TestCase):
    setUp=simple.RecorridoTests.setUp
    tearDown=simple.RecorridoTests.tearDown
    abrir=simple.RecorridoTests.abrir
    paso=simple.RecorridoTests.paso

    def test_editar_guardada_en_cuatro_perfiles_y_copia_recuperable(self):
        for area in ('Aprendizaje','Psicología','Comunicación','Trabajo Social'):
            with self.subTest(area=area):
                app=self.abrir(area);old=app.session_state.versiones_ficticias[-1]['id']
                self.paso(app,0)
                next(b for b in app.button if b.label=='Editar planeación').click().run()
                self.assertFalse(app.exception)
                self.assertTrue(any(b.label=='Guardar borrador' for b in app.button))
                next(w for w in app.selectbox if w.label=='¿Qué quieres modificar?').set_value('Alumnos o periodo · copia adaptada').run()
                next(c for c in app.checkbox if c.label.startswith('Revisé que las actividades')).check().run()
                next(b for b in app.button if b.label=='Crear copia adaptada en borrador').click().run()
                self.assertFalse(app.exception)
                nuevo=app.session_state.versiones_ficticias[-1]
                if area=='Aprendizaje':
                    self.assertEqual(nuevo['id'],old)
                    self.assertTrue(any('no se duplica' in w.value for w in app.warning))
                else:
                    self.assertNotEqual(nuevo['id'],old)
                    self.assertEqual(nuevo['metadatos']['copia_de']['documento'],old)
                self.assertEqual(app.session_state.llamadas_ficticias,0)

    def test_fallo_ia_no_modifica_formato(self):
        app=self.abrir();self.paso(app,2)
        next(b for b in app.button if b.label.startswith('Añadir fila · Organización')).click().run()
        next(t for t in app.text_area if t.label=='Actividades').set_value('Inicio con tarjetas; desarrollo guiado; cierre con registro.').run()
        next(b for b in app.button if b.label=='Guardar borrador').click().run()
        next(w for w in app.selectbox if w.label=='¿Qué quieres modificar?').set_value('Reformular actividades con IA').run()
        next(m for m in app.multiselect if m.label.startswith('Actividades por reformular')).set_value(['dosificacion:0:Actividades']).run()
        next(c for c in app.checkbox if c.label.startswith('Revisé este resumen')).check().run()
        previo=deepcopy(app.session_state.versiones_ficticias[-1])
        with patch.object(e,'generar_revision',side_effect=RuntimeError('IA no disponible')):
            next(b for b in app.button if b.label=='Preparar reformulación de actividades').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state.versiones_ficticias[-1],previo)
        self.assertTrue(any(b.label=='Guardar borrador' for b in app.button))

    def test_reintento_de_copia_no_cambia_su_id_tras_fallo(self):
        app=self.abrir()
        next(w for w in app.selectbox if w.label=='¿Qué quieres modificar?').set_value('Alumnos o periodo · copia adaptada').run()
        next(w for w in app.selectbox if w.label=='Trimestre de la copia').set_value(2).run()
        next(c for c in app.checkbox if c.label.startswith('Revisé que las actividades')).check().run()
        from ui import planeacion_edicion as ui
        pending=[]
        def fallo(prefix,doc):
            pending.append(doc['id']);raise RuntimeError('Guardado pendiente ficticio')
        with patch.object(ui,'_abrir_copia',side_effect=fallo):
            for _ in range(2):
                next(b for b in app.button if b.label=='Crear copia adaptada en borrador').click().run()
                self.assertFalse(app.exception)
        self.assertEqual(len(pending),2);self.assertEqual(pending[0],pending[1])

    def test_fallo_historial_conserva_acceso_al_formato(self):
        app=self.abrir();self.paso(app,2)
        with patch.object(s,'listar',side_effect=RuntimeError('Lectura no disponible')):
            next(w for w in app.selectbox if w.label=='¿Qué quieres modificar?').set_value('Recuperar una versión anterior').run()
        self.assertFalse(app.exception)
        self.assertTrue(any(b.label=='Guardar borrador' for b in app.button))

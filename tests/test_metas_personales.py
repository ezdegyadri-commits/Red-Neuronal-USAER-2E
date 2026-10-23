from copy import deepcopy
from io import BytesIO
import json
from unittest import TestCase
from unittest.mock import patch
import pandas as pd
from pypdf import PdfReader
from streamlit.testing.v1 import AppTest
from services import metas_personales as s
from ui import metas_personales as ui

ACTOR={'cuenta':'docente-ficticia','nombre':'Docente ficticia','rol':'APOYO','area':'Aprendizaje','director':False}
PADRON=[{'ID_Alumno':'A1','ID_Escuela':'ESC-001','Nombre_Escuela':'Damián Carmona','Nombre_Completo':'Alumno ficticio','Grado':'1°','Grupo':'A'}]


class GuardadoTests(TestCase):
    def setUp(self):
        self.rows=[];self.options=[]
        outer=self
        class Sheet:
            def row_values(self,n):return s.HEADERS
            def append_rows(self,rows,value_input_option):
                outer.options.append(value_input_option)
                outer.rows.extend(dict(zip(s.HEADERS,row)) for row in rows)
        self.patches=[patch.object(s.planes,'identidad',return_value=ACTOR),patch.object(s.planes,'padron_autorizado',return_value=pd.DataFrame(PADRON)),
                      patch.object(s.repo,'read',side_effect=lambda name:pd.DataFrame(deepcopy(self.rows))),patch.object(s,'ensure_headers',return_value=(Sheet(),s.HEADERS)),patch.object(s,'clear_cache')]
        for p in self.patches:p.start()
        self.addCleanup(lambda:[p.stop() for p in reversed(self.patches)])

    def filas(self,meta='Implementar apoyo visual'):
        return [{'ID_Alumno':'A1','Metas':meta,'Recursos necesarios':'Tarjetas'}]

    def test_guardado_recuperacion_versiones_y_reintento_idempotente(self):
        a=s.guardar('ESC-001','2026-10-23',self.filas());original=deepcopy(self.rows[0])
        self.assertEqual(s.guardar('Damián Carmona','2026-10-23',self.filas()),a)
        self.assertEqual(len(self.rows),1)
        b=s.guardar('ESC-001','2026-10-23',self.filas('Meta corregida'),a['Revision'])
        self.assertEqual(len(self.rows),2);self.assertEqual(self.rows[0],original)
        self.assertEqual(s.recuperar('ESC-001','2026-10-23'),b)
        self.assertEqual(self.options,['RAW','RAW'])
        self.assertEqual(b['Filas'][0]['Alumno'],'Alumno ficticio')

    def test_acceso_solo_propietario_y_alumnos_de_su_asignacion(self):
        s.guardar('ESC-001','2026-10-23',self.filas())
        with patch.object(s.planes,'identidad',return_value={**ACTOR,'cuenta':'otra'}):self.assertIsNone(s.recuperar('ESC-001','2026-10-23'))
        with self.assertRaises(PermissionError):s.recuperar('ESC-006','2026-10-23')
        with self.assertRaises(PermissionError):s.guardar('ESC-001','2026-10-23',[{'ID_Alumno':'OTRO','Metas':'Ajena'}])
        self.assertEqual(len(self.rows),1)

    def test_conflicto_concurrente_y_texto_literal_sin_sobrescribir(self):
        a=s.guardar('ESC-001','2026-10-23',self.filas())
        s.guardar('ESC-001','2026-10-23',self.filas('Cambio remoto'),a['Revision'])
        with self.assertRaises(RuntimeError):s.guardar('ESC-001','2026-10-23',self.filas('Texto local'),a['Revision'])
        self.assertEqual(len(self.rows),2)
        s.guardar('ESC-001','2026-10-24',self.filas('=SUM(1,2)'))
        self.assertEqual(json.loads(self.rows[-1]['Contenido'])['Filas'][0]['Metas'],'=SUM(1,2)')

    def test_fallo_de_confirmacion_no_crea_exito_y_reintento_no_duplica(self):
        original=s._versiones;calls=0
        def leer(*a):
            nonlocal calls
            calls+=1
            if calls==2:raise TimeoutError('Fallo de lectura')
            return original(*a)
        with patch.object(s,'_versiones',side_effect=leer):
            with self.assertRaises(TimeoutError):s.guardar('ESC-001','2026-10-23',self.filas())
        self.assertEqual(len(self.rows),1)
        self.assertEqual(s.guardar('ESC-001','2026-10-23',self.filas())['Filas'][0]['Metas'],self.filas()[0]['Metas'])
        self.assertEqual(len(self.rows),1)

    def test_tabla_y_pdf_conservan_tres_columnas_sin_firma_directiva(self):
        from documents.metas_personales import generar_pdf
        data=generar_pdf(s.guardar('ESC-001','2026-10-23',self.filas()))
        texto='\n'.join(p.extract_text() for p in PdfReader(BytesIO(data)).pages)
        for value in ('METAS PERSONALES','Alumno ficticio','Implementar apoyo visual','Recursos necesarios'):self.assertIn(value,texto)
        self.assertNotIn('Director de la USAER',texto)


class InterfazTests(TestCase):
    def abrir(self,**state):
        from pathlib import Path
        app=AppTest.from_file(str(Path(__file__).parent/'fixtures'/'juntas_academicas_app.py'),default_timeout=30)
        for key,value in state.items():app.session_state[key]=value
        return app.run()

    def test_reabrir_modulo_recupera_borrador_pendiente_no_base_antigua(self):
        from hashlib import sha256
        key='metas_'+sha256(json.dumps(['cuenta-ficticia','ESC-001','2026-10-23']).encode()).hexdigest()[:20]
        capture={'Cuenta':'cuenta-ficticia','Docente':'Docente ficticia','Escuela':'Damián Carmona','ID_Escuela':'ESC-001','Fecha_Sesion':'2026-10-23',
                 'Filas':[{'ID_Alumno':'A1','Metas':'Avance pendiente','Recursos necesarios':'Tarjetas'}]}
        app=self.abrir(**{key+'_borrador':capture,key+'_pending':True,'qa_fallo':True})
        next(x for x in app.selectbox if x.label=='Alumno de mi asignación').select('A1').run()
        self.assertFalse(app.exception)
        self.assertEqual(next(x for x in app.text_area if x.label=='Metas para este alumno').value,'Avance pendiente')

    def test_captura_precargada_se_guarda_y_no_duplica_en_rerun(self):
        app=self.abrir()
        next(x for x in app.selectbox if x.label=='Alumno de mi asignación').select('A1').run()
        next(x for x in app.text_area if x.label=='Metas para este alumno').set_value('Meta de prueba').run()
        next(x for x in app.button if x.label=='Guardar instrumento').click().run()
        self.assertFalse(app.exception);self.assertEqual(app.session_state.qa_envios,1)
        app.run()
        self.assertEqual(app.session_state.qa_envios,1)
        self.assertEqual(next(x for x in app.text_area if x.label=='Metas para este alumno').value,'Meta de prueba')

    def test_render_precarga_escuela_y_campos_sin_escribir(self):
        app=self.abrir()
        self.assertFalse(app.exception)
        self.assertFalse(any(x.label=='Escuela asignada' for x in app.selectbox))
        self.assertEqual(len(next(x for x in app.selectbox if x.label=='Alumno de mi asignación').options),2)
        self.assertEqual(app.session_state.qa_envios,0)

    def test_error_conserva_borrador_y_cerrar_requiere_guardado_o_respaldo(self):
        captura={'Cuenta':ACTOR['cuenta'],'ID_Escuela':'ESC-001','Fecha_Sesion':'2026-10-23','Filas':[{'ID_Alumno':'A1','Metas':'Texto protegido','Recursos necesarios':'Tarjetas'}]}
        state={'usuario':ACTOR['cuenta'],'metas_test_pending':True,'metas_test_borrador':deepcopy(captura),'metas_test_doc':{}}
        with patch.object(ui.st,'session_state',state),patch.object(ui.s,'identidad',return_value=ACTOR),patch.object(ui.s,'guardar',side_effect=ConnectionError()),patch.object(ui.st,'warning'),patch.object(ui.st,'download_button'),patch.object(ui.st,'button',return_value=False),patch.object(ui.st,'checkbox',return_value=False):
            self.assertFalse(ui._guardar_pendiente('metas_test',manual=True))
            self.assertTrue(state['metas_test_pending']);self.assertEqual(state['metas_test_borrador'],captura)
            self.assertFalse(ui.proteger_salida('salir'))

    def test_autoguardado_agrupa_sin_enviar_cada_celda(self):
        state={'metas_test_pending':True,'metas_test_ultimo_intento':100,'metas_test_borrador':{'Cuenta':ACTOR['cuenta']}}
        with patch.object(ui.st,'session_state',state),patch.object(ui.time,'monotonic',return_value=104),patch.object(ui.s,'guardar') as guardar:
            self.assertFalse(ui._guardar_pendiente('metas_test'));guardar.assert_not_called()

    def test_cerrar_confirmado_limpia_capturas_del_dispositivo_compartido(self):
        from ui import auth
        state={'usuario':ACTOR['cuenta'],'autenticado':True,'metas_test_borrador':{'dato':'privado'},'metas_test_pending':False}
        with patch.object(auth.st,'session_state',state),patch.object(auth.st,'rerun'):
            auth._cerrar()
        self.assertFalse(any(k.startswith('metas_') for k in state))
        self.assertNotIn('usuario',state)

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
                      patch.object(s.repo,'read',side_effect=lambda name:pd.DataFrame(deepcopy(self.rows))),patch.object(s,'ensure_headers',return_value=Sheet()),patch.object(s,'clear_cache')]
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
    def test_reabrir_modulo_recupera_borrador_pendiente_no_base_antigua(self):
        app=AppTest.from_string('''
import streamlit as st
import pandas as pd
from unittest.mock import patch
from hashlib import sha256
import json
from tests.test_metas_personales import ACTOR,PADRON
from services import metas_personales as s
from ui.metas_personales import page
key='metas_'+sha256(json.dumps([ACTOR['cuenta'],'ESC-001','2026-10-23']).encode()).hexdigest()[:20]
st.session_state[key+'_base_editor']=[{'Alumno':None,'Metas':'','Recursos necesarios':''}]
st.session_state[key+'_labels']={'A1':'Alumno ficticio · 1° A'}
st.session_state[key+'_borrador']={'Cuenta':ACTOR['cuenta'],'Filas':[{'ID_Alumno':'A1','Metas':'Avance pendiente','Recursos necesarios':'Tarjetas'}]}
with patch.object(s.planes,'identidad',return_value=ACTOR),patch.object(s.planes,'padron_autorizado',return_value=pd.DataFrame(PADRON)),patch.object(s,'recuperar',return_value=None),patch.object(s,'guardar',side_effect=ConnectionError()):page()
''',default_timeout=30).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.dataframe[0].value.iloc[0]['Metas'],'Avance pendiente')

    def test_captura_precargada_se_guarda_y_no_duplica_en_rerun(self):
        app=AppTest.from_string('''
import streamlit as st
import pandas as pd
from unittest.mock import patch
from hashlib import sha256
import json
from tests.test_metas_personales import ACTOR,PADRON
from services import metas_personales as s
from ui.metas_personales import page
key='metas_'+sha256(json.dumps([ACTOR['cuenta'],'ESC-001','2026-10-23']).encode()).hexdigest()[:20]
st.session_state.setdefault(key+'_base_editor',[{'Alumno':'Alumno ficticio · 1° A','Metas':'Meta de prueba','Recursos necesarios':'Tarjetas'}])
st.session_state.setdefault(key+'_labels',{'A1':'Alumno ficticio · 1° A'})
st.session_state.setdefault('envios',[])
def guardar(escuela,fecha,filas,revision):
    st.session_state.envios.append(filas)
    return {'Revision':'r1','Guardado_En':'confirmado','Filas':[{**r,'Alumno':'Alumno ficticio'} for r in filas]}
with patch.object(s.planes,'identidad',return_value=ACTOR),patch.object(s.planes,'padron_autorizado',return_value=pd.DataFrame(PADRON)),patch.object(s,'recuperar',return_value=None),patch.object(s,'guardar',side_effect=guardar):page()
''',default_timeout=30).run()
        self.assertFalse(app.exception);self.assertEqual(len(app.session_state.envios),1)
        self.assertEqual(app.session_state.envios[0][0]['ID_Alumno'],'A1')
        app.run();self.assertFalse(app.exception);self.assertEqual(len(app.session_state.envios),1)
        self.assertEqual(app.dataframe[0].value.iloc[0]['Metas'],'Meta de prueba')

    def test_render_precarga_escuela_y_campos_sin_escribir(self):
        app=AppTest.from_string('''
from unittest.mock import patch
import pandas as pd
from tests.test_metas_personales import ACTOR,PADRON
from services import metas_personales as s
from ui.metas_personales import page
with patch.object(s.planes,'identidad',return_value=ACTOR),patch.object(s.planes,'padron_autorizado',return_value=pd.DataFrame(PADRON)),patch.object(s,'recuperar',return_value=None),patch.object(s,'guardar',side_effect=AssertionError('No escribir al abrir')):
    page()
''',default_timeout=30).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.selectbox[0].options,['Damián Carmona'])
        self.assertEqual(list(app.dataframe[0].value.columns),['Alumno','Metas','Recursos necesarios'])
        self.assertEqual(len(app.dataframe[0].value),8)

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

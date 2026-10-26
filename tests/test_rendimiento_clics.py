"""Evita carga global por clic; todos los datos y componentes son ficticios."""
from copy import deepcopy
from unittest import TestCase
from unittest.mock import Mock, patch
import pandas as pd
from services import planeacion as s
from ui import escritura
from tests.test_planeacion_grupo_unico import duplicados
from tests.test_planeacion_panel import ALUMNO, ACTOR


class ClicsTests(TestCase):
    def test_diccionario_solo_se_envia_hasta_confirmacion_del_navegador(self):
        state={};render=Mock(return_value={'evento':None})
        with patch.object(escritura.st,'session_state',state),patch.object(escritura,'_componente',return_value=render),patch.object(escritura,'_palabras',return_value=['usaer']) as words:
            escritura.activar_revision();self.assertEqual(render.call_args.kwargs['data'],{'words':['usaer']})
            state['corrector_global']={'evento':{'tipo':'diccionario_listo'}};escritura._evento()
            for _ in range(30):escritura.activar_revision()
            self.assertEqual(render.call_args.kwargs['data'],{});self.assertEqual(words.call_count,1)
            state['corrector_global']={'evento':{'tipo':'pedir_diccionario'}};escritura._evento()
            escritura.activar_revision();self.assertEqual(words.call_count,2)

    def test_consulta_abierta_omite_otros_grados_y_reutiliza_matricula(self):
        a,b=duplicados();otras=[]
        for i in range(80):
            d=deepcopy(a);d['id']='otro-'+str(i);d['datos']['Trimestre']='otro-'+str(i);otras.append(d)
        from services.planeacion_modalidad import guia_grupal
        with patch.object(s,'identidad',return_value=ACTOR),patch.object(s,'versiones_actuales',return_value=[a,b]+otras),patch.object(s,'padron_autorizado',return_value=pd.DataFrame([ALUMNO])) as padron:
            result=s.compartidos(documento=a['id'])
            self.assertEqual([d['id'] for d in result],[a['id']]);self.assertEqual(padron.call_count,1)
            self.assertEqual(guia_grupal(result[0])['filas'][0]['Comunicación'],'Actividad de comunicación')
            self.assertEqual(s.compartidos(documento='no-existe'),[])

    def test_filtro_de_rendimiento_no_autoriza_alumno_ajeno(self):
        a,b=duplicados()
        with patch.object(s,'identidad',return_value=ACTOR),patch.object(s,'versiones_actuales',return_value=[a,b]),patch.object(s,'padron_autorizado',return_value=pd.DataFrame([ALUMNO])),patch.object(s,'autorizar',side_effect=PermissionError('Sin permiso')):
            self.assertEqual(s.compartidos(documento=a['id']),[])

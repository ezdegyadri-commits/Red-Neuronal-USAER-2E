"""Evita que una plantilla nueva oculte el avance; datos exclusivamente ficticios."""
from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch
import pandas as pd
from services import planeacion_recuperacion as r
from tests.test_planeacion_cero_friccion import individual,ACTOR


def ejemplo(did='con-avance',fecha='2026-10-19T11:17:00-06:00',actividad='Texto docente'):
    doc=individual();doc['id']=did;doc['guardado_en']=fecha
    doc['tablas']['dosificacion']=[{'Contextos':'Aula regular','Actividades':actividad}]
    doc['datos']['Curso escolar']='2026-2027';doc['datos']['Trimestre']=1
    return doc


class RecuperacionTests(TestCase):
    def test_avance_anterior_visible_antes_de_plantillas_nuevas_sin_borrar(self):
        avanzado=ejemplo();plantilla=ejemplo('nuevo','2026-10-19T11:44:00-06:00','')
        entrada=[plantilla,avanzado];antes=deepcopy(entrada)
        self.assertEqual([d['id'] for d in r.ordenar(entrada)],['con-avance','nuevo'])
        self.assertEqual(entrada,antes);self.assertIn('1 actividad',r.etiqueta(avanzado))
        self.assertIn('Sin actividades redactadas',r.etiqueta(plantilla))

    def test_si_ambos_tienen_actividades_se_respeta_la_fecha_no_la_longitud(self):
        self.assertEqual(r.ordenar([ejemplo(actividad='X'*1000),ejemplo('reciente','2026-10-20','Y')])[0]['id'],'reciente')

    def test_equivalencia_exacta_no_mezcla_cuentas_alumnos_escuelas_ni_periodos(self):
        doc=ejemplo();args=[ACTOR,'XXIII',['A1'],doc['datos']['ID_Escuela'],2026,1,'individual']
        self.assertEqual(r.equivalentes([doc],*args),[doc])
        for campo,valor in [('cuenta','otro'),('formato','XXI'),('estado','ENVIADO')]:
            otro=deepcopy(doc);otro[campo]=valor;self.assertFalse(r.equivalentes([otro],*args))
        for campo,valor in [('ID_Escuela','AJENA'),('Trimestre',2),('Curso escolar','2025-2026')]:
            otro=deepcopy(doc);otro['datos'][campo]=valor;self.assertFalse(r.equivalentes([otro],*args))
        self.assertFalse(r.equivalentes([doc],ACTOR,'XXIII',['A10'],doc['datos']['ID_Escuela'],2026,1,'individual'))

    def test_reabrir_equivalente_no_crea_ni_guarda_otro_documento(self):
        from ui import planeacion_simple as ui,planeacion as u
        doc=ejemplo();frame=pd.DataFrame([{'ID_Alumno':'A1','ID_Escuela':doc['datos']['ID_Escuela']}])
        with patch.object(ui.st,'session_state',{}),patch.object(ui.s,'padron_autorizado',return_value=frame),patch.object(ui.s,'identidad',return_value=ACTOR),patch.object(ui.s,'listar',return_value=[doc]),patch.object(ui,'_abrir') as abrir,patch.object(ui.s,'nueva') as nueva,patch.object(u,'_persist') as guardar:
            self.assertEqual(ui.crear_borrador('p','XXIII',['A1'],2026,1,'individual'),'p_individual')
            abrir.assert_called_once_with('p','p_individual',doc);nueva.assert_not_called();guardar.assert_not_called()

    def test_fallo_lectura_no_crea_plantilla_que_aparente_perdida(self):
        from ui import planeacion_simple as ui
        frame=pd.DataFrame([{'ID_Alumno':'A1','ID_Escuela':'E1'}])
        with patch.object(ui.st,'session_state',{}),patch.object(ui.s,'padron_autorizado',return_value=frame),patch.object(ui.s,'listar',side_effect=RuntimeError('Lectura pendiente')),patch.object(ui.s,'nueva') as crear:
            with self.assertRaises(RuntimeError):ui.crear_borrador('p','XXIII',['A1'],2026,1,'individual')
            crear.assert_not_called()

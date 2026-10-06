import unittest
from unittest.mock import patch,Mock
import pandas as pd
from services import horarios as h

class ReferenciasTests(unittest.TestCase):
    def test_coro_ambiguo_y_grupos_confirmados(self):
        p=[{'Dia':'Viernes','Inicio':'09:00','Fin':'09:45','Grupo':'4A'}]
        r=pd.DataFrame([{'Dia':'Viernes','Inicio':'08:00','Fin':'12:00','Grupo':'','Actividad':'Coros y Cantos'}])
        self.assertTrue(h.detectar_choques(p,r).empty)
        for grupo in ('4A','Todos'):
            r.loc[0,'Grupo']=grupo
            self.assertFalse(h.detectar_choques(p,r).empty)
    def test_documentacion_no_choca_con_materias_pero_si_con_bloques_propios(self):
        r=pd.DataFrame([{'Dia':'Viernes','Inicio':'08:00','Fin':'12:00','Grupo':'Todos','Actividad':'Maya'}])
        p=[{'Dia':'Viernes','Inicio':'09:00','Fin':'09:45','Grupo':'','ID_Alumnos':'','Actividad':'Documentación'}]
        self.assertTrue(h.detectar_choques(p,r).empty)
        p.append({**p[0],'Inicio':'09:15','Fin':'10:00'})
        self.assertFalse(h.detectar_choques(p,r).empty)
    def test_edicion_preserva_historial_solo_del_archivo_elegido(self):
        ws=Mock();filas=[{'_fila':2,'Escuela':'Escuela uno','Archivo':'Maya','Estado':'ACTIVO','ID_Version':'v1'},{'_fila':3,'Escuela':'Escuela uno','Archivo':'Inglés','Estado':'ACTIVO','ID_Version':'v2'}]
        frame=pd.DataFrame([{'Dia':'Lunes','Inicio':'08:00','Fin':'09:00','Grupo':'3A','Actividad':'Maya'}])
        with patch.object(h.st,'session_state',{'autenticado':True,'nombre':'Docente','rol':'APOYO'}),patch.object(h,'escuelas_asignadas',return_value=['Escuela uno']),patch.object(h,'_leer',return_value=(ws,h.RESTRICCIONES_HEADERS,filas)),patch.object(h,'_id_escuela',return_value='E1'),patch.object(h,'clear_cache'):
            h.editar_referencia('Escuela uno','Maya',frame,'v1')
        self.assertEqual(ws.append_rows.call_count,1)
        self.assertEqual(ws.batch_update.call_args.args[0],[{'range':'M2','values':[['SUSTITUIDO']]}])
        self.assertEqual(filas[0]['Estado'],'ACTIVO')
    def test_no_permite_otra_escuela(self):
        with patch.object(h.st,'session_state',{'autenticado':True,'nombre':'Docente','rol':'APOYO'}),patch.object(h,'escuelas_asignadas',return_value=['Escuela uno']):
            with self.assertRaises(PermissionError):h.editar_referencia('Otra escuela','Maya',pd.DataFrame(),'v1')
    def test_no_sobrescribe_nueva_version(self):
        ws=Mock();filas=[{'Escuela':'Escuela uno','Archivo':'Maya','Estado':'ACTIVO','ID_Version':'nueva'}]
        frame=pd.DataFrame([{'Dia':'Lunes','Inicio':'08:00','Fin':'09:00','Actividad':'Maya'}])
        with patch.object(h.st,'session_state',{'autenticado':True,'nombre':'Docente','rol':'APOYO'}),patch.object(h,'escuelas_asignadas',return_value=['Escuela uno']),patch.object(h,'_leer',return_value=(ws,h.RESTRICCIONES_HEADERS,filas)):
            with self.assertRaisesRegex(RuntimeError,'Otra cuenta'):h.editar_referencia('Escuela uno','Maya',frame,'vieja')
        ws.append_rows.assert_not_called()

if __name__=='__main__':unittest.main()

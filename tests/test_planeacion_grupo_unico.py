"""Unicidad y colaboración con datos ficticios; no conecta a Sheets."""
from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch,Mock
import ast
import hashlib
import json
from pathlib import Path
import threading
import pandas as pd
from services import planeacion as s,planeacion_grupo_unico as unico
from services.planeacion_modalidad import guia_grupal
from services.planeacion_colaboracion import aportar
from tests.test_planeacion_compartida import grupal
from tests.test_planeacion_panel import ALUMNO,ACTOR,PanelTests


def duplicados():
    a=grupal();a.update(id='origen',revision='r1',guardado_en='2026-10-01T10:00:00')
    a['datos']['Alumnos'][0]['Grupo']=''
    a['metadatos']['guia_grupal_manual']={'filas':[{'ID_Alumno':'A1','Aprendizaje':'Texto de apoyo'}]}
    b=deepcopy(a);b.update(id='copia',revision='r2',guardado_en='2026-10-02T10:00:00')
    b=aportar(b,{**ACTOR,'cuenta':'com','area':'Comunicación'},[{'ID_Alumno':'A1','Texto en formato':'Actividad de comunicación'}],'Nota')
    return a,b


class DocumentoUnicoTests(TestCase):
    def test_dos_documentos_sin_letra_se_reunen_y_no_mutan_originales(self):
        a,b=duplicados();antes=deepcopy([a,b]);docs=unico.documentos([a,b])
        self.assertEqual(len(docs),1);self.assertEqual(docs[0]['id'],'origen')
        fila=guia_grupal(docs[0])['filas'][0]
        self.assertEqual(fila['Aprendizaje'],'Texto de apoyo');self.assertEqual(fila['Comunicación'],'Actividad de comunicación')
        self.assertEqual([a,b],antes)

    def test_identidad_no_cambia_al_guardar_ni_al_reordenar(self):
        a,b=duplicados();nuevo=deepcopy(a);nuevo.update(revision='r3',guardado_en='2026-10-19T10:00:00')
        self.assertEqual(unico.documentos([b,a,nuevo])[0]['id'],'origen')
        self.assertEqual(unico.identificador(a),unico.identificador(b))

    def test_no_mezcla_grados_grupos_escuelas_ni_trimestres(self):
        a,b=duplicados()
        for campo,valor in [('Trimestre',2),('Curso escolar','2027-2028'),('ID_Escuela','E2')]:
            otro=deepcopy(b);otro['datos'][campo]=valor
            self.assertEqual(len(unico.documentos([a,otro])),2)
        for campo,valor in [('Grupo','A'),('Grado','4°')]:
            otro=deepcopy(b);otro['datos']['Alumnos'][0][campo]=valor
            self.assertEqual(len(unico.documentos([a,otro])),2)

    def test_textos_distintos_se_conservan_sin_repetir_ni_revivir_eliminados(self):
        a,b=duplicados();b['metadatos']['guia_grupal_manual']['filas'][0]['Aprendizaje']='Otro texto de apoyo'
        unido=unico.documentos([a,b])[0]
        self.assertIn('Otro texto',guia_grupal(unido)['filas'][0]['Aprendizaje'])
        self.assertEqual(unico.conciliar(unido,[b]),unido)
        unido['metadatos']['guia_grupal_manual']['filas'][0]['Aprendizaje']='Edición revisada'
        self.assertEqual(guia_grupal(unico.conciliar(unido,[b]))['filas'][0]['Aprendizaje'],'Edición revisada')

    def test_dos_autorias_de_area_quedan_señaladas_no_apropiadas(self):
        a,b=duplicados();a=aportar(a,{**ACTOR,'cuenta':'otra-com','area':'Comunicación'},[{'ID_Alumno':'A1','Texto en formato':'Primera actividad'}],'')
        unido=unico.documentos([a,b])[0]
        self.assertEqual(unido['metadatos']['unificacion_grupal']['conflictos_area'],['Comunicación'])
        self.assertIn('Primera actividad',guia_grupal(unido)['filas'][0]['Comunicación'])
        self.assertIn('Actividad de comunicación',guia_grupal(unido)['filas'][0]['Comunicación'])

    def test_nueva_reutiliza_misma_hoja_y_especialistas_no_crean_xix(self):
        a,b=duplicados();frame=pd.DataFrame([{**ALUMNO,'Grupo':'','Tipo_Atencion':'Grupal'}])
        with patch.object(s,'identidad',return_value=ACTOR),patch.object(s,'padron_autorizado',return_value=frame),patch.object(s.repo,'escuelas',return_value=pd.DataFrame()),patch.object(s,'versiones_actuales',return_value=[a,b]):
            doc=s.nueva('XXIII',['A1'],modalidad='grupal')
            self.assertEqual(doc['id'],'origen')
        for area in ('Comunicación','Psicología','Trabajo Social'):
            with patch.object(s,'identidad',return_value={**ACTOR,'area':area}):
                with self.assertRaises(PermissionError):s.nueva('XXIII',['A1'],modalidad='grupal')

    def test_nuevas_sesiones_generan_mismo_id_para_mismo_grupo(self):
        frame=pd.DataFrame([{**ALUMNO,'Tipo_Atencion':'Grupal'}])
        with patch.object(s,'identidad',return_value=ACTOR),patch.object(s,'padron_autorizado',return_value=frame),patch.object(s.repo,'escuelas',return_value=pd.DataFrame()),patch.object(s,'versiones_actuales',return_value=[]):
            self.assertEqual(s.nueva('XXIII',['A1'],modalidad='grupal')['id'],s.nueva('XXIII',['A1'],modalidad='grupal')['id'])

    def test_archivar_unificado_no_revive_copias_y_conserva_fuentes(self):
        a,b=duplicados();unido=unico.documentos([a,b])[0]
        unido['metadatos']['borrador_eliminado']=True;unido['revision']='archivo'
        resultado=unico.documentos([a,b,unido])
        self.assertEqual([d['id'] for d in resultado],['origen'])
        self.assertTrue(resultado[0]['metadatos']['borrador_eliminado'])
        self.assertNotIn('borrador_eliminado',b['metadatos'])

    def test_unificacion_no_expone_destinatarios_ajenos(self):
        a,b=duplicados();b['datos']['Alumnos'][0]['ID_Alumno']='AJENO'
        b['metadatos'].pop('aportaciones_equipo',None)
        b['metadatos']['guia_grupal_manual']={'filas':[{'ID_Alumno':'AJENO','Aprendizaje':'Texto ajeno'}]}
        with patch.object(s,'versiones_actuales',return_value=[a,b]),patch.object(s,'padron_autorizado',return_value=pd.DataFrame([ALUMNO])),patch.object(s,'identidad',return_value=ACTOR):
            self.assertEqual(s.compartidos(),[])

    def test_selector_solo_un_documento_y_no_amplia_asignacion(self):
        a,b=duplicados()
        with patch.object(s,'versiones_actuales',return_value=[a,b]),patch.object(s,'padron_autorizado',return_value=pd.DataFrame([ALUMNO])),patch.object(s,'autorizar'),patch.object(s,'identidad',return_value=ACTOR):
            self.assertEqual([d['id'] for d in s.compartidos()],['origen'])
            self.assertEqual([d['id'] for d in s.listar()],['origen'])
            self.assertEqual(len(s.listar(True)),2)

    def test_guardados_de_hoja_no_recargan_app_y_componente_se_registra_una_vez(self):
        from ui import planeacion_papel as ui
        ui._COMPONENTES.clear()
        uno,dos=Mock(),Mock()
        with patch.object(ui,'_registro_componentes',side_effect=[uno,uno,dos]),patch.object(ui.components,'component') as registrar:
            ui._componente_editor();ui._componente_editor();ui._componente_editor()
            self.assertEqual(registrar.call_count,2)
        ui._COMPONENTES.clear()
        with patch.object(ui,'_registro_componentes',return_value=Mock()),patch.object(ui.components,'component') as registrar:
            self.assertIs(ui._componente_editor(),ui._componente_editor())
            registrar.assert_called_once()
        ui._COMPONENTES.clear()
        for nombre in ('planeacion_papel.py','planeacion_anexo_compartido.py'):
            tree=ast.parse((Path(__file__).parents[1]/'ui'/nombre).read_text(encoding='utf-8'))
            callbacks=[n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name in ('hoja','panel')]
            for fn in callbacks:
                self.assertTrue(any(isinstance(d,ast.Call) and getattr(d.func,'attr','')=='fragment' for d in fn.decorator_list))
                for n in ast.walk(fn):
                    if isinstance(n,ast.Call) and getattr(n.func,'attr','')=='rerun':
                        self.assertTrue(n.keywords,'Toda recarga de hoja debe declarar su alcance')


class PersistenciaUnicaTests(PanelTests):
    def test_apoyo_conserva_edicion_durante_los_aportes_y_primera_conciliacion(self):
        a,b=duplicados()
        for d in (a,b):d['datos']['Alumnos'][0]['Grupo']='B';self.sembrar(d)
        apoyo=s.compartidos()[0]
        apoyo['metadatos']['guia_grupal_manual']['filas'][0]['Aprendizaje']='Edición local de apoyo'
        psic={**ACTOR,'cuenta':'psic','area':'Psicología'}
        with patch.object(s,'identidad',return_value=psic):
            s.guardar_aportacion(s.compartidos()[0],[{'ID_Alumno':'A1','Texto en formato':'Aporte psicología'}],'')
        guardado=s.guardar(apoyo);fila=guia_grupal(guardado)['filas'][0]
        self.assertEqual(fila['Aprendizaje'],'Edición local de apoyo')
        self.assertEqual(fila['Psicología'],'Aporte psicología')
        self.assertEqual(fila['Comunicación'],'Actividad de comunicación')

    def sembrar(self,doc):
        payload=json.dumps(doc,ensure_ascii=False,sort_keys=True);digest=hashlib.sha256(payload.encode()).hexdigest()
        self.sheet.rows.append([doc['id'],doc['revision'],'',doc['guardado_en'],doc['cuenta'],doc['datos']['Nombre del especialista'],doc['datos']['ID_Escuela'],json.dumps(['A1']),doc['formato'],doc['estado'],'0','1',digest,payload])
        s._versiones.clear()

    def test_concilia_en_otro_guardado_del_canonico_y_bloquea_copia_antigua(self):
        a,b=duplicados();a['datos']['Alumnos'][0]['Grupo']='B';b['datos']['Alumnos'][0]['Grupo']='B'
        self.sembrar(a);self.sembrar(b)
        unido=s.compartidos()[0];saved=s.guardar(unido)
        self.assertEqual(saved['id'],'origen');self.assertEqual(len(s.compartidos()),1)
        self.assertEqual(len(s.reconstruir(self.sheet.rows)),3)
        with self.assertRaisesRegex(RuntimeError,'único Anexo'):s.guardar(b)
        self.assertEqual(guia_grupal(s.compartidos()[0])['filas'][0]['Comunicación'],'Actividad de comunicación')

    def test_tres_areas_concurrentes_conservan_una_hoja_y_todos_sus_textos(self):
        d=grupal();saved=s.guardar(d);fallos=[];resultados=[];identidad=threading.local()
        def escribir(area):
            identidad.actor={**ACTOR,'cuenta':area,'area':area}
            try:resultados.append(s.guardar_aportacion(saved,[{'ID_Alumno':'A1','Texto en formato':'Actividad '+area}],''))
            except Exception as exc:fallos.append(str(exc))
        with patch.object(s,'identidad',side_effect=lambda:getattr(identidad,'actor',ACTOR)):
            hilos=[threading.Thread(target=escribir,args=(a,)) for a in ('Comunicación','Psicología','Trabajo Social')]
            for t in hilos:t.start()
            for t in hilos:t.join(10)
        self.assertFalse(fallos);self.assertEqual(len(resultados),3)
        actual=s.compartidos()[0];fila=guia_grupal(actual)['filas'][0]
        for area in ('Comunicación','Psicología','Trabajo Social'):self.assertEqual(fila[area],'Actividad '+area)
        self.assertEqual({d['id'] for d in s.reconstruir(self.sheet.rows)},{saved['id']})

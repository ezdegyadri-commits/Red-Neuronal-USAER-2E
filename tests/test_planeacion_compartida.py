"""Regresiones de Anexo XIX, escala e identidad: exclusivamente datos ficticios."""
from copy import deepcopy
from datetime import date
import unittest
from unittest.mock import patch
import pandas as pd
from services import planeacion as s,planeacion_papel as papel
from services.planeacion_compartida import ampliar_matricula,situacion_inicial,conciliar_autor,etiqueta
from services.planeacion_modalidad import guia_grupal,comprobar
from services.planeacion_colaboracion import aportar
from services import planeacion_evaluacion as escala
from utils.escolar import grado_canonico,edad_septiembre
from services.identidad_alumno import raiz_curp,comprobar_fecha_curp
from tests.test_planeacion_panel import documento,ALUMNO,ACTOR,PanelTests


def grupal():
    d=documento();d['datos']['Alumnos'][0].update(Situacion_Alumno='RI',ID_Maestro_Regular='Docente ficticio')
    d['metadatos'].update(modalidad_planeacion='grupal',vista_formato='guia')
    return d


class ProyeccionTests(unittest.TestCase):
    def test_grados_equivalentes_y_edad_en_limites(self):
        for v in ('3','3o','3º','3°','3.','3ro','tercero'):self.assertEqual(grado_canonico(v),'3°')
        self.assertEqual(edad_septiembre(date(2020,9,1),2026),6)
        self.assertEqual(edad_septiembre(date(2020,9,2),2026),5)
        self.assertEqual(edad_septiembre(date(2020,2,29),2026),6)
        with self.assertRaises(ValueError):edad_septiembre(date(2027,1,1),2026)

    def test_curp_propuesta_sin_homoclave_ni_asignacion_oficial(self):
        root=raiz_curp('López','García','Ana',date(2017,5,12),'M','Yucatán')
        self.assertEqual(root,'LOGA170512MYNPRN');self.assertEqual(len(root),16)
        with self.assertRaises(ValueError):comprobar_fecha_curp(root+'A0',date(2017,5,13))

    def test_captura_canonica_no_reescribe_grado_historico_equivalente(self):
        from data import repository as repo
        headers=repo.BASE_HEADERS['Alumnos']
        original={'ID_Alumno':'ALU-001','CURP':'AAAA100101HYNXXX00','Nombre_Completo':'Alumno ficticio','Grado':'3o','Grupo':'b','Estatus':'Activo'}
        values=[headers,[str(original.get(k,'')) for k in headers]]
        class Sheet:
            def get_all_values(self):return deepcopy(values)
            def batch_update(self,*a,**k):raise AssertionError('No debe reescribir el registro equivalente')
        with patch.object(repo,'ensure_headers'),patch.object(repo,'worksheet',return_value=Sheet()),patch.object(repo,'retry_google',side_effect=lambda f:f()),patch.object(repo,'clear_cache'),patch.object(repo,'google_append_rows_raw') as append:
            self.assertEqual(repo.upsert_alumnos([{'CURP':original['CURP'],'Grado':'3°','Grupo':'B'}]),(0,0))
            repo.upsert_alumnos([{'CURP':'BBBB100101HYNXXX00','Nombre_Completo':'Otro ficticio','Grado':'3o','Grupo':'b','Fecha_Nacimiento':'2010-01-01'}])
            nuevo=append.call_args.args[1][0]
            self.assertEqual(nuevo['Grado'],'3°');self.assertEqual(nuevo['Grupo'],'B')
            self.assertEqual(nuevo['Fecha_Nacimiento'],'2010-01-01')
        self.assertEqual(original['Grado'],'3o')

    def test_altas_solo_mismo_grupo_modalidad_y_escuela_sin_reescribir(self):
        d=grupal();antes=deepcopy(d)
        r={**ALUMNO,'ID_Alumno':'A2','Grado':'1o','Grupo':'b','Tipo_Atencion':'Grupal'}
        frame=pd.DataFrame([r,{**r,'ID_Alumno':'I','Tipo_Atencion':'Individual'},{**r,'ID_Alumno':'X','ID_Escuela':'OTRA'},{**r,'ID_Alumno':'G','Grupo':'C'}])
        nuevo=ampliar_matricula(d,frame)
        self.assertEqual([a['ID_Alumno'] for a in nuevo['datos']['Alumnos']],['A1','A2'])
        self.assertEqual(len(guia_grupal(nuevo)['filas']),2);self.assertEqual(d,antes)
        self.assertEqual(ampliar_matricula(nuevo,frame),nuevo)
        self.assertEqual(guia_grupal(d)['maestro_grupo'],'Docente ficticio')

    def test_situacion_sin_inventar_nee_y_final_protegida(self):
        d=grupal();a=d['datos']['Alumnos'][0]
        self.assertTrue(situacion_inicial(a,[{'tipo':'III','texto':'BAP_Fisicas: JSON'}]).startswith('RI'))
        self.assertNotIn('BAP_Fisicas',situacion_inicial(a,[]))
        a.pop('Situacion_Alumno');self.assertEqual(situacion_inicial(a,[]),'')
        with patch.object(s,'autorizar',return_value=ACTOR):
            spec=papel.hoja(d);self.assertFalse(next(c for c in spec['cells'].values() if c['label']=='Situación final')['editable'])
        self.assertIn('1 alumno(s)',etiqueta(d))
        self.assertNotIn('Alumno ficticio',etiqueta(d))

    def test_escala_por_destinatario_editable_eliminacion_no_reaparece(self):
        d=documento();d['metadatos']['modalidad_planeacion']='individual'
        d['datos']['Alumnos'].append({**d['datos']['Alumnos'][0],'ID_Alumno':'A2','Nombre del alumno':'Otro ficticio'})
        d['tablas']['aprendizajes']=[{'Descriptor de logro':'Identifica una idea','_alumnos_planeacion':['A1']}]
        d['tablas']['dosificacion']=[{'Actividades':'Lee un cuento','_alumnos_planeacion':['A1']},{'Actividades':'Otro alumno','_alumnos_planeacion':['A2']}]
        rows=escala.filas(d);self.assertEqual(len(rows),1);self.assertEqual(rows[0]['Valoración'],'Sin valorar')
        self.assertEqual(rows[0]['Actividad vinculada'],'Lee un cuento')
        editado=escala.editar(d,0,'Indicador de logro','Redacción docente')
        self.assertEqual(escala.filas(editado)[0]['Indicador de logro'],'Redacción docente')
        quitado=escala.cambiar_fila(editado,0);self.assertEqual(escala.filas(quitado),[])
        self.assertEqual(len(escala.filas(escala.cambiar_fila(quitado))),1)
        self.assertEqual(escala.filas(d)[0]['Indicador de logro'],'Identifica una idea')

    def test_individual_no_admite_grupal_y_especialista_conserva_formato_propio(self):
        frame=pd.DataFrame([{**ALUMNO,'Tipo_Atencion':'Grupal'}])
        with self.assertRaises(PermissionError):comprobar(frame,['A1'],'individual')
        comprobar(frame,['A1'],'especialista')
        d=grupal();d['datos']['Función']='Psicología'
        with patch.object(s,'autorizar',return_value={**ACTOR,'area':'Psicología'}):
            self.assertFalse(papel.hoja(d)['grupal'])

    def test_misma_hoja_solo_columna_propia_y_edicion_o_borrado(self):
        d=grupal();actor={**ACTOR,'area':'Psicología','cuenta':'psic'}
        with patch.object(s,'autorizar',return_value=actor),patch.object(s,'identidad',return_value=actor):
            spec=papel.hoja(d,colaborativa=True)
            editable={c['label'] for c in spec['cells'].values() if c['editable']}
            self.assertEqual(editable,{'Psicología','Observaciones de mi área'})
            key=next(k for k,c in spec['cells'].items() if c['editable'])
            event={'documento':d['id'],'huella':spec['huella'],'accion':'guardar','cambios':{key:'Atención · juego breve'}}
            rows=papel.aplicar_aporte(d,event);nuevo=aportar(d,actor,rows,'')
            self.assertEqual(guia_grupal(nuevo)['filas'][0]['Psicología'],'Atención · juego breve')
            espec=papel.hoja(nuevo,colaborativa=True);event.update(huella=espec['huella'],cambios={key:''})
            self.assertEqual(guia_grupal(aportar(nuevo,actor,papel.aplicar_aporte(nuevo,event),''))['filas'][0]['Psicología'],'')
            ajena=next(k for k,c in spec['cells'].items() if c['label']=='Comunicación')
            event.update(huella=spec['huella'],cambios={ajena:'No permitido'})
            with self.assertRaises(PermissionError):papel.aplicar_aporte(d,event)

    def test_conciliacion_no_pisa_otro_docente(self):
        base=grupal();doc=deepcopy(base);latest=deepcopy(base);latest['revision']='r2'
        latest['metadatos']['aportaciones_equipo']={'Psicología':{'filas':[{'ID_Alumno':'A1','Texto en formato':'Aporte psic'}]}}
        doc['textos']['Observaciones']='Cambio maestra'
        fusion=conciliar_autor(doc,base,latest)
        self.assertEqual(fusion['textos']['Observaciones'],'Cambio maestra')
        self.assertEqual(guia_grupal(fusion)['filas'][0]['Psicología'],'Aporte psic')
        latest['textos']['Observaciones']='Otra maestra'
        with self.assertRaises(RuntimeError):conciliar_autor(doc,base,latest)

    def test_abrir_no_recupera_revision_vieja_despues_del_autoguardado(self):
        from ui import planeacion_viva as ui,planeacion as base_ui
        base='planeacion_ficticia';prefix=base+'_grupal';d=grupal()
        d['revision']='vieja';guardado=deepcopy(d);guardado['revision']='nueva'
        guardado['textos']['Observaciones']='Última edición de la maestra'
        state={prefix+'_doc':deepcopy(d),prefix+'_pending':True}
        def guardar(p):state[p+'_doc']=guardado;state[p+'_pending']=False;return True
        def abrir(p,doc):state[p+'_doc']=deepcopy(doc)
        with patch.object(ui.st,'session_state',state),patch.object(base_ui.st,'session_state',state),patch.object(s,'padron_autorizado',return_value=pd.DataFrame()),patch.object(base_ui,'_guardar_edicion_pendiente',side_effect=guardar),patch.object(base_ui,'_open',side_effect=abrir):
            ui._abrir(base,d)
        self.assertEqual(state[prefix+'_doc'],d)
        self.assertTrue(state[prefix+'_pending'])
        self.assertFalse(state[base+'_viva_entrada'])


class PersistenciaTests(PanelTests):
    def test_tres_areas_guardan_desde_misma_revision_sin_perder_aportes(self):
        inicial=s.guardar(grupal())
        for area in ('Psicología','Comunicación','Trabajo Social'):
            actor={**ACTOR,'area':area,'cuenta':area}
            with patch.object(s,'identidad',return_value=actor):
                s.guardar_aportacion(inicial,[{'ID_Alumno':'A1','Texto en formato':'Aporte '+area}],'')
        actual=s.listar()[0]
        self.assertEqual(set(actual['metadatos']['aportaciones_equipo']),{'Psicología','Comunicación','Trabajo Social'})
        maestra=deepcopy(inicial);maestra['textos']['Observaciones']='Texto maestra'
        saved=s.guardar(maestra)
        self.assertEqual(saved['textos']['Observaciones'],'Texto maestra')
        self.assertEqual(len(saved['metadatos']['aportaciones_equipo']),3)
        with patch.object(s,'identidad',return_value={**ACTOR,'area':'Psicología','cuenta':'Psicología'}):
            with self.assertRaises(RuntimeError):s.guardar_aportacion(inicial,[{'ID_Alumno':'A1','Texto en formato':'Texto obsoleto'}],'')
        self.assertEqual(s.reconstruir(self.sheet.rows)[0]['revision'],inicial['revision'])
        self.assertEqual(s.reconstruir(self.sheet.rows)[-1]['revision'],saved['revision'])

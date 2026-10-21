"""Pruebas sin red ni datos reales de continuidad, catálogos e integración."""
from copy import deepcopy
from datetime import date
import json
from unittest import TestCase
from unittest.mock import patch,Mock
import pandas as pd
from services.sesiones_recuperables import Sesiones,TTL


class Memoria:
    def __init__(self):
        self.registros=[]
        self.cuenta={'Usuario':'ficticia','Password':'clave-sintetica','Rol':'APOYO','Nombre':'Prueba','Escuelas_Permitidas':'E1','Estatus':'Activo'}
    def user(self,nombre):
        if nombre!=self.cuenta['Usuario'] or self.cuenta['Estatus']!='Activo':raise PermissionError()
        return dict(self.cuenta)
    def append(self,row):self.registros.append(dict(row))
    def rows(self):return deepcopy(self.registros)


class SesionTests(TestCase):
    def setUp(self):
        self.now=1800000000;self.store=Memoria()
        self.s=Sesiones(b'secreto-exclusivo-de-prueba',self.store,lambda:self.now)
    def test_recarga_y_token_sin_datos_legibles(self):
        token=self.s.emitir('ficticia')
        self.assertNotIn('ficticia',token);self.assertNotIn('clave-sintetica',str(self.store.registros))
        self.assertEqual(self.s.recuperar(token)['Usuario'],'ficticia')
    def test_expira_exactamente_a_las_doce_horas(self):
        token=self.s.emitir('ficticia');self.now+=TTL-1;self.s.recuperar(token)
        self.now+=1
        with self.assertRaises(ValueError):self.s.recuperar(token)
    def test_revocacion_impide_reuso_incluso_si_se_reordena_el_diario(self):
        token=self.s.emitir('ficticia');self.s.cerrar(token,'ficticia');self.store.registros.reverse()
        with self.assertRaises(ValueError):self.s.recuperar(token)
    def test_revocacion_de_token_vencido_permite_cerrar(self):
        token=self.s.emitir('ficticia');self.now+=TTL+1;self.s.cerrar(token,'ficticia')
    def test_no_cierra_otra_cuenta(self):
        token=self.s.emitir('ficticia')
        with self.assertRaises(PermissionError):self.s.cerrar(token,'otra')
    def test_token_alterado_o_registro_alterado_no_autentica(self):
        token=self.s.emitir('ficticia')
        with self.assertRaises(ValueError):self.s.recuperar('X'+token[1:])
        self.store.registros[0]['Estado']='OTRA'
        with self.assertRaises(ValueError):self.s.recuperar(token)
    def test_cambio_de_password_rol_o_escuelas_invalida(self):
        for campo in ('Password','Rol','Escuelas_Permitidas','Nombre'):
            self.setUp();token=self.s.emitir('ficticia');self.store.cuenta[campo]='Cambio'
            with self.assertRaises(ValueError):self.s.recuperar(token)
    def test_cuenta_inactiva_no_recupera(self):
        token=self.s.emitir('ficticia');self.store.cuenta['Estatus']='Baja'
        with self.assertRaises(PermissionError):self.s.recuperar(token)
    def test_borrador_cifrado_solo_misma_cuenta_y_campos_permitidos(self):
        datos={'evento_descripcion':'Texto ficticio','evento_fecha':date(2026,10,21),'rol':'Dirección'}
        token=self.s.proteger_borrador('ficticia',datos)
        self.assertNotIn('Texto ficticio',token)
        recuperado=self.s.recuperar_borrador('ficticia',token)
        self.assertNotIn('rol',recuperado);self.assertEqual(recuperado['evento_fecha'],datos['evento_fecha'])
        with self.assertRaises(ValueError):self.s.recuperar_borrador('otra',token)
    def test_borrador_vence_sin_borrar_original(self):
        token=self.s.proteger_borrador('ficticia',{'evento_descripcion':'Texto'})
        self.now+=TTL+1
        with self.assertRaises(ValueError):self.s.recuperar_borrador('ficticia',token)


class CatalogosTests(TestCase):
    def test_grados_y_condicion_se_homologan_sin_mutar_fuente(self):
        from services.padron_catalogos import canonico
        for valor in ('3o','3°','3ro','3º'):
            self.assertEqual(canonico('Grado',valor),'3°')
        self.assertEqual(canonico('Sexo','h'),'H')
    def test_fechas_y_orden_numerico(self):
        from services.padron_catalogos import fecha_documental,ordenar
        self.assertEqual(fecha_documental('21/10/2026'),date(2026,10,21))
        with self.assertRaises(ValueError):fecha_documental('99/99/2026')
        f=pd.DataFrame([{'Grado':'3o','Nombre_Completo':'ZETA X','Edad_1_Septiembre':'10'},
                        {'Grado':'1ro','Nombre_Completo':'ALFA Y','Edad_1_Septiembre':'6'}]);antes=f.copy()
        self.assertEqual(ordenar(f,'Grado')['Grado'].tolist(),['1ro','3o'])
        self.assertEqual(ordenar(f,'Edad')['Edad_1_Septiembre'].tolist(),['6','10'])
        pd.testing.assert_frame_equal(f,antes)
    def test_cronologia_fecha_desconocida_al_final(self):
        from services.expediente_automatico import orden_cronologico
        rows=[{'ID_Documento':'sin','Fecha':''},{'ID_Documento':'dos','Fecha':'2026-10-21'},
              {'ID_Documento':'uno','Fecha':'19/10/2026'}]
        self.assertEqual([r['ID_Documento'] for r in orden_cronologico(rows)],['uno','dos','sin'])
    def test_recupera_grupo_con_nomenclatura_anterior_sin_otra_escuela(self):
        from data import repository as repo
        from config.settings import ESCUELAS_USAER
        codigo=str(next(iter(ESCUELAS_USAER.values())))
        datos=pd.DataFrame([{'ID_Evento':'V1','ID_Alumno':'GRUPO-'+codigo+'-6o-A','Fecha':'2026-10-20'},
                            {'ID_Evento':'V2','ID_Alumno':'GRUPO-OTRA-6to-A','Fecha':'2026-10-20'}])
        with patch.object(repo,'anexo5',return_value=datos),patch.object(repo,'read',return_value=pd.DataFrame()):
            recuperados=repo.eventos_alumno('GRUPO-'+codigo+'-6to-A')
        self.assertEqual(recuperados['ID_Evento'].tolist(),['V1'])
    def test_calendario_derivacion_y_valor_central_sin_pisar_historia(self):
        from services import planeacion_papel as p
        from tests.test_planeacion_local import documento
        from services.planeacion_modalidad import guia_grupal
        d=documento();d['metadatos']['modalidad_planeacion']='grupal'
        aid=d['datos']['Alumnos'][0]['ID_Alumno']
        d['metadatos']['contexto_padron_grupo']={aid:{'Fecha_Derivacion':'2026-10-01'}}
        with patch.object(p.s,'autorizar',return_value={}):
            spec=p.hoja(d);cell=next(c for c in spec['cells'].values() if c['label']=='Fecha derivación')
            self.assertEqual(cell['tipo'],'fecha');self.assertEqual(cell['fecha_iso'],'2026-10-01')
            nuevo=p.aplicar(d,{'documento':d['id'],'huella':spec['huella'],'accion':'guardar','cambios':{cell['id']:'2026-10-03'}})
            self.assertEqual(guia_grupal(nuevo)['filas'][0]['Fecha derivación'],'03/10/2026')
            self.assertEqual(guia_grupal(d)['filas'][0]['Fecha derivación'],'01/10/2026')
    def test_borradores_de_hojas_no_se_mezclan(self):
        from services.eventos_continuidad import cambiar_contexto
        state={};cambiar_contexto(state,'A1');state['evento_descripcion']='Avance uno'
        cambiar_contexto(state,'A2');self.assertEqual(state['evento_descripcion'],'')
        state['evento_descripcion']='Avance dos';cambiar_contexto(state,'A1')
        self.assertEqual(state['evento_descripcion'],'Avance uno')
        self.assertEqual(json.loads(state['evento_borradores_json'])['A2'],'Avance dos')
    def test_borrador_no_recupera_alumnos_fuera_de_asignacion_actual(self):
        from services.eventos_continuidad import filtrar_borrador
        frame=pd.DataFrame([{'ID_Alumno':'A1'}])
        datos={'evento_contexto_actual':'A2','evento_descripcion':'Texto ajeno al ámbito actual',
               'evento_borradores_json':json.dumps({'A1':'Autorizado','A2':'Fuera de asignación'})}
        recuperado=filtrar_borrador(datos,frame)
        self.assertNotIn('evento_descripcion',recuperado)
        self.assertEqual(json.loads(recuperado['evento_borradores_json']),{'A1':'Autorizado'})
    def test_no_repite_actividades_literales_o_casi_identicas(self):
        from services.planeacion_variedad import repetida
        texto='Inicio con tarjetas. Desarrollo: elegir objetos y ordenarlos por su color. Cierre: explicar el criterio de clasificación.'
        self.assertTrue(repetida(texto.upper(),[texto]))
        self.assertTrue(repetida(texto.replace('objetos','figuras'),[texto]))
        self.assertFalse(repetida('Conversar sobre un acuerdo y representar con títeres una solución.',[texto]))


class ProgramacionTests(TestCase):
    def setUp(self):
        from services import epp_programacion as s
        self.s=s;self.rows=[]
        self.actor={'cuenta':'apoyo-ficticio','area':'Aprendizaje','rol':'APOYO','director':False}
        self.frame=pd.DataFrame([{'ID_Alumno':'A1','ID_Escuela':'E1'}])
        for p in (patch.object(s.epp,'actor',side_effect=lambda:self.actor),
                  patch.object(s.epp,'puede_crear',side_effect=lambda:self.actor['rol']=='APOYO'),
                  patch.object(s.epp.planes,'padron_autorizado',return_value=self.frame),
                  patch.object(s.epp,'alumno_autorizado',return_value=self.frame.iloc[0].to_dict()),
                  patch.object(s,'_rows',side_effect=lambda:deepcopy(self.rows)),patch.object(s,'clear_cache')):
            p.start();self.addCleanup(p.stop)
        self.ws=Mock();self.ws.row_values.return_value=s.HEADERS
        self.ws.append_rows.side_effect=lambda values,**kw:self.rows.extend(dict(zip(s.HEADERS,r)) for r in values)
        p=patch.object(s,'ensure_headers',return_value=self.ws);p.start();self.addCleanup(p.stop)
    def test_crear_y_reintento_no_duplica(self):
        r=self.s.guardar('A1','2026-2027','Comunicación',date(2026,11,3),estado='Programada')
        self.assertEqual(self.s.guardar('A1','2026-2027','Comunicación',date(2026,11,3),estado='Programada'),r)
        self.assertEqual(len(self.rows),1)
    def test_equipo_continua_no_inicia_y_conflicto_no_sobrescribe(self):
        r=self.s.guardar('A1','2026-2027','Aprendizaje')
        self.actor.update(cuenta='comunicacion-ficticia',area='Comunicación',rol='COMUNICACION')
        with self.assertRaises(PermissionError):self.s.guardar('A1','2026-2027','Comunicación')
        nuevo=self.s.guardar('A1','2026-2027','Comunicación',date(2026,11,3),estado='Programada',identificador=r['ID_Programacion'],revision=r['Revision'])
        self.assertEqual(len(self.rows),2)
        with self.assertRaises(RuntimeError):self.s.guardar('A1','2026-2027','Psicología',identificador=r['ID_Programacion'],revision=r['Revision'])
        self.assertEqual(self.s.listar()[0]['Revision'],nuevo['Revision'])
    def test_no_expone_otra_escuela_y_solo_director_valida(self):
        self.rows=[{'ID_Programacion':'ajeno','ID_Alumno':'A1','ID_Escuela':'E2'}]
        self.assertEqual(self.s.listar(),[])
        with self.assertRaises(PermissionError):self.s.guardar('A1','2026-2027','Aprendizaje',date(2026,11,3),estado='Validada por Dirección')
    def test_calendario_una_fecha_actual_sin_datos_de_alumno(self):
        r=self.s.guardar('A1','2026-2027','Aprendizaje',date(2026,11,3),estado='Programada')
        self.s.guardar('A1','2026-2027','Aprendizaje',date(2026,11,4),estado='Programada',identificador=r['ID_Programacion'],revision=r['Revision'])
        with patch.object(self.s.epp.st,'session_state',{'autenticado':True}):events=self.s.eventos_calendario('2026-11')
        self.assertEqual(len(events),1);self.assertEqual(events[0]['Fecha'],'2026-11-04')
        self.assertNotIn('A1',str(events))


class ExpedienteVivoTests(TestCase):
    def test_reubica_referencia_especifica_sin_mover_documento_colectivo(self):
        from services.expediente_automatico import organizar_archivados
        rows=[{'ID_Documento':'especifico','Ambito':'grupal','Tipo':'Sugerencias','ID_Alumnos_JSON':'["A1"]','Fecha':'2026-10-20'},
              {'ID_Documento':'colectivo','Ambito':'grupal','Tipo':'Sugerencias','ID_Alumnos_JSON':'["A1","A2"]','Fecha':'2026-10-20'}]
        antes=deepcopy(rows);resultado={r['ID_Documento']:r for r in organizar_archivados(rows,{'A1'})}
        self.assertEqual(resultado['especifico']['Ambito'],'individual')
        self.assertEqual(resultado['colectivo']['Ambito'],'grupal')
        self.assertEqual(rows,antes)

    def test_fuentes_conectadas_sin_confundir_grupo_individual_ni_otra_escuela(self):
        from services import expediente_automatico as s,archivo_expediente as ar,epp,planeacion as p
        from config.settings import ESCUELAS_USAER
        codigo=str(next(iter(ESCUELAS_USAER.values())))
        frame=pd.DataFrame([{'ID_Alumno':'A1','ID_Escuela':codigo,'Grado':'2o','Grupo':'A'},
                            {'ID_Alumno':'A2','ID_Escuela':codigo,'Grado':'2°','Grupo':'A'}])
        datos={'Anexo3_Deteccion':pd.DataFrame([{'ID_Anexo3':'B1','ID_Alumno':'GRUPO-'+codigo+'-2do-A','Fecha':'2026-10-01'}]),
               'Anexo4_Sugerencias':pd.DataFrame([{'ID_Anexo4':'S1','ID_Alumno':'A1','Fecha':'2026-10-02'},
                                                 {'ID_Anexo4':'AJENO','ID_Alumno':'A3','Fecha':'2026-10-03'}])}
        informe={'alumno':'A1','id':'EPP1','ciclo':'2026-2027','partes':{}}
        with patch.object(ar,'visibles',return_value=frame),patch.object(epp,'listar',return_value=[informe]),patch.object(p,'versiones_actuales',return_value=[]),patch.object(s, 'fecha_documental',wraps=s.fecha_documental),patch('data.repository.read',side_effect=lambda h:datos.get(h,pd.DataFrame())):
            grupo=s.documentos_vivos(['A1','A2'],True)
            individual=s.documentos_vivos(['A1'])
            self.assertEqual([r['Tipo'] for r in grupo],['BAP áulico'])
            self.assertIn('Sugerencias',[r['Tipo'] for r in individual])
            self.assertNotIn('BAP áulico',[r['Tipo'] for r in individual])
            self.assertNotIn('AJENO',str(individual))
            with self.assertRaises(PermissionError):s.documentos_vivos(['A3'])

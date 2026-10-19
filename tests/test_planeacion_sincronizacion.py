"""Sincronización por ID y área; no usa datos reales ni servicios externos."""
from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch
from services import planeacion as s,planeacion_papel as papel
from services.planeacion_colaboracion import aportar
from services.planeacion_compartida import etiqueta_selector,actualizar_lectura,actualizar_aportes_autor
from tests.test_planeacion_compartida import grupal,ACTOR


class SincronizacionTests(TestCase):
    def test_autor_no_confirma_nonce_hasta_guardado_durable(self):
        from ui import planeacion as u
        state={'p_doc':grupal(),'p_papel_nonce':'nuevo','p_papel_aceptado':'viejo'}
        with patch.object(u.st,'session_state',state),patch.object(s,'guardar',side_effect=RuntimeError('Sin conexión ficticia')):
            self.assertFalse(u._persist('p'))
        self.assertTrue(state['p_pending']);self.assertEqual(state['p_papel_aceptado'],'viejo')
        with patch.object(u.st,'session_state',state),patch.object(s,'guardar',return_value=grupal()):
            self.assertTrue(u._persist('p'))
        self.assertFalse(state['p_pending']);self.assertEqual(state['p_papel_aceptado'],'nuevo')

    def test_etiqueta_no_cambia_al_guardar_ni_ordenar(self):
        d=grupal();nuevo=deepcopy(d);nuevo['guardado_en']='otra-hora'
        self.assertEqual(etiqueta_selector(d),etiqueta_selector(nuevo))
        otro=deepcopy(d);otro['id']='otro';otro['datos']['Alumnos'][0]['Grado']='3°'
        self.assertNotEqual(etiqueta_selector(d),etiqueta_selector(otro))

    def test_apoyo_visible_sin_invalidar_evento_en_vuelo_de_especialista(self):
        for area in ('Comunicación','Psicología','Trabajo Social'):
            actor={**ACTOR,'cuenta':'ficticio-'+area,'area':area}
            d=grupal();latest=deepcopy(d)
            latest['metadatos']['guia_grupal_manual']={'filas':[{'ID_Alumno':'A1','Aprendizaje':'Lectura acompañada con imágenes.'}]}
            latest['guardado_en']='nuevo';latest['revision']='nueva'
            with self.subTest(area=area),patch.object(s,'autorizar',return_value=actor),patch.object(s,'identidad',return_value=actor):
                antes=papel.hoja(d,colaborativa=True)
                nuevo=actualizar_lectura(d,latest,area)
                spec=papel.hoja(nuevo,colaborativa=True)
                self.assertEqual(antes['huella'],spec['huella'])
                self.assertIn('Lectura acompañada',str(spec['tables']))
                celda=next(k for k,c in antes['cells'].items() if c['target']==('aporte',0,area))
                obs=next(k for k,c in antes['cells'].items() if c['target']==('aporte_obs',))
                filas,notas=papel.aplicar_aporte(nuevo,{'documento':d['id'],'huella':antes['huella'],
                    'accion':'guardar','cambios':{celda:'Actividad de mi área',obs:'Observación editable'}},con_observaciones=True)
                self.assertEqual(filas[0]['Texto en formato'],'Actividad de mi área')
                self.assertEqual(notas,'Observación editable')

    def test_lectura_no_oculta_conflicto_de_dos_sesiones_de_misma_area(self):
        actor={**ACTOR,'area':'Comunicación','cuenta':'com'}
        base=grupal();latest=aportar(base,actor,[],'Otra sesión')
        visible=actualizar_lectura(base,latest,'Comunicación')
        self.assertNotIn('Comunicación',visible['metadatos']['aportaciones_equipo'])
        with patch.object(s,'autorizar',return_value=actor),patch.object(s,'compartidos',return_value=[latest]),patch.object(s,'_guardar_version') as write:
            with self.assertRaises(RuntimeError):s.guardar_aportacion(visible,[],'Mi edición')
            write.assert_not_called()

    def test_apoyo_actualiza_otras_areas_sin_tocar_su_texto_ni_revision(self):
        d=grupal();d['metadatos']['guia_grupal_manual']={'filas':[{'ID_Alumno':'A1','Aprendizaje':'Texto local de apoyo'}]}
        actor={**ACTOR,'area':'Comunicación','cuenta':'com'}
        latest=aportar(d,actor,[],'Notas de comunicación')
        latest['metadatos']['guia_grupal_manual']['filas'][0]['Aprendizaje']='No reemplazar'
        nuevo=actualizar_aportes_autor(d,latest)
        self.assertEqual(nuevo['revision'],d['revision'])
        self.assertEqual(nuevo['metadatos']['guia_grupal_manual']['filas'][0]['Aprendizaje'],'Texto local de apoyo')
        self.assertEqual(papel.huella(d),papel.huella(nuevo))

    def test_matricula_distinta_invalida_evento_y_documento_distinto_se_rechaza(self):
        actor={**ACTOR,'area':'Comunicación','cuenta':'com'}
        d=grupal();latest=deepcopy(d)
        latest['datos']['Alumnos'].append({**latest['datos']['Alumnos'][0],'ID_Alumno':'A2'})
        with patch.object(s,'autorizar',return_value=actor):
            self.assertNotEqual(papel.hoja(d,colaborativa=True)['huella'],papel.hoja(latest,colaborativa=True)['huella'])
        latest['id']='otro'
        with self.assertRaises(ValueError):actualizar_lectura(d,latest,'Comunicación')

    def test_guardar_sin_cambios_no_consume_otra_escritura(self):
        actor={**ACTOR,'area':'Comunicación','cuenta':'com'}
        doc=aportar(grupal(),actor,[],'Revisado')
        with patch.object(s,'autorizar',return_value=actor),patch.object(s,'compartidos',return_value=[doc]),patch.object(s,'_guardar_version') as write:
            self.assertEqual(s.guardar_aportacion(doc,[],'Revisado'),doc)
            write.assert_not_called()

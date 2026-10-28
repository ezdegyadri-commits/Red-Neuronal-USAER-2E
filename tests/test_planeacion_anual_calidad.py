from copy import deepcopy
import unittest
from unittest.mock import patch
from services import planeacion_periodo as periodo,planeacion_grupo_unico as unico,planeacion_calidad as calidad
from tests.test_planeacion_local import documento


class AnualTests(unittest.TestCase):
    def doc(self):
        d=documento();d['revision']='';d['metadatos'].update(modalidad_planeacion='grupal',vista_formato='guia')
        d['datos']['Alumnos']=d['datos']['Alumnos'][:1]
        return d
    def test_anual_y_trimestral_no_se_concilian_ni_comparten_identidad(self):
        d=self.doc();antes=deepcopy(d);a=periodo.anual(d)
        self.assertNotEqual(unico.clave(d),unico.clave(a))
        self.assertNotEqual(unico.identificador(d),unico.identificador(a))
        self.assertEqual(d,antes)
        b=deepcopy(a);b['datos']['Trimestre']=3
        self.assertEqual(unico.clave(a),unico.clave(b))
        self.assertIn('09-01',a['datos']['Periodo']);self.assertIn('08-31',a['datos']['Periodo'])
    def test_historia_no_se_convierte(self):
        d=self.doc();d['revision']='guardada'
        with self.assertRaises(ValueError):periodo.anual(d)
    def test_seguimientos_idempotentes_y_dentro_del_ciclo(self):
        d=periodo.anual(self.doc());inicio,fin=d['datos']['Periodo'].split(' / ')
        n=periodo.agregar_seguimiento(d,inicio,fin,'Valorar avances con apoyos visuales')
        self.assertEqual(periodo.agregar_seguimiento(n,inicio,fin,'Valorar avances con apoyos visuales'),n)
        with self.assertRaises(ValueError):periodo.agregar_seguimiento(n,'2000-01-01',fin,'Fuera del ciclo')


class CalidadTests(unittest.TestCase):
    def test_catorce_indicadores_sin_calificacion_automatica(self):
        d=documento();antes=deepcopy(d);rows=calidad.revisar(d)
        self.assertEqual(len(rows),14);self.assertTrue(all(r['Valoración docente'] is None for r in rows))
        self.assertEqual(rows[7]['Comprobación estructural'],'Revisión pedagógica necesaria')
        self.assertEqual(d,antes)
    def test_descriptor_personalizado_y_observable(self):
        self.assertEqual(calidad.descriptor('Alumno Ficticio','identifica','dos imágenes entre tres opciones con apoyo visual'),'Alumno Ficticio identifica dos imágenes entre tres opciones con apoyo visual.')
        with self.assertRaises(ValueError):calidad.descriptor('Alumno Ficticio','aprenderá','contenido genérico')
    def test_anonimizacion_completa_no_deja_identificadores_en_xml(self):
        from services.planeacion import anonimizar_texto
        d=documento();nombre=d['datos']['Alumnos'][0]['Nombre del alumno']
        result=anonimizar_texto(d,'<datos>'+('Hallazgo '*2000)+nombre+' AAAA160101HYNLNNA1</datos>')
        self.assertNotIn(nombre,result);self.assertNotIn('AAAA160101HYNLNNA1',result)

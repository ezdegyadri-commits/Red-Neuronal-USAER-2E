"""Redacción y salida institucional con personal y actividades ficticios."""
from copy import deepcopy
from io import BytesIO
from unittest import TestCase
from pypdf import PdfReader
from documents.oficios import cuerpo_comision,generar_oficio_comision


def registro():
    return dict(Fecha_Emision='2026-10-22',Fecha_Comision='2026-10-23',Folio=999,
                Escuela='Escuela de prueba',Director_Escuela='Dirección de prueba',
                Maestra_Apoyo='Mtra. Ana Pérez',Destino='Organización de EPP y expedientes de atención.',
                Horario='en su horario laboral.',Asunto='COMISIÓN DE SERVICIO')


class RedaccionTests(TestCase):
    def test_actividad_nominal_sin_para_ni_repeticion_ni_sede_inventada(self):
        r=registro();antes=deepcopy(r);texto=cuerpo_comision(r)
        self.assertIn('comisión de servicio: Organización de EPP y expedientes de atención.',texto)
        self.assertIn('23 de octubre de 2026, en su horario laboral.',texto)
        for cadena in ('para Organización','apoyo Mtra.','..','en la escuela a su cargo'):
            self.assertNotIn(cadena,texto)
        self.assertEqual(r,antes)

    def test_nombre_masculino_y_destino_no_alterados(self):
        r=registro();r.update(Maestra_Apoyo='Mtro. Luis Pérez',Destino='Reunión en la sede de supervisión',Horario='de 08:00 a 12:00 horas')
        texto=cuerpo_comision(r)
        self.assertIn('Mtro. Luis Pérez, docente de apoyo',texto)
        self.assertNotIn('comisionada',texto)
        self.assertIn(r['Destino'],texto)

    def test_campos_obligatorios_y_pdf(self):
        for campo in ('Maestra_Apoyo','Destino','Fecha_Comision'):
            r=registro();r[campo]=''
            with self.assertRaises(ValueError):cuerpo_comision(r)
        pdf=PdfReader(BytesIO(generar_oficio_comision(registro())))
        texto='\n'.join(p.extract_text() for p in pdf.pages)
        self.assertIn('Organización de EPP',texto)
        self.assertIn('Director de la USAER 02-E',texto)
        self.assertEqual(len(pdf.pages),1)

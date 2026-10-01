import unittest

from services.asignaciones import puede_dar_alta_alumnos


class AltaPermissionsTest(unittest.TestCase):
    def test_autoriza_cuentas_de_apoyo_indicadas_por_direccion(self):
        maestras_y_apoyo = [
            "Cindy Mayanin Burgos Gonzalez",
            "Luis Jorge Garcia Herrera",
            "Marycruz Caamal Coral",
            "Maria Cecilia Solis Vazquez",
            "Maria del Rosario Perez Vitorin",
            "Dolores Eugenia Cortazar Navarrete",
            "Dianely de Sugeidy Caamal Tamay",
            "Zu emmy del Carmen Perez Basto",
        ]
        # La grafía de la cuenta de Zuemmy no lleva espacio interno.
        maestras_y_apoyo[-1] = "Zuemmy del Carmen Perez Basto"
        for nombre in maestras_y_apoyo:
            with self.subTest(nombre=nombre):
                self.assertTrue(puede_dar_alta_alumnos(nombre, "Apoyo"))

    def test_admite_prefijo_de_apoyo_y_cuenta_directiva_autorizada(self):
        self.assertTrue(puede_dar_alta_alumnos("Mtra. Marycruz Caamal Coral", "Apoyo"))
        self.assertTrue(puede_dar_alta_alumnos("Edgar Adrián Yam Briceño", "Director"))

    def test_bloquea_especialistas_y_apoyos_no_autorizados(self):
        no_autorizados = [
            ("María José Cupul Realpozo", "Psicología"),
            ("Elmy Lucelly Puerto Gone", "Comunicación"),
            ("Diego Peralta Torres", "Trabajo Social"),
            ("Pedro Manuel Torres May", "Apoyo"),
            ("Edgar Adrián Yam Briceño", "Especialista"),
        ]
        for nombre, rol in no_autorizados:
            with self.subTest(nombre=nombre, rol=rol):
                self.assertFalse(puede_dar_alta_alumnos(nombre, rol))


if __name__ == "__main__":
    unittest.main()

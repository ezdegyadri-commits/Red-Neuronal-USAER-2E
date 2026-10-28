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
            "Zuemmy del Carmen Perez Basto",
        ]
        for nombre in maestras_y_apoyo:
            with self.subTest(nombre=nombre):
                self.assertTrue(puede_dar_alta_alumnos(nombre, "Apoyo"))

    def test_admite_prefijo_de_apoyo_y_cuenta_directiva_autorizada(self):
        self.assertTrue(puede_dar_alta_alumnos("Mtra. Marycruz Caamal Coral", "Apoyo"))
        self.assertTrue(puede_dar_alta_alumnos("Edgar Adrián Yam Briceño", "Director"))
        self.assertTrue(puede_dar_alta_alumnos("Psic. Edgar Adrián Yam Briceño MD", "Director"))

    def test_restituye_acceso_al_apoyo_autorizado_con_tratamiento_masculino(self):
        for prefijo in ("Mtro.", "Mtro", "Maestro"):
            with self.subTest(prefijo=prefijo):
                self.assertTrue(puede_dar_alta_alumnos(prefijo+" Luis Jorge García Herrera", "Apoyo"))
                self.assertFalse(puede_dar_alta_alumnos(prefijo+" Pedro Manuel Torres May", "Apoyo"))
                self.assertFalse(puede_dar_alta_alumnos(prefijo+" Luis Jorge García Herrera", "Comunicación"))

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

import unittest
from pathlib import Path
from services.cronogramas import perfil_especialista
from config.settings import ESCUELAS_USAER


class DiegoCronogramaTest(unittest.TestCase):
    def test_diego_explicit_authorization_and_eight_schools(self):
        for nombre in ("Diego Peralta Torres", "TS. Diego Peralta Torres", "T.S. Diego Peralta Torres", "Lic. Diego Peralta Torres"):
            for rol in ("Trabajo Social", "TS", "T.S.", "Especialista", "Apoyo", ""):
                with self.subTest(nombre=nombre, rol=rol):
                    p = perfil_especialista(nombre, rol)
                    self.assertEqual(p["area"], "Trabajo Social")
                    self.assertEqual(p["escuelas"], list(ESCUELAS_USAER))

    def test_unknown_identity_not_granted(self):
        for nombre in ("Diego", "Otra persona", "Diego Peralta Torres Otra"):
            self.assertIsNone(perfil_especialista(nombre, "T.S."))

    def test_sidebar_uses_authorized_profile_without_second_role_gate(self):
        source = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
        self.assertIn('if perfil_cronograma and perfil_cronograma["area"] != "Dirección":', source)
        self.assertNotIn('if es_especialista(rol) and perfil_especialista', source)


if __name__ == "__main__":
    unittest.main()

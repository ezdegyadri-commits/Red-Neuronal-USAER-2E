import unittest

from ui.estadisticas import _cambios_edicion


class RosterEditTest(unittest.TestCase):
    def test_blank_fields_are_ignored_unless_group_clear_is_explicit(self):
        current = {"Grupo": "A", "Sexo": "H"}
        entered = {"Grupo": "", "Sexo": "H"}

        self.assertEqual(_cambios_edicion(entered, current), {})
        self.assertEqual(_cambios_edicion(entered, current, quitar_grupo=True), {"Grupo": ""})

    def test_explicit_group_clear_does_not_change_other_fields(self):
        current = {"Grupo": "A", "Sexo": "H", "Grado": "1"}
        entered = {"Grupo": "A", "Sexo": "M", "Grado": ""}

        self.assertEqual(_cambios_edicion(entered, current, quitar_grupo=True), {
            "Grupo": "",
            "Sexo": "M",
        })

    def test_no_group_is_not_added_as_a_change(self):
        self.assertEqual(_cambios_edicion({"Grupo": ""}, {"Grupo": ""}, quitar_grupo=True), {})


if __name__ == "__main__":
    unittest.main()

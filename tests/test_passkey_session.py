import unittest
from unittest.mock import patch

class SessionTest(unittest.TestCase):
    def test_both_methods_use_server_assignments_and_clear_challenge(self):
        from ui import auth
        state = {"passkey_pending": {"challenge": "old"}}
        account = {"Usuario": "test", "Nombre": "Synthetic", "Rol": "Maestra de Apoyo",
                   "Escuelas_Permitidas": "Wrong client scope"}
        with patch.object(auth.st, "session_state", state), patch.object(auth, "escuelas_asignadas", return_value=["School A"]):
            auth.start_session(account)
        self.assertTrue(state["autenticado"])
        self.assertEqual(state["usuario"], "test")
        self.assertEqual(state["escuelas_permitidas"], "School A")
        self.assertNotIn("passkey_pending", state)

    def test_login_cancel_renews_challenge_without_sheet_access(self):
        from ui import passkeys
        from services.passkeys import begin
        state = {}
        pending = begin(state, "authenticate")
        with patch.object(passkeys.st, "session_state", state), patch.object(passkeys, "_render", return_value={"request": pending["request"], "error": "cancelled"}), patch.object(passkeys.st, "rerun") as rerun, patch.object(passkeys, "GooglePasskeyStore") as store:
            passkeys.login_passkey(lambda _: self.fail("Cancelled login"))
        rerun.assert_called_once()
        store.assert_not_called()
        self.assertNotIn("passkey_pending", state)

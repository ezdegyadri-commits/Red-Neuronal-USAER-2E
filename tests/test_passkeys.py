"""Cryptographic ceremonies with synthetic credentials; no real accounts/data."""
import copy
import hashlib
import json
import secrets
import struct
import unittest
from unittest.mock import Mock, patch

import cbor2
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from webauthn.helpers import bytes_to_base64url as b64, base64url_to_bytes
from services import passkeys as p


USER = {"ID_Usuario": "TEST-1", "Usuario": "cuenta-prueba", "Password": "solo-pruebas",
        "Nombre": "Persona de prueba", "Rol": "Maestra de Apoyo", "Escuelas_Permitidas": "Ichcaanziho"}


class FakeStore:
    def __init__(self):
        self.users = {USER["Usuario"]: copy.deepcopy(USER)}
        self.items = {}
        self.fail_write = False

    def user(self, username):
        if username not in self.users:
            raise p.AccessError("Cuenta no disponible")
        return self.users[username]

    def binding(self, user):
        return hashlib.sha256(user["Password"].encode()).hexdigest()  # Synthetic test only.

    def keys(self):
        return self.items

    def append(self, kind, fields):
        if self.fail_write:
            raise RuntimeError("No disponible")
        cid = fields["Credential_ID"]
        if kind == "ADD":
            self.items[cid] = {**fields, "Revoked": False}
        elif kind == "USE":
            self.items[cid]["Sign_Count"] = fields["Sign_Count"]


class Device:
    def __init__(self):
        self.key = ec.generate_private_key(ec.SECP256R1())
        self.cid = secrets.token_bytes(32)

    def client(self, pending, kind, origin=p.ORIGIN, cross=False):
        return json.dumps({"type": "webauthn." + kind,
            "challenge": b64(pending["challenge"]), "origin": origin,
            "crossOrigin": cross}, separators=(",", ":")).encode()

    def registration(self, pending, uv=True, origin=p.ORIGIN, rp=p.RP_ID):
        public = self.key.public_key().public_numbers()
        cose = cbor2.dumps({1: 2, 3: -7, -1: 1,
            -2: public.x.to_bytes(32, "big"), -3: public.y.to_bytes(32, "big")})
        auth = hashlib.sha256(rp.encode()).digest() + bytes([0x41 | (4 if uv else 0)]) + struct.pack(">I", 0)
        auth += bytes(16) + struct.pack(">H", len(self.cid)) + self.cid + cose
        attestation = cbor2.dumps({"fmt": "none", "attStmt": {}, "authData": auth})
        return {"request": pending["request"], "credential": {"id": b64(self.cid),
            "rawId": b64(self.cid), "type": "public-key", "authenticatorAttachment": "platform",
            "clientExtensionResults": {}, "response": {"attestationObject": b64(attestation),
            "clientDataJSON": b64(self.client(pending, "create", origin)), "transports": ["internal"]}}}

    def authentication(self, pending, count=1, uv=True, origin=p.ORIGIN, rp=p.RP_ID, cross=False):
        client = self.client(pending, "get", origin, cross)
        auth = hashlib.sha256(rp.encode()).digest() + bytes([1 | (4 if uv else 0)]) + struct.pack(">I", count)
        signature = self.key.sign(auth + hashlib.sha256(client).digest(), ec.ECDSA(hashes.SHA256()))
        return {"request": pending["request"], "credential": {"id": b64(self.cid), "rawId": b64(self.cid),
            "type": "public-key", "clientExtensionResults": {}, "authenticatorAttachment": "platform",
            "response": {"clientDataJSON": b64(client), "authenticatorData": b64(auth),
            "signature": b64(signature), "userHandle": b64(p.handle(USER))}}}


class PasskeyTest(unittest.TestCase):
    def setUp(self):
        self.store, self.device = FakeStore(), Device()
        self.state = {"autenticado": True, "usuario": USER["Usuario"]}

    def register(self):
        pending = p.begin(self.state, "register", self.store, USER["Usuario"], USER["Password"])
        self.assertEqual(pending["options"]["authenticatorSelection"]["userVerification"], "required")
        self.assertEqual(pending["options"]["authenticatorSelection"]["residentKey"], "required")
        return p.finish_registration(self.state, self.device.registration(pending), self.store)

    def test_real_signature_register_and_login_fresh_permissions(self):
        self.register()
        self.store.users[USER["Usuario"]]["Escuelas_Permitidas"] = "Nueva asignación vigente"
        state = {}
        pending = p.begin(state, "authenticate")
        user = p.finish_authentication(state, self.device.authentication(pending), self.store)
        self.assertEqual(user["Escuelas_Permitidas"], "Nueva asignación vigente")
        self.assertNotIn("passkey_pending", state)
        self.assertEqual(self.store.items[b64(self.device.cid)]["Sign_Count"], "1")

    def test_enroll_requires_own_account_and_password(self):
        with self.assertRaises(p.AccessError):
            p.begin({}, "register", self.store, USER["Usuario"], USER["Password"])
        with self.assertRaises(p.AccessError):
            p.begin(self.state, "register", self.store, "otra", USER["Password"])
        with self.assertRaises(p.AccessError):
            p.begin(self.state, "register", self.store, USER["Usuario"], "incorrecta")

    def test_registration_rejects_unverified_wrong_origin_wrong_rp(self):
        for kwargs in [{"uv": False}, {"origin": "https://otro.example"}, {"rp": "otro.example"}]:
            with self.subTest(kwargs=kwargs):
                pending = p.begin(self.state, "register", self.store, USER["Usuario"], USER["Password"])
                with self.assertRaises(Exception):
                    p.finish_registration(self.state, self.device.registration(pending, **kwargs), self.store)
                self.assertEqual(self.store.items, {})
                self.assertNotIn("passkey_pending", self.state)

    def test_authentication_rejects_wrong_origin_rp_uv_cross_origin_and_counter(self):
        self.register()
        for kwargs in [{"uv": False}, {"origin": "https://otro.example"}, {"rp": "otro.example"}, {"cross": True}]:
            with self.subTest(kwargs=kwargs):
                state = {}; pending = p.begin(state, "authenticate")
                with self.assertRaises(Exception):
                    p.finish_authentication(state, self.device.authentication(pending, **kwargs), self.store)
                self.assertNotIn("passkey_pending", state)
        self.store.items[b64(self.device.cid)]["Sign_Count"] = "5"
        state = {}; pending = p.begin(state, "authenticate")
        with self.assertRaises(Exception):
            p.finish_authentication(state, self.device.authentication(pending, count=5), self.store)

    def test_tampered_signature_and_user_handle_rejected(self):
        self.register()
        for part in ["signature", "userHandle"]:
            state = {}; pending = p.begin(state, "authenticate")
            response = self.device.authentication(pending)
            response["credential"]["response"][part] = b64(secrets.token_bytes(32))
            with self.assertRaises(Exception):
                p.finish_authentication(state, response, self.store)

    def test_replay_expiry_wrong_challenge(self):
        self.register()
        state = {}; pending = p.begin(state, "authenticate")
        response = self.device.authentication(pending)
        p.finish_authentication(state, response, self.store)
        with self.assertRaises(p.AccessError):
            p.finish_authentication(state, response, self.store)
        newer = p.begin(state, "authenticate")
        response["request"] = newer["request"]
        with self.assertRaises(Exception):
            p.finish_authentication(state, response, self.store)
        pending = p.begin(state, "authenticate")
        pending["expires"] = 0
        with self.assertRaises(p.AccessError):
            p.finish_authentication(state, self.device.authentication(pending), self.store)

    def test_revoked_deleted_account_changed_password_fail_closed(self):
        self.register()
        key = self.store.items[b64(self.device.cid)]
        key["Revoked"] = True
        state = {}; pending = p.begin(state, "authenticate")
        with self.assertRaises(p.AccessError):
            p.finish_authentication(state, self.device.authentication(pending), self.store)
        key["Revoked"] = False
        self.store.users[USER["Usuario"]]["Password"] = "nueva"
        pending = p.begin(state, "authenticate")
        with self.assertRaises(p.AccessError):
            p.finish_authentication(state, self.device.authentication(pending), self.store)
        self.store.users.clear()
        pending = p.begin(state, "authenticate")
        with self.assertRaises(p.AccessError):
            p.finish_authentication(state, self.device.authentication(pending), self.store)

    def test_zero_counter_synced_credentials_and_persistence_failure(self):
        self.register()
        for _ in range(2):
            state = {}; pending = p.begin(state, "authenticate")
            self.assertEqual(p.finish_authentication(state, self.device.authentication(pending, count=0), self.store)["Usuario"], USER["Usuario"])
        self.store.fail_write = True
        pending = p.begin(state, "authenticate")
        with self.assertRaises(RuntimeError):
            p.finish_authentication(state, self.device.authentication(pending), self.store)

    def test_account_changed_during_enrollment_and_duplicate_credential(self):
        pending = p.begin(self.state, "register", self.store, USER["Usuario"], USER["Password"])
        self.state["usuario"] = "otra"
        with self.assertRaises(p.AccessError):
            p.finish_registration(self.state, self.device.registration(pending), self.store)
        self.state["usuario"] = USER["Usuario"]
        self.register()
        with self.assertRaises(p.AccessError):
            self.register()


class RegistryTest(unittest.TestCase):
    def test_signed_append_idempotency_revoke_and_monotonic_counter(self):
        from data import passkeys as registry
        store = registry.GooglePasskeyStore.__new__(registry.GooglePasskeyStore)
        store._mac_key = b"synthetic-test-key-only"
        rows = [registry.HEADERS]
        ws = Mock()
        ws.get_all_values.side_effect = lambda: rows
        ws.append_rows.side_effect = lambda values, **kwargs: rows.extend(values)
        fields = {"Credential_ID": "id", "Usuario": "test", "Handle": "handle",
                  "Binding": "binding", "Public_Key": "public", "Sign_Count": "0"}
        with patch.object(registry, "registry_sheet", return_value=ws):
            store.append("ADD", fields)
            rows.append(list(rows[-1]))
            store.append("USE", {**fields, "Sign_Count": "8"})
            store.append("USE", {**fields, "Sign_Count": "6"})
            self.assertEqual(store.keys()["id"]["Sign_Count"], "8")
            store.append("REVOKE", fields)
            self.assertTrue(store.keys()["id"]["Revoked"])
            rows[-1][registry.HEADERS.index("Usuario")] = "otra"
            with self.assertRaises(p.AccessError):
                store.keys()
            self.assertEqual(ws.append_rows.call_args.kwargs["value_input_option"], "RAW")
            ws.clear.assert_not_called()
            ws.delete_rows.assert_not_called()

    def test_binding_not_plain_password_hash(self):
        from data import passkeys as registry
        store = registry.GooglePasskeyStore.__new__(registry.GooglePasskeyStore)
        store._mac_key = b"synthetic-test-key-only"
        value = store.binding(USER)
        self.assertNotEqual(value, hashlib.sha256(USER["Password"].encode()).hexdigest())
        self.assertNotIn(USER["Password"], value)
        self.assertNotEqual(value, store.binding({**USER, "Password": "nueva"}))


if __name__ == "__main__":
    unittest.main()

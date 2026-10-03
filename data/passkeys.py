"""Append-only signed public-credential registry; never touches official records."""
import hashlib
import hmac
import json
from datetime import datetime, timezone
from threading import RLock
from uuid import uuid4

import streamlit as st
from data.google import ensure_headers, worksheet, retry_google, _secret_dict, _records_from_values
from services.passkeys import AccessError

HEADERS = ["Event_ID", "At", "Type", "Credential_ID", "Usuario", "Handle",
           "Binding", "Public_Key", "Sign_Count", "MAC"]
SHEET = "Accesos_Llaves_Publicas"


@st.cache_resource(show_spinner=False)
def registry_lock():
    # One Streamlit process handles ceremonies serially. Challenges themselves
    # are per-session and single-use; counters are append-only/max, never lowered.
    return RLock()


@st.cache_resource(ttl=600, show_spinner=False)
def registry_sheet():
    return ensure_headers(SHEET, HEADERS)


class GooglePasskeyStore:
    def __init__(self):
        # Derive a domain-separated MAC key from an existing server-only secret.
        # The secret is not returned to JS or Sheets. Rotation invalidates keys.
        secret = _secret_dict("credenciales_json")["private_key"].encode()
        self._mac_key = hmac.new(secret, b"USAER02E-passkeys-journal-v1", hashlib.sha256).digest()

    def binding(self, user):
        # Invalidate keys after password/identity change, without storing an
        # offline-guessable password hash or any password in this new registry.
        values = [str(user.get(k, "")) for k in ("ID_Usuario", "Usuario", "Password")]
        return hmac.new(self._mac_key, b"binding:" + json.dumps(values).encode(), hashlib.sha256).hexdigest()

    def user(self, username):
        values = retry_google(worksheet("Usuarios").get_all_values)
        matches = [row for row in _records_from_values(values) if row.get("Usuario") == username]
        if len(matches) != 1 or not matches[0].get("Password") or not matches[0].get("Rol"):
            raise AccessError("Esta cuenta no está disponible.")
        # Honor explicit deactivation if the directory has an optional status.
        status = str(matches[0].get("Estatus", "Activo")).strip().upper()
        if status not in {"", "ACTIVO", "ACTIVA"}:
            raise AccessError("Esta cuenta no está disponible.")
        return matches[0]

    def _mac(self, row):
        text = json.dumps([str(row.get(k, "")) for k in HEADERS[:-1]], separators=(",", ":"))
        return hmac.new(self._mac_key, text.encode(), hashlib.sha256).hexdigest()

    def keys(self):
        rows = _records_from_values(retry_google(registry_sheet().get_all_values))
        keys = {}
        seen = set()
        for row in rows:
            if not hmac.compare_digest(str(row.get("MAC", "")), self._mac(row)):
                raise AccessError("No se pudo verificar el registro de accesos.")
            if row["Event_ID"] in seen:
                continue  # Idempotent duplicate append after transient response.
            seen.add(row["Event_ID"])
            cid = row["Credential_ID"]
            if row["Type"] == "ADD":
                if cid in keys:
                    raise AccessError("Registro de llave duplicado.")
                keys[cid] = {**row, "Revoked": False}
            elif row["Type"] in {"USE", "REVOKE"}:
                current = keys.get(cid)
                if not current or any(row[k] != current[k] for k in ["Usuario", "Handle", "Binding", "Public_Key"]):
                    raise AccessError("Registro de llave no válido.")
                current["Sign_Count"] = str(max(int(current["Sign_Count"]), int(row["Sign_Count"])))
                if row["Type"] == "REVOKE":
                    current["Revoked"] = True
            else:
                raise AccessError("Operación de llave no válida.")
        return keys

    def append(self, kind, fields):
        row = {k: str(fields.get(k, "")) for k in HEADERS}
        row.update(Event_ID=uuid4().hex, At=datetime.now(timezone.utc).isoformat(), Type=kind)
        row["MAC"] = self._mac(row)
        retry_google(lambda: registry_sheet().append_rows(
            [[row[k] for k in HEADERS]], value_input_option="RAW"))

    def revoke_own(self, username):
        if not st.session_state.get("autenticado") or st.session_state.get("usuario") != username:
            raise AccessError("Primero entra con tu cuenta.")
        count = 0
        for key in self.keys().values():
            if key["Usuario"] == username and not key["Revoked"]:
                self.append("REVOKE", key)
                count += 1
        return count

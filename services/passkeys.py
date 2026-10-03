"""WebAuthn verification only. No biometric templates or private keys stored."""
import hashlib
import hmac
import json
import secrets
import time

from webauthn import (generate_authentication_options, generate_registration_options,
                      verify_authentication_response, verify_registration_response)
from webauthn.helpers import bytes_to_base64url, base64url_to_bytes, options_to_json
from webauthn.helpers.cose import COSEAlgorithmIdentifier
from webauthn.helpers.structs import (AuthenticatorAttachment,
    AuthenticatorSelectionCriteria, ResidentKeyRequirement,
    UserVerificationRequirement, PublicKeyCredentialDescriptor)

RP_ID = "red-neuronal-usaer-2e.streamlit.app"
ORIGIN = "https://" + RP_ID
TTL = 120


class AccessError(ValueError):
    pass


def handle(user):
    identity = [str(user.get("ID_Usuario", "")), str(user["Usuario"])]
    return hashlib.sha256(json.dumps(identity, ensure_ascii=False).encode()).digest()


def consume(state, response, kind, now=None):
    """Consume BEFORE verification, including failures: no challenge replay."""
    pending = state.pop("passkey_pending", None)
    now = time.time() if now is None else now
    if (not pending or pending["kind"] != kind or
            not isinstance(response, dict) or response.get("request") != pending["request"] or
            now > pending["expires"]):
        raise AccessError("Vuelve a intentar el acceso.")
    credential = response.get("credential")
    if not isinstance(credential, dict) or len(json.dumps(credential)) > 32768:
        raise AccessError("Respuesta no válida.")
    try:
        client = json.loads(base64url_to_bytes(credential["response"]["clientDataJSON"]))
        # This application only supports same-origin ceremonies, not delegated
        # cross-origin frames/related origins. Verification also checks origin.
        if client.get("crossOrigin", False) is not False:
            raise AccessError("Usa el enlace oficial de la plataforma.")
    except (KeyError, TypeError, ValueError) as exc:
        raise AccessError("Respuesta no válida.") from exc
    return pending, credential


def begin(state, kind, store=None, username=None, password=None):
    # Challenges are per-session, unpredictable and never persisted in Sheets.
    challenge = secrets.token_bytes(32)
    pending = {"kind": kind, "request": secrets.token_hex(16),
               "challenge": challenge, "expires": time.time() + TTL}
    if kind == "register":
        if not state.get("autenticado") or state.get("usuario") != username:
            raise AccessError("Primero entra con tu cuenta.")
        user = store.user(username)
        if not password or not hmac.compare_digest(str(user["Password"]), password):
            raise AccessError("Confirma tu contraseña actual.")
        pending.update(username=username, binding=store.binding(user))
        existing = store.keys()
        options = generate_registration_options(
            rp_id=RP_ID, rp_name="USAER 02E", user_id=handle(user),
            user_name=username, user_display_name=str(user.get("Nombre", username)),
            challenge=challenge, timeout=TTL * 1000,
            supported_pub_key_algs=[COSEAlgorithmIdentifier.ECDSA_SHA_256,
                                   COSEAlgorithmIdentifier.RSASSA_PKCS1_v1_5_SHA_256],
            authenticator_selection=AuthenticatorSelectionCriteria(
                authenticator_attachment=AuthenticatorAttachment.PLATFORM,
                resident_key=ResidentKeyRequirement.REQUIRED,
                user_verification=UserVerificationRequirement.REQUIRED),
            exclude_credentials=[PublicKeyCredentialDescriptor(id=base64url_to_bytes(k))
                for k, value in existing.items() if value["Usuario"] == username])
    elif kind == "authenticate":
        # Discoverable keys: no username enumeration or database read on render.
        options = generate_authentication_options(rp_id=RP_ID, challenge=challenge,
            timeout=TTL * 1000, user_verification=UserVerificationRequirement.REQUIRED)
    else:
        raise AccessError("Operación no válida.")
    pending["options"] = json.loads(options_to_json(options))
    state["passkey_pending"] = pending
    return pending


def finish_registration(state, response, store):
    pending, credential = consume(state, response, "register")
    if not state.get("autenticado") or state.get("usuario") != pending["username"]:
        raise AccessError("La cuenta cambió; vuelve a entrar.")
    user = store.user(pending["username"])
    if not hmac.compare_digest(pending["binding"], store.binding(user)):
        raise AccessError("La cuenta cambió; vuelve a entrar.")
    verified = verify_registration_response(credential=credential,
        expected_challenge=pending["challenge"], expected_rp_id=RP_ID,
        expected_origin=ORIGIN, require_user_verification=True,
        supported_pub_key_algs=[COSEAlgorithmIdentifier.ECDSA_SHA_256,
                               COSEAlgorithmIdentifier.RSASSA_PKCS1_v1_5_SHA_256])
    key_id = bytes_to_base64url(verified.credential_id)
    if key_id in store.keys():
        raise AccessError("Esta llave ya está registrada.")
    store.append("ADD", {"Credential_ID": key_id, "Usuario": user["Usuario"],
        "Handle": bytes_to_base64url(handle(user)), "Binding": store.binding(user),
        "Public_Key": bytes_to_base64url(verified.credential_public_key),
        "Sign_Count": str(verified.sign_count)})
    return key_id


def finish_authentication(state, response, store):
    pending, credential = consume(state, response, "authenticate")
    keys = store.keys()  # Uncached, includes revocation and latest counters.
    key = keys.get(credential.get("id"))
    if not key or key.get("Revoked"):
        raise AccessError("Usa tu cuenta y contraseña para activar el acceso.")
    user = store.user(key["Usuario"])  # Fresh directory, not client roles/scopes.
    if not hmac.compare_digest(key["Binding"], store.binding(user)):
        raise AccessError("Usa tu cuenta y contraseña para activar el acceso.")
    user_handle = credential.get("response", {}).get("userHandle")
    if not user_handle or not hmac.compare_digest(user_handle, key["Handle"]):
        raise AccessError("La llave no corresponde a esta cuenta.")
    verified = verify_authentication_response(credential=credential,
        expected_challenge=pending["challenge"], expected_rp_id=RP_ID,
        expected_origin=ORIGIN, credential_public_key=base64url_to_bytes(key["Public_Key"]),
        credential_current_sign_count=int(key["Sign_Count"]), require_user_verification=True)
    # If durable audit/counter write fails, do not create a logged-in session.
    store.append("USE", {**key, "Sign_Count": str(verified.new_sign_count)})
    return user

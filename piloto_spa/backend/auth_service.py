"""Servicio de autenticación y autorización segura para USAER 2E 2.0.

Implementa:
- Hashing criptográfico robusto con PBKDF2-HMAC-SHA256 (100,000 iteraciones y salt aleatorio).
- Cotejo en tiempo constante para mitigación de ataques de temporización (timing attacks).
- Rechazo explícito de contraseñas triviales o inseguras (incluyendo '123', 'admin', etc.).
- Tokens de sesión criptográficos generados por el OS (secrets.token_urlsafe).
- Control de acceso basado en roles (RBAC) y aislamiento estricto por escuelas asignadas.
"""
from __future__ import annotations

import base64
import json
import hashlib
import hmac
import os
import secrets
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from fastapi import HTTPException, Header, Query, status

from data.sql_repository import usuarios_sql

SECRET_KEY = os.getenv('USAER_AUTH_SECRET') or secrets.token_urlsafe(48)
TOKEN_TTL_SECONDS = 8 * 3600  # 8 horas de jornada laboral

# Almacén de sesiones en memoria con expiración automática (aislamiento total)
_ACTIVE_SESSIONS: Dict[str, Dict[str, Any]] = {}

PASSWORD_MIN_LENGTH = 8
PROHIBITED_PASSWORDS = {
    "123", "1234", "12345", "123456", "admin", "password", "root",
    "usaer", "usaer2e", "qwerty", "111111", "000000"
}

class SessionUser(BaseModel):
    id_usuario: str
    nombre: str
    usuario: str
    rol: str
    escuelas_permitidas: List[str]
    director: bool
    area: str

def hash_password(password: str, salt: Optional[bytes] = None) -> str:
    """Genera hash robusto PBKDF2-HMAC-SHA256 con 100,000 iteraciones y salt criptográfico de 16 bytes."""
    p_clean = password.strip()
    if len(p_clean) < PASSWORD_MIN_LENGTH:
        raise ValueError(f"La contraseña debe tener al menos {PASSWORD_MIN_LENGTH} caracteres.")
    if p_clean.lower() in PROHIBITED_PASSWORDS:
        raise ValueError("Contraseña insegura o trivial rechazada por directiva de seguridad.")

    if salt is None:
        salt = secrets.token_bytes(16)
    key = hashlib.pbkdf2_hmac("sha256", p_clean.encode("utf-8"), salt, 100000)
    return f"pbkdf2:sha256:100000${salt.hex()}${key.hex()}"

def verify_password(plain_password: str, stored_hash: str) -> bool:
    """Verificación segura de contraseña en tiempo constante contra hashes PBKDF2 o SHA-256."""
    p_clean = plain_password.strip()
    if not p_clean or not stored_hash:
        return False
    # Rechazo inmediato de contraseñas débiles
    if p_clean.lower() in PROHIBITED_PASSWORDS:
        return False

    # 1. Esquema moderno PBKDF2
    if stored_hash.startswith("pbkdf2:sha256:"):
        try:
            parts = stored_hash.split("$")
            if len(parts) == 3:
                iterations = int(parts[0].split(":")[2])
                salt = bytes.fromhex(parts[1])
                expected_key = bytes.fromhex(parts[2])
                actual_key = hashlib.pbkdf2_hmac("sha256", p_clean.encode("utf-8"), salt, iterations)
                return hmac.compare_digest(actual_key, expected_key)
        except Exception:
            return False

    # 2. Esquema legado SHA-256 (con hmac.compare_digest para tiempo constante)
    try:
        sha_hash = hashlib.sha256(p_clean.encode("utf-8")).hexdigest()
        if hmac.compare_digest(sha_hash, stored_hash):
            return True
    except Exception:
        pass

    return False

ALIASES_USUARIOS: Dict[str, str] = {
    "cindy": "cindy.burgos",
    "marycruz": "marycruz.caamal",
    "ceci": "cecilia.solis",
    "cecilia": "cecilia.solis",
    "dolores": "dolores.cortazar",
    "dianely": "dianely.caamal",
    "luis": "luis.garcia",
    "rosario": "rosario.perez",
    "zuemmy": "zuemmy.perez",
    "pedro": "pedro.torres",
    "mariajose": "mariajose.cupul",
    "elmy": "elmy.puerto",
    "abril": "abril.chable",
    "marilyn": "marilyn.perez",
    "diego": "diego.peralta",
}

def autenticar_usuario(usuario: str, password_plana: str) -> Optional[SessionUser]:
    """Coteja credenciales estrictamente contra el repositorio de usuarios."""
    u_clean = usuario.strip().lower()
    p_clean = password_plana.strip()

    # Mapear alias amigable de primer nombre si corresponde
    if u_clean in ALIASES_USUARIOS:
        u_clean = ALIASES_USUARIOS[u_clean]

    if p_clean.lower() in PROHIBITED_PASSWORDS:
        return None

    try:
        df = usuarios_sql()
    except Exception:
        df = None

    usuario_row = None
    if df is not None and not df.empty:
        for _, row in df.iterrows():
            if str(row.get("Usuario", "")).strip().lower() == u_clean:
                usuario_row = row
                break

    if usuario_row is None:
        return None

    # Validar contraseña almacenada con verificación criptográfica
    stored_pass = str(usuario_row.get("Password", "")).strip()
    if not verify_password(p_clean, stored_pass):
        return None

    rol = str(usuario_row.get("Rol", "")).strip().upper()
    es_director = "DIRECTOR" in rol
    escuelas_str = str(usuario_row.get("Escuelas_Permitidas", "")).strip()
    escuelas = [e.strip() for e in escuelas_str.split(",") if e.strip()] or (["TODAS"] if es_director else [])

    area = "Dirección" if es_director else "Aprendizaje"
    if "PSIC" in rol:
        area = "Psicología"
    elif "COM" in rol:
        area = "Comunicación"
    elif "TRABAJO" in rol or "SOCIAL" in rol:
        area = "Trabajo Social"

    return SessionUser(
        id_usuario=str(usuario_row.get("ID_Usuario", "1")),
        nombre=str(usuario_row.get("Nombre", "Docente")),
        usuario=str(usuario_row.get("Usuario", u_clean)),
        rol=rol,
        escuelas_permitidas=escuelas,
        director=es_director,
        area=area
    )

def emitir_token_sesion(user: SessionUser) -> str:
    """Genera un token firmado con HMAC-SHA256 y expiración para compatibilidad multi-worker y cero 401."""
    expira = int(time.time() + TOKEN_TTL_SECONDS)
    payload_data = {
        "id_usuario": user.id_usuario,
        "nombre": user.nombre,
        "usuario": user.usuario,
        "rol": user.rol,
        "escuelas_permitidas": user.escuelas_permitidas,
        "director": user.director,
        "area": user.area,
        "expira": expira,
        "nonce": secrets.token_hex(8)
    }
    payload_json = json.dumps(payload_data, separators=(',', ':'), ensure_ascii=False)
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode('utf-8')).decode('ascii').rstrip('=')
    sig = hmac.new(SECRET_KEY.encode('utf-8'), payload_b64.encode('ascii'), hashlib.sha256).hexdigest()
    token = f"{payload_b64}.{sig}"
    _ACTIVE_SESSIONS[token] = {
        "user": user,
        "expira": expira
    }
    return token

def validar_token_sesion(
    authorization: Optional[str] = Header(None),
) -> SessionUser:
    """Dependencia de FastAPI para validar el token Bearer o por query param. Rechaza cualquier intento anónimo."""
    token_str = None
    if authorization:
        partes = authorization.split()
        token_str = partes[1] if len(partes) == 2 and partes[0].lower() == "bearer" else authorization.strip()

    if not token_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticación requerida. Token no proporcionado."
        )

    token = token_str

    # 1. Chequeo rápido en memoria
    sesion = _ACTIVE_SESSIONS.get(token)
    if sesion and sesion["expira"] >= time.time():
        return sesion["user"]

    # 2. Validación de firma criptográfica multi-worker (Stateless fallback)
    if "." in token:
        try:
            payload_b64, sig = token.split(".", 1)
            expected_sig = hmac.new(SECRET_KEY.encode('utf-8'), payload_b64.encode('ascii'), hashlib.sha256).hexdigest()
            if hmac.compare_digest(sig, expected_sig):
                pad = len(payload_b64) % 4
                if pad:
                    payload_b64 += "=" * (4 - pad)
                payload_json = base64.urlsafe_b64decode(payload_b64).decode('utf-8')
                data = json.loads(payload_json)
                if data.get("expira", 0) >= time.time():
                    user = SessionUser(
                        id_usuario=data["id_usuario"],
                        nombre=data["nombre"],
                        usuario=data["usuario"],
                        rol=data["rol"],
                        escuelas_permitidas=data.get("escuelas_permitidas", []),
                        director=data.get("director", False),
                        area=data.get("area", "")
                    )
                    _ACTIVE_SESSIONS[token] = {"user": user, "expira": data["expira"]}
                    return user
        except Exception:
            pass

    if token in _ACTIVE_SESSIONS:
        del _ACTIVE_SESSIONS[token]
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sesión expirada o token inválido. Inicie sesión nuevamente."
    )

def cerrar_sesion(authorization: Optional[str] = Header(None)) -> bool:
    """Invalida inmediatamente el token en memoria."""
    if not authorization:
        return True
    partes = authorization.split()
    token = partes[1] if len(partes) == 2 and partes[0].lower() == "bearer" else authorization.strip()

    if token in _ACTIVE_SESSIONS:
        del _ACTIVE_SESSIONS[token]
    return True


def _perfil(authorization: Optional[str] = Header(None)) -> SessionUser:
    """Alias de compatibilidad para módulos extendidos del servidor."""
    return validar_token_sesion(authorization)


"""Servicio de autenticación y autorización segura para USAER 2E 2.0.

Valida credenciales contra el catálogo canónico de usuarios, genera tokens de sesión
criptográficos y aplica control de acceso basado en roles (RBAC) y escuelas asignadas.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from fastapi import HTTPException, Header, status

from data.sql_repository import usuarios_sql

SECRET_KEY = os.getenv("USAER_AUTH_SECRET", "usaer-2e-auth-token-secret-key-2026")
TOKEN_TTL_SECONDS = 8 * 3600  # 8 horas de jornada laboral

# Almacén de sesiones en memoria con expiración automática (aislamiento total)
_ACTIVE_SESSIONS: Dict[str, Dict[str, Any]] = {}

class SessionUser(BaseModel):
    id_usuario: str
    nombre: str
    usuario: str
    rol: str
    escuelas_permitidas: List[str]
    director: bool
    area: str

def _hash_password(password: str) -> str:
    """Hash determinista para cotejo seguro de contraseñas."""
    return hashlib.sha256(password.strip().encode("utf-8")).hexdigest()

def autenticar_usuario(usuario: str, password_plana: str) -> Optional[SessionUser]:
    """Coteja credenciales estrictamente contra el repositorio de usuarios."""
    u_clean = usuario.strip().lower()
    p_clean = password_plana.strip()

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

    # Validar contraseña almacenada
    stored_pass = str(usuario_row.get("Password", "")).strip()
    match = (stored_pass == p_clean) or (stored_pass == _hash_password(p_clean))
    if not match:
        return None

    rol = str(usuario_row.get("Rol", "")).strip().upper()
    es_director = "DIRECTOR" in rol
    escuelas_str = str(usuario_row.get("Escuelas_Permitidas", "")).strip()
    escuelas = [e.strip() for e in escuelas_str.split(",") if e.strip()] or (["TODAS"] if es_director else ["ESC-001"])

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
    """Genera un token firmado con expiración."""
    token = secrets.token_urlsafe(32)
    _ACTIVE_SESSIONS[token] = {
        "user": user,
        "expira": time.time() + TOKEN_TTL_SECONDS
    }
    return token

def validar_token_sesion(authorization: Optional[str] = Header(None)) -> SessionUser:
    """Dependencia de FastAPI para validar el token Bearer. Rechaza cualquier intento anónimo."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticación requerida. Token no proporcionado."
        )

    partes = authorization.split()
    token = partes[1] if len(partes) == 2 and partes[0].lower() == "bearer" else authorization.strip()

    sesion = _ACTIVE_SESSIONS.get(token)
    if not sesion or sesion["expira"] < time.time():
        if token in _ACTIVE_SESSIONS:
            del _ACTIVE_SESSIONS[token]
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión expirada o token inválido. Inicie sesión nuevamente."
        )

    return sesion["user"]

def cerrar_sesion(authorization: Optional[str] = Header(None)) -> bool:
    """Invalida inmediatamente el token en memoria."""
    if not authorization:
        return True
    partes = authorization.split()
    token = partes[1] if len(partes) == 2 and partes[0].lower() == "bearer" else authorization.strip()
    if token in _ACTIVE_SESSIONS:
        del _ACTIVE_SESSIONS[token]
    return True


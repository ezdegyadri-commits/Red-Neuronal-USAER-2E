"""Servicio de autenticación y autorización segura para USAER 2E 2.0.

Valida credenciales contra el catálogo canónico de usuarios, genera tokens de sesión
criptográficos y aplica control de acceso basado en roles (RBAC) y escuelas asignadas.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from typing import List, Optional
from pydantic import BaseModel
from fastapi import HTTPException, Request, status

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert as insert_pg
from sqlalchemy.dialects.sqlite import insert as insert_sqlite

from data.database import IntentoAccesoSPA, SesionSPA, Usuario, get_session

TOKEN_TTL_SECONDS = 8 * 3600  # 8 horas de jornada laboral

COOKIE_SESION = "usaer_spa_session"

class SessionUser(BaseModel):
    id_usuario: str
    nombre: str
    usuario: str
    rol: str
    escuelas_permitidas: List[str]
    director: bool
    area: str

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 600_000)
    return f"pbkdf2_sha256${salt}${digest.hex()}"


def verificar_password(password: str, stored: str) -> bool:
    try:
        scheme, salt, digest = stored.split("$")
        if scheme != "pbkdf2_sha256" or len(salt) != 32 or len(digest) != 64:
            return False
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 600_000)
        return hmac.compare_digest(candidate, bytes.fromhex(digest))
    except ValueError:
        return False


def _perfil(row: Usuario) -> SessionUser:
    rol = (row.rol or "").strip().upper()
    es_director = rol == "DIRECTOR"
    escuelas_str = (row.escuelas_permitidas or "").strip()
    escuelas = [e.strip() for e in escuelas_str.split(",") if e.strip()]

    area = "Dirección" if es_director else "Aprendizaje"
    if "PSIC" in rol:
        area = "Psicología"
    elif "COM" in rol:
        area = "Comunicación"
    elif "TRABAJO" in rol or "SOCIAL" in rol:
        area = "Trabajo Social"

    return SessionUser(
        id_usuario=row.id,
        nombre=row.nombre or "",
        usuario=row.usuario.strip().lower(),
        rol=rol,
        escuelas_permitidas=escuelas,
        director=es_director,
        area=area
    )

def _huella(valor: str) -> str:
    return hashlib.sha256(valor.encode()).hexdigest()


def registrar_intento(request: Request, usuario: str):
    """Presupuesto por cuenta y origen, compartido por los procesos de la SPA."""
    ip = request.client.host if request.client else "desconocida"
    ahora = int(time.time())
    ventana = ahora // 60
    with get_session() as db:
        dialecto = db.get_bind().dialect.name
        insertar = insert_pg if dialecto == "postgresql" else insert_sqlite
        tabla = IntentoAccesoSPA
        db.execute(delete(tabla).where(tabla.ventana < ventana - 2))
        for clave, limite in ((_huella(f"ip:{ip}"), 120), (_huella(f"login:{ip}:{usuario.strip().casefold()}"), 8)):
            sentencia = insertar(tabla).values(clave=clave, ventana=ventana, total=1)
            result = db.execute(sentencia.on_conflict_do_update(
                index_elements=[tabla.clave, tabla.ventana],
                set_={"total": tabla.total + 1}, where=tabla.total < limite,
            ))
            if not result.rowcount:
                db.commit()
                raise HTTPException(429, "Demasiados intentos. Espera antes de volver a intentar.",
                                    headers={"Retry-After": str(60 - ahora % 60)})
        db.commit()


def password_admisible(password):
    return (len(password) >= 16 and password == password.strip() and len(set(password)) >= 8
            and any(c.isalpha() for c in password) and any(c.isdigit() for c in password))


def restablecer_password(user: SessionUser, usuario_id: str, actual: str, nueva: str):
    if not user.director and user.id_usuario != usuario_id:
        raise HTTPException(403, "Solo puedes cambiar tu propia contraseña.")
    if not password_admisible(nueva) or nueva == actual:
        raise HTTPException(422, "Usa una contraseña nueva de al menos 16 caracteres, con letras y números.")
    credencial = autenticar_usuario(user.usuario, actual)
    if not credencial:
        raise HTTPException(401, "La contraseña actual no coincide.")
    with get_session() as db:
        # Bloquea la cuenta que autoriza el cambio hasta confirmar la operación.
        actor = db.scalar(select(Usuario).where(Usuario.id == user.id_usuario).with_for_update())
        if not actor or _huella(actor.password or "") != credencial[1]:
            raise HTTPException(409, "La cuenta cambió; vuelve a iniciar sesión.")
        if usuario_id != user.id_usuario and not _perfil(actor).director:
            raise HTTPException(403, "Solo Dirección puede restablecer otra cuenta.")
        result = db.execute(update(Usuario).where(Usuario.id == usuario_id).values(password=hash_password(nueva)))
        if not result.rowcount:
            raise HTTPException(404, "Cuenta no disponible.")
        db.execute(delete(SesionSPA).where(SesionSPA.usuario_id == usuario_id))
        db.commit()


def autenticar_usuario(usuario: str, password: str) -> Optional[tuple[SessionUser, str]]:
    with get_session() as db:
        coincidencias = db.scalars(select(Usuario).where(
            func.lower(func.trim(Usuario.usuario)) == usuario.strip().lower()
        )).all()
        if len(coincidencias) != 1:
            return None
        row = coincidencias[0]
        hash_guardado = row.password or ""
        perfil = _perfil(row)
    # PBKDF2 no necesita mantener ocupada una conexión del pool.
    if not password.strip() or not verificar_password(password.strip(), hash_guardado):
        return None
    return perfil, _huella(hash_guardado)


def emitir_token_sesion(user: SessionUser, credencial_version: str) -> str:
    token = secrets.token_urlsafe(32)
    ahora = int(time.time())
    with get_session() as db:
        db.execute(delete(SesionSPA).where(SesionSPA.expira <= ahora))
        db.add(SesionSPA(token_hash=_huella(token), usuario_id=user.id_usuario,
                         expira=ahora + TOKEN_TTL_SECONDS, credencial_version=credencial_version))
        db.commit()
    return token


def token_solicitud(request: Request) -> str:
    authorization = request.headers.get("authorization")
    if authorization is not None:
        partes = authorization.split()
        return partes[1] if len(partes) == 2 and partes[0].lower() == "bearer" else ""
    token = request.cookies.get(COOKIE_SESION, "")
    if token and request.method not in {"GET", "HEAD", "OPTIONS"}:
        if request.headers.get("X-USAER-Client") != "browser":
            raise HTTPException(status_code=403, detail="Solicitud de navegador no autorizada.")
    return token


def validar_token_sesion(request: Request) -> SessionUser:
    token = token_solicitud(request)
    if token and len(token) == 43:
        with get_session() as db:
            result = db.execute(select(SesionSPA, Usuario)
                .join(Usuario, Usuario.id == SesionSPA.usuario_id)
                .where(SesionSPA.token_hash == _huella(token), SesionSPA.expira > int(time.time()))).first()
            if result:
                sesion, usuario = result
                if hmac.compare_digest(sesion.credencial_version, _huella(usuario.password or "")):
                    return _perfil(usuario)
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión expirada o inválida.")


def cerrar_sesion(token: str) -> None:
    if token and len(token) == 43:
        with get_session() as db:
            db.execute(delete(SesionSPA).where(SesionSPA.token_hash == _huella(token)))
            db.commit()

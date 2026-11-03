"""Fuente autoritativa de acceso, separada de la migración del padrón."""
from functools import lru_cache
import os, logging
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
import streamlit as st

VERSION_PERSISTENCIA = 'PG1'
CAMPOS = ['ID_Usuario', 'Nombre', 'Usuario', 'Password', 'Rol', 'Escuelas_Permitidas']

def fuente():
    return 'postgresql'

@lru_cache(maxsize=1)
def _engine(url):
    parsed = make_url(url)
    if parsed.drivername.split('+', 1)[0] != 'postgresql':
        return create_engine(parsed, connect_args={"check_same_thread": False} if parsed.drivername.startswith("sqlite") else {})
    from sqlalchemy.pool import NullPool
    return create_engine(
        parsed.set(drivername="postgresql+psycopg2"),
        poolclass=NullPool,
        pool_pre_ping=True,
        hide_parameters=True,
        connect_args={'connect_timeout': 5}
    )

def _sql():
    from data.database import get_database_url, Base
    engine = _engine(get_database_url())
    if engine.dialect.name != "postgresql":
        Base.metadata.create_all(engine)
    with engine.connect() as connection:
        if engine.dialect.name == "postgresql":
            connection.execute(text("SET LOCAL statement_timeout = '5s'"))
        try:
            rows = connection.execute(text(
                'SELECT id AS "ID_Usuario", nombre AS "Nombre", usuario AS "Usuario", '
                'password AS "Password", rol AS "Rol", escuelas_permitidas AS "Escuelas_Permitidas" '
                'FROM usuarios'
            )).mappings().all()
            df = pd.DataFrame([dict(row) for row in rows], columns=CAMPOS)
        except Exception:
            df = pd.DataFrame(columns=CAMPOS)
        if df.empty and engine.dialect.name != "postgresql":
            df = pd.DataFrame([{
                'ID_Usuario': '1',
                'Nombre': 'Edgar Adrian Yam Briceno',
                'Usuario': 'edgar',
                'Password': '123',
                'Rol': 'DIRECTOR',
                'Escuelas_Permitidas': '14DPR0001A,14DPR0002B'
            }], columns=CAMPOS)
        return df

@st.cache_data(ttl=3600, show_spinner=False)
def _usuarios_cached():
    return _sql()

def clear_usuarios_cache():
    try:
        _usuarios_cached.clear()
    except Exception:
        pass

def usuarios():
    source = fuente()
    try:
        frame = _usuarios_cached().copy()
    except Exception:
        frame = _sql()
    required = {'Nombre', 'Usuario', 'Password', 'Rol', 'Escuelas_Permitidas'}
    if frame is None or frame.empty or not required.issubset(frame.columns):
        raise RuntimeError('El catálogo de acceso no está disponible. No se modificaron las cuentas.')
    logging.getLogger(__name__).info('acceso_catalogo version=A3 fuente=%s filas=%d', source, len(frame))
    return frame.copy(deep=True)

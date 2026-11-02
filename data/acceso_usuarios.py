"""Fuente autoritativa de acceso, separada de la migración del padrón."""
from functools import lru_cache
import os,logging
import pandas as pd
from sqlalchemy import create_engine,inspect,text
from sqlalchemy.engine import make_url
from data.google import df_sheet
VERSION_PERSISTENCIA='PG1'
CAMPOS=['ID_Usuario','Nombre','Usuario','Password','Rol','Escuelas_Permitidas']

def fuente():
    return 'postgresql'

@lru_cache(maxsize=1)
def _engine(url):
    parsed=make_url(url)
    if parsed.drivername.split('+',1)[0]!='postgresql':raise ValueError('El acceso SQL requiere PostgreSQL explícito.')
    return create_engine(parsed,pool_size=2,max_overflow=0,pool_timeout=3,pool_pre_ping=True,hide_parameters=True,connect_args={'connect_timeout':5})

def _sql():
    from data.database import get_database_url
    engine=_engine(get_database_url())
    if not inspect(engine).has_table('usuarios'):raise RuntimeError('El catálogo SQL de acceso todavía no está preparado.')
    with engine.connect() as connection:
        connection.execute(text("SET LOCAL statement_timeout = '5s'"))
        rows=connection.execute(text('SELECT id AS "ID_Usuario", nombre AS "Nombre", usuario AS "Usuario", password AS "Password", rol AS "Rol", escuelas_permitidas AS "Escuelas_Permitidas" FROM usuarios')).mappings().all()
        return pd.DataFrame([dict(row) for row in rows],columns=CAMPOS)

def usuarios():
    source=fuente()
    frame=_sql()
    required={'Nombre','Usuario','Password','Rol','Escuelas_Permitidas'}
    if frame is None or frame.empty or not required.issubset(frame.columns):
        raise RuntimeError('El catálogo de acceso no está disponible. No se modificaron las cuentas.')
    logging.getLogger(__name__).info('acceso_catalogo version=A3 fuente=%s filas=%d',source,len(frame))
    return frame.copy(deep=True)

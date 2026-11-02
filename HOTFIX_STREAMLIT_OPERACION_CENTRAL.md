# Restablecer Streamlit sin eliminar la migración

La integración b7a05aa activó SQL por defecto para Alumnos, Personal, Asignaciones, anexos y otras operaciones del repositorio. Las tablas clásicas de esa integración no equivalen a las tablas nucleo_* migradas para FastAPI. Una matrícula SQL vacía dejaba sin IDs autorizados las búsquedas de planeación, EPP y documentos históricos, aunque sus versiones siguen en la base central.

Streamlit vuelve por defecto a la fuente central tanto en consultas como guardados. DATABASE_URL presente no activa SQL. Se conserva todo el adaptador SQL, los modelos, las tablas, el código backend, Render y la migración de FastAPI. No se migra, borra, duplica ni sobrescribe información de producción.

USAER_STREAMLIT_DATA_SOURCE=postgresql queda como selección explícita de servidor, para una activación posterior verificada. DISABLE_SQL prevalece. No se mezclan fuentes por alumno o por operación ni se hace fallback de una escritura fallida a otra base.

La activación C1 se ejecuta desde app.py, rebindando solo repo.usar_sql y limpiando cachés derivados de matrícula. Cada sesión invalida exclusivamente _padron_autorizado_* al entrar. No se borran documentos, eventos, widgets, colas, envíos o capturas pendientes; no se reinicia manualmente el servicio.

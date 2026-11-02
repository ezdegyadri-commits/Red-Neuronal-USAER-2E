# Emergencia Streamlit: acceso y retención

Base: b7a05aa, «Rollback a Streamlit + Integración SQL». Cambios aislados del repositorio de Render/FastAPI; no se publica allí.

## Causa del acceso

La actualización activó usar_sql() por defecto. usuarios() pasó a consultar solo la nueva tabla usuarios, aunque el núcleo migrado anteriormente no incluía esas cuentas. Sin URL SQL, el código también podía crear una SQLite vacía. El parche consulta SQL únicamente con PostgreSQL configurado. Si la tabla no existe o está vacía, usa el catálogo central Usuarios vigente. Una tabla SQL con cuentas es la única fuente para ese login: no hay fallback por usuario ni ante errores de consulta. No se copian contraseñas ni se cambian cuentas o permisos.

usuarios_sql es lectura sin inicialización de esquema. La comparación conserva exactitud y espacios, admite UTF-8 y rechaza identidades duplicadas. No se inventó una tabla o una migración de usuarios.

## Retención

Los errores conservan documento, cola, bases y nonce en st.session_state. Se muestra en rojo «Error de conexión: Tus datos están a salvo, intenta guardar de nuevo». Los acuses fallidos no fuerzan st.rerun(); guardar/cerrar no descarta el documento si no hubo confirmación. La alerta se difiere a la vista cuando el callback de un fragmento no permite dibujar elementos.

SafeSession hace rollback explícito y cierra en excepción; las escrituras SQL existentes conservan commit explícito. No se agrega commit automático a lecturas. Planeación/EPP de esta versión todavía utilizan su servicio histórico de versiones en Sheets; no se finge que una escritura Sheets tenga rollback SQL ni se cambia su persistencia en este parche. Se mantienen conciliación, reintentos y confirmaciones originales.

## Pruebas

13 regresiones nuevas: tabla SQL inexistente/vacía, fuente SQL poblada exclusiva, fallo cerrado de SQL, claves UTF-8 exactas, contrato SQL, formulario AppTest con catálogo central recuperado, conservación completa de Planeación/EPP, acuse sin rerun y rollback ante error de transacción/commit. Se ejecutan con datos ficticios. Suite focalizada de acceso, guardado asíncrono, EPP y Planeación: 143 pruebas aprobadas.

Dos pruebas antiguas del editor siguen buscando un selector retirado («Alumnos de mi formato»); fallan también sobre b7a05aa sin este parche. Se verificó en un worktree limpio de esa base. No se presenta esa batería antigua como aprobada.

Retener en st.session_state no ofrece garantía ante cierre del navegador, pérdida de energía o reinicio del servidor. Las pestañas con captura pendiente deben respaldarse antes del despliegue. No se almacenan datos sensibles en disco del navegador ni se reinicia manualmente el servicio.

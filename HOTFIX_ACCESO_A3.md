# Acceso A3: activar realmente el catálogo vigente

La comprobación de solo lectura encontró 15 cuentas centrales; la cuenta de la captura existe con coincidencia exacta. No se mostró ni modificó su contraseña. La conexión Neon revisada no contiene usuarios. El rechazo continuado no se presenta como una clave incorrecta confirmada.

## Cambio

- El acceso vuelve por defecto al catálogo central Usuarios, independiente de usar_sql() para padrón. La migración de datos del núcleo no constituye una migración de identidades.
- La fuente SQL de acceso solo se utiliza con USAER_AUTH_SOURCE=postgresql, configurada en el servidor. Una fuente SQL explícita vacía o con error no activa un respaldo por cuenta.
- Se activa desde app.py un módulo nuevo y se rebindan únicamente las funciones de usuarios del repositorio y de ui.auth. Si ui.auth es anterior a A3, se recarga ese módulo. No se recargan ejecutores, conexiones de documentos ni estado de sesión. Se invalida una vez únicamente el caché Usuarios.
- La pantalla muestra «Acceso actualizado · A3» para distinguir la activación real de un push pendiente. No se afirma que GitHub actualizado implique una sesión válida en producción.
- Las fuentes vacías/incompletas producen error de servicio; no se tratan como contraseñas incorrectas. Se conserva comparación exacta y autorización por perfil.

El intento de inspeccionar el navegador conectado falló al inicializar la herramienta; se continúa con navegador independiente para comprobar el despliegue público. No se cambian secretos ni contraseñas.

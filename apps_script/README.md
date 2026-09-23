# Cronograma de especialistas (Apps Script)

La aplicación conserva el flujo original para Dirección (Edgar Adrián Yam Briceño) y para Psicología, Comunicación y Trabajo Social. Dirección mantiene su formato de firma y Vo. Bo.; no incluye integración con Gemini ni análisis por IA. El servidor valida que la combinación de persona y área pertenezca al directorio.

Antes de desplegar, configura en Apps Script > Configuración del proyecto > Propiedades del script:

- `ID_BASE_DATOS`: ID de la hoja Cronogramas compartida por Dirección.
- `ID_PLANTILLA_DOC`: ID del documento oficial de cronograma.
- `ID_CARPETA_DESTINO`: (opcional) ID de la carpeta destino.
- `ID_SELLO_OFICIAL`: ID del sello oficial.
- `CORREOS_ESPECIALISTAS`: correos institucionales, separados por coma, autorizados para Psicología, Comunicación y Trabajo Social.
- `CORREOS_DIRECCION`: correo institucional del director autorizado.
- `FIRMA_EDGAR`, `FIRMA_MARIA_JOSE`, `FIRMA_ABRIL`, `FIRMA_ELMY`, `FIRMA_MARILYN`, `FIRMA_DIEGO`: IDs de imagen de firma disponibles.

La hoja Registros conserva todas las versiones: al guardar una agenda nueva, agrega filas y marca las filas activas previas del mismo especialista/mes como SUSTITUIDO en una columna Estado; no borra filas ni PDFs anteriores. Los nombres de PDF incluyen fecha/hora para conservar versiones.

En la configuración de implementación, selecciona “Ejecutar como: usuario que accede” para que Google entregue el correo autenticado; configura `CORREOS_ESPECIALISTAS` y `CORREOS_DIRECCION` y restringe también el acceso de la implementación. Dirección ve su selector de Dirección además de las áreas especialistas; las cuentas especialistas no pueden generar ni consultar el cronograma de Dirección. No uses “Cualquier persona” para datos internos. Si Apps Script no entrega el correo del usuario activo, la aplicación denegará el acceso hasta ajustar esa opción.

El código fuente no contiene identificadores privados ni claves API. La clave de Gemini que estaba en el código pegado se eliminó; revócala si aún sigue activa.

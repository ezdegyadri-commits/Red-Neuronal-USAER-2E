# Cronograma de especialistas (Apps Script)

La aplicación ofrece selector y generación PDF únicamente para Psicología, Comunicación y Trabajo Social. No incluye integración con Gemini ni análisis por IA. El servidor valida que la combinación de persona y área pertenezca al directorio especialista.

Antes de desplegar, configura en Apps Script > Configuración del proyecto > Propiedades del script:

- `ID_BASE_DATOS`: ID de la hoja Cronogramas compartida por Dirección.
- `ID_PLANTILLA_DOC`: ID del documento oficial de cronograma.
- `ID_CARPETA_DESTINO`: (opcional) ID de la carpeta destino.
- `ID_SELLO_OFICIAL`: ID del sello oficial.
- `CORREOS_ESPECIALISTAS`: correos institucionales, separados por coma, autorizados a usar la aplicación.
- `FIRMA_EDGAR`, `FIRMA_MARIA_JOSE`, `FIRMA_ABRIL`, `FIRMA_ELMY`, `FIRMA_MARILYN`, `FIRMA_DIEGO`: IDs de imagen de firma disponibles.

La hoja Registros conserva todas las versiones: al guardar una agenda nueva, agrega filas y marca las filas activas previas del mismo especialista/mes como SUSTITUIDO en una columna Estado; no borra filas ni PDFs anteriores. Los nombres de PDF incluyen fecha/hora para conservar versiones.

En la configuración de implementación, selecciona “Ejecutar como: usuario que accede” para que Google entregue el correo autenticado; configura `CORREOS_ESPECIALISTAS` y restringe también el acceso de la implementación. No uses “Cualquier persona” para datos internos. Si Apps Script no entrega el correo del usuario activo, la aplicación denegará el acceso hasta ajustar esa opción.

El código fuente no contiene identificadores privados ni claves API. La clave de Gemini que estaba en el código pegado se eliminó; revócala si aún sigue activa.

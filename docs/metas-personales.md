# Metas personales de la junta académica

El acceso Metas personales se encuentra en el Centro de Control, en Planeación y EPP, para las cuentas con acceso a planeación. Conserva las columnas Alumno, Metas y Recursos necesarios del formato de la sesión 2, con docente precargado y escuela limitada a su matrícula autorizada. La fecha inicial de esta sesión es 23 de octubre de 2026 y puede seleccionarse otra fecha para recuperar su captura.

La identidad del alumno se guarda por ID, no por coincidencia de nombres. La captura es personal por cuenta, escuela y fecha: no se muestran las metas de otras cuentas. No se envía su contenido a IA.

Las versiones se añaden a Metas_Personales_Versiones con texto RAW, huella de integridad y revisión anterior. Nunca se vacía una tabla. Antes de anunciar confirmación se lee la revisión añadida; una confirmación perdida se reconoce por contenido en el siguiente intento, sin duplicar versiones. Los cambios concurrentes incompatibles conservan la captura local y requieren conciliación. El candado es por proceso, como el resto de la aplicación; no representa un bloqueo distribuido.

El editor mantiene una base estable para no reaplicar renglones añadidos en cada rerun. La captura pendiente se conserva por cuenta/escuela/fecha en la sesión. El autoguardado agrupado usa un fragmento de estado cada 15 segundos, sin recargar la tabla; Guardar metas confirma de inmediato. Al cerrar sesión se ofrecen reintento y respaldo de metas pendientes, y el cierre confirmado limpia sus capturas del dispositivo.

La descarga PDF contiene la captura actual y no equivale a guardado central. No incorpora automáticamente la firma ni el sello de Dirección. Un cierre forzado del navegador antes de guardar no se considera protegido por la sesión; se ofrece respaldo JSON para conservar la captura cuando falla la conexión.

La hoja se crea con los permisos existentes del spreadsheet central cuando se guarda la primera captura. No se modifican permisos ni se publican respuestas personales en el repositorio.

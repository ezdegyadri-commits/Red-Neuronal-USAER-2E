# Edición directa del cronograma propio

Un mes con actividades guardadas inicializaba el editor como solo lectura y conservaba esa bandera en la sesión. Por eso los selectores de escuela y las actividades aparecían desactivados hasta pulsar Editar cronograma.

La vista del cronograma propio autorizado ahora permite editar directamente al abrir cualquier mes, incluido noviembre de 2026. Recupera también las sesiones con la bandera antigua en falso. Las modificaciones siguen publicándose únicamente con Guardar cambios y generar PDF. Conserva la agenda, recuperación de borradores, avisos y versiones. Las vistas de consulta ajena mantienen el parámetro lectura y no se modificaron.

Diego mantiene las ocho escuelas ya autorizadas por el directorio. María José conserva su conjunto asignado, sin ampliar permisos. No se modificaron cuentas, cronogramas reales ni datos de producción.

Validación: 38 pruebas aprobadas. Se verificó noviembre con cronograma existente y bandera antigua para Diego y María José: selección de escuela, cambio de actividad, guardado y continuidad de edición. También se probaron identidad no autorizada, ocho escuelas de Trabajo Social, opciones restringidas de Psicología, recuperación de meses anteriores, borradores, versiones y generación de PDF mediante simulación. No se hicieron escrituras reales en Sheets ni se generaron avisos reales durante las pruebas.

La entrega incluye activación puntual del módulo para sesiones abiertas, sin reinicio manual. La comprobación con usuarios reales en producción queda fuera de la prueba simulada.

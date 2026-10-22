# EPP: el informe compartido, no copias por especialista

La entrada EPP abre el Anexo XVII sobre la misma identidad alumno/ciclo que ya usa EPP_Versiones. El Anexo XVIII orienta los campos; no se trasladan formatos CAM al servicio USAER. Fuente contrastada: Manual USAER, páginas impresas 141–151 (PDF 152–162). Se conserva el generador PDF existente, el cuadro de programación, el calendario y el botón de expediente.

## Acceso y continuidad

Apoyo elige su escuela autorizada y un alumno de toda su matrícula, sin filtrar por modalidad ni exigir letras de grupo. Abrir reutiliza el documento existente; no duplica META por un segundo intento. Los especialistas ven solo informes iniciados de sus escuelas, consultan todo el documento y editan su función. Apoyo coordina la conclusión. Una EPP retirada requiere recuperar su identidad, no crear otra. Dirección consulta sin modificar hallazgos.

Las sesiones que ya tienen una edición guiada mantienen esa interfaz y sus campos. Actualizar aportaciones ya no borra su estado. Las nuevas aperturas utilizan el componente nativo de Planeación: texto literal, respaldo por pestaña, acuses por nonce, edición mientras se envía, DOM persistente y sincronización de aportes sin cambiar alumno/cursor. Los identificadores de celda son hashes seguros, independientes de nombres y acentos.

## Persistencia

Se conserva el diario aditivo de EPP_Versiones y sus encabezados. Las revisiones nuevas son deterministas por documento/área/revisión anterior/contenido. Un reintento consulta el diario antes de repetir el envío y confirma por lectura central; el caché de revisiones recientes se alimenta solo después de esa comprobación. No se migran ni borran filas previas.

Los cambios pendientes se mantienen por cuenta, alumno/ciclo y área. La fusión de tres vías aplica únicamente las diferencias respecto de su base: combina campos independientes incluso de una misma área y rechaza cambios incompatibles sobre el mismo dato. Las tablas se tratan como unidades: no se supone que dos filas con la misma posición sean equivalentes. La conclusión validada sigue ligada a las revisiones revisadas por el equipo y deja de estar vigente si cambian.

Los envíos automáticos se agrupan durante 30 segundos después de una confirmación; Guardar EPP confirma sin esperar ese intervalo. Se reutiliza el presupuesto compartido de Planeación y no se realizan esperas de reintento manteniendo el candado de escritura. El acuse conserva la huella original mientras el envío queda pendiente, para no confundir la captura local recibida con una edición remota incompatible.

Los fallos muestran causa y siguiente acción, permiten reintentar y descargar respaldo. Abrir otra EPP no descarta las pendientes. El cierre requiere confirmarlas o reconocer el respaldo descargado; el cierre confirmado elimina el estado EPP de ese dispositivo. Se pueden recuperar respaldos del mismo informe y área. El respaldo de celdas no reemplaza un dato remoto que ya cambió de manera incompatible.

## Antecedentes y análisis

Los datos generales disponibles se precargan sin inventar información. Antecedentes y evaluaciones reutiliza las conexiones previas del expediente y marca lecturas incompletas. La aplicación directa y la transcripción local incorporan resultados revisados al mismo informe. Los instrumentos y fechas se reutilizan en la tabla sin capturarlos por duplicado.

El análisis con IA mantiene la revisión del resumen anonimizado y el consentimiento explícito. Las referencias de instrumentos son obligatorias y se conserva el validador existente. La propuesta completa solo campos vacíos; no reemplaza redacción ni revisiones del equipo. Una solicitud idéntica reutiliza su propuesta en la sesión. La barra indica etapas reales, no una estimación del porcentaje interno del proveedor. Ninguna IA califica pruebas ni determina CI/diagnósticos. El equipo confirma sus áreas y apoyo valida la conclusión acordada.

## Verificación y límites

Pruebas con matrícula ficticia: acceso por área, documento único, readback, confirmación interrumpida, fusión independiente y conflicto, conservación de pendientes, recuperación acotada y matrícula con grupos/modalidades distintas. Navegador real local: escribir/guardar, conservar texto tras ticks, abrir/cerrar herramientas y especialista sin acceso de escritura a Aprendizaje. Se mantienen las regresiones de Planeación, sesiones, Metas personales y EPP guiada.

El candado de escritura es por proceso, no una transacción distribuida entre múltiples servidores. Sheets y una red pueden fallar: no se promete ausencia absoluta de errores. El respaldo por pestaña no sustituye el guardado central y puede ser eliminado por el navegador; se ofrece descarga explícita. La verificación con datos ficticios no equivale a una captura probada en una cuenta real. No se reinicia producción ni se alteran evaluaciones reales para probar.

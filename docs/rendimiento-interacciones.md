# Auditoría de interacciones y guardado

## Hallazgos

- Los callbacks del documento esperaban la escritura y confirmación de Google en el hilo que atiende la sesión. El navegador mantenía el campo, pero otras acciones esperaban el resultado.
- La consulta periódica de aportaciones podía esperar una petición remota antes de presentar el editor.
- Los widgets de módulos ordinarios volvían a ejecutar la cabecera y sus herramientas. El instalador se leía y verificaba repetidamente; el borrador de continuidad se cifraba incluso sin cambios.
- Cada celda editable y botón agregaba sus listeners. Cada pulsación solicitaba una medición síncrona de altura, además del respaldo local duplicado.

## Cambios y contratos

La ruta de cada módulo se ejecuta en un fragmento. Un cambio de módulo vuelve expresamente al script principal para actualizar navegación y permisos; una interacción local conserva la cabecera.

Los documentos de Planeación, sus aportaciones y EPP envían snapshots mediante un ejecutor limitado a cuatro workers y doce trabajos admitidos. La admisión no espera ni acumula una cola ilimitada. Se usa concurrencia de Python para los clientes síncronos de Google, sin un `async` superficial que siga bloqueando. El worker no recibe el objeto de sesión ni llama a widgets: su identidad y alcance son copias aisladas mediante ContextVar. La matrícula y las reglas se vuelven a comprobar en el servicio.

Solo el hilo de la sesión incorpora el resultado de un Future terminado. Hay un trabajo pendiente por documento y sesión, y los clics posteriores reutilizan ese trabajo. Un acuse anterior se fusiona con las modificaciones posteriores; no confirma ese texto nuevo ni reemplaza el borrador. La EPP conserva por separado las áreas guardadas y fallidas. Navegar traslada el Future junto con su borrador pendiente, sin copiarlo ni cambiar el documento. El presupuesto, las revisiones, los append idempotentes y la exclusión de conflictos siguen vigentes.

La UI optimista significa captura visible y editable con estado pendiente. No se presenta un éxito antes de la confirmación ni se revierte eliminando texto ante un fallo. Se retira el estado de envío activo, se conserva el borrador y se muestra diagnóstico/toast. El respaldo de navegador y la protección de salida continúan activos.

El editor delega input/change/paste y botones a sus contenedores. Mantiene el debounce de escritura y agrupa la lectura de altura mediante requestAnimationFrame, enviándola únicamente si cambió. Los botones propios se deshabilitan inmediatamente hasta su acuse. Los botones nativos tienen feedback local y rechazo de clics repetidos por delegación, sin alterar el disabled que decide React por permisos o validación. Hay limpieza de listeners, observers y timers.

Las herramientas de instalación se preparan al abrirlas. El APK público ya verificado se reutiliza por proceso. El respaldo cifrado de continuidad se reutiliza cuando no cambió la cuenta ni el contenido, con renovación cada treinta minutos; no cambia la duración, comprobación de permisos ni revocación de la sesión.

## Verificación y límites

`python -m tests.medir_respuesta_documento` compara el retorno del evento con la misma red ficticia de un segundo, sin servicios externos. Las pruebas cubren veinte clics durante un envío, captura posterior al envío, errores parciales, acceso por cuenta, navegación, un único append y reapertura desde el repositorio ficticio. El contrato Node cubre antirrebote, liberación, escritura durante envío, respaldo y cien entradas agrupadas sin mediciones repetidas.

Medición local del 27 de octubre de 2026: retorno síncrono 1003,64 ms; retorno del envío en segundo plano 5,42 ms. Veinte clics adicionales no crearon otra operación. Se confirmaron las dos operaciones previstas del comparativo. Es una simulación, no una medida de producción.

Regresión: 416 casos Python de los módulos afectados y 7 casos de Estadística en proceso separado; 4 contratos Node. La separación evita que fixtures de interfaz que sustituyen funciones globales contaminen la matrícula ficticia de otro módulo. Una verificación adicional de 130 casos cubre la liberación del botón al fallar y el reintento del mismo nonce, conservando el respaldo.

La prueba visual local simula tres segundos de red. Permite escribir después de pulsar Guardar y confirma posteriormente ambos avances. Las pruebas no miden la latencia real de Cloud con toda la plantilla conectada. Google Sheets e IA mantienen sus tiempos y cuotas; los controles de espera y confirmación no se sustituyen por un éxito aparente. Las operaciones excepcionales, acceso, exportaciones y pantallas antiguas conservan sus contratos síncronos; esta entrega no afirma convertir todas las APIs de la plataforma en asíncronas ni eliminar cualquier espera externa.

Se publican exclusivamente código y datos ficticios. Sin cambios de matrícula, permisos, historial ni planeaciones reales. Sin reinicio manual.

# Planeación: navegación con envíos pendientes

Una demora de un documento no bloquea crear o continuar otro. No se modifica
la persistencia central, la identidad del Anexo XIX, los permisos ni el historial.

Antes de reutilizar el espacio de edición de otra planeación, se conserva una
copia profunda en una clave independiente de la misma sesión y cuenta. Incluye
documento, aportación acotada si corresponde, estado solicitado, acuse y espera
de reintento. No se marca como guardado: queda en la cola pendiente.

Volver al mismo ID recupera primero el texto pendiente de esta sesión y no una
versión anterior del catálogo. El retorno al inicio conoce la raíz de la sesión,
también cuando se edita una copia conservada en la cola.

Un fragmento cada 15 segundos reintenta como máximo dos documentos inactivos
por pasada, respetando sus esperas y presupuesto existente. La edición activa
conserva su propio autoguardado. No se recarga toda la página tras un reintento.
El fallo del primer envío no evita intentar el siguiente. Los acuses solo se
emiten tras respuesta confirmada del servicio versionado existente.

La cola es de sesión, no es una segunda base durable ni una confirmación de
Google Sheets. Ante un fallo permanente o pérdida de conexión se permite
continuar trabajando, pero se advierte no cerrar la pestaña sin confirmar los
envíos o descargar los respaldos. No garantiza sobrevivir a un reinicio del
servidor. Por eso este ajuste no requiere ni autoriza reiniciar producción.

Pruebas: `tests.test_planeacion_cola_pendientes` reproduce fallo de envío del
grupo A, apertura del grupo B, conservación y posterior envío de A; aislamiento
entre cuentas, aportaciones, estados de envío y cierre sin confirmaciones falsas.

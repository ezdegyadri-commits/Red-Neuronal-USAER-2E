# Recuperación separada y generación verificable

- Individuales y Grupales son repositorios visuales del mismo historial autorizado; no son tablas nuevas ni copias. Se mantienen visibles Mi intervención y Otros formatos cuando existen documentos de esos tipos.
- Las tarjetas muestran destinatario o grado, escuela, ciclo, trimestre, fecha, estado y trabajo redactado. Se filtran por grado y búsqueda, con seis tarjetas por página. Los respaldos se preparan bajo demanda, no para todos los documentos al cargar la pantalla.
- El editor conserva sus permisos, cola de pendientes y guardado. Continuar usa el mismo ID y mecanismo de apertura previo.
- La barra de IA representa hitos reales, no tiempo transcurrido ni progreso interno de Gemini. Mientras espera al servicio no inventa porcentajes. Sólo alcanza 100 al recibir una respuesta que superó el validador; si falla, se retira sin anunciar éxito.
- Para respuestas estructuradas incompletas o no verificables de causas explícitamente enumeradas se permite una corrección adicional, como máximo tres unidades concisas. Se envía exactamente el mismo conjunto de datos consentidos más una indicación de formato y el código de causa permitido. No se reenvía el mensaje del proveedor ni una respuesta fallida.
- La corrección mantiene el mismo validador de evidencias, destinatarios, fuentes, PDA, contexto y variedad. No integra parcialmente respuestas sin validar. Los fallos de autenticación, cuotas, saldo o configuración no activan esa corrección de formato. El transporte conserva su reintento acotado existente.
- No se cambia modelo, clave, proveedor, permisos ni fuentes autorizadas. Las pruebas no solicitan IA con datos reales ni modifican registros centrales. Se conserva la huella de las generaciones guardadas porque la solicitud inicial no cambió.

Esto no garantiza disponibilidad ni una tasa de éxito determinada del proveedor. Los avisos ahora distinguen la causa segura devuelta por el servicio y permiten continuar en la misma hoja sin crear un borrador nuevo.

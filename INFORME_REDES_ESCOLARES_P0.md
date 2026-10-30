# Primera entrega para redes escolares lentas

30 de octubre de 2026. Rama aislada: fix/redes-escolares-p0.
Base: 9cf45b1. Esta entrega no está publicada.

## Cambios preparados

1. Planeación y EPP distinguen texto recibido por el servidor y guardado central.
   El recibo libera el intercambio del editor sin declarar que Sheets persistió.
2. Al volver al listado con escritura pendiente, el cliente entrega primero el texto.
   Mientras espera ese recibo permite seguir escribiendo. Si apareció escritura
   posterior al envío, la entrega antes de solicitar la salida.
3. El respaldo por pestaña conserva también los cambios recibidos que todavía no
   tienen confirmación central. No se borra por un simple recibo.
4. Expedientes genera sus PDF y HTML imprimibles únicamente al descargarlos;
   las vistas previas requieren activación explícita. No se eliminan capacidades.

Los permisos, los registros de datos, los límites de concurrencia, los nonces de
reintento y la reconciliación de persistencia no se sustituyen.
No se contrataron servicios ni se modificó la beta FastAPI.

## Comparación comprobada

Mismo expediente ficticio y generadores instrumentados con contadores:

| Operación inicial | Base | Cambio |
|---|---:|---:|
| Anexo III PDF | 1 | 0 |
| Anexo IV PDF | 1 | 0 |
| Anexo V PDF | 0 | 0 |
| Anexo III HTML | 1 | 0 |
| Anexo IV HTML | 1 | 0 |
| Anexo V HTML | 2 | 0 |

No son solicitudes HTTP ni tiempos de una escuela. Los documentos completos ya
no se preparan para pestañas que la persona no abrió.

El contrato JavaScript comprueba que una herramienta en cola puede abrirse con
recibo local aunque el guardado central siga pendiente. El respaldo continúa
presente y el estado no dice Guardado confirmado.

## Pruebas

- Contrato JavaScript existente ampliado: pasa en transporte integrado y marco
  ficticio; rechazo, nonces, cortes, escritura posterior y recuperación.
- 19 pruebas Python focalizadas: pasan, incluidas persistencia asíncrona, EPP,
  respaldo de cierre, cargas diferidas y recibo sin confirmación.
- Siete perfiles de latencia/velocidad modelados como prueba determinista del
  protocolo. Incluyen 150/300/500 ms y límites de transmisión calculados.
  NO son throttling real de red, mediciones de WebSocket ni p95 de producción.
- La batería amplia antigua ejecuta 60 tests y presenta 23 fallos y 13 errores.
  La base sin cambios presenta los mismos 36 casos fallidos por nombre.
  No se presenta esa batería como aprobada. Los cambios no corrigen sus
  problemas de fixtures y compatibilidad ajenos a esta entrega.
- La comprobación visual en navegador no pudo completarse: la herramienta
  de control no pudo iniciar su entorno, incluso después de restablecerlo.
  El servidor local de prueba solo contiene datos ficticios.

Evidencias técnicas fuera del repositorio: p0-redes-generacion.json,
p0-redes-protocolo.json, p0-redes-regresiones.log y comparaciones de la base.
No contienen datos reales de alumnos ni credenciales.

## Límites y publicación

Una caída total de internet todavía impide que el servidor reciba acciones.
Mientras tanto se conserva la escritura en la pestaña y no se afirma que esté
guardada en la base. Esto no es una solución offline completa.

El respaldo existente es sessionStorage, no un almacén cifrado de expedientes;
no se amplía a una copia completa del padrón. Una revisión distinta se trata
como respaldo para revisar, sin sobrescribir automáticamente la versión central.

Antes de publicar: completar prueba visual del editor, probar el cambio con un
documento ficticio bajo red realmente limitada, y coordinar una ventana en la
que no haya texto aún sin transmitir en las sesiones activas. La nueva versión
del componente debe activarse correctamente en el runtime; no se debe forzar
un reemplazo del editor en medio de una captura sin respaldo.

La primera publicación requiere autorización explícita. No se ha hecho push,
merge, despliegue ni reinicio de producción.

## Siguiente etapa

Medir y después reducir consultas frías, tamaño de los índices y sincronización
periódica. Esta entrega no cambia sus intervalos a ciegas ni promete que todos
los módulos queden por debajo de dos segundos.

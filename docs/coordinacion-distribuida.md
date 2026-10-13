# Coordinación transaccional de Planeación · preparación

Estado: preparada en desarrollo, DESACTIVADA, pendiente de proyecto y credenciales seguros. No hay escrituras reales en Sheets, Supabase ni Drive. La interfaz publicada en PR #54 no se modifica como parte de esta preparación.

## Arquitectura y alcance

- `data/coordinacion.py`: adaptador REST y configuración segura. SQL RPC de PostgreSQL, sin copiar contenido educativo. Ninguna dependencia nueva en producción.
- `deployment/coordinacion_postgres.sql`: instalación idempotente en un proyecto dedicado. Tablas privadas con RLS; función con search_path fijo y permiso de ejecución solo para service_role. Sin acceso público o de docentes al servicio de control.
- `services/planeacion_distribuida.py`: puente hacia el mismo ledger de versiones en Google Sheets. Autorización y validación se realizan antes de adquirir el control; no altera firmas, formatos, alumnado ni estados normativos.
- `data/google.py`: el cliente gspread de cuenta de servicio reserva cupo compartido antes de las solicitudes. Máximo 45 lecturas y 45 escrituras por minuto para estos clientes, no 45 por cada proceso. El margen no cubre escritores ajenos a esta aplicación.
- `services/planeacion.py`: revisión fresca del ledger dentro de la sección coordinada, conflicto optimista conservado, orden canónico por posición física cuando hay varios hosts. El presupuesto local permanece como protección adicional.
- `utils/guardado.py`: estado transitorio común, reexportado desde planeacion_estabilidad para preservar los consumidores existentes.

La exclusión de edición se aplica a Planeación y sus aportaciones colaborativas. El presupuesto HTTP se comparte entre los clientes de cuenta de servicio de los módulos existentes. Esto NO transforma en transaccionales todos los procesos de otros módulos: antes de escalarlos a varios escritores hay que revisar sus contratos. Drive/OAuth u otros clientes independientes no quedan limitados por este adaptador.

La opción Redis se descartó para esta entrega: la documentación del proveedor examinado describe consistencia eventual y retirada del modo fuerte. Se optó por las transacciones y conflictos de fila de PostgreSQL. No se creó ninguna cuenta o proyecto en ninguno de los proveedores.

## Invariantes de seguridad

ADQUIRIR usa INSERT/ON CONFLICT sobre una clave única namespace/documento. Un permiso RESERVADO antiguo puede reemplazarse tras 120 segundos; el propietario anterior no puede iniciar ni liberar la operación nueva porque todas las transiciones comprueban token.

Antes de enviar el append, INICIAR marca la operación INCIERTO y conserva únicamente revisión, digest y huella. Ese estado NO expira por reloj: Google Sheets no valida fencing tokens y una solicitud puede terminar después del timeout del cliente. Una confirmación ambigua jamás permite otro append sin reconciliar.

RECUPERAR libera únicamente el token/revisión/digest comprobados frente a una versión completa de Sheets, con todos sus fragmentos y SHA válido. Si no hay prueba de confirmación, difiere la operación y preserva la edición. Un rechazo explícito antes de transmitir o del servidor 4xx puede volver a intentarse; un timeout o 5xx no se considera ausencia de escritura.

Los cachés no autorizan cambios obsoletos. La lectura canónica se realiza dentro del permiso; las versiones nuevas sin índice físico invalidan únicamente la caché del ledger para recuperar su orden real. No se escoge una versión anterior por diferencias entre relojes de hosts.

Una configuración incompleta activa o un coordinador caído no cae silenciosamente a bloqueos locales. El modo sin configurar/desactivado mantiene el comportamiento publicado de una instancia; no se lo presenta como distribuido.

## Verificación

Corredor offline: 345 pruebas correctas en 80.700 segundos, incluidos los 18 casos nuevos del adaptador, permisos, formatos XXI/XXIII/XXV, respuestas perdidas, memoria local vacía, fragmentos incompletos, caché obsoleto, relojes distintos y 20 guardados simulados. HTTP y sockets externos permanecen bloqueados; los repositorios y respuestas son ficticios.

Pruebas SQL: ejecución íntegra e idempotente en PostgreSQL embebido PGlite 0.3.14. Se verificaron 20 solicitudes competidoras con un solo propietario, 20 documentos independientes, 80 reservas con 45 aceptadas, recuperación por digest, dueño antiguo rechazado y permisos anon/authenticated sin ejecución. Son pruebas del motor y operaciones, no 20 navegadores reales ni una medición de Supabase.

Para repetir el SQL: instala `@electric-sql/pglite@0.3.14` en un directorio de pruebas, define `PGLITE_TEST_MODULE` con la ruta absoluta a su `dist/index.js` y ejecuta `node tests/coordinacion_postgres_sql.mjs`. No se incluye ese paquete en la aplicación ni se necesitan credenciales para estas pruebas.

Pendiente: prueba remota con proyecto gratuito dedicado, namespace de pruebas, documentos ficticios, 15–20 sesiones y mediciones p95/cupos/recuperación. No se certifica capacidad real ni disponibilidad absoluta a partir de simulaciones. Se conserva la incidencia heredada de test_student_school_scope.py ya documentada en la batería de estabilización.

## Activación y reversión

Seguir `docs/activar_coordinacion_gratuita.md`. No habilitar replicas sin que todos los escritores usen el mismo coordinador. Activar en una ventana tranquila después de confirmar/respaldar los borradores pendientes; no introducir el cambio durante la junta.

No hay migración, eliminación ni cambio de esquema del ledger. Para revertir coordinación activa, detener guardados, verificar las operaciones inciertas y asegurar un único escritor antes de desactivar. No resetear controles operativos ni borrar versiones como atajo.

Referencias: [Supabase Functions](https://supabase.com/docs/guides/database/functions), [Supabase API keys](https://supabase.com/docs/guides/getting-started/api-keys), [plan gratuito](https://supabase.com/pricing), [limitación de consistencia Redis examinada](https://upstash.com/docs/redis/features/consistency).

# Estabilización de Planeación para la sesión del 14 de octubre de 2026

## Contratos conservados

Se conservan formatos XXI, XXIII, XXV y guías grupales, generación educativa con
IA, referentes oficiales, documentos aportados, autollenado, edición, revisión
directiva, colaboración, EPP, permisos y exportación PDF. No hay migraciones,
eliminaciones de registros ni cambios de credenciales o permisos.

La persistencia sigue siendo aditiva en Planeaciones_Versiones con los mismos
encabezados, fragmentos y SHA-256. Las versiones históricas siguen disponibles.

## Guardado

Los cambios confirmados en campos se agrupan aproximadamente cada 60–75 segundos.
El botón Guardar borrador sigue disponible. Debe confirmarse el guardado antes de
cerrar o recargar: el texto no confirmado y los cambios pendientes de sesión no
constituyen persistencia durable. Los fragmentos revisan pendientes cada 15 segundos,
pero no escriben cada 15 segundos.

El presupuesto de Planeación admite 45 intentos de escritura por ventana móvil
de 60 segundos por proceso. El margen no garantiza la cuota total: otros módulos
comparten la cuenta de servicio y requieren observación en la sesión. Un intento
aplazado no se considera guardado; permanece pendiente con reintento automático.

Un candado por documento evita que la latencia de una planeación inmovilice todas
las demás. La coordinación de cachés usa un candado breve, sin red bajo ese candado.
Un guardado sin cambios no añade otra versión.

Si se pierde la confirmación de un append, se conserva el mismo UUID, contenido y
huella del intento en memoria del proceso. Antes de reintentar se consulta servidor.
Si la revisión ya existe, se confirma sin repetir append. Si no existe y no hay otro
avance, se reusa la revisión. Si el usuario cambió el contenido, se conserva su
edición y se pide conciliación, sin reemplazarla con el intento anterior.

Esta coordinación no es distribuida. Antes de producción se debe confirmar una
única instancia escritora. Varios procesos o reiniciar un proceso con intentos
ambiguos requieren revisión adicional; no se declara garantizada la capacidad
de 25 navegadores por haber aprobado simulaciones de hilos.

## Recuperación y errores

Abrir otro documento no reemplaza una edición pendiente silenciosamente. La
recuperación permite conservar una copia adicional para conciliar en la sesión,
con descarga JSON. Esa copia no sustituye el archivo descargado ni sobrevive
necesariamente a una recarga. Salir con cambios pendientes requiere confirmación.

La interfaz conserva acceso a respaldos de sesión ante fallos de consulta y PDF.
Los logs indican operación/tipo, sin resumen del alumno ni mensajes del proveedor.
La revisión IA de Dirección recibe una lista estructurada de evidencias para
minimizar la contextualización, igual que las rutas de docentes.

## Rendimiento

El PDF se reutiliza por huella y sesión. No se envía a IA ni consulta Sheets.
Dos transcripciones pesadas como máximo se procesan a la vez por proceso; si no
hay cupo, el archivo sigue cargado y se indica reintentar. Se conservan tipos de
archivo, 32 MB, intervalos de páginas y límites de OCR/texto.

La invalidación de caché es por hoja. Actualizar evidencias invalida solo sus
fuentes; no vacía tablas ni borra expedientes. Las seis dependencias principales
de Planeación quedan fijadas a las versiones del entorno usado para regresión.

## Verificación sin producción

Ejecutar desde la raíz:

    python tools/probar_estabilizacion_sin_red.py

El corredor bloquea clientes HTTP y sockets externos antes de importar pruebas.
Solo permite el loopback que Windows requiere para asyncio/AppTest. Usa repositorios
ficticios, Google simulado y Gemini simulado. No necesita credenciales.

Incluye regresión del módulo y procesos vecinos, pérdida de confirmación, conflicto
de dos editores, aislamiento de un documento lento, cuotas y persistencia sintética
con 15/20/25/30 documentos, conservación de edición y reutilización del PDF.

Prueba pendiente antes de afirmar capacidad real: 15/20/25/30 navegadores en un
despliegue aislado, spreadsheet ficticio y cuenta de prueba. Medir latencias p95,
solicitudes/min, memoria, cola, PDF, OCR, reconexión y recuperación tras reinicio.
No hacer esa prueba en producción ni usar expedientes reales.

## Resultado de la regresión local

El 9 de octubre de 2026, el corredor aprobó 312 pruebas en 65.753 segundos.
Los escenarios de persistencia sintética conservaron 30, 40, 50 y 60 versiones
para 15, 20, 25 y 30 documentos respectivamente. En los escenarios de 25 y 30,
cinco y quince guardados se aplazaron y luego se recuperaron sin perder contenido.
La simulación del presupuesto anterior de cuatro solicitudes/persona/minuto
aceptó como máximo 45 reservas por ventana y difirió el exceso. Estas cifras
son de repositorios ficticios y no son mediciones del servidor ni de Google.

Se detectó también una prueba preexistente que no puede importarse:
tests/test_student_school_scope.py importa validar_identidad_padron, ausente
en services/padron_oficial.py en el commit base. No se modificó ese servicio
ni se eliminó la prueba; no forma parte de las 312 pruebas aprobadas. El resto
de las pruebas de ámbito compartido y permisos incluidas sí se ejecutó.

## Operación y reversión

Evitar despliegues durante la reunión. Preparar documentos grandes antes, verificar
guardados y descargar respaldos. IA puede faltar sin impedir edición manual.

Revertir solo el commit de código si aparece una regresión; no revertir ni limpiar
la hoja de versiones. Este cambio no requiere transformaciones de datos.

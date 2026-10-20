# Un único Anexo XIX y edición sin recarga completa

## Identidad

Una guía compartida se identifica por escuela canónica, ciclo, trimestre,
grado y grupo. Grados equivalentes se normalizan para comparar, sin reescribir
las capturas históricas. Una letra vacía identifica el grado sin letra: no se
equipara a A, B u otro grupo. Un nuevo XIX obtiene un ID determinista; volver
a abrirlo reutiliza el documento existente. Solo apoyo inicia esta guía.
Las intervenciones propias de especialistas, los PI individuales y los formatos
trimestrales de subgrupos mantienen su propósito y sus formatos.

## Documentos anteriores repetidos

Se proyectan sobre el documento con la primera versión más antigua, no el
último guardado (que cambiaría el ID durante la colaboración). Se reúnen alumnos
por ID y textos distintos sin borrar las fuentes. Sus IDs/revisiones quedan
registrados en `metadatos.unificacion_grupal.fuentes`. El primer guardado crea
una versión aditiva del documento canónico: no migra ni vacía las hojas.

La misma revisión de origen no vuelve a incorporarse: una edición o eliminación
posterior de texto en la hoja unificada se respeta. Una copia antigua abierta
no puede volver a escribir como otro documento activo; conserva el respaldo y
pide abrir la hoja del equipo. Los originales permanecen en el historial.

Si se detectan dos cuentas propietarias de una misma área, se conservan ambos
textos, se señala el conflicto y esa columna queda en lectura hasta conciliar
su autoría. No se asigna silenciosamente el trabajo de otra persona. Todos los
alumnos de la proyección deben superar la autorización del servidor antes de
mostrarse. La deduplicación no amplía asignaciones ni permisos.

## Edición y guardado

El editor se registra una vez por proceso. La hoja de apoyo y la hoja de
especialistas se ejecutan en fragmentos: lectura del equipo, eventos de celda,
confirmación y reintento no provocan una recarga completa de la aplicación.
El cambio de módulo o regresar al inicio sigue siendo explícito y protegido.
La recepción y la confirmación durable continúan siendo eventos distintos.

El transporte nativo conserva nodos, cursor y texto pendiente al recibir otras
áreas. Se mantienen el respaldo de pestaña, nonce, control de revisión y
guardado acotado por área. La consulta del equipo es periódica (10 segundos)
y las escrituras se agrupan para respetar las cuotas de Sheets. No se afirma
edición carácter a carácter, cursores compartidos ni CRDT como Google Docs.

La coordinación actual requiere una única instancia escritora. El candado por
grupo evita creaciones simultáneas dentro de ese proceso; el ID determinista
evita identidades nuevas para el mismo grupo. Esto no convierte Google Sheets
en una base con CAS distribuido. No se cambian Gemini, permisos ni registros
anteriores durante las pruebas.

## Verificación

Datos sintéticos: dos documentos equivalentes, letra vacía, separación de
escuelas/grados/grupos/trimestres, identidad estable al reordenar o guardar,
conciliación idempotente, originales inmutables, bloqueo de copias antiguas,
propiedad de áreas, tres especialistas concurrentes y conciliación de apoyo.
Se conservan los contratos Node del editor y las regresiones de interfaz.

Cierre del 19/10/2026: 209 pruebas Python aprobadas (incluye regresiones de
interfaz y persistencia sintética), contrato Node del editor aprobado y revisión
de espacios del diff aprobada. La prueba de carga es sintética: no se presenta
como una medición de latencia o carga de usuarios reales contra Google Sheets.
La publicación fue autorizada por Dirección después de verificar.

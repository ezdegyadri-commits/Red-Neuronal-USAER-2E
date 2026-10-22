# Preparación de planeación, docentes regulares y protección del texto

Estado: publicación autorizada por Dirección, sujeta a las pruebas finales. No se escribieron registros de producción ni se reinició manualmente la plataforma.

## Alcance del Anexo XIX

- «Todos» se registra explícitamente como alcance de todo un grado. Incluye sus secciones A/B y los registros sin letra, sin cambiar la ubicación de los alumnos en el padrón.
- Un grupo sin letra no se interpreta como comodín. Las selecciones concretas A/B conservan la comparación exacta.
- Si se solicita todo el grado y existen hojas por sección, se reutiliza una raíz y se concilian los textos por ID, conservando las versiones originales. Los conflictos de autoría no se sobrescriben.
- Se limita a un grado, escuela, ciclo y trimestre. No se redistribuyen automáticamente borradores históricos que mezclan varios grados: requieren revisión para no atribuir actividades incorrectamente.
- Regla más reciente de Dirección: se excluye atención individual del Anexo XIX, incluso si una versión histórica habilitaba su inclusión. La planeación individual no se modifica. Se preservan filas y aportaciones anteriores en metadatos históricos y en las versiones previas.
- La lectura autorizada de matrícula deja de permanecer congelada toda la sesión. Se conserva el caché compartido de acceso a Sheets para no aumentar innecesariamente las consultas.

## Docentes regulares

- Precarga por ID de escuela, ciclo, grado, grupo y turno, sin copiar contactos al documento.
- Para un grado completo se muestran los docentes de las secciones correspondientes. Sin letra, sólo se infiere docente cuando existe una única sección posible.
- Se respeta el texto editado manualmente en la planeación; una corrección del catálogo actualiza la precarga automática, no una edición manual.
- El formulario requiere cuenta identificada y restringe escuelas tanto en pantalla como en la operación de escritura. Las asignaciones oficiales prevalecen; Dirección conserva las siete primarias.
- Correcciones mediante append de otra versión con el mismo ID y cuenta responsable. No se borran filas anteriores. Ciclo, escuela e identidad no se modifican desde la edición.
- Se distingue confirmación central de contingencia local. Un fallo no vacía el formulario ni se anuncia como guardado confirmado.

## Guardado y recuperación

- Se muestra la causa y una acción concreta para límite temporal, conexión, acceso, validación o conflicto de revisión.
- Se ofrecen reintento y descarga de cada edición pendiente, también desde el cierre de sesión.
- El editor integrado intercepta el cierre cuando todavía tiene texto no enviado o sin acuse. Solicita guardarlo antes de permitir el cierre.
- El respaldo de texto incorpora el ID del destinatario y el valor base de cada celda. La recuperación no aplica texto por posición de fila ni sobre una edición remota diferente.
- La recuperación de un documento completo conserva su revisión original: no se le asigna artificialmente la revisión reciente para eludir conflictos.
- Las aportaciones se recuperan con la misma cuenta y área y conservan su validación de cambios concurrentes.
- Navegar entre planeaciones mantiene la cola de pendientes. No se fuerza el descarte ni se exige borrar otra edición para avanzar.
- Se comparan base, edición local y versión reciente por campo e ID de alumno. Cambios independientes se reúnen; dos valores distintos para la misma celda se detienen sin elegir un ganador silenciosamente. Las aportaciones ajenas siguen procediendo de su área autorizada.
- Las tres versiones se proyectan con la misma matrícula autorizada antes de comparar, para no confundir altas/exclusiones automáticas con edición concurrente del autor.
- Un borrador eliminado desde otra sesión se identifica como tal y ofrece «Restaurar este borrador y reintentar». La restauración usa la autorización del autor y conserva la revisión base del texto pendiente para conciliarla, sin saltarse los controles de concurrencia.

## Límites y comprobación

Pruebas con matrícula, documentos, DOM y repositorios ficticios; no usan alumnos reales ni motores de IA. Se ejecutan módulos en procesos separados porque los fixtures de interfaz sustituyen servicios globales y pueden interferir si se agrupan en una sola ejecución.

Resultado final: 43 módulos, 508 verificaciones ejecutadas sin fallos; pruebas de cliente JavaScript aprobadas. La prueba de conciliación se volvió a ejecutar después de añadir la protección frente a cambios de estado de revisión. `git diff --check` sin errores de contenido.

El respaldo en la pestaña no equivale a persistencia central. El usuario debe ver «Guardado confirmado» o descargar su respaldo antes de cerrar. No se promete conservación absoluta ante pérdida del dispositivo, almacenamiento bloqueado o cierre forzado sin respaldo.

La publicación en la rama de producción y su comprobación visual se informan por separado: una respuesta de salud HTTP 200 no demuestra por sí sola qué revisión está ejecutándose ni un guardado autenticado correcto.

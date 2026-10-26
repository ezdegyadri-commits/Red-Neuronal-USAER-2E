# EPP compartida y recuperación de planeación

## Comportamiento

- Cada apartado narrativo editable ofrece opciones para proponer redacción y marcar «No se requiere».
- La exclusión es reversible: el texto anterior permanece en el contenido versionado. El PDF omite el apartado marcado y su encabezado; omite una sección completa cuando todos sus apartados están marcados.
- El asistente usa ideas, resultados y hallazgos registrados. Primero prepara un resumen minimizado para revisión; solo consulta IA tras consentimiento explícito. La propuesta es editable y requiere incorporarla. No valida un área ni inventa puntuaciones o diagnósticos.
- Comunicación comparte únicamente orientación temporal y coordinación motriz fina/gruesa. Trabajo Social comparte los datos generales de Aprendizaje. Las tablas, instrumentos y demás campos conservan sus permisos originales. Una edición compartida no puede validar el área ajena.
- La fusión de tres vías conserva aportes independientes. Si dos personas cambian el mismo dato, se mantiene la captura pendiente y se comunica el conflicto; no se sobrescribe silenciosamente.
- Datos generales reutiliza etiquetas explícitas de evaluaciones de Trabajo Social cuyo nombre identifica una entrevista, y parentescos explícitos madre/padre de la tabla familiar. El origen queda identificado. Las correcciones manuales prevalecen. No se infieren datos desde prosa libre o CURP.
- La hoja completa sigue disponible en las vistas guiada y nativa, respetando permisos por campo.
- Planeación permite insertar filas antes/después de una fila existente. Las filas anteriores y sus versiones se conservan.
- «Continuar planeación» se presenta primero y se dibuja antes de consultar la matrícula para crear documentos. La búsqueda global por alumno ignora filtros locales de grado y búsqueda; los documentos antiguos sin modalidad permanecen en «Otros formatos guardados» y muestran el nombre cuando tienen un solo alumno. Buscar no modifica el documento ni la asignación del alumno.

## Verificación

Datos ficticios y repositorios simulados: permisos exactos, combinación concurrente y conflicto, exclusión/restauración, extracción de texto del PDF, precarga y corrección manual, pantallas de Comunicación/Trabajo Social, preparación del asistente sin IA, búsqueda histórica e inserción de filas. El contrato del cliente se verifica con DOM y reloj ficticios, incluyendo escritura durante guardado y conservación del respaldo.

No se usaron alumnos reales en las pruebas ni se hicieron llamadas reales a IA. La recuperación de una planeación localizada en producción se realiza mostrando su identidad original; no requiere duplicarla, cambiar grado ni reasignar alumnado. La verificación en la aplicación publicada debe hacerse después del despliegue autorizado.

## Compatibilidad de despliegue en Cloud

La comprobación posterior al despliegue mostró la búsqueda nueva en Planeación, pero EPP seguía renderizando controles anteriores pese al registro «Updated app». La entrada versionada `ui.epp_acceso` comprueba el marcador de la interfaz. Si encuentra la versión anterior en memoria, recarga una sola vez y en orden el conjunto acotado de módulos EPP. No modifica `session_state`, no vacía cachés y no reinicia el proceso. En un arranque con el marcador actual no recarga módulos. Se prueba la ruta actual, la actualización única y el fallo explícito si el código esperado aún no está disponible. Esta compatibilidad no sustituye la verificación visual posterior a publicar.

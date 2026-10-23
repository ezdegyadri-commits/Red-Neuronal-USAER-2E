# Juntas académicas y metas por alumno

La primera sesión disponible es el 23 de octubre de 2026. El módulo reúne el
instrumento de metas/valoración y el cuadro de metodologías; el acceso previo
«Metas personales» continúa abriendo la misma captura, no una base duplicada.

## Instrumento de planeación

Referencia: Instrumento planeacion USAER.docx aportado por Dirección. Se
conservan catorce indicadores, escala 0–3, observaciones y análisis de coherencia.
La adaptación agrega metas y recursos por alumno. Es autoevaluación docente,
no una calificación del alumno ni una validación automática de Dirección.
Las respuestas pendientes no equivalen a cero. Solo se muestra total /42 al
responder los catorce indicadores; coherencia /3 siempre se informa aparte.
No se inventan rangos de desempeño a partir de ese total.

Apoyo elige entre todos sus alumnos autorizados, sin excluir modalidades de
atención ni grados. Psicología, Comunicación y Trabajo Social eligen escuela
entre las asignadas y después un alumno de esa escuela. La autorización se
revalida en el servicio al guardar usando ID de alumno y escuela canónica,
nunca coincidencias de nombre. Los homónimos se desambiguan visualmente.

Se reutiliza Metas_Personales_Versiones y su identidad cuenta/escuela/sesión.
Las versiones anteriores no se reescriben. Las filas antiguas sin rúbrica
siguen siendo válidas y se incluyen en consulta y exportación. Incluso al
guardar mediante el contrato anterior se conserva la rúbrica ya existente.
Dirección proyecta la última versión íntegra por documento, con procedencia;
no mezcla ni suma puntajes de docentes distintos. Puede exportar todas las
respuestas de una sesión a un solo PDF. Consultar/integrar no escribe datos.

## Cuadro de metodologías

Referencia: Sesión 2- Cuadro de metodologías.docx, aportado por Dirección.
Los 25 registros conservan sus seis áreas y sus referencias; los saltos de línea
y la puntuación se normalizaron para lectura en pantalla. A, C y P se conservan
literalmente como marcas sin significado atribuido, por indicación expresa
de Dirección. Se agregan aplicación prevista y evidencia/seguimiento.
El catálogo es consulta institucional, no recomendación generada por IA ni
prescripción automática por diagnóstico. No se consultan enlaces externos
ni se envían capturas a motores de IA como parte de esta funcionalidad.

Cada docente conserva una aportación por sesión en Juntas_Academicas_Versiones.
La hoja se crea solamente al guardar por primera vez. Contenido JSON literal
(RAW), huella SHA256, versión anterior, bloqueo por documento, comprobación de
revisión, reintentos idempotentes y confirmación por lectura. Un conflicto
de la misma cuenta en dos pestañas se comunica sin sobrescribir la otra versión.
Solo Dirección consulta las aportaciones de todo el equipo y las exporta juntas.

## Continuidad y verificación

Los controles capturan al abandonar el campo y el envío se agrupa cada 15 s.
Cambiar alumno, escuela, fecha o material no elimina los borradores en sesión.
Un guardado fallido no bloquea abrir otros instrumentos. Se ofrecen guardado
explícito, respaldo JSON y protección de cierre; cerrar sesión limpia también
los estados de juntas del dispositivo compartido. No se promete persistencia
de texto aún no transmitido ante cierre forzado del navegador/dispositivo.

Pruebas con datos exclusivamente ficticios: escala, pendientes, totales,
conservación de antecedentes, aislamiento por cuenta y escuela, consolidado
directivo, integridad, RAW, reintentos, conflicto, selección por roles, cambio
de alumno, navegación por fecha y marcas A/C/P. Regresiones de EPP y planeación
se ejecutan en procesos separados para aislar los dobles de prueba.

Estos cambios se preparan localmente. La preparación no cambia permisos,
registros reales, calendario compartido ni datos de alumnos; tampoco publica
ni reinicia la aplicación sin autorización para este alcance.

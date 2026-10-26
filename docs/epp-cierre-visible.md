# Cierre interdisciplinario visible en la EPP

El botón de preparación de resumen compartía su clave de Streamlit con el
contenido generado. La asignación al estado del widget fallaba y dejaba la
generación deshabilitada. Ahora cada estado tiene una clave distinta.

La coordinadora encuentra «Generar conclusión y NEE del equipo» junto a la hoja.
El resumen recupera los aportes actuales de las cuatro áreas, incluyendo
síntesis y evaluaciones, con presupuesto por área para evitar truncar las últimas.
Mantiene la revisión del resumen anonimizado y su autorización antes de IA.

«Generar y llenar conclusión y NEE» incorpora la propuesta al mismo informe y
actualiza inmediatamente la hoja. Actualiza los campos de cierre propuestos,
conservando las versiones anteriores en el diario. Las filas de NEE/BAP editadas
por docentes se conservan; las propuestas anteriores sin editar pueden
actualizarse sin duplicación. La conclusión sigue sin validar.

Antes de incorporar se comprueban de nuevo las revisiones de las cuatro áreas.
Si cambiaron durante la generación, no se guarda un cierre obsoleto. Si el
guardado falla, la propuesta permanece visible y pendiente de confirmación.
No se modifican las aportaciones de los especialistas ni se crean otras EPP.

Las pruebas usan matrícula ficticia y motor sustituido. Cubren preparación,
autorización, generación, guardado y actualización visible de conclusión/NEE,
reintentos, conservación de filas editadas y cambios simultáneos del equipo.
